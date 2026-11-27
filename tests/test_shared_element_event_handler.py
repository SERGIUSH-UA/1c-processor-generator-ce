"""A form can bind several controls to one BSL handler."""
import importlib
import xml.etree.ElementTree as ET

import pytest


parse_yaml_config = importlib.import_module(
    "1c_processor_generator.yaml_parser"
).parse_yaml_config
ProcessorGenerator = importlib.import_module(
    "1c_processor_generator.generator"
).ProcessorGenerator


@pytest.mark.parametrize("with_handlers_file", [False, True])
def test_shared_on_change_handler_is_emitted_once(tmp_path, with_handlers_file):
    config = tmp_path / "processor.yaml"
    config.write_text(
        """languages: [ru]
processor:
  name: SharedHandler
  synonym_ru: Общий обработчик
attributes:
  - {name: First, type: string}
  - {name: Second, type: string}
  - {name: Third, type: string}
forms:
  - name: MainForm
    default: true
    elements:
      - type: InputField
        name: FirstField
        attribute: First
        events: {OnChange: SharedChanged}
      - type: InputField
        name: SecondField
        attribute: Second
        events: {OnChange: SharedChanged}
      - type: UsualGroup
        name: Fields
        child_items:
          - type: InputField
            name: ThirdField
            attribute: Third
            events: {OnChange: SharedChanged}
""",
        encoding="utf-8",
    )
    handlers_file = None
    if with_handlers_file:
        handlers_file = tmp_path / "handlers.bsl"
        handlers_file.write_text(
            """&НаКлиенте
Процедура SharedChanged(Элемент)
	SharedChangedНаСервере();
КонецПроцедуры // Конец клиентского обработчика

&НаСервере
Процедура SharedChangedНаСервере()
	Объект.First = "Changed";
КонецПроцедуры // Конец серверного обработчика
""",
            encoding="utf-8",
        )

    processor = parse_yaml_config(config, handlers_file=handlers_file)
    assert processor is not None
    output = ProcessorGenerator(processor).generate(str(tmp_path / "output"))
    assert output is not None
    form_dir = output / "SharedHandler" / "Forms" / "MainForm" / "Ext"
    form = ET.parse(form_dir / "Form.xml")
    for name in ("FirstField", "SecondField", "ThirdField"):
        handler = form.find(f".//{{*}}InputField[@name='{name}']/{{*}}Events/{{*}}Event[@name='OnChange']")
        assert handler is not None
        assert handler.text == "SharedChanged"

    module = (form_dir / "Form" / "Module.bsl").read_text(encoding="utf-8-sig")
    assert module.count("Процедура SharedChanged(") == 1
    assert module.count("Процедура SharedChangedНаСервере(") == 1
    if with_handlers_file:
        assert 'Объект.First = "Changed";' in module
        assert "КонецПроцедуры // Конец клиентского обработчика" in module
        assert "КонецПроцедуры // Конец серверного обработчика" in module


def test_splitter_preserves_inline_end_comments_on_methods(tmp_path):
    splitter = importlib.import_module("1c_processor_generator.bsl_splitter").BSLSplitter
    source = tmp_path / "handlers.bsl"
    source.write_text(
        """&НаКлиенте
Процедура First()
КонецПроцедуры // }

&НаСервере
Функция Second()
	Возврат Истина;
КонецФункции // }

&AtClient
Procedure Third()
EndProcedure
""",
        encoding="utf-8",
    )
    procedures = splitter(source).extract_procedures()
    assert list(procedures) == ["First", "Second", "Third"]
    assert procedures["First"].endswith("КонецПроцедуры // }")
    assert procedures["Second"].endswith("КонецФункции // }")
    assert procedures["Third"].endswith("EndProcedure")
