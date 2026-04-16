#!/usr/bin/env python3
"""
Smoke test: генерація EPF/XML з усіх прикладів.

Використання:
    python scripts/smoke_test_all_examples.py
    python scripts/smoke_test_all_examples.py --format xml
    python scripts/smoke_test_all_examples.py --format epf
    python scripts/smoke_test_all_examples.py --verbose
    python scripts/smoke_test_all_examples.py --keep-output

Призначення:
    Швидка перевірка після великих рефакторингів що всі приклади
    коректно парсяться та генеруються.
"""

import sys
import os
import argparse
import tempfile
import shutil
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Додаємо шлях до модуля
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import with importlib due to module name with dash
import importlib
yaml_parser = importlib.import_module('1c_processor_generator.yaml_parser')
generator_mod = importlib.import_module('1c_processor_generator.generator')
bsl_splitter = importlib.import_module('1c_processor_generator.bsl_splitter')
bsl_injector = importlib.import_module('1c_processor_generator.bsl_injector')
metadata_analyzer = importlib.import_module('1c_processor_generator.metadata_analyzer')
validators = importlib.import_module('1c_processor_generator.validators')

YAMLParser = yaml_parser.YAMLParser
ProcessorGenerator = generator_mod.ProcessorGenerator
BSLSplitter = bsl_splitter.BSLSplitter
BSLInjector = bsl_injector.BSLInjector
MetadataAnalyzer = metadata_analyzer.MetadataAnalyzer
ProcessorValidator = validators.ProcessorValidator
HandlerValidator = validators.HandlerValidator


@dataclass
class TestResult:
    """Результат тестування одного прикладу."""
    name: str
    success: bool
    stage: str  # parse, validate, generate, compile
    error: Optional[str] = None
    duration_ms: float = 0
    output_path: Optional[Path] = None


def find_examples(examples_dir: Path) -> list[tuple[Path, Optional[Path]]]:
    """
    Знаходить всі приклади для тестування.

    Returns:
        List of (config_path, handlers_path) tuples
    """
    examples = []

    for subdir in sorted(examples_dir.iterdir()):
        if not subdir.is_dir():
            continue

        config_path = subdir / "config.yaml"
        if not config_path.exists():
            continue

        # Шукаємо handlers файл
        handlers_path = None
        for handlers_name in ["handlers.bsl", "handler.bsl", "module.bsl"]:
            candidate = subdir / handlers_name
            if candidate.exists():
                handlers_path = candidate
                break

        examples.append((config_path, handlers_path))

    return examples


def test_example(
    config_path: Path,
    handlers_path: Optional[Path],
    output_dir: Path,
    output_format: str,
    verbose: bool
) -> TestResult:
    """Тестує один приклад."""
    name = config_path.parent.name
    start_time = time.time()

    try:
        # 1. Parse YAML
        if verbose:
            print(f"  Parsing {config_path}...")
        parser = YAMLParser(str(config_path))
        processor = parser.parse()

        if processor is None:
            return TestResult(
                name=name,
                success=False,
                stage="parse",
                error="Parser returned None",
                duration_ms=(time.time() - start_time) * 1000
            )

        # 2. Inject BSL handlers
        virtual_handlers = {}
        if handlers_path and handlers_path.exists():
            if verbose:
                print(f"  Injecting handlers from {handlers_path}...")
            splitter = BSLSplitter(handlers_path)
            virtual_handlers = splitter.extract_procedures()

            injector = BSLInjector()
            injector.virtual_handlers_cache = virtual_handlers
            injector.inject_all_handlers(processor)

        # 2.5. Validate processor and handlers
        if verbose:
            print(f"  Validating...")

        validation_log = []

        # Processor validation
        proc_validator = ProcessorValidator(processor)
        proc_valid, proc_errors, proc_warnings = proc_validator.validate()
        validation_log.append("=== Processor Validation ===")
        validation_log.append(f"Valid: {proc_valid}")
        if proc_errors:
            validation_log.append(f"Errors: {proc_errors}")
        if proc_warnings:
            validation_log.append(f"Warnings: {proc_warnings}")

        if not proc_valid:
            # Save validation log even on failure
            example_output = output_dir / name
            example_output.mkdir(parents=True, exist_ok=True)
            (example_output / "validation.log").write_text("\n".join(validation_log), encoding="utf-8")
            return TestResult(
                name=name,
                success=False,
                stage="validate",
                error=f"Processor validation: {'; '.join(proc_errors[:3])}",
                duration_ms=(time.time() - start_time) * 1000
            )

        # Handler validation (if handlers exist)
        if handlers_path and handlers_path.exists():
            handler_validator = HandlerValidator(processor, virtual_handlers)
            handler_valid, handler_errors, handler_warnings = handler_validator.validate()
            validation_log.append("\n=== Handler Validation ===")
            validation_log.append(f"Valid: {handler_valid}")
            if handler_errors:
                validation_log.append(f"Errors: {handler_errors}")
            if handler_warnings:
                validation_log.append(f"Warnings: {handler_warnings}")

            if not handler_valid:
                # Save validation log even on failure
                example_output = output_dir / name
                example_output.mkdir(parents=True, exist_ok=True)
                (example_output / "validation.log").write_text("\n".join(validation_log), encoding="utf-8")
                return TestResult(
                    name=name,
                    success=False,
                    stage="validate",
                    error=f"Handler validation: {'; '.join(handler_errors[:3])}",
                    duration_ms=(time.time() - start_time) * 1000
                )

        # 3. Generate XML
        if verbose:
            print(f"  Generating XML...")
        example_output = output_dir / name
        generator = ProcessorGenerator(processor)
        result_path = generator.generate(str(example_output))

        # Save validation log after generation
        (example_output / "validation.log").write_text("\n".join(validation_log), encoding="utf-8")

        if result_path is None:
            return TestResult(
                name=name,
                success=False,
                stage="generate",
                error="Generator returned None",
                duration_ms=(time.time() - start_time) * 1000
            )

        # 4. Compile to EPF (якщо потрібно)
        if output_format == "epf":
            if verbose:
                print(f"  Compiling to EPF...")
            try:
                epf_compiler = importlib.import_module('1c_processor_generator.epf_compiler')
                EPFCompiler = epf_compiler.EPFCompiler
                compiler = EPFCompiler()

                processor_dir = Path(result_path)
                xml_file = processor_dir / f"{processor_dir.name}.xml"
                output_epf = processor_dir.parent / f"{processor_dir.name}.epf"

                # Analyze if processor needs configuration (CatalogRef/DocumentRef/DynamicList)
                requirements = MetadataAnalyzer.analyze_processor(processor)

                if requirements.has_metadata():
                    # Use configuration mode for CatalogRef/DocumentRef/DynamicList
                    # compile_epf_with_configuration expects parent dir, not processor_dir
                    # Structure: parent_dir/ProcessorName/ProcessorName.xml
                    if verbose:
                        print(f"    Using configuration mode (has metadata requirements)")
                    success = compiler.compile_epf_with_configuration(
                        processor_dir.parent, output_epf, processor, requirements
                    )
                else:
                    # Simple mode - no external references
                    success = compiler.compile_epf(xml_file, output_epf)

                if success:
                    result_path = output_epf
            except ImportError:
                pass  # EPF compiler not available
            except Exception as e:
                # EPF compilation is optional, don't fail the test
                if verbose:
                    print(f"  Warning: EPF compilation failed: {e}")

        duration = (time.time() - start_time) * 1000
        return TestResult(
            name=name,
            success=True,
            stage="complete",
            duration_ms=duration,
            output_path=Path(result_path) if result_path else None
        )

    except Exception as e:
        duration = (time.time() - start_time) * 1000
        return TestResult(
            name=name,
            success=False,
            stage="unknown",
            error=str(e)[:200],
            duration_ms=duration
        )


def print_results(results: list[TestResult], verbose: bool, output_dir: Path, output_format: str):
    """Виводить результати тестування та зберігає звіт у файл."""
    from datetime import datetime

    report_lines = []

    def log(msg: str):
        print(msg)
        report_lines.append(msg)

    log("\n" + "=" * 70)
    log("SMOKE TEST RESULTS")
    log("=" * 70)
    log(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Output: {output_dir}")

    passed = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    # Summary
    total = len(results)
    log(f"\nTotal: {total} | Passed: {len(passed)} | Failed: {len(failed)}")

    total_time = sum(r.duration_ms for r in results)
    log(f"Total time: {total_time:.0f}ms ({total_time/1000:.1f}s)")

    # EPF summary (if epf format)
    epf_success = True
    if output_format == "epf":
        epf_files = list(output_dir.glob("*/*.epf"))
        epf_dirs = {f.parent.name for f in epf_files}
        all_dirs = [d.name for d in output_dir.iterdir() if d.is_dir()]
        no_epf = sorted(set(all_dirs) - epf_dirs)

        log(f"\n{'EPF SUMMARY':=^70}")
        log(f"Expected: {len(all_dirs)} EPF | Generated: {len(epf_files)} EPF | Missing: {len(no_epf)}")

        if no_epf:
            epf_success = False
            log(f"\nMissing EPF ({len(no_epf)}):")
            for name in no_epf:
                # Find reason from results
                result = next((r for r in results if r.name == name), None)
                if result and not result.success:
                    reason = f"{result.stage}: {result.error[:60]}..."
                else:
                    # Check for designer log
                    log_files = list((output_dir / name).glob("*_designer.log")) + \
                                list((output_dir / name).glob("*_load_config.log"))
                    if log_files:
                        reason = "EPF compilation failed (see logs)"
                    else:
                        reason = "Unknown"
                log(f"  - {name}: {reason}")

    # Passed tests (compact)
    if passed and verbose:
        log(f"\n{'PASSED':=^70}")
        for r in passed:
            log(f"  [OK] {r.name} ({r.duration_ms:.0f}ms)")

    # Failed tests (detailed)
    if failed:
        log(f"\n{'FAILED':=^70}")
        for r in failed:
            log(f"\n  [FAIL] {r.name}")
            log(f"         Stage: {r.stage}")
            log(f"         Error: {r.error}")

    log("\n" + "=" * 70)

    # Final status
    all_success = len(failed) == 0 and epf_success
    if all_success:
        log("✅ ALL TESTS PASSED!")
    else:
        log("❌ SOME TESTS FAILED!")

    log("=" * 70)

    # Save report to file
    report_path = output_dir / "smoke_test_report.txt"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\n📄 Report saved to: {report_path}")

    return all_success


def main():
    parser = argparse.ArgumentParser(
        description="Smoke test: генерація з усіх прикладів"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["xml", "epf"],
        default="xml",
        help="Output format (default: xml)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--keep-output", "-k",
        action="store_true",
        help="Keep generated output (don't delete temp dir)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        help="Output directory (default: temp)"
    )
    parser.add_argument(
        "--examples-dir", "-e",
        type=Path,
        default=Path(__file__).parent.parent / "examples" / "yaml",
        help="Examples directory"
    )

    args = parser.parse_args()

    # Знаходимо приклади
    examples_dir = args.examples_dir
    if not examples_dir.exists():
        print(f"Examples directory not found: {examples_dir}")
        sys.exit(1)

    examples = find_examples(examples_dir)
    if not examples:
        print(f"No examples found in {examples_dir}")
        sys.exit(1)

    print(f"Found {len(examples)} examples to test")
    print(f"Output format: {args.format}")

    # Створюємо output директорію
    if args.output_dir:
        output_dir = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        output_dir = Path(tempfile.mkdtemp(prefix="smoke_test_"))
        cleanup = not args.keep_output

    print(f"Output directory: {output_dir}")
    print()

    # Тестуємо кожен приклад
    results = []
    for i, (config_path, handlers_path) in enumerate(examples, 1):
        name = config_path.parent.name
        print(f"[{i}/{len(examples)}] Testing {name}...")

        result = test_example(
            config_path=config_path,
            handlers_path=handlers_path,
            output_dir=output_dir,
            output_format=args.format,
            verbose=args.verbose
        )
        results.append(result)

        if result.success:
            print(f"  OK ({result.duration_ms:.0f}ms)")
        else:
            print(f"  FAILED at {result.stage}: {result.error[:50]}...")

    # Виводимо результати
    all_passed = print_results(results, args.verbose, output_dir, args.format)

    # Cleanup
    if cleanup:
        shutil.rmtree(output_dir, ignore_errors=True)
        print(f"\nCleaned up temp directory")
    elif args.keep_output:
        print(f"\nOutput kept at: {output_dir}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
