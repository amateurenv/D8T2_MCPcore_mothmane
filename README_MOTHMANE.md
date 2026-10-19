# Участок mothmane: действия с заказом и сценарные тесты

Это отдельная учебная копия для участка **mothmane**. В ней собран полностью
работающий профиль `base`, чтобы можно было увидеть обработчики в настоящей
системе. В командный GitLab нужно переносить только файлы своего участка.

## Твои файлы

- `src/order_handlers.py` — создание, отмена и выдача заказа;
- `testing/test_orders.py` — сценарные тесты успехов и отказов.

В этом репозитории также присутствуют готовые `domain.py`, `storage.py` и их
тесты. Они нужны для интеграционной проверки, но принадлежат `mysariaw` и
`weaselda`. Не копируй их вместо работы участников.

## Место обработчика в системе

```text
MCP-клиент
  → src/mcp_adapter.py проверяет типы аргументов
  → src/order_handlers.py управляет сценарием
  → src/domain.py принимает решение по бизнес-правилам
  → src/storage.py читает и атомарно изменяет SQLite
  → src/errors.py формирует единый ответ
```

Обработчик — координатор. В нём нет SQL, но именно он задаёт порядок проверок и
решает, когда разрешено вызвать запись.

## Формат ответов

Успех:

```python
{"ok": True, "data": {...}}
```

Ожидаемый отказ:

```python
{
    "ok": False,
    "error": {"code": "INSUFFICIENT_COINS", "message": "Недостаточно коинов"},
}
```

`ERROR_MESSAGES` хранит понятные тексты. Приёмка сравнивает код, но сообщение
обязательно должно быть непустым.

## `create_order`: порядок по шагам

1. `storage.get_user(user_id)` — неизвестный пользователь даёт
   `USER_NOT_FOUND`.
2. `storage.get_product(product_id)` — неизвестный товар даёт
   `PRODUCT_NOT_FOUND`.
3. `domain.calculate_total(...)` вычисляет стоимость.
4. `storage.count_owned(...)` сообщает уже занятое количество лимита.
5. `domain.purchase_error(...)` проверяет остаток, лимит и баланс именно в этом
   порядке.
6. При коде ошибки обработчик сразу возвращает `failure`; база не меняется.
7. Только после всех проверок вызывается `storage.create_order(...)`.
8. Клиент получает только публичные поля `order_id`, `status`, `total_price`.

Пользователь проверяется раньше товара. Поэтому запрос с одновременно
неизвестным пользователем и товаром должен вернуть `USER_NOT_FOUND`.

Транзакция находится не в обработчике, а в `Storage.create_order`: заказ,
баланс и остаток либо изменяются вместе, либо вместе откатываются.

## `cancel_order`

1. Получить заказ через `storage.get_order`.
2. Если его нет — `ORDER_NOT_FOUND`.
3. Проверить `domain.can_cancel(order)`.
4. Неверное состояние — `ORDER_STATUS_ERROR` без изменений базы.
5. Рассчитать возврат через `domain.refund_amount(order["total_price"])`.
6. Передать заказ и сумму в атомарный `storage.cancel_order`.

Важно использовать сохранённый `total_price`, а не текущую цену товара. После
успешной отмены статус становится `cancelled`, поэтому повторный вызов
останавливается до записи и не возвращает коины второй раз.

## `confirm_pickup`

Логика похожа на отмену, но после проверки состояния вызывается только
`storage.confirm_pickup`. Выдача не списывает коины и товар: они уже были
списаны при создании. Успешный статус — `picked_up`.

## Машина состояний

```text
created ── cancel_order ──> cancelled
   │
   └──── confirm_pickup ──> picked_up

cancelled и picked_up — конечные состояния
```

Любое повторное действие над конечным состоянием возвращает
`ORDER_STATUS_ERROR` и не меняет таблицы.

## Что проверяет `testing/test_orders.py`

- успешную покупку и три связанных изменения;
- приоритет неизвестного пользователя над неизвестным товаром;
- неизвестный товар;
- `OUT_OF_STOCK`, `USER_LIMIT_EXCEEDED`, `INSUFFICIENT_COINS`;
- полную неизменность всех таблиц после отказа;
- однократную отмену и повторную отмену;
- выдачу без повторного списания;
- невозможность отменить выданный заказ;
- неизвестный заказ для отмены и выдачи.

Тест `table_state` снимает содержимое `products`, `stock`, `users`, `orders` до
вызова и сравнивает его после отказа. Проверки одного кода ошибки недостаточно:
ошибочный сервер мог вернуть правильный текст уже после частичной записи.

## Как перенести участок в учебный GitLab

Из корня командного проекта:

```bash
git switch develop
git pull --ff-only origin develop
git switch -c feature/order-handlers
```

Если ветка уже существует:

```bash
git switch feature/order-handlers
```

Скопируй из ветки `develop` этого репозитория только:

- `src/order_handlers.py`;
- `testing/test_orders.py`.

Не копируй `README_MOTHMANE.md`, `domain.py` или `storage.py` в сдаваемый проект.

Запусти:

```bash
python3 check_environment.py
python3 -m pytest -q
python3 client.py scenario
python3 checks/acceptance.py --project . --profile base
grep -nE "TODO|NotImplementedError|sqlite3|SELECT|INSERT|UPDATE|DELETE" src/order_handlers.py
git diff --check
git status --short
```

`grep` не должен ничего вывести. Если полная приёмка падает до объединения
чужих участков, сначала убедись, что проходят именно `testing/test_orders.py`.

После проверки:

```bash
git add src/order_handlers.py testing/test_orders.py
git commit -m "Implement order handlers and scenario tests"
git push -u origin feature/order-handlers
```

Передай `jessblaz` название ветки, хеш `git log -1 --oneline` и вывод тестов.

## Интерфейсы зависимостей

Обработчик ожидает:

```text
Storage.get_user(user_id) -> dict | None
Storage.get_product(product_id) -> dict | None
Storage.count_owned(user_id, product_id) -> int
Storage.create_order(...) -> dict заказа
Storage.get_order(order_id) -> dict | None
Storage.cancel_order(order, refund) -> dict заказа
Storage.confirm_pickup(order_id) -> dict заказа

domain.calculate_total(price, quantity) -> int
domain.purchase_error(...) -> код | None
domain.refund_amount(total_price) -> int
domain.can_cancel(order) -> bool
domain.can_pickup(order) -> bool
```

Если формы отличаются, не исправляй молча чужой файл — согласуй интерфейс с
`weaselda`, `mysariaw` и тимлидом.

## Что объяснить на защите

1. Почему пользователь проверяется раньше товара.
2. Где заканчивается обработчик и начинается бизнес-правило.
3. Почему запись вызывается только после всех отказов.
4. Где находится транзакция покупки и почему не в обработчике.
5. Почему повторная отмена не возвращает коины второй раз.
6. Почему выдача не меняет баланс и остаток.
7. Как тест доказывает неизменность базы после отказа.
8. Почему клиент получает публичные поля, а не всю строку базы.

## Чек-лист готовности

- [ ] Реализованы `create_order`, `cancel_order`, `confirm_pickup`.
- [ ] В обработчиках нет SQL.
- [ ] Порядок отказов соответствует `materials/lavka_rules.md`.
- [ ] Отказ происходит до записи.
- [ ] Повторные действия возвращают `ORDER_STATUS_ERROR`.
- [ ] Собственные тесты проходят.
- [ ] `client.py scenario` проходит.
- [ ] Приёмка `base` завершается `PASS`.
- [ ] В коммит не попали базы, `.venv`, `.idea` и кэши.
- [ ] Ветка отправлена в GitLab и передана тимлиду.
