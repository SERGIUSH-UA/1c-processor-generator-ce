"""
Tests for BSP print form handler routing (v2.78.0+)

Regression cover for the "silent handler loss" bug: a print handler written in
handlers.bsl outside the #Область МодульОбъекта region was loaded, reported as
loaded, then dropped - the generated ObjectModule kept a TODO stub and the
processor printed an empty document while the CLI said "✨ Готово!".
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
models_module = importlib.import_module("1c_processor_generator.models")
yaml_parser_module = importlib.import_module("1c_processor_generator.yaml_parser")
validators_module = importlib.import_module("1c_processor_generator.validators")
bsp_module = importlib.import_module("1c_processor_generator.pro.bsp_generator_impl")

Processor = models_module.Processor
BSPConfig = models_module.BSPConfig
BSPCommand = models_module.BSPCommand
HandlerValidator = validators_module.HandlerValidator
parse_yaml_config = yaml_parser_module.parse_yaml_config
generate_bsp_object_module = bsp_module.generate_bsp_object_module
BSPGenerator = bsp_module.BSPGenerator


CONFIG_YAML = """
languages: [ru]

processor:
  name: ТестоваяПечать

bsp:
  type: print_form
  version: "1.0"
  targets:
    - Документ.СчетНаОплатуПокупателю
  commands:
    - id: Счет
      title: "Счет"
      usage: server_method
      modifier: ПечатьMXL
"""

HANDLER_BODY = """
	ТабличныйДокумент = Новый ТабличныйДокумент;
	ТабличныйДокумент.Область(1, 1).Текст = "Привет";
	Возврат ТабличныйДокумент;
"""


def _write(tmp_path: Path, config: str, handlers: str):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config, encoding="utf-8")
    handlers_path = tmp_path / "handlers.bsl"
    handlers_path.write_text(handlers, encoding="utf-8")
    return config_path, handlers_path


class TestStubGeneration:
    """BSPGenerator decides between user code and a TODO stub"""

    def _config(self, *commands):
        return BSPConfig(type="PrintForm", targets=["Документ.Тест"], commands=list(commands))

    def test_stub_generated_without_user_handlers(self):
        warnings = []
        code = generate_bsp_object_module(
            self._config(BSPCommand(id="Счет", title_ru="Счет")),
            user_handlers=None,
            warnings_out=warnings,
        )

        assert "TODO: Реализуйте" in code
        assert len(warnings) == 1
        assert "Счет" in warnings[0]

    def test_user_handler_replaces_stub(self):
        warnings = []
        user_code = f"Функция ПечатьСчет(МассивОбъектов, ОбъектыПечати)\n{HANDLER_BODY}\nКонецФункции"

        code = generate_bsp_object_module(
            self._config(BSPCommand(id="Счет", title_ru="Счет")),
            user_handlers=user_code,
            warnings_out=warnings,
        )

        assert "TODO: Реализуйте" not in code
        assert warnings == []
        assert 'ТабличныйДокумент.Область(1, 1).Текст = "Привет"' in code

    def test_similar_command_names_do_not_collide(self):
        """'ПечатьСчет' must not be considered present just because 'ПечатьСчетФактура' is"""
        warnings = []
        user_code = f"Функция ПечатьСчетФактура(МассивОбъектов, ОбъектыПечати)\n{HANDLER_BODY}\nКонецФункции"

        code = generate_bsp_object_module(
            self._config(
                BSPCommand(id="Счет", title_ru="Счет"),
                BSPCommand(id="СчетФактура", title_ru="Счет-фактура"),
            ),
            user_handlers=user_code,
            warnings_out=warnings,
        )

        # Счет has no implementation -> stub + warning; СчетФактура has one
        assert "Функция ПечатьСчет(МассивОбъектов, ОбъектыПечати)" in code
        assert len(warnings) == 1
        assert "'Счет'" in warnings[0]

    def test_mention_in_comment_does_not_suppress_stub(self):
        """A comment mentioning the name is not an implementation"""
        warnings = []
        code = generate_bsp_object_module(
            self._config(BSPCommand(id="Счет", title_ru="Счет")),
            user_handlers="// ПечатьСчет - буде реалізовано пізніше",
            warnings_out=warnings,
        )

        assert "TODO: Реализуйте" in code
        assert len(warnings) == 1

    def test_custom_handler_name_is_honored(self):
        """`handler:` in YAML was documented but ignored before v2.78.0"""
        warnings = []
        user_code = f"Функция МояФункцияПечати(МассивОбъектов, ОбъектыПечати)\n{HANDLER_BODY}\nКонецФункции"

        code = generate_bsp_object_module(
            self._config(BSPCommand(id="Счет", title_ru="Счет", handler="МояФункцияПечати")),
            user_handlers=user_code,
            warnings_out=warnings,
        )

        assert warnings == []
        assert "TODO: Реализуйте" not in code
        assert "ПечатныйДокумент = МояФункцияПечати(МассивОбъектов, ОбъектыПечати);" in code


class TestHandlerRouting:
    """End-to-end: handlers.bsl -> Processor.object_module_from_handlers"""

    def test_handler_inside_region_is_routed(self, tmp_path):
        handlers = (
            "#Область МодульОбъекта\n\n"
            f"Функция ПечатьСчет(МассивОбъектов, ОбъектыПечати)\n{HANDLER_BODY}\nКонецФункции\n\n"
            "#КонецОбласти\n"
        )
        config_path, handlers_path = _write(tmp_path, CONFIG_YAML, handlers)

        processor = parse_yaml_config(config_path, handlers_file=handlers_path)

        assert processor is not None
        assert processor.object_module_from_handlers is not None
        assert "ПечатьСчет" in processor.object_module_from_handlers
        assert processor.generation_warnings == []

    def test_handler_outside_region_warns(self, tmp_path):
        """The reported bug: code loaded, silently dropped, stub kept"""
        handlers = f"Функция ПечатьСчет(МассивОбъектов, ОбъектыПечати)\n{HANDLER_BODY}\nКонецФункции\n"
        config_path, handlers_path = _write(tmp_path, CONFIG_YAML, handlers)

        processor = parse_yaml_config(config_path, handlers_file=handlers_path)

        assert processor is not None
        assert processor.object_module_from_handlers is None
        assert any("#Область МодульОбъекта" in w for w in processor.generation_warnings)

    def test_missing_handler_warns(self, tmp_path):
        config_path, handlers_path = _write(tmp_path, CONFIG_YAML, "// nothing here\n")

        processor = parse_yaml_config(config_path, handlers_file=handlers_path)

        assert processor is not None
        assert any("ПечатьСчет" in w for w in processor.generation_warnings)


class TestDirectiveValidation:
    """Compilation directives are a form module concept - not for ObjectModule"""

    def test_no_directive_required_without_forms(self):
        processor = Processor(name="Тест")
        processor.bsp_config = BSPConfig(
            type="PrintForm",
            targets=["Документ.Тест"],
            commands=[BSPCommand(id="Счет", title_ru="Счет")],
        )

        validator = HandlerValidator(
            processor=processor,
            loaded_handlers={
                "ПечатьСчет": f"Функция ПечатьСчет(МассивОбъектов, ОбъектыПечати)\n{HANDLER_BODY}\nКонецФункции"
            },
        )
        errors, _ = validator.validate_handler_signatures()

        assert not any("директиви компіляції" in e for e in errors)
