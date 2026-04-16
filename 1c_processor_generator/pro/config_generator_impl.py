"""
Генератор Configuration.xml з мінімальними метаданими для EPF компіляції
"""

from pathlib import Path
from typing import Dict, List
import logging
from jinja2 import Environment, FileSystemLoader, BaseLoader

try:
    # When running as compiled .pyd
    from utils import generate_uuid
    from xml_converter_impl import XMLConverter
    from _protected import get_embedded_template
except ImportError:
    # When running as part of package
    from .utils import generate_uuid
    from .xml_converter_impl import XMLConverter
    from .._protected import get_embedded_template

# v2.64.2: Fix for DEFAULT_COMPATIBILITY_MODE import in compiled .pyd
# v2.64.3: Added DEFAULT_XML_FORMAT_VERSION import
# The constants module is in parent package, not in pro/ directory
# Note: Package name starts with digit, so we need importlib for compiled .pyd
try:
    # Development mode - relative import works
    from ..constants import DEFAULT_COMPATIBILITY_MODE, DEFAULT_XML_FORMAT_VERSION
except ImportError:
    try:
        # Compiled .pyd in installed package - use importlib
        # (can't use "from 1c_processor_generator..." - syntax error due to leading digit)
        import importlib
        _constants = importlib.import_module("1c_processor_generator.constants")
        DEFAULT_COMPATIBILITY_MODE = _constants.DEFAULT_COMPATIBILITY_MODE
        DEFAULT_XML_FORMAT_VERSION = _constants.DEFAULT_XML_FORMAT_VERSION
    except ImportError:
        # Fallback - hardcoded values (should rarely happen)
        DEFAULT_COMPATIBILITY_MODE = "Version8_3_15"
        DEFAULT_XML_FORMAT_VERSION = "2.9"  # Must match DEFAULT_COMPATIBILITY_MODE

logger = logging.getLogger(__name__)


class _EmbeddedTemplateLoader(BaseLoader):
    """
    v2.55.0+: Custom Jinja2 loader for embedded templates.
    Used by ConfigurationGenerator to load templates from _protected.pyd.
    """

    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        self._file_loader = FileSystemLoader(str(template_dir))

    def get_source(self, environment, template):
        # Try embedded templates first (release mode)
        content = get_embedded_template(template)
        if content is not None:
            return content, template, lambda: True

        # Fallback to file system (development mode)
        return self._file_loader.get_source(environment, template)


class ConfigurationData:
    """Дані для генерації однього елемента метаданих (Catalog/Document)"""
    def __init__(self, name: str, metadata_type: str, attributes: list = None):
        self.name = name
        self.type = metadata_type  # "Catalog" або "Document"
        self.uuid = generate_uuid()
        self.attributes = attributes or []  # List of StubAttribute for smart stubs
        self.generated_types = self._generate_types()

    def _generate_types(self) -> List[Dict[str, str]]:
        """
        Генерує 5 GeneratedType з UUID для Catalog або Document

        Формат: Object, Ref, Selection, List, Manager
        Кожен тип має TypeId та ValueId
        """
        categories = ["Object", "Ref", "Selection", "List", "Manager"]
        types = []

        for category in categories:
            types.append({
                "category": category,
                "type_id": generate_uuid(),
                "value_id": generate_uuid()
            })

        return types


class CommonPictureData:
    """Дані для генерації CommonPicture заглушки (простіший ніж ConfigurationData)"""
    def __init__(self, name: str):
        self.name = name
        self.uuid = generate_uuid()


class CommonModuleData:
    """v2.57.0+ Дані для генерації CommonModule заглушки (для BSP модулів)"""
    def __init__(self, name: str):
        self.name = name
        self.uuid = generate_uuid()


class ConfigurationGenerator:
    """Генератор Configuration.xml та метаданих"""

    def __init__(self, processor, requirements, installed_platform_version: str = None):
        """
        Ініціалізація генератора

        Args:
            processor: Processor об'єкт з models.py
            requirements: MetadataRequirements з metadata_analyzer.py
            installed_platform_version: v2.62.7+ Версія встановленої платформи 1C (наприклад "8.3.25.1394").
                                       Використовується для CompatibilityMode в Configuration.xml.
                                       Якщо не вказано - використовується processor.platform_version (fallback).
        """
        self.processor = processor
        self.requirements = requirements
        # v2.62.7: Версія платформи для CompatibilityMode
        # ВАЖЛИВО: Для Configuration.xml потрібна версія ВСТАНОВЛЕНОЇ платформи,
        # а не версія сумісності обробки з YAML
        self.installed_platform_version = installed_platform_version
        # v2.64.3: Обчислена версія XML формату (встановлюється в _generate_configuration_root)
        # Ініціалізуємо з YAML для backward compatibility, переписується в generate_configuration
        self.xml_format_version = processor.platform_version

        # UUID для Configuration
        self.configuration_uuid = generate_uuid()
        self.internal_object_ids = [generate_uuid() for _ in range(7)]

        # Генерація даних для кожного Catalog/Document/CommonPicture
        # з атрибутами для Smart Stub генерації
        self.catalogs_data = [
            ConfigurationData(
                name,
                "Catalog",
                attributes=requirements.get_stub_attributes("Catalog", name)
            )
            for name in sorted(requirements.catalogs)
        ]

        self.documents_data = [
            ConfigurationData(
                name,
                "Document",
                attributes=requirements.get_stub_attributes("Document", name)
            )
            for name in sorted(requirements.documents)
        ]

        self.common_pictures_data = [
            CommonPictureData(name)
            for name in sorted(requirements.common_pictures)
        ]

        # v2.57.0+ BSP Common Modules stubs
        self.common_modules_data = [
            CommonModuleData(name)
            for name in sorted(requirements.common_modules)
        ]

        # Jinja2 environment with embedded template support (v2.55.0+)
        templates_dir = Path(__file__).parent.parent / "templates"
        self.jinja_env = Environment(
            loader=_EmbeddedTemplateLoader(templates_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
        # Register XML escape filter (same as in generator.py)
        self.jinja_env.filters['x'] = self._xml_escape

        # XML converter
        self.xml_converter = XMLConverter()

    @staticmethod
    def _xml_escape(value):
        """Escape special characters for XML content"""
        if value is None:
            return ''
        s = str(value)
        s = s.replace('&', '&amp;')  # Must be first!
        s = s.replace('<', '&lt;')
        s = s.replace('>', '&gt;')
        return s

    def generate_configuration(
        self,
        output_dir: Path,
        processor_xml_dir: Path,
        include_processor: bool = True,
        processor_suffix: str = ""
    ) -> Path:
        """
        Генерує повну Configuration структуру

        Args:
            output_dir: Директорія для збереження Configuration
            processor_xml_dir: Директорія з згенерованим DataProcessor XML
            include_processor: Включити DataProcessor в Configuration (за замовчуванням True)
                              Якщо False - Configuration матиме тільки метадані (Catalogs/Documents)
            processor_suffix: Суфікс до імені DataProcessor в Configuration (наприклад, "_Validation")
                             Використовується щоб уникнути конфлікту з External processor

        Returns:
            Path до згенерованої Configuration директорії

        Структура:
        output_dir/
        ├── Configuration.xml
        ├── Languages/
        │   └── Русский.xml
        ├── Catalogs/
        │   ├── Catalog1.xml
        │   └── Catalog2.xml
        ├── Documents/
        │   ├── Document1.xml
        │   └── Document2.xml
        └── DataProcessors/  (опціонально, якщо include_processor=True)
            └── ProcessorName/
                └── (copied from processor_xml_dir)
        """
        config_dir = output_dir / "Configuration"
        config_dir.mkdir(parents=True, exist_ok=True)

        # 1. Генерація Configuration.xml
        self._generate_configuration_root(config_dir, include_processor=include_processor, processor_suffix=processor_suffix)

        # 2. Генерація Languages/Русский.xml
        self._generate_language(config_dir)

        # 3. Генерація Catalogs/*.xml
        self._generate_catalogs(config_dir)

        # 4. Генерація Documents/*.xml
        self._generate_documents(config_dir)

        # 5. Генерація CommonPictures/*.xml
        self._generate_common_pictures(config_dir)

        # 6. v2.57.0+ Генерація CommonModules/*.xml (для BSP)
        self._generate_common_modules(config_dir)

        # 7. Копіювання DataProcessor (опціонально)
        if include_processor:
            self._copy_data_processor(config_dir, processor_xml_dir, processor_suffix=processor_suffix)
        else:
            logger.warning(f"⚠️ Skipping DataProcessor copy (include_processor=False)")

        return config_dir

    def _get_compatibility_mode(self, platform_version: str) -> str:
        """
        v2.62.6+ Витягує CompatibilityMode з версії платформи.

        Args:
            platform_version: Версія платформи (наприклад "8.3.25.1394")

        Returns:
            Рядок CompatibilityMode (наприклад "Version8_3_25")

        Note:
            v2.64.1: Додано валідацію формату версії.
            Версія МУСИТЬ починатися з "8.3" (версія платформи 1C),
            а не бути версією формату XML (2.11, 2.18 тощо).
        """
        # v2.64.1: Валідація - версія мусить бути формату 8.3.X.X
        if not platform_version.startswith("8.3"):
            logger.warning(
                f"⚠️ Invalid platform version format '{platform_version}', "
                f"expected 8.3.X.X format. Using fallback {DEFAULT_COMPATIBILITY_MODE}"
            )
            return DEFAULT_COMPATIBILITY_MODE

        # Парсимо версію: "8.3.25.1394" -> "8", "3", "25", "1394"
        parts = platform_version.split(".")
        if len(parts) >= 3:
            major, minor, patch = parts[0], parts[1], parts[2]
            return f"Version{major}_{minor}_{patch}"
        else:
            # Fallback до мінімальної підтримуваної версії
            logger.warning(
                f"⚠️ Cannot parse platform version '{platform_version}', "
                f"using fallback {DEFAULT_COMPATIBILITY_MODE}"
            )
            return DEFAULT_COMPATIBILITY_MODE

    def _get_xml_format_version(self, platform_version: str) -> str:
        """
        v2.64.1: Визначає версію формату XML для версії платформи 1C.

        Офіційний маппінг з документації 1C (2.17.2. Версии формата выгрузки):
        - 8.3.15 → 2.9       - 8.3.20 → 2.13
        - 8.3.16 → 2.9.1     - 8.3.21 → 2.14
        - 8.3.17 → 2.10      - 8.3.22 → 2.15
        - 8.3.18 → 2.11      - 8.3.23 → 2.16
        - 8.3.19 → 2.12      - 8.3.24 → 2.17
                             - 8.3.25+ → 2.18

        Args:
            platform_version: Версія платформи (наприклад "8.3.23.1688")

        Returns:
            Версія формату XML (наприклад "2.16")
        """
        # Офіційний маппінг версій (з документації 1C: 2.17.2. Версии формата выгрузки)
        VERSION_MAP = {
            # 8.5.x (нова гілка)
            # 8.5.1, 8.5.2, 8.5.3 → 2.21 (обробляється окремо)
            # 8.3.x
            27: "2.20",
            26: "2.19",
            25: "2.18",
            24: "2.17",
            23: "2.16",
            22: "2.15",
            21: "2.14",
            20: "2.13",
            19: "2.12",
            18: "2.11",
            17: "2.10",
            16: "2.9.1",
            15: "2.9",
        }

        # Парсимо версію (8.3.XX.YYYY або 8.5.X.YYYY)
        parts = platform_version.split(".")
        if len(parts) >= 3:
            try:
                major = int(parts[0])
                minor = int(parts[1])
                patch = int(parts[2])

                # Гілка 8.5.x → формат 2.21
                if major == 8 and minor == 5:
                    return "2.21"

                # Гілка 8.3.x
                if major == 8 and minor == 3:
                    # Точний маппінг
                    if patch in VERSION_MAP:
                        return VERSION_MAP[patch]
                    # Для новіших версій використовуємо найновіший відомий формат 8.3.x
                    elif patch > 27:
                        return "2.20"
                    # Для старіших версій використовуємо найстаріший відомий формат
                    else:
                        return "2.9"
            except ValueError:
                pass

        # Fallback - безпечна стара версія
        return "2.11"

    def _generate_configuration_root(self, config_dir: Path, include_processor: bool = True, processor_suffix: str = "") -> None:
        """Генерує Configuration.xml"""
        template = self.jinja_env.get_template("configuration_root.xml.j2")

        # Дані для темплейту
        processor_name_with_suffix = f"{self.processor.name}{processor_suffix}" if include_processor else None

        # v2.64.1: Виправлено fallback логіку
        # КРИТИЧНО: processor.platform_version - це версія формату XML (2.11, 2.18),
        # а НЕ версія платформи 1C (8.3.25.1394)! Використовувати її як fallback - ПОМИЛКА!
        if self.installed_platform_version:
            compatibility_mode = self._get_compatibility_mode(self.installed_platform_version)
            # v2.64.1: Автоматично визначаємо версію формату XML на основі платформи
            xml_format_version = self._get_xml_format_version(self.installed_platform_version)
            if xml_format_version != self.processor.platform_version:
                logger.info(
                    f"📝 XML format version adjusted: {self.processor.platform_version} → {xml_format_version} "
                    f"(for platform {self.installed_platform_version})"
                )
        else:
            # v2.64.3: Fallback - використовуємо DEFAULT_XML_FORMAT_VERSION замість YAML версії!
            # КРИТИЧНО: processor.platform_version - це версія формату XML (2.11, 2.18),
            # яка може не відповідати платформі користувача!
            # DEFAULT_XML_FORMAT_VERSION = "2.9" відповідає DEFAULT_COMPATIBILITY_MODE = "Version8_3_15"
            logger.warning(
                f"⚠️ Cannot detect installed platform version. "
                f"Using fallback: CompatibilityMode={DEFAULT_COMPATIBILITY_MODE}, "
                f"XML format={DEFAULT_XML_FORMAT_VERSION}. "
                f"Specify --compiler-path if this causes errors."
            )
            compatibility_mode = DEFAULT_COMPATIBILITY_MODE
            xml_format_version = DEFAULT_XML_FORMAT_VERSION

        # v2.64.3: Зберігаємо обчислену версію для використання в інших методах
        self.xml_format_version = xml_format_version

        # v2.65.0: Версія платформи як tuple для умовної генерації властивостей
        if self.installed_platform_version:
            parts = self.installed_platform_version.split('.')
            platform_version_tuple = tuple(int(p) for p in parts[:3])
        else:
            # Fallback: DEFAULT_COMPATIBILITY_MODE = "Version8_3_15" → (8, 3, 15)
            platform_version_tuple = (8, 3, 15)

        data = {
            "platform_version": xml_format_version,
            "platform_version_tuple": platform_version_tuple,  # v2.65.0: для умовної генерації властивостей
            "compatibility_mode": compatibility_mode,
            "configuration_uuid": self.configuration_uuid,
            "configuration_name": f"{self.processor.name}_Metadata",
            "processor_name": processor_name_with_suffix,
            "common_picture_names": [p.name for p in self.common_pictures_data],
            "common_module_names": [m.name for m in self.common_modules_data],  # v2.57.0+ BSP
            "catalog_names": [c.name for c in self.catalogs_data],
            "document_names": [d.name for d in self.documents_data],
            "include_processor": include_processor,
            **{f"internal_object_id_{i+1}": obj_id for i, obj_id in enumerate(self.internal_object_ids)}
        }

        # Рендеринг і збереження
        xml_content = template.render(data)
        output_file = config_dir / "Configuration.xml"
        output_file.write_text(xml_content, encoding="utf-8")

        logger.info(f"✅ Generated: {output_file}")

    def _generate_language(self, config_dir: Path) -> None:
        """Генерує Languages/Русский.xml та Languages/English.xml"""
        languages_dir = config_dir / "Languages"
        languages_dir.mkdir(exist_ok=True)

        # Генеруємо Русский.xml
        # v2.64.3: Використовуємо self.xml_format_version для консистентності
        russian_template = self.jinja_env.get_template("language.xml.j2")
        russian_data = {
            "platform_version": self.xml_format_version,
            "uuid": generate_uuid()
        }
        russian_xml = russian_template.render(russian_data)
        russian_file = languages_dir / "Русский.xml"
        russian_file.write_text(russian_xml, encoding="utf-8")
        logger.info(f"✅ Generated: {russian_file}")

        # Генеруємо English.xml
        english_template = self.jinja_env.get_template("english.xml.j2")
        english_data = {
            "platform_version": self.xml_format_version,
            "uuid": generate_uuid()
        }
        english_xml = english_template.render(english_data)
        english_file = languages_dir / "English.xml"
        english_file.write_text(english_xml, encoding="utf-8")
        logger.info(f"✅ Generated: {english_file}")

    def _generate_catalogs(self, config_dir: Path) -> None:
        """Генерує Catalogs/*.xml"""
        if not self.catalogs_data:
            return

        catalogs_dir = config_dir / "Catalogs"
        catalogs_dir.mkdir(exist_ok=True)

        template = self.jinja_env.get_template("catalog_minimal.xml.j2")

        for catalog_data in self.catalogs_data:
            # v2.64.3: Використовуємо self.xml_format_version для консистентності
            data = {
                "platform_version": self.xml_format_version,
                "catalog_uuid": catalog_data.uuid,
                "catalog_name": catalog_data.name,
                "catalog_synonym": catalog_data.name,  # Synonym = Name для мінімальних метаданих
                "generated_types": catalog_data.generated_types,
                "attributes": catalog_data.attributes,  # Smart stub attributes
            }

            xml_content = template.render(data)
            output_file = catalogs_dir / f"{catalog_data.name}.xml"
            output_file.write_text(xml_content, encoding="utf-8")

            attr_info = f" ({len(catalog_data.attributes)} attributes)" if catalog_data.attributes else ""
            logger.info(f"✅ Generated: {output_file}{attr_info}")

    def _generate_documents(self, config_dir: Path) -> None:
        """Генерує Documents/*.xml"""
        if not self.documents_data:
            return

        documents_dir = config_dir / "Documents"
        documents_dir.mkdir(exist_ok=True)

        template = self.jinja_env.get_template("document_minimal.xml.j2")

        for document_data in self.documents_data:
            # v2.64.3: Використовуємо self.xml_format_version для консистентності
            data = {
                "platform_version": self.xml_format_version,
                "document_uuid": document_data.uuid,
                "document_name": document_data.name,
                "document_synonym": document_data.name,  # Synonym = Name для мінімальних метаданих
                "generated_types": document_data.generated_types,
                "attributes": document_data.attributes,  # Smart stub attributes
            }

            xml_content = template.render(data)
            output_file = documents_dir / f"{document_data.name}.xml"
            output_file.write_text(xml_content, encoding="utf-8")

            attr_info = f" ({len(document_data.attributes)} attributes)" if document_data.attributes else ""
            logger.info(f"✅ Generated: {output_file}{attr_info}")

    def _generate_common_pictures(self, config_dir: Path) -> None:
        """
        Генерує CommonPictures/*.xml з placeholder картинками

        Структура для кожної картинки:
        CommonPictures/
        ├── PictureName.xml
        └── PictureName/
            └── Ext/
                ├── Picture.xml
                └── Picture/
                    └── Picture.png
        """
        import shutil

        if not self.common_pictures_data:
            return

        pictures_dir = config_dir / "CommonPictures"
        pictures_dir.mkdir(exist_ok=True)

        # Шлях до placeholder.png
        assets_dir = Path(__file__).parent.parent / "assets"
        placeholder_path = assets_dir / "placeholder.png"

        if not placeholder_path.exists():
            logger.warning(f"⚠️ Placeholder image not found: {placeholder_path}")
            return

        main_template = self.jinja_env.get_template("common_picture_minimal.xml.j2")
        ext_template = self.jinja_env.get_template("common_picture_ext.xml.j2")

        for picture_data in self.common_pictures_data:
            # 1. Генерація PictureName.xml
            # v2.64.3: Використовуємо self.xml_format_version для консистентності
            main_data = {
                "platform_version": self.xml_format_version,
                "picture_uuid": picture_data.uuid,
                "picture_name": picture_data.name,
            }
            main_xml = main_template.render(main_data)
            main_file = pictures_dir / f"{picture_data.name}.xml"
            main_file.write_text(main_xml, encoding="utf-8")

            # 2. Створення структури PictureName/Ext/Picture/
            picture_content_dir = pictures_dir / picture_data.name / "Ext" / "Picture"
            picture_content_dir.mkdir(parents=True, exist_ok=True)

            # 3. Генерація Picture.xml
            ext_data = {
                "platform_version": self.xml_format_version,
            }
            ext_xml = ext_template.render(ext_data)
            ext_file = pictures_dir / picture_data.name / "Ext" / "Picture.xml"
            ext_file.write_text(ext_xml, encoding="utf-8")

            # 4. Копіювання placeholder.png
            target_picture = picture_content_dir / "Picture.png"
            shutil.copy2(placeholder_path, target_picture)

            logger.info(f"✅ Generated CommonPicture: {picture_data.name}")

    def _generate_common_modules(self, config_dir: Path) -> None:
        """
        v2.57.0+ Генерує CommonModules/*.xml та BSL файли для BSP модулів.

        Структура для кожного модуля:
        CommonModules/
        ├── ModuleName.xml
        └── ModuleName/
            └── Ext/
                └── Module.bsl
        """
        if not self.common_modules_data:
            return

        modules_dir = config_dir / "CommonModules"
        modules_dir.mkdir(exist_ok=True)

        main_template = self.jinja_env.get_template("common_module_stub.xml.j2")
        bsl_template = self.jinja_env.get_template("common_module_bsl_stub.bsl.j2")

        for module_data in self.common_modules_data:
            # 1. Генерація ModuleName.xml
            # v2.64.3: Використовуємо self.xml_format_version для консистентності
            main_data = {
                "platform_version": self.xml_format_version,
                "module_uuid": module_data.uuid,
                "module_name": module_data.name,
            }
            main_xml = main_template.render(main_data)
            main_file = modules_dir / f"{module_data.name}.xml"
            main_file.write_text(main_xml, encoding="utf-8")

            # 2. Створення структури ModuleName/Ext/
            module_content_dir = modules_dir / module_data.name / "Ext"
            module_content_dir.mkdir(parents=True, exist_ok=True)

            # 3. Генерація Module.bsl з stub функціями
            bsl_data = {
                "module_name": module_data.name,
            }
            bsl_content = bsl_template.render(bsl_data)
            bsl_file = module_content_dir / "Module.bsl"
            bsl_file.write_text(bsl_content, encoding="utf-8-sig")

            logger.info(f"✅ Generated CommonModule stub: {module_data.name}")

    def _copy_data_processor(self, config_dir: Path, processor_xml_dir: Path, processor_suffix: str = "") -> None:
        """
        Копіює згенерований DataProcessor в Configuration структуру.

        ProcessorGenerator створює:
          processor_xml/ProcessorName/ProcessorName.xml
          processor_xml/ProcessorName/ProcessorName/Ext/
          processor_xml/ProcessorName/ProcessorName/Forms/

        Configuration очікує:
          DataProcessors/ProcessorName{suffix}.xml
          DataProcessors/ProcessorName{suffix}/Ext/
          DataProcessors/ProcessorName{suffix}/Forms/

        Args:
            config_dir: Директорія Configuration
            processor_xml_dir: Вихідна директорія з DataProcessor XML
            processor_suffix: Суфікс для назви (наприклад, "_Validation")
        """
        import shutil

        data_processors_dir = config_dir / "DataProcessors"
        data_processors_dir.mkdir(exist_ok=True)

        # ProcessorGenerator створює структуру: processor_xml/ProcessorName/
        source_root = processor_xml_dir / self.processor.name

        if not source_root.exists():
            raise FileNotFoundError(f"Processor XML not found: {source_root}")

        # Файл ProcessorName.xml на верхньому рівні
        source_xml = source_root / f"{self.processor.name}.xml"
        if not source_xml.exists():
            raise FileNotFoundError(f"Processor XML file not found: {source_xml}")

        # Папка з вмістом ProcessorName/Ext, ProcessorName/Forms
        source_content = source_root / self.processor.name
        if not source_content.exists():
            raise FileNotFoundError(f"Processor content folder not found: {source_content}")

        # Цільова назва з suffix
        target_name = f"{self.processor.name}{processor_suffix}"

        # Копіюємо файл ProcessorName.xml і конвертуємо ExternalDataProcessor → DataProcessor
        target_xml = data_processors_dir / f"{target_name}.xml"
        self.xml_converter.convert_external_to_internal(
            source_xml,
            target_xml,
            add_cfg_prefix=True,  # Configuration DataProcessor ПОТРЕБУЄ cfg: префіксів для metadata types!
            rename_to=target_name if processor_suffix else None,
            generate_new_uuid=True  # Генеруємо новий UUID для уникнення конфлікту з ExternalDataProcessor
        )

        # Копіюємо ВМІСТ папки (без подвоєння назви)
        # ExternalDataProcessor: ProcessorName/ProcessorName/Ext
        # DataProcessor:         ProcessorName/Ext
        target_dir = data_processors_dir / target_name
        if target_dir.exists():
            shutil.rmtree(target_dir)

        # Копіюємо вміст source_content (Ext, Forms) без подвоєння назви
        target_dir.mkdir(parents=True, exist_ok=True)
        for item in source_content.iterdir():
            if item.is_dir():
                shutil.copytree(item, target_dir / item.name)
            else:
                shutil.copy2(item, target_dir / item.name)

        # Конвертуємо всі XML файли в скопійованій структурі (з перейменуванням + новими UUID)
        self.xml_converter.convert_all_xml_in_directory(
            target_dir,
            transformation="external_to_internal",
            rename_to=target_name if processor_suffix else None,
            original_name=self.processor.name,
            generate_new_uuids=True  # Генеруємо нові UUID для уникнення конфлікту з ExternalDataProcessor
        )

        logger.info(f"✅ Copied & converted DataProcessor: {target_xml}")
        logger.info(f"✅ Copied DataProcessor content: {target_dir}")

    def print_generation_summary(self) -> None:
        """Виводить підсумок генерації"""
        logger.info("\n" + "="*60)
        logger.info("Configuration Generation Summary")
        logger.info("="*60)

        logger.info(f"\n📦 Configuration: {self.processor.name}_Metadata")
        logger.info(f"   UUID: {self.configuration_uuid}")
        logger.info(f"   Platform: {self.processor.platform_version}")

        logger.info(f"\n📚 Catalogs ({len(self.catalogs_data)}):")
        for catalog_data in self.catalogs_data:
            logger.info(f"   - {catalog_data.name} ({catalog_data.uuid})")
            logger.info(f"     Generated types: {len(catalog_data.generated_types)} (11 UUIDs total)")

        logger.info(f"\n📄 Documents ({len(self.documents_data)}):")
        for document_data in self.documents_data:
            logger.info(f"   - {document_data.name} ({document_data.uuid})")
            logger.info(f"     Generated types: {len(document_data.generated_types)} (11 UUIDs total)")

        logger.info(f"\n🖼️ CommonPictures ({len(self.common_pictures_data)}):")
        for picture_data in self.common_pictures_data:
            logger.info(f"   - {picture_data.name} ({picture_data.uuid})")

        logger.info(f"\n🔧 DataProcessor: {self.processor.name}")

        total_uuids = (
            1 +  # Configuration
            7 +  # InternalInfo ObjectIds
            1 +  # Language
            len(self.catalogs_data) * 11 +  # Catalogs (1 + 5*2)
            len(self.documents_data) * 11 +  # Documents (1 + 5*2)
            len(self.common_pictures_data) * 1  # CommonPictures (1 UUID each)
        )
        logger.info(f"\n✨ Total UUIDs generated: {total_uuids}")
        logger.info("="*60 + "\n")
