"""
v2.67.0: EPF Version Helper - визначення версії формату XML для EPF генерації.

Модуль винесено з __main__.py для приховування внутрішньої логіки PRO модулів.
"""

from typing import Optional


def adjust_platform_version(args, processor) -> Optional[str]:
    """
    Автоматично визначає версію формату XML для EPF генерації.

    Args:
        args: Аргументи командного рядка (повинен мати compiler_path)
        processor: Processor об'єкт (повинен мати platform_version)

    Returns:
        Скорегована версія формату XML або None якщо корекція не потрібна
    """
    try:
        from .designer_finder_impl import DesignerFinder
        from .config_generator_impl import ConfigurationGenerator
    except ImportError:
        return None

    # Знаходимо Designer
    explicit_path = getattr(args, 'compiler_path', None)
    finder = DesignerFinder(explicit_path=explicit_path)
    platform_version = finder.platform_version

    # Якщо версія не визначена але Designer знайдено - пробуємо отримати з exe
    if not platform_version and finder.designer_path:
        platform_version = finder._get_file_version(finder.designer_path)
        if not platform_version:
            # Останній fallback - витягнути зі шляху
            platform_version = finder._extract_version_from_path(finder.designer_path)

    if not platform_version:
        return None

    # Використовуємо маппінг з ConfigurationGenerator
    cg = ConfigurationGenerator.__new__(ConfigurationGenerator)
    xml_version = cg._get_xml_format_version(platform_version)

    if xml_version != processor.platform_version:
        print(f"📝 XML format version adjusted: {processor.platform_version} → {xml_version} "
              f"(for platform {platform_version})")
        return xml_version

    return None
