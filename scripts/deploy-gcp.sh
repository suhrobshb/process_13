#!/bin/bash
#
# AI Engine - Google Cloud Platform Deployment Script
# ==================================================
#
# This script automates the deployment of the AI Engine to Google Cloud Platform.
# It handles:
#   - Project setup and authentication
#   - Cloud SQL (PostgreSQL) database creation and configuration
#   - Secret Manager setup for API keys and credentials
#   - Container image building and pushing to GCR
#   - Cloud Run deployment
#   - Monitoring setup with Prometheus/Grafana
#
# Usage:
#   ./deploy-gcp.sh [options]
#
# Options:
#   --project-id=<id>       GCP project ID (required)
#   --region=<region>       GCP region (default: us-central1)
#   --db-tier=<tier>        Database tier (default: db-f1-micro)
#   --db-password=<pwd>     Database password (will prompt if not provided)
#   --service-account=<sa>  Service account name (default: ai-engine-sa)
#   --openai-key=<key>      OpenAI API key (will prompt if not provided)
#   --jwt-secret=<secret>   JWT secret key (will generate if not provided)
#   --headless              Run in non-interactive mode
#   --skip-db               Skip database creation
#   --skip-build            Skip container building
#   --help                  Show this help message
#
# Example:
#   ./deploy-gcp.sh --project-id=my-ai-engine --region=europe-west1
#
# Author: AI Engine Team
# Date: June 27, 2025
# Version: 1.0.0

set -e  # Exit on any error

# Default values
PROJECT_ID=""
REGION="us-central1"
DB_TIER="db-f1-micro"
DB_PASSWORD=""
SERVICE_ACCOUNT="ai-engine-sa"
OPENAI_KEY=""
JWT_SECRET=""
HEADLESS=false
SKIP_DB=false
SKIP_BUILD=false
DEPLOYMENT_ID=$(date +%Y%m%d%H%M%S)
LOG_FILE="deployment-$DEPLOYMENT_ID.log"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages
log() {
  local level=$1
  local message=$2
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  
  case $level in
    "INFO")
      echo -e "${GREEN}[INFO]${NC} $timestamp - $message"
      ;;
    "WARN")
      echo -e "${YELLOW}[WARN]${NC} $timestamp - $message"
      ;;
    "ERROR")
      echo -e "${RED}[ERROR]${NC} $timestamp - $message"
      ;;
    "STEP")
      echo -e "\n${BLUE}[STEP]${NC} $timestamp - $message"
      echo -e "${BLUE}=======================================================================${NC}"
      ;;
    *)
      echo -e "$timestamp - $message"
      ;;
  esac
  
  echo "[$level] $timestamp - $message" >> "$LOG_FILE"
}

# Function to show help message
show_help() {
  grep "^#" "$0" | grep -v "!/bin/bash" | sed 's/^#//'
  exit 0
}

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
  log "STEP" "Checking prerequisites"
  
  # Check for required commands
  local missing_commands=()
  for cmd in gcloud docker gsutil jq curl; do
    if ! command_exists "$cmd"; then
      missing_commands+=("$cmd")
    fi
  done
  
  if [ ${#missing_commands[@]} -gt 0 ]; then
    log "ERROR" "Missing required commands: ${missing_commands[*]}"
    log "INFO" "Please install the missing commands and try again."
    exit 1
  fi
  
  # Check if gcloud is authenticated
  if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" >/dev/null 2>&1; then
    log "ERROR" "Not authenticated with gcloud. Please run 'gcloud auth login' first."
    exit 1
  fi
  
  # Check if Docker is running
  if ! docker info >/dev/null 2>&1; then
    log "ERROR" "Docker is not running. Please start Docker and try again."
    exit 1
  }
  
  log "INFO" "All prerequisites met."
}

# Function to setup GCP project
setup_project() {
  log "STEP" "Setting up GCP project: $PROJECT_ID"
  
  # Set the project
  log "INFO" "Setting active project to $PROJECT_ID"
  gcloud config set project "$PROJECT_ID"
  
  # Enable required APIs
  log "INFO" "Enabling required GCP APIs. This may take a few minutes..."
  gcloud services enable \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    run.googleapis.com \
    sql-component.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com \
    monitoring.googleapis.com \
    logging.googleapis.com \
    cloudtrace.googleapis.com
  
  # Create service account if it doesn't exist
  if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com" >/dev/null 2>&1; then
    log "INFO" "Creating service account: $SERVICE_ACCOUNT"
    gcloud iam service-accounts create "$SERVICE_ACCOUNT" \
      --display-name="AI Engine Service Account"
  else
    log "INFO" "Service account $SERVICE_ACCOUNT already exists"
  fi
  
  # Grant required roles to service account
  log "INFO" "Granting required roles to service account"
  for role in roles/cloudsql.client roles/secretmanager.secretAccessor roles/monitoring.metricWriter roles/logging.logWriter; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
      --member="serviceAccount:$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com" \
      --role="$role"
  done
  
  log "INFO" "GCP project setup completed"
}

# Function to setup Cloud SQL
setup_database() {
  if [ "$SKIP_DB" = true ]; then
    log "INFO" "Skipping database setup as requested"
    return 0
  fi
  
  log "STEP" "Setting up Cloud SQL database"
  
  # Check if DB password is provided
  if [ -z "$DB_PASSWORD" ] && [ "$HEADLESS" = false ]; then
    read -sp "Enter database password: " DB_PASSWORD
    echo
    if [ -z "$DB_PASSWORD" ]; then
      log "ERROR" "Database password cannot be empty"
      exit 1
    fi
  elif [ -z "$DB_PASSWORD" ]; then
    DB_PASSWORD=$(openssl rand -base64 16)
    log "INFO" "Generated random database password"
  fi
  
  # Create database instance if it doesn't exist
  local instance_name="ai-engine-db"
  if ! gcloud sql instances describe "$instance_name" >/dev/null 2>&1; then
    log "INFO" "Creating Cloud SQL instance: $instance_name"
    gcloud sql instances create "$instance_name" \
      --database-version=POSTGRES_14 \
      --tier="$DB_TIER" \
      --region="$REGION" \
      --storage-size=10GB \
      --storage-auto-increase \
      --backup-start-time="23:00" \
      --availability-type=zonal \
      --root-password="$DB_PASSWORD"
  else
    log "INFO" "Cloud SQL instance $instance_name already exists"
  fi
  
  # Create database if it doesn't exist
  local db_name="autoops"
  if ! gcloud sql databases list --instance="$instance_name" --filter="name=$db_name" | grep -q "$db_name"; then
    log "INFO" "Creating database: $db_name"
    gcloud sql databases create "$db_name" --instance="$instance_name"
  else
    log "INFO" "Database $db_name already exists"
  fi
  
  # Create user if it doesn't exist
  local db_user="aiuser"
  if ! gcloud sql users list --instance="$instance_name" --filter="name=$db_user" | grep -q "$db_user"; then
    log "INFO" "Creating database user: $db_user"
    gcloud sql users create "$db_user" \
      --instance="$instance_name" \
      --password="$DB_PASSWORD"
  else
    log "INFO" "Database user $db_user already exists"
  fi
  
  # Get connection details
  local instance_connection_name=$(gcloud sql instances describe "$instance_name" --format="value(connectionName)")
  
  # Store database connection string in Secret Manager
  local db_connection_string="postgresql://$db_user:$DB_PASSWORD@localhost/$db_name?host=/cloudsql/$instance_connection_name"
  echo -n "$db_connection_string" | gcloud secrets create database-url --data-file=- --replication-policy="automatic" 2>/dev/null || \
    echo -n "$db_connection_string" | gcloud secrets versions add database-url --data-file=-
  
  log "INFO" "Database setup completed"
  log "INFO" "Connection name: $instance_connection_name"
}

# Function to setup secrets
setup_secrets() {
  log "STEP" "Setting up Secret Manager secrets"
  
  # Setup OpenAI API key
  if [ -z "$OPENAI_KEY" ] && [ "$HEADLESS" = false ]; then
    read -sp "Enter OpenAI API key: " OPENAI_KEY
    echo
  elif [ -z "$OPENAI_KEY" ]; then
    log "WARN" "No OpenAI API key provided. LLM features will not work."
    OPENAI_KEY="dummy-key-please-replace"
  fi
  
  echo -n "$OPENAI_KEY" | gcloud secrets create openai-api-key --data-file=- --replication-policy="automatic" 2>/dev/null || \
    echo -n "$OPENAI_KEY" | gcloud secrets versions add openai-api-key --data-file=-
  
  # Setup JWT secret
  if [ -z "$JWT_SECRET" ]; then
    JWT_SECRET=$(openssl rand -base64 32)
    log "INFO" "Generated random JWT secret"
  fi
  
  echo -n "$JWT_SECRET" | gcloud secrets create jwt-secret --data-file=- --replication-policy="automatic" 2>/dev/null || \
    echo -n "$JWT_SECRET" | gcloud secrets versions add jwt-secret --data-file=-
  
  log "INFO" "Secret Manager setup completed"
}

# Function to build and push Docker images
build_and_push_images() {
  if [ "$SKIP_BUILD" = true ]; then
    log "INFO" "Skipping image building as requested"
    return 0
  fi
  
  log "STEP" "Building and pushing Docker images"
  
  # Set GCR as Docker credential helper
  gcloud auth configure-docker gcr.io
  
  # Build images using docker-compose
  log "INFO" "Building Docker images"
  docker-compose -f docker-compose.prod.yml build
  
  # Tag and push images
  local services=("api" "worker" "dashboard")
  for service in "${services[@]}"; do
    local image_name="ai_engine_$service"
    local gcr_image="gcr.io/$PROJECT_ID/$image_name:$DEPLOYMENT_ID"
    
    log "INFO" "Tagging and pushing $image_name to $gcr_image"
    docker tag "$image_name" "$gcr_image"
    docker push "$gcr_image"
    
    # Also tag as latest
    local gcr_latest="gcr.io/$PROJECT_ID/$image_name:latest"
    docker tag "$image_name" "$gcr_latest"
    docker push "$gcr_latest"
  done
  
  log "INFO" "Docker images built and pushed successfully"
}

# Function to deploy to Cloud Run
deploy_to_cloud_run() {
  log "STEP" "Deploying to Cloud Run"
  
  # Deploy API service
  log "INFO" "Deploying API service to Cloud Run"
  gcloud run deploy ai-engine-api \
    --image="gcr.io/$PROJECT_ID/ai_engine_api:$DEPLOYMENT_ID" \
    --platform=managed \
    --region="$REGION" \
    --allow-unauthenticated \
    --service-account="$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com" \
    --add-cloudsql-instances="$PROJECT_ID:$REGION:ai-engine-db" \
    --set-secrets="DATABASE_URL=database-url:latest,OPENAI_API_KEY=openai-api-key:latest,JWT_SECRET=jwt-secret:latest" \
    --memory=1Gi \
    --cpu=1 \
    --concurrency=80 \
    --max-instances=10 \
    --min-instances=1
  
  # Deploy Dashboard service
  log "INFO" "Deploying Dashboard service to Cloud Run"
  gcloud run deploy ai-engine-dashboard \
    --image="gcr.io/$PROJECT_ID/ai_engine_dashboard:$DEPLOYMENT_ID" \
    --platform=managed \
    --region="$REGION" \
    --allow-unauthenticated \
    --service-account="$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com" \
    --set-env-vars="API_URL=https://ai-engine-api-$(gcloud run services describe ai-engine-api --platform=managed --region=$REGION --format='value(status.url)' | cut -d'/' -f3)" \
    --memory=512Mi \
    --cpu=1 \
    --concurrency=80 \
    --max-instances=5 \
    --min-instances=1
  
  # Deploy Worker service
  log "INFO" "Deploying Worker service to Cloud Run"
  gcloud run deploy ai-engine-worker \
    --image="gcr.io/$PROJECT_ID/ai_engine_worker:$DEPLOYMENT_ID" \
    --platform=managed \
    --region="$REGION" \
    --no-allow-unauthenticated \
    --service-account="$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com" \
    --add-cloudsql-instances="$PROJECT_ID:$REGION:ai-engine-db" \
    --set-secrets="DATABASE_URL=database-url:latest,OPENAI_API_KEY=openai-api-key:latest,JWT_SECRET=jwt-secret:latest" \
    --memory=2Gi \
    --cpu=2 \
    --concurrency=10 \
    --max-instances=5 \
    --min-instances=1
  
  # Get service URLs
  local api_url=$(gcloud run services describe ai-engine-api --platform=managed --region="$REGION" --format='value(status.url)')
  local dashboard_url=$(gcloud run services describe ai-engine-dashboard --platform=managed --region="$REGION" --format='value(status.url)')
  
  log "INFO" "Deployment to Cloud Run completed"
  log "INFO" "API URL: $api_url"
  log "INFO" "Dashboard URL: $dashboard_url"
}

# Function to setup monitoring
setup_monitoring() {
  log "STEP" "Setting up monitoring"
  
  # Create a GKE cluster for Prometheus and Grafana if it doesn't exist
  local cluster_name="monitoring-cluster"
  if ! gcloud container clusters describe "$cluster_name" --region="$REGION" >/dev/null 2>&1; then
    log "INFO" "Creating GKE cluster for monitoring: $cluster_name"
    gcloud container clusters create "$cluster_name" \
      --region="$REGION" \
      --num-nodes=1 \
      --machine-type=e2-standard-2
  else
    log "INFO" "GKE cluster $cluster_name already exists"
  fi
  
  # Get credentials for the cluster
  gcloud container clusters get-credentials "$cluster_name" --region="$REGION"
  
  # Apply Kubernetes manifests for Prometheus and Grafana
  log "INFO" "Deploying Prometheus and Grafana to GKE"
  kubectl apply -f monitoring/kubernetes/prometheus.yaml
  kubectl apply -f monitoring/kubernetes/grafana.yaml
  
  # Wait for deployments to be ready
  kubectl rollout status deployment/prometheus -n monitoring
  kubectl rollout status deployment/grafana -n monitoring
  
  # Create a LoadBalancer service for Grafana if it doesn't exist
  if ! kubectl get service grafana -n monitoring | grep -q LoadBalancer; then
    log "INFO" "Creating LoadBalancer service for Grafana"
    kubectl expose deployment grafana --type=LoadBalancer --port=80 --target-port=3000 -n monitoring
  fi
  
  # Get Grafana URL
  local grafana_ip=""
  local retries=0
  while [ -z "$grafana_ip" ] && [ "$retries" -lt 10 ]; do
    grafana_ip=$(kubectl get service grafana -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [ -z "$grafana_ip" ]; then
      log "INFO" "Waiting for Grafana LoadBalancer IP..."
      sleep 10
      retries=$((retries + 1))
    fi
  done
  
  if [ -n "$grafana_ip" ]; then
    log "INFO" "Grafana URL: http://$grafana_ip"
    log "INFO" "Default credentials: admin / admin"
  else
    log "WARN" "Could not get Grafana LoadBalancer IP. Please check manually."
  fi
  
  log "INFO" "Monitoring setup completed"
}

# Function to initialize the database schema
initialize_database() {
  log "STEP" "Initializing database schema"
  
  # Run database migrations
  log "INFO" "Running database migrations"
  gcloud run jobs create ai-engine-db-init \
    --image="gcr.io/$PROJECT_ID/ai_engine_api:$DEPLOYMENT_ID" \
    --command="python" \
    --args="-m","alembic","upgrade","head" \
    --service-account="$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com" \
    --add-cloudsql-instances="$PROJECT_ID:$REGION:ai-engine-db" \
    --set-secrets="DATABASE_URL=database-url:latest" \
    --region="$REGION"
  
  # Execute the job
  gcloud run jobs execute ai-engine-db-init --region="$REGION"
  
  log "INFO" "Database schema initialized"
}

# Function to display deployment summary
deployment_summary() {
  log "STEP" "Deployment Summary"
  
  local api_url=$(gcloud run services describe ai-engine-api --platform=managed --region="$REGION" --format='value(status.url)')
  local dashboard_url=$(gcloud run services describe ai-engine-dashboard --platform=managed --region="$REGION" --format='value(status.url)')
  
  echo -e "\n${GREEN}=============================================================${NC}"
  echo -e "${GREEN}                 AI ENGINE DEPLOYMENT COMPLETE                ${NC}"
  echo -e "${GREEN}=============================================================${NC}"
  echo -e "Project ID:         ${BLUE}$PROJECT_ID${NC}"
  echo -e "Region:             ${BLUE}$REGION${NC}"
  echo -e "Deployment ID:      ${BLUE}$DEPLOYMENT_ID${NC}"
  echo -e "API URL:            ${BLUE}$api_url${NC}"
  echo -e "Dashboard URL:      ${BLUE}$dashboard_url${NC}"
  echo -e "API Documentation:  ${BLUE}$api_url/docs${NC}"
  echo -e "Log File:           ${BLUE}$LOG_FILE${NC}"
  echo -e "\n${YELLOW}Next Steps:${NC}"
  echo -e "1. Visit the Dashboard URL to access the AI Engine UI"
  echo -e "2. Create a user account using the registration endpoint"
  echo -e "3. Set up your first workflow using the dashboard"
  echo -e "4. Check the monitoring dashboard for system health"
  echo -e "\n${YELLOW}For any issues, please check the deployment log:${NC} $LOG_FILE"
  echo -e "${GREEN}=============================================================${NC}\n"
}

# Parse command line arguments
while [ "$#" -gt 0 ]; do
  case "$1" in
    --project-id=*)
      PROJECT_ID="${1#*=}"
      ;;
    --region=*)
      REGION="${1#*=}"
      ;;
    --db-tier=*)
      DB_TIER="${1#*=}"
      ;;
    --db-password=*)
      DB_PASSWORD="${1#*=}"
      ;;
    --service-account=*)
      SERVICE_ACCOUNT="${1#*=}"
      ;;
    --openai-key=*)
      OPENAI_KEY="${1#*=}"
      ;;
    --jwt-secret=*)
      JWT_SECRET="${1#*=}"
      ;;
    --headless)
      HEADLESS=true
      ;;
    --skip-db)
      SKIP_DB=true
      ;;
    --skip-build)
      SKIP_BUILD=true
      ;;
    --help)
      show_help
      ;;
    *)
      log "ERROR" "Unknown option: $1"
      show_help
      ;;
  esac
  shift
done

# Validate required parameters
if [ -z "$PROJECT_ID" ]; then
  log "ERROR" "Project ID is required. Use --project-id=<id> to specify."
  exit 1
fi

# Main deployment flow
log "INFO" "Starting AI Engine deployment to GCP"
log "INFO" "Project ID: $PROJECT_ID"
log "INFO" "Region: $REGION"
log "INFO" "Deployment ID: $DEPLOYMENT_ID"

check_prerequisites
setup_project
setup_database
setup_secrets
build_and_push_images
deploy_to_cloud_run
initialize_database
setup_monitoring
deployment_summary

log "INFO" "Deployment completed successfully"
