from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.auth.dependencies import get_optional_current_user
from app.recipes import router as recipes_router
from app.saved_recipes import router as saved_recipes_router
from app.users import router as users_router
from app.pantry import router as pantry_router
from app.shopping import router as shopping_router
from app.planner import router as planner_router
from app.api.ai import router as ai_router
from app.api.camera import router as camera_router
from app.api.auth import router as auth_router


BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="SavorAI API")

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

templates = Jinja2Templates(
    directory=BASE_DIR / "templates",
)

app.include_router(recipes_router)
app.include_router(saved_recipes_router)
app.include_router(users_router)
app.include_router(pantry_router)
app.include_router(shopping_router)
app.include_router(planner_router)
app.include_router(ai_router)
app.include_router(camera_router)
app.include_router(auth_router)


@app.get("/")
def home(
    current_user=Depends(get_optional_current_user),
):
    if current_user:
        return RedirectResponse("/app", status_code=303)

    return RedirectResponse("/login", status_code=303)


@app.get("/login")
def login_page(
    request: Request,
    current_user=Depends(get_optional_current_user),
):
    if current_user:
        return RedirectResponse("/app", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="auth.html",
    )


@app.get("/app")
def app_page(
    request: Request,
    current_user=Depends(get_optional_current_user),
):
    if not current_user:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.get("/health")
def health():
    return {"status": "healthy"}