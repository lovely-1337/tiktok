from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    jwt_secret_key: str
    database_url: str = "postgresql+psycopg://launcher:launcher@127.0.0.1:5434/launcher"
    test_database_url: str = "postgresql+psycopg://launcher:launcher@127.0.0.1:5434/launcher_test"


settings = Settings()