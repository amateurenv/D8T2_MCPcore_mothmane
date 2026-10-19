"""Сценарные проверки обработчиков заказов участка mothmane."""

from pathlib import Path

import pytest

from src.order_handlers import cancel_order, confirm_pickup, create_order
from src.storage import Storage


SEED = Path(__file__).resolve().parents[1] / "data/seed.sql"


@pytest.fixture
def storage(tmp_path):
    instance = Storage(tmp_path / "orders.db", SEED)
    try:
        yield instance
    finally:
        instance.close()


def table_state(storage):
    state = {}
    for table in ("products", "stock", "users", "orders"):
        rows = storage.connection.execute(
            f"SELECT * FROM {table} ORDER BY 1, 2"
        ).fetchall()
        state[table] = [tuple(row) for row in rows]
    return state


def error_code(result):
    assert result["ok"] is False
    return result["error"]["code"]


def test_successful_purchase_changes_all_required_state(storage):
    result = create_order(storage, "student_01", "bottle", "one_size", 1)

    assert result["ok"] is True
    assert result["data"]["status"] == "created"
    assert result["data"]["total_price"] == 150
    assert storage.get_user("student_01")["coins"] == 850
    assert storage.get_product("bottle")["stock"]["one_size"] == 11
    assert storage.get_order(result["data"]["order_id"])["status"] == "created"


def test_unknown_user_is_checked_before_unknown_product(storage):
    before = table_state(storage)
    result = create_order(storage, "missing", "missing", "missing", 1)

    assert error_code(result) == "USER_NOT_FOUND"
    assert table_state(storage) == before


def test_unknown_product_does_not_change_state(storage):
    before = table_state(storage)
    result = create_order(storage, "student_01", "missing", "one_size", 1)

    assert error_code(result) == "PRODUCT_NOT_FOUND"
    assert table_state(storage) == before


@pytest.mark.parametrize(
    ("user_id", "product_id", "size", "quantity", "expected"),
    [
        ("student_01", "hoodie", "XXL", 1, "OUT_OF_STOCK"),
        ("student_01", "hoodie", "M", 2, "USER_LIMIT_EXCEEDED"),
        ("student_poor", "bottle", "one_size", 1, "INSUFFICIENT_COINS"),
    ],
)
def test_business_refusal_keeps_every_table_unchanged(
    storage, user_id, product_id, size, quantity, expected
):
    before = table_state(storage)
    result = create_order(storage, user_id, product_id, size, quantity)

    assert error_code(result) == expected
    assert table_state(storage) == before


def test_cancel_returns_resources_only_once(storage):
    created = create_order(storage, "student_01", "bottle", "one_size", 1)
    order_id = created["data"]["order_id"]

    cancelled = cancel_order(storage, order_id)
    assert cancelled == {
        "ok": True,
        "data": {"order_id": order_id, "status": "cancelled"},
    }
    assert storage.get_user("student_01")["coins"] == 1000
    assert storage.get_product("bottle")["stock"]["one_size"] == 12

    after_first_cancel = table_state(storage)
    assert error_code(cancel_order(storage, order_id)) == "ORDER_STATUS_ERROR"
    assert error_code(confirm_pickup(storage, order_id)) == "ORDER_STATUS_ERROR"
    assert table_state(storage) == after_first_cancel


def test_pickup_changes_only_status_and_cannot_repeat(storage):
    created = create_order(storage, "student_01", "bottle", "one_size", 1)
    order_id = created["data"]["order_id"]
    balance_after_purchase = storage.get_user("student_01")["coins"]
    stock_after_purchase = storage.get_product("bottle")["stock"]["one_size"]

    picked_up = confirm_pickup(storage, order_id)
    assert picked_up == {
        "ok": True,
        "data": {"order_id": order_id, "status": "picked_up"},
    }
    assert storage.get_user("student_01")["coins"] == balance_after_purchase
    assert storage.get_product("bottle")["stock"]["one_size"] == stock_after_purchase

    after_pickup = table_state(storage)
    assert error_code(confirm_pickup(storage, order_id)) == "ORDER_STATUS_ERROR"
    assert error_code(cancel_order(storage, order_id)) == "ORDER_STATUS_ERROR"
    assert table_state(storage) == after_pickup


def test_unknown_order_is_rejected_without_changes(storage):
    before = table_state(storage)
    assert error_code(cancel_order(storage, "missing")) == "ORDER_NOT_FOUND"
    assert error_code(confirm_pickup(storage, "missing")) == "ORDER_NOT_FOUND"
    assert table_state(storage) == before
