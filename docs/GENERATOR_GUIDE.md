# Генератор зовнішніх обробок 1C - Повна інструкція

> **⚠️ ВАЖЛИВО: Python API застарів (v2.7.3+)**
>
> **Рекомендовано використовувати YAML API** для всіх нових проєктів:
> - 📖 **Основна документація:** [YAML_GUIDE.md](YAML_GUIDE.md)
> - ⚡ **Швидкий старт для LLM:** [LLM_PROMPT.md](../LLM_PROMPT.md)
> - 🎯 **Cheatsheet:** [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
>
> **Python API** залишається для backward compatibility, але може мати обмеження.
> Приклади нижче показують legacy підхід (до v2.0.0) та новий підхід (v2.0.0+).

## Огляд

Автоматичний генератор зовнішніх обробок для 1C:Enterprise 8.3 на основі Python.

**Переваги:**
- ⚡ Створення обробки за **1-2 хвилини** (замість 20-40 хвилин вручну)
- ✅ **0% помилок** - автоматична валідація UUID, ID, структури
- 🎯 **100% валідний код** - готовий до відкриття в 1C
- 🔧 Підтримка різних версій платформи (2.11, 2.18)

**Рекомендації:**
- ✅ Для нових проєктів: використовуйте **YAML API** (простіше, швидше, краще для LLM)
- ⚠️ Для існуючих проєктів: Python API працює, але розгляньте міграцію на YAML

## Встановлення

### 1. Встановіть залежності

```bash
cd .claude/tools/1c_processor_generator
pip install -r requirements.txt
```

Потрібні бібліотеки:
- `jinja2>=3.1.0` - для генерації XML з шаблонів
- `pyyaml>=6.0` - для читання конфігураційних файлів (опціонально)

### 2. Перевірте встановлення

```bash
python -m 1c_processor_generator
```

Має вивести інструкцію використання.

## Швидкий старт

### Мінімальна обробка (30 секунд)

```bash
cd .claude/tools
python -m 1c_processor_generator minimal МояОбробка
```

**Що створюється:**
- Один реквізит типу `string`
- Одне поле вводу на формі
- Всі необхідні BSL модулі
- Валідна структура папок

**Результат:**
```
МояОбробка.xml
МояОбробка/
├── Ext/
│   └── ObjectModule.bsl
└── Forms/
    └── Форма/
        ├── Форма.xml
        └── Ext/
            ├── Form.xml
            └── Form/
                └── Module.bsl
```

### Відкрити в 1C

1. Запустіть 1C:Enterprise 8.3
2. **Файл → Відкрити** (Ctrl+O)
3. Виберіть `МояОбробка.xml`
4. Готово! ✅

## Використання через код Python

### Приклад 1: Мінімальна обробка

```python
from 1c_processor_generator import ProcessorGenerator, create_minimal_processor

# Створити мінімальну обробку
processor = create_minimal_processor("МояОбработка", platform_version="2.11")

# Згенерувати
generator = ProcessorGenerator(processor)
generator.generate("./output")
```

### Приклад 2: Обробка з табличною частиною

> **⚠️ ВАЖЛИВО:** Для форм з елементами рекомендуємо **YAML API** (простіше):
> ```bash
> python -m 1c_processor_generator yaml --config config.yaml --handlers-file handlers.bsl
> ```
> Приклад YAML конфігурації: [examples/yaml/](../examples/yaml/)

**Python API (v2.0.0+):**

```python
from 1c_processor_generator import ProcessorGenerator, Processor, Column, FormElement

# Створити обробку
processor = Processor(
    name="КопированиеГруппДоступа",
    synonym_ru="Копирование групп доступа",
    synonym_uk="Копіювання груп доступу",
    platform_version="2.11",
)

# Додати реквізити
processor.add_attribute(
    name="ИсходныйПользователь",
    type="CatalogRef.Пользователи",
    synonym_ru="Исходный пользователь",
    synonym_uk="Вихідний користувач",
)

processor.add_attribute(
    name="ЦелевойПользователь",
    type="CatalogRef.Пользователи",
    synonym_ru="Целевой пользователь",
    synonym_uk="Цільовий користувач",
)

# Додати табличну частину
ts = processor.add_tabular_section(
    name="ГруппыДоступа",
    synonym_ru="Группы доступа",
    synonym_uk="Групи доступу",
)

# Додати колонки
ts.columns.append(Column(
    name="Создать",
    type="boolean",
    synonym_ru="Создать",
    synonym_uk="Створити",
))

ts.columns.append(Column(
    name="ГруппаДоступа",
    type="CatalogRef.ГруппыДоступа",
    synonym_ru="Группа доступа",
    synonym_uk="Група доступу",
))

# Створити форму (NEW API v2.0.0+)
form = processor.add_form("Форма", default=True)

# Додати елементи до форми
form.elements.append(FormElement(
    element_type="InputField",
    name="ИсходныйПользователь",
    attribute="ИсходныйПользователь",
))

form.elements.append(FormElement(
    element_type="InputField",
    name="ЦелевойПользователь",
    attribute="ЦелевойПользователь",
))

form.elements.append(FormElement(
    element_type="Table",
    name="ГруппыДоступа",
    tabular_section="ГруппыДоступа",
))

# Згенерувати
generator = ProcessorGenerator(processor)
generator.generate("./output")
```

## Типи даних

### Базові типи

| Python тип | 1C тип | Приклад |
|------------|--------|---------|
| `"string"` | xs:string | Текстовий рядок |
| `"boolean"` | xs:boolean | Так/Ні |
| `"number"` | xs:decimal | Число |
| `"date"` | xs:dateTime | Дата та час |

### Довідникові типи

```python
# Конкретний довідник
type="CatalogRef.Пользователи"
type="CatalogRef.ГруппыДоступа"
type="CatalogRef.Номенклатура"
type="CatalogRef.Контрагенты"

# Загальний тип CatalogRef (будь-який довідник)
type="CatalogRef"
```

### Документові типи

```python
# Конкретний документ
type="DocumentRef.РеализацияТоваровУслуг"
type="DocumentRef.ПоступлениеТоваровУслуг"

# Загальний тип DocumentRef (будь-який документ)
type="DocumentRef"
```

### Перерахування

```python
# Конкретне перерахування
type="EnumRef.СтатусыДокументов"
type="EnumRef.ТипыЦен"
```

### Параметри типів

**Для string:**
```python
processor.add_attribute(
    name="НазваРядка",
    type="string",
    length=150,  # Довжина рядка
)
```

**Для number:**
```python
processor.add_attribute(
    name="Сумма",
    type="number",
    digits=15,  # Загальна кількість цифр
    fraction_digits=2,  # Десяткових знаків
)
```

## Валідація

Генератор автоматично перевіряє:

✅ **UUID:**
- Тільки hex-символи (0-9, a-f)
- Правильний формат (8-4-4-4-12)
- Унікальність UUID

✅ **Назви:**
- PascalCase
- Починаються з великої літери
- Без пробілів

✅ **Структура:**
- Коректні ID елементів форми
- Правильні посилання на атрибути
- Валідні типи даних

Якщо є помилки, генератор їх покаже:

```
❌ Помилки валідації:
   - Назва обробки: Назва обробки 'моя обробка' має починатися з великої літери (PascalCase)
   - UUID #3: UUID містить невалідні символи: g, h
```

## Що генерується автоматично

### 1. UUID

Всі UUID генеруються автоматично:
- ✅ Main UUID обробки
- ✅ ObjectId
- ✅ TypeId і ValueId
- ✅ UUID форми
- ✅ UUID кожного атрибута
- ✅ UUID табличних частин і колонок

**ClassId НЕ ЗМІНЮЄТЬСЯ** - це константа платформи!

### 2. ID елементів форми

Автоматична нумерація з урахуванням патернів:
- AutoCommandBar: -1
- Інші елементи: 1, 2, 3, ...
- Кожен елемент + ContextMenu + ExtendedTooltip

### 3. Іменування

Автоматичні суфікси по конвенціям 1C:
- `ИмяПоляКонтекстноеМеню`
- `ИмяПоляРасширеннаяПодсказка`
- `ИмяТаблицыКоманднаяПанель`

### 4. BSL модулі

З правильною структурою областей:
```bsl
#Область ПрограммныйИнтерфейс
// Публічні функції
#КонецОбласті

#Область СлужебныеПроцедурыИФункции
// Приватні функції
#КонецОбласті
```

## Приклад 3: ValueTable з CurrentData

> **⚠️ Рекомендуємо YAML API:** [Приклад з ValueTable](../examples/yaml/sales_report/)

**Python API (v2.0.0+):**

```python
from 1c_processor_generator import Processor, Column, ProcessorGenerator, FormElement, ValueTableAttribute

processor = Processor(
    name="ТестValueTable",
    synonym_ru="Тест ValueTable",
    synonym_uk="Тест ValueTable",
    platform_version="2.18",
)

# Створити форму
form = processor.add_form("Форма", default=True)

# Властивості форми
form.properties["Title"] = True
form.properties["Title_ru"] = "Тестирование ValueTable"
form.properties["Title_uk"] = "Тестування ValueTable"
form.properties["AutoTitle"] = False

# ValueTable атрибут форми
vt_attr = ValueTableAttribute(
    name="СписокТоваров",
    title_ru="Список товаров",
    title_uk="Список товарів",
)

# Додаємо колонки до ValueTable
vt_attr.columns.append(Column(
    name="Наименование",
    type="string",
    synonym_ru="Наименование",
    synonym_uk="Найменування",
    length=150,
))

vt_attr.columns.append(Column(
    name="Номенклатура",
    type="CatalogRef.Номенклатура",
    synonym_ru="Номенклатура",
    synonym_uk="Номенклатура",
))

vt_attr.columns.append(Column(
    name="ДокументПоставки",
    type="DocumentRef",  # Загальний тип - будь-який документ
    synonym_ru="Документ поставки",
    synonym_uk="Документ постачання",
))

vt_attr.columns.append(Column(
    name="Комментарий",
    type="string",
    synonym_ru="Комментарий",
    synonym_uk="Коментар",
    length=500,
))

# Додати ValueTable до форми
form.value_table_attributes.append(vt_attr)

# Таблиця для відображення ValueTable
form.elements.append(FormElement(
    element_type="Table",
    name="СписокТоваров",
    tabular_section="СписокТоваров",
    properties={"is_value_table": True},
))

# LabelField з посиланням на CurrentData (коментар поточного рядка)
form.elements.append(FormElement(
    element_type="LabelField",
    name="КомментарийПоле",
    properties={
        "data_path": "Items.СписокТоваров.CurrentData.Комментарий",
    },
))

# Події форми
form.events["OnCreateAtServer"] = "ПриСозданииНаСервере"

generator = ProcessorGenerator(processor)
generator.generate("./output")
```

**Особливості ValueTable:**
- ValueTable - це атрибут форми, не об'єкта обробки
- `is_value_table=True` вказує що це ValueTable, не TabularSection
- CurrentData дозволяє посилатися на поточний рядок таблиці
- Підтримка складних типів: CatalogRef, DocumentRef, EnumRef

## Приклад 4: Pages (вкладки)

> **⚠️ ДУЖЕ рекомендуємо YAML API для складних форм:** [Приклад з Pages](../examples/yaml/data_import/)
>
> Python API для Pages дуже багатослівний - YAML набагато компактніше!

**Python API (v2.0.0+) - складний варіант:**

```python
from 1c_processor_generator import Processor, Column, ProcessorGenerator, FormElement, FormGroup, ValueTableAttribute

processor = Processor(
    name="ТестPages",
    synonym_ru="Тест вкладок",
    synonym_uk="Тест вкладок",
    platform_version="2.18",
)

# Атрибути
processor.add_attribute(name="Текст1", type="string", length=200)
processor.add_attribute(name="Текст2", type="string", length=200)

# Створити форму
form = processor.add_form("Форма", default=True)

# ValueTable для другої вкладки
vt_attr = ValueTableAttribute(name="СписокДанных")
vt_attr.columns.append(Column(name="Наименование", type="string", length=100))
form.value_table_attributes.append(vt_attr)

# Pages з вкладками
pages_element = FormElement(
    element_type="Pages",
    name="ГруппаВкладок",
    properties={
        "pages_representation": "TabsOnTop",  # або "TabsOnBottom"
    },
)

# Вкладка 1
page1 = FormGroup(
    name="ВкладкаОсновная",
    properties={
        "title_ru": "Основная",
        "title_uk": "Основна",
    },
)
page1.child_items.append(FormElement(
    element_type="InputField",
    name="Текст1",
    attribute="Текст1",
))

# Вкладка 2
page2 = FormGroup(
    name="ВкладкаДополнительная",
    properties={
        "title_ru": "Дополнительная",
        "title_uk": "Додаткова",
    },
)
page2.child_items.append(FormElement(
    element_type="InputField",
    name="Текст2",
    attribute="Текст2",
))
page2.child_items.append(FormElement(
    element_type="Table",
    name="СписокДанных",
    tabular_section="СписокДанных",
    properties={"is_value_table": True},
))

pages_element.child_items = [page1, page2]
form.elements.append(pages_element)

generator = ProcessorGenerator(processor)
generator.generate("./output")
```

**Для порівняння - той самий функціонал у YAML (набагато коротше!):**

```yaml
forms:
  - name: Форма
    default: true
    value_tables:
      - name: СписокДанных
        columns:
          - {name: Наименование, type: string, length: 100}
    elements:
      - type: Pages
        name: ГруппаВкладок
        pages_representation: TabsOnTop
        pages:
          - name: ВкладкаОсновная
            title: Основная
            child_items:
              - {type: InputField, name: Текст1, attribute: Текст1}
          - name: ВкладкаДополнительная
            title: Дополнительная
            child_items:
              - {type: InputField, name: Текст2, attribute: Текст2}
              - {type: Table, name: СписокДанных, tabular_section: СписокДанных, is_value_table: true}
```

## Приклад 5: Команди та кнопки

> **⚠️ Рекомендуємо YAML API:** [Приклад з командами](../examples/yaml/sales_report/)

**Python API (v2.0.0+):**

```python
from 1c_processor_generator import Processor, ProcessorGenerator, Command, FormElement

processor = Processor(
    name="ТестКоманд",
    synonym_ru="Тест команд",
    synonym_uk="Тест команд",
)

# Створити форму
form = processor.add_form("Форма", default=True)

# Додати команди до форми
form.commands.append(Command(
    name="Обновить",
    title_ru="Обновить",
    title_uk="Оновити",
    handler="ОбновитьДанные",  # Ім'я методу-обробника
    tooltip_ru="Обновить данные",
    tooltip_uk="Оновити дані",
    picture="StdPicture.Refresh",
    shortcut="F5",
))

form.commands.append(Command(
    name="ВыполнитьОбработку",
    title_ru="Выполнить",
    title_uk="Виконати",
    handler="ВыполнитьОбработку",
    picture="StdPicture.ExecuteTask",
    shortcut="Ctrl+Enter",
))

# Додати кнопку на форму
form.elements.append(FormElement(
    element_type="Button",
    name="КнопкаОбновить",
    command="Обновить",
    properties={
        "representation": "Auto",
    },
))

# Події форми
form.events["OnOpen"] = "ПриОткрытии"

generator = ProcessorGenerator(processor)
generator.generate("./output")
```

**Згенерується BSL модуль:**
```bsl
&НаКлиенте
Процедура ОбновитьДанные(Команда)
    // Вставить содержимое обработчика.
КонецПроцедуры

&НаКлиенте
Процедура ВыполнитьОбработку(Команда)
    // Вставить содержимое обработчика.
КонецПроцедуры

&НаСервере
Процедура ПриОткрытии(Отказ, СтандартнаяОбработка)
    // Вставить содержимое обработчика.
КонецПроцедуры
```

## Приклад 6: UsualGroup з вкладеними елементами

> **⚠️ Рекомендуємо YAML API:** набагато читабельніше для вкладених структур

**Python API (v2.0.0+):**

```python
from 1c_processor_generator import FormElement, FormGroup

# Створити UsualGroup
group = FormElement(
    element_type="UsualGroup",
    name="ГруппаРеквизитов",
    properties={
        "title": "Параметри обробки",
        "behavior": "Collapsible",  # Група згортається
        "representation": "NormalSeparation",
        "show_title": True,
    },
)

# Додати дочірні елементи
group.child_items = [
    FormElement(
        element_type="InputField",
        name="Параметр1",
        attribute="Параметр1",
    ),
    FormElement(
        element_type="LabelField",
        name="Подсказка",
        properties={
            "title": "Виберіть значення параметра",
        },
    ),
    FormElement(
        element_type="Button",
        name="КнопкаДействия",
        command="ВыполнитьДействие",
    ),
]

# Додати групу до форми
form.elements.append(group)
```

## Приклад 7: LabelField з гіперпосиланням

**Python API (v2.0.0+):**

```python
from 1c_processor_generator import FormElement

# LabelField з гіперпосиланням та обробником кліку
label_element = FormElement(
    element_type="LabelField",
    name="СсылкаПомощь",
    properties={
        "title": "Довідка по обробці",
        "hyperlink": True,
    },
)

# Додати обробник події Click
label_element.events = {
    "Click": "СсылкаПомощьНажатие",
}

form.elements.append(label_element)

# Автоматично згенерується в Module.bsl як:
# &НаКлиенте
# Процедура СсылкаПомощьНажатие(Элемент)
#     // Вставить содержимое обработчика.
# КонецПроцедуры
```

## Обмеження Python API

> **⚠️ ВАЖЛИВО:** Більшість обмежень не стосуються YAML API!
> YAML API підтримує всі функції (DynamicList, RadioButtonField, CheckBoxField, тощо).

**Python API обмеження (v2.7.3):**

❌ **Не підтримується в Python API:**
- DynamicList атрибути (⚠️ але працює в YAML!)
- RadioButtonField, CheckBoxField (⚠️ але працює в YAML!)
- ChoiceList для InputField (⚠️ але працює в YAML!)
- Popup меню (⚠️ але працює в YAML!)
- Інтерактивний режим
- Генерація з існуючої обробки (reverse engineering)

✅ **Підтримується в обох API (Python + YAML):**
- Реквізити (всі базові типи + складні типи)
- Табличні частини з колонками
- ValueTable атрибути форми
- InputField, LabelField, LabelDecoration
- Table (TabularSection і ValueTable)
- Button з командами
- UsualGroup (з Behavior="Collapsible")
- Pages/Page (вкладки)
- CurrentData (посилання на поточний рядок)
- Обробники подій (форми та елементів)
- Автоматична валідація
- BSL injection (завантаження коду з файлів)
- Multi-forms підтримка (v2.0.0+)

**Рекомендація:** Для нових проєктів використовуйте **YAML API** - він підтримує всі функції!

## Поширені помилки

### Помилка: "UUID містить невалідні символи"

**Причина:** Спроба вручну вказати UUID з невалідними символами

**Рішення:** Не вказуйте UUID - вони генеруються автоматично

### Помилка: "Назва має починатися з великої літери"

**Причина:** Назва обробки не PascalCase

**Рішення:**
```python
# ❌ Неправильно
processor = Processor(name="моя обробка")

# ✅ Правильно
processor = Processor(name="МояОбработка")
```

## Порівняння: вручну vs генератор

| Параметр | Вручну | Генератор |
|----------|--------|-----------|
| Час створення | 20-40 хв | 1-2 хв |
| Помилки UUID | ~100% | 0% |
| Валідація | Немає | Автоматична |
| Складність | Висока | Низька |

## Приклади використання

Див. теку `examples/` для повних прикладів:
- `minimal.py` - Мінімальна обробка
- `with_table.py` - З табличною частиною
- `copy_access_groups.py` - Копіювання груп доступу

## Подальший розвиток

Заплановано:
- [ ] DynamicList підтримка (MainTable, QueryText)
- [ ] YAML конфігурація для швидкого створення
- [ ] Інтерактивний CLI режим
- [ ] Зворотна генерація (XML → Python)
- [ ] Підтримка більше типів елементів форми
- [ ] Діаграми та графіки
- [ ] Умовне оформлення

---

**Версія:** 2.7.3 (оновлено: 14.10.2025)
**Python API версія:** 2.0.0+ (legacy)
**Рекомендовано:** YAML API (підтримує всі функції)

> **📚 Актуальна документація:**
> - [YAML_GUIDE.md](YAML_GUIDE.md) - **ОСНОВНА ДОКУМЕНТАЦІЯ**
> - [LLM_PROMPT.md](../LLM_PROMPT.md) - Для LLM (Claude, GPT)
> - [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Cheatsheet

## Історія версій (Python API)

### Версія 2.7.3 (14.10.2025)
- ♻️ Рефакторинг: рекурсивна обробка елементів форми
- 🧹 Cleanup: видалено deprecated методи (add_form_element, add_command, тощо)
- ⚠️ **Python API застарів** - рекомендовано YAML API

### Версія 2.0.0 (07.10.2025)

### Нові можливості

**ValueTable підтримка:**
- ValueTable атрибути форми (не тільки TabularSection)
- Складні типи: CatalogRef, DocumentRef, EnumRef
- Загальні типи: CatalogRef, DocumentRef (будь-який довідник/документ)
- CurrentData - посилання на поточний рядок таблиці

**Pages і вкладки:**
- Pages з PagesRepresentation (TabsOnTop/TabsOnBottom)
- Page елементи з власними заголовками
- Вкладені елементи всередині вкладок
- Повна підтримка таблиць у вкладках

**Групи елементів:**
- UsualGroup з Behavior="Collapsible" (групи що згортаються)
- Вкладені елементи в групах
- Підтримка InputField, LabelField, Button всередині груп

**Команди та події:**
- Команди з Title, ToolTip (ru/uk)
- Picture (StdPicture, CommonPicture)
- Shortcut (F5, Ctrl+S, тощо)
- Автоматична генерація BSL обробників команд
- Обробники подій форми (OnOpen, OnCreateAtServer)
- Обробники подій елементів (Click, OnChange)

**Інші покращення:**
- LabelField з гіперпосиланнями
- LabelDecoration для декоративного тексту
- Button елементи на формі
- Власний DataPath для LabelField (для CurrentData)
