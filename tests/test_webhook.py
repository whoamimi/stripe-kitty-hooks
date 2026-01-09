# tests/test_webhook.py

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from firebase_admin._user_mgt import UserRecord
from app.src.schema import UserProfile

client = TestClient(app)

# Mock data fixtures
@pytest.fixture
def mock_stripe_event_checkout_completed():
    """Mock Stripe checkout.session.completed event"""
    return {
        "id": "evt_test_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "amount_total": 1000,
                "currency": "usd",
                "customer": "cus_test_123",
                "payment_status": "paid",
                "metadata": {}
            }
        }
    }

@pytest.fixture
def mock_stripe_event_invoice_succeeded():
    """Mock Stripe invoice.payment_succeeded event"""
    return {
        "id": "evt_test_456",
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": "in_test_456",
                "amount_paid": 2000,
                "currency": "usd",
                "customer": "cus_test_123"
            }
        }
    }

@pytest.fixture
def mock_user_record():
    """Mock Firebase UserRecord"""
    user = Mock(spec=UserRecord)
    user.uid = "test_user_123"
    user.email = "test@example.com"
    user.display_name = "Test User"
    return user

@pytest.fixture
def mock_user_profile():
    """Mock user profile data"""
    return UserProfile(
        id="test_user_123",
        displayName="Test User",
        userType="member",
        email="test@example.com",
        createdAt=1234567890,
        updatedAt=1234567890,
        lastLogin=1234567890
    )

@pytest.fixture
def mock_platform_config():
    """Mock platform configuration"""
    mock_product = Mock()
    mock_product.type = "tokens"
    mock_product.add_count = 100

    mock_service = {"test_product": mock_product}

    mock_platform = Mock()
    mock_platform.apps = {"test_app": mock_service}
    mock_platform.account.webhook_secret = "whsec_test_secret"

    return mock_platform


# Test Cases

@patch("app.src.crud.firebase_admin._apps", {"[DEFAULT]": Mock()})
@patch("app.api.webhook.platform")
@patch("app.api.webhook.update_user_token_balance", new_callable=AsyncMock)
@patch("app.api.webhook.store_transaction_record", new_callable=AsyncMock)
@patch("app.utils.deps.get_user_profile", new_callable=AsyncMock)
@patch("app.utils.deps.auth.get_user")
@patch("app.utils.deps.stripe.Webhook.construct_event")
def test_webhook_checkout_completed_success(
    mock_construct_event,
    mock_get_user,
    mock_get_profile,
    mock_store_transaction,
    mock_update_balance,
    mock_platform,
    mock_stripe_event_checkout_completed,
    mock_user_record,
    mock_user_profile,
    mock_platform_config
):
    """Test successful checkout.session.completed webhook"""
    # Setup mocks
    mock_construct_event.return_value = mock_stripe_event_checkout_completed
    mock_get_user.return_value = mock_user_record
    mock_get_profile.return_value = mock_user_profile
    mock_platform.apps = mock_platform_config.apps
    mock_platform.account.webhook_secret = mock_platform_config.account.webhook_secret

    # Make request
    response = client.post(
        "/webhook/test_app/test_product",
        json=mock_stripe_event_checkout_completed,
        headers={
            "stripe-signature": "t=123,v1=test_sig",
            "x-firebase-user-auth": "test_user_123"
        }
    )

    # Assertions
    assert response.status_code == 200
    assert response.json() == {"status": 200, "message": "Socket Completed."}
    mock_construct_event.assert_called_once()
    mock_get_user.assert_called_once_with("test_user_123")


@patch("app.utils.deps.stripe.Webhook.construct_event")
def test_webhook_missing_stripe_signature(mock_construct_event):
    """Test webhook fails when stripe-signature header is missing"""
    response = client.post(
        "/webhook/test_app/test_product",
        json={},
        headers={
            "x-firebase-user-auth": "test_user_123"
        }
    )

    assert response.status_code == 400
    assert "Missing Stripe signature header" in response.json()["detail"]


@patch("app.utils.deps.stripe.Webhook.construct_event")
def test_webhook_missing_firebase_auth(mock_construct_event, mock_stripe_event_checkout_completed):
    """Test webhook fails when firebase auth header is missing"""
    mock_construct_event.return_value = mock_stripe_event_checkout_completed

    response = client.post(
        "/webhook/test_app/test_product",
        json=mock_stripe_event_checkout_completed,
        headers={
            "stripe-signature": "t=123,v1=test_sig"
        }
    )

    assert response.status_code == 400
    assert "Missing Firebase auth header" in response.json()["detail"]


@patch("app.src.crud.firebase_admin._apps", {"[DEFAULT]": Mock()})
@patch("app.api.webhook.platform")
@patch("app.utils.deps.get_user_profile", new_callable=AsyncMock)
@patch("app.utils.deps.auth.get_user")
@patch("app.utils.deps.stripe.Webhook.construct_event")
def test_webhook_invalid_service_app(
    mock_construct_event,
    mock_get_user,
    mock_get_profile,
    mock_platform,
    mock_stripe_event_checkout_completed,
    mock_user_record,
    mock_user_profile
):
    """Test webhook fails with invalid service app ID"""
    # Setup mocks
    mock_construct_event.return_value = mock_stripe_event_checkout_completed
    mock_get_user.return_value = mock_user_record
    mock_get_profile.return_value = mock_user_profile
    mock_platform.apps = {}  # Empty apps
    mock_platform.account.webhook_secret = "whsec_test"

    response = client.post(
        "/webhook/invalid_app/test_product",
        json=mock_stripe_event_checkout_completed,
        headers={
            "stripe-signature": "t=123,v1=test_sig",
            "x-firebase-user-auth": "test_user_123"
        }
    )

    assert response.status_code == 404
    assert "Service app or product not found" in response.json()["detail"]


@patch("app.src.crud.firebase_admin._apps", {"[DEFAULT]": Mock()})
@patch("app.api.webhook.platform")
@patch("app.api.webhook.store_transaction_record", new_callable=AsyncMock)
@patch("app.utils.deps.get_user_profile", new_callable=AsyncMock)
@patch("app.utils.deps.auth.get_user")
@patch("app.utils.deps.stripe.Webhook.construct_event")
def test_webhook_invoice_payment_succeeded(
    mock_construct_event,
    mock_get_user,
    mock_get_profile,
    mock_store_transaction,
    mock_platform,
    mock_stripe_event_invoice_succeeded,
    mock_user_record,
    mock_user_profile,
    mock_platform_config
):
    """Test invoice.payment_succeeded webhook"""
    # Setup mocks
    mock_construct_event.return_value = mock_stripe_event_invoice_succeeded
    mock_get_user.return_value = mock_user_record
    mock_get_profile.return_value = mock_user_profile
    mock_platform.apps = mock_platform_config.apps
    mock_platform.account.webhook_secret = mock_platform_config.account.webhook_secret

    response = client.post(
        "/webhook/test_app/test_product",
        json=mock_stripe_event_invoice_succeeded,
        headers={
            "stripe-signature": "t=123,v1=test_sig",
            "x-firebase-user-auth": "test_user_123"
        }
    )

    # Invoice events don't trigger checkout logic, so they return 200
    assert response.status_code == 200


@patch("app.src.crud.firebase_admin._apps", {"[DEFAULT]": Mock()})
@patch("app.api.webhook.platform")
@patch("app.api.webhook.update_user_token_balance", new_callable=AsyncMock)
@patch("app.api.webhook.store_transaction_record", new_callable=AsyncMock)
@patch("app.utils.deps.get_user_profile", new_callable=AsyncMock)
@patch("app.utils.deps.auth.get_user")
@patch("app.utils.deps.stripe.Webhook.construct_event")
def test_webhook_product_type_tokens(
    mock_construct_event,
    mock_get_user,
    mock_get_profile,
    mock_store_transaction,
    mock_update_balance,
    mock_platform,
    mock_stripe_event_checkout_completed,
    mock_user_record,
    mock_user_profile
):
    """Test webhook handles token product type correctly"""
    # Setup mocks with token product
    mock_product = Mock()
    mock_product.type = "tokens"
    mock_product.add_count = 250

    mock_platform.apps = {"test_app": {"test_product": mock_product}}
    mock_platform.account.webhook_secret = "whsec_test"

    mock_construct_event.return_value = mock_stripe_event_checkout_completed
    mock_get_user.return_value = mock_user_record
    mock_get_profile.return_value = mock_user_profile

    response = client.post(
        "/webhook/test_app/test_product",
        json=mock_stripe_event_checkout_completed,
        headers={
            "stripe-signature": "t=123,v1=test_sig",
            "x-firebase-user-auth": "test_user_123"
        }
    )

    assert response.status_code == 200


@patch("app.src.crud.firebase_admin._apps", {"[DEFAULT]": Mock()})
@patch("app.api.webhook.platform")
@patch("app.api.webhook.store_transaction_record", new_callable=AsyncMock)
@patch("app.utils.deps.get_user_profile", new_callable=AsyncMock)
@patch("app.utils.deps.auth.get_user")
@patch("app.utils.deps.stripe.Webhook.construct_event")
def test_webhook_unsupported_product_type(
    mock_construct_event,
    mock_get_user,
    mock_get_profile,
    mock_store_transaction,
    mock_platform,
    mock_stripe_event_checkout_completed,
    mock_user_record,
    mock_user_profile
):
    """Test webhook fails with unsupported product type"""
    # Setup mocks with unsupported product type
    mock_product = Mock()
    mock_product.type = "subscription"  # Unsupported type

    mock_platform.apps = {"test_app": {"test_product": mock_product}}
    mock_platform.account.webhook_secret = "whsec_test"

    mock_construct_event.return_value = mock_stripe_event_checkout_completed
    mock_get_user.return_value = mock_user_record
    mock_get_profile.return_value = mock_user_profile

    response = client.post(
        "/webhook/test_app/test_product",
        json=mock_stripe_event_checkout_completed,
        headers={
            "stripe-signature": "t=123,v1=test_sig",
            "x-firebase-user-auth": "test_user_123"
        }
    )

    assert response.status_code == 500
    assert "Unsupported product type" in response.json()["detail"]
