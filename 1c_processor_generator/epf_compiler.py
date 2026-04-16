"""
EPF Compiler - публічний інтерфейс.

Реалізація захищена в pro/ модулі.

Використання:
    >>> from 1c_processor_generator.epf_compiler import EPFCompiler
    >>> compiler = EPFCompiler()
    >>> compiler.compile_epf(xml_root, output_epf)
"""

from .pro.epf_compiler_impl import EPFCompiler, CompilationContext

__all__ = ["EPFCompiler", "CompilationContext"]
