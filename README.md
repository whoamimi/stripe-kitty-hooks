# Stripe Payment SAAS Template

To support multiple apps with Google Firebase stack.

**Requirements**

- Firebase Authentication
- Firebase Realtime Database
- Stripe Account & Meta data ready

**Stripe Websocket Services**

1.	HTTP webhook endpoint to ingest Stripe events (the list you provided), and
2.	WebSocket endpoint to notify the frontend of wallet updates in real time, and
3.	HTTP callback/confirmation routes the frontend hits after redirects (success/cancel and “confirm session” patterns).

**To Start**

```bash
python -m stripe_payment.app.main
# or for FastAPI
uvicorn stripe_payment.app.main:app --reload
# or lazy start
PYTHONPATH=./stripe_payment uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Reference**

https://docs.cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-fastapi-service#local-shell

https://github.com/mazzasaverio/fastapi-cloudrun-starter/tree/master
