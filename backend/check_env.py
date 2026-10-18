"""Checks DATABASE_URL in .env WITHOUT printing your password."""
import re
from dotenv import dotenv_values

url = dotenv_values(".env").get("DATABASE_URL")
if url is None:
    print("DATABASE_URL is not in .env (or .env is not in this folder)")
else:
    masked = re.sub(r"(://[^:/]*:)(.*)(@[^@]*)$", r"\1****\3", url)
    print("value      :", repr(masked))
    print("length     :", len(url))
    print("'@' count  :", url.count("@"), "(should be exactly 1)")
    print("starts ok  :", url.startswith(("postgresql://", "postgres://", "postgresql+psycopg://", "sqlite")))
    print("has [ ]    :", "[" in url or "]" in url, "(should be False)")
    print("has spaces :", url != url.strip() or " " in url, "(should be False)")
    print("has quotes :", "'" in url or '"' in url, "(should be False)")