# Версії платформи 1С → Формат XML

## Маппінг версій

| Платформа | Формат XML | CompatibilityMode |
|-----------|------------|-------------------|
| 8.3.15 | `2.9` | `Version8_3_15` |
| 8.3.16 | `2.9.1` | `Version8_3_16` |
| 8.3.17 | `2.10` | `Version8_3_17` |
| 8.3.18 | `2.11` | `Version8_3_18` |
| 8.3.19 | `2.12` | `Version8_3_19` |
| 8.3.20 | `2.13` | `Version8_3_20` |
| 8.3.21 | `2.14` | `Version8_3_21` |
| 8.3.22 | `2.15` | `Version8_3_22` |
| 8.3.23 | `2.16` | `Version8_3_23` |
| 8.3.24 | `2.17` | `Version8_3_24` |
| 8.3.25 | `2.18` | `Version8_3_25` |
| 8.3.26 | `2.19` | `Version8_3_26` |
| 8.3.27 | `2.20` | `Version8_3_27` |
| 8.5.x | `2.21` | `Version8_5_X` |

## Що змінюється в Configuration.xml

### 8.3.16+
- `<StandaloneConfigurationRestrictionRoles/>`

### 8.3.17+
- 7-й `<xr:ContainedObject>` в InternalInfo (ClassId `fb282519-d103-4dd3-bc12-cb271d631dfc`)

### 8.3.18+
- `<URLExternalDataStorage/>`
- `<MobileApplicationURLs/>`

### 8.3.20+
- `<DefaultReportAppearanceTemplate/>`
- `<AllowedIncomingShareRequestTypes/>`
- `<DatabaseTablespacesUseMode>DontUse</DatabaseTablespacesUseMode>`

## Поведінкові різниці

| Версія | Відмінність |
|--------|-------------|
| 8.3.15–8.3.19 | Строга валідація `GeneratedType name` — ім'я МУСИТЬ збігатися з `<Name>` |
| 8.3.20+ | Толерантна валідація `GeneratedType name` — невідповідність не дає помилку |
