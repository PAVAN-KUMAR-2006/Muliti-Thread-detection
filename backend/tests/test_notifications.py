import uuid
from app import models


def add_note(db, user_id, title, read=False):
    n = models.Notification(user_id=uuid.UUID(user_id), title=title, body="b", read=read)
    db.add(n); db.commit()
    return str(n.id)


def test_user_only_sees_own_notifications(client, make_user, db):
    ha, a = make_user("a@example.com"); hb, b = make_user("b@example.com")
    add_note(db, a, "for A"); add_note(db, b, "for B"); add_note(db, b, "for B too")
    ra = client.get("/api/notifications", headers=ha).json()
    assert [n["title"] for n in ra["items"]] == ["for A"]
    assert ra["unread_count"] == 1
    assert client.get("/api/notifications", headers=hb).json()["unread_count"] == 2


def test_cannot_mark_another_users_notification(client, make_user, db):
    ha, a = make_user("a@example.com"); hb, _ = make_user("b@example.com")
    nid = add_note(db, a, "for A")
    assert client.patch(f"/api/notifications/{nid}/read", headers=hb).status_code == 404
    assert client.get("/api/notifications", headers=ha).json()["unread_count"] == 1      # untouched
    r = client.patch(f"/api/notifications/{nid}/read", headers=ha)
    assert r.status_code == 200
    assert r.json()["read"] is True
    assert client.get("/api/notifications", headers=ha).json()["unread_count"] == 0


def test_read_all_only_affects_caller(client, make_user, db):
    ha, a = make_user("a@example.com"); hb, b = make_user("b@example.com")
    for t in ("1", "2"): add_note(db, a, t)
    add_note(db, b, "B1")
    assert client.post("/api/notifications/read-all", headers=ha).json() == {"updated": 2}
    assert client.get("/api/notifications", headers=ha).json()["unread_count"] == 0
    assert client.get("/api/notifications", headers=hb).json()["unread_count"] == 1
    assert client.get("/api/notifications?unread_only=true", headers=hb).json()["items"][0]["title"] == "B1"
