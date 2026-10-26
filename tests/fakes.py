from app.ad_platform import AdPlatform, PlatformError
import threading
import time


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

class CountingPlatform(AdPlatform):
    def __init__(self, delay: float = 0.2):
        self.delay = delay
        self.calls = 0
        self._lock = threading.Lock()

    def create_campaign(self, settings) -> str:
        with self._lock:
            self.calls += 1
            n = self.calls
        time.sleep(self.delay)
        return f"campaign-{n}"