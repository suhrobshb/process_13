#!/bin/bash

# production-setup.sh
# This script automates the setup and deployment of the AI Engine in a production environment.

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
# Default values - can be overridden by environment variables or command line args
DOMAIN_NAME="${DOMAIN_NAME:-your-domain.com}" # IMPORTANT: Change this to your actual domain
EMAIL="${EMAIL:-your-email@example.com}"     # Email for Let's Encrypt
PROJECT_DIR="/opt/ai_engine"                 # Where the project will be cloned/deployed

# --- Utility Functions ---

log_info() {
  echo -e "\n\033[1;34mINFO:\033[0m $1"
}

log_success() {
  echo -e "\n\033[1;32mSUCCESS:\033[0m $1"
}

log_error() {
  echo -e "\n\033[1;31mERROR:\033[0m $1" >&2
}

check_command() {
  if ! command -v "$1" &> /dev/null; then
    log_error "$1 is not installed. Please install it and try again."
    exit 1
  fi
}

# --- Setup Steps ---

check_system_requirements() {
  log_info "Checking system requirements..."
  check_command "git"
  check_command "docker"
  check_command "docker-compose" || check_command "docker compose" # Check for both docker-compose and docker compose plugin
  check_command "curl"
  check_command "sed"
  log_success "System requirements met."
}

setup_project_directory() {
  log_info "Setting up project directory: $PROJECT_DIR"
  if [ ! -d "$PROJECT_DIR" ]; then
    git clone https://github.com/suhrobshb/AI_engine.git "$PROJECT_DIR"
    log_success "Project cloned."
  else
    log_info "Project directory already exists. Pulling latest changes..."
    (cd "$PROJECT_DIR" && git pull)
    log_success "Latest changes pulled."
  fi
  # Ensure correct permissions for storage volumes
  mkdir -p "$PROJECT_DIR/storage"
  chmod -R 777 "$PROJECT_DIR/storage" # Ensure Docker containers can write
  log_success "Project directory ready."
}

generate_env_file() {
  log_info "Generating .env.prod file..."
  if [ -f "$PROJECT_DIR/.env.prod" ]; then
    log_info ".env.prod already exists. Skipping generation. Please edit it manually if needed."
  else
    # Prompt for sensitive variables if not already set
    read -p "Enter PostgreSQL password (e.g., secure_password): " -r POSTGRES_PASSWORD_INPUT
    read -p "Enter Redis password (e.g., secure_redis_password): " -r REDIS_PASSWORD_INPUT
    read -p "Enter application SECRET_KEY (e.g., openssl rand -hex 32): " -r SECRET_KEY_INPUT
    read -p "Enter OpenAI API Key (optional): " -r OPENAI_API_KEY_INPUT
    read -p "Enter Grafana Admin Password (e.g., secure_grafana_password): " -r GRAFANA_ADMIN_PASSWORD_INPUT

    cat <<EOF > "$PROJECT_DIR/.env.prod"
# Production Environment Variables
POSTGRES_DB=ai_engine_prod
POSTGRES_USER=ai_engine_user
POSTGRES_PASSWORD=${POSTGRES_PASSWORD_INPUT}
DATABASE_URL=postgresql://\${POSTGRES_USER}:\${POSTGRES_PASSWORD}@db:5432/\${POSTGRES_DB}

REDIS_PASSWORD=${REDIS_PASSWORD_INPUT}
REDIS_URL=redis://redis:6379/1
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

SECRET_KEY=${SECRET_KEY_INPUT}
ACCESS_TOKEN_EXPIRE_MINUTES=30

OPENAI_API_KEY=${OPENAI_API_KEY_INPUT}

DOMAIN_NAME=${DOMAIN_NAME}

GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD_INPUT}
GRAFANA_ROOT_URL=http://localhost:3000 # Adjust if Grafana is exposed publicly

API_IMAGE_TAG=main # Or specific commit SHA
DASHBOARD_IMAGE_TAG=main # Or specific commit SHA

LOG_LEVEL=INFO
AGENT_OUTPUT_DIR=/app/recordings
TASK_UPLOAD_URL=http://api:8000/api/tasks/upload
EOF
    log_success ".env.prod file generated. Please review and update it with actual values."
  fi
}

generate_ssl_certificates() {
  log_info "Generating SSL certificates with Certbot for $DOMAIN_NAME..."
  
  # Create Nginx config directory if it doesn't exist
  mkdir -p "$PROJECT_DIR/nginx/conf.d"
  
  # Create a dummy Nginx config for Certbot to use
  cat <<EOF > "$PROJECT_DIR/nginx/conf.d/default.conf"
server {
    listen 80;
    server_name ${DOMAIN_NAME} www.${DOMAIN_NAME};
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    location / {
        return 404;
    }
}
EOF

  # Start Nginx temporarily for Certbot
  docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" up -d nginx

  # Request certificates
  docker run --rm --name certbot \
    -v "$PROJECT_DIR/certbot/www:/var/www/certbot" \
    -v "$PROJECT_DIR/certbot/conf:/etc/letsencrypt" \
    certbot/certbot certonly --webroot -w /var/www/certbot \
    -d "$DOMAIN_NAME" -d "www.$DOMAIN_NAME" \
    --agree-tos --non-interactive --email "$EMAIL"

  # Stop temporary Nginx
  docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" stop nginx
  
  # Remove dummy config
  rm "$PROJECT_DIR/nginx/conf.d/default.conf"

  log_success "SSL certificates generated."
}

initialize_database() {
  log_info "Initializing database and creating default auth data..."
  # Run init_auth.py script inside the API container
  docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" run --rm api python scripts/init_auth.py
  log_success "Database initialized and default auth data created."
}

start_services() {
  log_info "Starting all services..."
  # Use the production Docker Compose file
  docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" up -d --build --remove-orphans
  log_success "All services started. Check logs for status."
  log_info "API should be available at https://$DOMAIN_NAME/api"
  log_info "Dashboard should be available at https://$DOMAIN_NAME"
  log_info "Grafana should be available at http://localhost:3000 (if exposed locally)"
  log_info "Prometheus should be available at http://localhost:9090 (if exposed locally)"
}

setup_monitoring() {
  log_info "Setting up monitoring services..."
  # Create monitoring directory if it doesn't exist
  mkdir -p "$PROJECT_DIR/monitoring"
  
  # Start monitoring services
  docker-compose -f "$PROJECT_DIR/monitoring/docker-compose.monitoring.yml" up -d
  log_success "Monitoring services started."
}

# --- Main Script Execution ---

main() {
  log_info "Starting AI Engine Production Setup Script..."

  check_system_requirements
  setup_project_directory
  
  # Navigate into the project directory for subsequent commands
  cd "$PROJECT_DIR"

  generate_env_file
  
  # Create necessary directories for Nginx and Certbot
  mkdir -p nginx/conf.d certbot/www certbot/conf postgres/init redis

  # Generate SSL certificates only if they don't exist
  if [ ! -f "$PROJECT_DIR/certbot/conf/live/$DOMAIN_NAME/fullchain.pem" ]; then
    generate_ssl_certificates
  else
    log_info "SSL certificates already exist. Skipping generation."
  fi

  # Build Docker images first to catch errors early
  log_info "Building Docker images..."
  docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" build
  log_success "Docker images built."

  initialize_database
  start_services
  setup_monitoring

  log_success "AI Engine Production Setup Complete!"
}

# Run the main function
main "$@"
