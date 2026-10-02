"""Test Verifiable Stay create and verify.

Start the API first:
  uvicorn main:app --reload

Then:
  python test_api.py
  python test_api.py http://127.0.0.1:8000
"""

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def post(path, body):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return res.status, json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def main():
    stay = {
        "property": "The Oak and Harbor Inn",
        "guest": "Taylor Morgan",
        "check_in": "2026-09-12",
        "check_out": "2026-09-15",
        "amount": "487.00",
        "confirmation": "STAY-8F2K",
    }

    print("CREATE", BASE + "/receipts")
    status, created = post("/receipts", stay)
    print(status, json.dumps(created, indent=2))
    if status != 200:
        print("Create failed. Is the API running?")
        sys.exit(1)

    print("\nVERIFY good receipt")
    status, good = post("/verify", {
        "payload": created["payload"],
        "signature": created["signature"],
        "public_key": created["public_key"],
    })
    print(status, json.dumps(good, indent=2))
    if not good.get("valid"):
        print("Expected valid. Fail.")
        sys.exit(1)

    print("\nVERIFY altered amount")
    tampered = dict(created["payload"])
    tampered["amount"] = "999.00"
    status, bad = post("/verify", {
        "payload": tampered,
        "signature": created["signature"],
        "public_key": created["public_key"],
    })
    print(status, json.dumps(bad, indent=2))
    if bad.get("valid"):
        print("Expected invalid. Fail.")
        sys.exit(1)

    print("\nOK. Create works. Good receipt verifies. Changed amount fails.")


if __name__ == "__main__":
    main()
