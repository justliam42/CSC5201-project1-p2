import logging
import os
import uuid
from contextvars import ContextVar

import google.cloud.logging
import requests
from fastapi import APIRouter, Header, HTTPException
from google.cloud.logging_v2.handlers import CloudLoggingHandler
from google.cloud.logging_v2.handlers.transports import SyncTransport

router = APIRouter(prefix="/recommendations", tags=["Recommendation"])

CART_URL = os.getenv("CART_URL", "https://cart-service-617213266896.us-central1.run.app")
CATALOG_URL = os.getenv("CATALOG_URL", "https://catalog-617213266896.us-central1.run.app")
TIMEOUT = 90

HEADER = "X-Correlation-ID"
correlation_id = ContextVar("correlation_id", default="-")

log = logging.getLogger("recommendation")


def add_correlation_id(record):
    record.correlation_id = correlation_id.get()
    record.json_fields = {"service": "recommendation", "correlation_id": record.correlation_id}
    return True


handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(levelname)s [%(correlation_id)s] %(name)s %(message)s"))
log.addFilter(add_correlation_id)
log.addHandler(handler)
log.setLevel(logging.INFO)
log.propagate = False

# send the same logs to Google Cloud Logging as structured entries
try:
    cloud_handler = CloudLoggingHandler(google.cloud.logging.Client(), name="recommendation", transport=SyncTransport)
    log.addHandler(cloud_handler)
except Exception as e:
    log.warning("cloud logging is off, logs only go to the terminal: %s", e)


def get_json(url, empty_on_404=False):
    try:
        response = requests.get(url, headers={HEADER: correlation_id.get()}, timeout=TIMEOUT)
        if empty_on_404 and response.status_code == 404:
            return []
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as error:
        log.error("call to %s failed: %s", url, error)
        raise HTTPException(502, "cart or catalog service error") from error


def product_id(product):
    return str(product.get("id", product.get("product_id")))


@router.get("/{user_id}")
def recommendations(user_id: int, x_correlation_id: str | None = Header(default=None)):
    correlation_id.set(x_correlation_id or str(uuid.uuid4()))

    # the cart sends a plain list, or 404 when the cart is empty
    cart = get_json(f"{CART_URL}/cart/{user_id}", empty_on_404=True)
    if isinstance(cart, dict):
        cart = cart.get("items", [])
    products = get_json(f"{CATALOG_URL}/products")
    if isinstance(products, dict):
        products = products["products"]

    cart_ids = {product_id(item) for item in cart}
    cart_categories = set()
    for product in products:
        if product_id(product) in cart_ids:
            cart_categories.update(product["categories"])

    recommended = []
    for product in products:
        if product_id(product) not in cart_ids and cart_categories.intersection(product["categories"]):
            recommended.append(product)
            if len(recommended) == 5:
                break

    log.info("%d recommendations for user %s, cart has %d items", len(recommended), user_id, len(cart))
    return recommended
