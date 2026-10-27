from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator

from app.models import ItemStatus, JobStatus


class CampaignSettings(BaseModel):
    name: str
    budget: float = Field(gt=0)  # бюджет строго больше нуля
    geo: list[str] = Field(min_length=1)


class LaunchOutput(BaseModel):
    job_id: int
    status: str
    items_created: int
    items_failed: int


class ItemOutput(BaseModel):
    index: int
    status: str
    external_campaign_id: str | None = None
    error_message: str | None = None


class TemplateCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    settings: CampaignSettings


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class LaunchCreate(BaseModel):
    template_id: int
    count: int = Field(gt=0)


class LaunchCreate(BaseModel):
    template_id: int
    count: int = Field(gt=0)


class LaunchAccepted(BaseModel):
    id: int


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    index: int
    status: ItemStatus
    external_campaign_id: str | None
    error_message: str | None


class LaunchOut(BaseModel):
    id: int
    status: JobStatus
    count: int
    items: list[ItemOut]

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        # Иначе A@x.com и a@x.com станут двумя пользователями.
        return v.lower()

class UserOut(BaseModel):
    id: int
    email: str
