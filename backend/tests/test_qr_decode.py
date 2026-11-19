"""QR decoding tests use real QR images generated with the `qrcode` package (a dev dependency)."""
import io
import socket
import pytest
import qrcode
from fastapi import HTTPException
from PIL import Image
from app import models
from app.ml import service
from app.routes_upload import decode_qr

TEXT = "https://example.com"


def make(text=TEXT, box=10, border=4, ec=qrcode.constants.ERROR_CORRECT_M, back="white", mode="RGB"):
    q = qrcode.QRCode(error_correction=ec, box_size=box, border=border); q.add_data(text); q.make(fit=True)
    return q.make_image(fill_color="black", back_color=back).convert(mode)


def encode(im, fmt="PNG", **kw):
    b = io.BytesIO(); im.save(b, fmt, **kw); return b.getvalue()


def transparent():
    im = make().convert("RGBA")
    im.putdata([(0, 0, 0, 0) if p[:3] == (255, 255, 255) else p for p in im.getdata()])
    return encode(im)


def on_big_page():
    page = Image.new("RGB", (1200, 1200), "white"); page.paste(make(box=4), (500, 500)); return encode(page)


def inverted():
    from PIL import ImageOps
    return encode(ImageOps.invert(make()))


CASES = {f"box{b}-border{br}": (lambda b=b, br=br: encode(make(box=b, border=br))) for b in (2, 4, 10, 20) for br in (0, 1, 2, 4)}
CASES.update({
    "tiny-1px-modules": lambda: encode(make(box=1, border=4)),
    "tiny-1px-modules-no-margin": lambda: encode(make(box=1, border=0)),
    "transparent-background": transparent, "grayscale": lambda: encode(make(mode="L")),
    "small-code-on-large-page": on_big_page, "jpeg-q70": lambda: encode(make(), "JPEG", quality=70),
    "webp": lambda: encode(make(), "WEBP"), "high-error-correction": lambda: encode(make(ec=qrcode.constants.ERROR_CORRECT_H)),
    "inverted-light-on-dark": inverted,
})


@pytest.mark.parametrize("name", list(CASES))
def test_decodes_ordinary_qr_images(name):
    assert decode_qr(CASES[name]()) == TEXT


def test_blank_and_noise_images_return_none():
    assert decode_qr(encode(Image.new("RGB", (300, 300), "white"))) is None
    import os
    assert decode_qr(encode(Image.frombytes("L", (200, 200), os.urandom(200 * 200)))) is None


def test_wrong_type_and_unreadable_images():
    with pytest.raises(HTTPException) as e: decode_qr(b"GIF89a" + b"\x00" * 50)
    assert e.value.status_code == 415
    with pytest.raises(HTTPException) as e: decode_qr(b"\x89PNG" + b"not really a png")
    assert e.value.status_code == 422


# ---------- through the API ----------
def upload(client, headers, data, name="qr.png", mime="image/png"):
    return client.post("/api/scan/qr", files={"file": (name, data, mime)}, headers=headers)


def test_upload_of_plain_text_qr_is_shown_but_not_scored(client, make_user, db):
    h, _ = make_user("a@example.com")
    r = upload(client, h, encode(make("just some text")))
    assert r.status_code == 200, r.text
    d = r.json()["details"]
    assert d["decoded"] == "just some text" and d["is_url"] is False
    assert db.query(models.QrScan).count() == 1


def test_upload_with_no_qr_gives_a_clear_error(client, make_user):
    h, _ = make_user("a@example.com")
    r = upload(client, h, encode(Image.new("RGB", (300, 300), "white")))
    assert r.status_code == 422 and "No readable QR code" in r.json()["detail"]


def test_upload_requires_authentication(client):
    assert upload(client, {}, encode(make())).status_code == 401


def test_url_qr_is_analysed_and_the_url_is_never_opened(client, make_user, db, monkeypatch):
    """Prediction is stubbed, so this checks the flow, not model accuracy. Any network connection attempt fails the test."""
    monkeypatch.setattr(service, "predict_url", lambda url: (0.02, [("HTTPS used: 0", -0.1)]))
    monkeypatch.setattr(service, "bundle", lambda name: {"meta": {"version": "test"}})
    def no_network(*a, **k): raise AssertionError("a network connection was attempted")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    h, uid = make_user("a@example.com")
    r = upload(client, h, CASES["box10-border4"]())
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["details"]["decoded"] == TEXT and d["details"]["is_url"] is True and d["scan_type"] == "qr"
    assert db.query(models.QrScan).count() == 1


def test_qr_text_endpoint_for_camera_results(client, make_user):
    h, _ = make_user("a@example.com")
    r = client.post("/api/scan/qr-text", json={"content": "WIFI:T:WPA;S:cafe;P:secret;;"}, headers=h)
    assert r.status_code == 200 and r.json()["details"]["is_url"] is False
