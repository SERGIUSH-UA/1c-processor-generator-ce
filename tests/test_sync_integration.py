"""
Integration tests for Sync Tool (v2.25.0+)

Tests the full sync workflow:
- Snapshot creation during generation
- XML/BSL change detection
- Change mapping to YAML/BSL updates
- File updates with backup
- LLM mode functionality
"""

import pytest
import tempfile
import shutil
import sys
import json
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import using importlib (module name starts with digit)
import importlib

generator_module = importlib.import_module('1c_processor_generator.generator')
models_module = importlib.import_module('1c_processor_generator.models')
xml_differ_module = importlib.import_module('1c_processor_generator.xml_differ')
bsl_differ_module = importlib.import_module('1c_processor_generator.bsl_differ')
change_mapper_module = importlib.import_module('1c_processor_generator.change_mapper')
sync_tool_module = importlib.import_module('1c_processor_generator.sync_tool')

ProcessorGenerator = generator_module.ProcessorGenerator
Processor = models_module.Processor
Attribute = models_module.Attribute
Form = models_module.Form
FormElement = models_module.FormElement
Command = models_module.Command
XMLDiffer = xml_differ_module.XMLDiffer
ChangeType = xml_differ_module.ChangeType
ElementType = xml_differ_module.ElementType
BSLDiffer = bsl_differ_module.BSLDiffer
BSLChangeType = bsl_differ_module.BSLChangeType
ChangeMapper = change_mapper_module.ChangeMapper
SyncTool = sync_tool_module.SyncTool
run_sync = sync_tool_module.run_sync
XMLChange = xml_differ_module.XMLChange


@pytest.fixture
def test_processor():
    """Create a simple test processor."""
    processor = Processor(
        name="TestSync",
        synonym_ru="Тестовый процессор",
        platform_version="2.11"
    )

    # Add attributes
    processor.attributes.append(Attribute(
        name="Product",
        type="string",
        synonym_ru="Товар"
    ))

    processor.attributes.append(Attribute(
        name="Quantity",
        type="number",
        synonym_ru="Количество"
    ))

    # Add form
    form = Form(
        name="Форма",
        properties={
            "Title": {
                "ru": "Главная форма",
                "uk": "Головна форма"
            }
        }
    )

    # Add form elements
    form.elements.append(FormElement(
        element_type="InputField",
        name="Product",
        attribute="Product",
        properties={"Title": {"ru": "Товар"}}
    ))

    form.elements.append(FormElement(
        element_type="InputField",
        name="Quantity",
        attribute="Quantity",
        properties={"Title": {"ru": "Количество"}, "Width": 10}
    ))

    # Add command
    form.commands.append(Command(
        name="Calculate",
        title_ru="Рассчитать",
        title_uk="Розрахувати",
        action="Calculate"
    ))

    processor.forms.append(form)

    # Add BSL code
    form.events_bsl = {
        "Calculate": "Сообщить(\"Calculated\");"
    }

    return processor


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for testing."""
    tmpdir = tempfile.mkdtemp()
    workspace = Path(tmpdir)

    yield workspace

    # Cleanup
    shutil.rmtree(tmpdir)


class TestSnapshotCreation:
    """Test snapshot creation during generation."""

    def test_snapshot_created_on_generation(self, test_processor, temp_workspace):
        """Test that snapshot is created when generating processor."""
        generator = ProcessorGenerator(test_processor)

        # Generate with snapshot enabled (default)
        processor_root = generator.generate(str(temp_workspace), save_snapshot=True)

        assert processor_root is not None

        # Check snapshot directory exists
        snapshot_dir = temp_workspace / "_snapshot"
        assert snapshot_dir.exists()

        # Check snapshot files
        assert (snapshot_dir / "original.xml").exists()
        assert (snapshot_dir / "original_handlers.bsl").exists()
        assert (snapshot_dir / "metadata.json").exists()

        # Verify metadata
        metadata = json.loads((snapshot_dir / "metadata.json").read_text())
        assert metadata["processor_name"] == "TestSync"
        assert metadata["platform_version"] == "2.11"
        assert "generated_at" in metadata

    def test_snapshot_not_created_when_disabled(self, test_processor, temp_workspace):
        """Test that snapshot is NOT created when save_snapshot=False."""
        generator = ProcessorGenerator(test_processor)

        processor_root = generator.generate(str(temp_workspace), save_snapshot=False)

        assert processor_root is not None

        snapshot_dir = temp_workspace / "_snapshot"
        assert not snapshot_dir.exists()


class TestXMLDiffDetection:
    """Test XML change detection."""

    def test_detect_attribute_rename(self, temp_workspace):
        """Test detection of renamed attribute."""
        # Create original and modified XML
        original_xml = temp_workspace / "original.xml"
        modified_xml = temp_workspace / "modified.xml"

        # Simple test XML with attribute
        original_content = """<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core">
    <ExternalDataProcessor>
        <ChildObjects>
            <Attribute>
                <Properties>
                    <Name>Product</Name>
                    <Synonym>
                        <v8:item><v8:lang>ru</v8:lang><v8:content>Товар</v8:content></v8:item>
                    </Synonym>
                </Properties>
            </Attribute>
        </ChildObjects>
    </ExternalDataProcessor>
</MetaDataObject>"""

        modified_content = original_content.replace("<Name>Product</Name>", "<Name>ProductName</Name>")

        original_xml.write_text(original_content, encoding='utf-8')
        modified_xml.write_text(modified_content, encoding='utf-8')

        # Detect changes
        differ = XMLDiffer(str(original_xml), str(modified_xml))
        changes = differ.detect_changes()

        # Should detect rename
        renames = [c for c in changes if c.change_type == ChangeType.RENAME]
        assert len(renames) == 1
        assert renames[0].old_value == "Product"
        assert renames[0].new_value == "ProductName"

    def test_detect_property_change(self, temp_workspace):
        """Test detection of property changes."""
        original_xml = temp_workspace / "original.xml"
        modified_xml = temp_workspace / "modified.xml"

        original_content = """<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core">
    <ExternalDataProcessor>
        <ChildObjects>
            <Attribute>
                <Properties>
                    <Name>Product</Name>
                    <Synonym>
                        <v8:item><v8:lang>ru</v8:lang><v8:content>Товар</v8:content></v8:item>
                    </Synonym>
                </Properties>
            </Attribute>
        </ChildObjects>
    </ExternalDataProcessor>
</MetaDataObject>"""

        modified_content = original_content.replace("<v8:content>Товар</v8:content>",
                                                    "<v8:content>Товар Изменённый</v8:content>")

        original_xml.write_text(original_content, encoding='utf-8')
        modified_xml.write_text(modified_content, encoding='utf-8')

        differ = XMLDiffer(str(original_xml), str(modified_xml))
        changes = differ.detect_changes()

        # Should detect property change
        prop_changes = [c for c in changes if c.change_type == ChangeType.PROPERTY_CHANGE]
        assert len(prop_changes) >= 1


class TestBSLDiffDetection:
    """Test BSL code change detection."""

    def test_detect_new_procedure(self):
        """Test detection of newly added procedure."""
        original_bsl = """
Процедура Calculate()
    Сообщить("Original");
КонецПроцедуры
"""

        modified_bsl = """
Процедура Calculate()
    Сообщить("Original");
КонецПроцедуры

Процедура NewProcedure()
    Сообщить("New");
КонецПроцедуры
"""

        differ = BSLDiffer(original_bsl, modified_bsl)
        changes = differ.detect_changes()

        added = differ.get_added_procedures()
        assert len(added) == 1
        assert added[0].procedure_name == "NewProcedure"

    def test_detect_modified_procedure(self):
        """Test detection of modified procedure."""
        original_bsl = """
Процедура Calculate()
    Result = 100;
КонецПроцедуры
"""

        modified_bsl = """
Процедура Calculate()
    Result = 200;  // Changed
КонецПроцедуры
"""

        differ = BSLDiffer(original_bsl, modified_bsl)
        changes = differ.detect_changes()

        modified = differ.get_modified_procedures()
        assert len(modified) == 1
        assert modified[0].procedure_name == "Calculate"

    def test_detect_deleted_procedure(self):
        """Test detection of deleted procedure."""
        original_bsl = """
Процедура Calculate()
    Сообщить("Test");
КонецПроцедуры

Процедура OldProcedure()
    Сообщить("Old");
КонецПроцедуры
"""

        modified_bsl = """
Процедура Calculate()
    Сообщить("Test");
КонецПроцедуры
"""

        differ = BSLDiffer(original_bsl, modified_bsl)
        changes = differ.detect_changes()

        deleted = differ.get_deleted_procedures()
        assert len(deleted) == 1
        assert deleted[0].procedure_name == "OldProcedure"


class TestChangeMapping:
    """Test mapping of XML/BSL changes to YAML updates."""

    def test_map_attribute_rename(self, temp_workspace):
        """Test mapping attribute rename to YAML update."""
        # Create minimal config
        config_path = temp_workspace / "config.yaml"
        config_content = """
processor:
  name: Test
  synonym_ru: Test

attributes:
  - name: Product
    type: string
    synonym_ru: Товар
"""
        config_path.write_text(config_content, encoding='utf-8')

        # Create mapper
        mapper = ChangeMapper(str(config_path))

        # Simulate XML change (rename)
        xml_change = XMLChange(
            change_type=ChangeType.RENAME,
            element_type=ElementType.ATTRIBUTE,
            xpath="//Attribute[Name='Product']",
            old_value="Product",
            new_value="ProductName"
        )

        # Map to YAML updates
        updates = mapper.map_xml_changes([xml_change])

        assert len(updates) == 1
        assert updates[0].path == "attributes[0].name"
        assert updates[0].old_value == "Product"
        assert updates[0].new_value == "ProductName"


class TestSyncTool:
    """Test full sync tool workflow."""

    @patch('builtins.input', return_value='y')  # Auto-confirm
    def test_sync_workflow_rename(self, mock_input, test_processor, temp_workspace):
        """Test full sync workflow for attribute rename."""
        # Generate processor with snapshot
        generator = ProcessorGenerator(test_processor)
        processor_root = generator.generate(str(temp_workspace), save_snapshot=True)

        # Get snapshot paths
        snapshot_dir = temp_workspace / "_snapshot"
        original_xml = snapshot_dir / "original.xml"

        # Create modified XML (rename Product → ProductName)
        modified_xml = temp_workspace / "modified.xml"
        original_content = original_xml.read_text(encoding='utf-8')
        modified_content = original_content.replace(
            "<Name>Product</Name>",
            "<Name>ProductName</Name>"
        )
        modified_xml.write_text(modified_content, encoding='utf-8')

        # Create config and handlers files
        config_path = temp_workspace / "config.yaml"
        handlers_path = temp_workspace / "handlers.bsl"

        config_content = """
processor:
  name: TestSync
  synonym_ru: Тестовый процессор

attributes:
  - name: Product
    type: string
    synonym_ru: Товар

forms:
  - name: Форма
    properties:
      Title:
        ru: Главная форма
    elements:
      - element_type: InputField
        name: Product
        attribute: Product
"""

        config_path.write_text(config_content, encoding='utf-8')
        handlers_path.write_text("// handlers", encoding='utf-8-sig')

        # Run sync
        exit_code = run_sync(
            original_xml=str(original_xml),
            modified_xml=str(modified_xml),
            config=str(config_path),
            handlers=str(handlers_path),
            auto_apply=True,
            json_output=False,
            llm_mode=False
        )

        assert exit_code == 0

        # Verify YAML was updated
        updated_config = config_path.read_text(encoding='utf-8')
        assert "ProductName" in updated_config
        # "Product" appears in: element name, and twice in "ProductName" string
        assert "name: Product\n" in updated_config  # Element name preserved
        assert "attribute: ProductName" in updated_config  # Attribute reference updated

    def test_llm_mode_json_output(self, test_processor, temp_workspace):
        """Test LLM mode runs without errors."""
        # Generate processor
        generator = ProcessorGenerator(test_processor)
        generator.generate(str(temp_workspace), save_snapshot=True)

        snapshot_dir = temp_workspace / "_snapshot"
        original_xml = snapshot_dir / "original.xml"

        # No changes - just test that LLM mode works
        config_path = temp_workspace / "config.yaml"
        handlers_path = temp_workspace / "handlers.bsl"

        config_path.write_text("processor:\n  name: Test\n  synonym_ru: Test\nattributes: []", encoding='utf-8')
        handlers_path.write_text("// handlers", encoding='utf-8-sig')

        # Run sync in LLM mode with JSON output
        exit_code = run_sync(
            original_xml=str(original_xml),
            modified_xml=str(original_xml),  # No changes
            config=str(config_path),
            handlers=str(handlers_path),
            auto_apply=True,
            json_output=True,
            llm_mode=True
        )

        # Should complete successfully
        assert exit_code == 0


class TestBackupRestore:
    """Test backup and restore functionality."""

    def test_backup_created(self, temp_workspace):
        """Test that backup is created before applying changes."""
        config_path = temp_workspace / "config.yaml"
        handlers_path = temp_workspace / "handlers.bsl"

        config_path.write_text("test: original", encoding='utf-8')
        handlers_path.write_text("// original", encoding='utf-8')

        # Create minimal XML files for SyncTool
        original_xml = temp_workspace / "original.xml"
        modified_xml = temp_workspace / "modified.xml"

        minimal_xml = """<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses">
    <ExternalDataProcessor>
        <ChildObjects></ChildObjects>
    </ExternalDataProcessor>
</MetaDataObject>"""

        original_xml.write_text(minimal_xml, encoding='utf-8')
        modified_xml.write_text(minimal_xml, encoding='utf-8')

        # Create sync tool
        tool = SyncTool(
            original_xml=str(original_xml),
            modified_xml=str(modified_xml),
            config_path=str(config_path),
            handlers_path=str(handlers_path),
            auto_apply=True
        )

        # Create backup
        backup_dir = tool._create_backup()

        assert Path(backup_dir).exists()
        assert (Path(backup_dir) / "config.yaml").exists()
        assert (Path(backup_dir) / "handlers.bsl").exists()

        # Verify content
        backup_config = (Path(backup_dir) / "config.yaml").read_text(encoding='utf-8')
        assert backup_config == "test: original"


# Integration test that runs full workflow
class TestFullIntegration:
    """End-to-end integration tests."""

    def test_full_workflow_with_real_files(self, test_processor, temp_workspace):
        """Test complete workflow: generate → modify → sync."""
        # Step 1: Generate processor with snapshot
        test_processor.config_dir = str(temp_workspace)  # Set config dir

        generator = ProcessorGenerator(test_processor)
        processor_root = generator.generate(str(temp_workspace), save_snapshot=True)

        assert processor_root is not None

        # Step 2: Modify generated XML
        main_xml = processor_root / f"{test_processor.name}.xml"
        original_content = main_xml.read_text(encoding='utf-8')

        # Make multiple changes
        modified_content = original_content
        modified_content = modified_content.replace("<Name>Product</Name>", "<Name>ProductName</Name>")
        modified_content = modified_content.replace("<v8:content>Товар</v8:content>",
                                                    "<v8:content>Товар Modified</v8:content>")

        modified_xml = temp_workspace / "modified.xml"
        modified_xml.write_text(modified_content, encoding='utf-8')

        # Step 3: Create config and handlers
        config_path = temp_workspace / "config.yaml"
        handlers_path = temp_workspace / "handlers.bsl"

        config_path.write_text("""
processor:
  name: TestSync
  synonym_ru: Тестовый процессор

attributes:
  - name: Product
    type: string
    synonym_ru: Товар
  - name: Quantity
    type: number
    synonym_ru: Количество

forms:
  - name: Форма
    title_ru: Главная форма
    title_uk: Головна форма
    elements:
      - type: InputField
        name: Product
        attribute: Product
        title_ru: Товар
    commands:
      - name: Calculate
        title_ru: Рассчитать
        title_uk: Розрахувати
        action: Calculate
        handler: Calculate
""", encoding='utf-8')

        handlers_path.write_text("Процедура Calculate()\nКонецПроцедуры", encoding='utf-8-sig')

        # Step 4: Run sync
        snapshot_dir = temp_workspace / "_snapshot"
        original_xml = snapshot_dir / "original.xml"

        exit_code = run_sync(
            original_xml=str(original_xml),
            modified_xml=str(modified_xml),
            config=str(config_path),
            handlers=str(handlers_path),
            auto_apply=True,
            json_output=False,
            llm_mode=False
        )

        # Step 5: Verify
        assert exit_code == 0

        # Check YAML was updated
        updated_yaml = config_path.read_text(encoding='utf-8')
        assert "ProductName" in updated_yaml

        # Check backup exists
        backups = list(temp_workspace.glob(".sync_backup_*"))
        assert len(backups) >= 1


class TestStructuralChanges_Attribute:
    """Test structural changes for attributes (add/delete) - Phase 2."""

    def test_add_attribute_to_yaml(self, temp_workspace):
        """Test adding a new attribute via sync."""
        # Create initial config with one attribute
        config_path = temp_workspace / "config.yaml"
        config_content = """
processor:
  name: TestAddAttr
  synonym_ru: Тест

attributes:
  - name: ExistingAttr
    type: string
    synonym_ru: Существующий
"""
        config_path.write_text(config_content, encoding='utf-8')

        # Create original and modified XML
        original_xml = temp_workspace / "original.xml"
        modified_xml = temp_workspace / "modified.xml"

        # Simple XML with one attribute
        original_content = """<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core">
    <ExternalDataProcessor>
        <ChildObjects>
            <Attribute>
                <Properties>
                    <Name>ExistingAttr</Name>
                    <Synonym>
                        <v8:item><v8:lang>ru</v8:lang><v8:content>Существующий</v8:content></v8:item>
                    </Synonym>
                    <Type>
                        <v8:Type>xs:string</v8:Type>
                    </Type>
                </Properties>
            </Attribute>
        </ChildObjects>
    </ExternalDataProcessor>
</MetaDataObject>"""

        # Modified XML with new attribute
        modified_content = """<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core">
    <ExternalDataProcessor>
        <ChildObjects>
            <Attribute>
                <Properties>
                    <Name>ExistingAttr</Name>
                    <Synonym>
                        <v8:item><v8:lang>ru</v8:lang><v8:content>Существующий</v8:content></v8:item>
                    </Synonym>
                    <Type>
                        <v8:Type>xs:string</v8:Type>
                    </Type>
                </Properties>
            </Attribute>
            <Attribute>
                <Properties>
                    <Name>NewAttribute</Name>
                    <Synonym>
                        <v8:item><v8:lang>ru</v8:lang><v8:content>Новый атрибут</v8:content></v8:item>
                    </Synonym>
                    <Type>
                        <v8:Type>xs:decimal</v8:Type>
                    </Type>
                </Properties>
            </Attribute>
        </ChildObjects>
    </ExternalDataProcessor>
</MetaDataObject>"""

        original_xml.write_text(original_content, encoding='utf-8')
        modified_xml.write_text(modified_content, encoding='utf-8')

        # Create handlers file
        handlers_path = temp_workspace / "handlers.bsl"
        handlers_path.write_text("// handlers", encoding='utf-8-sig')

        # Run sync with auto-apply
        exit_code = run_sync(
            original_xml=str(original_xml),
            modified_xml=str(modified_xml),
            config=str(config_path),
            handlers=str(handlers_path),
            auto_apply=True,
            json_output=False,
            llm_mode=False
        )

        assert exit_code == 0

        # Verify YAML was updated
        updated_yaml = config_path.read_text(encoding='utf-8')
        assert "NewAttribute" in updated_yaml
        assert "synonym_ru: Новый атрибут" in updated_yaml or "synonym_ru: 'Новый атрибут'" in updated_yaml
        # xs:decimal in XML maps to 'number' in YAML (our internal convention)
        assert "type: number" in updated_yaml

    def test_delete_attribute_without_references(self, temp_workspace):
        """Test deleting an attribute that has no references."""
        # Create config with two attributes
        config_path = temp_workspace / "config.yaml"
        config_content = """
processor:
  name: TestDelAttr
  synonym_ru: Тест

attributes:
  - name: Attr1
    type: string
    synonym_ru: Атрибут 1
  - name: Attr2
    type: number
    synonym_ru: Атрибут 2
"""
        config_path.write_text(config_content, encoding='utf-8')

        # Create XMLs
        original_xml = temp_workspace / "original.xml"
        modified_xml = temp_workspace / "modified.xml"

        original_content = """<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core">
    <ExternalDataProcessor>
        <ChildObjects>
            <Attribute>
                <Properties>
                    <Name>Attr1</Name>
                    <Synonym>
                        <v8:item><v8:lang>ru</v8:lang><v8:content>Атрибут 1</v8:content></v8:item>
                    </Synonym>
                </Properties>
            </Attribute>
            <Attribute>
                <Properties>
                    <Name>Attr2</Name>
                    <Synonym>
                        <v8:item><v8:lang>ru</v8:lang><v8:content>Атрибут 2</v8:content></v8:item>
                    </Synonym>
                </Properties>
            </Attribute>
        </ChildObjects>
    </ExternalDataProcessor>
</MetaDataObject>"""

        # Modified: Attr2 deleted
        modified_content = original_content.replace(
            """            <Attribute>
                <Properties>
                    <Name>Attr2</Name>
                    <Synonym>
                        <v8:item><v8:lang>ru</v8:lang><v8:content>Атрибут 2</v8:content></v8:item>
                    </Synonym>
                </Properties>
            </Attribute>""", ""
        )

        original_xml.write_text(original_content, encoding='utf-8')
        modified_xml.write_text(modified_content, encoding='utf-8')

        handlers_path = temp_workspace / "handlers.bsl"
        handlers_path.write_text("// No references to Attr2", encoding='utf-8-sig')

        # Run sync
        exit_code = run_sync(
            original_xml=str(original_xml),
            modified_xml=str(modified_xml),
            config=str(config_path),
            handlers=str(handlers_path),
            auto_apply=True,
            json_output=False,
            llm_mode=False
        )

        assert exit_code == 0

        # Verify Attr2 was removed
        updated_yaml = config_path.read_text(encoding='utf-8')
        assert "Attr1" in updated_yaml
        assert "Attr2" not in updated_yaml

    def test_delete_attribute_with_references_blocked(self, temp_workspace):
        """Test that deleting an attribute with references is blocked."""
        # Create config
        config_path = temp_workspace / "config.yaml"
        config_content = """
processor:
  name: TestDelRef
  synonym_ru: Тест

attributes:
  - name: ReferencedAttr
    type: string
    synonym_ru: Используется
"""
        config_path.write_text(config_content, encoding='utf-8')

        # Create XMLs
        original_xml = temp_workspace / "original.xml"
        modified_xml = temp_workspace / "modified.xml"

        original_content = """<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core">
    <ExternalDataProcessor>
        <ChildObjects>
            <Attribute>
                <Properties>
                    <Name>ReferencedAttr</Name>
                    <Synonym>
                        <v8:item><v8:lang>ru</v8:lang><v8:content>Используется</v8:content></v8:item>
                    </Synonym>
                </Properties>
            </Attribute>
        </ChildObjects>
    </ExternalDataProcessor>
</MetaDataObject>"""

        # Modified: attribute deleted
        modified_content = """<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core">
    <ExternalDataProcessor>
        <ChildObjects>
        </ChildObjects>
    </ExternalDataProcessor>
</MetaDataObject>"""

        original_xml.write_text(original_content, encoding='utf-8')
        modified_xml.write_text(modified_content, encoding='utf-8')

        # Create handlers with reference to ReferencedAttr
        handlers_path = temp_workspace / "handlers.bsl"
        handlers_content = """
Процедура Test()
    Value = Объект.ReferencedAttr;  // Reference here!
КонецПроцедуры
"""
        handlers_path.write_text(handlers_content, encoding='utf-8-sig')

        # Run sync
        exit_code = run_sync(
            original_xml=str(original_xml),
            modified_xml=str(modified_xml),
            config=str(config_path),
            handlers=str(handlers_path),
            auto_apply=True,
            json_output=False,
            llm_mode=False
        )

        # Should still succeed but with warnings
        assert exit_code == 0

        # Verify attribute was NOT removed (reference check blocked it)
        updated_yaml = config_path.read_text(encoding='utf-8')
        assert "ReferencedAttr" in updated_yaml


class TestXMLExtraction:
    """Test XML data extraction for structural changes."""

    def test_extract_attribute_data(self, temp_workspace):
        """Test extraction of attribute data from XML."""
        # Create modified XML (matching real 1C structure)
        modified_xml = temp_workspace / "modified.xml"
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core" xmlns:xs="http://www.w3.org/2001/XMLSchema">
    <ExternalDataProcessor>
        <ChildObjects>
            <Attribute>
                <Properties>
                    <Name>TestAttr</Name>
                    <Synonym>
                        <v8:item><v8:lang>ru</v8:lang><v8:content>Тестовый атрибут</v8:content></v8:item>
                        <v8:item><v8:lang>uk</v8:lang><v8:content>Тестовий атрибут</v8:content></v8:item>
                    </Synonym>
                    <Type xmlns:d4p1="http://v8.1c.ru/8.1/data/core">
                        <d4p1:Type xmlns:d5p1="http://www.w3.org/2001/XMLSchema">d5p1:string</d4p1:Type>
                        <d4p1:StringQualifiers>
                            <d4p1:Length>0</d4p1:Length>
                        </d4p1:StringQualifiers>
                    </Type>
                </Properties>
            </Attribute>
        </ChildObjects>
    </ExternalDataProcessor>
</MetaDataObject>"""
        modified_xml.write_text(xml_content, encoding='utf-8')

        # Create SyncTool to test extraction
        config_path = temp_workspace / "config.yaml"
        config_path.write_text("processor:\n  name: Test\n  synonym_ru: Test\nattributes: []", encoding='utf-8')
        handlers_path = temp_workspace / "handlers.bsl"
        handlers_path.write_text("// test", encoding='utf-8-sig')

        tool = SyncTool(
            original_xml=str(modified_xml),
            modified_xml=str(modified_xml),
            config_path=str(config_path),
            handlers_path=str(handlers_path),
            auto_apply=True
        )

        # Test _parse_attribute_data directly (bypass XPath issues)
        # Parse XML and get Attribute element
        from lxml import etree as ET
        tree = ET.parse(str(modified_xml))
        # Find Attribute using simple tag search
        attr_elem = tree.find(".//{http://v8.1c.ru/8.3/MDClasses}Attribute")

        # Parse attribute data
        data = tool._parse_attribute_data(attr_elem)

        # Verify extracted data
        assert data['name'] == 'TestAttr'
        assert data['type'] == 'string'
        assert data['synonym_ru'] == 'Тестовый атрибут'
        assert data['synonym_uk'] == 'Тестовий атрибут'

    def test_extract_form_index_from_xpath(self, temp_workspace):
        """Test extraction of form index from xpath."""
        config_path = temp_workspace / "config.yaml"
        config_path.write_text("processor:\n  name: Test\nattributes: []", encoding='utf-8')
        handlers_path = temp_workspace / "handlers.bsl"
        handlers_path.write_text("// test", encoding='utf-8-sig')

        # Create minimal XML file
        dummy_xml = temp_workspace / "dummy.xml"
        dummy_xml.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses">
    <ExternalDataProcessor>
        <ChildObjects></ChildObjects>
    </ExternalDataProcessor>
</MetaDataObject>""", encoding='utf-8')

        tool = SyncTool(
            original_xml=str(dummy_xml),
            modified_xml=str(dummy_xml),
            config_path=str(config_path),
            handlers_path=str(handlers_path)
        )

        # Test various xpath patterns
        assert tool._extract_form_index_from_xpath("//Form[1]/Items/Item") == 0
        assert tool._extract_form_index_from_xpath("//Form[2]/Commands/Command") == 1
        assert tool._extract_form_index_from_xpath("//Form[3]/Items") == 2
        assert tool._extract_form_index_from_xpath("//Item[@name='Field']") == 0  # default
        assert tool._extract_form_index_from_xpath("") == 0  # default


class TestLLMMode_StructuralChanges:
    """Test LLM mode with structural changes."""

    def test_llm_mode_includes_structural_changes(self, temp_workspace):
        """Test that LLM mode JSON output includes structural changes."""
        # Create simple config
        config_path = temp_workspace / "config.yaml"
        config_path.write_text("processor:\n  name: Test\n  synonym_ru: Test\nattributes: []", encoding='utf-8')

        # Create XMLs with one new attribute
        original_xml = temp_workspace / "original.xml"
        modified_xml = temp_workspace / "modified.xml"

        original_content = """<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core">
    <ExternalDataProcessor>
        <ChildObjects>
        </ChildObjects>
    </ExternalDataProcessor>
</MetaDataObject>"""

        modified_content = """<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core">
    <ExternalDataProcessor>
        <ChildObjects>
            <Attribute>
                <Properties>
                    <Name>NewAttr</Name>
                    <Synonym>
                        <v8:item><v8:lang>ru</v8:lang><v8:content>Новый</v8:content></v8:item>
                    </Synonym>
                    <Type>
                        <v8:Type>xs:string</v8:Type>
                    </Type>
                </Properties>
            </Attribute>
        </ChildObjects>
    </ExternalDataProcessor>
</MetaDataObject>"""

        original_xml.write_text(original_content, encoding='utf-8')
        modified_xml.write_text(modified_content, encoding='utf-8')

        handlers_path = temp_workspace / "handlers.bsl"
        handlers_path.write_text("// test", encoding='utf-8-sig')

        # Capture stdout
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()

        try:
            run_sync(
                original_xml=str(original_xml),
                modified_xml=str(modified_xml),
                config=str(config_path),
                handlers=str(handlers_path),
                auto_apply=True,
                json_output=True,
                llm_mode=True
            )
        finally:
            sys.stdout = old_stdout

        output = captured_output.getvalue()

        # Parse JSON
        import json
        json_output = json.loads(output.strip())

        # Verify structural_changes in output
        assert 'structural_changes' in json_output.get('details', {})
        structural = json_output['details']['structural_changes']
        assert len(structural) == 1
        assert structural[0]['operation'] == 'add'
        assert structural[0]['element_type'] == 'attribute'
        assert structural[0]['element_name'] == 'NewAttr'


class TestConflictResolution:
    """Test conflict resolution UI (Phase 2.4)."""

    def test_conflict_resolution_apply_all(self, temp_workspace, monkeypatch):
        """Test conflict resolution with 'apply all' option."""
        # Create config
        config_path = temp_workspace / "config.yaml"
        config_content = """
processor:
  name: Test
  synonym_ru: Тест

attributes:
  - name: Attr1
    type: string
    synonym_ru: Атрибут 1
"""
        config_path.write_text(config_content, encoding='utf-8')

        # Create XMLs with changes
        original_xml = temp_workspace / "original.xml"
        modified_xml = temp_workspace / "modified.xml"

        original_content = """<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core">
    <ExternalDataProcessor>
        <ChildObjects>
            <Attribute>
                <Properties>
                    <Name>Attr1</Name>
                    <Synonym>
                        <v8:item><v8:lang>ru</v8:lang><v8:content>Атрибут 1</v8:content></v8:item>
                    </Synonym>
                </Properties>
            </Attribute>
        </ChildObjects>
    </ExternalDataProcessor>
</MetaDataObject>"""

        modified_content = """<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core">
    <ExternalDataProcessor>
        <ChildObjects>
            <Attribute>
                <Properties>
                    <Name>Attr1</Name>
                    <Synonym>
                        <v8:item><v8:lang>ru</v8:lang><v8:content>Изменённый атрибут</v8:content></v8:item>
                    </Synonym>
                </Properties>
            </Attribute>
        </ChildObjects>
    </ExternalDataProcessor>
</MetaDataObject>"""

        original_xml.write_text(original_content, encoding='utf-8')
        modified_xml.write_text(modified_content, encoding='utf-8')

        handlers_path = temp_workspace / "handlers.bsl"
        handlers_path.write_text("// test", encoding='utf-8-sig')

        # Mock user input to select 'apply all' (a)
        inputs = iter(['a'])
        monkeypatch.setattr('builtins.input', lambda _: next(inputs))

        # Run with conflict resolution UI
        tool = SyncTool(
            original_xml=str(original_xml),
            modified_xml=str(modified_xml),
            config_path=str(config_path),
            handlers_path=str(handlers_path),
            auto_apply=False
        )

        result = tool.run()

        # Verify changes were applied
        assert result['status'] == 'success'
        assert result['changes_applied']['yaml_updates'] >= 1

    def test_conflict_resolution_skip_all(self, temp_workspace, monkeypatch):
        """Test conflict resolution with 'skip all' option."""
        # Create config
        config_path = temp_workspace / "config.yaml"
        config_content = """
processor:
  name: Test
  synonym_ru: Тест

attributes:
  - name: Attr1
    type: string
    synonym_ru: Атрибут 1
"""
        config_path.write_text(config_content, encoding='utf-8')

        # Create XMLs with changes
        original_xml = temp_workspace / "original.xml"
        modified_xml = temp_workspace / "modified.xml"

        original_content = """<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core">
    <ExternalDataProcessor>
        <ChildObjects>
            <Attribute>
                <Properties>
                    <Name>Attr1</Name>
                    <Synonym>
                        <v8:item><v8:lang>ru</v8:lang><v8:content>Атрибут 1</v8:content></v8:item>
                    </Synonym>
                </Properties>
            </Attribute>
        </ChildObjects>
    </ExternalDataProcessor>
</MetaDataObject>"""

        modified_content = """<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core">
    <ExternalDataProcessor>
        <ChildObjects>
            <Attribute>
                <Properties>
                    <Name>Attr1</Name>
                    <Synonym>
                        <v8:item><v8:lang>ru</v8:lang><v8:content>Изменённый атрибут</v8:content></v8:item>
                    </Synonym>
                </Properties>
            </Attribute>
        </ChildObjects>
    </ExternalDataProcessor>
</MetaDataObject>"""

        original_xml.write_text(original_content, encoding='utf-8')
        modified_xml.write_text(modified_content, encoding='utf-8')

        handlers_path = temp_workspace / "handlers.bsl"
        handlers_path.write_text("// test", encoding='utf-8-sig')

        # Mock user input to select 'skip all' (s)
        inputs = iter(['s'])
        monkeypatch.setattr('builtins.input', lambda _: next(inputs))

        # Run with conflict resolution UI
        tool = SyncTool(
            original_xml=str(original_xml),
            modified_xml=str(modified_xml),
            config_path=str(config_path),
            handlers_path=str(handlers_path),
            auto_apply=False
        )

        result = tool.run()

        # Verify no changes were applied
        assert result['status'] == 'cancelled'

    def test_conflict_resolution_selective(self, temp_workspace, monkeypatch):
        """Test conflict resolution with selective approval."""
        # Create config with two attributes
        config_path = temp_workspace / "config.yaml"
        config_content = """
processor:
  name: Test
  synonym_ru: Тест

attributes:
  - name: Attr1
    type: string
    synonym_ru: Атрибут 1
  - name: Attr2
    type: string
    synonym_ru: Атрибут 2
"""
        config_path.write_text(config_content, encoding='utf-8')

        # Create XMLs with changes to both attributes
        original_xml = temp_workspace / "original.xml"
        modified_xml = temp_workspace / "modified.xml"

        original_content = """<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core">
    <ExternalDataProcessor>
        <ChildObjects>
            <Attribute>
                <Properties>
                    <Name>Attr1</Name>
                    <Synonym>
                        <v8:item><v8:lang>ru</v8:lang><v8:content>Атрибут 1</v8:content></v8:item>
                    </Synonym>
                </Properties>
            </Attribute>
            <Attribute>
                <Properties>
                    <Name>Attr2</Name>
                    <Synonym>
                        <v8:item><v8:lang>ru</v8:lang><v8:content>Атрибут 2</v8:content></v8:item>
                    </Synonym>
                </Properties>
            </Attribute>
        </ChildObjects>
    </ExternalDataProcessor>
</MetaDataObject>"""

        modified_content = """<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core">
    <ExternalDataProcessor>
        <ChildObjects>
            <Attribute>
                <Properties>
                    <Name>Attr1</Name>
                    <Synonym>
                        <v8:item><v8:lang>ru</v8:lang><v8:content>Изменённый 1</v8:content></v8:item>
                    </Synonym>
                </Properties>
            </Attribute>
            <Attribute>
                <Properties>
                    <Name>Attr2</Name>
                    <Synonym>
                        <v8:item><v8:lang>ru</v8:lang><v8:content>Изменённый 2</v8:content></v8:item>
                    </Synonym>
                </Properties>
            </Attribute>
        </ChildObjects>
    </ExternalDataProcessor>
</MetaDataObject>"""

        original_xml.write_text(original_content, encoding='utf-8')
        modified_xml.write_text(modified_content, encoding='utf-8')

        handlers_path = temp_workspace / "handlers.bsl"
        handlers_path.write_text("// test", encoding='utf-8-sig')

        # Mock user input: approve first change (y), skip second (n)
        inputs = iter(['y', 'n'])
        monkeypatch.setattr('builtins.input', lambda _: next(inputs))

        # Run with conflict resolution UI
        tool = SyncTool(
            original_xml=str(original_xml),
            modified_xml=str(modified_xml),
            config_path=str(config_path),
            handlers_path=str(handlers_path),
            auto_apply=False
        )

        result = tool.run()

        # Verify one change was applied
        assert result['status'] == 'success'
        assert result['changes_applied']['yaml_updates'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
