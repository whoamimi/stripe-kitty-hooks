# app/src/crud.py

from uuid import UUID
import firebase_admin
from pathlib import Path
from fastapi import Depends
from typing import Annotated
from firebase_admin import credentials, db
from firebase_admin._user_mgt import UserRecord

from .schema import UserProfile
from ..utils.setup import platform

STRIPE_SIGNATURE = "stripe-signature"
FIREBASE_AUTH_SIGNATURE = "x-firebase-user-auth"
CHECKOUT_LINKS = ("checkout.session.completed", "checkout.session.async_payment_succeeded","invoice.payment_succeeded")

class RecordPaths:
    PROFILES = "profiles"
    ACCOUNTS = "accounts"
    TRANSACTIONS = "transactions"
    TIMELINE = "timeline"

# setup firebase admin sdk
def setup_firebase(
    service_account_path: Path = platform.database._service_account_path,
    database_url: str = platform.database.url,
):
    try:

        if not firebase_admin._apps:
            file_path = str(service_account_path)
            cred = credentials.Certificate(file_path)
            firebase_admin.initialize_app(cred, {"databaseUrl": database_url})

    except Exception:
        raise RuntimeError(
            "Failed to initialize Firebase Admin SDK. Ensure to configure "
            "Service Account file path configs/_secrets/serviceAccount.json and"
            "refer to Google Firebase setup."
        )

# User Profiling Operations
async def _migrate_auth_to_db(user: UserRecord, profile: dict):
    """Migrate Firebase Authentication user to Realtime Database profile."""

    final = {}
    # update with user authentication account
    final.update(**{
        "id": user.uid,
        "userType": "member",
        "email": user.email,
        "displayName": user.display_name,
        "createdAt": user.user_metadata.creation_timestamp or 0,
        "provider_ids": [p.provider_id for p in user.provider_data],
        "tenant_id": user.tenant_id,
    })
    final["meta"] = {
        "provider_ids": [p.provider_id for p in user.provider_data],
        "tenant_id": user.tenant_id
    }

    # migrate all timelines datasets over to new google account id
    old_id = profile.get("id", None)
    if old_id and old_id != user.uid:
        # find old timeline records and migrate to new user id
        old_id_ref = db.reference(f"/timeline/{old_id}").get()

        if old_id_ref:
            # copy old sessions to new user id
            new_ref = db.reference(f"/timeline/{user.uid}")
            new_ref.update(old_id_ref)
            # delete old record
            db.reference(f"/timeline/{old_id}").delete()

    # update with any other profile fields that exist
    final.update(**{k: v for k, v in profile.items() if k not in final and v})
    # update final profile record and store in database
    final_ref = db.reference(f"/users/{user.uid}")
    # validate final profile structure
    new_profile = UserProfile(**final)
    final_ref.set(new_profile.model_dump_json())
    return new_profile

async def create_new_profile(user: UserRecord):
    """Create a new user profile in Firebase Realtime Database. Note: It is expected that any new user profile returned from this function should be of member userType. Otherwise, anonymous users should not reach this code path as an error will be raised."""
    # Placeholder for creating a new user profile logic

    if not user.provider_data:
        raise RuntimeError(f"Cannot create profile for anonymous user without provider data. User ID: {user.uid} and Email: {user.email}. Please manually upgrade anonymous user to member account via frontend authentication flow or resolve via Firebase Console.")

    ref = db.reference(f"/profiles/{user.uid}")
    new_profile = UserProfile(
        id=str(user.uid),
        userType="member",
        displayName=user.display_name,
        createdAt=user.user_metadata.creation_timestamp or 0,
        email=user.email,

    )

    ref.set(new_profile.model_dump_json())
    return new_profile

async def get_user_profile(user):
    """Fetch user profile from Firebase Realtime Database."""

    user_id = user.uid
    ref = db.reference(f"/profiles/{user_id}")
    profile_data = ref.get()

    if not isinstance(profile_data, dict) or not profile_data:
        # If no profile found, this is a new user or has previously upgraded from anonymous without profile reading migration setup.
        print("No user profile found. May be a new user.")
        return await create_new_profile(user)
    else:

        userType = profile_data.get("userType", "guest")

        if userType == "anon" or userType == "guest":
            print(f"Attempting to migrate authenticated user to Realtime Database profile.Alternatively, please factory reset frontend data collections as member account is configured as non-member userType.({profile_data.get('userType')}).")
            return await _migrate_auth_to_db(user, profile_data)

        return UserProfile(**profile_data)

# Stripe Transaction Records
async def store_transaction_record(record: dict, user_id: str | UUID):
    """Store a transaction record in Firebase Realtime Database."""

    timestamp = record.get("timestamp")

    if not user_id or not timestamp:
        raise ValueError("Transaction record must contain 'user_id' and 'timestamp' fields.")

    ref = db.reference(f"{RecordPaths.TRANSACTIONS}/{str(user_id)}/{timestamp}")
    ref.set(record)

# User Account Operations Handlers
async def update_user_token_balance(user_id: str | UUID, amount: float):
    """Update user's token balance in Firebase Realtime Database."""

    account_ref = db.reference(f"{RecordPaths.ACCOUNTS}/{str(user_id)}/tokenBalance")
    current_balance = account_ref.get()
    curr = current_balance if isinstance(current_balance, (int, float)) else 0.0
    new_balance = curr + amount
    account_ref.set(new_balance)

    return new_balance
