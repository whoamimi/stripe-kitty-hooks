# Stripe Kitty Hooks - SAAS Template

A centralized Stripe event listener and wallet-notification platform built with FastAPI Websockets, Google cloud run and Firebase Realtime Database. Worthy solutions it supports:

- Google Workspace
- Notion Integrations
- Reddit (Devit) Apps
- ... or other Standalone Apps

Supports Subscription plans and pay by tokens.

**Requirements**

- Firebase Authentication
- Firebase Realtime Database
- Stripe Account

**Stripe Websocket Core Services**

1. HTTP webhook endpoint to ingest Stripe events (the list you provided), and
2. WebSocket endpoint to notify the frontend of wallet updates in real time, and
3. HTTP callback/confirmation routes the frontend hits after redirects (success/cancel and “confirm session” patterns).

**To Start**

1. Copy and paste `.env.example` to `.env`
2. and run:

```bash
python -m stripe_payment.app.main
# or for FastAPI
uvicorn stripe_payment.app.main:app --reload
# or lazy start
PYTHONPATH=./stripe_payment uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**To Deploy on Google Cloud Run**

```bash
gcloud run deploy \
  --source . \
  --region australia-southeast1 \
  --allow-unauthenticated
```

**Reference**

- [Google Cloud Run Setup](https://docs.cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-fastapi-service#local-shell)