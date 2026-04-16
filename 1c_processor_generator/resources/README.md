# Resources Directory

Цей каталог містить ресурси для валідації EPF файлів.

## validator.epf

**Призначення:** Перевірка синтаксису згенерованих EPF файлів.

### Генерація validator.epf

```bash
# З кореневої директорії проекту:
python scripts/build_validator_epf.py
```

Цей скрипт:
1. Парсить `validator_config.yaml`
2. Завантажує BSL код з `validator_object_module.bsl`
3. Генерує XML структуру обробки (без форми, тільки ObjectModule)
4. Компілює XML → EPF через Designer

**Вимоги:** Встановлена платформа 1С:Підприємство 8.3+

### Вручну (якщо скрипт не працює)

```bash
# Згенерувати validator.epf через CLI генератора:
python -m 1c_processor_generator yaml \
  --config 1c_processor_generator/resources/validator_config.yaml \
  --handlers-file 1c_processor_generator/resources/validator_object_module.bsl \
  --output 1c_processor_generator/resources \
  --output-format epf
```

### Використання validator.epf

**Через командний рядок 1С:**

```bash
1cv8.exe ENTERPRISE \
  /F"temp_ib" \
  /Execute"validator.epf" \
  /C"MyProcessor.epf" \
  /Out"validation.log"
```

**Через Python (EPFValidator):**

```python
from pathlib import Path
from 1c_processor_generator.epf_validator import EPFValidator

validator = EPFValidator()
result = validator.validate_epf(Path("MyProcessor.epf"))

if result.success:
    print("✓ Syntax OK")
else:
    print(f"✗ Errors: {result.error_count}")
```

## validator_config.yaml

YAML конфігурація validator обробки. Command-line tool без форми - тільки ObjectModule.

## validator_object_module.bsl

BSL код модуля обробки validator (ObjectModule). Основна логіка:
- **Точка входу:** `ПараметрыСеанса.ПараметрыКлиентаНаСервере` для отримання параметрів командного рядка
- Приймає шлях до EPF через параметр `/C`
- Завантажує EPF через `ВнешниеОбработки.Создать()`
- Ловить помилки компіляції в блоці `Попытка...Исключение`
- Виводить детальний опис помилки (через `ПодробноеПредставлениеОшибки`) або успіх

**Архітектура:** ObjectModule (не Form Module) - дозволяє використовувати `ПараметрыСеанса` для command-line параметрів.

## Що перевіряє validator

✅ **Знаходить:**
- Критичні синтаксичні помилки
- Непарні дужки, невірні ключові слова
- Помилки компіляції BSL коду

❌ **НЕ знаходить:**
- Відсутні методи з конфігурації
- Type errors
- Unused variables
- Code quality issues

**Важливо:** Designer **НЕ перевіряє** BSL синтаксис під час XML→EPF компіляції! Навіть невалідний BSL (незакриті рядки) успішно компілюється в EPF. Помилки виявляються тільки при **runtime** - коли validator.epf намагається завантажити цільовий EPF через `ВнешниеОбработки.Создать()`.

**Діагностика:**
- "Designer return code: 0 + EPF створено" = структура XML коректна
- "Designer return code: 1 + EPF не створено" = логічні/контекстні помилки BSL (не синтаксис)
- "ValidationResult.success = False" = критичні помилки BSL (runtime)

Для повної перевірки (включно з відсутніми методами, type errors) буде додано Extension + /CheckModules в майбутніх версіях (див. `docs/EPF_SYNTAX_VALIDATION_RESEARCH.md`).
