"""
Integration тести для bsl_injector.py
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
bsl_injector_module = importlib.import_module("1c_processor_generator.bsl_injector")
models_module = importlib.import_module("1c_processor_generator.models")

BSLInjector = bsl_injector_module.BSLInjector
Processor = models_module.Processor


class TestBSLInjector:
    """Тести для BSLInjector"""

    def test_load_handler(self, fixtures_dir):
        """Завантаження BSL файлу"""
        handlers_dir = fixtures_dir / "handlers"
        injector = BSLInjector(handlers_dir)

        code = injector.load_handler("ПриОткрытии")
        assert code is not None
        assert "Форма открыта" in code

    def test_load_nonexistent_handler(self, fixtures_dir):
        """Завантаження неіснуючого BSL файлу"""
        handlers_dir = fixtures_dir / "handlers"
        injector = BSLInjector(handlers_dir)

        code = injector.load_handler("НеіснуючийОбробник")
        assert code is None

    def test_has_bsl_signature_with_directive(self, fixtures_dir):
        """Перевірка сигнатури - файл з директивою &"""
        handlers_dir = fixtures_dir / "handlers"
        injector = BSLInjector(handlers_dir)

        code = injector.load_handler("ПолнаяСигнатура")
        assert injector.has_bsl_signature(code)

    def test_has_bsl_signature_without_directive(self, fixtures_dir):
        """Перевірка сигнатури - файл без директиви"""
        handlers_dir = fixtures_dir / "handlers"
        injector = BSLInjector(handlers_dir)

        code = injector.load_handler("ПриОткрытии")
        assert not injector.has_bsl_signature(code)

    def test_has_bsl_signature_with_procedure(self):
        """Перевірка сигнатури - код починається з Процедура"""
        injector = BSLInjector()
        code = "Процедура ИмяПроцедуры()\nКонецПроцедуры"
        assert injector.has_bsl_signature(code)

    def test_has_bsl_signature_with_function(self):
        """Перевірка сигнатури - код починається з Функция"""
        injector = BSLInjector()
        code = "Функция ИмяФункции()\nКонецФункции"
        assert injector.has_bsl_signature(code)

    def test_wrap_handler_code_without_signature(self, fixtures_dir):
        """Обгортка коду без сигнатури"""
        handlers_dir = fixtures_dir / "handlers"
        injector = BSLInjector(handlers_dir)

        code = injector.load_handler("ПриОткрытии")
        # v2.53.0+: FORM_EVENT_SIGNATURES moved to PRO module
        gen_ctx_module = importlib.import_module("1c_processor_generator.pro.generation_context")
        ctx = gen_ctx_module.get_generation_context()
        FORM_EVENT_SIGNATURES = ctx["form_event_signatures"]

        wrapped = injector.wrap_handler_code(
            code,
            "ПриОткрытии",
            FORM_EVENT_SIGNATURES["OnOpen"]
        )

        assert "&НаКлиенте" in wrapped or "&НаСервере" in wrapped
        assert "Процедура" in wrapped
        assert "КонецПроцедуры" in wrapped

    def test_wrap_handler_code_with_signature(self, fixtures_dir):
        """Обгортка коду з сигнатурою - має повернутися без змін"""
        handlers_dir = fixtures_dir / "handlers"
        injector = BSLInjector(handlers_dir)

        code = injector.load_handler("ПолнаяСигнатура")
        # v2.53.0+: FORM_EVENT_SIGNATURES moved to PRO module
        gen_ctx_module = importlib.import_module("1c_processor_generator.pro.generation_context")
        ctx = gen_ctx_module.get_generation_context()
        FORM_EVENT_SIGNATURES = ctx["form_event_signatures"]

        wrapped = injector.wrap_handler_code(
            code,
            "ПолнаяСигнатура",
            FORM_EVENT_SIGNATURES["OnOpen"]
        )

        # Має повернутися без змін
        assert wrapped == code

    def test_inject_form_event_handlers(self, fixtures_dir, simple_processor):
        """Інжектування обробників подій форми"""
        handlers_dir = fixtures_dir / "handlers"
        injector = BSLInjector(handlers_dir)

        # Отримуємо форму і додаємо подію
        form = simple_processor.get_default_form()
        form.events["OnOpen"] = "ПриОткрытии"

        # Використовуємо новий API - inject_form_handlers для однієї форми
        injector.inject_form_handlers(form, handlers_dir)

        assert hasattr(form, "events_bsl")
        assert "ПриОткрытии" in form.events_bsl

    def test_inject_command_handlers(self, fixtures_dir, simple_processor):
        """Інжектування обробників команд"""
        handlers_dir = fixtures_dir / "handlers"
        injector = BSLInjector(handlers_dir)

        # Використовуємо новий API - inject_forms_handlers для всіх форм
        injector.inject_forms_handlers(simple_processor)

        # Перевіряємо що команда має BSL код
        form = simple_processor.get_default_form()
        cmd = form.commands[0]
        assert hasattr(cmd, "bsl_code")
        assert cmd.bsl_code is not None

    def test_inject_command_with_server_handler(self, fixtures_dir):
        """Інжектування команди з серверною частиною"""
        import importlib
        models_module = importlib.import_module("1c_processor_generator.models")
        Command = models_module.Command

        handlers_dir = fixtures_dir / "handlers"
        injector = BSLInjector(handlers_dir)

        processor = Processor(name="Test")
        form = processor.add_form(name="Форма", default=True)
        cmd = Command(
            name="ЗагрузитьДанные",
            title_ru="Загрузить данные",
            title_uk="Завантажити дані",
            action="ЗагрузитьДанные",
        )
        form.commands.append(cmd)

        # Використовуємо новий API - inject_form_handlers для однієї форми
        injector.inject_form_handlers(form, handlers_dir)

        # Має бути і клієнтський, і серверний код
        assert hasattr(cmd, "bsl_code")
        assert "ЗагрузитьДанные" in cmd.bsl_code
        assert "ЗагрузитьДанныеНаСервере" in cmd.bsl_code

    def test_inject_all_handlers(self, fixtures_dir, simple_processor):
        """Інжектування всіх обробників"""
        handlers_dir = fixtures_dir / "handlers"
        injector = BSLInjector(handlers_dir)

        form = simple_processor.get_default_form()
        form.events["OnOpen"] = "ПриОткрытии"
        injector.inject_all_handlers(simple_processor)

        # Перевіряємо що всі обробники завантажені
        assert hasattr(form, "events_bsl")
        assert len(injector._loaded_handlers) > 0


class TestBSLCodeWrapping:
    """Тести обгортки BSL коду"""

    def test_wrap_command_handler_client(self):
        """Обгортка клієнтського обробника команди"""
        injector = BSLInjector()
        code = 'Сообщить("Test");'

        wrapped = injector.wrap_command_handler(code, "TestCommand", is_client=True)

        assert "&НаКлиенте" in wrapped
        assert "Процедура TestCommand(Команда)" in wrapped
        assert "КонецПроцедуры" in wrapped

    def test_wrap_command_handler_server(self):
        """Обгортка серверного обробника команди"""
        injector = BSLInjector()
        code = 'Сообщить("Test");'

        wrapped = injector.wrap_command_handler(code, "TestCommand", is_client=False)

        assert "&НаСервере" in wrapped
        assert "Процедура TestCommand(Команда)" in wrapped

    def test_wrap_server_call_handler(self, fixtures_dir):
        """Обгортка клієнт-серверної пари"""
        handlers_dir = fixtures_dir / "handlers"
        injector = BSLInjector(handlers_dir)

        client_code = injector.load_handler("ЗагрузитьДанные")
        server_code = injector.load_handler("ЗагрузитьДанныеНаСервере")

        wrapped = injector.wrap_server_call_handler(
            client_code=client_code,
            server_code=server_code,
            client_handler="ЗагрузитьДанные",
            server_handler="ЗагрузитьДанныеНаСервере",
            params="Команда",
        )

        # Має містити обидві процедури
        assert "ЗагрузитьДанные" in wrapped
        assert "ЗагрузитьДанныеНаСервере" in wrapped
        assert "&НаКлиенте" in wrapped
        assert "&НаСервере" in wrapped

    def test_indent_code(self):
        """Тест відступів коду"""
        injector = BSLInjector()
        code = "Line1\nLine2\nLine3"

        indented = injector._indent_code(code, "\t")

        lines = indented.split("\n")
        assert all(line.startswith("\t") or line == "" for line in lines)


class TestBSLInjectorWithoutHandlers:
    """Тести BSLInjector без директорії handlers"""

    def test_injector_without_handlers_dir(self):
        """BSLInjector без директорії handlers"""
        injector = BSLInjector()
        assert injector.handlers_dir is None

    def test_load_handler_without_dir(self):
        """Завантаження handler без директорії"""
        injector = BSLInjector()
        code = injector.load_handler("Test")
        assert code is None

    def test_inject_with_no_handlers_dir(self, simple_processor):
        """Інжектування без директорії handlers"""
        injector = BSLInjector()

        form = simple_processor.get_default_form()
        form.events["OnOpen"] = "ПриОткрытии"

        # Використовуємо новий API - inject_all_handlers
        injector.inject_all_handlers(simple_processor)

        # Не має створюватися events_bsl якщо немає handlers


class TestBSLParserEdgeCases:
    """
    Тести для edge cases BSL парсера (v2.38.0+)

    Покриває:
    - Директиви препроцесора (#Если, #КонецЕсли)
    - Вкладені коментарі
    - Рядки з "Процедура" всередині
    """

    def test_has_signature_with_preprocessor_directive(self):
        """Код з директивою препроцесора перед &НаКлиенте"""
        injector = BSLInjector()

        # Код з #Если перед процедурою - але починається з &
        code = """&НаКлиенте
#Если Клиент Тогда
Процедура ТестПрепроцесор()
    // Тіло
КонецПроцедуры
#КонецЕсли"""
        assert injector.has_bsl_signature(code)

    def test_has_signature_preprocessor_at_start(self):
        """Код що починається з #Если (не має сигнатури)"""
        injector = BSLInjector()

        # Код починається з #Если - не має сигнатури процедури
        code = """#Если Сервер Тогда
    Сообщить("Привет");
#КонецЕсли"""
        assert not injector.has_bsl_signature(code)

    def test_has_signature_with_leading_comment(self):
        """Код з коментарем на початку (не має сигнатури)"""
        injector = BSLInjector()

        code = """// Це коментар
Процедура ТестКоментар()
КонецПроцедуры"""
        # Починається з коментаря, не з сигнатури
        assert not injector.has_bsl_signature(code)

    def test_has_signature_procedure_in_string(self):
        """Рядок 'Процедура' всередині тексту - не є сигнатурою"""
        injector = BSLInjector()

        # "Процедура" у рядковому літералі
        code = 'Сообщить("Процедура виконана успішно");'
        assert not injector.has_bsl_signature(code)

    def test_has_signature_procedure_in_comment(self):
        """'Процедура' в коментарі - не є сигнатурою"""
        injector = BSLInjector()

        code = """// Процедура для тестування
Сообщить("Test");"""
        assert not injector.has_bsl_signature(code)

    def test_has_signature_async_procedure(self):
        """Асинхронна процедура (Асинх)"""
        injector = BSLInjector()

        code = """Асинх Процедура АсинхроннаяОперация()
    // async code
КонецПроцедуры"""
        assert injector.has_bsl_signature(code)

    def test_has_signature_async_english(self):
        """Async procedure (English)"""
        injector = BSLInjector()

        code = """Async Procedure AsyncOperation()
    // async code
EndProcedure"""
        assert injector.has_bsl_signature(code)

    def test_has_signature_with_whitespace(self):
        """Код з пробілами/табами на початку"""
        injector = BSLInjector()

        # Пробіли на початку - strip() має їх прибрати
        code = """   &НаСервере
Процедура Тест()
КонецПроцедуры"""
        assert injector.has_bsl_signature(code)

    def test_has_signature_empty_code(self):
        """Порожній код"""
        injector = BSLInjector()
        assert not injector.has_bsl_signature("")
        assert not injector.has_bsl_signature("   ")
        assert not injector.has_bsl_signature("\n\n")

    def test_has_signature_function_ru(self):
        """Функция (російською)"""
        injector = BSLInjector()

        code = """Функция ОтриматиЗначення()
    Возврат 42;
КонецФункции"""
        assert injector.has_bsl_signature(code)

    def test_has_signature_function_en(self):
        """Function (English)"""
        injector = BSLInjector()

        code = """Function GetValue()
    Return 42;
EndFunction"""
        assert injector.has_bsl_signature(code)

    def test_multiline_directive(self):
        """Кілька директив перед процедурою"""
        injector = BSLInjector()

        code = """&НаКлиенте
&БезБлокировкиДанных
Процедура МультиДиректива()
КонецПроцедуры"""
        assert injector.has_bsl_signature(code)
