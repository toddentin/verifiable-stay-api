# Verifiable Stay API

Two endpoints.

- POST /receipts — property system sends a stay, gets a signed receipt
- POST /verify — anyone checks that stamp

## Local

pip install -r requirements.txt
uvicorn main:app --reload

Open http://127.0.0.1:8000/docs

## Render

Build: pip install -r requirements.txt
Start: uvicorn main:app --host 0.0.0.0 --port $PORT

Free tier sleeps, and the signing key on disk can vanish on restart.
For a pilot, set STAY_KEY_PATH to a persistent disk.

This verifies the stamp, not that the guest slept there.
