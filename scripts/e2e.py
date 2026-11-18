"""Run browser acceptance against disposable servers and a temporary database.

Usage from repository root: .venv-e2e/bin/python scripts/e2e.py
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "e2e"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def ready(url, process):
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Server exited with {process.returncode}: {url}; see {OUTPUT}")
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"Server did not become ready: {url}")


def main():
    from e2e_scenarios import run_scenarios

    OUTPUT.mkdir(parents=True, exist_ok=True)
    python = ROOT / "backend" / ".venv" / "bin" / "python"
    vite = ROOT / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
    if not python.exists() or not vite.exists():
        raise SystemExit("Install backend requirements-dev.txt and run npm ci in frontend first.")

    with ExitStack() as stack:
        temp_dir = stack.enter_context(tempfile.TemporaryDirectory(prefix="fft-e2e-"))
        backend_port, frontend_port = free_port(), free_port()
        while frontend_port == backend_port:
            frontend_port = free_port()
        api_url = f"http://127.0.0.1:{backend_port}"
        base_url = f"http://127.0.0.1:{frontend_port}"
        env = {**os.environ, "FFT_E2E_DB_PATH": str(Path(temp_dir) / "test.db"),
               "DB_PATH": str(Path(temp_dir) / "unused-default.db"),
               "VITE_API_PROXY_TARGET": api_url, "TZ": "Asia/Shanghai"}
        backend_log = stack.enter_context((OUTPUT / "backend.log").open("w"))
        frontend_log = stack.enter_context((OUTPUT / "frontend.log").open("w"))
        backend = subprocess.Popen(
            [str(python), "-m", "uvicorn", "e2e_server:create_test_app", "--factory",
             "--app-dir", str(ROOT / "scripts"), "--host", "127.0.0.1", "--port", str(backend_port)],
            cwd=ROOT, env=env, stdout=backend_log, stderr=subprocess.STDOUT,
        )
        stack.callback(stop, backend)
        ready(api_url + "/api/health", backend)
        frontend = subprocess.Popen(
            ["node", str(vite), "--host", "127.0.0.1", "--port", str(frontend_port), "--strictPort"],
            cwd=ROOT / "frontend", env=env, stdout=frontend_log, stderr=subprocess.STDOUT,
        )
        stack.callback(stop, frontend)
        ready(base_url, frontend)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="zh-CN", timezone_id="Asia/Shanghai")
                # Freeze Date only; browser timers and animation remain functional.
                context.add_init_script("""{ const OriginalDate = Date; const fixed = new OriginalDate('2026-11-18T12:00:00+08:00').getTime(); window.Date = class extends OriginalDate { constructor(...args) { super(...(args.length ? args : [fixed])); } static now() { return fixed; } }; }""")
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
                try:
                    report = run_scenarios(page, context, base_url, OUTPUT)
                    assert not errors, f"Browser console errors: {errors}"
                except Exception:
                    page.screenshot(path=str(OUTPUT / "failure.png"), full_page=True)
                    (OUTPUT / "failure-dom.txt").write_text(page.locator("body").inner_text())
                    raise
                report["console_errors"] = errors
                (OUTPUT / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
                print(json.dumps(report, ensure_ascii=False, indent=2))
            finally:
                browser.close()


if __name__ == "__main__":
    main()
