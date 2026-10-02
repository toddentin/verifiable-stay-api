"""Verifiable Stay API: create a signed receipt, verify it.

Run locally:
  pip install -r requirements.txt
  uvicorn main:app --reload

Render start command:
  uvicorn main:app --host 0.0.0.0 --port $PORT
"""

import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

KEY_PATH = Path(os.environ.get("STAY_KEY_PATH", "property_key.pem"))
DEMO_AMOUNT = "487.00"

app = FastAPI(title="Verifiable Stay", version="0.1.0")


def load_or_create_key() -> Ed25519PrivateKey:
    if KEY_PATH.exists():
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        return load_pem_private_key(KEY_PATH.read_bytes(), password=None)
    key = Ed25519PrivateKey.generate()
    KEY_PATH.write_bytes(
        key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    )
    return key


PRIVATE = load_or_create_key()
PUBLIC = PRIVATE.public_key()
PUBLIC_B64 = base64.b64encode(
    PUBLIC.public_bytes(Encoding.Raw, PublicFormat.Raw)
).decode()


class StayIn(BaseModel):
    property: str = Field(examples=["The Oak and Harbor Inn"])
    guest: str = Field(examples=["Taylor Morgan"])
    check_in: str = Field(examples=["2026-09-12"])
    check_out: str = Field(examples=["2026-09-15"])
    amount: str = Field(examples=["487.00"])
    confirmation: str = Field(examples=["STAY-8F2K"])


class Receipt(BaseModel):
    payload: dict
    signature: str
    public_key: str
    verify_url: str


class VerifyIn(BaseModel):
    payload: dict
    signature: str
    public_key: str


def canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


@app.get("/")
def home():
    return {
        "service": "Verifiable Stay",
        "create": "POST /receipts",
        "verify": "POST /verify",
        "page": "/verify",
        "docs": "/docs",
    }


@app.post("/receipts", response_model=Receipt)
def create_receipt(stay: StayIn):
    payload = {
        "property": stay.property,
        "guest": stay.guest,
        "check_in": stay.check_in,
        "check_out": stay.check_out,
        "amount": stay.amount,
        "confirmation": stay.confirmation,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    signature = base64.b64encode(PRIVATE.sign(canonical(payload))).decode()
    return Receipt(
        payload=payload,
        signature=signature,
        public_key=PUBLIC_B64,
        verify_url="/verify",
    )


@app.post("/verify")
def verify_receipt(item: VerifyIn):
    try:
        raw_key = base64.b64decode(item.public_key)
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        key = Ed25519PublicKey.from_public_bytes(raw_key)
        key.verify(base64.b64decode(item.signature), canonical(item.payload))
        valid = True
        reason = "signature matches"
    except Exception:
        valid = False
        reason = "signature does not match the receipt"
    return {"valid": valid, "reason": reason, "payload": item.payload}


@app.get("/verify", response_class=HTMLResponse)
def verify_page():
    return """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Verify</title>
<style>body{font-family:sans-serif;max-width:640px;margin:40px auto;padding:0 16px}
label{display:block;margin-top:10px;font-size:13px;color:#555}input{width:100%;padding:8px}</style>
</head><body>
<h1>Verify a stay</h1>
<p>Paste the signed receipt JSON from POST /receipts.</p>
<textarea id="box" style="width:100%;height:140px"></textarea>
<p><button onclick="go()">Verify</button></p>
<pre id="out"></pre>
<script>
async function go(){
  const body = document.getElementById('box').value;
  const res = await fetch('/verify', {method:'POST', headers:{'Content-Type':'application/json'}, body});
  document.getElementById('out').textContent = await res.text();
}
</script></body></html>"""


@app.get("/health")
def health():
    return {"ok": True, "public_key": PUBLIC_B64}
