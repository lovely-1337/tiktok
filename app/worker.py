import time
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from typing import Callable

from app.ad_platform import AdPlatform, PlatformError
from app.models import ItemStatus, JobStatus, LaunchItem, LaunchJob, Template
from app.schemas import CampaignSettings


def run_job(session: Session, job_id: int, platform: AdPlatform, max_attempts: int = 3, sleep: Callable[[float], None] = time.sleep) -> None:

    job = session.get(LaunchJob, job_id)
    if job is None:
        raise ValueError(f"job {job_id} not found")

    job.status = JobStatus.RUNNING
    session.commit()

   
    session.execute(
        insert(LaunchItem)
        .values([{"job_id": job_id, "index": i} for i in range(job.count)])
        .on_conflict_do_nothing(index_elements=["job_id", "index"])
    )
    session.commit()

    template = session.get(Template, job.template_id)
    settings = CampaignSettings(**template.settings)

    item_ids = session.scalars(
        select(LaunchItem.id).where(LaunchItem.job_id == job_id).order_by(LaunchItem.index)
    ).all()

    for item_id in item_ids:
        item = session.scalars(
            select(LaunchItem)
            .where(LaunchItem.id == item_id, LaunchItem.status != ItemStatus.CREATED)
            .with_for_update(skip_locked=True)
        ).first()
        if item is None:
            continue  # уже создан или занят другим воркером

        for attempt in range(1, max_attempts + 1):
            item.attempts += 1
            try:
                campaign_id = platform.create_campaign(settings)
            except PlatformError as e:
                item.error_message = str(e)
                if attempt < max_attempts:
                    sleep(2 ** (attempt - 1))  # 1, 2, 4 секунды
                continue
            else:
                item.status = ItemStatus.CREATED
                item.external_campaign_id = campaign_id
                item.error_message = None
                break
        else:
            item.status = ItemStatus.FAILED

        session.commit()  # внутри цикла: снимает блокировку после каждого item

    statuses = session.scalars(
        select(LaunchItem.status).where(LaunchItem.job_id == job_id)
    ).all()
    job.status = (
        JobStatus.DONE
        if all(s == ItemStatus.CREATED for s in statuses)
        else JobStatus.FAILED
    )
    session.commit()
