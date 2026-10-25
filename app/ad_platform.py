import random
import time
import uuid
from abc import ABC, abstractmethod

from app.schemas import CampaignSettings


class PlatformError(Exception):
    """Base class for platform errors."""



class AdPlatform(ABC):
    @abstractmethod
    def create_campaign(self, settings: CampaignSettings) -> str:
        """Create a campaign and return its external id."""


class FakePlatform(AdPlatform):
    def __init__(
        self,
        name: str = "FakePlatform",
        fail_rate: float = 0.0,
        delay: float = 0.0,
        seed: int | None = None,
    ):
        if not 0.0 <= fail_rate <= 1.0:
            raise ValueError("fail_rate must be between 0 and 1")
        if delay < 0:
            raise ValueError("delay must be non-negative")

        self.name = name
        self.fail_rate = fail_rate
        self.delay = delay
        self._rng = random.Random(seed)

    def create_campaign(self, settings: CampaignSettings) -> str:
        time.sleep(self.delay)

        if self._rng.random() < self.fail_rate:
            raise PlatformError(f"{self.name}: failed to create campaign")

        return uuid.uuid4().hex
