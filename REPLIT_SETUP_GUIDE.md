# AI Engine – Replit Setup & Testing Guide

Welcome!  
This document walks you **step-by-step** through cloning, configuring and **running the AI Engine inside Replit** so you can test every core feature (Shell, HTTP, Decision, LLM, Browser automation, Workflows) entirely from your browser.

---

## 1  Fork or Import the Repository

1. Log-in to [replit.com](https://replit.com).
2. Click **“+ Create Repl” → “Import from GitHub”**.  
   Paste the repo URL:  
   `https://github.com/suhrobshb/AI_engine`
3. Wait for Replit to import & index the project.

> **Tip:** Replit uses the root file `.replit` to decide which command to run.  
> We already committed a ready-to-go `.replit` that launches `replit_main.py`.

---

## 2  Install Dependencies

Replit detects `requirements.txt` automatically.  
If the Nix build fails, open the **“Shell” tab** at the bottom and run:

```bash
pip install -r requirements.txt
# New in the latest build:  
# `evdev-binary` is now part of `requirements.txt` to enable low-level
# keyboard / mouse capture for the recorder. Replit will compile it
# automatically – no extra steps needed.
```

### Optional – Browser automation  
If you want to test Playwright actions as well (works in headless mode):

```bash
pip install playwright
python -m playwright install chromium
# (Our `.replit` file already runs this on first boot, so you usually
# don’t need to run it manually – it’s shown here for completeness.)
```

*(Desktop automation via PyAutoGUI needs a GUI/display and is **disabled** in the Replit demo.)*

---

## 3  Add Secrets (Environment Variables)

Open **Tools → Secrets** (🔑 icon) and add:

| Key               | Value                                    | Notes                                   |
|-------------------|------------------------------------------|-----------------------------------------|
| `OPENAI_API_KEY`  | **Your OpenAI key**                      | Needed for LLM runner. Omit to test mock mode. |
| `DATABASE_URL`    | `sqlite:///ai_engine_replit.db`          | Already set in `replit_main.py`, change if desired. |

*(All other variables have sensible defaults for Replit.)*

---

## 4  File Structure Used by Replit Demo

```
.
├── replit_main.py           # ➜ Entry-point FastAPI app prepared for Replit
├── templates/
│   └── index.html           # Single-page dashboard UI
├── requirements.txt         # Python dependencies
└── .replit                  # Tells Replit to run `python replit_main.py`
```

The full AI Engine codebase ( `ai_engine/`, `agent/`, etc.) is untouched and available for deeper development.

---

## 5  Run the Server

Hit the **“Run” button** (or `Ctrl + Enter`).  
Replit will:

1. Install missing packages (first run only)  
2. Launch **Uvicorn** on port `8080`

When you see:

```
INFO:     Uvicorn running on http://0.0.0.0:8080
```

click the **“Open in Browser”** button.  
URL will look like: `https://AI_engine.<your-repl-subdomain>.repl.co`

---

## 6  Using the Web Dashboard

The Replit demo dashboard provides four tabs:

1. **Runners** – test Shell / HTTP / Decision / LLM / Browser actions live  
2. **Workflows** – create JSON workflows, execute or delete them  
3. **Executions** – inspect recent workflow runs & results  
4. **System Status** – environment info & runner availability

### Quick smoke test

* **Shell runner** – default command prints “Hello from Shell Runner”  
* **HTTP runner** – default GET to `https://httpbin.org/get` returns 200  
* **Decision runner** – expression `value > 10` with value 20 goes to `high_value_path`  
* **LLM runner** – enter a simple prompt (needs `OPENAI_API_KEY`)  
* **Browser runner** – choose *Visit URL* → `https://example.com` ➜ takes a screenshot (visible below result).

---

## 7  Creating & Executing a Workflow

1. Go to **Workflows → “Create Workflow”**  
2. Keep the default JSON (two shell steps) or paste your own.  
3. Click **Create Workflow** → it appears in the list.  
4. Click **Execute** → refresh **Executions** tab to watch status.  
   *When completed* click an execution to inspect `stdout` of each step.

---

## 8  Known Limitations on Replit

| Feature                  | Status on Replit | Notes                                                                    |
|--------------------------|------------------|--------------------------------------------------------------------------|
| Desktop (Python GUI)     | ❌ disabled      | No display / X11 in Replit containers.                                   |
| Browser (Playwright)     | ✅ headless only | Requires `playwright` install; screenshots served via `/screenshots/*`.  |
| Long-running workflows   | Replit limits    | Free tier sleeps after inactivity; use paid plan for persistent jobs.    |
| Docker / Celery workers  | Not in Replit    | The demo runs single-process FastAPI; for queues use e.g. Cloud Run.     |

---

## 9  Troubleshooting

| Issue / Error                                     | Fix |
|---------------------------------------------------|-----|
| `KeyError: 'DISPLAY'` on import `pyautogui`       | Desktop runner auto-disables; ignore or hide PyAutoGUI import. |
| `openai.error.AuthenticationError`                | Add a valid `OPENAI_API_KEY` in Secrets. |
| Playwright `Executable does not exist`            | Run `python -m playwright install chromium` in the Shell. |
| Port `8080` already in use                        | Replit auto-assigns; ensure only one `uvicorn.run()` instance. |
| `evdev` compile fails (very rare)                 | Re-run `pip install evdev-binary --force-reinstall`; ensure `.replit` uses the latest requirements. |
| Log output missing                                | Logging level defaults to **INFO**; set `LOG_LEVEL=DEBUG` in Secrets to see more details. |

---

## 10  Next Steps after Replit Testing

1. **Commit changes** back to GitHub (Replit pushes automatically).  
2. **Run full test suite** locally or in CI (`pytest`).  
3. **Deploy to Google Cloud** using `scripts/deploy-gcp.sh` (see docs).  
4. **Invite teammates** to your Replit for collaborative workflow design.

---

### 🎉 You’re all set!

Within minutes you can prototype, run and share AI Engine workflows entirely in the browser.  
Happy automating! If you run into issues, open the Replit Shell and inspect logs printed by **`replit_main.py`**.  

Enjoy building! 🚀
