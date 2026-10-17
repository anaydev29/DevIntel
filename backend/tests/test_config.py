from app.config import Settings


def test_provider_urls_get_psycopg_driver():
    assert Settings(database_url="postgresql://u:p@host/db?sslmode=require").database_url == \
        "postgresql+psycopg://u:p@host/db?sslmode=require"
    assert Settings(database_url="postgres://u:p@host/db").database_url == "postgresql+psycopg://u:p@host/db"


def test_other_urls_untouched():
    assert Settings(database_url="sqlite:///./devintel.db").database_url == "sqlite:///./devintel.db"
    assert Settings(database_url="postgresql+psycopg://u:p@host/db").database_url == "postgresql+psycopg://u:p@host/db"
