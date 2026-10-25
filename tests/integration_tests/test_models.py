import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import ItemStatus, LaunchItem, LaunchJob, Template


def test_job_with_items_is_saved(session):
    template = Template(name="t", settings={"name": "x", "budget": 10, "geo": ["US"]})
    session.add(template)
    session.flush()

    job = LaunchJob(template_id=template.id, count=3)
    session.add(job)
    session.flush()

    session.add_all(LaunchItem(job_id=job.id, index=i) for i in range(3))
    session.flush()

    items = session.scalars(
        select(LaunchItem).where(LaunchItem.job_id == job.id).order_by(LaunchItem.index)
    ).all()

    assert len(items) == 3
    assert all(item.status == ItemStatus.PENDING for item in items)
    assert all(item.external_campaign_id is None for item in items)


def test_duplicate_index_is_rejected(session, job):
    session.add(LaunchItem(job_id=job.id, index=0))
    session.flush()

    session.add(LaunchItem(job_id=job.id, index=0))
    with pytest.raises(IntegrityError):
        session.flush()
