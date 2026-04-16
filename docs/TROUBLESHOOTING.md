# Troubleshooting Guide

Цей документ описує найпоширеніші проблеми при генерації EPF файлів та їх вирішення.

## Зміст
- [XDTO помилки (XML Schema)](#xdto-помилки-xml-schema)
- [BSL валідація](#bsl-валідація)
- [Configuration Mode](#configuration-mode)
- [XML форматування](#xml-форматування)

---

## XDTO помилки (XML Schema)

### Симптоми
```
Ошибка загрузки документа.
Исключение XDTO произошло при чтении файла- Form.xml
```

### Причина 1: cfg: префікс у ExternalDataProcessorObject

**Помилка:**
```xml
<v8:Type>cfg:ExternalDataProcessorObject.ProcessorName</v8:Type>
```

**Правильно:**
```xml
<v8:Type>ExternalDataProcessorObject.ProcessorName</v8:Type>
```

**Пояснення:**
- `cfg:` префікс потрібен ТІЛЬКИ для `CatalogRef.*` та `DocumentRef.*`
- `ExternalDataProcessorObject` НІКОЛИ не потребує `cfg:` префікса
- Це відбувається автоматично при генерації через шаблон `form.xml.j2`

**Виправлення:** Оновіть до версії 2.11.1+, де ця проблема виправлена.

---

### Причина 2: Склеєні XML теги (Jinja2 whitespace)

**Помилка:**
```xml
version="2.18">	<AutoCommandBar name="...">	</AutoCommandBar>	<Events>
```

Всі теги на одному рядку через `{%-` у Jinja2, який видаляє newlines.

**Виправлення:** Оновіть до версії 2.11.1+, де застосовується автоматичне XML форматування:

```python
# generator.py - post-processing
content = re.sub(r'(>)(\t|<)', r'\1\n\2', content)  # Додаємо newlines
content = re.sub(r'\n\n\n+', '\n', content)  # Видаляємо зайві порожні рядки
```

---

### Причина 3: Порожні рядки між XML елементами

**Симптоми:** Form.xml має зайві порожні рядки між `<InputField>` елементами.

**Виправлення:** Автоматично виправляється post-processing regex (версія 2.11.1+).

---

## BSL валідація

### Помилки синтаксису не виводяться

**Проблема:** BSL має помилки, але компілятор не показує їх.

**Рішення:**
1. Перевірте що використовується Configuration mode (автоматично для CatalogRef/DocumentRef)
2. Перевірте лог файл: `output/ProcessorName_check_modules.log`
3. Оновіть до версії 2.11.1+ де парсинг логів покращено

### Помилки валідації блокують компіляцію

**Симптоми:**
```
✗ BSL validation failed: 4 errors
  1. Line 25, Col 25: Ожидается символ ';'
  2. Line 28, Col 1: Неопознанный оператор
💡 Use --ignore-validation-errors to force compilation
```

**Рішення:**
1. Виправте помилки BSL у вашому коді
2. АБО використайте `--ignore-validation-errors` для примусової компіляції:

```bash
python -m 1c_processor_generator \
    --output-format epf \
    --ignore-validation-errors \
    yaml --config config.yaml
```

⚠️ **Увага:** Примусова компіляція може створити EPF з помилками які проявляться під час виконання!

---

## Configuration Mode

### Коли використовується Configuration Mode?

Configuration mode автоматично активується коли ваш процесор містить:
- `CatalogRef.*` типи
- `DocumentRef.*` типи

**Переваги:**
- ✅ Автоматична валідація BSL через `/CheckModules`
- ✅ Підтримка складних метаданих
- ✅ Автоматичне додавання `cfg:` префіксів

**Недоліки:**
- ⏱️ Повільніше (~30-60 сек замість 5-10 сек)
- 📊 Потребує Designer

### cfg: префікси - коли потрібні?

**ПОТРІБЕН cfg: prefix:**
```xml
<!-- В атрибутах процесора -->
<v8:Type>cfg:CatalogRef.Пользователи</v8:Type>
<v8:Type>cfg:DocumentRef.Договор</v8:Type>
```

**НЕ ПОТРІБЕН cfg: prefix:**
```xml
<!-- В формі (Объект attribute) -->
<v8:Type>ExternalDataProcessorObject.ProcessorName</v8:Type>
```

**Автоматично:** Generator додає `cfg:` префікси в Step 5 компіляції через `add_cfg_prefix()` метод.

---

## XML форматування

### Як працює автоматичне форматування?

Після рендерингу Jinja2 шаблону застосовується post-processing:

```python
# 1. Додаємо newline після закриваючих тегів
content = re.sub(r'(>)(\t|<)', r'\1\n\2', content)

# 2. Видаляємо зайві порожні рядки (3+ newlines → 1 newline)
content = re.sub(r'\n\n\n+', '\n', content)
```

Це вирішує проблеми:
- ✅ Склеєні XML теги на одному рядку
- ✅ Зайві порожні рядки між елементами
- ✅ Неправильний whitespace від Jinja2 `{%-` синтаксису

---

## Діагностика проблем

### Крок 1: Перевірте версію

```bash
python -m 1c_processor_generator --version
```

Переконайтесь що використовується **версія 2.11.1+** де виправлені XDTO проблеми.

### Крок 2: Перевірте згенеровані XML файли

```bash
# Основний файл процесора
cat output/ProcessorName/ProcessorName.xml | grep -i "catalogref\|documentref"

# Form.xml - перевірте ExternalDataProcessorObject
cat output/ProcessorName/ProcessorName/Forms/Форма/Ext/Form.xml | grep "ExternalDataProcessorObject"
```

### Крок 3: Перевірте логи валідації

```bash
# Лог перевірки модулів
cat output/ProcessorName_check_modules.log

# Вивід Designer
cat output/ProcessorName_designer_out.log
```

### Крок 4: Увімкніть DEBUG logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Типові помилки та швидкі виправлення

| Проблема | Швидке виправлення |
|----------|-------------------|
| XDTO Exception in Form.xml | Оновіть до версії 2.11.1+ |
| "cfg:ExternalDataProcessorObject" | Оновіть `form.xml.j2` шаблон або версію |
| Склеєні XML теги | Оновіть до версії 2.11.1+ з auto-formatting |
| BSL помилки не виводяться | Перевірте `_check_modules.log` або оновіть версію |
| Compilation timeout | Збільште `--timeout` або видаліть складні метадані |
| Designer не знайдено | Встановіть змінну `PATH_1C_DESIGNER` або вкажіть `--designer-path` |

---

## Приклади успішної компіляції

### Базовий режим (без метаданих)
```yaml
# Швидка компіляція ~5-10 сек
attributes:
  - name: Text
    type: string
```

```bash
python -m 1c_processor_generator \
    --output-format epf \
    yaml --config config.yaml
# ✅ Готово! EPF створено: output/Processor.epf
```

### Configuration mode (з CatalogRef)
```yaml
# Повільніша компіляція ~30-60 сек з валідацією
attributes:
  - name: User
    type: CatalogRef.Пользователи
```

```bash
python -m 1c_processor_generator \
    --output-format epf \
    yaml --config config.yaml
# ⚙️ Configuration mode активовано...
# ✅ BSL validation passed
# ✅ Готово! EPF створено: output/Processor.epf
```

---

## Звітування про проблеми

Якщо проблема не вирішується:

1. Перевірте [existing issues](https://github.com/anthropics/claude-code/issues)
2. Зберіть діагностичну інформацію:
   - Версія generator: `python -m 1c_processor_generator --version`
   - YAML конфігурація
   - Designer log: `*_designer_out.log`
   - Check modules log: `*_check_modules.log`
3. Створіть новий issue з повною інформацією

---

## Історія виправлень

### v2.11.1 (2025-10-18)
- ✅ Виправлено XDTO Exception через `cfg:ExternalDataProcessorObject`
- ✅ Додано автоматичне XML форматування (post-processing)
- ✅ Покращено парсинг логів /CheckModules (2 формати)
- ✅ Додано нові error keywords для класифікації
- ✅ 264 тести, coverage 59.02%

### v2.11.0 (2025-10-18)
- ✅ Major Code Refactoring
- ✅ BSL валідація через /CheckModules
- ✅ Automatic CatalogRef/DocumentRef support

### v2.10.0 (2025-10-17)
- ✅ Intelligent mode selection
- ✅ MetadataAnalyzer + ConfigurationGenerator
