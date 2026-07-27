# LLM Guide: BSP External Print Forms

> **For AI/LLM agents generating 1C external print forms compatible with BSP (Business Standard Subsystems Library)**

## Quick Start

BSP print forms are external data processors (.epf) that integrate with 1C configurations using the BSP framework. They appear in the "Print" menu of documents/catalogs.

### Minimal Example

**config.yaml:**
```yaml
languages: [ru, uk]

processor:
  name: ПечатьСчeta
  synonym: "Печать счета | Друк рахунку"

bsp:
  type: print_form
  version: "1.0"
  targets:
    - Документ.СчетНаОплатуПокупателю
  commands:
    - id: СчетНаОплату
      title: "Счет на оплату | Рахунок на оплату"
      usage: server_method
      modifier: ПечатьMXL
```

**handlers.bsl:**
```bsl
#Область МодульОбъекта

Функция ПечатьСчетНаОплату(МассивОбъектов, ОбъектыПечати)

    ТабличныйДокумент = Новый ТабличныйДокумент;

    Макет = ПолучитьМакет("ПФ_MXL_Счет");
    ОбластьШапка = Макет.ПолучитьОбласть("Шапка");

    Для Каждого Ссылка Из МассивОбъектов Цикл
        Данные = Ссылка.ПолучитьОбъект();
        ОбластьШапка.Параметры.Номер = Данные.Номер;
        ОбластьШапка.Параметры.Дата = Данные.Дата;
        ТабличныйДокумент.Вывести(ОбластьШапка);
    КонецЦикла;

    Возврат ТабличныйДокумент;

КонецФункции

#КонецОбласти
```

---

## ⚠️ Handler Contract (read before writing any BSL)

Print form code lives in the **ObjectModule**, not in a form module. Three rules follow from that, and breaking any of them silently produces an empty print form:

**1. Wrap everything in `#Область МодульОбъекта`.**
This region is the *only* channel from `handlers.bsl` into `ObjectModule.bsl`. A procedure written outside it is loaded, reported as loaded — and then dropped. The generator emits a TODO stub in its place.

```bsl
#Область МодульОбъекта
    // print functions go here
#КонецОбласти
```

**2. Write the full signature. It is fixed:**

```bsl
Функция Печать<CommandId>(МассивОбъектов, ОбъектыПечати)
    ТабличныйДокумент = Новый ТабличныйДокумент;
    // ... build the document ...
    Возврат ТабличныйДокумент;
КонецФункции
```

The function **creates and returns** the spreadsheet. It is not handed one. The generated `Печать()` procedure calls it as
`ПечатныйДокумент = Печать<CommandId>(МассивОбъектов, ОбъектыПечати);` and puts the result into the BSP collection itself.

**3. No compilation directives.**
`&НаСервере` / `&НаКлиенте` are form module concepts. In an ObjectModule they make the code invalid — do not add them.

Since v2.78.0 the generator warns explicitly when a print handler ends up as a TODO stub, and the CLI finishes with `✨ Готово (з попередженнями: N)` instead of a bare success message.

---

## BSP Section Reference

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | `print_form` for print forms |
| `version` | string | Version in "X.Y" format (e.g., "1.0") |
| `targets` | list | Full metadata names (e.g., `Документ.СчетНаОплату`) |
| `commands` | list | At least one command definition |

### Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `safe_mode` | boolean | `true` | Run in safe mode (recommended) |
| `information` | string | - | Description for administrator |

### BSP Types

| Type | Description |
|------|-------------|
| `print_form` | External print form (most common) |
| `object_filling` | Fill object with data |
| `creation_of_related` | Create related documents |
| `report` | Context report |
| `additional_processor` | Global processing |
| `additional_report` | Global report |

---

## Command Definition

### Required Command Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier (used in Печать handler) |
| `title` | object | Localized title (`ru:`, `uk:`, `en:`) |
| `usage` | string | Command type (see below) |

### Optional Command Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `modifier` | string | - | `ПечатьMXL` for spreadsheet, `ПечатьOFD` for Office |
| `show_notification` | boolean | `true` | Show "Executing..." message |
| `handler` | string | - | Custom handler name (default: `Печать{id}`) |

### Usage Types

| Value | Description |
|-------|-------------|
| `server_method` | Call `Печать()` on server (most common) |
| `client_method` | Call `Печать()` on client |
| `open_form` | Open processor form |

---

## Handler Patterns

### Pattern 1: Simple MXL Print (Most Common)

For tabular document (spreadsheet) output:

**config.yaml:**
```yaml
languages: [ru]

bsp:
  type: print_form
  version: "1.0"
  targets:
    - Документ.РеализацияТоваровУслуг
  commands:
    - id: Накладная
      title: "Накладная"
      usage: server_method
      modifier: ПечатьMXL
```

**handlers.bsl:**
```bsl
#Область МодульОбъекта

Функция ПечатьНакладная(МассивОбъектов, ОбъектыПечати)

    ТабличныйДокумент = Новый ТабличныйДокумент;
    ТабличныйДокумент.КлючПараметровПечати = "ПАРАМЕТРЫ_ПЕЧАТИ_Накладная";

    Макет = ПолучитьМакет("ПФ_MXL_Накладная");

    Для Каждого Ссылка Из МассивОбъектов Цикл

        НачалоОбласти = ТабличныйДокумент.ВысотаТаблицы + 1;

        Если ТабличныйДокумент.ВысотаТаблицы > 0 Тогда
            ТабличныйДокумент.ВывестиГоризонтальныйРазделительСтраниц();
        КонецЕсли;

        // Шапка
        Область = Макет.ПолучитьОбласть("Шапка");
        Область.Параметры.Номер = Ссылка.Номер;
        Область.Параметры.Дата = Формат(Ссылка.Дата, "ДЛФ=D");
        Область.Параметры.Контрагент = Ссылка.Контрагент;
        ТабличныйДокумент.Вывести(Область);

        // Табличная часть
        ОбластьСтрока = Макет.ПолучитьОбласть("Строка");
        Для Каждого СтрокаТЧ Из Ссылка.Товары Цикл
            ОбластьСтрока.Параметры.Номенклатура = СтрокаТЧ.Номенклатура;
            ОбластьСтрока.Параметры.Количество = СтрокаТЧ.Количество;
            ОбластьСтрока.Параметры.Цена = СтрокаТЧ.Цена;
            ОбластьСтрока.Параметры.Сумма = СтрокаТЧ.Сумма;
            ТабличныйДокумент.Вывести(ОбластьСтрока);
        КонецЦикла;

        // Подвал
        Область = Макет.ПолучитьОбласть("Подвал");
        Область.Параметры.Итого = Ссылка.Товары.Итог("Сумма");
        ТабличныйДокумент.Вывести(Область);

        УправлениеПечатью.ЗадатьОбластьПечатиДокумента(ТабличныйДокумент, НачалоОбласти, ОбъектыПечати, Ссылка);

    КонецЦикла;

    ТабличныйДокумент.АвтоМасштаб = Истина;

    Возврат ТабличныйДокумент;

КонецФункции

#КонецОбласти
```

### Pattern 2: Multiple Print Commands

One processor with several print forms:

**config.yaml:**
```yaml
languages: [ru]

bsp:
  type: print_form
  version: "1.0"
  targets:
    - Документ.ЗаказКлиента
  commands:
    - id: Счет
      title: "Счет на оплату"
      usage: server_method
      modifier: ПечатьMXL

    - id: СчетФактура
      title: "Счет-фактура"
      usage: server_method
      modifier: ПечатьMXL

    - id: Накладная
      title: "Товарная накладная"
      usage: server_method
      modifier: ПечатьMXL
```

**handlers.bsl:**
```bsl
#Область МодульОбъекта

Функция ПечатьСчет(МассивОбъектов, ОбъектыПечати)
    ТабличныйДокумент = Новый ТабличныйДокумент;
    Макет = ПолучитьМакет("ПФ_MXL_Счет");
    // ... формування ...
    Возврат ТабличныйДокумент;
КонецФункции

Функция ПечатьСчетФактура(МассивОбъектов, ОбъектыПечати)
    ТабличныйДокумент = Новый ТабличныйДокумент;
    Макет = ПолучитьМакет("ПФ_MXL_СчетФактура");
    // ... формування ...
    Возврат ТабличныйДокумент;
КонецФункции

Функция ПечатьНакладная(МассивОбъектов, ОбъектыПечати)
    ТабличныйДокумент = Новый ТабличныйДокумент;
    Макет = ПолучитьМакет("ПФ_MXL_Накладная");
    // ... формування ...
    Возврат ТабличныйДокумент;
КонецФункции

#КонецОбласти
```

> One function per command, all inside a single `#Область МодульОбъекта`. Names are matched by declaration, so `ПечатьСчет` and `ПечатьСчетФактура` do not collide.

### Pattern 3: Multiple Targets

Print form for several document types:

**config.yaml:**
```yaml
languages: [ru]

bsp:
  type: print_form
  version: "1.0"
  targets:
    - Документ.СчетНаОплатуПокупателю
    - Документ.РеализацияТоваровУслуг
    - Документ.ЗаказКлиента
  commands:
    - id: УниверсальныйСчет
      title: "Универсальный счет"
      usage: server_method
      modifier: ПечатьMXL
```

**handlers.bsl:**
```bsl
#Область МодульОбъекта

Функция ПечатьУниверсальныйСчет(МассивОбъектов, ОбъектыПечати)

    ТабличныйДокумент = Новый ТабличныйДокумент;
    Макет = ПолучитьМакет("ПФ_MXL_УниверсальныйСчет");

    Для Каждого Ссылка Из МассивОбъектов Цикл

        // Визначення типу документа
        ТипДокумента = ТипЗнч(Ссылка);

        Если ТипДокумента = Тип("ДокументСсылка.СчетНаОплатуПокупателю") Тогда
            ДанныеДокумента = ПолучитьДанныеСчета(Ссылка);
        ИначеЕсли ТипДокумента = Тип("ДокументСсылка.РеализацияТоваровУслуг") Тогда
            ДанныеДокумента = ПолучитьДанныеРеализации(Ссылка);
        Иначе
            ДанныеДокумента = ПолучитьДанныеЗаказа(Ссылка);
        КонецЕсли;

        // ... вивід в табличний документ ...

    КонецЦикла;

    Возврат ТабличныйДокумент;

КонецФункции

// Допоміжні функції теж живуть у цьому регіоні
Функция ПолучитьДанныеСчета(Ссылка)
    // ...
КонецФункции

#КонецОбласти
```

### Pattern 4: Word/Office Template — NOT generated automatically

⚠️ **Current limitation.** The generated `Печать()` procedure always routes results through
`УправлениеПечатью.ВывестиТабличныйДокументВКоллекцию(...)`, i.e. every command handler must return a
`ТабличныйДокумент`. There is no generated path that fills `ОфисныеДокументы`, so Word output cannot be
expressed through `bsp.commands` alone.

If you need Word output, supply the whole module yourself and skip the generated `Печать()`:

```yaml
object_module:
  file: object_module.bsl   # your own СведенияОВнешнейОбработке() + Печать()
```

For everything else prefer a spreadsheet template (Pattern 1 or 5) — that path is fully supported.

### Pattern 5: Excel Template (v2.63.0+)

For print forms with Excel-based templates - simplest for LLMs:

**config.yaml:**
```yaml
languages: [ru, uk]

processor:
  name: ПечатьКарточкиНоменклатуры

bsp:
  type: print_form
  version: "1.0"
  targets:
    - Справочник.Номенклатура
  commands:
    - id: КарточкаНоменклатуры
      title: "Карточка номенклатуры | Картка номенклатури"
      usage: server_method
      modifier: ПечатьMXL

templates:
  - name: ПФ_MXL_КарточкаНоменклатуры
    type: SpreadsheetDocument
    file: templates/card.xlsx  # ← Excel auto-converted to MXL!
```

**Excel file structure (`templates/card.xlsx`):**
- Named Range `Header` or `Заголовок` → document header area
- Named Range `Row` or `Строка` → repeating data row
- Parameters in cells: `{Код}`, `{Наименование}`, `{Артикул}`

**handlers.bsl:**
```bsl
#Область МодульОбъекта

Функция ПечатьКарточкаНоменклатуры(МассивОбъектов, ОбъектыПечати)

    ТабличныйДокумент = Новый ТабличныйДокумент;

    Макет = ПолучитьМакет("ПФ_MXL_КарточкаНоменклатуры");
    ОбластьЗаголовок = Макет.ПолучитьОбласть("Заголовок");
    ОбластьДанные = Макет.ПолучитьОбласть("Строка");

    Для Каждого Ссылка Из МассивОбъектов Цикл
        НачалоОбласти = ТабличныйДокумент.ВысотаТаблицы + 1;

        ОбластьЗаголовок.Параметры.Наименование = Ссылка.Наименование;
        ТабличныйДокумент.Вывести(ОбластьЗаголовок);

        ОбластьДанные.Параметры.Код = Ссылка.Код;
        ОбластьДанные.Параметры.Артикул = Ссылка.Артикул;
        ТабличныйДокумент.Вывести(ОбластьДанные);

        УправлениеПечатью.ЗадатьОбластьПечатиДокумента(ТабличныйДокумент, НачалоОбласти, ОбъектыПечати, Ссылка);
    КонецЦикла;

    Возврат ТабличныйДокумент;

КонецФункции

#КонецОбласти
```

> **Note:** Excel auto-conversion requires `openpyxl`: `pip install openpyxl>=3.1.0`

### Pattern 6: Programmatic Print (No Template)

For simple cards without external template - pure BSL:

**config.yaml:**
```yaml
languages: [ru]

processor:
  name: ПечатьКарточкиПрограммно

bsp:
  type: print_form
  version: "1.0"
  targets:
    - Справочник.Номенклатура
  commands:
    - id: КарточкаПрограммно
      title: "Карточка (программно)"
      usage: server_method
      modifier: ПечатьMXL
# NO templates: section - everything in BSL!
```

**handlers.bsl:**
```bsl
#Область МодульОбъекта

Функция ПечатьКарточкаПрограммно(МассивОбъектов, ОбъектыПечати)

ТабличныйДокумент = Новый ТабличныйДокумент;

Для Каждого Ссылка Из МассивОбъектов Цикл

    // Розділювач сторінок
    Если ТабличныйДокумент.ВысотаТаблицы > 0 Тогда
        ТабличныйДокумент.ВывестиГоризонтальныйРазделительСтраниц();
    КонецЕсли;

    // Заголовок
    Область = ТабличныйДокумент.Область(ТабличныйДокумент.ВысотаТаблицы + 1, 1, , 2);
    Область.Объединить();
    Область.Текст = "КАРТКА НОМЕНКЛАТУРИ";
    Область.Шрифт = Новый Шрифт(, 14, Истина);
    Область.ГоризонтальноеПоложение = ГоризонтальноеПоложение.Центр;

    // Назва
    Область = ТабличныйДокумент.Область(ТабличныйДокумент.ВысотаТаблицы + 1, 1, , 2);
    Область.Объединить();
    Область.Текст = Ссылка.Наименование;
    Область.Шрифт = Новый Шрифт(, 12, Истина);
    Область.ГоризонтальноеПоложение = ГоризонтальноеПоложение.Центр;

    // Пустий рядок
    ТабличныйДокумент.Область(ТабличныйДокумент.ВысотаТаблицы + 1, 1).Текст = "";

    // Дані
    ВивестиРядок(ТабличныйДокумент, "Код:", Ссылка.Код);
    ВивестиРядок(ТабличныйДокумент, "Артикул:", Ссылка.Артикул);
    ВивестиРядок(ТабличныйДокумент, "Повна назва:", Ссылка.НаименованиеПолное);
    ВивестиРядок(ТабличныйДокумент, "Вид номенклатури:", Строка(Ссылка.ВидНоменклатуры));
    ВивестиРядок(ТабличныйДокумент, "Одиниця виміру:", Строка(Ссылка.ЕдиницаИзмерения));

КонецЦикла;

ТабличныйДокумент.АвтоМасштаб = Истина;

Возврат ТабличныйДокумент;

КонецФункции

// Допоміжна процедура для виведення рядка даних - у тому самому регіоні
Процедура ВивестиРядок(ТабДок, Заголовок, Значение)
    НомерРядка = ТабДок.ВысотаТаблицы + 1;

    ОбластьЗаголовок = ТабДок.Область(НомерРядка, 1);
    ОбластьЗаголовок.Текст = Заголовок;
    ОбластьЗаголовок.Шрифт = Новый Шрифт(, 10, Истина);
    ОбластьЗаголовок.ШиринаКолонки = 25;

    ОбластьЗначение = ТабДок.Область(НомерРядка, 2);
    ОбластьЗначение.Текст = Значение;
    ОбластьЗначение.ШиринаКолонки = 50;
КонецПроцедуры

#КонецОбласти
```

> **Tip:** Programmatic approach is best for simple forms (5-10 fields). For complex layouts with borders, logos, merged cells - use Excel template (Pattern 5).

---

## Templates (Макети)

### MXL Template Naming

Template names MUST follow BSP convention:
- `ПФ_MXL_` prefix for spreadsheet templates
- `ПФ_DOC_` prefix for Word templates

**config.yaml:**
```yaml
templates:
  - name: ПФ_MXL_Счет
    type: SpreadsheetDocument

  - name: ПФ_DOC_Договор
    type: ActiveDocument
```

### MXL Template Areas

Standard area structure:
```
Шапка           - Header (company, document number, date)
ШапкаТаблицы    - Table header row
Строка          - Table row (repeated for each item)
Подвал          - Footer (totals, signatures)
```

---

## Handler Signature

The generator writes `СведенияОВнешнейОбработке()` and the dispatching `Печать()` procedure. You write one
function per command — **with its full signature** — inside `#Область МодульОбъекта`.

```bsl
Функция Печать<CommandId>(МассивОбъектов, ОбъектыПечати)
    ТабличныйДокумент = Новый ТабличныйДокумент;
    // ...
    Возврат ТабличныйДокумент;
КонецФункции
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `МассивОбъектов` | Array | References to the objects being printed |
| `ОбъектыПечати` | ValueList | Object ↔ printed area mapping; pass it to `УправлениеПечатью.ЗадатьОбластьПечатиДокумента` |

**Return value:** `ТабличныйДокумент` — the function creates it and returns it. It is *not* passed in.

### Handler Naming Convention

Default: `Печать{CommandId}`

Examples:
- Command `id: СчетНаОплату` → Handler `ПечатьСчетНаОплату`
- Command `id: Накладная` → Handler `ПечатьНакладная`

Custom handler name (supported since v2.78.0):
```yaml
commands:
  - id: СчетНаОплату
    handler: МояФункцияПечати  # Custom name
```

---

## Complete Example

### Invoice Print Form

**config.yaml:**
```yaml
languages: [ru, uk]

processor:
  name: ПечатьСчетаВнешняя
  synonym: "Печать счета (внешняя) | Друк рахунку (зовнішня)"

bsp:
  type: print_form
  version: "1.0"
  safe_mode: true
  information: "Внешняя печатная форма счета на оплату для документов продажи"

  targets:
    - Документ.СчетНаОплатуПокупателю
    - Документ.РеализацияТоваровУслуг

  commands:
    - id: СчетНаОплату
      title: "Счет на оплату | Рахунок на оплату"
      usage: server_method
      modifier: ПечатьMXL
      show_notification: false

templates:
  - name: ПФ_MXL_СчетНаОплату
    type: SpreadsheetDocument
```

**handlers.bsl:**
```bsl
#Область МодульОбъекта

Функция ПечатьСчетНаОплату(МассивОбъектов, ОбъектыПечати)

ТабличныйДокумент = Новый ТабличныйДокумент;
ТабличныйДокумент.КлючПараметровПечати = "ПАРАМЕТРЫ_ПЕЧАТИ_СчетНаОплату";

Макет = ПолучитьМакет("ПФ_MXL_СчетНаОплату");

ОбластьШапка = Макет.ПолучитьОбласть("Шапка");
ОбластьШапкаТаблицы = Макет.ПолучитьОбласть("ШапкаТаблицы");
ОбластьСтрока = Макет.ПолучитьОбласть("Строка");
ОбластьПодвал = Макет.ПолучитьОбласть("Подвал");

НомерСтроки = 0;

Для Каждого Ссылка Из МассивОбъектов Цикл

    НачалоОбласти = ТабличныйДокумент.ВысотаТаблицы + 1;

    // Розділювач сторінок для кількох документів
    Если ТабличныйДокумент.ВысотаТаблицы > 0 Тогда
        ТабличныйДокумент.ВывестиГоризонтальныйРазделительСтраниц();
    КонецЕсли;

    // Шапка
    ОбластьШапка.Параметры.НомерДокумента = Ссылка.Номер;
    ОбластьШапка.Параметры.ДатаДокумента = Формат(Ссылка.Дата, "ДЛФ=D");
    ОбластьШапка.Параметры.Контрагент = Ссылка.Контрагент;
    ОбластьШапка.Параметры.Организация = Ссылка.Организация;
    ТабличныйДокумент.Вывести(ОбластьШапка);

    // Шапка таблиці
    ТабличныйДокумент.Вывести(ОбластьШапкаТаблицы);

    // Товари
    НомерСтроки = 0;
    ИтогоСумма = 0;

    Для Каждого СтрокаТовара Из Ссылка.Товары Цикл
        НомерСтроки = НомерСтроки + 1;

        ОбластьСтрока.Параметры.НомерСтроки = НомерСтроки;
        ОбластьСтрока.Параметры.Номенклатура = СтрокаТовара.Номенклатура;
        ОбластьСтрока.Параметры.Количество = СтрокаТовара.Количество;
        ОбластьСтрока.Параметры.Цена = СтрокаТовара.Цена;
        ОбластьСтрока.Параметры.Сумма = СтрокаТовара.Сумма;

        ИтогоСумма = ИтогоСумма + СтрокаТовара.Сумма;

        ТабличныйДокумент.Вывести(ОбластьСтрока);
    КонецЦикла;

    // Підсумки
    ОбластьПодвал.Параметры.ИтогоСумма = ИтогоСумма;
    ОбластьПодвал.Параметры.СуммаПрописью = ЧислоПрописью(ИтогоСумма, "Л=ru_RU");
    ТабличныйДокумент.Вывести(ОбластьПодвал);

    УправлениеПечатью.ЗадатьОбластьПечатиДокумента(ТабличныйДокумент, НачалоОбласти, ОбъектыПечати, Ссылка);

КонецЦикла;

ТабличныйДокумент.АвтоМасштаб = Истина;
ТабличныйДокумент.ОриентацияСтраницы = ОриентацияСтраницы.Портрет;

Возврат ТабличныйДокумент;

КонецФункции

#КонецОбласти
```

---

## Generation Command

```bash
python -m 1c_processor_generator yaml \
  --config config.yaml \
  --handlers-file handlers.bsl \
  --output output/ \
  --output-format epf
```

---

## Common Mistakes

### 0. Handler outside `#Область МодульОбъекта` (most common — silently prints nothing)

```bsl
// WRONG - loaded, then dropped; ObjectModule gets a TODO stub
Функция ПечатьСчет(МассивОбъектов, ОбъектыПечати)
    ...
КонецФункции

// WRONG - body only, no signature; nothing is extracted at all
Макет = ПолучитьМакет("ПФ_MXL_Счет");
...

// WRONG - directives are a form module concept, invalid in ObjectModule
&НаСервере
Функция ПечатьСчет(МассивОбъектов, ОбъектыПечати)

// CORRECT
#Область МодульОбъекта

Функция ПечатьСчет(МассивОбъектов, ОбъектыПечати)
    ТабличныйДокумент = Новый ТабличныйДокумент;
    ...
    Возврат ТабличныйДокумент;
КонецФункции

#КонецОбласти
```

Symptom if you get this wrong: generation succeeds, the .epf compiles and opens, the print command appears
in 1C — and prints an empty document. Since v2.78.0 the CLI reports this as a warning instead of staying silent.

### 1. Missing modifier for MXL

```yaml
# WRONG - no modifier
commands:
  - id: Счет
    usage: server_method

# CORRECT
commands:
  - id: Счет
    usage: server_method
    modifier: ПечатьMXL
```

### 2. Wrong template name prefix

```yaml
# WRONG
templates:
  - name: Счет  # Missing prefix

# CORRECT
templates:
  - name: ПФ_MXL_Счет
```

### 3. Using Объект instead of direct reference

```bsl
// WRONG - Объект не існує в контексті друку
Для Каждого Строка Из Объект.Товары Цикл

// CORRECT - використовувати Ссылка
Для Каждого Строка Из Ссылка.Товары Цикл
```

### 4. Missing page break for multiple documents

```bsl
// WRONG - всі документи на одній сторінці
Для Каждого Ссылка Из МассивОбъектов Цикл
    // друк...
КонецЦикла;

// CORRECT - розділювач сторінок
Для Каждого Ссылка Из МассивОбъектов Цикл
    Если ТабличныйДокумент.ВысотаТаблицы > 0 Тогда
        ТабличныйДокумент.ВывестиГоризонтальныйРазделительСтраниц();
    КонецЕсли;
    // друк...
КонецЦикла;
```

### 5. Wrong target format

```yaml
# WRONG - English names
targets:
  - Document.Invoice

# CORRECT - 1C metadata names
targets:
  - Документ.СчетНаОплату
```

---

## PRO License Required

BSP Integration is a PRO feature. Ensure valid license before generation.

---

## See Also

- [LLM_CORE.md](LLM_CORE.md) - Core LLM instructions
- [LLM_PATTERNS_ESSENTIAL.md](LLM_PATTERNS_ESSENTIAL.md) - UI patterns
- [examples/yaml/bsp_print_form/](../examples/yaml/bsp_print_form/) - Working example
