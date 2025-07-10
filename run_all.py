#!/usr/bin/env python3
"""
One-click launcher for the whole Automations platform.

Usage:
    python run_all.py              # dev mode (hot-reload, Tailwind JIT, verbose logs)
    python run_all.py --prod       # production assets, no reload, optimized workers
"""
import argparse, asyncio, os, pathlib, subprocess, sys
from textwrap import dedent

ROOT = pathlib.Path(__file__).parent.resolve()
ENV  = os.environ.copy()
ENV["PYTHONUNBUFFERED"] = "1"

BACKEND_CMD_DEV  = ["uvicorn", "main:app", "--reload", "--port", "8000"]
BACKEND_CMD_PROD = ["uvicorn", "main:app", "--workers", "4", "--port", "8000"]

UI_CMD_DEV       = ["npm", "run", "dev"]
UI_CMD_PROD      = ["npm", "run", "start"]

RUNNER_CMD       = ["python", "-m", "ai_engine.runner_service"]

async def run(name, cmd, cwd=None):
    work_dir = cwd or ROOT
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=work_dir, env=ENV,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    print(f"▶ {name} started  (pid {proc.pid})")
    async for line in proc.stdout:
        sys.stdout.buffer.write(f"[{name}] ".encode() + line)
    await proc.wait()

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prod", action="store_true", help="Start in production mode")
    args = ap.parse_args()

    # Ensure Playwright browsers are present once on first run
    if not (ROOT / ".pw_installed").exists():
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        (ROOT / ".pw_installed").touch()

    # Spin up Postgres if the user doesn't already have one (docker-in-docker friendly)
    if os.system("pg_isready -q") != 0:
        subprocess.run(["docker", "compose", "up", "-d", "postgres"], check=True)

    backend = BACKEND_CMD_PROD if args.prod else BACKEND_CMD_DEV
    ui      = UI_CMD_PROD      if args.prod else UI_CMD_DEV

    await asyncio.gather(
        run("API ", backend),
        run("UI  ", ui, ROOT / "dashboard_ui_v2"),
        run("RUNR", RUNNER_CMD),
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹  Stopped by user")