import pytest
import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient

import checkout
import frontend

ORDER = {
    "card": {"number": "4111111111111111", "expiry": "12/30", "cvv": "123"},
    "address": {
        "name": "Test User",
        "street": "1 Main St",
        "city": "Milwaukee",
        "state": "WI",
        "zip": "53202",
    },
}

CART = [
    {"id": 3, "name": "Bag", "priceCents": 3000},
    {"id": 4, "name": "Hat", "priceCents": 1200},
]

PRICES = {"3": 30.0, "4": 12.0}


class FakeResponse:
    def __init__(self, status_code, data=None):
        self.status_code = status_code
        self.data = data

    def json(self):
        return self.data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError()


class FakeServices:
    # stands in for the real cart, catalog and payment services
    def __init__(self):
        self.cart = list(CART)
        self.calls = []
        self.cart_down = False
        self.payment_status = 200

    def request(self, method, url, **kwargs):
        self.calls.append((method, url))
        if "/cart/" in url:
            if self.cart_down:
                raise requests.ConnectionError()
            if method == "GET":
                return FakeResponse(200, {"user_id": 1, "items": self.cart})
            return FakeResponse(204)
        if "/products/" in url:
            product_id = url.split("/")[-1]
            if product_id not in PRICES:
                return FakeResponse(404)
            return FakeResponse(200, {"id": product_id, "price": PRICES[product_id]})
        if url.endswith("/payment"):
            return FakeResponse(self.payment_status, {"transaction_id": "abc-123"})
        return FakeResponse(200, {})


@pytest.fixture
def services(monkeypatch):
    fake = FakeServices()
    monkeypatch.setattr(checkout.requests, "request", fake.request)
    monkeypatch.setattr(checkout, "PAYMENT_URL", None)
    monkeypatch.setattr(checkout, "NOTIFICATION_URL", None)
    monkeypatch.setattr(checkout, "SHIPPING_URL", None)
    return fake


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(checkout.router)
    return TestClient(app)


def test_good_order(client, services):
    r = client.post("/checkout/1", json=ORDER)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 42.0
    assert data["items"] == CART
    assert data["order_id"]
    assert data["transaction_id"]


def test_cart_is_emptied(client, services):
    client.post("/checkout/1", json=ORDER)
    deletes = [c for c in services.calls if c[0] == "DELETE"]
    assert len(deletes) == 2


def test_empty_cart(client, services):
    services.cart = []
    r = client.post("/checkout/1", json=ORDER)
    assert r.status_code == 400
    assert r.json()["detail"] == "cart is empty"


def test_product_not_in_catalog(client, services):
    services.cart = [{"id": 99, "name": "Ghost", "priceCents": 100}]
    r = client.post("/checkout/1", json=ORDER)
    assert r.status_code == 400
    assert "99" in r.json()["detail"]


def test_cart_service_down(client, services):
    services.cart_down = True
    r = client.post("/checkout/1", json=ORDER)
    assert r.status_code == 502
    assert "cart" in r.json()["detail"]


def test_payment_service_ok(client, services, monkeypatch):
    monkeypatch.setattr(checkout, "PAYMENT_URL", "http://payment")
    r = client.post("/checkout/1", json=ORDER)
    assert r.status_code == 200
    assert r.json()["transaction_id"] == "abc-123"


def test_payment_failed(client, services, monkeypatch):
    monkeypatch.setattr(checkout, "PAYMENT_URL", "http://payment")
    services.payment_status = 402
    r = client.post("/checkout/1", json=ORDER)
    assert r.status_code == 402
    # the cart must not be emptied when the payment fails
    assert not [c for c in services.calls if c[0] == "DELETE"]


def test_shipping_and_email_are_called(client, services, monkeypatch):
    monkeypatch.setattr(checkout, "NOTIFICATION_URL", "http://mail")
    monkeypatch.setattr(checkout, "SHIPPING_URL", "http://ship")
    client.post("/checkout/1", json=ORDER)
    urls = [c[1] for c in services.calls]
    assert "http://mail/emails/1" in urls
    assert any(u.startswith("http://ship/shipping/") for u in urls)


def test_missing_card(client, services):
    r = client.post("/checkout/1", json={"address": ORDER["address"]})
    assert r.status_code == 422


def test_recommendation_url_is_configured_for_deployment():
    assert frontend.RECOMMENDATION_URL, "Set RECOMMENDATION_URL before deploying"


def recommendation_client(monkeypatch, products, status_code=200):
    def fake_get(url, headers, timeout):
        assert url == "http://recommendation/recommendations/110"
        assert headers["X-Correlation-ID"] == "rec-test"
        return FakeResponse(status_code, products)

    monkeypatch.setattr(frontend, "RECOMMENDATION_URL", "http://recommendation")
    monkeypatch.setattr(frontend.requests, "get", fake_get)
    app = FastAPI()
    app.include_router(frontend.router)
    return TestClient(app)


def test_recommendations_from_service(monkeypatch):
    product = {"id": 2, "name": "Ball", "description": "A ball", "price": 15.0}
    client = recommendation_client(monkeypatch, [product])

    response = client.get("/recommendations/110", headers={"X-Correlation-ID": "rec-test"})

    assert response.status_code == 200
    assert "Ball" in response.text
    assert "$15.00" in response.text


def test_empty_recommendations(monkeypatch):
    client = recommendation_client(monkeypatch, [])

    response = client.get("/recommendations/110", headers={"X-Correlation-ID": "rec-test"})

    assert response.status_code == 200
    assert "No recommendations yet." in response.text


def test_recommendation_service_error(monkeypatch):
    client = recommendation_client(monkeypatch, None, 500)

    response = client.get("/recommendations/110", headers={"X-Correlation-ID": "rec-test"})

    assert response.status_code == 502
    assert response.json()["detail"] == "recommendation service error"
