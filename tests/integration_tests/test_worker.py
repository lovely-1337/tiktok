from unittest.mock import Mock

from sqlalchemy import select

from app.ad_platform import FakePlatform, AdPlatform, PlatformError
from app.models import ItemStatus, JobStatus, LaunchItem
from app.worker import run_job

from tests.conftest import FlakyPlatform

def no_sleep(_: float) -> None:
    pass

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

def test_succeeds_on_third_attempt(session, job):
    platform = FlakyPlatform(failures=2)
    sleeps = []

    run_job(session, job.id, platform, sleep=sleeps.append)

    items = session.scalars(
        select(LaunchItem).where(LaunchItem.job_id == job.id).order_by(LaunchItem.index)
    ).all()
    first = items[0]

    assert first.status == ItemStatus.CREATED
    assert first.attempts == 3          # две неудачи + успех
    assert first.error_message is None  # успех стёр старую ошибку
    assert sleeps == [1, 2]             # паузы только между попытками
    assert platform.calls == 5          # 3 вызова на первый item + по 1 на два остальных
    assert job.status == JobStatus.DONE

def test_gives_up_after_max_attempts(session, job):
    platform = FlakyPlatform(failures=100)
    sleeps = []

    run_job(session, job.id, platform, max_attempts=3, sleep=sleeps.append)

    items = session.scalars(select(LaunchItem).where(LaunchItem.job_id == job.id)).all()
    assert all(i.status == ItemStatus.FAILED for i in items)
    assert all(i.attempts == 3 for i in items)
    assert all(i.error_message for i in items)
    assert job.status == JobStatus.FAILED
    assert sleeps == [1, 2] * 3         # по две паузы на каждый из трёх items