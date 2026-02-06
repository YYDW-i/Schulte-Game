import threading
import time
import webbrowser

import uvicorn

# ✅ 关键：显式导入，让 PyInstaller 能看见依赖并打包进去
from app.main import app as fastapi_app


def run():
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(0.8)  # 等服务起来
    webbrowser.open("http://127.0.0.1:8000/login")
    t.join()
