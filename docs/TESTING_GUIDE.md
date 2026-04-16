# 1C Processor Testing Guide (v2.23.2+)

Comprehensive guide for automated testing of 1C external processors through COM with auto-detection architecture.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Test Configuration](#test-configuration)
- [Declarative Tests](#declarative-tests)
- [Procedural Tests](#procedural-tests)
- [BSL Testing Infrastructure](#bsl-testing-infrastructure)
- [pytest Integration](#pytest-integration)
- [Running Tests](#running-tests)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [Examples](#examples)

---

## Overview

The 1C Processor Generator (v2.23.2+) includes built-in support for automated testing of generated EPF files through COM (Component Object Model) with automatic test type detection.

### Key Features (v2.23.2)

✅ **Auto-Detection Architecture**: System automatically selects connection type based on test location
✅ **ObjectModule Tests**: Fast testing via External Connection (no UI)
❌ **Form Tests**: NOT AVAILABLE - COM limitations prevent Automation Server usage (see below)
✅ **Hybrid Approach**: Combine declarative YAML tests with procedural BSL tests
✅ **Zero Configuration**: No flags needed - system detects what to run and how

### Supported Test Types

| Test Type | Format | Use Case | Speed |
|-----------|--------|----------|-------|
| **Declarative** | YAML | Simple scenarios (attributes, commands, messages) | Fast |
| **Procedural** | BSL | Complex logic, multiple steps, conditionals | Medium |

### Limitations

⚠️ **Windows Only**: COM testing requires Windows + pywin32
❌ **No Form Testing**: Forms cannot be tested via COM (V83.Application incompatible, see docs/research/V83_INVESTIGATION_REPORT.md)
✅ **ObjectModule Testing Works**: Business logic, commands, data manipulation fully supported
⚠️ **1C Platform Required**: Tests execute in real 1C runtime environment

---

## Quick Start

### 1. Prerequisites

```bash
# Install pywin32 (Windows only)
pip install pywin32>=305

# Verify 1C Designer is available
where 1cv8.exe
```

### 2. Create Test Configuration

Create `tests/processor_tests.yaml`:

```yaml
# ObjectModule tests (via External Connection - fast, no UI)
objectmodule_tests:
  declarative:
    - name: test_calculation
      description: "Test basic calculation"
      setup:
        attributes: {Number1: 10, Number2: 20}
      execute_command: Calculate
      assert:
        attributes: {Result: 30}
        messages: [{contains: "Done"}]

  procedural:
    file: tests/objectmodule_tests.bsl
    procedures:
      - Тест_ComplexScenario

# Per-form tests (via Automation Server - slow, with UI)
forms:
  - name: Форма
    declarative:
      - name: test_form_button
        execute_command: ShowReport
        assert:
          messages: [{contains: "Report generated"}]

# Global settings
timeout: 300
```

### 3. Reference in config.yaml

```yaml
processor:
  name: MyProcessor
  tests_file: tests/processor_tests.yaml  # Add this line
```

### 4. Generate and Test

```bash
# Generate EPF + tests
python -m 1c_processor_generator yaml \
  --config config.yaml \
  --handlers-file handlers.bsl \
  --output-format epf

# Run tests (auto-detection - no flags needed!)
python -m 1c_processor_generator.test_runner \
  --tests-config tmp/MyProcessor/tests/processor_tests.yaml \
  --epf-path tmp/MyProcessor.epf \
  --ib-path "C:\Users\...\persistent_ib" \
  --processor-name MyProcessor
```

### 5. View Results

```
======================== test session starts ========================
tmp/MyProcessor/tests/test_MyProcessor.py::TestDeclarative::test_calculation PASSED [50%]
tmp/MyProcessor/tests/test_MyProcessor.py::TestProcedural::test_complexscenario PASSED [100%]

======================== 2 passed in 3.52s ==========================
```

---

## Architecture

### Auto-Detection System (v2.23.2)

The testing system **automatically selects** the appropriate connection type based on test location:

```
┌─────────────────────────────────────────────────────────────┐
│                    TestsConfig                               │
│  ┌───────────────────────┐   ┌──────────────────────────┐   │
│  │  objectmodule_tests   │   │      forms[]              │   │
│  │                       │   │                           │   │
│  │  declarative: [...]   │   │  - name: Форма           │   │
│  │  procedural: {...}    │   │    declarative: [...]    │   │
│  └───────────┬───────────┘   │    procedural: {...}     │   │
│              │               └──────────┬───────────────┘   │
│              │                          │                   │
│              ▼                          ▼                   │
│   ┌──────────────────────┐   ┌──────────────────────────┐  │
│   │ External Connection  │   │  Automation Server       │  │
│   │ (Fast, No UI)        │   │  (Slow, With UI)         │  │
│   └──────────────────────┘   └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Key principle:** System detects test type and automatically uses the right connection.

### External Connection (ObjectModule Tests)

**Automatically used for:**
- `objectmodule_tests` section
- Business logic tests
- Attribute manipulation tests

**Characteristics:**
- ⚡ Fast execution (~10x faster than Automation)
- 💾 Low memory usage
- 🔄 No UI overhead
- ✅ Direct ObjectModule access

**Connection:**
```python
connection = ExternalConnection(
    epf_path=epf_path,
    ib_path=ib_path,
    load_from_configuration=True,
    processor_name="ProcessorName"
)
```

**Limitations:**
- ❌ No form access
- ❌ No UI testing
- ✅ Perfect for business logic

### ❌ Automation Server (Form Tests) - NOT AVAILABLE

**⚠️ IMPORTANT: Form testing is NOT POSSIBLE in current version (v2.23.2+)**

After extensive COM investigation (2025-11-18), we determined that form testing via Automation Server cannot be implemented due to fundamental COM limitations.

**Why it doesn't work:**
- ❌ V83.Application inaccessible from Python (RPC_E_DISCONNECTED)
- ❌ PowerShell Connect() succeeds but object is hollow
- ❌ V83.COMConnector.ПолучитьФорму() fails with "Интерактивные операции недоступны"
- ❌ External Connection is headless by design

**Root cause:**
- LocalServer32 COM architecture limitation
- Process lifecycle management issues
- Possibly intentional 1C platform restriction

**What this means:**
- ❌ `forms[]` section in tests.yaml will NOT execute
- ❌ UI interaction tests not possible
- ❌ Form event tests not possible
- ✅ **ObjectModule tests work perfectly** (use these instead)

**Alternatives:**
- ✅ Use `objectmodule_tests` (fast, reliable, headless)
- Manual form testing through 1C Configurator
- Future: Web client + Selenium automation

**Full technical report:** `docs/research/V83_INVESTIGATION_REPORT.md`

### Testing Flow

```
┌─────────────────────────────────────────────────┐
│ 1. Generator parses tests.yaml                  │
│    → Creates TestsConfig object                 │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 2. Generator compiles EPF                       │
│    → Adds BSL testing infrastructure            │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 3. TestGenerator creates pytest files           │
│    → test_ProcessorName.py                      │
│    → conftest.py (fixtures)                     │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 4. pytest runs tests                            │
│    → EPFTester connects via COM                 │
│    → Loads EPF in 1C runtime                    │
│    → Executes test procedures                   │
│    → Collects results                           │
└─────────────────────────────────────────────────┘
```

---

## Test Configuration

### tests.yaml Schema (v2.23.2)

Full schema available in `1c_processor_generator/test_schema.json`.

#### Top-Level Structure

```yaml
# v2.23.2 structure with auto-detection
objectmodule_tests: {}     # ObjectModule tests (External Connection)
forms: []                  # Per-form tests (Automation Server)
fixtures: {}               # Reusable test data (optional)
persistent_ib_path: null   # Custom IB path (optional)
timeout: 300               # Global timeout (seconds)
```

#### ObjectModule Tests Section

```yaml
objectmodule_tests:
  declarative:             # Declarative tests (YAML format)
    - name: test_name
      # ...

  procedural:              # Procedural tests (BSL format)
    file: objectmodule_tests.bsl
    procedures:
      - Тест_Something
```

**Execution:** External Connection (fast, no UI)

#### Forms Section

```yaml
forms:
  - name: Форма           # Form name
    declarative:          # Declarative tests for this form
      - name: test_form_button
        # ...

    procedural:           # Procedural tests for this form
      file: form_tests.bsl
      procedures:
        - Тест_FormLogic
```

**Execution:** Automation Server (slow, with UI)

**Note:** Each form can have its own test suite with separate procedural test files.

---

## Declarative Tests

Declarative tests describe test scenarios in YAML format. Best for simple, straightforward scenarios.

### Test Structure

```yaml
- name: test_name              # Required: Python-style name (test_*)
  description: "Description"   # Optional: Test description
  setup: {}                    # Optional: Test setup
  execute_command: CommandName # Optional: Command to execute
  execute_procedure: ProcName  # Optional: Procedure to call
  assert: {}                   # Optional: Assertions
```

### Setup Section

Prepare test data before execution:

```yaml
setup:
  # Set attribute values
  attributes:
    AttributeName: value
    Number1: 10
    Status: "Active"

  # Fill table rows
  table_rows:
    TableName:
      - {Column1: "Value1", Column2: 100}
      - {Column1: "Value2", Column2: 200}
```

**Example:**

```yaml
- name: test_table_processing
  setup:
    attributes:
      FilterDate: "2024-01-01"
    table_rows:
      Lines:
        - {Product: "Apple", Quantity: 5, Price: 10.50}
        - {Product: "Orange", Quantity: 3, Price: 8.00}
  execute_command: ProcessTable
```

### Execution Section

Execute a command or procedure:

```yaml
# Option 1: Execute form command
execute_command: Calculate

# Option 2: Execute BSL procedure
execute_procedure: CustomProcedure
```

**Note:** Use `execute_command` for user-facing commands, `execute_procedure` for internal logic.

### Assertion Section

Verify test results:

#### Attribute Assertions

```yaml
assert:
  attributes:
    Result: 30
    Status: "Complete"
    IsValid: true
```

**Data Types:**
- Numbers: `42`, `3.14`
- Strings: `"text"`
- Booleans: `true`, `false`
- Null: `null`

#### Message Assertions

```yaml
assert:
  messages:
    # Contains check
    - contains: "Operation complete"

    # Exact match
    - equals: "Success"

    # Message count
    - count: 3
```

**Multiple conditions:**

```yaml
assert:
  messages:
    - contains: "Success"    # Message must contain "Success"
    - count: 1               # Exactly 1 message
```

#### Table Assertions

```yaml
assert:
  tables:
    - table_name: Results
      row_count: 10          # Expected row count
      columns:               # Expected columns exist
        - Product
        - Quantity
        - Price
      row_data:              # Specific cell values
        0: {Product: "Apple", Quantity: 5}
        1: {Product: "Orange", Quantity: 3}
```

**Row indexing:** 0-based (first row = 0)

#### Exception Assertions

```yaml
assert:
  exception:
    raised: true                    # Exception must be raised
    contains: "Amount must be positive"  # Error message check
```

**Use cases:**
- Validation error testing
- Required field checks
- Business rule violations

### Complete Examples

#### Simple Calculation Test

```yaml
- name: test_addition
  description: "Test addition of two numbers"
  setup:
    attributes: {Number1: 10, Number2: 20}
  execute_command: Add
  assert:
    attributes: {Result: 30}
    messages: [{contains: "Addition complete"}]
```

#### Validation Error Test

```yaml
- name: test_negative_amount_error
  description: "Negative amount should raise error"
  setup:
    attributes: {Amount: -100}
  execute_command: Validate
  assert:
    exception:
      raised: true
      contains: "Amount must be positive"
```

#### Table Processing Test

```yaml
- name: test_table_fill
  description: "Table should be filled with 10 rows"
  execute_command: LoadData
  assert:
    tables:
      - table_name: Results
        row_count: 10
        columns: [Product, Quantity, Price]
```

---

## Procedural Tests

Procedural tests are written in BSL for complex scenarios that require:
- Multiple sequential operations
- Conditional logic
- Loops and iterations
- Complex assertions
- Shared helper functions

### Configuration

```yaml
procedural_tests:
  file: tests/custom_tests.bsl    # Path to BSL file
  procedures:                      # List of test procedures
    - Тест_ComplexScenario
    - Тест_MultiStepProcess
    - Test_ValidationRules
```

**Path resolution:** Relative to `tests.yaml` directory.

### BSL Test Procedure Format

```bsl
&НаСервере
Процедура Тест_ProcedureName() Экспорт
    // Test logic

    // Use ВызватьИсключение for test failures
    Если Объект.Result <> ExpectedValue Тогда
        ВызватьИсключение "Expected X, got Y";
    КонецЕсли;

КонецПроцедуры
```

**Requirements:**
- ✅ Must start with `Тест_` or `Test_` prefix
- ✅ Must be exported (`Экспорт`)
- ✅ Must be `&НаСервере` (server-side)
- ✅ Raise exception on failure

### Access to Processor

Inside test procedures, you have full access to the processor object:

```bsl
&НаСервере
Процедура Тест_FullAccess() Экспорт
    // Access attributes
    Объект.Number1 = 10;

    // Call procedures
    CalculateНаСервере();

    // Access tabular sections
    Row = Объект.Lines.Add();
    Row.Product = "Apple";

    // Call commands
    ProcessTableНаСервере();

КонецПроцедуры
```

### Examples

#### Sequential Operations Test

```bsl
&НаСервере
Процедура Тест_SequentialOperations() Экспорт
    // Step 1: Add 10 + 5 = 15
    Объект.Number1 = 10;
    Объект.Number2 = 5;
    AddНаСервере();

    Если Объект.Result <> 15 Тогда
        ВызватьИсключение "Addition failed: expected 15, got " + Объект.Result;
    КонецЕсли;

    // Step 2: Multiply result by 2 = 30
    Объект.Number1 = Объект.Result;
    Объект.Number2 = 2;
    MultiplyНаСервере();

    Если Объект.Result <> 30 Тогда
        ВызватьИсключение "Multiplication failed: expected 30, got " + Объект.Result;
    КонецЕсли;

КонецПроцедуры
```

#### Table Processing Test

```bsl
&НаСервере
Процедура Тест_TableProcessing() Экспорт
    // Fill table
    For Index = 1 To 5 Do
        Row = Объект.Lines.Add();
        Row.Product = "Product" + Index;
        Row.Quantity = Index * 10;
        Row.Price = Index * 100;
    EndDo;

    // Process table
    ProcessTableНаСервере();

    // Verify results
    Если Объект.Lines.Count() <> 5 Тогда
        ВызватьИсключение "Expected 5 rows, got " + Объект.Lines.Count();
    КонецЕсли;

    // Check calculated values
    TotalAmount = 0;
    For Each Row In Объект.Lines Do
        TotalAmount = TotalAmount + Row.Amount;
    EndDo;

    Если TotalAmount <> 15000 Тогда
        ВызватьИсключение "Total amount mismatch";
    КонецЕсли;

КонецПроцедуры
```

#### Validation Rules Test

```bsl
&НаСервере
Процедура Тест_ValidationRules() Экспорт
    // Test 1: Negative amount should fail
    Объект.Amount = -100;
    ErrorCaught = False;

    Попытка
        ValidateAmountНаСервере();
    Исключение
        ErrorCaught = True;
        ErrorText = ОписаниеОшибки();

        Если Не СтрНайти(ErrorText, "positive") Тогда
            ВызватьИсключение "Wrong error message: " + ErrorText;
        КонецЕсли;
    КонецПопытки;

    Если Не ErrorCaught Тогда
        ВызватьИсключение "Expected validation error, but none was raised";
    КонецЕсли;

    // Test 2: Positive amount should pass
    Объект.Amount = 100;
    ValidateAmountНаСервере();  // Should not raise error

КонецПроцедуры
```

---

## BSL Testing Infrastructure

The generator automatically adds a testing infrastructure to `Module.bsl`:

```bsl
#Область ТестоваяИнфраструктура

Перем ТестовыеСообщения;

&НаСервере
Процедура НачатьЗаписьСообщений() Экспорт
    ТестовыеСообщения = Новый Массив;
КонецПроцедуры

&НаСервере
Функция ПолучитьТестовыеСообщения() Экспорт
    Возврат ТестовыеСообщения;
КонецФункции

&НаСервереБезКонтекста
Процедура ОтправитьСообщение(Текст)
    Если ЗначениеЗаполнено(ТестовыеСообщения) Тогда
        ТестовыеСообщения.Добавить(Текст);
    Иначе
        Сообщить(Текст);
    КонецЕсли;
КонецПроцедуры

#КонецОбласти
```

### Usage in BSL Code

**Instead of:**
```bsl
Сообщить("Operation complete");
```

**Use:**
```bsl
ОтправитьСообщение("Operation complete");
```

**Benefits:**
- ✅ Works in normal mode (calls `Сообщить`)
- ✅ Captured in test mode (stored in array)
- ✅ No code changes needed for production

### Message Interception Flow

```
Test starts
    ↓
НачатьЗаписьСообщений()
    ↓ (enables recording)
ОтправитьСообщение("text")
    ↓ (stores in array)
ПолучитьТестовыеСообщения()
    ↓ (retrieves array)
Test verifies messages
```

### Best Practices

1. **Always use wrapper:**
   ```bsl
   // ✅ Good (testable)
   ОтправитьСообщение("Done");

   // ❌ Bad (not captured in tests)
   Сообщить("Done");
   ```

2. **Message format:**
   ```bsl
   // ✅ Good (specific, testable)
   ОтправитьСообщение("Calculation complete: " + Result);

   // ❌ Bad (too generic)
   ОтправитьСообщение("Done");
   ```

3. **Error messages:**
   ```bsl
   // ✅ Good (includes details)
   ВызватьИсключение "Amount must be positive, got: " + Amount;

   // ❌ Bad (no context)
   ВызватьИсключение "Invalid amount";
   ```

---

## pytest Integration

### Generated File Structure

```
tmp/ProcessorName/
├── ProcessorName.epf           # Compiled EPF
├── ProcessorName/              # XML structure
└── tests/                      # Generated tests
    ├── test_ProcessorName.py   # Test file
    ├── conftest.py             # pytest fixtures
    ├── custom_tests.bsl        # Copied BSL tests
    └── __init__.py
```

### conftest.py (Fixtures)

Auto-generated fixtures for COM connection:

```python
@pytest.fixture(scope="session")
def epf_tester(check_com_support):
    """Session-wide EPF tester with COM connection"""
    tester = EPFTester(
        epf_path=EPF_PATH,
        ib_path=IB_PATH,
        use_external_connection=True,
    )

    connected = tester.connect_external()
    if not connected:
        pytest.fail(f"Failed to connect to {IB_PATH}")

    yield tester
    tester.disconnect()

@pytest.fixture(scope="function")
def processor(epf_tester):
    """Function-scope processor (clean state per test)"""
    yield epf_tester
```

**Scopes:**
- `session`: One connection for all tests (fast)
- `function`: Clean state per test (isolated)

### Test File Structure

```python
class TestDeclarative:
    """Declarative tests from YAML"""

    def test_calculation(self, processor):
        # Auto-generated from YAML
        pass

class TestProcedural:
    """Procedural tests from BSL"""

    def test_complex_scenario(self, processor):
        # Calls BSL procedure
        pass
```

### Running Tests

#### Basic Execution

```bash
# Run all tests
pytest tmp/ProcessorName/tests/

# Verbose output
pytest tmp/ProcessorName/tests/ -v

# Stop on first failure
pytest tmp/ProcessorName/tests/ -x

# Run specific test
pytest tmp/ProcessorName/tests/test_ProcessorName.py::TestDeclarative::test_calculation
```

#### Advanced Options

```bash
# Parallel execution (requires pytest-xdist)
pytest tmp/ProcessorName/tests/ -n 4

# Coverage report
pytest tmp/ProcessorName/tests/ --cov

# HTML report
pytest tmp/ProcessorName/tests/ --html=report.html

# JUnit XML (for CI/CD)
pytest tmp/ProcessorName/tests/ --junitxml=results.xml
```

#### Filtering Tests

```bash
# Run only declarative tests
pytest tmp/ProcessorName/tests/ -k "TestDeclarative"

# Run only procedural tests
pytest tmp/ProcessorName/tests/ -k "TestProcedural"

# Run tests matching pattern
pytest tmp/ProcessorName/tests/ -k "calculation"
```

### Test Output Example

```
======================== test session starts ========================
platform win32 -- Python 3.11.0, pytest-7.4.0
rootdir: E:\Projects\1c-processor-generator
plugins: cov-4.1.0

tmp/Calculator/tests/test_Calculator.py::TestDeclarative::test_addition PASSED     [ 16%]
tmp/Calculator/tests/test_Calculator.py::TestDeclarative::test_subtraction PASSED  [ 33%]
tmp/Calculator/tests/test_Calculator.py::TestDeclarative::test_multiplication PASSED [ 50%]
tmp/Calculator/tests/test_Calculator.py::TestDeclarative::test_zero_addition PASSED [ 66%]
tmp/Calculator/tests/test_Calculator.py::TestProcedural::test_sequential PASSED    [ 83%]
tmp/Calculator/tests/test_Calculator.py::TestProcedural::test_large_numbers PASSED [100%]

======================== 6 passed in 3.52s ==========================
```

---

## Running Tests

### Prerequisites Checklist

- [ ] Windows OS
- [ ] 1C:Enterprise 8.3 installed
- [ ] Python 3.8+ installed
- [ ] pywin32 installed (`pip install pywin32>=305`)
- [ ] persistent_ib exists (auto-created on first run)

### Step-by-Step Guide

#### 1. Generate EPF with Tests

```bash
python -m 1c_processor_generator yaml \
  --config config.yaml \
  --handlers-file handlers.bsl \
  --output-format epf
```

**Output:**
```
🚀 Генерація обробки з YAML: config.yaml...
✅ YAML успішно розпарсено: Calculator
📄 Завантаження tests.yaml: tests/calculator_tests.yaml
✅ Tests config завантажено: 4 declarative, 2 procedural
...
🎉 Готово! EPF створено: tmp/Calculator.epf
🧪 Генерація автоматичних тестів...
✅ Тести згенеровано: tmp/Calculator/tests
   Declarative: 4
   Procedural: 2

💡 Запустіть тести: pytest tmp/Calculator/tests
```

#### 2. Verify Generated Files

```bash
ls tmp/Calculator/tests/
```

Expected output:
```
test_Calculator.py
conftest.py
custom_tests.bsl
__init__.py
```

#### 3. Run Tests

```bash
cd E:\Projects\1c-processor-generator
pytest tmp/Calculator/tests/ -v
```

#### 4. Interpret Results

**Success:**
```
======================== 6 passed in 3.52s ==========================
```

**Failure:**
```
FAILED tmp/Calculator/tests/test_Calculator.py::test_addition
    AssertionError: Тест провалився: Атрибут Result: очікувалось 30, отримано 25
```

**Error:**
```
ERROR tmp/Calculator/tests/test_Calculator.py::test_addition
    ImportError: pywin32 не встановлено. COM тести пропущено.
```

### Continuous Integration

#### GitHub Actions Example

```yaml
name: Test 1C Processors

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pywin32

      - name: Install 1C Platform
        run: |
          # Download and install 1C (requires license)
          # Or use pre-installed runner

      - name: Generate EPF
        run: |
          python -m 1c_processor_generator yaml \
            --config config.yaml \
            --handlers-file handlers.bsl \
            --output-format epf

      - name: Run Tests
        run: pytest tmp/*/tests/ --junitxml=results.xml

      - name: Publish Test Results
        uses: EnricoMi/publish-unit-test-result-action@v2
        if: always()
        with:
          files: results.xml
```

---

## Troubleshooting

### Common Issues

#### 1. pywin32 Not Installed

**Error:**
```
pywin32 не встановлено. COM підключення недоступне.
```

**Solution:**
```bash
pip install pywin32>=305

# Verify installation
python -c "import win32com.client; print('OK')"
```

#### 2. Designer Not Found

**Error:**
```
Designer не знайдено!
Встановіть 1C:Підприємство або вкажіть шлях через --designer-path
```

**Solution:**
```bash
# Option 1: Set environment variable
set PATH_1C_DESIGNER=C:\Program Files\1cv8\8.3.25.1394\bin\1cv8.exe

# Option 2: Use CLI parameter
python -m 1c_processor_generator yaml \
  --designer-path "C:\Program Files\1cv8\8.3.25.1394\bin\1cv8.exe" \
  ...
```

#### 3. COM Connection Failed

**Error:**
```
Помилка External Connection: (-2147221005, 'Invalid class string', None, None)
```

**Possible causes:**
- 1C Platform not registered
- Wrong platform version
- Insufficient permissions

**Solution:**
```bash
# Re-register COM server
regsvr32 "C:\Program Files\1cv8\8.3.25.1394\bin\comcntr.dll"

# Check platform version
python -c "import win32com.client; print(win32com.client.Dispatch('V83.COMConnector'))"
```

#### 4. Infobase Lock

**Error:**
```
Помилка: Інформаційна база заблокована іншим процесом
```

**Solution:**
```bash
# Close all 1C sessions
taskkill /F /IM 1cv8.exe

# Clear persistent_ib cache
python -c "from 1c_processor_generator.persistent_ib_manager import PersistentIBManager; PersistentIBManager().clear_cache()"
```

#### 5. Test Timeout

**Error:**
```
pytest: error: test execution exceeded timeout of 300s
```

**Solution:**

Increase timeout in `tests.yaml`:
```yaml
settings:
  timeout: 600  # 10 minutes
```

#### 6. Message Not Captured

**Problem:**
```python
# Test fails: expected message not found
assert:
  messages: [{contains: "Done"}]
```

**Cause:** Using `Сообщить()` instead of `ОтправитьСообщение()`

**Solution:**

Update BSL code:
```bsl
// ❌ Wrong
Сообщить("Done");

// ✅ Correct
ОтправитьСообщение("Done");
```

#### 7. Module Not Found

**Error:**
```python
ImportError: cannot import name 'EPFTester'
```

**Solution:**
```bash
# Reinstall package in editable mode
pip install -e .

# Or add to PYTHONPATH
set PYTHONPATH=E:\Projects\1c-processor-generator;%PYTHONPATH%
```

### Debug Mode

Enable verbose logging:

```python
# In conftest.py, add:
import logging
logging.basicConfig(level=logging.DEBUG)
```

Run pytest with debug output:
```bash
pytest tmp/Calculator/tests/ -v --log-cli-level=DEBUG
```

---

## Best Practices

### Test Organization

#### 1. Separate Test Types

```yaml
# Good: Clear separation
declarative_tests:
  - name: test_simple_calculation
    # ...

procedural_tests:
  file: tests/complex_tests.bsl
  procedures:
    - Тест_ComplexScenario
```

#### 2. Descriptive Names

```yaml
# ✅ Good
- name: test_addition_with_positive_numbers
  description: "Verify addition returns correct sum"

# ❌ Bad
- name: test1
  description: "Test"
```

#### 3. One Concern Per Test

```yaml
# ✅ Good: Single responsibility
- name: test_addition
  execute_command: Add
  assert: {attributes: {Result: 30}}

# ❌ Bad: Multiple operations
- name: test_all_operations
  # Tests add, subtract, multiply...
```

### BSL Code Quality

#### 1. Meaningful Error Messages

```bsl
// ✅ Good
Если Result <> ExpectedValue Тогда
    ВызватьИсключение СтрШаблон(
        "Calculation error: expected %1, got %2",
        ExpectedValue, Result
    );
КонецЕсли;

// ❌ Bad
Если Result <> ExpectedValue Тогда
    ВызватьИсключение "Error";
КонецЕсли;
```

#### 2. Test Independence

```bsl
// ✅ Good: Self-contained
&НаСервере
Процедура Тест_Addition() Экспорт
    Объект.Number1 = 10;  // Reset state
    Объект.Number2 = 20;
    AddНаСервере();
    // Assert...
КонецПроцедуры

// ❌ Bad: Depends on previous test
&НаСервере
Процедура Тест_Subtraction() Экспорт
    // Assumes Number1 already set
    Объект.Number2 = 5;
    SubtractНаСервере();
КонецПроцедуры
```

#### 3. Helper Functions

```bsl
// Extract common logic
&НаСервере
Функция AssertEqual(Actual, Expected, Message)
    Если Actual <> Expected Тогда
        ВызватьИсключение СтрШаблон(
            "%1: expected %2, got %3",
            Message, Expected, Actual
        );
    КонецЕсли;
КонецФункции

&НаСервере
Процедура Тест_Calculation() Экспорт
    Объект.Number1 = 10;
    Объект.Number2 = 20;
    AddНаСервере();

    AssertEqual(Объект.Result, 30, "Addition failed");
КонецПроцедуры
```

### Performance Optimization

#### 1. Use External Connection

```yaml
# ✅ Fast (default)
settings:
  use_external_connection: true
  use_automation_server: false

# ❌ Slow (only if UI needed)
settings:
  use_external_connection: false
  use_automation_server: true
```

#### 2. Session-Scope Fixtures

Generated `conftest.py` uses session scope by default:
```python
@pytest.fixture(scope="session")  # One connection for all tests
def epf_tester(check_com_support):
    # ...
```

#### 3. Minimize Data Setup

```yaml
# ✅ Good: Only necessary data
setup:
  attributes: {Number1: 10, Number2: 20}

# ❌ Bad: Excessive data
setup:
  table_rows:
    Lines:
      # 1000 rows...
```

### Maintenance

#### 1. Version Control

```
.gitignore:
tmp/                    # Generated files
*.epf                   # Compiled EPF
__pycache__/
*.pyc
```

Keep in version control:
```
tests/
├── calculator_tests.yaml   # Test configuration
└── custom_tests.bsl        # Procedural tests
```

#### 2. Documentation

```yaml
# Document complex tests
declarative_tests:
  - name: test_complex_calculation
    description: |
      Tests multi-step calculation:
      1. Load initial data
      2. Apply discount
      3. Calculate taxes
      4. Verify total amount
```

#### 3. Regular Cleanup

```bash
# Remove old test runs
rm -rf tmp/*/tests/

# Clear persistent_ib cache
python -c "from 1c_processor_generator.persistent_ib_manager import PersistentIBManager; PersistentIBManager().clear_cache()"
```

---

## Examples

### Complete Working Example

See `examples/yaml/calculator_with_tests/` for a full example with:
- ✅ 4 declarative tests
- ✅ 2 procedural tests
- ✅ BSL wrapper integration
- ✅ Detailed README

### Common Patterns

#### Pattern 1: Data Processing Test

```yaml
- name: test_data_processing
  description: "Process table data and verify results"
  setup:
    table_rows:
      InputData:
        - {Code: "A001", Quantity: 10}
        - {Code: "A002", Quantity: 20}
  execute_command: ProcessData
  assert:
    tables:
      - table_name: OutputData
        row_count: 2
      - table_name: Errors
        row_count: 0
```

#### Pattern 2: Validation Chain Test

```bsl
&НаСервере
Процедура Тест_ValidationChain() Экспорт
    // Test 1: Empty value
    Объект.RequiredField = "";
    AssertValidationError("Required field");

    // Test 2: Invalid format
    Объект.RequiredField = "INVALID";
    AssertValidationError("Invalid format");

    // Test 3: Valid value
    Объект.RequiredField = "VALID_001";
    ValidateНаСервере();  // Should not raise
КонецПроцедуры

&НаСервере
Процедура AssertValidationError(ExpectedMessage)
    ErrorCaught = False;
    Попытка
        ValidateНаСервере();
    Исключение
        ErrorCaught = True;
        ErrorText = ОписаниеОшибки();
        Если Не СтрНайти(ErrorText, ExpectedMessage) Тогда
            ВызватьИсключение "Wrong error: " + ErrorText;
        КонецЕсли;
    КонецПопытки;

    Если Не ErrorCaught Тогда
        ВызватьИсключение "Expected error not raised";
    КонецЕсли;
КонецПроцедуры
```

#### Pattern 3: Master-Detail Test

```yaml
- name: test_master_detail
  description: "Verify master-detail relationship"
  setup:
    attributes:
      MasterID: "MASTER_001"
    table_rows:
      Details:
        - {DetailID: "D001", Amount: 100}
        - {DetailID: "D002", Amount: 200}
  execute_command: CalculateTotal
  assert:
    attributes:
      TotalAmount: 300
    messages:
      - contains: "2 items processed"
```

---

## Conclusion

The 1C Processor Generator testing framework provides:

✅ **Automated Testing**: Generate pytest tests from YAML
✅ **Hybrid Approach**: Combine declarative and procedural tests
✅ **Fast Execution**: External Connection for speed
✅ **Easy Debugging**: Clear error messages and logging
✅ **CI/CD Ready**: JUnit XML output support

### Next Steps

1. **Try the example**: `examples/yaml/calculator_with_tests/`
2. **Write your first test**: Start with simple declarative tests
3. **Add procedural tests**: For complex scenarios
4. **Integrate with CI/CD**: Automate testing pipeline

### Resources

- **LLM_PROMPT.md**: Documentation for LLM-assisted development
- **QUICK_REFERENCE.md**: One-page cheatsheet
- **examples/yaml/**: Working examples

### Support

For issues and questions:
- GitHub Issues: https://github.com/anthropics/1c-processor-generator/issues
- Documentation: `docs/` directory

---

**Version**: 2.23.2
**Last Updated**: 2025-11-17
**Author**: 1C Processor Generator Team

## Migration from v2.16.0-v2.23.0

See CHANGELOG.md for detailed migration guide from old structure to v2.23.2 auto-detection architecture.
