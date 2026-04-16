# YAML API Guide для генератора зовнішніх обробок 1C

Посібник по використанню YAML конфігурації для створення зовнішніх обробок 1C:Enterprise 8.3.

## 📋 Зміст

- [Навіщо YAML API?](#навіщо-yaml-api)
- [Швидкий старт](#швидкий-старт)
- [Структура YAML файлу](#структура-yaml-файлу)
- [BSL Handlers](#bsl-handlers)
- [Приклади](#приклади)
- [Довідник](#довідник)

---

## Навіщо YAML API?

### Проблема з Python API

**Без YAML:**
```python
# ЛЛМ генерує Python код - схильний до помилок
processor = Processor(name="МояОбробка", ...)
processor.add_attribute("Пользователь", type="CatalogRef.Пользователи")
# ... багато коду з ризиком помилок
```

**З YAML:**
```yaml
# Декларативна конфігурація - простіше для ЛЛМ
processor:
  name: МояОбробка

attributes:
  - name: Пользователь
    type: CatalogRef.Пользователи
```

### Переваги YAML API

✅ **Для ЛЛМ (Claude, GPT):**
- Декларативний синтаксис (простіший за Python)
- Менше можливостей для помилок
- Валідація через JSON Schema
- Фокус на структурі, а не на деталях реалізації

✅ **Для розробників:**
- BSL логіка в окремих файлах (легше читати)
- Легко версіонувати в git
- Зрозуміла структура обробки з першого погляду

✅ **Технічні переваги:**
- Автоматична генерація UUID
- Автоматична нумерація ID
- Валідація структури перед генерацією

---

## Швидкий старт

### 1. Створіть структуру проекту

```
my_processor/
├── config.yaml       # YAML конфігурація
└── handlers/         # BSL обробники (опціонально)
    ├── ПриОткрытии.bsl
    └── МояКоманда.bsl
```

### 2. Напишіть config.yaml

```yaml
processor:
  name: МояОбробка
  synonym_ru: Моя обработка
  synonym_uk: Моя обробка

attributes:
  - name: ТекстовоеПоле
    type: string
    length: 100

forms:
  - name: Форма
    default: true
    elements:
      - type: InputField
        name: ТекстовоеПоле
        attribute: ТекстовоеПоле
```

### 3. Згенеруйте обробку

```bash
python -m 1c_processor_generator yaml \
  --config my_processor/config.yaml \
  --handlers my_processor/handlers/
```

### 4. Відкрийте в 1C

```
Файл → Відкрити → МояОбробка/МояОбробка.xml
```

---

## ⚠️ КРИТИЧНО ВАЖЛИВО: Обмеження кирилиці

**Генератор підтримує ТІЛЬКИ російську кирилицю!**

**Підтримувані символи:** а-я, А-Я, ё, Ё, a-z, A-Z, 0-9, _

**НЕ підтримується (українська кирилиця):** і, ї, є, ґ, І, Ї, Є, Ґ

Це обмеження платформи 1C (regex валідації ідентифікаторів: `^[а-яА-ЯёЁa-zA-Z_][а-яА-ЯёЁa-zA-Z0-9_]*$`)

❌ **НЕПРАВИЛЬНО (українська кирилиця):**
```yaml
processor:
  name: ПошукDuckDuckGo  # 'о' українська!

attributes:
  - name: ПошуковийЗапит  # 'і' українська!
  - name: ШляхДоФайлу     # українське слово
```

✅ **ПРАВИЛЬНО (російська кирилиця):**
```yaml
processor:
  name: ПоискDuckDuckGo  # 'о' російська!

attributes:
  - name: ПоисковыйЗапрос  # 'и' російська!
  - name: ПутьКФайлу       # російський еквівалент
```

**Візуально схожі, але РІЗНІ літери:**
- і (українська U+0456) ≠ и (російська U+0438)
- ї (українська U+0457) ≠ й (російська U+0439)
- є (українська U+0454) ≠ е (російська U+0435)
- ґ (українська U+0491) ≠ г (російська U+0433)

**Де українська ДОЗВОЛЕНА:**
- ✅ Синоніми: `synonym_uk: "Пошуковий запит"` - OK!
- ✅ Рядки в BSL: `Сообщить("Пошук завершено")` - OK!
- ✅ Коментарі: `// Український коментар` - OK!

**Де українська ЗАБОРОНЕНА:**
- ❌ Назви процесорів, атрибутів, команд, обробників
- ❌ Будь-які ідентифікатори що стають іменами метаданих 1C

**Для українських розробників:**
Використовуйте російську кирилицю для ВСІХ ідентифікаторів, але українську можна використовувати в user-facing тексті.

---

## Структура YAML файлу

### Мінімальна конфігурація

```yaml
processor:
  name: МінімальнаОбробка  # ⚠️ Тільки російська кирилиця!
```

Це найпростіша валідна конфігурація. Згенерує пусту обробку з формою.

### Compact Multilang Syntax (v2.69.0+)

Підтримуються **три еквівалентні формати** для локалізованих полів (`title`, `synonym`, `tooltip`, `input_hint`, `presentation`, `progress_message`).

**ВАЖЛИВО:** На початку config.yaml потрібно вказати `languages:`:
```yaml
languages: [ru, uk, en]  # Визначає порядок мов для pipe/array форматів
```

#### Формат 1: Pipe String (рекомендований, v2.69.0+)

Найкомпактніший формат - одна мова розділена символом `|`:

```yaml
languages: [ru, uk, en]

processor:
  name: МояОбробка
  synonym: "Моя обработка | Моя обробка | My Processor"

forms:
  - name: Форма
    default: true
    properties:
      title: "Калькулятор | Калькулятор | Calculator"
    commands:
      - name: Выполнить
        title: "Выполнить | Виконати | Execute"
        handler: Выполнить
```

**Переваги:** Максимальна компактність (~67% менше рядків), легко читається.

#### Формат 2: Dict (explicit keys)

Явне вказування ключів мов:

```yaml
processor:
  name: МояОбробка
  synonym:
    ru: Моя обработка
    uk: Моя обробка
    en: My Processor

commands:
  - name: Выполнить
    title:
      ru: Выполнить
      uk: Виконати
      en: Execute
```

**Переваги:** Самодокументований, не залежить від порядку `languages:`.

#### Формат 3: Array (positional)

Масив значень у порядку `languages:`:

```yaml
languages: [ru, uk, en]

processor:
  name: МояОбробка
  synonym: ["Моя обработка", "Моя обробка", "My Processor"]
```

**Переваги:** Компактний для inline використання.

#### Формат 4: Flat Suffix (legacy, backward compatible)

```yaml
processor:
  name: МояОбробка
  synonym_ru: Моя обработка
  synonym_uk: Моя обробка
  synonym_en: My Processor
```

**Використання:** Тільки для сумісності зі старими файлами.

#### Smart Fallback

Якщо вказано менше значень ніж мов, використовується перша (основна) мова:

```yaml
languages: [ru, uk, en]

# Двомовне значення → en отримує значення ru
synonym: "Калькулятор | Калькулятор"  # en = "Калькулятор"

# Одномовне значення → всі мови отримують це значення
title: "Заголовок"  # ru, uk, en = "Заголовок"
```

#### choice_list: Inline Dict Format

Для `choice_list` рекомендується inline dict формат:

```yaml
choice_list:
  - v: "Production"
    presentation: {ru: "Продакшн", uk: "Продакшн", en: "Production"}
  - v: "Staging"
    presentation: {ru: "Стейджинг", uk: "Стейджинг", en: "Staging"}
```

> 💡 **Рекомендація:** Використовуйте pipe формат для нових проектів - це найкомпактніший варіант.

### Повна структура

```yaml
# Метадані обробки
processor:
  name: string              # Обов'язкове
  synonym_ru: string
  synonym_uk: string
  platform_version: "2.11"  # За замовчуванням 2.11
                             # Підтримуються: 2.10, 2.11, 2.18, 2.19, тощо
                             # Використовуйте версію сумісну з вашою платформою 1C

# Атрибути об'єкта обробки
attributes:
  - name: string
    type: string            # string, boolean, number, date, CatalogRef.*, etc.
    synonym_ru: string
    synonym_uk: string
    length: number          # Для string
    digits: number          # Для number
    fraction_digits: number # Для number

# Табличні частини (об'єктні)
tabular_sections:
  - name: string
    synonym_ru: string
    synonym_uk: string
    columns:
      - name: string
        type: string
        # ... як у attributes

# ValueTable атрибути (всередині форми!)
# value_tables: ... - див. forms[].value_tables

# ValueTree атрибути (всередині форми!) - v2.64.0+
# value_trees: ... - див. forms[].value_trees

# DynamicList атрибути (всередині форми!)
# dynamic_lists: ... - див. forms[].dynamic_lists

**DynamicListParameter:**
```yaml
parameters:
  - name: StartDate
    type: Date
    default_value: "2025-01-01"
```

**Typical usage with parameters:**
```yaml
dynamic_lists:
  - name: FilteredOrders
    title_ru: "Отфильтрованные заказы"
    manual_query: true
    query_text: |
      SELECT
        Ссылка,
        Номер,
        Дата
      FROM
        Document.Заказ
      WHERE
        Дата >= &StartDate
    parameters:
      - name: StartDate
        type: Date
    functional_options: ["UseAdvancedFilters"]
    auto_save_user_settings: true
```

# Налаштування форми (новий формат forms:)
forms:
  - name: string              # Ім'я форми (Форма за замовчуванням)
    default: boolean          # true = форма за замовчуванням

    properties:
      title: boolean
      title_ru: string
      title_uk: string
      auto_title: boolean

    events:
      OnOpen: string          # Ім'я обробника → handlers/ПриОткрытии.bsl
      OnCreateAtServer: string
      OnClose: string
      BeforeClose: string

    # ValueTable атрибути (формові)
    value_tables:
      - name: string
        columns:
          - name: string
            type: string

    # ValueTree атрибути (формові) - v2.64.0+
    value_trees:
      - name: string
        title_ru: string
        title_uk: string
        title_en: string
        columns:
          - name: string
            type: string

    # DynamicList атрибути (формові)
    dynamic_lists:
      - name: string
        manual_query: boolean
        main_table: string
        query_text: string

    elements:
      - type: InputField|LabelField|Table|Button|UsualGroup|Pages
        name: string
        # ... специфічні властивості

    # Команди форми (всередині форми!)
    commands:
      - name: string
        title_ru: string
        title_uk: string
        handler: string         # Ім'я обробника → handlers/Команда.bsl
        tooltip_ru: string
        tooltip_uk: string
        picture: string         # StdPicture.* або CommonPicture.*
        shortcut: string        # F5, Ctrl+S, тощо
```

---

## BSL Handlers

### Структура handlers/

```
handlers/
├── ПриОткрытии.bsl              # События форми
├── ПриОткрытииНаСервере.bsl     # Серверні частини
├── МояКоманда.bsl               # Команди
├── МояКомандаНаСервере.bsl      # Серверні частини команд
└── ПолеПриИзменении.bsl         # Події елементів
```

### Формат BSL файлів

**ВАЖЛИВО:** Файли містять **ТІЛЬКИ тіло процедури**, без сигнатури!

**❌ Неправильно:**
```bsl
&НаКлиенте
Процедура ПриОткрытии(Отказ)
    Сообщить("Форма открыта");
КонецПроцедуры
```

**✅ Правильно:**
```bsl
Сообщить("Форма открыта");
```

Генератор **автоматично** додасть сигнатуру.

### ⚠️ ВАЖЛИВО: Зарезервовані слова BSL

**Імена обробників НЕ можуть бути зарезервованими словами BSL!**

Генератор автоматично перевіряє імена обробників (commands.handler, form.events, elements.events) і заблокує генерацію якщо використовується зарезервоване слово.

**❌ Заборонені імена (40+ зарезервованих слів):**
- **КРИТИЧНО:** `Выполнить`, `Вычислить`, `Execute`, `Eval` - системні функції
- `Экспорт`, `Импорт`, `Export` - модифікатори
- `Процедура`, `Функция`, `Procedure`, `Function` - структура
- `Перем`, `Var`, `Знач`, `Val` - ключові слова
- Та інші... (повний список в `constants.BSL_RESERVED_KEYWORDS`)

**✅ Правильно:**
```yaml
commands:
  - name: Выполнить
    handler: ВыполнитьОбработку  # ✅ OK
  - name: Экспорт
    handler: ЭкспортДанных        # ✅ OK
  - name: Импорт
    handler: ИмпортДанных         # ✅ OK
```

**❌ Неправильно:**
```yaml
commands:
  - name: Выполнить
    handler: Выполнить  # ❌ ПОМИЛКА: зарезервоване слово BSL!
```

**Рекомендовані суфікси для імен:**
- `КомандаВыполнить`, `ВыполнитьКоманда` - додати "Команда"
- `ВыполнитьОбработку` - додати контекст
- `ВыполнитьОбработчик` - додати "Обработчик"

### Автоматичні серверні виклики

**Конфігурація:**
```yaml
forms:
  - name: Форма
    default: true
    events:
      OnOpen: ПриОткрытии  # handlers/ПриОткрытии.bsl
```

**Якщо існує handlers/ПриОткрытииНаСервере.bsl**, генератор автоматично:

```bsl
&НаКлиенте
Процедура ПриОткрытии(Отказ)
    ПриОткрытииНаСервере();  # ← Автоматично додано
КонецПроцедуры

&НаСервере
Процедура ПриОткрытииНаСервере()
    # ← Код з handlers/ПриОткрытииНаСервере.bsl
КонецПроцедуры
```

### Команди з серверною частиною

**Структура:**
```
handlers/
├── ВыполнитьРасчет.bsl          # Клієнтська частина
└── ВыполнитьРасчетНаСервере.bsl # Серверна частина
```

**ВыполнитьРасчет.bsl:**
```bsl
Если НЕ ЗначениеЗаполнено(Объект.Дата) Тогда
    Сообщить("Укажите дату!");
    Возврат;
КонецЕсли;

ВыполнитьРасчетНаСервере();  # Виклик серверної процедури
```

**ВыполнитьРасчетНаСервере.bsl:**
```bsl
# Тільки тіло - без параметрів!
Результат = РасчетнаяФункция(Объект.Дата);
Объект.Результат = Результат;
Сообщить("Расчет выполнен: " + Результат);
```

**Згенерується:**
```bsl
&НаКлиенте
Процедура ВыполнитьРасчет(Команда)
    # ... клієнтський код
КонецПроцедуры

&НаСервере
Процедура ВыполнитьРасчетНаСервере()
    # ... серверний код
КонецПроцедуры
```

---

## Приклади

### Приклад 1: Проста форма з полями

```yaml
processor:
  name: АнкетаПользователя
  synonym_ru: Анкета пользователя
  synonym_uk: Анкета користувача

attributes:
  - name: ФИО
    type: string
    length: 150
    synonym_ru: ФИО
    synonym_uk: ПІБ

  - name: ДатаРождения
    type: date
    synonym_ru: Дата рождения
    synonym_uk: Дата народження

  - name: Активен
    type: boolean
    synonym_ru: Активен
    synonym_uk: Активний

forms:
  - name: Форма
    default: true
    properties:
      title: true
      title_ru: Заполнение анкеты
      title_uk: Заповнення анкети
    elements:
      - type: InputField
        name: ФИОПоле
        attribute: ФИО
      - type: InputField
        name: ДатаРожденияПоле
        attribute: ДатаРождения
      - type: InputField
        name: АктивенПоле
        attribute: Активен
```

### Приклад 2: Таблиця з ValueTable

```yaml
processor:
  name: СписокТоваров

forms:
  - name: Форма
    default: true
    value_tables:
      - name: Товары
        title_ru: Товары
        title_uk: Товари
        columns:
          - name: Наименование
            type: string
            length: 200
          - name: Количество
            type: number
            digits: 10
            fraction_digits: 2
          - name: Цена
            type: number
            digits: 15
            fraction_digits: 2
    elements:
      - type: Table
        name: ТоварыТаблица
        tabular_section: Товары
        is_value_table: true  # ← ValueTable (не TabularSection)
```

### Приклад 2.5: Дерево з ValueTree (v2.64.0+)

```yaml
processor:
  name: ПримерДерева

forms:
  - name: Форма
    default: true
    value_trees:
      - name: ДеревоДанных
        title_ru: Дерево данных
        title_uk: Дерево даних
        columns:
          - name: Наименование
            type: string
          - name: Значение
            type: string
          - name: Тип
            type: string
            length: 50
          - name: ЕстьПодчиненные
            type: boolean
    elements:
      - type: Table
        name: ДеревоТаблица
        tabular_section: ДеревоДанных
        representation: tree              # ← Режим відображення дерева
        initial_tree_view: expand_top_level  # ← Початковий стан
        show_root: false
        columns:
          - name: Наименование
          - name: Значение
          - name: Тип
    commands:
      - name: Обновить
        title_ru: Обновить дерево
        handler: Обновить
        picture: StdPicture.Refresh
        shortcut: F5
```

**BSL Handlers (handlers.bsl):**
```bsl
#Область ОбработчикиКомандФормы

&НаКлиенте
Процедура Обновить(Команда)
    ОбновитьНаСервере();
КонецПроцедуры

&НаСервере
Процедура ОбновитьНаСервере()
    ЗаполнитьДеревоПримером();
КонецПроцедуры

#КонецОбласти

#Область СлужебныеПроцедурыИФункции

&НаСервере
Процедура ЗаполнитьДеревоПримером()
    ДеревоДанных.ПолучитьЭлементы().Очистить();

    // Корневой узел
    Настройки = ДеревоДанных.ПолучитьЭлементы().Добавить();
    Настройки.Наименование = "Настройки";
    Настройки.Тип = "Объект";
    Настройки.ЕстьПодчиненные = Истина;

    // Дочерний узел
    БД = Настройки.ПолучитьЭлементы().Добавить();
    БД.Наименование = "База данных";
    БД.Тип = "Объект";

    // Листовой узел
    Хост = БД.ПолучитьЭлементы().Добавить();
    Хост.Наименование = "Хост";
    Хост.Значение = "localhost";
    Хост.Тип = "Значение";
КонецПроцедуры

#КонецОбласти
```

**Tree Properties:**
| Property | Values | Description |
|----------|--------|-------------|
| `representation` | `list`, `tree` | Table display mode (default: list) |
| `initial_tree_view` | `no_expand`, `expand_top_level`, `expand_all_levels` | Initial tree expansion |
| `show_root` | `true`, `false` | Show root element |
| `allow_root_choice` | `true`, `false` | Allow selecting root |
| `choice_folders_and_items` | `folders`, `items`, `folders_and_items` | Selection mode |

### Приклад 3: Кнопки та команди

```yaml
processor:
  name: УправлениеДанными

forms:
  - name: Форма
    default: true
    commands:
      - name: Обновить
        title_ru: Обновить
        title_uk: Оновити
        handler: ОбновитьДанные
        picture: StdPicture.Refresh
        shortcut: F5
      - name: Сохранить
        title_ru: Сохранить
        title_uk: Зберегти
        handler: СохранитьДанные
        picture: StdPicture.Write
        shortcut: Ctrl+S
      - name: ЗакрытьФорму
        title_ru: Закрыть
        title_uk: Закрити
        handler: ЗакрытьФорму
    elements:
      # Горизонтальна група з кнопками
      - type: UsualGroup
        name: ГруппаКнопок
        group_direction: Horizontal
        child_items:
          - type: Button
            name: ОбновитьКнопка
            command: Обновить
          - type: Button
            name: СохранитьКнопка
            command: Сохранить
          - type: Button
            name: ЗакрытьКнопка
            command: ЗакрытьФорму
```

**handlers/Сохранить.bsl:**
```bsl
Если НЕ ЗначениеЗаполнено(Объект.Наименование) Тогда
    Сообщить("Заполните наименование!");
    Возврат;
КонецЕсли;

СохранитьДанныеНаСервере();
```

**handlers/СохранитьДанныеНаСервере.bsl:**
```bsl
# Логіка збереження на сервері
Попытка
    # Ваша логіка збереження
    Сообщить("Данные сохранены успешно!");
Исключение
    Сообщить("Ошибка сохранения: " + ОписаниеОшибки());
КонецПопытки;
```

### Приклад 4: Вкладки (Pages)

```yaml
processor:
  name: МногостраничнаяФорма

forms:
  - name: Форма
    default: true
    elements:
      - type: Pages
        name: Страницы
        pages_representation: TabsOnTop  # TabsOnTop | TabsOnBottom | None
        pages:
          - name: ОсновныеДанные
            title: Основные данные
            child_items:
              - type: InputField
                name: Наименование
                attribute: Наименование
          - name: Дополнительно
            title: Дополнительно
            child_items:
              - type: InputField
                name: Комментарий
                attribute: Комментарий
```

### Приклад 5: Довідникові типи

```yaml
processor:
  name: ВыборОбъектов

attributes:
  # Конкретний довідник
  - name: Пользователь
    type: CatalogRef.Пользователи
  # Конкретний документ
  - name: Документ
    type: DocumentRef.РеализацияТоваровУслуг
  # Загальний тип (будь-який довідник)
  - name: ЛюбойСправочник
    type: CatalogRef
  # Загальний тип (будь-який документ)
  - name: ЛюбойДокумент
    type: DocumentRef
  # Перерахування
  - name: Статус
    type: EnumRef.СтатусыДокументов

forms:
  - name: Форма
    default: true
    elements:
      - type: InputField
        name: ПользовательПоле
        attribute: Пользователь
        events:
          OnChange: ПользовательПриИзменении  # handlers/ПользовательПриИзменении.bsl
```

### Приклад 6: DynamicList з параметрами

```yaml
processor:
  name: СложныйДинамическийСписок
  synonym_ru: Сложный динамический список с параметрами
  synonym_uk: Складний динамічний список з параметрами

attributes:
  - name: ДатаНачала
    type: date
    synonym_ru: Дата начала
    synonym_uk: Дата початку
  - name: ДатаОкончания
    type: date
    synonym_ru: Дата окончания
    synonym_uk: Дата закінчення
  - name: Организация
    type: CatalogRef.Организации
    synonym_ru: Организация
    synonym_uk: Організація

forms:
  - name: Форма
    default: true
    dynamic_lists:
      - name: СписокДокументов
        title_ru: Документы продаж
        title_uk: Документи продажу
        manual_query: true
        main_table: Document.РеализацияТоваровУслуг
        key_fields: [Ссылка]
        query_text: |
          ВЫБРАТЬ
            РеализацияТоваровУслуг.Ссылка КАК Ссылка,
            РеализацияТоваровУслуг.Дата КАК Дата,
            РеализацияТоваровУслуг.Номер КАК Номер,
            РеализацияТоваровУслуг.Организация КАК Организация,
            РеализацияТоваровУслуг.Контрагент КАК Контрагент,
            РеализацияТоваровУслуг.СуммаДокумента КАК Сумма
          ИЗ
            Документ.РеализацияТоваровУслуг КАК РеализацияТоваровУслуг
          ГДЕ
            РеализацияТоваровУслуг.Дата МЕЖДУ &ДатаНачала И &ДатаОкончания
            И РеализацияТоваровУслуг.Организация = &Организация
            И РеализацияТоваровУслуг.Проведен
        parameters:
          - {name: ДатаНачала, value_type: date, value: Объект.ДатаНачала}
          - {name: ДатаОкончания, value_type: date, value: Объект.ДатаОкончания}
          - {name: Организация, value_type: CatalogRef.Организации, value: Объект.Организация}
        use_always_fields: [Ссылка, Дата]
        columns:
          - {field: Дата, title_ru: Дата, title_uk: Дата}
          - {field: Номер, title_ru: Номер, title_uk: Номер}
          - {field: Организация, title_ru: Организация, title_uk: Організація}
          - {field: Контрагент, title_ru: Контрагент, title_uk: Контрагент}
          - {field: Сумма, title_ru: Сумма, title_uk: Сума}
    events:
      OnCreateAtServer: ПриСозданииНаСервере
    elements:
      - type: InputField
        name: ДатаНачала
        attribute: ДатаНачала
        events:
          OnChange: ДатаНачалаПриИзменении
      - type: InputField
        name: ДатаОкончания
        attribute: ДатаОкончания
        events:
          OnChange: ДатаОкончанияПриИзменении
      - type: InputField
        name: Организация
        attribute: Организация
        events:
          OnChange: ОрганизацияПриИзменении
      - type: Table
        name: СписокДокументов
        tabular_section: СписокДокументов
        properties:
          is_dynamic_list: true
    commands:
      - name: Обновить
        title_ru: Обновить
        title_uk: Оновити
        handler: ОбновитьСписок
        picture: StdPicture.Refresh
        shortcut: F5
```

**handlers/ПриСозданииНаСервере.bsl:**
```bsl
# Устанавливаем значения по умолчанию для фильтров
Объект.ДатаНачала = НачалоМесяца(ТекущаяДата());
Объект.ДатаОкончания = КонецМесяца(ТекущаяДата());

# Устанавливаем параметры списка
СписокДокументов.Параметры.УстановитьЗначениеПараметра("ДатаНачала", Объект.ДатаНачала);
СписокДокументов.Параметры.УстановитьЗначениеПараметра("ДатаОкончания", Объект.ДатаОкончания);
СписокДокументов.Параметры.УстановитьЗначениеПараметра("Организация", Объект.Организация);
```

**handlers/ДатаНачалаПриИзмененииНаСервере.bsl:**
```bsl
СписокДокументов.Параметры.УстановитьЗначениеПараметра("ДатаНачала", Объект.ДатаНачала);
```

---

## Довідник

### Типи даних

#### Прості типи
- `string` - Рядок (length)
- `boolean` - Булеве
- `number` - Число (digits, fraction_digits)
- `date` - Дата/час

#### Довідникові типи
- `CatalogRef.ИмяСправочника` - Конкретний довідник
- `CatalogRef` - Будь-який довідник
- `DocumentRef.ИмяДокумента` - Конкретний документ
- `DocumentRef` - Будь-який документ
- `EnumRef.ИмяПеречисления` - Перерахування

### Події форми

```yaml
forms:
  - name: Форма
    events:
      OnOpen: string              # ПриОткрытии(Отказ)
      OnCreateAtServer: string    # ПриСозданииНаСервере(Отказ, СтандартнаяОбработка)
      OnClose: string             # ПриЗакрытии(ЗавершениеРаботы)
      BeforeClose: string         # ПередЗакрытием(Отказ, ЗавершениеРаботы, ТекстПредупреждения, СтандартнаяОбработка)
```

### visible/enabled Properties (v2.72.0+)

All elements support visibility control:

```yaml
elements:
  - type: ButtonGroup
    name: СкрытыеКнопки
    visible: false          # Hide element
    elements:
      - type: Button
        name: КнопкаW
        command: ВверхКоманда

  - type: InputField
    name: ПолеТолькоЧтение
    attribute: Данные
    enabled: false          # Disable element
```

### Події елементів

```yaml
- type: InputField
  name: МоеПоле
  attribute: МойАтрибут
  events:
    OnChange: string            # ПриИзменении(Элемент)
    StartChoice: string         # НачалоВыбора(Элемент, ДанныеВыбора, СтандартнаяОбработка)
    Clearing: string            # Очистка(Элемент, СтандартнаяОбработка)
```

```yaml
- type: LabelField
  name: МояМетка
  events:
    Click: string               # Нажатие(Элемент)
```

### Елементи форми

#### InputField
```yaml
- type: InputField
  name: string
  attribute: string  # Посилання на attribute

  # Optional properties
  multiline: boolean           # Multiline text input (default: false)
  height: integer             # Number of visible text lines (for multiline fields, in row units)
  width: integer              # Width in character units
  horizontal_stretch: boolean # Stretch to fill horizontal space
  title_location: string      # None, Top, Left, Right, Bottom
  read_only: boolean          # Read-only field
  password_mode: boolean      # Password field (masked input)
  text_edit: boolean          # Enable text editing
  auto_max_width: boolean     # Auto-adjust width
  choice_list:                # Choice list items (array of objects)
    - v: string               # Value stored in attribute (no spaces)
      ru: string              # Display text (Russian)
      uk: string              # Display text (Ukrainian, optional)
      en: string              # Display text (English, optional)
      t: string               # Optional: xs:string (default), xs:decimal
  input_hint_ru: string       # Input hint (Russian)
  input_hint_uk: string       # Input hint (Ukrainian)
  input_hint_en: string       # Input hint (English)
  events: {}

  # Styling properties (v2.43.0+)
  title_text_color: string    # Title text color in HEX format (#RRGGBB)
  text_color: string          # Field text color in HEX format
  back_color: string          # Background color in HEX format
  border_color: string        # Border color in HEX format

  # Title font (v2.43.0+)
  title_font:
    ref: string               # Font reference (style:NormalTextFont, style:LargeTextFont, etc.)
    faceName: string          # Font family name (Arial, Bahnschrift, etc.)
    height: integer           # Font height in points
    scale: integer            # Font scale percentage (100 = normal)
    bold: boolean
    italic: boolean
    underline: boolean
    strikethrough: boolean
    kind: string              # StyleItem (default) or WindowsFont

  # Field font (v2.43.0+)
  font:
    ref: string               # Font reference
    faceName: string          # Font family name
    height: integer           # Font height in points
    scale: integer            # Font scale percentage
    bold: boolean
    italic: boolean
    underline: boolean
    strikethrough: boolean
    kind: string              # StyleItem (default) or WindowsFont

  # Choice button (v2.77.0+)
  choice_button: boolean         # Show/hide choice button (no CommonPicture needed)
  choice_button_picture: string  # Custom picture for choice button (CommonPicture.Name, requires CommonPicture in configuration)
```

**InputField Styling Example (v2.43.0+):**

```yaml
- type: InputField
  name: StyledField
  attribute: Description

  # Colors (HEX format only)
  title_text_color: "#616EFF"   # Blue title
  text_color: "#330910"         # Dark text
  back_color: "#F0FFF0"         # Light green background
  border_color: "#DB6C1F"       # Orange border

  # Custom title font
  title_font:
    ref: "style:ExtraLargeTextFont"
    faceName: "Bahnschrift SemiLight Condensed"
    height: 11
    scale: 102

  # Custom field font
  font:
    ref: "style:ExtraLargeTextFont"
    faceName: "Berlin Sans FB Demi"
    height: 10
    bold: true
```

**Generated XML:**
```xml
<InputField name="StyledField" id="7">
    <DataPath>Объект.Description</DataPath>
    <TitleTextColor>#616EFF</TitleTextColor>
    <TitleFont ref="style:ExtraLargeTextFont" faceName="Bahnschrift SemiLight Condensed" height="11" scale="102" kind="StyleItem"/>
    <TextColor>#330910</TextColor>
    <BackColor>#F0FFF0</BackColor>
    <BorderColor>#DB6C1F</BorderColor>
    <Font ref="style:ExtraLargeTextFont" faceName="Berlin Sans FB Demi" height="10" bold="true" kind="StyleItem"/>
</InputField>
```

**Font Reference Options:**
- `style:NormalTextFont` - Standard form text (default)
- `style:LargeTextFont` - Large headers
- `style:SmallTextFont` - Small captions
- `style:ExtraLargeTextFont` - Extra large titles
- `sys:DefaultGUIFont` - System GUI font

#### LabelField
```yaml
- type: LabelField
  name: string
  attribute: string        # Опціонально
  data_path: string        # Кастомний DataPath (Items.Table.CurrentData.Field)
  hyperlink: boolean       # Гіперпосилання
  events: {}
```

#### LabelDecoration
```yaml
- type: LabelDecoration
  name: string
  title: string  # Single language title (deprecated, use multilingual)

  # Multilingual support
  title_ru: string
  title_uk: string
  title_en: string

  # Optional properties
  hyperlink: boolean  # Make label clickable (v2.35.0+)
  formatted: boolean  # Enable HTML tags in title (v2.45.0+)
                      # Supports: <b>, <i>, <u>, <font color="...">
  horizontal_align: string  # Left, Center, Right, Auto (v2.36.0+)
  vertical_align: string    # Top, Center, Bottom, Auto (v2.36.0+)

  # Font styling (v2.35.1+, fixed in v2.43.0)
  font:
    ref: string            # Font reference (default: style:NormalTextFont)
                           # Options: style:NormalTextFont, style:LargeTextFont,
                           #          style:SmallTextFont, sys:DefaultGUIFont
    kind: string           # Font type (default: StyleItem)
                           # Options: StyleItem, WindowsFont
    bold: boolean          # Bold text style
    italic: boolean        # Italic text style
    underline: boolean     # Underlined text style
    strikethrough: boolean # Strikethrough text style
    height: integer        # Font height in points (for WindowsFont)

  # Events (v2.35.0+)
  events:
    Click: string  # Event handler (only works when hyperlink=true)
```

**Font Styling Examples:**

```yaml
# Bold header
- type: LabelDecoration
  name: SectionHeader
  title_ru: "📊 Основная информация"
  font:
    bold: true
    size: 12

# Warning text
- type: LabelDecoration
  name: WarningLabel
  title_ru: "⚠️ Важно!"
  font:
    bold: true
    italic: true

# Strikethrough (deprecated feature)
- type: LabelDecoration
  name: OldFeatureLabel
  title_ru: "Устаревшая функция"
  font:
    strikethrough: true

# Formatted text with HTML tags (v2.45.0+)
- type: LabelDecoration
  name: WarningMessage
  title_ru: "УВАГА: <b>Важливо</b> - ця дія <font color='red'>незворотня</font>!"
  formatted: true
```

**Generated XML:**
```xml
<LabelDecoration name="SectionHeader" id="5">
    <Title formatted="false">
        <v8:item>
            <v8:lang>ru</v8:lang>
            <v8:content>📊 Основная информация</v8:content>
        </v8:item>
    </Title>
    <Font ref="style:NormalTextFont" bold="true" kind="StyleItem"/>
    <ContextMenu name="SectionHeaderКонтекстноеМеню" id="6"/>
    <ExtendedTooltip name="SectionHeaderРасширеннаяПодсказка" id="7"/>
</LabelDecoration>
```

#### Table
```yaml
- type: Table
  name: string
  tabular_section: string  # Ім'я TabularSection, ValueTable, ValueTree або DynamicList

  # Варіант 1: is_value_table на рівні елемента
  is_value_table: boolean  # true для ValueTable, false для TabularSection

  # Варіант 2: is_value_table в properties (обидва варіанти підтримуються!)
  properties:
    is_value_table: boolean  # true для ValueTable, false для TabularSection
    is_dynamic_list: boolean  # true для DynamicList

  # Tree mode properties (v2.64.0+)
  representation: string           # list (default) | tree
  initial_tree_view: string        # no_expand | expand_top_level | expand_all_levels
  show_root: boolean               # Show root element (default: true)
  allow_root_choice: boolean       # Allow selecting root (default: true)
  choice_folders_and_items: string # folders | items | folders_and_items

  # Optional properties
  height: integer             # Number of visible rows (in row units, without scrolling)
  horizontal_stretch: boolean # Stretch to fill horizontal space
  read_only: boolean          # Read-only table
  events: {}
```

**⚠️ ВАЖЛИВО: Розміщення is_value_table та is_dynamic_list:**

Генератор підтримує **два способи** вказати `is_value_table` та `is_dynamic_list`:

**Варіант 1 - На рівні елемента (рекомендується):**
```yaml
- type: Table
  name: РезультатыТаблица
  tabular_section: Результаты
  is_value_table: true  # ← Прямо на рівні Table
```

**Варіант 2 - В properties:**
```yaml
- type: Table
  name: РезультатыТаблица
  tabular_section: Результаты
  properties:
    is_value_table: true  # ← Під properties
```

**Обидва варіанти працюють однаково!** Генератор автоматично перевіряє обидва місця.

**Вплив на DataPath:**
- `is_value_table: true` → `<DataPath>ИмяТаблицы</DataPath>` (без префікса Объект.)
- `is_value_table: false` → `<DataPath>Объект.ИмяТаблицы</DataPath>` (з префіксом)
- `is_dynamic_list: true` → `<DataPath>ИмяСписка</DataPath>` (без префікса)

#### SpreadSheetDocumentField
```yaml
- type: SpreadSheetDocumentField
  name: string
  attribute: string  # Посилання на form_attribute (SpreadsheetDocument)

  # Optional properties
  title_location: string          # None, Top, Left, Right, Bottom, Auto
  stretch: string                 # No, Horizontally, Vertically, HorizontalAndVertically
  vertical_scrollbar: boolean     # Show vertical scrollbar (default: true)
  horizontal_scrollbar: boolean   # Show horizontal scrollbar (default: true)
  show_grid: boolean              # Show cell grid (default: true)
  show_headers: boolean           # Show row/column headers (default: true)
  edit: boolean                   # Allow cell editing (default: false)
  protection: boolean             # Enable cell protection (default: false)
  events: {}
```

**Typical usage:**
```yaml
forms:
  - name: Форма
    form_attributes:
      - name: Отчет
        type: spreadsheet_document  # Must be form attribute!

    elements:
      - type: SpreadSheetDocumentField
        name: ПолеОтчет
        attribute: Отчет
        title_location: None
        show_grid: false            # Hide grid for clean report look
        show_headers: true
        edit: false                 # Read-only report
        events:
          DetailProcessing: ОтчетДетальнаяОбработка  # Drill-down handler
```

#### HTMLDocumentField (v2.39.0+)

Field for displaying and interacting with HTML content. Supports hyperlink click handling.

```yaml
- type: HTMLDocumentField
  name: string
  attribute: string  # Reference to string form_attribute for HTML content

  # Optional properties
  title_location: string  # None, Auto, Left, Top, Right, Bottom (default: None)
  width: integer          # Field width in character units
  height: integer         # Field height in row units

  events:
    OnClick: string       # Hyperlink click handler
```

**Event signature:**
```bsl
&НаКлиенте
Процедура ПолеHTMLПриНажатии(Элемент, ДанныеСобытия, СтандартнаяОбработка)
    // ДанныеСобытия.href - URL of clicked link
    СтандартнаяОбработка = Ложь;
    // Handle link...
КонецПроцедуры
```

**Typical usage:**
```yaml
forms:
  - name: Форма
    form_attributes:
      - name: HTMLКонтент
        type: string  # Unlimited string for HTML content

    elements:
      - type: HTMLDocumentField
        name: ПолеHTML
        attribute: HTMLКонтент
        title_location: None
        width: 50
        height: 20
        events:
          OnClick: ПолеHTMLПриНажатии
```

**Link handling patterns:**
```bsl
#Область ПолеHTMLПриНажатии
&НаКлиенте
Процедура ПолеHTMLПриНажатии(Элемент, ДанныеСобытия, СтандартнаяОбработка)

    Если ПустаяСтрока(ДанныеСобытия.href) Тогда
        Возврат;
    КонецЕсли;

    СтандартнаяОбработка = Ложь;

    // Web links (http/https)
    Если СтрНайти(ДанныеСобытия.href, "http") > 0 Тогда
        ФайловаяСистемаКлиент.ОткрытьНавигационнуюСсылку(ДанныеСобытия.href);

    // 1C navigation links (e1cib/)
    ИначеЕсли СтрНайти(ДанныеСобытия.href, "e1cib/") > 0 Тогда
        ФайловаяСистемаКлиент.ОткрытьНавигационнуюСсылку(ДанныеСобытия.href);

    КонецЕсли;

КонецПроцедуры
#КонецОбласти
```

#### UsualGroup

Container for grouping form elements with visual styling, collapse support, and infinite nesting.

```yaml
- type: UsualGroup
  name: string

  # Layout
  group_direction: Vertical|Horizontal  # Default: Vertical

  # Visual styling
  representation: None|NormalSeparation|WeakSeparation|StrongSeparation  # Default: None
  behavior: Usual|Collapsible  # Default: Usual
  show_title: boolean  # Default: false

  # State
  read_only: boolean  # Makes all children read-only recursively (default: false)

  # Multilingual title
  title_ru: string
  title_uk: string
  title_en: string

  # Child elements (supports ANY element type, infinite nesting!)
  elements:
    - type: InputField
      ...
    - type: UsualGroup  # Nested groups supported!
      group_direction: Horizontal
      elements:
        - type: Button
          ...
        - type: UsualGroup  # 3rd level nesting!
          ...
```

**Example:**
```yaml
- type: UsualGroup
  name: FilterGroup
  group_direction: Horizontal
  representation: WeakSeparation
  behavior: Collapsible
  show_title: true
  title_ru: Фильтры
  title_uk: Фільтри
  title_en: Filters
  elements:
    - type: InputField
      name: DateFrom
      attribute: DateFrom
      width: 12
    - type: InputField
      name: DateTo
      attribute: DateTo
      width: 12
    - type: Button
      name: ApplyFilter
      command: ApplyFilter
      width: 15
```

#### ColumnGroup (v2.37.0+)

**Multi-level table headers** - Groups table columns under one header for professional layouts.

```yaml
- type: ColumnGroup
  name: string

  # Visual header
  title_ru: string
  title_uk: string
  title_en: string

  # Tooltip (optional)
  tooltip_ru: string
  tooltip_uk: string
  tooltip_en: string

  # Layout
  group_layout: Horizontal|Vertical  # Default: Horizontal
  show_in_header: boolean  # Default: true

  # Alignment (v2.36.0+ Phase 2)
  horizontal_align: Left|Center|Right|Auto
  vertical_align: Top|Center|Bottom|Auto

  # Child columns (ONLY field types: LabelField, InputField, CheckBoxField, PictureField)
  elements:
    - type: LabelField
      name: Date
      attribute: Date
    - type: LabelField
      name: Time
      attribute: Time
```

**Example - Date & Time Group:**
```yaml
- type: Table
  name: OperationsTable
  tabular_section: Operations
  elements:
    - type: ColumnGroup
      name: DateTimeGroup
      title_ru: Дата и время
      title_uk: Дата і час
      title_en: Date and Time
      tooltip: "Operation date and time"
      group_layout: Horizontal
      horizontal_align: Center
      elements:
        - type: LabelField
          name: Date
          attribute: Date
          width: 12
        - type: LabelField
          name: Time
          attribute: Time
          width: 10
```

**Example - Financial Amounts:**
```yaml
- type: ColumnGroup
  name: AmountsGroup
  title: "Суми"
  group_layout: Horizontal
  horizontal_align: Right
  elements:
    - type: LabelField
      name: Debit
      attribute: Debit
      width: 12
    - type: LabelField
      name: Credit
      attribute: Credit
      width: 12
    - type: LabelField
      name: Total
      attribute: Total
      width: 15
```

**Visual Result:**
```
| Операція | ┌─ Дата і час ─┐ | ┌─── Суми ────┐ |
|          | Дата    | Час  | Дебет | Кредит | Підсумок |
```

**Key Features:**
- **Context**: Only valid inside `Table.elements` array
- **Children**: Only LabelField, InputField, CheckBoxField, PictureField allowed
- **No Nesting**: ColumnGroup cannot contain another ColumnGroup
- **ID Allocation**: Element + ExtendedTooltip = 2 IDs
- **Use Cases**: Financial reports, Plan vs Fact, grouped periods (Q1/Q2), address parts

**Real-World Examples:**
1. **Quarters**: Q1 (Jan/Feb/Mar), Q2 (Apr/May/Jun)
2. **Plan vs Fact**: Plan (Qty/Amt), Fact (Qty/Amt)
3. **Address**: City/Street/Building under "Address" header
4. **Amounts**: Debit/Credit/Balance under "Financial Data"

#### ButtonGroup (v2.15.0+)

Visual container for grouping related buttons.

```yaml
- type: ButtonGroup
  name: string

  # Layout
  group_direction: Vertical|Horizontal  # Default: Horizontal

  # Multilingual title (optional separator label)
  title_ru: string
  title_uk: string
  title_en: string

  # Child buttons only
  elements:
    - type: Button
      name: SaveButton
      command: Save
      width: 15
    - type: Button
      name: CancelButton
      command: Cancel
      width: 15
```

**Example:**
```yaml
- type: ButtonGroup
  name: ActionButtons
  group_direction: Horizontal
  title_ru: Действия
  title_uk: Дії
  title_en: Actions
  elements:
    - type: Button
      name: CreateButton
      command: Create
      width: 15
    - type: Button
      name: EditButton
      command: Edit
      width: 15
    - type: Button
      name: DeleteButton
      command: Delete
      width: 15
```

**Comparison: ButtonGroup vs UsualGroup**

| Feature | ButtonGroup | UsualGroup |
|---------|-------------|------------|
| Child types | Buttons only | Any elements |
| group_direction | ✅ Vertical/Horizontal | ✅ Vertical/Horizontal |
| representation | ❌ Not supported | ✅ 4 visual styles |
| behavior | ❌ Not collapsible | ✅ Collapsible support |
| show_title | ❌ Title always visible | ✅ Can hide title |
| read_only | ❌ Not supported | ✅ Recursive read-only |

**When to use:**
- **ButtonGroup**: Simple visual grouping of buttons (lightweight)
- **UsualGroup**: Advanced grouping with styling, collapse, nested elements

**⚠️ ВАЖЛИВО для ValueTable:**
- `tabular_section` повинен посилатися на `value_tables.name`
- DataPath автоматично буде прямим (без префікса `Объект.`) - це form-level атрибут

**⚠️ ВАЖЛИВО для ValueTree (v2.64.0+):**
- `tabular_section` повинен посилатися на `value_trees.name`
- DataPath автоматично буде прямим (без префікса `Объект.`) - це form-level атрибут
- Рекомендується додавати `representation: tree` для ієрархічного відображення

**⚠️ ВАЖЛИВО для DynamicList:**
- `tabular_section` повинен посилатися на `dynamic_lists.name`
- DataPath автоматично буде прямим (без префікса `Объект.`)

### DynamicList атрибути

```yaml
dynamic_lists:
  - name: string                    # Ім'я атрибуту (обов'язкове)
    title_ru: string                # Заголовок (ru)
    title_uk: string                # Заголовок (uk)
    manual_query: boolean           # true = кастомний QueryText, false = авто-запит з MainTable
    main_table: string              # Document.*, Catalog.* (обов'язково для manual_query=true)
    query_text: string              # SQL запит (для manual_query=true)
    key_fields: []                  # Ключові поля для унікальної ідентифікації рядків
    parameters: []                  # Параметри запиту
    use_always_fields: []           # Поля які завжди вибираються
    columns: []                     # Колонки для відображення
```

**Властивості:**

- **name** (обов'язкове) - Ім'я атрибуту DynamicList на формі
- **title_ru/title_uk** - Заголовки для форми
- **manual_query** - `true` для кастомного QueryText, `false` для автоматичного запиту з MainTable
- **main_table** - Базова таблиця (обов'язково для `manual_query=true`)
  - Формат: `Document.ИмяДокумента` або `Catalog.ИмяСправочника`
  - Використовується 1C для валідації DataPath навіть з кастомним запитом
- **query_text** - SQL запит мовою запитів 1C (для `manual_query=true`)
  - Параметри передаються через `&ИмяПараметра`
  - Автоматично екранується в XML (`&` → `&amp;`)
- **key_fields** - Масив ключових полів для унікальної ідентифікації рядків
  - **Обов'язкове для `manual_query=true`**
  - Приклад: `[Ссылка]` для документних списків
  - Використовується 1C для валідації DataPath
- **parameters** - Параметри запиту (детально нижче)
- **use_always_fields** - Поля які завжди вибираються з запиту
  - ⚠️ **ВАЖЛИВО**: У YAML вказуються **БЕЗ префікса** імені списку!
  - Формат в YAML: `[ИмяПоля]` (приклад: `[Ссылка, Дата]`)
  - Генератор автоматично додає префікс в XML: `ListName.ИмяПоля`
  - ⚠️ **Валідація**: Генератор перевіряє наявність Table з is_dynamic_list на формі
  - Якщо Table не знайдено → UseAlways автоматично видаляється + попередження
- **columns** - Колонки для відображення на формі (детально нижче)

**Параметри (parameters):**

```yaml
parameters:
  - name: string          # Ім'я параметра (використовується як &ИмяПараметра в запиті)
    value_type: string    # Тип параметра (date, CatalogRef.*, etc.)
    value: string         # Значення (зазвичай посилання на атрибут: Объект.ИмяАтрибута)
```

**Колонки (columns):**

```yaml
columns:
  - field: string         # Ім'я поля з запиту (без префікса списку)
    title_ru: string      # Заголовок колонки (ru)
    title_uk: string      # Заголовок колонки (uk)
    width: number         # Ширина колонки (опціонально)
```

**Використання на формі:**

```yaml
forms:
  - name: Форма
    default: true
    dynamic_lists:
      - name: СписокДокументов
        # ... визначення списку
    elements:
      - type: Table
        name: МойСписок
        tabular_section: СписокДокументов  # Посилання на dynamic_lists.name
        properties:
          is_dynamic_list: true
```

**Приклад (детально див. Приклад 6):**

```yaml
forms:
  - name: Форма
    default: true
    dynamic_lists:
      - name: СписокДокументов
        title_ru: Документы продаж
        manual_query: true
        main_table: Document.РеализацияТоваровУслуг
        key_fields: [Ссылка]
        query_text: |
          ВЫБРАТЬ Ссылка, Дата, Номер ИЗ Документ.РеализацияТоваровУслуг ГДЕ Дата >= &ДатаНачала
        parameters:
          - { name: ДатаНачала, value_type: date, value: Объект.ДатаНачала }
        use_always_fields: [Ссылка]
        columns:
          - { field: Дата, title_ru: Дата }
          - { field: Номер, title_ru: Номер }
```

**⚠️ ВАЖЛИВО для DynamicList:**

1. **Автоматичний DynamicDataRead:**
   - `main_table` вказано → `DynamicDataRead=true` (живе підключення до БД)
   - `main_table` відсутнє → `DynamicDataRead=false` (статичний запит)
   - Генератор встановлює автоматично!

2. **use_always_fields формат:**
   - У YAML: **БЕЗ** префікса імені списку: `[Ссылка, Дата]`
   - В XML: З префіксом (автоматично): `<Field>ListName.Ссылка</Field>`
   - Генератор додає префікс автоматично!

3. **Валідація UseAlways:**
   - Генератор перевіряє наявність Table з `is_dynamic_list: true` на формі
   - Якщо Table не знайдено → UseAlways видаляється + попередження
   - **Завжди додавайте Table елемент** при використанні use_always_fields!

4. **Обов'язкові поля:**
   - `name` - завжди обов'язкове
   - `key_fields` - обов'язкове для `manual_query=true`
   - `main_table` - рекомендовано (навіть з custom query для DynamicDataRead)

5. **Параметри запиту:**
   - Використовуються як `&ИмяПараметра` в query_text
   - Генератор автоматично екранує `&` → `&amp;` в XML

#### Button
```yaml
- type: Button
  name: string
  command: string  # Посилання на command
```

#### UsualGroup
```yaml
- type: UsualGroup
  name: string
  title: string                                      # Заголовок
  show_title: boolean                                # Показувати заголовок
  group_direction: Vertical|Horizontal               # Напрямок
  representation: None|NormalSeparation|WeakSeparation|StrongSeparation
  behavior: Usual|Collapsible                        # Поведінка (згортається)
  child_items: []                                    # Вкладені елементи
```

#### Pages
```yaml
- type: Pages
  name: string
  pages_representation: TabsOnTop|TabsOnBottom|None
  pages:
    - name: string
      title: string
      child_items: []  # Вкладені елементи
```

### Templates (Макети) - v2.40.0+

Templates are DataProcessor-level metadata objects that contain external content (HTML, SpreadsheetDocument). They are NOT form elements - templates exist at the processor level.

#### Template Types

| Type | Description | File Extension | BSL Method |
|------|-------------|----------------|------------|
| `HTMLDocument` | HTML content for web display | `.html` | `GetText()` |
| `SpreadsheetDocument` | MXL spreadsheet layout | `.mxl` | Direct use |

#### YAML Syntax

```yaml
templates:
  - name: EmailTemplate      # Template name (required)
    type: HTMLDocument       # Template type (required)
    file: templates/email.html  # Path relative to config.yaml (required)

  - name: ReportLayout
    type: SpreadsheetDocument
    file: templates/report.mxl
```

#### BSL Usage

```bsl
// Get HTML template content
Макет = Обработки.MyProcessor.ПолучитьМакет("EmailTemplate");
HTMLКонтент = Макет.ПолучитьТекст();

// Dynamic placeholder replacement
HTMLКонтент = СтрЗаменить(HTMLКонтент, "%Имя%", ИмяКлиента);

// Display in HTMLDocumentField
Объект.HTMLПоле = HTMLКонтент;

// Use SpreadsheetDocument template
Макет = Обработки.MyProcessor.ПолучитьМакет("ReportLayout");
ТабДок = Новый ТабличныйДокумент;
ТабДок.Вывести(Макет);
```

#### File Structure Generated

```
MyProcessor/
├── MyProcessor.xml                           # Main processor XML (contains <Template>)
└── MyProcessor/
    └── Templates/
        ├── EmailTemplate.xml                 # Template metadata
        └── EmailTemplate/
            └── Ext/
                ├── Template.xml              # Template ext marker
                └── Template/
                    └── Template.html         # Actual HTML content
```

#### Use Cases

- **HTMLDocument**: Email templates, help/description screens, dashboards, rich text content
- **SpreadsheetDocument**: Report layouts, print forms, export templates

#### Template Automation (v2.41.0+)

Automation features reduce LLM token generation and errors.

##### auto_field - Automatic Form Integration

```yaml
templates:
  - name: EmailPreview
    type: HTMLDocument
    file: templates/email.html
    auto_field: true              # Creates form_attribute + HTMLDocumentField
    field_name: CustomEmailField  # Optional custom field name (default: {name}Field)
    target_form: Форма            # Optional target form (default: first default form)
```

**What auto_field creates:**
- `FormAttribute` named `{TemplateName}HTML` (type: html_document)
- `HTMLDocumentField` element named `{TemplateName}Field` (or custom field_name)

##### automation - Separate Automation File

For complex automation (placeholders, assets), use separate `.automation.yaml` file:

```yaml
# config.yaml
templates:
  - name: EmailTemplate
    type: HTMLDocument
    file: templates/email.html
    auto_field: true
    automation: templates/email.automation.yaml
```

```yaml
# templates/email.automation.yaml
placeholders:
  - name: "{{UserName}}"           # Mustache-style placeholder
    bsl_value: "ТекущийПользователь().Имя"  # Direct BSL expression
  - name: "{{CompanyName}}"
    attribute: CompanyName         # Reference to Объект.CompanyName
  - name: "{{Date}}"
    bsl_value: 'Формат(ТекущаяДата(), "ДФ=''dd.MM.yyyy''")'

assets:
  styles:
    - file: email-styles.css       # CSS file injected into <head>
    - inline: ".custom { color: red; }"
  scripts:
    - file: helpers.js             # JS file injected before </body>
```

##### Auto-Generated BSL Helper

For templates with placeholders, generator creates BSL helper function:

```bsl
&НаСервере
Функция ПолучитьТекстМакетаEmailTemplate()
    Макет = РеквизитФормыВЗначение("Объект").ПолучитьМакет("EmailTemplate");
    Результат = Макет.ПолучитьТекст();

    // Заміна placeholders
    Результат = СтрЗаменить(Результат, "{{UserName}}", ТекущийПользователь().Имя);
    Результат = СтрЗаменить(Результат, "{{CompanyName}}", Объект.CompanyName);

    Возврат Результат;
КонецФункции
```

**Usage in OnCreateAtServer:**
```bsl
&НаСервере
Процедура ПриСозданииНаСервере(Отказ, СтандартнаяОбработка)
    EmailTemplateHTML = ПолучитьТекстМакетаEmailTemplate();
КонецПроцедуры
```

### Команди

```yaml
commands:
  - name: string              # Ім'я команди
    title_ru: string          # Заголовок (ru)
    title_uk: string          # Заголовок (uk)
    handler: string           # Ім'я обробника (BSL файл)
    tooltip_ru: string        # Підказка (ru)
    tooltip_uk: string        # Підказка (uk)
    picture: string           # StdPicture.* або CommonPicture.*
    shortcut: string          # Гаряча клавіша
```

#### Стандартні картинки (StdPicture)
- `StdPicture.Refresh` - Оновити
- `StdPicture.Write` - Зберегти (іконка галочки) ✅
- `StdPicture.Delete` - Видалити
- `StdPicture.Find` - Знайти
- `StdPicture.Print` - Друк
- `StdPicture.ExecuteTask` - Виконати
- `StdPicture.SaveFile` - Зберегти файл
- `StdPicture.OpenFile` - Відкрити файл
- `StdPicture.CustomizeForm` - Налаштування
- `StdPicture.User` - Користувач
- `StdPicture.InputFieldClear` - Очистити

**⚠️ Увага:** `StdPicture.CheckMark` НЕ існує! Використовуйте `StdPicture.Write` для іконки збереження.

**Валідація:** Генератор перевіряє назви StdPicture проти списку з 130+ відомих картинок платформи. При використанні невалідної назви ви отримаєте помилку валідації з підказками.

📄 **Повний список:** Див. [VALID_PICTURES.md](VALID_PICTURES.md) для всіх 130+ доступних картинок.

#### Автоматичне відображення кнопок

**Нова функція (v2.2.0):** Коли команда має картинку (`picture`), кнопки автоматично отримують `representation: PictureAndText` для відображення і іконки, і тексту. Це можна перевизначити явно встановивши `representation` на кнопці.

**Приклад:**
```yaml
forms:
  - name: Форма
    default: true
    commands:
      - name: Выполнить
        title_ru: Выполнить
        picture: StdPicture.ExecuteTask  # Команда має картинку
        handler: ВыполнитьОбработку
    elements:
      # Ця кнопка автоматично отримає representation: PictureAndText
      - type: Button
        name: ВыполнитьКнопка
        command: Выполнить
      # Ця кнопка примусово показує тільки текст
      - type: Button
        name: ДругаКнопка
        command: Выполнить
        representation: Text  # Перевизначає автоматичне PictureAndText
```

#### Гарячі клавіші
- `F1` - `F12`
- `Ctrl+S`, `Ctrl+N`, `Ctrl+O` тощо
- `Shift+F5`, `Ctrl+Shift+S` тощо

---

## Workflow для ЛЛМ

### Крок 1: Аналіз запиту

```
Користувач: "Створи обробку для установки ролі користувачу"
```

### Крок 2: Створення config.yaml

ЛЛМ створює декларативну конфігурацію:

```yaml
processor:
  name: УстановкаРоли
  synonym_ru: Установка роли пользователя
  synonym_uk: Встановлення ролі користувача

attributes:
  - name: Пользователь
    type: CatalogRef.Пользователи
  - name: Роль
    type: string
    length: 100

forms:
  - name: Форма
    default: true
    events:
      OnOpen: ПриОткрытии
    elements:
      - type: InputField
        name: ПользовательПоле
        attribute: Пользователь
      - type: InputField
        name: РольПоле
        attribute: Роль
      - type: Button
        name: УстановитьКнопка
        command: УстановитьРоль
    commands:
      - name: УстановитьРоль
        title_ru: Установить роль
        title_uk: Встановити роль
        handler: УстановитьРольОбработчик
        picture: StdPicture.Write
        shortcut: F5
```

### Крок 3: Створення BSL handlers

**handlers/УстановитьРольОбработчик.bsl:**
```bsl
Если НЕ ЗначениеЗаполнено(Объект.Пользователь) Тогда
    Сообщить("Выберите пользователя!");
    Возврат;
КонецЕсли;

Если НЕ ЗначениеЗаполнено(Объект.Роль) Тогда
    Сообщить("Укажите роль!");
    Возврат;
КонецЕсли;

УстановитьРольОбработчикНаСервере();
```

**handlers/УстановитьРольОбработчикНаСервере.bsl:**
```bsl
# Тільки бізнес-логіка
ПользовательИБ = ПользователиИнформационнойБазы.НайтиПоУникальномуИдентификатору(
    Объект.Пользователь.ИдентификаторПользователяИБ
);

Если ПользовательИБ <> Неопределено Тогда
    Роль = Метаданные.Роли.Найти(Объект.Роль);
    Если Роль <> Неопределено Тогда
        ПользовательИБ.Роли.Добавить(Роль);
        ПользовательИБ.Записать();
        Сообщить("Роль успешно установлена!");
    КонецЕсли;
КонецЕсли;
```

### Крок 4: Генерація

```bash
python -m 1c_processor_generator yaml \
  --config config.yaml \
  --handlers handlers/
```

### Результат

✅ Готова обробка з:
- Валідними UUID
- Правильними ID елементів
- Повним BSL кодом з сигнатурами
- Коректною XML структурою

---

## Валідація

Генератор автоматично валідує YAML через JSON Schema та бізнес-правила:

### 1. Валідація YAML структури

```bash
✅ YAML валідація пройдена
```

Якщо є помилки структури:

```bash
❌ YAML не валідний: 'name' is a required property
   Шлях: processor
```

**Встановіть jsonschema для валідації:**
```bash
pip install jsonschema
```

### 2. Валідація імен обробників (BSL Reserved Keywords)

Генератор перевіряє всі імена обробників (commands.handler, form.events, elements.events) на зарезервовані слова BSL:

```bash
❌ Ім'я обробника 'Выполнить' є зарезервованим ключовим словом BSL і не може
   використовуватися як ім'я процедури.
   Використовуйте інше ім'я, наприклад: 'КомандаВыполнить', 'ВыполнитьКоманда',
   'ВыполнитьОбработчик', тощо.
```

Це захищає від синтаксичних помилок BSL при генерації.

### 3. Валідація картинок (StdPicture)

Генератор перевіряє назви `StdPicture.*` проти списку 130+ відомих картинок:

```bash
❌ Невалідна назва StdPicture: 'StdPicture.InvalidName'
   Відомі картинки: StdPicture.ExecuteTask, StdPicture.Write, ...
```

---

## Поради

### ✅ Рекомендується

1. **Використовуйте YAML для ЛЛМ** - простіше і надійніше
2. **BSL логіку в окремі файли** - легше підтримувати
3. **Конвенція імен** - `ПриОткрытии`, а не `ПриОткритті` (системні події російською)
4. **Серверні суфікси** - `КомандаНаСервере` для авто-генерації парних процедур
5. **Уникайте зарезервованих слів** - імена обробників не можуть бути `Выполнить`, `Экспорт`, `Импорт` тощо
6. **Додавайте контекст до імен** - `ВыполнитьОбработку` замість `Выполнить`, `ЭкспортДанных` замість `Экспорт`

### ❌ Уникайте

1. **Сигнатури в BSL файлах** - генератор додає автоматично
2. **Українські назви системних подій** - використовуйте `OnOpen`, не `ПриОткритті`
3. **Хардкод UUID/ID в YAML** - генератор створює автоматично
4. **Зарезервованих слів BSL** - `Выполнить`, `Экспорт`, `Импорт`, `Процедура`, `Функция` тощо (40+ слів)

---

## Повний приклад

Див. `examples/yaml/simple_role_setter/` для повного робочого прикладу.

```bash
cd examples/yaml/simple_role_setter
python -m 1c_processor_generator yaml --config config.yaml --handlers handlers/
```

---

**Версія:** 2.64.0
**Дата:** 28.12.2025

---

## Changelog

### v2.64.0 (2025-12-28)
- ✨ **ValueTree Support** - ієрархічні дані у формі дерева
  - Нова секція `value_trees:` для визначення атрибутів ValueTree
  - Режим `representation: tree` для Table
  - Tree-specific properties: `initial_tree_view`, `show_root`, `allow_root_choice`, `choice_folders_and_items`
  - Повний приклад з BSL handlers для роботи з деревом
- 📚 Додано документацію ValueTree до форм та елементів

### v2.43.0 (2025-12-03)
- 🐛 **КРИТИЧНЕ ВИПРАВЛЕННЯ:** Виправлено генерацію XML для Font елементів
  - Було: вкладені елементи `<Font><v8:Bold>true</v8:Bold></Font>`
  - Стало: self-closing тег з атрибутами `<Font ref="style:NormalTextFont" bold="true" kind="StyleItem"/>`
  - Виправляє проблему з відкриттям обробок в 1C через некоректний Font XML
- 📚 Додано повну документацію InputField styling (colors, fonts)
- 🎯 Додано робочий приклад `examples/yaml/styled_form_example/`

### v2.6.1 (2025-10-14)
- 🐛 **ВАЖЛИВЕ ВИПРАВЛЕННЯ:** Виправлено парсинг `is_value_table` та `is_dynamic_list` в yaml_parser.py
  - Тепер підтримується вказівка `is_value_table` як на рівні Table елемента, так і в properties
  - Виправлено некоректну генерацію DataPath (було `Объект.Имя`, стало `Имя` для ValueTable)
  - Рекомендується використовувати варіант на рівні елемента для простоти
- 📚 Додано детальну документацію про два способи вказати `is_value_table` та `is_dynamic_list`
- 📚 Додано пояснення впливу на генерацію DataPath

### v2.6.0 (2025-10-13)
- ✨ Додано повний опис DynamicList атрибутів
- 🐛 Виправлено структуру Table для DynamicList (is_dynamic_list під properties!)
- 📚 Додано розділ про автоматичний DynamicDataRead
- 📚 Оновлено інформацію про use_always_fields (БЕЗ префікса в YAML)
- 📚 Додано інформацію про валідацію UseAlways

### v2.2.0 (2025-10-10)
- ✨ Додано RadioButtonField, CheckBoxField
- ✨ Додано підтримку ChoiceList та InputHint
- ✨ Додано автоматичне відображення кнопок з картинками

### v2.0.0 (2025-10-07)
- 🎉 Початкова версія YAML API Guide
