"""
Post-Generation Validator - валідація після генерації XML файлів

Перевіряє, що всі елементи з YAML були коректно згенеровані в XML.
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple
import xml.etree.ElementTree as ET


class PostGenerationValidator:
    """Валідатор для перевірки коректності згенерованих XML файлів"""

    def __init__(self, processor, output_dir: Path):
        """
        Args:
            processor: Processor об'єкт з YAML конфігурацією
            output_dir: Шлях до директорії з згенерованими файлами
        """
        self.processor = processor
        self.output_dir = Path(output_dir)
        self.errors = []
        self.warnings = []

    def _count_yaml_elements(self, elements: List, depth: int = 0) -> int:
        """
        Рекурсивно підраховує кількість елементів у YAML структурі

        Args:
            elements: Список FormElement об'єктів або dict'ів (для Page)
            depth: Глибина рекурсії (для debug)

        Returns:
            Загальна кількість елементів (включаючи вкладені)
        """
        if not elements:
            return 0

        count = 0

        for elem in elements:
            count += 1  # Рахуємо сам елемент

            # Рекурсія для child_items (Pages, Page, UsualGroup, ButtonGroup, Popup)
            if elem.child_items:
                count += self._count_yaml_elements(elem.child_items, depth + 1)

        return count

    def _count_xml_elements(self, xml_path: Path) -> int:
        """
        Підраховує кількість елементів форми у згенерованому XML файлі

        Рахує всі елементи з атрибутом id (окрім AutoCommandBar з id=-1)

        Args:
            xml_path: Шлях до Form.xml файлу

        Returns:
            Кількість елементів з id
        """
        if not xml_path.exists():
            return 0

        try:
            # Читаємо файл та рахуємо елементи з id через regex (швидше за XML parser)
            content = xml_path.read_text(encoding='utf-8')

            # Шукаємо всі теги з атрибутом id (окрім id="-1")
            # Формат: name="ElementName" id="123"
            pattern = r'\s+id="(\d+)"'
            matches = re.findall(pattern, content)

            # Рахуємо тільки позитивні ID (AutoCommandBar має id=-1)
            count = len([m for m in matches if int(m) > 0])

            return count

        except Exception as e:
            self.errors.append(f"Помилка читання {xml_path}: {e}")
            return 0

    def _find_empty_containers(self, form, xml_path: Path) -> List[Dict[str, str]]:
        """
        Виявляє порожні контейнери (Page, UsualGroup, ButtonGroup) у згенерованому XML

        Args:
            form: Form об'єкт з YAML
            xml_path: Шлях до Form.xml

        Returns:
            Список dict'ів з інформацією про порожні контейнери:
            [{"type": "Page", "name": "PageName", "expected_children": 5}, ...]
        """
        if not xml_path.exists():
            return []

        empty_containers = []

        try:
            content = xml_path.read_text(encoding='utf-8')

            # Перевіряємо кожен елемент форми рекурсивно
            def check_element(elem, elem_name_prefix=""):
                """Рекурсивна перевірка елементів"""
                if isinstance(elem, dict):
                    # Dict (Page)
                    elem_type = elem.get("type", "Unknown")
                    elem_name = elem.get("name", "Unknown")
                    child_items = elem.get("child_items", [])

                    if child_items:
                        # Перевіряємо, чи є цей елемент у XML з ChildItems
                        pattern = rf'<{elem_type}\s+name="{elem_name}"[^>]*>.*?<ChildItems>.*?</ChildItems>.*?</{elem_type}>'
                        if not re.search(pattern, content, re.DOTALL):
                            # Може бути самозакриваючийся або без ChildItems
                            pattern_empty = rf'<{elem_type}\s+name="{elem_name}"[^>]*/?>(?!.*?<ChildItems>)'
                            if re.search(pattern_empty, content, re.DOTALL):
                                empty_containers.append({
                                    "type": elem_type,
                                    "name": elem_name,
                                    "expected_children": len(child_items)
                                })

                        # Рекурсивно перевіряємо дочірні елементи
                        for child in child_items:
                            check_element(child, elem_name + ".")

                else:
                    # FormElement об'єкти
                    elem_type = elem.element_type
                    elem_name = elem.name

                    if elem_type == "Pages" and hasattr(elem, "child_items") and elem.child_items:
                        # Перевіряємо Pages
                        for page in elem.child_items:
                            check_element(page, elem_name + ".")

                    elif elem_type in ["UsualGroup", "ButtonGroup"]:
                        if hasattr(elem, "properties") and "child_items" in elem.properties:
                            child_items = elem.properties["child_items"]
                            if child_items:
                                # Перевіряємо, чи є ChildItems у XML
                                pattern = rf'<{elem_type}\s+name="{elem_name}"[^>]*>.*?<ChildItems>.*?</ChildItems>.*?</{elem_type}>'
                                if not re.search(pattern, content, re.DOTALL):
                                    empty_containers.append({
                                        "type": elem_type,
                                        "name": elem_name,
                                        "expected_children": len(child_items)
                                    })

                                # Рекурсивно перевіряємо дочірні елементи
                                for child in child_items:
                                    check_element(child, elem_name + ".")

            # Перевіряємо всі елементи форми
            for elem in form.elements:
                check_element(elem)

        except Exception as e:
            self.errors.append(f"Помилка аналізу порожніх контейнерів у {xml_path}: {e}")

        return empty_containers

    def validate_generation(self, verbose: bool = True) -> bool:
        """
        Головний метод валідації згенерованих форм

        Args:
            verbose: Виводити детальну інформацію

        Returns:
            True якщо всі форми згенеровані коректно, False якщо є помилки
        """
        if verbose:
            print("\n📊 Post-Generation Validation:")

        all_valid = True

        for form in self.processor.forms:
            form_name = form.name

            # Підраховуємо елементи у YAML
            yaml_count = self._count_yaml_elements(form.elements)

            # Шлях до згенерованого Form.xml
            xml_path = self.output_dir / self.processor.name / self.processor.name / "Forms" / form_name / "Ext" / "Form.xml"

            # Підраховуємо елементи у XML
            xml_count = self._count_xml_elements(xml_path)

            # Шукаємо порожні контейнери
            empty_containers = self._find_empty_containers(form, xml_path)

            # Аналіз результатів
            if empty_containers:
                # Критична помилка - є порожні контейнери
                if verbose:
                    print(f"❌ Form '{form_name}': {len(empty_containers)} empty container(s) found")
                    for container in empty_containers[:3]:  # Показуємо перші 3
                        print(f"   - {container['type']} '{container['name']}' has 0 children (expected {container['expected_children']})")
                    if len(empty_containers) > 3:
                        print(f"   ... and {len(empty_containers) - 3} more")

                self.errors.append(f"Form '{form_name}': {len(empty_containers)} empty containers")
                all_valid = False

            elif xml_count < yaml_count * 0.5:  # Якщо менше 50% елементів - підозріло
                # Можлива помилка - занадто мало елементів
                percentage = (xml_count / yaml_count * 100) if yaml_count > 0 else 0
                if verbose:
                    print(f"⚠️  Form '{form_name}': {xml_count}/{yaml_count} elements ({percentage:.1f}%)")

                self.warnings.append(f"Form '{form_name}': Only {percentage:.1f}% elements generated")
                # Не блокуємо генерацію, але попереджаємо

            else:
                # Все OK (більше елементів - нормально, бо генератор додає ContextMenu, ExtendedTooltip, колонки таблиць)
                if verbose:
                    print(f"✅ Form '{form_name}': {xml_count} elements generated")

        # Підсумок
        if verbose:
            if self.errors:
                print(f"\n❌ Validation FAILED: {len(self.errors)} error(s)")
            elif self.warnings:
                print(f"\n⚠️  Validation completed with {len(self.warnings)} warning(s)")
            else:
                print("\n✅ All forms validated successfully!")

        return all_valid and not self.errors
