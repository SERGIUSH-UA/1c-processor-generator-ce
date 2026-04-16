<div align="center">

# 1C Processor Generator

### Generate 1C:Enterprise 8.3 processors with AI — from idea to .epf in 30 seconds

[![Tests](https://github.com/SERGIUSH-UA/1c-processor-generator-ce/workflows/Tests/badge.svg)](https://github.com/SERGIUSH-UA/1c-processor-generator-ce/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10--3.14-3776ab.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

[**Documentation**](docs/LLM_CORE.md) · [**Examples**](examples/yaml/) · [**Quick Reference**](docs/QUICK_REFERENCE.md)

</div>

---

## The Problem

LLMs (Claude, GPT, Gemini) **cannot** generate valid 1C XML directly. The format requires correct UUIDs, sequential IDs, nested structures, and dozens of XML namespaces. Even small mistakes = broken file.

## The Solution

You write simple **YAML + BSL**. The generator handles all the complexity.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ YAML config │ ──► │  Generator  │ ──► │  .epf file  │
│ + BSL code  │     │   (magic)   │     │   (ready!)  │
└─────────────┘     └─────────────┘     └─────────────┘
```

**What you get:**
- **20 lines of YAML** instead of 500+ lines of XML
- **Automatic UUIDs, IDs, namespaces** — zero manual work
- **AI-friendly** — LLMs generate YAML with near-zero errors
- **Full EPF compilation** — ready to use in 1C (requires local Designer)

---

## Quick Start

```bash
# Install
pip install git+https://github.com/SERGIUSH-UA/1c-processor-generator-ce.git

# Generate a minimal processor
python -m 1c_processor_generator minimal MyProcessor

# Generate from YAML config
python -m 1c_processor_generator yaml \
  --config config.yaml \
  --handlers-file handlers.bsl \
  --output output/ \
  --output-format epf
```

---

## Example

**config.yaml** (20 lines):
```yaml
processor:
  name: InvoiceGen
  synonym:
    uk: Invoice Generator

attributes:
  - name: Client
    type: string
  - name: Amount
    type: number

forms:
  - name: Form
    default: true
    elements:
      - type: InputField
        name: ClientField
        attribute: Client
      - type: InputField
        name: AmountField
        attribute: Amount
      - type: Button
        name: GenerateBtn
        command: Generate
    commands:
      - name: Generate
        handler: Generate
```

**handlers.bsl** (5 lines):
```bsl
#Region Generate
&AtClient
Procedure Generate(Command)
    ShowMessageBox(, "Invoice created for " + Object.Client);
EndProcedure
#EndRegion
```

**Result:** A fully functional .epf processor with a form, input fields, and a button.

---

## Features

| Category | Support |
|----------|---------|
| **Form Elements** | InputField, Button, Table, CheckBox, RadioButton, Pages, Groups, Labels, PictureField, HTMLDocumentField, SpreadsheetDocumentField, PlannerField |
| **Data** | Attributes, TabularSection, ValueTable, ValueTree, DynamicList |
| **Types** | string, number, date, boolean, CatalogRef, DocumentRef, and more |
| **BSL** | Automatic client-server pairs, form events, element events, long operations |
| **Validation** | YAML schema, BSL syntax, BSL reserved keywords, StdPicture names |
| **Output** | XML (import to Configurator) or EPF (ready-to-use processor) |
| **Templates** | SpreadsheetDocument, HTMLDocument, Excel auto-conversion |
| **Sync** | Bidirectional YAML ↔ XML synchronization |
| **BSP** | External Print Forms integration |

### Everything is Free

This is the **Community Edition** — all features are free and open-source:

| Feature | Status |
|---------|--------|
| XML generation | **Free** |
| EPF compilation (local Designer) | **Free** |
| BSL / CheckConfig validation | **Free** |
| Sync Tool | **Free** |
| All form elements & data types | **Free** |
| No watermark | **Free** |
| Cloud compilation (`--cloud`) | PRO license |

> Cloud compilation lets you generate .epf without local 1C Designer.
> Get a PRO license at [itdeo.tech](https://itdeo.tech/1c-processor-generator)

---

## For LLMs / AI Agents

**If you're an LLM, start here:** [docs/LLM_CORE.md](docs/LLM_CORE.md)

Documentation is optimized for Claude/GPT with a three-tier architecture:

| Tier | Document | Purpose |
|------|----------|---------|
| **Principles** | [LLM_CORE.md](docs/LLM_CORE.md) | Critical rules, thinking framework, navigation |
| **Patterns** | [LLM_PATTERNS_ESSENTIAL.md](docs/LLM_PATTERNS_ESSENTIAL.md) | 3 canonical patterns (80% of use cases) |
| | [LLM_DATA_GUIDE.md](docs/LLM_DATA_GUIDE.md) | Data model decisions |
| | [LLM_PRACTICES.md](docs/LLM_PRACTICES.md) | Best practices, validation, error handling |
| **Reference** | [reference/ALL_PATTERNS.md](docs/reference/ALL_PATTERNS.md) | Full pattern library (10+ patterns) |
| | [reference/API_REFERENCE.md](docs/reference/API_REFERENCE.md) | Complete YAML API specification |

**Token efficiency:** 6K tokens initial load (down from 20K), 90-95% LLM utilization.

### AI Assistants

| Platform | How to use |
|----------|-----------|
| **Claude Code** | Works out of the box — reads CLAUDE.md and docs automatically |
| **ChatGPT** | Use our [Custom GPT](https://chatgpt.com/g/g-69441faa0c8081919bcf14fb6b038bc3-1c-processor-generator) |
| **Claude.ai** | Connect this repo or upload [LLM_WEB_LITE.md](docs/LLM_WEB_LITE.md) |
| **Gemini** | Upload [LLM_WEB_LITE.md](docs/LLM_WEB_LITE.md) to the chat |

Templates for building your own AI assistants: [templates/](templates/)

---

## Feature Discovery

```bash
# List all supported elements, events, types
python -m 1c_processor_generator features

# Search by keyword
python -m 1c_processor_generator features --search "table"

# JSON output for programmatic use
python -m 1c_processor_generator features --json
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [LLM_CORE.md](docs/LLM_CORE.md) | Main guide for AI agents |
| [QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) | One-page cheatsheet |
| [reference/API_REFERENCE.md](docs/reference/API_REFERENCE.md) | Full YAML API |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [WEB_CHAT_GUIDE.md](docs/WEB_CHAT_GUIDE.md) | Using with web AI chats |

**Examples:** [examples/yaml/](examples/yaml/) — 15+ ready-to-use examples

---

## Requirements

- Python 3.10+
- 1C:Enterprise 8.3 (for EPF compilation only)

```bash
pip install git+https://github.com/SERGIUSH-UA/1c-processor-generator-ce.git
```

---

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

---

## License

**GPL v3** — free to use, modify, and distribute. See [LICENSE](LICENSE) for details.

Cloud compilation requires a [PRO license](https://itdeo.tech/1c-processor-generator).

---

<div align="center">

**[Documentation](docs/LLM_CORE.md)** · **[Examples](examples/yaml/)** · **[Issues](https://github.com/SERGIUSH-UA/1c-processor-generator-ce/issues)** · **[Cloud PRO](https://itdeo.tech/1c-processor-generator)**

Made with love by [SERGIUSH](https://github.com/SERGIUSH-UA)

</div>
