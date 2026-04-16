# BSL Validation Guide (v2.12.0+)

Повний гід по валідації BSL коду через 1C Designer в процесі генерації зовнішніх обробок.

## Зміст

- [Огляд](#огляд)
- [Швидкий старт](#швидкий-старт)
- [Типи валідації](#типи-валідації)
- [Налаштування через YAML](#налаштування-через-yaml)
- [Параметри валідації](#параметри-валідації)
- [Приклади використання](#приклади-використання)
- [Поширені помилки](#поширені-помилки)
- [FAQ](#faq)

---

## Огляд

Починаючи з версії **v2.12.0**, генератор підтримує розширену валідацію BSL коду через 1C Designer з можливістю налаштування через YAML.

### Що валідується?

1. **CheckModules** (Step 4.5) - Синтаксична перевірка
   - Синтаксичні помилки BSL
   - Невідомі методи/функції
   - Неправильні параметри
   - Для різних режимів клієнта (ThinClient, Server, WebClient, тощо)

2. **CheckConfig** (Step 4.6) - Семантична перевірка 🆕
   - Некоректні посилання на видалені об'єкти/форми
   - Існування назначених обробників
   - Пусті обробники (знижують продуктивність)
   - Невикористовувані процедури/функції
   - Розширена перевірка типів "через точку"

### Коли виконується валідація?

Валідація виконується **автоматично** при генерації EPF через `--output-format epf`:

```
Step 4.5: CheckModules (/CheckModules)  ← Завжди (якщо не вимкнено)
Step 4.6: CheckConfig (/CheckConfig)    ← Тільки якщо check_config_enabled: true
```

⚠️ **ВАЖЛИВО:** Валідація працює **ТІЛЬКИ** при генерації EPF (`--output-format epf`) в **Configuration mode**, який активується автоматично коли:
1. Обробка містить метадані (CatalogRef, DocumentRef), АБО
2. Налаштована валідація в YAML (секція `validation:` з `check_modules_enabled: true` або `check_config_enabled: true`)

При генерації XML (`--output-format xml` або відсутність `--output-format epf`) валідація НЕ виконується.

---

## Швидкий старт

### Базова валідація (за замовчуванням)

Без секції `validation:` використовується мінімальна перевірка:

```yaml
processor:
  name: МояОбробка
  # ... інші поля ...

# validation: відсутня - мінімальна валідація
```

**Що перевіряється:**
- ✅ CheckModules: ThinClient + Server
- ❌ CheckConfig: вимкнений

### Розширена валідація

Додайте секцію `validation:` для повного контролю:

```yaml
processor:
  name: МояОбробка

validation:
  check_config_enabled: true     # Увімкнути семантичну перевірку
  check_web_client: true         # Додати перевірку для WebClient
  check_extended_modules: true   # Розширена перевірка типів
```

**Що перевіряється:**
- ✅ CheckModules: ThinClient + Server + WebClient
- ✅ CheckConfig: Некоректні посилання, обробники, типи

---

## Типи валідації

### 1. CheckModules (Синтаксична перевірка)

**Команда Designer:** `/CheckModules`
**Швидкість:** ~5-10 секунд
**Обов'язковість:** За замовчуванням увімкнена

**Що перевіряє:**
- Синтаксичні помилки BSL (пропущені крапки з комою, помилкові оператори)
- Невідомі методи та функції
- Неправильна кількість/тип параметрів
- Помилки компіляції для різних режимів клієнта

**Параметри режимів клієнта:**

| Параметр | Designer флаг | За замовчуванням | Опис |
|----------|---------------|------------------|------|
| `check_thin_client` | `-ThinClient` | `true` | Тонкий клієнт |
| `check_server` | `-Server` | `true` | Сервер 1С |
| `check_web_client` | `-WebClient` | `false` 🆕 | Веб-клієнт |
| `check_external_connection` | `-ExternalConnection` | `false` 🆕 | Зовнішнє з'єднання |
| `check_thick_client` | `-ThickClientOrdinaryApplication` | `false` 🆕 | Товстий клієнт |

### 2. CheckConfig (Семантична перевірка) 🆕

**Команда Designer:** `/CheckConfig`
**Швидкість:** ~15-30 секунд (повільніше ніж CheckModules)
**Обов'язковість:** За замовчуванням **вимкнена** (opt-in)

**Що перевіряє:**
- Некоректні посилання (форми, команди, реквізити, які не існують)
- Існування призначених обробників подій
- Пусті обробники (можуть знижувати продуктивність)
- Невикористовувані процедури/функції (мертвий код)
- Розширена перевірка методів/властивостей "через точку"

**Параметри перевірок:**

| Параметр | Designer флаг | За замовчуванням | Опис |
|----------|---------------|------------------|------|
| `check_config_enabled` | - | `false` | **Головний перемикач** для /CheckConfig |
| `check_incorrect_references` | `-IncorrectReferences` | `true` | Некоректні посилання |
| `check_handlers_existence` | `-HandlersExistence` | `true` | Існування обробників |
| `check_empty_handlers` | `-EmptyHandlers` | `true` | Пусті обробники |
| `check_unreference_procedures` | `-UnreferenceProcedures` | `false` | Невикористовувані процедури (повільно) |
| `check_extended_modules` | `-ExtendedModulesCheck` | `true` | Розширена перевірка типів |

---

## Налаштування через YAML

### Повна структура секції validation:

```yaml
validation:
  # ===== CheckModules (синтаксична перевірка) =====
  check_modules_enabled: true     # Увімкнути /CheckModules (default: true)
  check_thin_client: true          # -ThinClient (default: true)
  check_server: true               # -Server (default: true)
  check_web_client: false          # -WebClient (default: false)
  check_external_connection: false # -ExternalConnection (default: false)
  check_thick_client: false        # -ThickClientOrdinaryApplication (default: false)

  # ===== CheckConfig (семантична перевірка) =====
  check_config_enabled: false              # Увімкнути /CheckConfig (default: false - opt-in!)
  check_incorrect_references: true         # -IncorrectReferences (default: true)
  check_handlers_existence: true           # -HandlersExistence (default: true)
  check_empty_handlers: true               # -EmptyHandlers (default: true)
  check_unreference_procedures: false      # -UnreferenceProcedures (default: false)
  check_extended_modules: true             # -ExtendedModulesCheck (default: true)
```

### Зворотня сумісність

✅ **Якщо секція `validation:` відсутня** - використовуються значення за замовчуванням (тільки базовий CheckModules).

✅ **Існуючі YAML конфіги працюватимуть без змін** - валідація не заважатиме.

---

## Параметри валідації

### CheckModules parameters

#### `check_modules_enabled`
- **Тип:** `boolean`
- **Default:** `true`
- **Опис:** Головний перемикач для /CheckModules. Якщо `false` - синтаксична перевірка не виконується.

#### `check_thin_client`
- **Тип:** `boolean`
- **Default:** `true`
- **Designer флаг:** `-ThinClient`
- **Опис:** Перевірка BSL для режиму тонкого клієнта.

#### `check_server`
- **Тип:** `boolean`
- **Default:** `true`
- **Designer флаг:** `-Server`
- **Опис:** Перевірка BSL для режиму сервера 1С.

#### `check_web_client` 🆕
- **Тип:** `boolean`
- **Default:** `false`
- **Designer флаг:** `-WebClient`
- **Опис:** Перевірка BSL для режиму веб-клієнта. **Рекомендовано** для сучасних застосунків.

#### `check_external_connection` 🆕
- **Тип:** `boolean`
- **Default:** `false`
- **Designer флаг:** `-ExternalConnection`
- **Опис:** Перевірка BSL для режиму зовнішнього з'єднання.

#### `check_thick_client` 🆕
- **Тип:** `boolean`
- **Default:** `false`
- **Designer флаг:** `-ThickClientOrdinaryApplication`
- **Опис:** Перевірка BSL для режиму товстого клієнта (звичайне застосування).

### CheckConfig parameters

#### `check_config_enabled` 🆕
- **Тип:** `boolean`
- **Default:** `false`
- **Опис:** **Головний перемикач** для /CheckConfig. Якщо `false` - семантична перевірка не виконується (opt-in).

#### `check_incorrect_references` 🆕
- **Тип:** `boolean`
- **Default:** `true`
- **Designer флаг:** `-IncorrectReferences`
- **Опис:** Пошук посилань на видалені об'єкти, форми, команди. **Дуже корисно** для великих проектів.

#### `check_handlers_existence` 🆕
- **Тип:** `boolean`
- **Default:** `true`
- **Designer флаг:** `-HandlersExistence`
- **Опис:** Перевірка що всі назначені обробники подій існують у модулях.

#### `check_empty_handlers` 🆕
- **Тип:** `boolean`
- **Default:** `true`
- **Designer флаг:** `-EmptyHandlers`
- **Опис:** Пошук пустих обробників, які можуть знижувати продуктивність.

#### `check_unreference_procedures` 🆕
- **Тип:** `boolean`
- **Default:** `false`
- **Designer флаг:** `-UnreferenceProcedures`
- **Опис:** Пошук невикористовуваних процедур/функцій (мертвий код). **Може бути повільно** на великих проектах.

#### `check_extended_modules` 🆕
- **Тип:** `boolean`
- **Default:** `true`
- **Designer флаг:** `-ExtendedModulesCheck`
- **Опис:** Розширена перевірка обращень до методів/властивостей "через точку" (`Объект.Свойство`, `Объект.Метод()`).

---

## Приклади використання

### Приклад 1: Мінімальна валідація

```yaml
processor:
  name: ПростаОбробка

# validation: відсутня
# Використовується: CheckModules (ThinClient + Server)
```

### Приклад 2: Додавання веб-клієнта

```yaml
processor:
  name: ВебОбробка

validation:
  check_web_client: true  # Додаємо перевірку для веб-клієнта
```

### Приклад 3: Повна семантична перевірка

```yaml
processor:
  name: СкладнаОбробка

validation:
  # Увімкнути /CheckConfig
  check_config_enabled: true

  # Всі семантичні перевірки
  check_incorrect_references: true
  check_handlers_existence: true
  check_empty_handlers: true
  check_extended_modules: true
```

### Приклад 4: Максимальна валідація

```yaml
processor:
  name: ПродакшенОбробка

validation:
  # CheckModules - всі режими
  check_modules_enabled: true
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
  check_unreference_procedures: true  # Може бути повільно!
  check_extended_modules: true
```

### Приклад 5: Вимкнення валідації

```yaml
processor:
  name: ТестоваОбробка

validation:
  check_modules_enabled: false  # Вимкнути синтаксичну перевірку
  check_config_enabled: false   # Вимкнути семантичну перевірку
```

---

## Поширені помилки

### Помилка 1: "Невідомий метод"

```
CheckModules Error:
  Строка 15, Колонка 5: Неизвестный метод "НесуществующийМетод"
```

**Причина:** Виклик методу, який не існує або має помилку в назві.

**Рішення:**
- Перевірте назву методу
- Додайте відсутній метод у модуль
- Перевірте регістр (BSL регістронезалежна, але краще додержуватись конвенції)

### Помилка 2: "Некоректне посилання"

```
CheckConfig Error:
  -IncorrectReferences: Ссылка на несуществующую форму "НесуществующаяФорма"
```

**Причина:** Посилання на форму/команду/реквізит, який не існує.

**Рішення:**
- Додайте відсутню форму в YAML
- Виправте назву форми в BSL коді
- Видаліть посилання, якщо воно більше не потрібне

### Помилка 3: "Пустий обробник"

```
CheckConfig Warning:
  -EmptyHandlers: Обработчик "ПриОткрытии" пустой
```

**Причина:** Обробник події існує, але не виконує жодних дій.

**Рішення:**
- Додайте логіку в обробник
- Видаліть пустий обробник, якщо він не потрібен

---

## FAQ

### Чи працює валідація для XML формату?

**Ні.** Валідація BSL коду працює **ТІЛЬКИ** при генерації EPF (`--output-format epf`) в **Configuration mode**.

**Як активувати Configuration mode та валідацію:**

**Варіант 1: Через налаштування валідації (🆕 v2.12.0)**

Додайте секцію `validation:` в YAML з увімкненою валідацією:

```yaml
processor:
  name: МояОбробка

validation:
  check_modules_enabled: true   # Синтаксична перевірка
  check_config_enabled: true    # Семантична перевірка
```

Генерація:
```bash
python -m 1c_processor_generator yaml \
  --config config.yaml \
  --handlers-file handlers.bsl \
  --output-format epf
```

✅ **Configuration mode активується автоматично** навіть без метаданих!

**Варіант 2: Через метадані (v2.10.0+)**

Додайте хоча б один атрибут з типом CatalogRef або DocumentRef:

```yaml
attributes:
  - name: Контрагент
    type: CatalogRef.Контрагенты
```

✅ **Configuration mode активується автоматично** через наявність метаданих.

**Технічні деталі:**

При Configuration mode генератор виконує:
1. Створює тимчасову Configuration.xml з обробкою (суфікс "_Validation")
2. Завантажує Configuration в тимчасову інфобазу
3. Виконує CheckModules та CheckConfig (якщо увімкнені)
4. Якщо є метадані: продовжує з Configuration mode (використовує cfg: префікси)
5. Якщо НЕмає метаданих: після валідації створює нову чисту інфобазу та компілює EPF без Configuration (швидше, немає cfg: префіксів)

**Чому раніше потрібні були метадані:**
- Швидкий режим (`compile_epf`) компілює XML напряму без створення Configuration
- Configuration mode (`compile_epf_with_configuration`) створює тимчасову конфігурацію і виконує валідацію

**Що змінилось в v2.12.0:**
- Configuration mode активується також при наявності `validation:` секції, навіть без метаданих
- Після валідації для обробок без метаданих використовується швидка компіляція через чисту базу

### Чи обов'язкова валідація?

**Ні.** За замовчуванням валідація увімкнена тільки для мінімального набору (CheckModules: ThinClient + Server). CheckConfig вимкнений за замовчуванням (opt-in).

### Як вимкнути валідацію?

```yaml
validation:
  check_modules_enabled: false
  check_config_enabled: false
```

Або використайте CLI параметр:

```bash
--ignore-validation-errors  # Продовжити навіть при помилках
```

### Чи можна ігнорувати помилки валідації?

**Так**, але не рекомендовано для production:

```bash
python -m 1c_processor_generator yaml \
  --config config.yaml \
  --handlers-file handlers.bsl \
  --output-format epf \
  --ignore-validation-errors
```

### Які параметри слід увімкнути для production?

Мінімум:

```yaml
validation:
  check_web_client: true           # Якщо використовується веб-клієнт
  check_config_enabled: true       # Семантична перевірка
  check_incorrect_references: true # Некоректні посилання
  check_handlers_existence: true   # Існування обробників
  check_empty_handlers: true       # Пусті обробники
```

### Скільки часу займає валідація?

- **CheckModules:** ~5-10 секунд
- **CheckConfig:** ~15-30 секунд (залежить від розміру проекту)

Сумарно: **~20-40 секунд** для повної валідації.

### Чи впливає валідація на згенерований EPF?

**Ні.** Валідація тільки перевіряє BSL код, але не змінює його. EPF генерується незалежно від результатів валідації (якщо не використовується `--ignore-validation-errors`).

---

## Дивіться також

- **examples/yaml/validation_example/** - Повний приклад з валідацією
- **CHANGELOG.md** - Історія змін (v2.12.0)
- **README.md** - Основна документація проекту
- **docs/EPF_SYNTAX_VALIDATION_RESEARCH.md** - Дослідження підходів до валідації

---

**Версія:** v2.12.0
**Дата:** 2025-10-18
