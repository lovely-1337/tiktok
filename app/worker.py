from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LaunchItem, ItemStatus, JobStatus, Template, LaunchJob
from app.schemas import CampaignSettings
from app.ad_platform import AdPlatform, PlatformError


def run_job(session: Session, job_id: int, platform: AdPlatform) -> None:
    
    
    job = session.get(LaunchJob, job_id)
    if job is None:
        raise ValueError(f"job {job_id} not found")

    job.status = JobStatus.RUNNING
    session.commit()
   
    existing = set(session.scalars(
        select(LaunchItem.index).where(LaunchItem.job_id == job_id)
    ))
    session.add_all(
        LaunchItem(job_id=job_id, index=i)
        for i in range(job.count) if i not in existing
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
        try:
            campaign_id = platform.create_campaign(settings)
            item.status = ItemStatus.CREATED
            item.error_message = None
            item.external_campaign_id = campaign_id
        except PlatformError as e:
            item.status = ItemStatus.FAILED
            item.error_message = str(e)
        session.commit()

    all_created = all(i.status == ItemStatus.CREATED for i in items)
    job.status = JobStatus.DONE if all_created else JobStatus.FAILED
    

    session.commit()