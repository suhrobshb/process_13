# AI Engine – Quick Start Guide  

Everything you need to **clone, run, and test** the AI Engine on your own machine.

---

## 1 Prerequisites  

| Tool | Minimum Version | Notes |
|------|-----------------|-------|
| **Git** | 2.30 | clone the repo |
| **Python** | 3.10+ | quick-start / dev mode |
| **Node.js** | 18+ | only if you want to build the dashboard locally |
| **Docker & Compose** | 20.10 / v2.5 | full-stack deployment |

> **Tip:** You can choose either **Dev mode** (Python + SQLite) _or_ **Prod-like** (Docker Compose).  
> Dev mode is fastest; Docker gives the full PostgreSQL + Redis + Grafana stack.

---

## 2 Clone the Repository  

```bash
git clone https://github.com/suhrobshb/AI_engine.git
cd AI_engine
```

---

## 3 Dev Mode (⏱ 2 min) – Python + SQLite  

1. **Create virtual env & install deps**

   ```bash
   python -m venv venv
   source venv/bin/activate          # Windows: venv\Scripts\activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **Set SQLite database**

   ```bash
   export DATABASE_URL=sqlite:///demo.db     # Windows: set DATABASE_URL=sqlite:///demo.db
   ```

3. **Start API server**

   ```bash
   uvicorn ai_engine.main:app --reload --host 0.0.0.0 --port 8000
   ```

   ➜ Swagger UI: **http://localhost:8000/docs**  
   ➜ Health-check: **http://localhost:8000/health**

4. *(optional)* **Run tests**

   ```bash
   pytest -q
   ```

---

## 4 Prod-Like Mode (≈ 5 min) – Docker Compose  

```bash
# build + start all containers in detached mode
docker compose -f docker-compose.prod.yml up -d --build
```

Services & Ports  

| Service | URL |
|---------|-----|
| API (FastAPI) | http://localhost:8000 |
| Dashboard (Next.js) | http://localhost:3000 |
| Swagger docs | http://localhost:8000/docs |
| Grafana | http://localhost:3000/grafana (admin / admin) |
| Prometheus | http://localhost:9090 |

Stop everything:

```bash
docker compose -f docker-compose.prod.yml down -v
```

---

## 5 Authentication Flow (Dev or Docker)  

```bash
# 1. Register
curl -X POST http://localhost:8000/api/register \
     -H "Content-Type: application/json" \
     -d '{"username":"demo","email":"demo@example.com","password":"password123"}'

# 2. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/token \
  -d "username=demo&password=password123" | jq -r .access_token)

# 3. Call protected endpoint
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/users/me
```

---

## 6 Create & Run Your First Workflow  

### 6.1 Define a workflow (JSON)

```json
{
  "name": "Hello Workflow",
  "description": "My first AI Engine workflow",
  "status": "active",
  "steps": [
    {
      "id": "echo",
      "type": "shell",
      "params": { "command": "echo 'Hello World!'", "timeout": 5 }
    },
    {
      "id": "http",
      "type": "http",
      "params": { "url": "https://httpbin.org/get", "method": "GET" }
    }
  ]
}
```

Save as `workflow.json`.

### 6.2 Create the workflow

```bash
curl -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d @workflow.json \
     http://localhost:8000/api/workflows
# → note the returned "id"
```

### 6.3 Trigger execution

```bash
WORKFLOW_ID=<id_from_previous_step>
EXEC=$(curl -s -H "Authorization: Bearer $TOKEN" \
        -X POST http://localhost:8000/api/workflows/$WORKFLOW_ID/trigger | jq -r .execution_id)

# poll for status
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/executions/$EXEC
```

When `status` becomes `completed`, check `result.results` for per-step output.

---

## 7 Upload a Task Recording  

```bash
curl -H "Authorization: Bearer $TOKEN" \
     -F file=@my_recording.zip \
     http://localhost:8000/api/tasks/upload
```

After processing you can fetch task clusters:

```bash
TASK_ID=<response.id>
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/tasks/$TASK_ID/clusters
```

---

## 8 Dashboard (UI) Quick Tour  

1. Open **http://localhost:3000**  
2. Sign-in with the same `demo / password123` credentials  
3. Explore tabs:  
   * **Tasks** – list & view recordings  
   * **Workflow Builder** – drag-and-drop nodes, save → calls `/api/workflows`  
   * **Graph** – interactive D3 visualisation of task clusters  
   * **Executions** – real-time status table  

---

## 9 Troubleshooting  

| Issue | Fix |
|-------|-----|
| `psycopg2.OperationalError` | PostgreSQL container not running → `docker compose up db` or switch to SQLite |
| `Error connecting Redis` | Redis container down → `docker compose up redis` |
| 404 on `/api/workflows` | Use `/api/workflows`, **not** `/api/workflows/workflows` |
| CORS errors from UI | Edit `cors_config` in `ai_engine/main.py` to whitelist the dashboard origin |

---

## 10 Next Steps  

* **Add new runner** – subclass `Runner`, register in `RunnerFactory`  
* **Extend UI** – components in `dashboard_ui/` (Next.js 14)  
* **Enable tenant-level workflow isolation** – update `workflow_router.py` and re-enable skipped tests  
* **Deploy to cloud** – CI/CD pipeline (`.github/workflows/ci-cd.yml`) builds & pushes images, servers run `docker-compose.prod.yml`

---

### 🎉 You’re ready!  
Clone, run, explore the docs, create workflows, upload tasks, and start automating.  
Happy hacking!
