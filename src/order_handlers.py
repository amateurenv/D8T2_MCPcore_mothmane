"""Порядок работы с заказом. Правила в domain, SQL в storage."""
from . import domain
from .errors import success, failure

ERROR_MESSAGES = {
    "USER_NOT_FOUND": "Пользователь не найден",
    "PRODUCT_NOT_FOUND": "Товар не найден",
    "OUT_OF_STOCK": "Недостаточно товара выбранного размера",
    "USER_LIMIT_EXCEEDED": "Превышен лимит товара на участника",
    "INSUFFICIENT_COINS": "Недостаточно коинов",
    "ORDER_NOT_FOUND": "Заказ не найден",
    "ORDER_STATUS_ERROR": "Действие недоступно для текущего состояния заказа",
}


def create_order(storage, user_id, product_id, size, quantity):
    'Реализуйте по правилам Лавки и согласованным методам.'
    user = storage.get_user(user_id)
    if user is None:
        return failure("USER_NOT_FOUND", ERROR_MESSAGES["USER_NOT_FOUND"])

    product = storage.get_product(product_id)
    if product is None:
        return failure("PRODUCT_NOT_FOUND", ERROR_MESSAGES["PRODUCT_NOT_FOUND"])

    total = domain.calculate_total(product["price_coins"], quantity)
    already_owned = storage.count_owned(user_id, product_id)
    error = domain.purchase_error(
        product=product,
        size=size,
        quantity=quantity,
        balance=user["coins"],
        already_owned=already_owned,
        total=total,
    )
    if error is not None:
        return failure(error, ERROR_MESSAGES[error])

    order = storage.create_order(
        user_id=user_id,
        product_id=product_id,
        size=size,
        quantity=quantity,
        total_price=total,
    )
    return success({
        "order_id": order["id"],
        "status": order["status"],
        "total_price": order["total_price"],
    })

def cancel_order(storage, order_id):
    'Реализуйте по правилам Лавки и согласованным методам.'
    order = storage.get_order(order_id)
    if order is None:
        return failure("ORDER_NOT_FOUND", ERROR_MESSAGES["ORDER_NOT_FOUND"])
    if not domain.can_cancel(order):
        return failure("ORDER_STATUS_ERROR", ERROR_MESSAGES["ORDER_STATUS_ERROR"])

    refund = domain.refund_amount(order["total_price"])
    cancelled = storage.cancel_order(order, refund)
    return success({
        "order_id": cancelled["id"],
        "status": cancelled["status"],
    })

def confirm_pickup(storage, order_id):
    'Реализуйте по правилам Лавки и согласованным методам.'
    order = storage.get_order(order_id)
    if order is None:
        return failure("ORDER_NOT_FOUND", ERROR_MESSAGES["ORDER_NOT_FOUND"])
    if not domain.can_pickup(order):
        return failure("ORDER_STATUS_ERROR", ERROR_MESSAGES["ORDER_STATUS_ERROR"])

    picked_up = storage.confirm_pickup(order_id)
    return success({
        "order_id": picked_up["id"],
        "status": picked_up["status"],
    })
