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

# ValueTable атрибути (формові)
value_tables:
  - name: string
    title_ru: string
    title_uk: string
    columns:
      - name: string
        type: string
        # ... як у attributes

# DynamicList атрибути (формові)
dynamic_lists:
  - name: string
    title_ru: string
    title_uk: string
    manual_query: boolean       # true = кастомний QueryText, false = авто-запит з MainTable
    main_table: string          # Document.*, Catalog.* (обов'язково для manual_query=true)
    query_text: string          # SQL запит (для manual_query=true)
    key_fields: []              # Ключові поля для унікальної ідентифікації рядків (наприклад: [Ссылка])
    parameters: []              # Параметри запиту
    use_always_fields: []       # Поля які завжди вибираються
    columns: []                 # Колонки для відображення

# Налаштування форми (новий формат)
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

    # ValueTable, DynamicList - всередині форми
    value_tables: []
    dynamic_lists: []

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
        is_value_table: true
```

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
        pages_representation: TabsOnTop
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
  - name: Пользователь
    type: CatalogRef.Пользователи
  - name: Документ
    type: DocumentRef.РеализацияТоваровУслуг
  - name: ЛюбойСправочник
    type: CatalogRef
  - name: ЛюбойДокумент
    type: DocumentRef
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
          OnChange: ПользовательПриИзменении
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
    default: true
    events:
      OnOpen: string              # ПриОткрытии(Отказ)
      OnCreateAtServer: string    # ПриСозданииНаСервере(Отказ, СтандартнаяОбработка)
      OnClose: string             # ПриЗакрытии(ЗавершениеРаботы)
      BeforeClose: string         # ПередЗакрытием(Отказ, ЗавершениеРаботы, ТекстПредупреждения, СтандартнаяОбработка)
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
  events: {}
```

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
  title: string
```

#### Table
```yaml
- type: Table
  name: string
  tabular_section: string  # Ім'я TabularSection, ValueTable або DynamicList

  # Варіант 1: is_value_table на рівні елемента
  is_value_table: boolean  # true для ValueTable, false для TabularSection

  # Варіант 2: is_value_table в properties (обидва варіанти підтримуються!)
  properties:
    is_value_table: boolean  # true для ValueTable, false для TabularSection
    is_dynamic_list: boolean  # true для DynamicList
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
      - name: ИмяDynamicList
        # ... конфігурація DynamicList
    elements:
      - type: Table
        name: МойСписок
        dynamic_list: ИмяDynamicList  # Посилання на dynamic_lists.name
```

**Приклад (детально див. Приклад 6):**

```yaml
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
      - name: ВыполнитьДействие
        title_ru: Выполнить
        picture: StdPicture.ExecuteTask  # Команда має картинку
    elements:
      # Ця кнопка автоматично отримає representation: PictureAndText
      - type: Button
        name: ВыполнитьКнопка
        command: ВыполнитьДействие

      # Ця кнопка примусово показує тільки текст
      - type: Button
        name: ДругаКнопка
        command: ВыполнитьДействие
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
    commands:
      - name: УстановитьРоль
        title_ru: Установить роль
        title_uk: Встановити роль
        handler: УстановитьРоль
        picture: StdPicture.Write  # ✅ Valid picture (checkmark icon)
        shortcut: F5
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
```

### Крок 3: Створення BSL handlers

**handlers/УстановитьРоль.bsl:**
```bsl
Если НЕ ЗначениеЗаполнено(Объект.Пользователь) Тогда
    Сообщить("Выберите пользователя!");
    Возврат;
КонецЕсли;

Если НЕ ЗначениеЗаполнено(Объект.Роль) Тогда
    Сообщить("Укажите роль!");
    Возврат;
КонецЕсли;

УстановитьРольНаСервере();
```

**handlers/УстановитьРольНаСервере.bsl:**
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

**Версія:** 2.6.0
**Дата:** 13.10.2025

---

## Changelog

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
