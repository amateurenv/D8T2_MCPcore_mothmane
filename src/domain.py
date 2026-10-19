"""Правила без SQL и MCP. Вся арифметика в целых коинах."""

def calculate_total(price, quantity):
    'Стоимость заказа.'
    return price * quantity

def purchase_error(product, size, quantity, balance, already_owned, total):
    'Код отказа или None. Пользователь и товар уже найдены.'
    # Порядок проверок является частью правил Лавки: при нескольких проблемах
    # клиент должен получить первый подходящий код из этого списка.
    stock = product["stock"]
    if size not in stock or stock[size] < quantity:
        return "OUT_OF_STOCK"
    if already_owned + quantity > product["user_limit"]:
        return "USER_LIMIT_EXCEEDED"
    if balance < total:
        return "INSUFFICIENT_COINS"
    return None

def refund_amount(total_price):
    'Сумма возврата по сохранённой стоимости заказа.'
    return total_price

def can_cancel(order):
    'Можно ли отменить найденный заказ.'
    return order["status"] == "created"

def can_pickup(order):
    'Можно ли выдать найденный заказ.'
    return order["status"] == "created"
