"""Проверки чистых бизнес-правил участка mysariaw."""

import pytest

from src.domain import (
    calculate_total,
    can_cancel,
    can_pickup,
    purchase_error,
    refund_amount,
)


@pytest.fixture
def bottle():
    return {
        "id": "bottle",
        "name": "Бутылка",
        "price_coins": 150,
        "user_limit": 2,
        "stock": {"one_size": 12},
    }


def test_two_bottles_cost_300():
    assert calculate_total(150, 2) == 300


@pytest.mark.parametrize(
    ("size", "quantity"),
    [
        ("missing", 1),
        ("one_size", 13),
    ],
)
def test_missing_size_or_quantity_returns_out_of_stock(bottle, size, quantity):
    assert purchase_error(
        bottle,
        size=size,
        quantity=quantity,
        balance=10_000,
        already_owned=0,
        total=calculate_total(bottle["price_coins"], quantity),
    ) == "OUT_OF_STOCK"


def test_stock_error_has_priority_over_limit_and_balance(bottle):
    assert purchase_error(
        bottle,
        size="missing",
        quantity=1,
        balance=0,
        already_owned=bottle["user_limit"],
        total=150,
    ) == "OUT_OF_STOCK"


def test_purchase_over_user_limit_is_rejected(bottle):
    assert purchase_error(
        bottle,
        size="one_size",
        quantity=1,
        balance=1000,
        already_owned=2,
        total=150,
    ) == "USER_LIMIT_EXCEEDED"


def test_insufficient_balance_is_rejected(bottle):
    assert purchase_error(
        bottle,
        size="one_size",
        quantity=1,
        balance=149,
        already_owned=0,
        total=150,
    ) == "INSUFFICIENT_COINS"


def test_valid_purchase_has_no_error(bottle):
    assert purchase_error(
        bottle,
        size="one_size",
        quantity=2,
        balance=300,
        already_owned=0,
        total=300,
    ) is None


def test_base_profile_refunds_saved_total_price():
    assert refund_amount(151) == 151


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("created", True),
        ("cancelled", False),
        ("picked_up", False),
    ],
)
def test_order_actions_are_allowed_only_for_created(status, expected):
    order = {"id": "order-1", "status": status}
    assert can_cancel(order) is expected
    assert can_pickup(order) is expected
