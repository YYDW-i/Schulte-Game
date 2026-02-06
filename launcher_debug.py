import os
import sys
import time
import threading
import importlib
import socket
import traceback
from pathlib import Path

import uvicorn
import webbrowser


def base_dir() -> Path:
    # exe 运行：exe 所在目录；源码运行：当前文件所在目录
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def log(msg: str):
    p = base_dir() / "SchulteGame.log"
    with p.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def wait_port(host: str, port: int, timeout: float = 15.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def load_app():
    base = base_dir()
    app_src = base / "app_src"
    if not app_src.exists():
        raise FileNotFoundError(f"未找到 app_src（必须与 exe 同级）：{app_src}")

    # 让 import app.main 从 app_src 里加载
    sys.path.insert(0, str(app_src))
    mod = importlib.import_module("app.main")
    return getattr(mod, "app")


def run_server():
    try:
        app = load_app()
        log("[OK] app loaded, starting uvicorn...")
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
        log("[WARN] uvicorn returned (server stopped).")
    except Exception:
        log("[ERR] server crashed:")
        log(traceback.format_exc())


if __name__ == "__main__":
    # ✅ 强制把工作目录切到 exe 所在目录（很多相对路径坑都靠这一下解决）
    os.chdir(base_dir())

    log("========== START ==========")
    log(f"base_dir={base_dir()}")
    log(f"cwd={Path.cwd()}")

    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    if wait_port("127.0.0.1", 8000, timeout=15):
        log("[OK] port 8000 is listening, opening browser.")
        webbrowser.open("http://127.0.0.1:8000/login")
        t.join()
    else:
        log("[ERR] port 8000 not listening after 15s. Check crash above / dependencies / app_src.")
