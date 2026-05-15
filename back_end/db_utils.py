from datetime import datetime
#-------------------
from database import SessionLocal
from models import GuestSession, PlayerState


def cleanup_expired_guests():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        expired = db.query(GuestSession).filter(GuestSession.expire_at < now).all()
        for sess in expired:
            db.query(PlayerState).filter_by(player_id=sess.guest_id).delete()
            db.delete(sess)
        db.commit()
        if expired:
            print(f"[cleanup] Removed {len(expired)} expired guest session(s)")
    finally:
        db.close()
