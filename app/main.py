from contextlib import asynccontextmanager
from typing import Annotated
from datetime import datetime, timedelta, timezone
import secrets


from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.ad_platform import AdPlatform, FakePlatform
from app.db import SessionLocal, engine, get_session
from app.models import Base, LaunchItem, LaunchJob, Template, User, TikTokOAuthState
from app.schemas import (
    LaunchAccepted,
    LaunchCreate,
    LaunchOut,
    TemplateCreate,
    TemplateOut,
    UserCreate,
    UserOut,
    UserLogin,
    TokenOut
)
from app.worker import run_job
from app.security import hash_password, verify_password
from app.auth import create_access_token, get_current_user

def get_platform() -> AdPlatform:
    # Отдельная функция для Depends: в тестах подменяется через dependency_overrides.
    return FakePlatform()


def run_in_background(job_id: int, platform: AdPlatform) -> None:
    # Своя сессия: сессия запроса к этому моменту уже закрыта.
    with SessionLocal() as session:
        run_job(session, job_id, platform)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Campaign Launcher", lifespan=lifespan)


SessionDep = Annotated[Session, Depends(get_session)]



@app.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, session: SessionDep) -> User:
    user = User(email=body.email, password_hash=hash_password(body.password))
    session.add(user)
    try:
        session.flush()  # здесь срабатывает unique по email
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    return user

@app.post("/login", response_model=TokenOut)
def login(body: UserLogin, session: SessionDep) -> User:
    user = session.scalar(
    select(User).where(User.email == str(body.email).lower())
)

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    return TokenOut(access_token=create_access_token(user.id))

@app.get("/users/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user

@app.post(
    "/launches", response_model=LaunchAccepted, status_code=status.HTTP_202_ACCEPTED
)
def create_launch(
    body: LaunchCreate,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    platform: Annotated[AdPlatform, Depends(get_platform)],
    current_user: User = Depends(get_current_user),
) -> LaunchAccepted:
    template = session.scalar(
        select(Template).where(
            Template.id == body.template_id,
            Template.user_id == current_user.id,
        )
    )

    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    job = LaunchJob(template_id=body.template_id, count=body.count)
    session.add(job)
    # commit, а не flush: фоновая задача откроет другую сессию,
    # и она увидит job только после коммита.
    session.commit()

    background_tasks.add_task(run_in_background, job.id, platform)
    return LaunchAccepted(id=job.id)


@app.get("/launches/{job_id}", response_model=LaunchOut, )
def get_launch_status(job_id: int, session: SessionDep,
    current_user: User = Depends(get_current_user),) -> LaunchOut:
    job = session.scalar(
        select(LaunchJob)
        .join(Template, LaunchJob.template_id == Template.id)
        .where(
            LaunchJob.id == job_id,
            Template.user_id == current_user.id,
        )
    )

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    items = session.scalars(
        select(LaunchItem).where(LaunchItem.job_id == job_id).order_by(LaunchItem.index)
    ).all()

    return LaunchOut(id=job.id, status=job.status, count=job.count, items=items)


@app.post("/templates", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(body: TemplateCreate, session: SessionDep, current_user: User = Depends(get_current_user),) -> Template:
    template = Template(user_id=current_user.id, name=body.name, settings=body.settings.model_dump())
    session.add(template)
    session.flush()
    return template

@app.get("/auth/tiktok/start")
def start(session: SessionDep, current_user: User = Depends(get_current_user)):
    state_value = secrets.token_urlsafe(32)

    oauth_state = TikTokOAuthState(
    user_id = current_user.id,
    state=state_value,
    expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    session.add(oauth_state)
    session.commit()
    return {"state": state_value}
@app.get("/auth/tiktok/callback")
def callback(session: SessionDep, state: str, auth_code: str):
    oauth_state = session.scalar(
    select(TikTokOAuthState).where(TikTokOAuthState.state == state)
)

    if oauth_state is None:
        raise HTTPException(status_code=400, detail="Invalid state")

    if oauth_state.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Expired state")
    session.delete(oauth_state)
    session.commit()
    return {"status": "state_valid"}