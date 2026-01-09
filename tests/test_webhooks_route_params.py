# tests/test_webhooks_route_params.py
"""
Tests for webhook route path parameters: service_app_id and product_id
Tests both successful routing and validation failures.
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
def test_webhook_valid_service_app_and_product_success(
    mock_construct_event,
    mock_get_user,
    mock_get_profile,
    mock_store_transaction,
    mock_update_balance,
    mock_platform,
    mock_user_setup
):
    """Test successful webhook request with valid service_app_id and product_id"""
    mock_user, mock_profile = mock_user_setup

    # Setup valid product configuration
    mock_product = Mock()
    mock_product.type = "tokens"
    mock_product.add_count = 10

    mock_platform.apps = {
        "tarotarotai": {
            "5_orbs": mock_product
        }
    }
    mock_platform.account.webhook_secret = "whsec_test"

    checkout_event = {
        "id": "evt_test_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "amount_total": 500,
                "currency": "usd",
                "customer": "cus_test_123",
                "timestamp": int(time.time())
            }
        }
    }

    mock_construct_event.return_value = checkout_event
    mock_get_user.return_value = mock_user
    mock_get_profile.return_value = mock_profile

    response = client.post(
        "/webhook/tarotarotai/5_orbs",
        json=checkout_event,
        headers={
            "stripe-signature": "t=123,v1=sig",
            "x-firebase-user-auth": "test_user_123"
        }
    )

    assert response.status_code == 200
    assert response.json() == {"status": 200, "message": "Socket Completed."}
    mock_update_balance.assert_called_once_with("test_user_123", 10)
    mock_store_transaction.assert_called_once()


@patch("app.src.crud.firebase_admin._apps", {"[DEFAULT]": Mock()})
@patch("app.api.webhook.platform")
@patch("app.api.webhook.update_user_token_balance", new_callable=AsyncMock)
@patch("app.api.webhook.store_transaction_record", new_callable=AsyncMock)
@patch("app.utils.deps.get_user_profile", new_callable=AsyncMock)
@patch("app.utils.deps.auth.get_user")
@patch("app.utils.deps.stripe.Webhook.construct_event")
def test_webhook_invalid_service_app_id_returns_404(
    mock_construct_event,
    mock_get_user,
    mock_get_profile,
    mock_store_transaction,
    mock_update_balance,
    mock_platform,
    mock_user_setup
):
    """Test webhook fails with 404 when service_app_id doesn't exist"""
    mock_user, mock_profile = mock_user_setup

    # Setup platform with different service apps
    mock_platform.apps = {
        "tarotarotai": {"5_orbs": Mock()},
        "notion_app": {"subscription": Mock()}
    }
    mock_platform.account.webhook_secret = "whsec_test"

    checkout_event = {
        "id": "evt_test_456",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_456",
                "timestamp": int(time.time())
            }
        }
    }

    mock_construct_event.return_value = checkout_event
    mock_get_user.return_value = mock_user
    mock_get_profile.return_value = mock_profile

    # Request with non-existent service_app_id
    response = client.post(
        "/webhook/invalid_app_id/5_orbs",
        json=checkout_event,
        headers={
            "stripe-signature": "t=123,v1=sig",
            "x-firebase-user-auth": "test_user_123"
        }
    )

    assert response.status_code == 404
    assert "Service app or product not found" in response.json()["detail"]
    assert "invalid_app_id/5_orbs" in response.json()["detail"]
    # Ensure no wallet mutation occurred
    mock_update_balance.assert_not_called()
    mock_store_transaction.assert_not_called()


@patch("app.src.crud.firebase_admin._apps", {"[DEFAULT]": Mock()})
@patch("app.api.webhook.platform")
@patch("app.api.webhook.update_user_token_balance", new_callable=AsyncMock)
@patch("app.api.webhook.store_transaction_record", new_callable=AsyncMock)
@patch("app.utils.deps.get_user_profile", new_callable=AsyncMock)
@patch("app.utils.deps.auth.get_user")
@patch("app.utils.deps.stripe.Webhook.construct_event")
def test_webhook_invalid_product_id_returns_404(
    mock_construct_event,
    mock_get_user,
    mock_get_profile,
    mock_store_transaction,
    mock_update_balance,
    mock_platform,
    mock_user_setup
):
    """Test webhook fails with 404 when product_id doesn't exist in valid service_app"""
    mock_user, mock_profile = mock_user_setup

    # Setup service app without the requested product
    mock_product = Mock()
    mock_product.type = "tokens"
    mock_product.add_count = 5

    mock_platform.apps = {
        "tarotarotai": {
            "5_orbs": mock_product,
            "10_orbs": mock_product
        }
    }
    mock_platform.account.webhook_secret = "whsec_test"

    checkout_event = {
        "id": "evt_test_789",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_789",
                "timestamp": int(time.time())
            }
        }
    }

    mock_construct_event.return_value = checkout_event
    mock_get_user.return_value = mock_user
    mock_get_profile.return_value = mock_profile

    # Request with non-existent product_id
    response = client.post(
        "/webhook/tarotarotai/100_orbs",
        json=checkout_event,
        headers={
            "stripe-signature": "t=123,v1=sig",
            "x-firebase-user-auth": "test_user_123"
        }
    )

    assert response.status_code == 404
    assert "Service app or product not found" in response.json()["detail"]
    assert "tarotarotai/100_orbs" in response.json()["detail"]
    # Ensure no wallet mutation occurred
    mock_update_balance.assert_not_called()
    mock_store_transaction.assert_not_called()


@patch("app.src.crud.firebase_admin._apps", {"[DEFAULT]": Mock()})
@patch("app.api.webhook.platform")
@patch("app.api.webhook.update_user_token_balance", new_callable=AsyncMock)
@patch("app.api.webhook.store_transaction_record", new_callable=AsyncMock)
@patch("app.utils.deps.get_user_profile", new_callable=AsyncMock)
@patch("app.utils.deps.auth.get_user")
@patch("app.utils.deps.stripe.Webhook.construct_event")
def test_webhook_both_invalid_service_app_and_product_returns_404(
    mock_construct_event,
    mock_get_user,
    mock_get_profile,
    mock_store_transaction,
    mock_update_balance,
    mock_platform,
    mock_user_setup
):
    """Test webhook fails with 404 when both service_app_id and product_id are invalid"""
    mock_user, mock_profile = mock_user_setup

    mock_platform.apps = {
        "valid_app": {"valid_product": Mock()}
    }
    mock_platform.account.webhook_secret = "whsec_test"

    checkout_event = {
        "id": "evt_test_999",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_999",
                "timestamp": int(time.time())
            }
        }
    }

    mock_construct_event.return_value = checkout_event
    mock_get_user.return_value = mock_user
    mock_get_profile.return_value = mock_profile

    response = client.post(
        "/webhook/nonexistent_app/nonexistent_product",
        json=checkout_event,
        headers={
            "stripe-signature": "t=123,v1=sig",
            "x-firebase-user-auth": "test_user_123"
        }
    )

    assert response.status_code == 404
    assert "Service app or product not found" in response.json()["detail"]
    assert "nonexistent_app/nonexistent_product" in response.json()["detail"]
    mock_update_balance.assert_not_called()
    mock_store_transaction.assert_not_called()


@patch("app.src.crud.firebase_admin._apps", {"[DEFAULT]": Mock()})
@patch("app.api.webhook.platform")
@patch("app.api.webhook.update_user_token_balance", new_callable=AsyncMock)
@patch("app.api.webhook.store_transaction_record", new_callable=AsyncMock)
@patch("app.utils.deps.get_user_profile", new_callable=AsyncMock)
@patch("app.utils.deps.auth.get_user")
@patch("app.utils.deps.stripe.Webhook.construct_event")
def test_webhook_multiple_apps_with_same_product_names(
    mock_construct_event,
    mock_get_user,
    mock_get_profile,
    mock_store_transaction,
    mock_update_balance,
    mock_platform,
    mock_user_setup
):
    """Test that different apps can have products with the same name (isolation)"""
    mock_user, mock_profile = mock_user_setup

    # Setup two different apps with products named the same
    tarot_product = Mock()
    tarot_product.type = "tokens"
    tarot_product.add_count = 5

    notion_product = Mock()
    notion_product.type = "tokens"
    notion_product.add_count = 100

    mock_platform.apps = {
        "tarotarotai": {"premium": tarot_product},
        "notion_app": {"premium": notion_product}
    }
    mock_platform.account.webhook_secret = "whsec_test"

    checkout_event = {
        "id": "evt_test_isolation",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_isolation",
                "timestamp": int(time.time())
            }
        }
    }

    mock_construct_event.return_value = checkout_event
    mock_get_user.return_value = mock_user
    mock_get_profile.return_value = mock_profile

    # Test tarotarotai/premium
    response1 = client.post(
        "/webhook/tarotarotai/premium",
        json=checkout_event,
        headers={
            "stripe-signature": "t=123,v1=sig",
            "x-firebase-user-auth": "test_user_123"
        }
    )

    assert response1.status_code == 200
    mock_update_balance.assert_called_with("test_user_123", 5)

    mock_update_balance.reset_mock()

    # Test notion_app/premium
    response2 = client.post(
        "/webhook/notion_app/premium",
        json=checkout_event,
        headers={
            "stripe-signature": "t=123,v1=sig",
            "x-firebase-user-auth": "test_user_123"
        }
    )

    assert response2.status_code == 200
    mock_update_balance.assert_called_with("test_user_123", 100)


@patch("app.src.crud.firebase_admin._apps", {"[DEFAULT]": Mock()})
@patch("app.api.webhook.platform")
@patch("app.api.webhook.update_user_token_balance", new_callable=AsyncMock)
@patch("app.api.webhook.store_transaction_record", new_callable=AsyncMock)
@patch("app.utils.deps.get_user_profile", new_callable=AsyncMock)
@patch("app.utils.deps.auth.get_user")
@patch("app.utils.deps.stripe.Webhook.construct_event")
def test_webhook_special_characters_in_path_params(
    mock_construct_event,
    mock_get_user,
    mock_get_profile,
    mock_store_transaction,
    mock_update_balance,
    mock_platform,
    mock_user_setup
):
    """Test webhook handles path parameters with special characters (underscores, hyphens)"""
    mock_user, mock_profile = mock_user_setup

    mock_product = Mock()
    mock_product.type = "tokens"
    mock_product.add_count = 15

    mock_platform.apps = {
        "my-cool-app_v2": {"product_tier-1": mock_product}
    }
    mock_platform.account.webhook_secret = "whsec_test"

    checkout_event = {
        "id": "evt_special_chars",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_special_chars",
                "timestamp": int(time.time())
            }
        }
    }

    mock_construct_event.return_value = checkout_event
    mock_get_user.return_value = mock_user
    mock_get_profile.return_value = mock_profile

    response = client.post(
        "/webhook/my-cool-app_v2/product_tier-1",
        json=checkout_event,
        headers={
            "stripe-signature": "t=123,v1=sig",
            "x-firebase-user-auth": "test_user_123"
        }
    )

    assert response.status_code == 200
    mock_update_balance.assert_called_once_with("test_user_123", 15)


@patch("app.src.crud.firebase_admin._apps", {"[DEFAULT]": Mock()})
@patch("app.api.webhook.platform")
@patch("app.api.webhook.update_user_token_balance", new_callable=AsyncMock)
@patch("app.api.webhook.store_transaction_record", new_callable=AsyncMock)
@patch("app.utils.deps.get_user_profile", new_callable=AsyncMock)
@patch("app.utils.deps.auth.get_user")
@patch("app.utils.deps.stripe.Webhook.construct_event")
def test_webhook_empty_service_app_dict_returns_404(
    mock_construct_event,
    mock_get_user,
    mock_get_profile,
    mock_store_transaction,
    mock_update_balance,
    mock_platform,
    mock_user_setup
):
    """Test webhook fails when service_app exists but has no products"""
    mock_user, mock_profile = mock_user_setup

    # Service app exists but is empty
    mock_platform.apps = {
        "empty_app": {}
    }
    mock_platform.account.webhook_secret = "whsec_test"

    checkout_event = {
        "id": "evt_empty_app",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_empty_app",
                "timestamp": int(time.time())
            }
        }
    }

    mock_construct_event.return_value = checkout_event
    mock_get_user.return_value = mock_user
    mock_get_profile.return_value = mock_profile

    response = client.post(
        "/webhook/empty_app/any_product",
        json=checkout_event,
        headers={
            "stripe-signature": "t=123,v1=sig",
            "x-firebase-user-auth": "test_user_123"
        }
    )

    assert response.status_code == 404
    assert "Service app or product not found" in response.json()["detail"]
    assert "empty_app/any_product" in response.json()["detail"]
    mock_update_balance.assert_not_called()
