"""List everyone who has signed in:   python -m app.list_users
Emails are personal data: keep this output private."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserBan


def fetch_users(db: Session) -> list[dict]:
    rows = db.execute(select(User, UserBan.id).outerjoin(UserBan, UserBan.user_id == User.id)
                      .order_by(User.created_at.desc())).all()
    return [{"id": u.id, "name": u.name or "", "email": u.email, "role": u.role, "banned": ban is not None,
             "joined": u.created_at, "last_login": u.last_login_at} for u, ban in rows]


if __name__ == "__main__":
    from app.database import SessionLocal

    with SessionLocal() as session:
        users = fetch_users(session)
    print(f"{len(users)} user(s)\n")
    print(f"{'id':>4}  {'name':22} {'email':32} {'role':10} {'banned':6} joined")
    for u in users:
        joined = u["joined"].strftime("%Y-%m-%d") if u["joined"] else ""
        print(f"{u['id']:>4}  {u['name'][:22]:22} {u['email'][:32]:32} {u['role']:10} {'yes' if u['banned'] else 'no':6} {joined}")
