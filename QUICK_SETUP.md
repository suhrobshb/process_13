# 🚀 Quick Setup - 10 Minutes to Full Platform

The fastest way to bring up the entire AI-driven RPA platform locally—API + UI + runner—without containers.

## 0️⃣ One-time Prerequisites

| Tool | Install Command |
|------|-----------------|
| **Python 3.11+** | `brew install python@3.11` · `choco install python --version 3.11` · [python.org](https://python.org) |
| **Node 18 LTS + pnpm** | `corepack enable && corepack prepare pnpm@latest --activate` |
| **Playwright browsers** | `python -m playwright install chromium` |
| **Git** | System package manager |

*(No Docker required for this workflow)*

## 1️⃣ Clone and Setup Virtual Environment

```bash
git clone https://github.com/suhrobshb/process_13.git
cd process_13

# Switch to optimized branch
git checkout optimized-main-branch

# Create virtual environment
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
```

## 2️⃣ Install Dependencies

```bash
# Backend dependencies (FastAPI, SQLModel, Playwright helpers...)
pip install -r requirements/dev.txt

# Frontend dependencies (Next.js + shadcn/ui components)
pnpm install --filter dashboard_ui_v2
```

## 3️⃣ Run the Entire Stack

```bash
python run_all.py
```

### What You'll See:
```
🚀 Starting platform...
   API:  http://localhost:8000
   UI:   http://localhost:3000
   Stop: Ctrl+C

▶ API  started  (pid 4218)
▶ UI   started  (pid 4220)
▶ RUNR started  (pid 4224)
```

The script automatically:
- ✅ Spins up lightweight Postgres container if nothing on port 5432
- ✅ Ensures Chromium is installed for Playwright on first launch
- ✅ Hot-reloads code and UI as you edit files
- ✅ Unified logging with service prefixes

**Stop everything**: `Ctrl+C`

## 4️⃣ Open the Modern Dashboard

1. **Browse**: http://localhost:3000
2. **Sign in**: Enter any email (dev mode skips magic-link)
3. **Record**: Click Record button (Chrome extension or desktop recorder)
4. **Convert**: Recordings → Convert to Workflow
5. **Execute**: Run workflows and watch live logs

## 5️⃣ Platform Features

### 🎯 Core User Journey:
- **Dashboard** → View workflow stats, success rates, system health
- **Recording Studio** → Real-time process capture and workflow generation
- **Workflows** → Visual editor with drag-and-drop nodes
- **Executions** → Live monitoring and execution history
- **Settings** → Profile, API tokens, workspace management

### 🔧 Development Features:
- **Hot Reload** → Both backend and frontend
- **Unified Logs** → All services with prefixes
- **Auto Setup** → Postgres and Playwright browsers
- **Clean Shutdown** → Single Ctrl+C stops everything

## 🔧 Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: pnpm` | Run `corepack enable && corepack prepare pnpm@latest --activate` |
| Browser never opens | `python -m playwright install chromium` (check corporate proxy) |
| Port 3000/8000 busy | `lsof -i :3000` → kill process, or edit `run_all.py` ports |
| Cannot connect to database | Local Postgres on 5432 with different creds → stop it or set `DATABASE_URL` |

## 🎯 Production Mode

```bash
python run_all.py --prod
```

Production features:
- Multi-worker API (4 workers)
- Optimized frontend assets
- Production-ready configurations

---

**That's it!** ✨ One command, full platform, ready to demo.