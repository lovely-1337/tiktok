from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://launcher:launcher@127.0.0.1:5434/launcher"


settings = Settings()