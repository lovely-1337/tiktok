import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.ad_platform import FakePlatform, AdPlatform, PlatformError
from app.config import settings
from app.main import app, get_platform, get_session
from app.models import Base, LaunchJob, Template


@pytest.fixture
def engine():
    engine = create_engine(settings.test_database_url, connect_args={"connect_timeout": 3})
    assert settings.test_database_url != settings.database_url, "tests must not use the main database"
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


@pytest.fixture
def client(engine, monkeypatch):
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_session():
        with TestSession() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_platform] = lambda: FakePlatform()
    monkeypatch.setattr("app.main.SessionLocal", TestSession)

    yield TestClient(app)

    app.dependency_overrides.clear()

class FlakyPlatform(AdPlatform):
    """Fails the first `failures` calls, then succeeds."""

    def __init__(self, failures: int):
        self.failures = failures
        self.calls = 0

    def create_campaign(self, settings) -> str:
        self.calls += 1
        if self.calls <= self.failures:
            raise PlatformError("temporary failure")
        return f"campaign-{self.calls}"
