# Шпаргалка: Версії платформи 1С та формат XML

> Довідка для агента, який генерує XML-файли конфігурації 1С:Підприємство 8.3.
> Не прив'язана до конкретного генератора — описує формат як такий.

## 1. Два типи версій — НЕ плутати!

| Поняття | Приклад | Де використовується |
|---------|---------|---------------------|
| **Версія платформи** | `8.3.25.1394` | Встановлений 1cv8.exe, шлях до Designer |
| **Версія формату XML** | `2.18` | Атрибут `version` кореневого `<MetaDataObject>` |

**Критично:** це різні числа! `8.3.25` != `2.18`. Версія формату XML визначається з версії платформи за таблицею маппінгу (розділ 2).

## 2. Маппінг: Платформа → Формат XML

Офіційний маппінг з документації 1С (розділ 2.17.2 "Версии формата выгрузки"):

| Платформа | Формат XML | Примітка |
|-----------|------------|----------|
| 8.3.15 | `2.9` | Мінімальна підтримувана версія |
| 8.3.16 | `2.9.1` | Єдиний трикомпонентний формат |
| 8.3.17 | `2.10` | +7-й InternalInfo об'єкт |
| 8.3.18 | `2.11` | +URLExternalDataStorage, MobileApplicationURLs |
| 8.3.19 | `2.12` | Строга валідація GeneratedType name |
| 8.3.20 | `2.13` | +DefaultReportAppearanceTemplate, DatabaseTablespacesUseMode |
| 8.3.21 | `2.14` | |
| 8.3.22 | `2.15` | |
| 8.3.23 | `2.16` | |
| 8.3.24 | `2.17` | |
| 8.3.25 | `2.18` | Найпоширеніша у продакшені |
| 8.3.26 | `2.19` | |
| 8.3.27 | `2.20` | |
| 8.5.x (будь-яка) | `2.21` | Нова гілка платформи |

**Fallback:** якщо версію не вдалося визначити — `2.9` / `Version8_3_15`.

## 3. CompatibilityMode

Формат: `Version{Major}_{Minor}_{Patch}` — з версії платформи, не формату XML.

```
8.3.15.1234  →  Version8_3_15
8.3.25.1394  →  Version8_3_25
8.5.1.100    →  Version8_5_1
```

Використовується у двох тегах Configuration.xml:
```xml
<ConfigurationExtensionCompatibilityMode>Version8_3_25</ConfigurationExtensionCompatibilityMode>
...
<CompatibilityMode>Version8_3_25</CompatibilityMode>
```

## 4. Кореневий елемент — атрибут version

Кожен XML-файл метаданих має кореневий `<MetaDataObject>` з атрибутом `version`:

```xml
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" ... version="2.18">
```

Значення `version` — це **версія формату XML** (2.18), а не версії платформи (8.3.25).

Цей атрибут є в УСІХ XML-файлах метаданих:
- Configuration.xml
- ExternalDataProcessor.xml (обробки)
- Catalog.xml, Document.xml (довідники, документи)
- Languages/Русский.xml, Languages/English.xml
- CommonPicture, CommonModule та інші

## 5. Умовні елементи Configuration.xml за версіями

### Всі версії (8.3.15+) — базова структура

```xml
<Configuration uuid="...">
  <InternalInfo>
    <!-- 6 обов'язкових ContainedObject з фіксованими ClassId -->
    <xr:ContainedObject>
      <xr:ClassId>9cd510cd-abfc-11d4-9434-004095e12fc7</xr:ClassId>
      <xr:ObjectId>{uuid}</xr:ObjectId>
    </xr:ContainedObject>
    <!-- ... ще 5 ContainedObject ... -->
  </InternalInfo>
  <Properties>
    <!-- базові властивості -->
  </Properties>
</Configuration>
```

### 8.3.16+ — StandaloneConfigurationRestrictionRoles

```xml
<StandaloneConfigurationRestrictionRoles/>
```

Додається після `<RequiredMobileApplicationPermissions/>`.

### 8.3.17+ — 7-й ContainedObject в InternalInfo

```xml
<xr:ContainedObject>
  <xr:ClassId>fb282519-d103-4dd3-bc12-cb271d631dfc</xr:ClassId>
  <xr:ObjectId>{uuid}</xr:ObjectId>
</xr:ContainedObject>
```

Додається 7-м після існуючих 6 об'єктів у `<InternalInfo>`.

### 8.3.18+ — URLExternalDataStorage, MobileApplicationURLs

```xml
<!-- Після <DynamicListsUserSettingsStorage/> -->
<URLExternalDataStorage/>

<!-- Після <StandaloneConfigurationRestrictionRoles/> (або <RequiredMobileApplicationPermissions/>) -->
<MobileApplicationURLs/>
```

### 8.3.20+ — DefaultReportAppearanceTemplate, AllowedIncomingShareRequestTypes, DatabaseTablespacesUseMode

```xml
<!-- Після <DefaultReportSettingsForm/> -->
<DefaultReportAppearanceTemplate/>

<!-- Після <MobileApplicationURLs/> -->
<AllowedIncomingShareRequestTypes/>

<!-- Після <InterfaceCompatibilityMode>Taxi</InterfaceCompatibilityMode> -->
<DatabaseTablespacesUseMode>DontUse</DatabaseTablespacesUseMode>
```

## 6. Повний порядок Properties в Configuration.xml

Нижче — повний порядок тегів `<Properties>` з позначками версій. Теги без позначки присутні завжди (8.3.15+).

```
Name
Synonym
Comment
NamePrefix
ConfigurationExtensionCompatibilityMode  ← значення CompatibilityMode
DefaultRunMode                           ← ManagedApplication
UsePurposes
ScriptVariant                            ← Russian
DefaultRoles
Vendor
Version
UpdateCatalogAddress
IncludeHelpInContents
UseManagedFormInOrdinaryApplication
UseOrdinaryFormInManagedApplication
AdditionalFullTextSearchDictionaries
CommonSettingsStorage
ReportsUserSettingsStorage
ReportsVariantsStorage
FormDataSettingsStorage
DynamicListsUserSettingsStorage
URLExternalDataStorage                   ← [8.3.18+]
Content
DefaultReportForm
DefaultReportVariantForm
DefaultReportSettingsForm
DefaultReportAppearanceTemplate          ← [8.3.20+]
DefaultDynamicListSettingsForm
DefaultSearchForm
DefaultDataHistoryChangeHistoryForm
DefaultDataHistoryVersionDataForm
DefaultDataHistoryVersionDifferencesForm
DefaultCollaborationSystemUsersChoiceForm
RequiredMobileApplicationPermissions
StandaloneConfigurationRestrictionRoles  ← [8.3.16+]
MobileApplicationURLs                    ← [8.3.18+]
AllowedIncomingShareRequestTypes         ← [8.3.20+]
MainClientApplicationWindowMode          ← Normal
DefaultInterface
DefaultStyle
DefaultLanguage                          ← Language.Русский
BriefInformation
DetailedInformation
Copyright
VendorInformationAddress
ConfigurationInformationAddress
DataLockControlMode                      ← Managed
ObjectAutonumerationMode                 ← NotAutoFree
ModalityUseMode                          ← DontUse
SynchronousPlatformExtensionAndAddInCallUseMode  ← DontUse
InterfaceCompatibilityMode               ← Taxi
DatabaseTablespacesUseMode               ← [8.3.20+] DontUse
CompatibilityMode                        ← значення CompatibilityMode
DefaultConstantsForm
```

## 7. InternalInfo — фіксовані ClassId

6 обов'язкових ContainedObject (всі версії):

| # | ClassId | Призначення |
|---|---------|-------------|
| 1 | `9cd510cd-abfc-11d4-9434-004095e12fc7` | Configuration |
| 2 | `9fcd25a0-4822-11d4-9414-008048da11f9` | Language |
| 3 | `e3687481-0a87-462c-a166-9f34594f9bba` | SessionParameter |
| 4 | `9de14907-ec23-4a07-96f0-85521cb6b53b` | Role |
| 5 | `51f2d5d8-ea4d-4064-8892-82951750031e` | CommonPicture |
| 6 | `e68182ea-4237-4383-967f-90c1e3370bc7` | FilterCriterion |
| 7 | `fb282519-d103-4dd3-bc12-cb271d631dfc` | **[8.3.17+]** |

Кожен ContainedObject має унікальний `ObjectId` (UUID v4).

## 8. GeneratedType — формат імен за типом об'єкта

### ExternalDataProcessor (зовнішня обробка, .epf)

```xml
<InternalInfo>
  <xr:ContainedObject>
    <xr:ClassId>{class-id}</xr:ClassId>
    <xr:ObjectId>{uuid}</xr:ObjectId>
  </xr:ContainedObject>
  <xr:GeneratedType name="ExternalDataProcessorObject.ІмяОбробки" category="Object">
    <xr:TypeId>{uuid}</xr:TypeId>
    <xr:ValueId>{uuid}</xr:ValueId>
  </xr:GeneratedType>
</InternalInfo>
```

EPF має тільки **один** GeneratedType — `Object`.

### DataProcessor (внутрішня обробка, в конфігурації)

```xml
<InternalInfo>
  <xr:GeneratedType name="DataProcessorObject.ІмяОбробки" category="Object">
    <xr:TypeId>{uuid}</xr:TypeId>
    <xr:ValueId>{uuid}</xr:ValueId>
  </xr:GeneratedType>
  <xr:GeneratedType name="DataProcessorManager.ІмяОбробки" category="Manager">
    <xr:TypeId>{uuid}</xr:TypeId>
    <xr:ValueId>{uuid}</xr:ValueId>
  </xr:GeneratedType>
</InternalInfo>
```

DataProcessor має **два** GeneratedType — `Object` + `Manager`.

### TabularSection (табличні частини)

```xml
<xr:GeneratedType name="DataProcessorTabularSection.ІмяОбробки.ІмяТЧ" category="TabularSection">
  <xr:TypeId>{uuid}</xr:TypeId>
  <xr:ValueId>{uuid}</xr:ValueId>
</xr:GeneratedType>
<xr:GeneratedType name="DataProcessorTabularSectionRow.ІмяОбробки.ІмяТЧ" category="TabularSectionRow">
  <xr:TypeId>{uuid}</xr:TypeId>
  <xr:ValueId>{uuid}</xr:ValueId>
</xr:GeneratedType>
```

### Catalog (довідник) — 5 GeneratedType

```xml
<xr:GeneratedType name="CatalogObject.ІмяДовідника" category="Object">
<xr:GeneratedType name="CatalogRef.ІмяДовідника" category="Ref">
<xr:GeneratedType name="CatalogSelection.ІмяДовідника" category="Selection">
<xr:GeneratedType name="CatalogList.ІмяДовідника" category="List">
<xr:GeneratedType name="CatalogManager.ІмяДовідника" category="Manager">
```

### Document (документ) — 5 GeneratedType

```xml
<xr:GeneratedType name="DocumentObject.ІмяДокумента" category="Object">
<xr:GeneratedType name="DocumentRef.ІмяДокумента" category="Ref">
<xr:GeneratedType name="DocumentSelection.ІмяДокумента" category="Selection">
<xr:GeneratedType name="DocumentList.ІмяДокумента" category="List">
<xr:GeneratedType name="DocumentManager.ІмяДокумента" category="Manager">
```

### Зведена таблиця

| Тип об'єкта | Категорії GeneratedType | Кількість |
|-------------|-------------------------|-----------|
| ExternalDataProcessor | Object | 1 |
| DataProcessor | Object, Manager | 2 |
| Catalog | Object, Ref, Selection, List, Manager | 5 |
| Document | Object, Ref, Selection, List, Manager | 5 |
| TabularSection | TabularSection, TabularSectionRow | 2 (на кожну ТЧ) |

## 9. Критичне: GeneratedType name валідація

**Платформи 8.3.15–8.3.19** строго валідують атрибут `name` в `<xr:GeneratedType>`. Ім'я об'єкта після крапки МУСИТЬ точно відповідати `<Name>` з `<Properties>`.

Приклад помилки:
```
Неизвестное имя типа - DataProcessorObject.МояОбробка_Copy
```

Причина: `<Name>` в Properties має `МояОбробка_Copy`, а GeneratedType name містить старе ім'я.

**Платформи 8.3.20+** толерантніші до неспівпадіння, але покладатись на це не варто.

**Правило:** завжди синхронізувати ім'я в GeneratedType name з `<Name>` в Properties.

## 10. XML Namespaces

Стандартний набір namespace-ів для всіх версій:

```xml
xmlns="http://v8.1c.ru/8.3/MDClasses"
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
```

Цей набір однаковий для всіх підтримуваних версій (8.3.15–8.5.x).

## 11. Швидка таблиця рішень

```
Яку версію платформи цільовий користувач?
│
├─ Невідомо / універсально
│  → version="2.9", CompatibilityMode=Version8_3_15
│  → 6 ContainedObject, без умовних тегів
│  → Працює скрізь, але без нових фіч
│
├─ 8.3.18+ (сучасний мінімум)
│  → version="2.11", CompatibilityMode=Version8_3_18
│  → 7 ContainedObject, +URLExternalDataStorage, +MobileApplicationURLs
│
├─ 8.3.20+ (рекомендовано)
│  → version="2.13", CompatibilityMode=Version8_3_20
│  → Все з 8.3.18 + DefaultReportAppearanceTemplate,
│    AllowedIncomingShareRequestTypes, DatabaseTablespacesUseMode
│
├─ 8.3.25 (найпоширеніша)
│  → version="2.18", CompatibilityMode=Version8_3_25
│
└─ 8.5.x (нова гілка)
   → version="2.21", CompatibilityMode=Version8_5_X
```

## 12. Типові помилки

| Помилка | Причина | Рішення |
|---------|---------|---------|
| `version="8.3.25"` в XML | Плутанина версій: платформа замість формату | Використовувати `version="2.18"` |
| Зайві теги для старих версій | `<URLExternalDataStorage/>` на 8.3.15 | Не додавати умовні теги |
| Відсутній 7-й ContainedObject | Генерація для 8.3.17+ без нового об'єкта | Перевірити за таблицею |
| Неспівпадіння GeneratedType name | Перейменували процесор, забули про GeneratedType | Завжди синхронізувати |
| Manager type в EPF | Додали Manager type до ExternalDataProcessor | EPF має тільки Object |
| Відсутній Manager в DataProcessor | Конвертація EPF→Config без Manager | DataProcessor потребує Object + Manager |

## 13. Кодування файлів

- **XML файли:** UTF-8 з XML declaration `<?xml version="1.0" encoding="UTF-8"?>`
- **BSL файли (.bsl):** UTF-8 з BOM (`utf-8-sig`)
- **Усі UUID:** lowercase, формат `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (UUID v4)
