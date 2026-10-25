from unittest.mock import Mock

from sqlalchemy import select

from app.ad_platform import FakePlatform
from app.models import ItemStatus, JobStatus, LaunchItem
from app.worker import run_job


def test_all_items_created(session, job):
    platform = FakePlatform()
    run_job(session, job.id, platform)

    items = session.scalars(select(LaunchItem).where(LaunchItem.job_id == job.id)).all()
    assert len(items) == 3
    assert all(i.status == ItemStatus.CREATED for i in items)
    assert len({i.external_campaign_id for i in items}) == 3
    assert job.status == JobStatus.DONE


def test_platform_failure(session, job):
    platform = FakePlatform(fail_rate=1.0)  # 100% failure rate
    run_job(session, job.id, platform)

    items = session.scalars(select(LaunchItem).where(LaunchItem.job_id == job.id)).all()
    assert len(items) == 3
    assert all(i.status == ItemStatus.FAILED for i in items)
    assert job.status == JobStatus.FAILED
    assert all(i.error_message for i in items)


def test_job_with_existing_items(session, job):
    platform = FakePlatform()
    # Create an existing item for the job
    existing_item = LaunchItem(
        job_id=job.id,
        index=0,
        external_campaign_id="existing_campaign",
        status=ItemStatus.CREATED,
    )
    session.add(existing_item)
    session.commit()

    run_job(session, job.id, platform)

    items = session.scalars(select(LaunchItem).where(LaunchItem.job_id == job.id)).all()
    existing = next(i for i in items if i.index == 0)
    assert existing.external_campaign_id == "existing_campaign"
    assert len(items) == 3  # Total items should still be 3
    assert all(i.status == ItemStatus.CREATED for i in items)
    assert (
        len({i.external_campaign_id for i in items}) == 3
    )  # Ensure unique external_campaign_ids
    assert job.status == JobStatus.DONE


def test_second_run_does_not_recreate(session, job):
    platform = Mock(wraps=FakePlatform())
    run_job(session, job.id, platform)
    run_job(session, job.id, platform)

    assert platform.create_campaign.call_count == 3


def test_failed_items_are_retried(session, job):
    platform = FakePlatform(fail_rate=1.0)
    run_job(session, job.id, platform)

    platform.fail_rate = 0.0
    run_job(session, job.id, platform)

    items = session.scalars(select(LaunchItem).where(LaunchItem.job_id == job.id)).all()
    assert all(i.status == ItemStatus.CREATED for i in items)
    assert all(i.error_message is None for i in items)
    assert job.status == JobStatus.DONE
