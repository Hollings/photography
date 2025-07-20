from typing import Iterator
from sqlalchemy.orm import Session

from database import SessionLocal

def get_db() -> Iterator[Session]:
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
