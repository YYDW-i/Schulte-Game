from fastapi import FastAPI, Request, Depends, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from datetime import timezone
from .db import Base, engine, get_db
from .models import User, SchulteRun
from .security import hash_password, verify_password
from .eval import schulte_level, training_tips

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Schulte 5x5 Web")
app.add_middleware(
    SessionMiddleware,
    secret_key="CHANGE_ME_TO_A_LONG_RANDOM_SECRET",  # 生产环境务必用环境变量
    same_site="lax",
    https_only=False,  # 上线 HTTPS 后改 True
)

import sys
from pathlib import Path
from fastapi.templating import Jinja2Templates

def templates_dir() -> Path:
    # PyInstaller 打包后：sys._MEIPASS 指向 bundle 目录（onedir 新版通常是 _internal）
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "app" / "templates"
    # 开发环境：app/main.py 所在目录就是 app/
    return Path(__file__).resolve().parent / "templates"

templates = Jinja2Templates(directory=str(templates_dir()))


def current_user(request: Request, db: Session) -> User | None:
    uid = request.session.get("user_id")
    if not uid:
        return None
    return db.get(User, uid)

def require_login(request: Request, db: Session) -> User:
    user = current_user(request, db)
    if not user:
        raise RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return user

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    return RedirectResponse("/dashboard" if user else "/login", status_code=303)

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None})

@app.post("/register")
def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    exists = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if exists:
        return templates.TemplateResponse("register.html", {"request": request, "error": "该邮箱已注册，请直接登录。"})
    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=303)

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if (not user) or (not verify_password(password, user.password_hash)):
        return templates.TemplateResponse("login.html", {"request": request, "error": "邮箱或密码错误。"})
    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=303)

@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # stats
    best = db.execute(
        select(func.min(SchulteRun.adjusted_seconds)).where(SchulteRun.user_id == user.id)
    ).scalar()

    avg = db.execute(
        select(func.avg(SchulteRun.adjusted_seconds)).where(SchulteRun.user_id == user.id)
    ).scalar()

    recent = db.execute(
        select(SchulteRun)
        .where(SchulteRun.user_id == user.id)
        .order_by(SchulteRun.created_at.desc())
        .limit(10)
    ).scalars().all()

    level = advice = None
    if avg is not None:
        level, advice = schulte_level(float(avg))

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "best": float(best) if best is not None else None,
            "avg": float(avg) if avg is not None else None,
            "level": level,
            "advice": advice,
            "recent": recent,
        },
    )

@app.get("/play", response_class=HTMLResponse)
def play(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("play.html", {"request": request, "user": user})

@app.post("/api/runs")
async def submit_run(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return JSONResponse({"detail": "Not logged in"}, status_code=401)

    payload = await request.json()
    elapsed = float(payload.get("elapsed_seconds", 0))
    errors = int(payload.get("errors", 0))
    grid_size = int(payload.get("grid_size", 5))

    # 实用做法：错误惩罚（你也可以改成 0 或者改成更严格）
    adjusted = elapsed + errors * 2.0

    run = SchulteRun(
        user_id=user.id,
        grid_size=grid_size,
        elapsed_seconds=elapsed,
        errors=errors,
        adjusted_seconds=adjusted,
    )
    db.add(run)
    db.commit()

    # 返回更新后的 stats
    best = db.execute(
        select(func.min(SchulteRun.adjusted_seconds)).where(SchulteRun.user_id == user.id)
    ).scalar()
    avg = db.execute(
        select(func.avg(SchulteRun.adjusted_seconds)).where(SchulteRun.user_id == user.id)
    ).scalar()

    level, advice = schulte_level(adjusted)

    return {
        "elapsed_seconds": elapsed,
        "errors": errors,
        "adjusted_seconds": adjusted,
        "level": level,
        "advice": advice,
        "tips": training_tips(),
        "best_adjusted": float(best) if best is not None else None,
        "avg_adjusted": float(avg) if avg is not None else None,
    }
def utciso(dt):
    # 兼容老数据：如果是 naive，就当作 UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    # 输出 ISO 8601；+00:00 和 Z 都是 UTC 的合法表示
    s = dt.isoformat()
    return s.replace("+00:00", "Z")

templates.env.filters["utciso"] = utciso