def cleanup_expired_guests(db):
    now = datetime.utcnow()

    expired_sessions = (
        db.query(GuestSession)
        .filter(GuestSession.expire_at < now)
        .all()
    )

    for sess in expired_sessions:
        # delete player state
        db.query(PlayerState).filter_by(player_id=sess.guest_id).delete()

        # delete session
        db.delete(sess)

    db.commit()