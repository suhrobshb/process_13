#!/usr/bin/env python3
"""
Minimal launcher for the AI-driven RPA platform - no external dependencies required.
"""
import asyncio, os, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).parent.resolve()
ENV = os.environ.copy()
ENV["PYTHONUNBUFFERED"] = "1"

# Use in-memory SQLite for simplicity
ENV["DATABASE_URL"] = "sqlite:///./app.db"

async def run_service(name, cmd, cwd=None):
    work_dir = cwd or ROOT
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=work_dir, env=ENV,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    print(f"▶ {name} started (pid {proc.pid})")
    
    async for line in proc.stdout:
        try:
            print(f"[{name}] {line.decode().strip()}")
        except:
            pass
    
    await proc.wait()

async def main():
    print("🚀 Starting minimal AI-driven RPA platform...")
    print("   API:  http://localhost:8000")
    print("   Stop: Ctrl+C\n")
    
    # Start only the API service for now
    await run_service("API", ["python3", "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"])

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹  Platform stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)