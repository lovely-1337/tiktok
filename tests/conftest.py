import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Base, LaunchJob, Template


@pytest.fixture
def engine():
    engine = create_engine(settings.database_url, connect_args={"connect_timeout": 3})
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session

@pytest.fixture
def job(session):
    template = Template(
        name="t",
        settings={"name": "x", "budget": 10, "geo": ["US"]},
    )
    session.add(template)
    session.flush()

    job = LaunchJob(template_id=template.id, count=3)
    session.add(job)
    session.flush()
    return job