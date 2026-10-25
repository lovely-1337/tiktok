import time
from sqlalchemy import select
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

    existing = set(
        session.scalars(select(LaunchItem.index).where(LaunchItem.job_id == job_id))
    )
    session.add_all(
        LaunchItem(job_id=job_id, index=i)
        for i in range(job.count)
        if i not in existing
    )
    session.commit()

    template = session.get(Template, job.template_id)
    settings = CampaignSettings(**template.settings)

    items = session.scalars(
        select(LaunchItem).where(LaunchItem.job_id == job_id).order_by(LaunchItem.index)
    ).all()

    for item in items:
        if item.status == ItemStatus.CREATED:
            continue
        for attempt in range(1, max_attempts + 1):
            item.attempts += 1
            try:
                campaign_id = platform.create_campaign(settings)
            except PlatformError as e:
                item.error_message = str(e)
                if attempt < max_attempts:
                    sleep(2 ** (attempt - 1))   # 1, 2, 4 секунды
                continue                 # следующая попытка
            else:
                item.status = ItemStatus.CREATED
                item.external_campaign_id = campaign_id
                item.error_message = None
                break
        else:
            item.status = ItemStatus.FAILED
    session.commit()

    all_created = all(i.status == ItemStatus.CREATED for i in items)
    job.status = JobStatus.DONE if all_created else JobStatus.FAILED

    session.commit()
