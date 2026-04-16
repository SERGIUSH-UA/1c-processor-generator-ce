# Швидкий довідник: Configuration.xml структура

**Використання:** Швидкі факти для реалізації

---

## 📍 Де знаходяться файли

| Що | Де |
|----|---|
| **Тестова БД** | `E:\Projects\1c-processor-generator\temp_test_ib` |
| **XML експорт** | `E:\Projects\1c-processor-generator\temp_test_ib\xml_export` |
| **Повна документація** | `docs/research/configuration_xml_structure/README.md` |

---

## ⚡ Ключові висновки

### 1. Мінімальна конфігурація для EPF компіляції

```
Configuration/
├── Configuration.xml          # UUID + ChildObjects (тільки імена!)
├── Languages/
│   └── Русский.xml           # Мінімум 1 мова
├── Catalogs/
│   └── НазваДовідника.xml    # UUID + 5 GeneratedType (10 UUID!)
└── DataProcessors/
    └── НазваОбробки/         # Копія існуючої генерації
```

---

### 2. Catalog.xml - що потрібно генерувати

```xml
<Catalog uuid="НОВИЙ_UUID">
  <InternalInfo>
    <!-- 5 типів: Object, Ref, Selection, List, Manager -->
    <!-- Кожен тип: 2 UUID (TypeId + ValueId) -->
    <!-- Всього: 10 UUID на кожен довідник! -->
  </InternalInfo>
  <Properties>
    <Name>НазваДовідника</Name>
    <Synonym>...</Synonym>
    <!-- ... дефолтні властивості ... -->
  </Properties>
  <ChildObjects/>  <!-- Порожній - без реквізитів -->
</Catalog>
```

**Генерація UUID:**
```python
import uuid
catalog_uuid = str(uuid.uuid4())
ref_type_id = str(uuid.uuid4())
ref_value_id = str(uuid.uuid4())
# ... + 8 інших UUID
```

---

### 3. Варіанти CatalogRef в атрибутах

| Тип в YAML | XML формат | Чи потрібна генерація метаданих? |
|------------|------------|----------------------------------|
| `CatalogRef.Організації` | `<v8:Type>cfg:CatalogRef.Організації</v8:Type>` | ✅ Так |
| `CatalogRef` | `<v8:TypeSet>cfg:CatalogRef</v8:TypeSet>` | ❌ Ні (універсальний) |
| Складений: `CatalogRef.Org` + `DocumentRef.Doc` | Декілька `<v8:Type>` тегів | ✅ Так (обидва) |

---

### 4. Алгоритм компіляції з Configuration

```bash
# 1. Згенерувати Configuration.xml
python: ConfigurationGenerator.generate_configuration()

# 2. Завантажити конфігурацію в БД
1cv8.exe DESIGNER /F"temp_ib" /LoadConfigFromFiles "temp_config" /Out"load.log"

# 3. ⚠️ КРИТИЧНО: Оновити БД (створити таблиці довідників)
1cv8.exe DESIGNER /F"temp_ib" /UpdateDBCfg /Out"update.log"

# 4. Тепер в БД є довідники → генеруємо EPF
1cv8.exe DESIGNER /F"temp_ib" /LoadExternalDataProcessorOrReportFromFiles "DataProcessor.xml" "output.epf"
```

**Без кроку 3 не працює!** Довідники існують тільки в метаданих, але НЕ в БД.

---

## 🎯 Що треба реалізувати

### Етап 1: MetadataAnalyzer
```python
class MetadataAnalyzer:
    @staticmethod
    def analyze_processor(processor: Processor) -> MetadataRequirements:
        """Витягує CatalogRef/DocumentRef з атрибутів."""
        # Парсити processor.attributes + processor.tabular_sections
        # Regex: r'CatalogRef\.(\w+)'
        pass
```

### Етап 2: ConfigurationGenerator
```python
class ConfigurationGenerator:
    def generate_configuration(processor, metadata, output_dir) -> Path:
        """Генерує Configuration.xml + Catalogs/*.xml + DataProcessor/"""
        # 1. Configuration.xml (Jinja2)
        # 2. Languages/Русский.xml
        # 3. Catalogs/НазваДовідника.xml (з 10 UUID!)
        # 4. Копіювати DataProcessor з ProcessorGenerator
        pass
```

### Етап 3: Інтеграція в EPFCompiler
```python
def compile_epf(xml_root, output_epf, processor=None):
    if processor and has_catalogrefs(processor):
        # Варіант A: Через Configuration
        return compile_with_configuration(processor)
    else:
        # Варіант Б: Існуючий алгоритм (прості типи)
        return compile_simple(xml_root)
```

---

## 🧪 Тестові сценарії

1. **Проста обробка** (string, number) → XML → EPF ✅
2. **Обробка з CatalogRef** → Configuration → EPF ⏳ (треба реалізувати)
3. **Обробка з DocumentRef** → Configuration → EPF ⏳
4. **Обробка з універсальним CatalogRef** → XML → EPF ❓ (перевірити чи працює)
5. **ТестированиеStripeTax** → Configuration → EPF ⏳ (інтеграційний тест)

---

## 📝 Приклади з тестової конфігурації

### Configuration.xml
- Розташування: `temp_test_ib/xml_export/Configuration.xml`
- Розмір: 260 рядків
- Version: 2.18

### Catalog.xml
- Розташування: `temp_test_ib/xml_export/Catalogs/ТестовыйСправочник.xml`
- Розмір: 91 рядок
- Ключове: 5 GeneratedType з UUID

### DataProcessor.xml
- Розташування: `temp_test_ib/xml_export/DataProcessors/ТестоваяОбработка.xml`
- Розмір: 199 рядків
- Приклади CatalogRef: рядки 42, 76, 110, 169

---

## ⚠️ Важливі моменти

1. **UUID генерація:** 10 UUID на кожен Catalog/Document (5 типів × 2 UUID)
2. **ChildObjects в Configuration:** Тільки **імена** метаданих, не структура!
3. **UpdateDBCfg обов'язковий:** Без цього довідники не створюються в БД
4. **Універсальний CatalogRef:** `<v8:TypeSet>cfg:CatalogRef</v8:TypeSet>` НЕ потребує генерації метаданих
5. **Persistent IB:** Можна переіспользувати одну БД для всіх компіляцій

---

**Останнє оновлення:** 2025-10-17
