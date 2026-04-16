"""
Configuration Generator - публічний інтерфейс.

Реалізація захищена в pro/ модулі.

Використання:
    >>> from 1c_processor_generator.configuration_generator import ConfigurationGenerator
    >>> generator = ConfigurationGenerator(processor, requirements)
    >>> config_dir = generator.generate_configuration(output_dir, xml_dir)
"""

from .pro.config_generator_impl import ConfigurationGenerator, ConfigurationData, CommonPictureData

__all__ = ["ConfigurationGenerator", "ConfigurationData", "CommonPictureData"]
