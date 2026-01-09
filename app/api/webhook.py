# app/api/webhook.py

import stripe
from fastapi import (
    APIRouter,
    HTTPException,
)
from ..utils.setup import platform
from ..utils.woodlogs import get_logger
from ..src.schema import StripeFirebaseRequest
from ..utils.deps import StripeFirebaseAuthorize
from ..src.crud import (
    CHECKOUT_LINKS,
    store_transaction_record,
    update_user_token_balance
)

stripe.api_key = platform.account.api_key

logger = get_logger(__file__)

webhook_router = APIRouter()

@webhook_router.post("/webhook/{service_app_id}/{product_id}")
async def stripe_webhook(service_app_id: str, product_id: str, inputs: StripeFirebaseAuthorize):
    """Handle Stripe webhook events for a specific service app and product.

    Returns HTTP 200 for all events to acknowledge receipt.
    Only returns 4xx for client errors (invalid config, missing headers, etc).
    Never returns 5xx as it causes Stripe to retry unnecessarily.
    """

    event_type = inputs.event["type"]
    event_id = inputs.event["id"]

    # Log all incoming webhook events
    logger.info(
        f"Webhook received: {event_type}",
        extra={
            "event_id": event_id,
            "event_type": event_type,
            "service_app_id": service_app_id,
            "product_id": product_id,
            "user_id": inputs.user.id,
        }
    )

    # Validate service app and product configuration
    service_app = platform.apps.get(service_app_id, None)
    product = service_app.get(product_id, None) if service_app else None

    if not service_app or not product:
        # 400 Bad Request - client configuration error, don't retry
        logger.error(
            f"Invalid service app or product configuration",
            extra={
                "event_id": event_id,
                "service_app_id": service_app_id,
                "product_id": product_id,
                "service_app_exists": service_app is not None,
            }
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid configuration: service_app_id '{service_app_id}' or product_id '{product_id}' not found. Please verify your webhook URL."
        )

    # Process checkout-related events
    if event_type in CHECKOUT_LINKS:
        session = inputs.event["data"]["object"]
        session_id = session.get("id")

        logger.info(
            f"Processing checkout event",
            extra={
                "event_id": event_id,
                "event_type": event_type,
                "session_id": session_id,
                "user_id": inputs.user.id,
                "product_type": product.type,
            }
        )

        try:
            # Store transaction record (includes idempotency check in the future)
            await store_transaction_record(session, inputs.user.id)

            if product.type == "tokens":
                if not hasattr(product, "add_count") or product.add_count is None:
                    # 400 Bad Request - product misconfiguration
                    logger.error(
                        f"Product configuration error: missing add_count",
                        extra={
                            "event_id": event_id,
                            "service_app_id": service_app_id,
                            "product_id": product_id,
                            "product_type": product.type,
                        }
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=f"Product misconfiguration: 'add_count' is missing for product '{product_id}'. Please update your product configuration."
                    )

                await update_user_token_balance(inputs.user.id, product.add_count)

                logger.info(
                    f"Successfully credited tokens",
                    extra={
                        "event_id": event_id,
                        "user_id": inputs.user.id,
                        "tokens_added": product.add_count,
                        "product_id": product_id,
                    }
                )

            else:
                # Log unsupported product type but return 200 (don't fail the webhook)
                logger.warning(
                    f"Unsupported product type - event acknowledged but not processed",
                    extra={
                        "event_id": event_id,
                        "product_type": product.type,
                        "product_id": product_id,
                        "service_app_id": service_app_id,
                    }
                )
                # Return 200 anyway - this isn't an error worth retrying
                return {"received": True}

        except HTTPException:
            # Re-raise HTTP exceptions (400 errors)
            raise
        except Exception as e:
            # Log unexpected errors but still return 200 to prevent retries
            logger.exception(
                f"Error processing webhook event",
                extra={
                    "event_id": event_id,
                    "event_type": event_type,
                    "user_id": inputs.user.id,
                    "error": str(e),
                }
            )
            # Return 200 to acknowledge receipt even if processing failed
            # This prevents infinite retries for transient database issues
            return {"received": True, "processed": False}

    else:
        # Event type not in CHECKOUT_LINKS - acknowledge but don't process
        logger.debug(
            f"Event type not processed: {event_type}",
            extra={
                "event_id": event_id,
                "event_type": event_type,
            }
        )

    # Success response - Stripe only cares about HTTP 200 status
    return {"received": True}