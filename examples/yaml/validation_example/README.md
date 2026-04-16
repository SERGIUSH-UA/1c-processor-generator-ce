# Приклад розширеної BSL валідації (v2.12.0+)

Цей приклад демонструє використання нової секції `validation:` в YAML конфігурації для налаштування перевірки BSL коду через 1C Designer.

## Що нового в v2.12.0?

### 1. Секція `validation:` в YAML

```yaml
validation:
  # CheckModules (синтаксична перевірка)
  check_modules_enabled: true
  check_web_client: true  # 🆕 Нова перевірка

  # CheckConfig (семантична перевірка) - 🆕 НОВА МОЖЛИВІСТЬ!
  check_config_enabled: true
  check_incorrect_references: true
  check_handlers_existence: true
  check_empty_handlers: true
  check_extended_modules: true
```

### 2. Два типи валідації

| Тип | Команда Designer | Що перевіряє | Швидкість |
|-----|------------------|--------------|-----------|
| **CheckModules** | `/CheckModules` | Синтаксис BSL для різних режимів клієнта | Швидко (~5-10 сек) |
| **CheckConfig** | `/CheckConfig` | Семантика: посилання, обробники, типи | Повільніше (~15-30 сек) |

## Як згенерувати

```bash
# Генерація XML з валідацією (тільки /CheckModules за замовчуванням)
python -m 1c_processor_generator yaml --config config.yaml --handlers-file handlers.bsl

# Генерація EPF з повною валідацією (/CheckModules + /CheckConfig)
python -m 1c_processor_generator yaml --config config.yaml --handlers-file handlers.bsl --output-format epf
```

## Структура файлів

```
validation_example/
├── config.yaml         # Конфігурація з секцією validation
├── handlers.bsl        # BSL код з обробниками
└── README.md           # Цей файл
```

## Що перевіряється

### CheckModules (Step 4.5)
✅ Синтаксичні помилки BSL
✅ Невідомі методи/функції
✅ Неправильні параметри
✅ Для режимів: ThinClient, Server, WebClient (якщо `check_web_client: true`)

### CheckConfig (Step 4.6) - 🆕
✅ Некоректні посилання на видалені форми/об'єкти (`check_incorrect_references`)
✅ Існування назначених обробників (`check_handlers_existence`)
✅ Пусті обробники, які знижують продуктивність (`check_empty_handlers`)
✅ Невикористовувані процедури/функції (`check_unreference_procedures`)
✅ Розширена перевірка типів "через точку" (`check_extended_modules`)

## Приклад виводу

```
⚙️ Step 4.5/6: Checking BSL modules syntax...
✓ BSL modules validation passed

⚙️ Step 4.6/6: Running semantic checks (/CheckConfig)...
✓ Semantic validation passed (/CheckConfig)

⚙️ Step 5/6: Preparing ExternalDataProcessor with cfg: prefixes...
⚙️ Step 6/6: Loading EPF with cfg: prefixes...
✓ EPF створено: ПрикладВалідації.epf
```

## Налаштування валідації

### Мінімальна валідація (за замовчуванням)
Якщо секція `validation:` відсутня - використовується тільки базовий `/CheckModules`:

```yaml
processor:
  name: МояОбробка
# validation секція відсутня = тільки ThinClient + Server
```

### Розширена валідація
Додайте секцію `validation:` для повного контролю:

```yaml
validation:
  check_config_enabled: true  # Увімкнути /CheckConfig
  check_web_client: true      # Додати перевірку для WebClient
```

### Максимальна валідація
Увімкніть всі можливі перевірки:

```yaml
validation:
  # CheckModules - всі режими
  check_thin_client: true
  check_server: true
  check_web_client: true
  check_external_connection: true
  check_thick_client: true

  # CheckConfig - всі перевірки
  check_config_enabled: true
  check_incorrect_references: true
  check_handlers_existence: true
  check_empty_handlers: true
  check_unreference_procedures: true
  check_extended_modules: true
```

## Ігнорування помилок валідації

Якщо потрібно згенерувати EPF навіть при наявності помилок валідації:

```bash
python -m 1c_processor_generator yaml \
  --config config.yaml \
  --handlers-file handlers.bsl \
  --output-format epf \
  --ignore-validation-errors
```

⚠️ **Увага:** Використовуйте `--ignore-validation-errors` тільки для тестування!

## Дивіться також

- **docs/VALIDATION_GUIDE.md** - Повний гід по валідації
- **examples/yaml/simple_role_setter/** - Базовий приклад без валідації
- **CHANGELOG.md** - Історія змін (v2.12.0)
