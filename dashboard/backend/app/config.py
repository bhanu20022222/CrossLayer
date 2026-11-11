from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CROSSLAYER_", extra="ignore")

    prometheus_url: str = "http://127.0.0.1:9091"
    prometheus_timeout_seconds: float = 8.0
    workload_namespace: str = "crosslayer-workloads"
    experiment_target_url: str = "http://127.0.0.1:8082/work"
    kubeconfig: str | None = None
    kubernetes_disabled: bool = False
    auth_username: str | None = None
    auth_password: str | None = None
    auth_secret: str | None = None
    auth_cookie_secure: bool = False
    auth_session_max_age_seconds: int = Field(default=28800, ge=60, le=604800)


settings = Settings()
