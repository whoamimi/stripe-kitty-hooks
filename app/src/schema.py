# app/src/schema.py

from uuid import UUID
from pydantic import BaseModel
from stripe._event import Event
from firebase_admin._user_mgt import UserRecord

from datetime import datetime
from typing import Any, Literal, Optional, Dict, Union
from pydantic import Field, EmailStr

# Firebase Related Schemas Records
class UserProfile(BaseModel):
    id: UUID | str
    displayName: str | None
    # account management
    userType: Literal["member", "guest", "anon"]
    createdAt: Union[datetime, int]
    updatedAt: Optional[Union[datetime, int]] = None
    lastLogin: Optional[Union[datetime, int]] = None
    # general info
    email: Optional[EmailStr] = None
    birthDate: Optional[str] = None
    birthTime: Optional[str] = None
    birthPlace: Optional[str] = None
    relationshipStatus: Literal[
        "single",
        "relationship",
        "married",
        "divorced",
        "widowed",
    ] | None = None
    gender: Optional[str] = None
    natalChart: Optional[str] = None
    astrology: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None

class UserAccount(BaseModel):
    tokenBalance: float

# Stripe Related Schemas Records
class TransactionRecord(BaseModel):
    transaction_id: str
    user_id: str
    amount: float
    currency: str
    transaction_type: str  # e.g., "credit", "debit"
    timestamp: str
    description: str | None = None

# REST API Request Schemas
class StripeFirebaseRequest(BaseModel):
    event: Any
    user: UserProfile
    auth: UserRecord | None = None
    model_config = {"arbitrary_types_allowed": True}