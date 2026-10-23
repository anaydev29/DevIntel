from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://devintel:devintel@localhost:5432/devintel"
    github_token: str | None = None
    stackexchange_key: str | None = None
    # Google login (leave empty to run without accounts)
    google_client_id: str | None = None
    google_client_secret: str | None = None
    session_secret: str | None = None        # long random string; signs the login cookie
    public_base_url: str | None = None       # e.g. https://devintel.example.com (needed behind a proxy)
    cookie_secure: bool = False              # set true when served over HTTPS
    admin_emails: str | None = None          # comma-separated Google emails that become admins at login

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, v: str) -> str:
        """Hosted providers (Neon, Supabase) give 'postgresql://...' URLs; SQLAlchemy needs the driver name."""
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v


    @property
    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in (self.admin_emails or "").split(",") if e.strip()}


settings = Settings()
