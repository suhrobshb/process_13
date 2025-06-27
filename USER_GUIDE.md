# AI Engine – User Guide  

Welcome! This document walks you through **running, exploring and testing the AI Engine as an end-user**.  
You will learn how to:

* start the system locally or with Docker  
* register, log-in and obtain a JWT  
* create, trigger and monitor workflows  
* upload task recordings  
* use the React dashboard UI  
* verify health & metrics

---

## 1  Quick Start Options  

| Option | When to use | Command |
|--------|-------------|---------|
| **Python + SQLite** (dev) | Fast, no external deps | `DATABASE_URL=sqlite:///demo.db uvicorn ai_engine.main:app --reload` |
| **Full stack** (prod-like) | Includes PostgreSQL, Redis, Nginx, Prometheus, Grafana | `docker compose -f docker-compose.prod.yml up -d` |

> **Ports**  
> • API: `http://localhost:8000` (or behind Nginx `https://<domain>/api`)  
> • Dashboard: `http://localhost:3000`  
> • Docs: `/docs` (Swagger)  
> • Grafana: `http://localhost:3000/grafana` (if exposed)

---

## 2  Authentication Flow  

### 2.1 Register

```bash
curl -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","email":"demo@example.com","password":"securePass"}'
```

### 2.2 Login

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/token \
  -d "username=demo&password=securePass" | jq -r .access_token)
echo "JWT: $TOKEN"
```

### 2.3 Use the token

```bash
AUTH="-H Authorization:Bearer:$TOKEN"
curl $AUTH http://localhost:8000/api/users/me
```

---

## 3  Exploring the API (Swagger)  

Open `http://localhost:8000/docs` in a browser, click “Authorize”, paste your JWT, then interact with every endpoint.

Key groups:

* `/api/workflows` – CRUD + trigger  
* `/api/executions` – monitor & retry  
* `/api/tasks` – upload recordings / clusters  
* `/api/tenants` – multi-tenant admin (if enabled)

---

## 4  Creating & Running a Workflow  

### 4.1 Sample workflow JSON

```json
{
  "name": "Hello Workflow",
  "description": "Demo multi-step workflow",
  "status": "active",
  "steps": [
    {
      "id": "hello",
      "type": "shell",
      "params": { "command": "echo 'Hello World ☺'", "timeout": 5 }
    },
    {
      "id": "http_get",
      "type": "http",
      "params": { "url": "https://httpbin.org/get", "method": "GET" }
    }
  ]
}
```

### 4.2 Create

```bash
curl $AUTH -H "Content-Type: application/json" \
     -d @workflow.json \
     http://localhost:8000/api/workflows
```

Response returns `"id": <WORKFLOW_ID>`.

### 4.3 Trigger execution

```bash
EXEC=$(curl -s $AUTH -X POST \
  http://localhost:8000/api/workflows/$WORKFLOW_ID/trigger | jq -r .execution_id)
```

### 4.4 Poll status

```bash
curl $AUTH http://localhost:8000/api/executions/$EXEC
```

Status progresses **pending → running → completed/failed**.  
When completed, the `result.results` object contains per-step output.

---

## 5  Uploading a Task Recording  

```bash
curl $AUTH -F file=@my_recording.zip \
     http://localhost:8000/api/tasks/upload
```

The backend:

1. stores the zip under `storage/users/<id>/recordings`  
2. enqueues processing (`process_task`)  
3. exposes clusters at `/api/tasks/<task_id>/clusters`

---

## 6  Dashboard UI  

If you included the dashboard service (Docker) browse to:

```
http://localhost:3000
```

Features:

* Task sidebar – list & play recordings  
* D3 graph – visualise clusters / relationships  
* Workflow builder – drag-and-drop nodes, save (calls `/api/workflows`)  
* Trigger buttons – start workflows & watch live status

Log-in with the same credentials as the API.

---

## 7  Observability  

* **Prometheus**: `http://localhost:9090`  
  * Targets: API, Redis, PostgreSQL, Celery, Nginx, node_exporter  
* **Grafana**: `http://localhost:3000/grafana`  
  * Default user/password: `admin / admin` (change in `.env`)  
  * Dashboards: API latency, Workflow throughput, Celery queue length

---

## 8  Common Problems & Fixes  

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `psycopg2.OperationalError` | PostgreSQL not running | `docker compose up db` or use SQLite |
| `redis.exceptions.ConnectionError` | Redis missing | start Redis container |
| 404 on `/api/workflows` | Wrong URL (double prefix) | ensure path is `/api/workflows`, not `/api/workflows/workflows` |
| CORS blocked | Frontend origin not allowed | edit `cors_config` in `ai_engine/main.py` |

---

## 9  Next Steps & Extending Functionality  

1. **Add new Runner**  
   *Create `MyRunner` subclass in `workflow_runners.py`, register in `RunnerFactory`.*

2. **Add UI component**  
   *Extend `dashboard_ui` Next.js pages; TSX components auto-watch via `npm run dev`.*

3. **Integrate external services**  
   *Use HTTP steps or write a custom runner for Kafka, Slack, AWS, etc.*

4. **Enable multi-tenant isolation for workflows**  
   *Audit `workflow_router.py` and re-introduce role/tenant checks, then re-run failing tests.*

---

## 10  Clean-up  

```bash
# Stop containers
docker compose down -v

# Remove demo SQLite DB
rm demo.db
```

---

### 🎉 You now have full end-to-end access to the AI Engine.  
Create workflows, upload tasks, monitor executions, and extend as needed!
