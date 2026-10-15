import logging
import os
import uuid
from contextvars import ContextVar

import google.cloud.logging
import requests
from google.cloud.logging_v2.handlers import CloudLoggingHandler
from google.cloud.logging_v2.handlers.transports import SyncTransport
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("checkout")

router = APIRouter(prefix="/checkout", tags=["Checkout"])

# urls of the other services
CATALOG_URL = os.getenv("CATALOG_URL", "https://catalog-km6fpv6l4a-uc.a.run.app")
CART_URL = os.getenv("CART_URL", "https://cart-service-km6fpv6l4a-uc.a.run.app")
# if one of these is not set, checkout only logs that step
PAYMENT_URL = os.getenv("PAYMENT_URL")
NOTIFICATION_URL = os.getenv("NOTIFICATION_URL")
SHIPPING_URL = os.getenv("SHIPPING_URL")

# a service that was asleep can take more than a minute to wake up
TIMEOUT = 90

HEADER = "X-Correlation-ID"
correlation_id = ContextVar("correlation_id", default="-")


def add_correlation_id(record):
    record.correlation_id = correlation_id.get()
    record.json_fields = {"service": "checkout", "correlation_id": record.correlation_id}
    return True


handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(levelname)s [%(correlation_id)s] %(name)s %(message)s"))
log.addFilter(add_correlation_id)
log.addHandler(handler)
log.setLevel(logging.INFO)
log.propagate = False

# send the same logs to Google Cloud Logging as structured entries
try:
    cloud_handler = CloudLoggingHandler(google.cloud.logging.Client(), name="checkout", transport=SyncTransport)
    log.addHandler(cloud_handler)
except Exception as e:
    log.warning("cloud logging is off, logs only go to the terminal: %s", e)


class Card(BaseModel):
    number: str
    expiry: str
    cvv: str


class Address(BaseModel):
    name: str
    street: str
    city: str
    state: str
    zip: str


class Order(BaseModel):
    card: Card
    address: Address


def call(service, method, url, **kwargs):
    try:
        return requests.request(method, url, timeout=TIMEOUT, headers={HEADER: correlation_id.get()}, **kwargs)
    except requests.RequestException as e:
        log.error("%s service is not answering: %s", service, e)
        raise HTTPException(502, f"{service} service is not answering")


def get_cart(user_id):
    r = call("cart", "GET", f"{CART_URL}/cart/{user_id}")
    if r.status_code != 200:
        raise HTTPException(502, "cart service error")
    return r.json()["items"]


def get_total(items):
    total = 0
    for item in items:
        r = call("catalog", "GET", f"{CATALOG_URL}/products/{item['id']}")
        if r.status_code == 404:
            raise HTTPException(400, f"product {item['id']} is not in the catalog")
        if r.status_code != 200:
            raise HTTPException(502, "catalog service error")
        total += r.json()["price"]
    return round(total, 2)


def pay(total, card):
    last4 = card.number[-4:]
    if not PAYMENT_URL:
        transaction_id = str(uuid.uuid4())
        log.info("payment (fake): charged %.2f, card ending %s", total, last4)
        return transaction_id
    body = {"amount": total, "card": card.model_dump()}
    r = call("payment", "POST", f"{PAYMENT_URL}/payment", json=body)
    if r.status_code != 200:
        raise HTTPException(402, "payment failed")
    log.info("payment: charged %.2f, card ending %s", total, last4)
    return r.json()["transaction_id"]


def send_email(user_id, order_id, total):
    message = f"Your order {order_id} is confirmed. Total: ${total:.2f}"
    if not NOTIFICATION_URL:
        log.info("notification (fake): email to user %s: %s", user_id, message)
        return
    r = call("notification", "POST", f"{NOTIFICATION_URL}/emails/{user_id}", json={"message": message})
    if r.status_code >= 400:
        raise HTTPException(502, "notification service error")
    log.info("notification: email sent to user %s", user_id)


def ship(order_id, address):
    if not SHIPPING_URL:
        log.info("shipping (fake): order %s to %s, %s", order_id, address.city, address.state)
        return
    r = call("shipping", "POST", f"{SHIPPING_URL}/shipping/{order_id}", json=address.model_dump())
    if r.status_code >= 400:
        raise HTTPException(502, "shipping service error")
    log.info("shipping: started for order %s", order_id)


def empty_cart(user_id, items):
    # the cart service deletes one item at a time
    for item in items:
        call("cart", "DELETE", f"{CART_URL}/cart/{user_id}", params={"item_id": item["id"]})


@router.post("/{user_id}")
def checkout(user_id: int, order: Order, x_correlation_id: str | None = Header(default=None)):
    correlation_id.set(x_correlation_id or str(uuid.uuid4()))
    log.info("checkout started for user %s", user_id)
    items = get_cart(user_id)
    if not items:
        raise HTTPException(400, "cart is empty")

    # check the products before the card is charged
    total = get_total(items)

    order_id = str(uuid.uuid4())
    transaction_id = pay(total, order.card)
    send_email(user_id, order_id, total)
    ship(order_id, order.address)
    empty_cart(user_id, items)

    log.info("order %s done for user %s", order_id, user_id)
    return {
        "order_id": order_id,
        "transaction_id": transaction_id,
        "total": total,
        "items": items,
        "correlation_id": correlation_id.get(),
    }
