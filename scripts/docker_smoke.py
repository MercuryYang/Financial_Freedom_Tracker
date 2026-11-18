"""Verify built Compose images using an isolated project and disposable volume."""

import argparse
import json
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", action="store_true", help="Also run Chromium acceptance against the production frontend image, using fixed test rates.")
    options = parser.parse_args()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    project = f"fft-acceptance-{os.getpid()}"
    env = {**os.environ, "PORT": str(port), "BIND_ADDRESS": "127.0.0.1"}
    # Resolve the images from the actual project configuration, without hardcoding
    # the user's checkout directory or production project name.
    production = json.loads(subprocess.check_output(
        ["docker", "compose", "--project-directory", str(ROOT), "config", "--format", "json"],
        cwd=ROOT, env=env, text=True,
    ))
    default_project = production["name"]
    images = {service: config.get("image", f"{default_project}-{service}")
              for service, config in production["services"].items()}
    with tempfile.TemporaryDirectory(prefix="fft-docker-check-") as folder:
        override = Path(folder) / "images.json"
        services = {name: {"image": image} for name, image in images.items()}
        if options.browser:
            services["backend"].update({
                "environment": {"FFT_E2E_DB_PATH": "/data/fft.db"},
                "volumes": [f"{ROOT / 'scripts' / 'e2e_server.py'}:/test-tools/e2e_server.py:ro"],
                "command": ["python", "-m", "uvicorn", "e2e_server:create_test_app", "--factory", "--app-dir", "/test-tools", "--host", "0.0.0.0", "--port", "8000"],
            })
        override.write_text(json.dumps({"services": services}))
        command = ["docker", "compose", "--project-name", project, "--file", str(ROOT / "docker-compose.yml"), "--file", str(override)]

        def compose(*args):
            subprocess.run([*command, *args], cwd=ROOT, env=env, check=True, timeout=180)

        def request(path, method="GET", payload=None):
            body = json.dumps(payload).encode() if payload is not None else None
            with urlopen(Request(f"http://127.0.0.1:{port}{path}", data=body, method=method,
                                 headers={"Content-Type": "application/json"}), timeout=15) as response:
                data = response.read().decode()
                return json.loads(data) if "application/json" in response.headers.get("Content-Type", "") else data

        try:
            compose("up", "--detach", "--no-build", "--wait", "--wait-timeout", "90")
            assert request("/api/health")["status"] == "ok"
            assert "<html" in request("/").lower()
            assert "<html" in request("/investments").lower()
            assert "<html" in request("/assets").lower()
            if options.browser:
                from playwright.sync_api import sync_playwright
                from e2e_scenarios import run_scenarios
                browser_output = ROOT / "output" / "docker-e2e"
                browser_output.mkdir(parents=True, exist_ok=True)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    try:
                        context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="zh-CN", timezone_id="Asia/Shanghai")
                        context.add_init_script("""{ const OriginalDate = Date; const fixed = new OriginalDate('2026-11-18T12:00:00+08:00').getTime(); window.Date = class extends OriginalDate { constructor(...args) { super(...(args.length ? args : [fixed])); } static now() { return fixed; } }; }""")
                        page = context.new_page()
                        errors = []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
                        report = run_scenarios(page, context, f"http://127.0.0.1:{port}", browser_output)
                        assert not errors, errors
                        report["console_errors"] = errors
                        (browser_output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
                        print(f"Production browser checks: {report['passed']} passed", flush=True)
                    finally:
                        browser.close()
            baseline = request("/api/assets")["total_cny"]
            asset = request("/api/assets", "POST", {"name": "容器持久化验收", "category": "checking", "currency": "CNY", "balance": 12345.67})
            before = request("/api/assets")
            expected = round(baseline + 12345.67, 2)
            assert before["total_cny"] == expected, before
            compose("restart", "backend")
            deadline = time.monotonic() + 45
            while True:
                try:
                    assert request("/api/health")["status"] == "ok"
                    break
                except (OSError, AssertionError):
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(0.5)
            after = request("/api/assets")
            assert any(row["id"] == asset["id"] and row["balance"] == 12345.67 for row in after["accounts"])
            assert after["total_cny"] == expected, after
            history = request("/api/networth/history")
            assert len(history) == 1 and history[0]["total_cny"] == expected
            result = {"passed": True, "checks": ["Compose健康检查", "Nginx首页与SPA深链接", "API反向代理", "SQLite命名卷重启持久化", "净资产快照持久化"], "isolated_project": project}
            if options.browser:
                result["browser_checks"] = report["passed"]
            output = ROOT / "output"
            output.mkdir(exist_ok=True)
            (output / "docker-smoke.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
            print(json.dumps(result, ensure_ascii=False, indent=2))
        finally:
            # This project name is created above and never refers to the user's
            # daily application; remove only its disposable test volume.
            compose("down", "--volumes")


if __name__ == "__main__":
    main()
