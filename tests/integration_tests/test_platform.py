import pytest
from app.schemas import CampaignSettings
from app.platform import FakePlatform, PlatformError

@pytest.fixture
def settings() -> CampaignSettings:
    return CampaignSettings(name="x", budget=10, geo=["US"])

def test_returns_id(settings):
    platform = FakePlatform()
    campaign_id = platform.create_campaign(settings)   # вот он

    assert isinstance(campaign_id, str)
    assert campaign_id != ""
def test_ids_are_unique(settings):
    platform = FakePlatform()
    first = platform.create_campaign(settings)
    second = platform.create_campaign(settings)

    assert first != second

def test_always_fails_when_rate_is_one(settings):
    platform = FakePlatform()
    platform.create_campaign(settings)        # успех при 0.0

    platform.fail_rate = 1.0
    with pytest.raises(PlatformError):
        platform.create_campaign(settings)
def outcomes(platform, settings, n):
    result = []
    for _ in range(n):
        try:
            platform.create_campaign(settings)
            result.append(True)   # вызов прошёл
        except PlatformError:
            result.append(False)   # вызов упал
    return result
def test_seed_equal_fail(settings):
    a = FakePlatform(fail_rate=0.5, seed=42)
    b = FakePlatform(fail_rate=0.5, seed=42)
    assert outcomes(a, settings, 20) == outcomes(b, settings, 20)

def test_fail_rate_above_one_is_rejected():
    with pytest.raises(ValueError):
        FakePlatform(fail_rate=1.5)

def test_negative_delay_is_rejected():
    with pytest.raises(ValueError):
        FakePlatform(delay=-1)
def test_fail_rate_one_always_fails(settings):
    platform = FakePlatform(fail_rate=1.0)
    for _ in range(5):
        with pytest.raises(PlatformError):
            platform.create_campaign(settings)