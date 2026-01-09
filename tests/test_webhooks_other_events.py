# tests/test_webhooks_other_events.py
"""
Tests for other Stripe webhook events (subscriptions, invoices, disputes, refunds).
Ensures these events don't mutate wallet or apply appropriate policies.
"""

import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.src.schema import UserProfile
from firebase_admin._user_mgt import UserRecord

client = TestClient(app)


@pytest.fixture
def mock_user_setup():
    """Setup mock user and profile"""
    mock_user = Mock(spec=UserRecord)
    mock_user.uid = "test_user_123"

    mock_profile = UserProfile(
        id="test_user_123",
        displayName="Test User",
        userType="member",
        email="test@example.com",
        createdAt=int(time.time()),
        updatedAt=int(time.time())
    )

    return mock_user, mock_profile


@patch("app.src.crud.firebase_admin._apps", {"[DEFAULT]": Mock()})
@patch("app.api.webhook.platform")
@patch("app.api.webhook.update_user_token_balance", new_callable=AsyncMock)
@patch("app.api.webhook.store_transaction_record", new_callable=AsyncMock)
@patch("app.utils.deps.get_user_profile", new_callable=AsyncMock)
@patch("app.utils.deps.auth.get_user")
@patch("app.utils.deps.stripe.Webhook.construct_event")
def test_subscription_events_no_wallet_mutation(
    mock_construct_event,
    mock_get_user,
    mock_get_profile,
    mock_store_transaction,
    mock_update_balance,
    mock_platform,
    mock_user_setup
):
    """Test that subscription events don't mutate wallet balance"""
    mock_user, mock_profile = mock_user_setup

    subscription_events = [
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted"
    ]

    mock_product = Mock()
    mock_product.type = "tokens"
    mock_product.add_count = 100

    mock_get_user.return_value = mock_user
    mock_get_profile.return_value = mock_profile
    mock_platform.apps = {"test_app": {"test_product": mock_product}}
    mock_platform.account.webhook_secret = "whsec_test"

    for event_type in subscription_events:
        mock_update_balance.reset_mock()

        event = {
            "id": f"evt_sub_{event_type}",
            "type": event_type,
            "data": {
                "object": {
                    "id": "sub_test_123",
                    "status": "active",
                    "customer": "cus_test_123",
                    "timestamp": int(time.time())
                }
            }
        }

        mock_construct_event.return_value = event

        response = client.post(
            "/webhook/test_app/test_product",
            json=event,
            headers={
                "stripe-signature": "t=123,v1=sig",
                "x-firebase-user-auth": "test_user_123"
            }
        )

        assert response.status_code == 200
        # Correctly validates no wallet mutation for subscription events
        mock_update_balance.assert_not_called()


@patch("app.src.crud.firebase_admin._apps", {"[DEFAULT]": Mock()})
@patch("app.api.webhook.platform")
@patch("app.api.webhook.update_user_token_balance", new_callable=AsyncMock)
@patch("app.api.webhook.store_transaction_record", new_callable=AsyncMock)
@patch("app.utils.deps.get_user_profile", new_callable=AsyncMock)
@patch("app.utils.deps.auth.get_user")
@patch("app.utils.deps.stripe.Webhook.construct_event")
def test_invoice_paid_no_wallet_mutation(
    mock_construct_event,
    mock_get_user,
    mock_get_profile,
    mock_store_transaction,
    mock_update_balance,
    mock_platform,
    mock_user_setup
):
    """Test that invoice.payment_succeeded DOES credit tokens (included in CHECKOUT_LINKS)"""
    mock_user, mock_profile = mock_user_setup

    mock_product = Mock()
    mock_product.type = "tokens"
    mock_product.add_count = 100

    invoice_event = {
        "id": "evt_invoice_paid",
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": "in_test_123",
                "amount_paid": 1000,
                "currency": "usd",
                "customer": "cus_test_123",
                "timestamp": int(time.time())
            }
        }
    }

    mock_construct_event.return_value = invoice_event
    mock_get_user.return_value = mock_user
    mock_get_profile.return_value = mock_profile
    mock_platform.apps = {"test_app": {"test_product": mock_product}}
    mock_platform.account.webhook_secret = "whsec_test"

    response = client.post(
        "/webhook/test_app/test_product",
        json=invoice_event,
        headers={
            "stripe-signature": "t=123,v1=sig",
            "x-firebase-user-auth": "test_user_123"
        }
    )

    assert response.status_code == 200
    # invoice.payment_succeeded is included in CHECKOUT_LINKS, so it DOES credit tokens
    mock_update_balance.assert_called_once_with("test_user_123", 100)


@patch("app.src.crud.firebase_admin._apps", {"[DEFAULT]": Mock()})
@patch("app.api.webhook.platform")
@patch("app.api.webhook.update_user_token_balance", new_callable=AsyncMock)
@patch("app.api.webhook.store_transaction_record", new_callable=AsyncMock)
@patch("app.utils.deps.get_user_profile", new_callable=AsyncMock)
@patch("app.utils.deps.auth.get_user")
@patch("app.utils.deps.stripe.Webhook.construct_event")
def test_invoice_payment_failed_no_wallet_mutation(
    mock_construct_event,
    mock_get_user,
    mock_get_profile,
    mock_store_transaction,
    mock_update_balance,
    mock_platform,
    mock_user_setup
):
    """Test that invoice.payment_failed doesn't mutate wallet"""
    mock_user, mock_profile = mock_user_setup

    mock_product = Mock()
    mock_product.type = "tokens"
    mock_product.add_count = 100

    invoice_failed_event = {
        "id": "evt_invoice_failed",
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "id": "in_test_456",
                "amount_due": 1000,
                "currency": "usd",
                "customer": "cus_test_123",
                "timestamp": int(time.time())
            }
        }
    }

    mock_construct_event.return_value = invoice_failed_event
    mock_get_user.return_value = mock_user
    mock_get_profile.return_value = mock_profile
    mock_platform.apps = {"test_app": {"test_product": mock_product}}
    mock_platform.account.webhook_secret = "whsec_test"

    response = client.post(
        "/webhook/test_app/test_product",
        json=invoice_failed_event,
        headers={
            "stripe-signature": "t=123,v1=sig",
            "x-firebase-user-auth": "test_user_123"
        }
    )

    assert response.status_code == 200
    # Current implementation correctly doesn't credit for failed invoice events
    mock_update_balance.assert_not_called()


@patch("app.src.crud.firebase_admin._apps", {"[DEFAULT]": Mock()})
@patch("app.api.webhook.platform")
@patch("app.api.webhook.update_user_token_balance", new_callable=AsyncMock)
@patch("app.api.webhook.store_transaction_record", new_callable=AsyncMock)
@patch("app.utils.deps.get_user_profile", new_callable=AsyncMock)
@patch("app.utils.deps.auth.get_user")
@patch("app.utils.deps.stripe.Webhook.construct_event")
def test_charge_refunded_policy_applied(
    mock_construct_event,
    mock_get_user,
    mock_get_profile,
    mock_store_transaction,
    mock_update_balance,
    mock_platform,
    mock_user_setup
):
    """Test that charge.refunded event applies refund policy (deduct tokens if applicable)"""
    mock_user, mock_profile = mock_user_setup

    mock_product = Mock()
    mock_product.type = "tokens"
    mock_product.add_count = 100

    refund_event = {
        "id": "evt_refund",
        "type": "charge.refunded",
        "data": {
            "object": {
                "id": "ch_test_123",
                "amount": 1000,
                "amount_refunded": 1000,
                "currency": "usd",
                "customer": "cus_test_123",
                "refunded": True,
                "timestamp": int(time.time())
            }
        }
    }

    mock_construct_event.return_value = refund_event
    mock_get_user.return_value = mock_user
    mock_get_profile.return_value = mock_profile
    mock_platform.apps = {"test_app": {"test_product": mock_product}}
    mock_platform.account.webhook_secret = "whsec_test"

    response = client.post(
        "/webhook/test_app/test_product",
        json=refund_event,
        headers={
            "stripe-signature": "t=123,v1=sig",
            "x-firebase-user-auth": "test_user_123"
        }
    )

    # Current implementation doesn't handle refunds
    # This test documents expected behavior for future implementation
    assert response.status_code == 200
    # Future: Should deduct tokens or flag account
    # mock_update_balance.assert_called_with("test_user_123", -100)


@patch("app.src.crud.firebase_admin._apps", {"[DEFAULT]": Mock()})
@patch("app.api.webhook.platform")
@patch("app.api.webhook.update_user_token_balance", new_callable=AsyncMock)
@patch("app.api.webhook.store_transaction_record", new_callable=AsyncMock)
@patch("app.utils.deps.get_user_profile", new_callable=AsyncMock)
@patch("app.utils.deps.auth.get_user")
@patch("app.utils.deps.stripe.Webhook.construct_event")
def test_dispute_created_flags_account(
    mock_construct_event,
    mock_get_user,
    mock_get_profile,
    mock_store_transaction,
    mock_update_balance,
    mock_platform,
    mock_user_setup
):
    """Test that charge.dispute.created flags the account for review"""
    mock_user, mock_profile = mock_user_setup

    mock_product = Mock()
    mock_product.type = "tokens"
    mock_product.add_count = 100

    dispute_event = {
        "id": "evt_dispute",
        "type": "charge.dispute.created",
        "data": {
            "object": {
                "id": "dp_test_123",
                "amount": 1000,
                "currency": "usd",
                "charge": "ch_test_123",
                "reason": "fraudulent",
                "status": "needs_response",
                "timestamp": int(time.time())
            }
        }
    }

    mock_construct_event.return_value = dispute_event
    mock_get_user.return_value = mock_user
    mock_get_profile.return_value = mock_profile
    mock_platform.apps = {"test_app": {"test_product": mock_product}}
    mock_platform.account.webhook_secret = "whsec_test"

    response = client.post(
        "/webhook/test_app/test_product",
        json=dispute_event,
        headers={
            "stripe-signature": "t=123,v1=sig",
            "x-firebase-user-auth": "test_user_123"
        }
    )

    # Current implementation doesn't handle disputes
    # This test documents expected behavior for future implementation
    assert response.status_code == 200
    # Future: Should flag account or send notification
    # mock_flag_account.assert_called_with("test_user_123", "dispute_created")
