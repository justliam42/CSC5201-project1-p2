# Test the cart service API

import os
import pytest
import redis
from fastapi.testclient import TestClient
from app import app, Item

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_redis():
    with redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=0,
    ) as database:
        database.flushdb()


def test_add_user_item():
    user_id = 1
    item_id = 1
    response = client.post(f"/cart/{user_id}", json={"id": item_id, "categories": ["electronics"], "description": "Test Item", "name": "Test Item", "price": 100.0})
    assert response.status_code == 201

    response = client.delete(f"/cart/{user_id}", params={"item_id": item_id})
    assert response.status_code == 204

def test_delete_nonexistent_item():
    user_id = 1
    item_id = 999  
    response = client.delete(f"/cart/{user_id}", params={"item_id": item_id})
    assert response.status_code == 204

def test_add_and_get_user_items():
    user_id = 2
    item1 = Item(id=1, categories=["electronics"], name="Item 1", price=100.0, description="Test Item 1")
    item2 = Item(id=2, categories=["books"], name="Item 2", price=200.0, description="Test Item 2")

    client.post(f"/cart/{user_id}", json=item1.model_dump())
    client.post(f"/cart/{user_id}", json=item2.model_dump())

    response = client.get(f"/cart/{user_id}")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert len(items) == 2
    assert any(item["id"] == item1.id for item in items)
    assert any(item["id"] == item2.id for item in items)