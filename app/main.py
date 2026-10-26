from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ad_platform import AdPlatform, FakePlatform
from app.db import SessionLocal, engine, get_session
from app.models import Base, LaunchItem, LaunchJob, Template
from app.schemas import (
    LaunchAccepted,
    LaunchCreate,
    LaunchOut,
    TemplateCreate,
    TemplateOut,
)
from app.worker import run_job


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


@app.post(
    "/launches", response_model=LaunchAccepted, status_code=status.HTTP_202_ACCEPTED
)
def create_launch(
    body: LaunchCreate,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    platform: Annotated[AdPlatform, Depends(get_platform)],
) -> LaunchAccepted:
    if session.get(Template, body.template_id) is None:
        raise HTTPException(status_code=404, detail="Template not found")

    job = LaunchJob(template_id=body.template_id, count=body.count)
    session.add(job)
    # commit, а не flush: фоновая задача откроет другую сессию,
    # и она увидит job только после коммита.
    session.commit()

    background_tasks.add_task(run_in_background, job.id, platform)
    return LaunchAccepted(id=job.id)


@app.get("/launches/{job_id}", response_model=LaunchOut)
def get_launch_status(job_id: int, session: SessionDep) -> LaunchOut:
    job = session.get(LaunchJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    items = session.scalars(
        select(LaunchItem).where(LaunchItem.job_id == job_id).order_by(LaunchItem.index)
    ).all()

    return LaunchOut(id=job.id, status=job.status, count=job.count, items=items)


@app.post("/templates", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(body: TemplateCreate, session: SessionDep) -> Template:
    template = Template(name=body.name, settings=body.settings.model_dump())
    session.add(template)
    session.flush()
    return template
