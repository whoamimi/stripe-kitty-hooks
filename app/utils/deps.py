# app/utils/deps.py
# Route Exception & Dependency utilities for the Stripe Payment application

import stripe
from uuid import UUID
from fastapi import HTTPException, Request, Depends
from typing import Annotated
from firebase_admin import auth
from firebase_admin._user_mgt import UserRecord

from ..utils.setup import platform
from ..src.schema import StripeFirebaseRequest
from ..src.crud import (
    STRIPE_SIGNATURE,
    FIREBASE_AUTH_SIGNATURE,
    setup_firebase,
    get_user_profile,
)

async def verify_signature(request: Request):
    """ Verify Stripe webhook signature from request headers. """

    if sig_header := request.headers.get(STRIPE_SIGNATURE, None):
        event = stripe.Webhook.construct_event(
            payload=await request.body(),
            sig_header=sig_header,
            secret=platform.account.webhook_secret
        )

        if not event:
            raise stripe.SignatureVerificationError("Invalid Stripe webhook signature.", sig_header=sig_header)

        return event

async def verify_member_profile(user_auth_token: str | UUID):
    """ Verify Firebase user authentication and retrieve user profile. """

    # Verify user_id from request context or headers
    # Member user should have account in
    #   - Firebase Authentication
    #   - Firebase Realtime Database under:
    #           - /profiles/{user_id}/*
    #           - /accounts/{user_id}/tokenBalance/*
    #           - /transactions/{user_id}/{timestamp}/*
    try:
        setup_firebase()
        user: UserRecord = auth.get_user(str(user_auth_token))
        profile = await get_user_profile(user)
        return user, profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System error. Invalid userType configuration. {str(e)}")

async def verify_headers(request: Request):
    # Main verification dependency to be used in webhook routes
    sig_key = request.headers.get(STRIPE_SIGNATURE, None)
    auth_key = request.headers.get(FIREBASE_AUTH_SIGNATURE, None)

    try:
        if sig_key is None or auth_key is None:
            if not sig_key:
                raise stripe.SignatureVerificationError (f"Missing Stripe signature header. Please add {STRIPE_SIGNATURE} to header.", sig_header=None)

            if not auth_key:
                raise RuntimeError(f"Missing Firebase auth header. Please add {FIREBASE_AUTH_SIGNATURE} to header.")

        stripe_event = await verify_signature(request)
        user_auth, user_profile = await verify_member_profile(auth_key)

        if stripe_event and user_auth:
            return StripeFirebaseRequest(
                event=stripe_event,
                user=user_profile,
                auth=user_auth
            )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Header verification failed: {str(e)}")

StripeFirebaseAuthorize = Annotated[
    StripeFirebaseRequest, Depends(verify_headers)]
