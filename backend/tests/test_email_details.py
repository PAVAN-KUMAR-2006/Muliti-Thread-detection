import uuid

from app import models


def test_email_scan_returns_sender_and_subject_without_body(
    client, make_user, add_scan, db
):
    headers, user_id = make_user("email-details@example.com")
    scan_id = add_scan(
        user_id, scan_type="email", summary="Routine scanner test"
    )
    db.add(
        models.EmailScan(
            scan_id=uuid.UUID(scan_id),
            sender="sender@example.com",
            subject="Routine scanner test",
            body_excerpt="PRIVATE EMAIL BODY MUST NOT BE RETURNED",
        )
    )
    db.commit()

    response = client.get(f"/api/history/{scan_id}", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["email_details"] == {
        "sender": "sender@example.com",
        "subject": "Routine scanner test",
    }
    assert "body_excerpt" not in response.text
    assert "PRIVATE EMAIL BODY MUST NOT BE RETURNED" not in response.text


def test_website_scan_has_no_email_details(client, make_user, add_scan):
    headers, user_id = make_user("website-details@example.com")
    scan_id = add_scan(user_id, scan_type="website")

    response = client.get(f"/api/history/{scan_id}", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["email_details"] is None


def test_email_scan_without_email_record_returns_null(
    client, make_user, add_scan
):
    headers, user_id = make_user("missing-email@example.com")
    scan_id = add_scan(user_id, scan_type="email")

    response = client.get(f"/api/history/{scan_id}", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["email_details"] is None


def test_other_user_cannot_read_email_details(
    client, make_user, add_scan, db
):
    owner_headers, owner_id = make_user("email-owner@example.com")
    other_headers, other_id = make_user("email-other@example.com")
    scan_id = add_scan(owner_id, scan_type="email")
    db.add(
        models.EmailScan(
            scan_id=uuid.UUID(scan_id),
            sender="private@example.com",
            subject="Private subject",
            body_excerpt="Private body",
        )
    )
    db.commit()

    response = client.get(
        f"/api/history/{scan_id}", headers=other_headers
    )

    assert response.status_code == 404
    assert "private@example.com" not in response.text
    assert "Private subject" not in response.text


def test_email_details_require_authentication(client, make_user, add_scan):
    _, user_id = make_user("email-auth@example.com")
    scan_id = add_scan(user_id, scan_type="email")

    response = client.get(f"/api/history/{scan_id}")

    assert response.status_code == 401


def test_history_list_format_remains_unchanged(
    client, make_user, add_scan, db
):
    headers, user_id = make_user("email-history@example.com")
    scan_id = add_scan(user_id, scan_type="email")
    db.add(
        models.EmailScan(
            scan_id=uuid.UUID(scan_id),
            sender="sender@example.com",
            subject="History test",
            body_excerpt="Private body",
        )
    )
    db.commit()

    response = client.get("/api/history", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1
    item = response.json()["items"][0]
    assert item["id"] == scan_id
    assert "email_details" not in item
