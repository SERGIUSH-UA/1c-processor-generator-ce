"""
Integration tests for ValueTable and FormAttribute support (v2.27.0)

Tests new features:
- ValueTable form-level attributes with columns
- FormAttribute support (SpreadsheetDocument, BinaryData, etc.)
- YAML CRUD operations
- Reference checking for both types

Note: XML extraction tests are omitted as forms are typically in separate files
and testing them requires complex XML structures. The CRUD operations and
reference checking are the critical functionality.
"""

import pytest
import tempfile
import shutil
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import using importlib (module name starts with digit)
import importlib

yaml_patcher_module = importlib.import_module('1c_processor_generator.yaml_patcher')

YAMLPatcher = yaml_patcher_module.YAMLPatcher
ReferenceChecker = yaml_patcher_module.ReferenceChecker


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for testing."""
    tmpdir = tempfile.mkdtemp()
    workspace = Path(tmpdir)
    yield workspace
    shutil.rmtree(tmpdir)


class TestReferenceChecker_ValueTable:
    """Test ReferenceChecker for ValueTable (v2.27.0)."""

    def test_detect_value_table_reference_in_bsl(self, temp_workspace):
        """Test detection of ValueTable references in BSL code."""
        config_path = temp_workspace / "config.yaml"
        config_content = """
processor:
  name: Test
  synonym_ru: Тест

forms:
  - name: Форма
    value_tables:
      - name: DataTable
        columns:
          - name: Field1
            type: string
"""
        config_path.write_text(config_content, encoding='utf-8')

        # BSL code with reference
        bsl_code = """
Процедура LoadData()
    Объект.DataTable.Clear();
    Row = Объект.DataTable.Add();
    Row.Field1 = "Test";
КонецПроцедуры
"""

        # Load config
        from ruamel.yaml import YAML
        yaml = YAML()
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.load(f)

        # Check references
        checker = ReferenceChecker(config, bsl_code)
        references = checker.check_value_table_references("DataTable")

        assert len(references) > 0
        assert any("Объект.DataTable" in ref for ref in references)

    def test_no_references_to_value_table(self, temp_workspace):
        """Test case when ValueTable has no references."""
        config_path = temp_workspace / "config.yaml"
        config_content = """
processor:
  name: Test
forms:
  - name: Форма
    value_tables:
      - name: UnusedTable
        columns: []
"""
        config_path.write_text(config_content, encoding='utf-8')

        bsl_code = "// No references"

        from ruamel.yaml import YAML
        yaml = YAML()
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.load(f)

        checker = ReferenceChecker(config, bsl_code)
        references = checker.check_value_table_references("UnusedTable")

        assert len(references) == 0


class TestReferenceChecker_FormAttribute:
    """Test ReferenceChecker for FormAttribute (v2.27.0)."""

    def test_detect_form_attribute_reference_in_bsl(self, temp_workspace):
        """Test detection of FormAttribute references in BSL code."""
        config_path = temp_workspace / "config.yaml"
        config_content = """
processor:
  name: Test
forms:
  - name: Форма
    form_attributes:
      - name: Report
        type: SpreadsheetDocument
"""
        config_path.write_text(config_content, encoding='utf-8')

        bsl_code = """
Процедура GenerateReport()
    Report.Clear();
    Report.Put(Template);
    Элементы.Report.Visible = True;
КонецПроцедуры
"""

        from ruamel.yaml import YAML
        yaml = YAML()
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.load(f)

        checker = ReferenceChecker(config, bsl_code)
        references = checker.check_form_attribute_references("Report")

        assert len(references) > 0
        assert any("Элементы.Report" in ref for ref in references)


class TestYAMLPatcher_ValueTable:
    """Test YAMLPatcher CRUD operations for ValueTable (v2.27.0)."""

    def test_add_value_table_to_form(self, temp_workspace):
        """Test adding ValueTable to form."""
        config_path = temp_workspace / "config.yaml"
        config_content = """
processor:
  name: Test
  synonym_ru: Тест

forms:
  - name: Форма
    title_ru: Форма
"""
        config_path.write_text(config_content, encoding='utf-8')

        patcher = YAMLPatcher(str(config_path), "")

        # Add ValueTable
        value_table_data = {
            'name': 'ResultTable',
            'columns': [
                {'name': 'Product', 'type': 'string'},
                {'name': 'Amount', 'type': 'decimal'}
            ]
        }

        success = patcher.add_value_table(0, value_table_data)
        assert success is True

        # Save and verify
        patcher.save()

        updated = config_path.read_text(encoding='utf-8')
        assert 'value_tables:' in updated
        assert 'ResultTable' in updated
        assert 'Product' in updated

    def test_delete_value_table_without_references(self, temp_workspace):
        """Test deleting ValueTable without references."""
        config_path = temp_workspace / "config.yaml"
        config_content = """
processor:
  name: Test

forms:
  - name: Форма
    value_tables:
      - name: OldTable
        columns:
          - name: Field1
            type: string
"""
        config_path.write_text(config_content, encoding='utf-8')

        patcher = YAMLPatcher(str(config_path), "// no references")

        success = patcher.delete_value_table(0, "OldTable", force=False)
        assert success is True

        patcher.save()

        updated = config_path.read_text(encoding='utf-8')
        assert 'OldTable' not in updated

    def test_delete_value_table_with_references_blocked(self, temp_workspace):
        """Test that deleting ValueTable with references is blocked."""
        config_path = temp_workspace / "config.yaml"
        config_content = """
processor:
  name: Test

forms:
  - name: Форма
    value_tables:
      - name: UsedTable
        columns: []
"""
        config_path.write_text(config_content, encoding='utf-8')

        bsl_code = """
Процедура Test()
    Объект.UsedTable.Clear();
КонецПроцедуры
"""

        patcher = YAMLPatcher(str(config_path), bsl_code)

        success = patcher.delete_value_table(0, "UsedTable", force=False)
        assert success is False  # Blocked by reference

        warnings = patcher.get_warnings()
        assert len(warnings) > 0
        assert "UsedTable" in warnings[0]


class TestYAMLPatcher_FormAttribute:
    """Test YAMLPatcher CRUD operations for FormAttribute (v2.27.0)."""

    def test_add_form_attribute(self, temp_workspace):
        """Test adding FormAttribute to form."""
        config_path = temp_workspace / "config.yaml"
        config_content = """
processor:
  name: Test

forms:
  - name: Форма
    title_ru: Форма
"""
        config_path.write_text(config_content, encoding='utf-8')

        patcher = YAMLPatcher(str(config_path), "")

        # Add SpreadsheetDocument
        form_attr_data = {
            'name': 'Report',
            'type': 'SpreadsheetDocument'
        }

        success = patcher.add_form_attribute(0, form_attr_data)
        assert success is True

        patcher.save()

        updated = config_path.read_text(encoding='utf-8')
        assert 'form_attributes:' in updated
        assert 'Report' in updated
        assert 'SpreadsheetDocument' in updated

    def test_delete_form_attribute_without_references(self, temp_workspace):
        """Test deleting FormAttribute without references."""
        config_path = temp_workspace / "config.yaml"
        config_content = """
processor:
  name: Test

forms:
  - name: Форма
    form_attributes:
      - name: OldReport
        type: SpreadsheetDocument
"""
        config_path.write_text(config_content, encoding='utf-8')

        patcher = YAMLPatcher(str(config_path), "// no references")

        success = patcher.delete_form_attribute(0, "OldReport", force=False)
        assert success is True

        patcher.save()

        updated = config_path.read_text(encoding='utf-8')
        assert 'OldReport' not in updated


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
