# Розташування прикладів XML для реалізації

**Використання:** Копіювати структуру з цих файлів при генерації

---

## 📁 Тестова БД

**Розташування:** `E:\Projects\1c-processor-generator\temp_test_ib`

```
temp_test_ib/
├── 1Cv8.1CD                  # Бінарна база
└── xml_export/               # ⭐ Експортована конфігурація
    ├── Configuration.xml     # Кореневий файл
    ├── ConfigDumpInfo.xml
    ├── Languages/
    ├── Catalogs/
    ├── Documents/
    ├── DataProcessors/
    └── ... інші метадані
```

---

## 🎯 Файли для копіювання структури

### 1. Configuration.xml - кореневий файл конфігурації

**Шлях:**
```
E:\Projects\1c-processor-generator\temp_test_ib\xml_export\Configuration.xml
```

**Що копіювати:**
```xml
<!-- Рядки 1-2: XML header + namespaces -->
<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" ... version="2.18">

<!-- Рядки 3-245: Properties з дефолтними значеннями -->
<Configuration uuid="303fb160-8945-407a-b0d7-36087b67e74b">
  <Properties>
    <Name>Конфігурация</Name>
    <CompatibilityMode>Version8_3_25</CompatibilityMode>
    <DefaultRunMode>ManagedApplication</DefaultRunMode>
    <ScriptVariant>Russian</ScriptVariant>
    <DefaultLanguage>Language.Русский</DefaultLanguage>
    <!-- ... багато інших Properties ... -->
  </Properties>

  <!-- Рядки 246-258: ChildObjects - НАЙВАЖЛИВІШЕ! -->
  <ChildObjects>
    <Language>Русский</Language>
    <Subsystem>ТестоваяПодсистема</Subsystem>
    <CommonModule>ТестовыйОбщийМодульСервер</CommonModule>
    <CommonModule>ТестовыйОбщийМодульКлиент</CommonModule>
    <Catalog>ТестовыйСправочник</Catalog>           <!-- ⭐ -->
    <Catalog>ТестовыйИерархическийСправочник</Catalog>
    <Document>ТестовыйДокумент</Document>           <!-- ⭐ -->
    <DataProcessor>ТестоваяОбработка</DataProcessor> <!-- ⭐ -->
    <InformationRegister>ТестовыйРегистрСведений</InformationRegister>
  </ChildObjects>
</Configuration>
```

**Для Jinja2 темплейту:**
- Взяти Properties (рядки 34-244) як дефолтні значення
- ChildObjects генерувати динамічно на основі MetadataRequirements
- Version та namespaces - константи

---

### 2. Catalog (мінімальний довідник)

**Шлях:**
```
E:\Projects\1c-processor-generator\temp_test_ib\xml_export\Catalogs\ТестовыйСправочник.xml
```

**Структура (91 рядок):**

```xml
<!-- Рядок 1-2: XML header -->
<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" ... version="2.18">

<!-- Рядок 3: Catalog з UUID -->
<Catalog uuid="1e4587eb-42a7-42fe-a577-882060bf982a">

  <!-- Рядки 4-25: InternalInfo - 5 GeneratedType ⭐ КРИТИЧНО -->
  <InternalInfo>
    <!-- Object type (рядки 5-8) -->
    <xr:GeneratedType name="CatalogObject.ТестовыйСправочник" category="Object">
      <xr:TypeId>7321f091-8df8-46d5-954b-30259e62dcdd</xr:TypeId>
      <xr:ValueId>b8fbccce-d96d-41cf-a4a7-76bff2e205ce</xr:ValueId>
    </xr:GeneratedType>

    <!-- Ref type (рядки 9-12) ⭐ НАЙВАЖЛИВІШИЙ! -->
    <xr:GeneratedType name="CatalogRef.ТестовыйСправочник" category="Ref">
      <xr:TypeId>14f9eec7-f20d-4f74-ab0d-b22627bf5836</xr:TypeId>
      <xr:ValueId>d56db808-2351-4e3a-9eb6-ed5b83d6aeb5</xr:ValueId>
    </xr:GeneratedType>

    <!-- Selection, List, Manager types (рядки 13-25) -->
    <!-- ... аналогічно ... -->
  </InternalInfo>

  <!-- Рядки 26-88: Properties -->
  <Properties>
    <Name>ТестовыйСправочник</Name>
    <Synonym>
      <v8:item>
        <v8:lang>ru</v8:lang>
        <v8:content>Тестовый справочник</v8:content>
      </v8:item>
    </Synonym>
    <Comment/>
    <Hierarchical>false</Hierarchical>
    <HierarchyType>HierarchyFoldersAndItems</HierarchyType>
    <!-- ... багато дефолтних властивостей ... -->
    <CodeLength>9</CodeLength>
    <DescriptionLength>25</DescriptionLength>
    <CodeType>String</CodeType>
    <!-- ... -->
  </Properties>

  <!-- Рядок 89: ChildObjects - порожній! -->
  <ChildObjects/>
</Catalog>
```

**Для Jinja2 темплейту:**
- InternalInfo: генерувати 5 GeneratedType з UUID
- Properties: взяти дефолтні значення (рядки 26-88)
- Name та Synonym - параметри темплейту
- ChildObjects порожній (мінімальний довідник без реквізитів)

---

### 3. Document (мінімальний документ)

**Шлях:**
```
E:\Projects\1c-processor-generator\temp_test_ib\xml_export\Documents\ТестовыйДокумент.xml
```

**Структура (82 рядки):**

```xml
<Document uuid="ae393648-00cd-4d6e-b72d-36ff06ec1372">
  <InternalInfo>
    <!-- 4 GeneratedType: Object, Ref, List, Manager -->
    <!-- ❌ НЕМАЄ Selection type (на відміну від Catalog) -->
    <xr:GeneratedType name="DocumentRef.ТестовыйДокумент" category="Ref">
      <xr:TypeId>89c51d4f-baf8-47a0-8b54-0622cd76e8c1</xr:TypeId>
      <xr:ValueId>c886e608-2259-4227-bf80-b49148c5e696</xr:ValueId>
    </xr:GeneratedType>
    <!-- ... + 3 інших типи -->
  </InternalInfo>

  <Properties>
    <Name>ТестовыйДокумент</Name>
    <Synonym>...</Synonym>
    <!-- Інші Properties для документів -->
    <NumberType>String</NumberType>
    <NumberLength>9</NumberLength>
    <Posting>Allow</Posting>
    <RealTimePosting>Allow</RealTimePosting>
    <!-- ... -->
  </Properties>

  <ChildObjects/>
</Document>
```

**Для Jinja2 темплейту:**
- Аналогічно до Catalog, але тільки 4 GeneratedType
- Properties специфічні для документів (Number, Posting)

---

### 4. Language (мінімум 1 мова)

**Шлях:**
```
E:\Projects\1c-processor-generator\temp_test_ib\xml_export\Languages\Русский.xml
```

**Структура (19 рядків):**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" ... version="2.18">
<Language uuid="e86eb25a-6087-40e2-b52d-4e12be7cd7df">
  <Properties>
    <Name>Русский</Name>
    <Synonym>
      <v8:item>
        <v8:lang>ru</v8:lang>
        <v8:content>Russian</v8:content>
      </v8:item>
    </Synonym>
    <Comment/>
    <LanguageCode>ru</LanguageCode>
  </Properties>
</Language>
</MetaDataObject>
```

**Для Jinja2 темплейту:**
- Завжди генерувати Русский.xml (для DefaultLanguage)
- UUID + Name + LanguageCode="ru"

---

### 5. DataProcessor з CatalogRef (приклад використання)

**Шлях:**
```
E:\Projects\1c-processor-generator\temp_test_ib\xml_export\DataProcessors\ТестоваяОбработка.xml
```

**Приклади CatalogRef в атрибутах:**

#### Рядки 31-64: Конкретний довідник
```xml
<Attribute uuid="3943ae3e-bd1e-4575-932e-e6409827b017">
  <Properties>
    <Name>ТестовыйСправочник</Name>
    <Type>
      <v8:Type>cfg:CatalogRef.ТестовыйСправочник</v8:Type>
    </Type>
    <!-- ... інші Properties ... -->
  </Properties>
</Attribute>
```

#### Рядки 65-98: Універсальний CatalogRef
```xml
<Attribute uuid="20eb2a66-4132-499e-933a-374bfd867794">
  <Properties>
    <Name>УниверсальныйЛюбойСправочник</Name>
    <Type>
      <v8:TypeSet>cfg:CatalogRef</v8:TypeSet>  <!-- БЕЗ назви довідника -->
    </Type>
  </Properties>
</Attribute>
```

#### Рядки 99-133: Складений тип (Catalog + Document)
```xml
<Attribute uuid="7f8001cd-f70e-4d2e-b1f4-a82bd91c9d51">
  <Properties>
    <Name>СоставнойРеквизитДокументИСправочник</Name>
    <Type>
      <v8:Type>cfg:CatalogRef.ТестовыйСправочник</v8:Type>
      <v8:Type>cfg:DocumentRef.ТестовыйДокумент</v8:Type>
    </Type>
  </Properties>
</Attribute>
```

#### Рядки 158-193: DocumentRef в TabularSection
```xml
<TabularSection uuid="a86034d8-9a74-49fd-ab02-c7a3a8611630">
  <ChildObjects>
    <Attribute uuid="7ba4abf7-8de2-4988-942e-3d178f0d3539">
      <Properties>
        <Name>ТестовыйДокумент</Name>
        <Type>
          <v8:Type>cfg:DocumentRef.ТестовыйДокумент</v8:Type>
        </Type>
      </Properties>
    </Attribute>
  </ChildObjects>
</TabularSection>
```

---

## 🎯 Алгоритм використання прикладів

### 1. Створення Jinja2 темплейтів

```python
# Крок 1: Скопіювати Configuration.xml (рядки 1-260)
template_path = "templates/configuration.xml.j2"
# Замінити:
# - UUID → {{ configuration_uuid }}
# - ChildObjects → {% for catalog in catalogs %}...

# Крок 2: Скопіювати Catalog.xml (рядки 1-91)
template_path = "templates/catalog_minimal.xml.j2"
# Замінити:
# - UUID → {{ catalog_uuid }}
# - Name → {{ catalog_name }}
# - InternalInfo GeneratedType → {% for type in generated_types %}...

# Крок 3: Аналогічно для Document, Language
```

### 2. Генерація Configuration.xml

```python
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('templates'))

# Підготувати дані
config_data = {
    'configuration_uuid': str(uuid.uuid4()),
    'catalogs': ['Організації', 'Контрагенты'],
    'documents': ['ЗамовленняКлієнта'],
    'data_processors': ['ТестированиеStripeTax']
}

# Згенерувати Configuration.xml
template = env.get_template('configuration.xml.j2')
xml_content = template.render(config_data)
```

### 3. Генерація Catalog.xml

```python
# Згенерувати 5 GeneratedType з UUID
generated_types = [
    {'category': 'Object', 'type_id': str(uuid.uuid4()), 'value_id': str(uuid.uuid4())},
    {'category': 'Ref', 'type_id': str(uuid.uuid4()), 'value_id': str(uuid.uuid4())},
    {'category': 'Selection', 'type_id': str(uuid.uuid4()), 'value_id': str(uuid.uuid4())},
    {'category': 'List', 'type_id': str(uuid.uuid4()), 'value_id': str(uuid.uuid4())},
    {'category': 'Manager', 'type_id': str(uuid.uuid4()), 'value_id': str(uuid.uuid4())},
]

catalog_data = {
    'catalog_uuid': str(uuid.uuid4()),
    'catalog_name': 'Організації',
    'generated_types': generated_types
}

template = env.get_template('catalog_minimal.xml.j2')
xml_content = template.render(catalog_data)
```

---

## 📊 Таблиця UUID генерації

| Метадані | Скільки UUID потрібно | Де використовується |
|----------|------------------------|---------------------|
| **Configuration** | 1 | Configuration uuid |
| **Language** | 1 | Language uuid |
| **Catalog** | 11 | 1 catalog uuid + 5 types × 2 UUID |
| **Document** | 9 | 1 document uuid + 4 types × 2 UUID |

**Для обробки ТестированиеStripeTax з 3 довідниками:**
- Configuration: 1 UUID
- Language (Русский): 1 UUID
- Catalogs (Організації, Контрагенты, Номенклатура): 3 × 11 = 33 UUID
- **Всього: 35 UUID**

---

## ⚠️ Важливі нюанси при копіюванні

### 1. UTF-8 BOM
```python
# Всі XML файли мають UTF-8 BOM на початку (﻿)
with open(file_path, 'w', encoding='utf-8-sig') as f:
    f.write(xml_content)
```

### 2. XML namespaces
```xml
<!-- Копіювати повністю з рядка 2 Configuration.xml -->
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses"
                xmlns:app="http://v8.1c.ru/8.2/managed-application/core"
                xmlns:cfg="http://v8.1c.ru/8.1/data/enterprise/current-config"
                xmlns:cmi="http://v8.1c.ru/8.2/managed-application/cmi"
                xmlns:ent="http://v8.1c.ru/8.1/data/enterprise"
                xmlns:lf="http://v8.1c.ru/8.2/managed-application/logform"
                xmlns:style="http://v8.1c.ru/8.1/data/ui/style"
                xmlns:sys="http://v8.1c.ru/8.1/data/ui/fonts/system"
                xmlns:v8="http://v8.1c.ru/8.1/data/core"
                xmlns:v8ui="http://v8.1c.ru/8.1/data/ui"
                xmlns:web="http://v8.1c.ru/8.1/data/ui/colors/web"
                xmlns:win="http://v8.1c.ru/8.1/data/ui/colors/windows"
                xmlns:xen="http://v8.1c.ru/8.3/xcf/enums"
                xmlns:xpr="http://v8.1c.ru/8.3/xcf/predef"
                xmlns:xr="http://v8.1c.ru/8.3/xcf/readable"
                xmlns:xs="http://www.w3.org/2001/XMLSchema"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                version="2.18">
```

### 3. Version attribute
```xml
<!-- version="2.18" взяти з генератора, не хардкодити -->
version="{{ platform_version }}"
```

---

**Документ створено:** 2025-10-17
**Використання:** Копіювати структуру при створенні Jinja2 темплейтів
