from sqlalchemy import select
from app.worker import run_job
from app.models import LaunchItem, ItemStatus, JobStatus
from app.platform import FakePlatform

def test_all_items_created(session, job):
    platform = FakePlatform()
    run_job(session, job.id, platform)

    items = session.scalars(select(LaunchItem).where(LaunchItem.job_id == job.id)).all()
    assert len(items) == 3
    assert all(i.status == ItemStatus.CREATED for i in items)
    assert len({i.external_campaign_id for i in items}) == 3
    assert job.status == JobStatus.DONE