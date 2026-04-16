"""
SVG to PNG converter for 1C External Data Processors.

This module provides SVG → PNG conversion functionality to support custom pictures
in EPF files. Since 1C platform doesn't support SVG natively, all SVG files must
be converted to PNG format before being embedded in the processor structure.

Usage:
    converter = SVGConverter()
    converter.convert_svg_to_png('logo.svg', 'output.png', width=200, height=80)

Version: 2.23.0+
"""

import logging
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class SVGConversionError(Exception):
    """Raised when SVG conversion fails."""
    pass


class SVGValidationError(Exception):
    """Raised when SVG validation fails."""
    pass


class SVGConverter:
    """Handles SVG to PNG conversion for 1C processors."""

    def __init__(self):
        """Initialize converter and check available libraries."""
        self._cairosvg_available = self._check_cairosvg()
        self._pillow_available = self._check_pillow()

        if not self._cairosvg_available and not self._pillow_available:
            logger.warning(
                "Neither cairosvg nor Pillow+svglib is available. "
                "SVG conversion will not work. Install with: pip install cairosvg Pillow"
            )

    def _check_cairosvg(self) -> bool:
        """Check if cairosvg is available."""
        try:
            import cairosvg
            logger.debug("cairosvg library is available")
            return True
        except ImportError:
            logger.debug("cairosvg library is not available")
            return False
        except OSError as e:
            # cairosvg installed but cairo system library missing (common on Windows)
            logger.debug(f"cairosvg installed but cairo library not found: {e}")
            return False

    def _check_pillow(self) -> bool:
        """Check if Pillow is available."""
        try:
            from PIL import Image
            logger.debug("Pillow library is available")
            return True
        except ImportError:
            logger.debug("Pillow library is not available")
            return False

    def validate_svg(self, svg_path: str) -> bool:
        """
        Validate SVG file structure and content.

        Args:
            svg_path: Path to SVG file

        Returns:
            True if valid

        Raises:
            SVGValidationError: If validation fails
        """
        svg_path = Path(svg_path)

        # Check file exists
        if not svg_path.exists():
            raise SVGValidationError(f"SVG file not found: {svg_path}")

        # Check file extension
        if svg_path.suffix.lower() != '.svg':
            raise SVGValidationError(
                f"Invalid file extension: {svg_path.suffix}. Expected .svg"
            )

        # Check file is not empty
        if svg_path.stat().st_size == 0:
            raise SVGValidationError(f"SVG file is empty: {svg_path}")

        # Try to parse as XML
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()
        except ET.ParseError as e:
            raise SVGValidationError(f"Invalid SVG XML structure: {e}")

        # Check root element is <svg>
        # Handle both with and without namespace
        if not (root.tag == 'svg' or root.tag.endswith('}svg')):
            raise SVGValidationError(
                f"Root element must be <svg>, found: {root.tag}"
            )

        logger.debug(f"SVG validation passed: {svg_path}")
        return True

    def get_svg_dimensions(self, svg_path: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Extract width and height from SVG file.

        Args:
            svg_path: Path to SVG file

        Returns:
            Tuple of (width, height) in pixels, or (None, None) if not found
        """
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()

            # Try to get width/height attributes
            width_str = root.get('width')
            height_str = root.get('height')

            if width_str and height_str:
                # Remove units (px, pt, etc.) and convert to int
                width = int(''.join(filter(str.isdigit, width_str)))
                height = int(''.join(filter(str.isdigit, height_str)))
                return (width, height)

            # Try viewBox attribute
            viewbox = root.get('viewBox')
            if viewbox:
                parts = viewbox.split()
                if len(parts) == 4:
                    width = int(float(parts[2]))
                    height = int(float(parts[3]))
                    return (width, height)

        except Exception as e:
            logger.debug(f"Could not extract SVG dimensions: {e}")

        return (None, None)

    def convert_svg_to_png(
        self,
        svg_path: str,
        output_path: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        dpi: int = 96,
        background: str = 'transparent'
    ) -> str:
        """
        Convert SVG file to PNG format.

        Args:
            svg_path: Path to source SVG file
            output_path: Path for output PNG file
            width: Target width in pixels (optional, preserves aspect ratio)
            height: Target height in pixels (optional, preserves aspect ratio)
            dpi: DPI for conversion (default: 96)
            background: Background color (default: 'transparent')

        Returns:
            Path to created PNG file

        Raises:
            SVGConversionError: If conversion fails
        """
        # Validate input
        self.validate_svg(svg_path)

        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get SVG dimensions if not provided
        if width is None and height is None:
            svg_width, svg_height = self.get_svg_dimensions(svg_path)
            if svg_width and svg_height:
                width, height = svg_width, svg_height
                logger.debug(f"Using SVG native dimensions: {width}x{height}")
            else:
                # Default size if dimensions not found
                width, height = 300, 300
                logger.debug(f"Using default dimensions: {width}x{height}")

        # Try cairosvg first (better quality)
        if self._cairosvg_available:
            try:
                return self._convert_with_cairosvg(
                    svg_path, output_path, width, height, dpi, background
                )
            except Exception as e:
                logger.warning(f"cairosvg conversion failed: {e}. Trying fallback...")

        # Fallback to Pillow (if available)
        if self._pillow_available:
            try:
                return self._convert_with_pillow(
                    svg_path, output_path, width, height
                )
            except Exception as e:
                logger.error(f"Pillow conversion failed: {e}")
                raise SVGConversionError(
                    f"All conversion methods failed. Last error: {e}"
                )

        # No conversion library available
        raise SVGConversionError(
            "No SVG conversion library available. "
            "Install cairosvg or Pillow: pip install cairosvg Pillow"
        )

    def _convert_with_cairosvg(
        self,
        svg_path: str,
        output_path: Path,
        width: Optional[int],
        height: Optional[int],
        dpi: int,
        background: str
    ) -> str:
        """Convert SVG using cairosvg library."""
        import cairosvg

        logger.debug(
            f"Converting {svg_path} → {output_path} "
            f"(size: {width}x{height}, dpi: {dpi})"
        )

        # Prepare kwargs
        kwargs = {
            'url': str(svg_path),
            'write_to': str(output_path),
            'dpi': dpi
        }

        if width:
            kwargs['output_width'] = width
        if height:
            kwargs['output_height'] = height

        # Background handling
        if background != 'transparent':
            kwargs['background'] = background

        # Convert
        cairosvg.svg2png(**kwargs)

        logger.info(f"Successfully converted SVG to PNG: {output_path}")
        return str(output_path)

    def _convert_with_pillow(
        self,
        svg_path: str,
        output_path: Path,
        width: Optional[int],
        height: Optional[int]
    ) -> str:
        """
        Convert SVG using Pillow library.

        Note: This is a simplified fallback. Pillow doesn't support SVG natively,
        so this method has limitations. It's here for future extensibility.
        """
        from PIL import Image

        # Pillow doesn't support SVG directly
        # This is a placeholder for future implementation with svglib or similar
        raise SVGConversionError(
            "Pillow-based SVG conversion not yet implemented. "
            "Please install cairosvg: pip install cairosvg"
        )

    def optimize_size(
        self,
        png_path: str,
        max_size_kb: int = 100,
        quality: int = 85
    ) -> int:
        """
        Optimize PNG file size.

        Args:
            png_path: Path to PNG file
            max_size_kb: Maximum target size in KB
            quality: Compression quality (0-100, for lossy formats)

        Returns:
            New file size in bytes

        Raises:
            SVGConversionError: If optimization fails
        """
        if not self._pillow_available:
            logger.warning("Pillow not available, skipping optimization")
            return Path(png_path).stat().st_size

        try:
            from PIL import Image

            png_path = Path(png_path)
            original_size = png_path.stat().st_size

            # If already under limit, skip optimization
            if original_size <= max_size_kb * 1024:
                logger.debug(
                    f"PNG already under size limit: "
                    f"{original_size / 1024:.1f}KB <= {max_size_kb}KB"
                )
                return original_size

            # Open and optimize
            img = Image.open(png_path)

            # Save with optimization
            img.save(
                png_path,
                'PNG',
                optimize=True,
                compress_level=9  # Max PNG compression
            )

            new_size = png_path.stat().st_size
            reduction = (1 - new_size / original_size) * 100

            logger.info(
                f"Optimized PNG: {original_size / 1024:.1f}KB → "
                f"{new_size / 1024:.1f}KB ({reduction:.1f}% reduction)"
            )

            return new_size

        except Exception as e:
            logger.warning(f"PNG optimization failed: {e}")
            # Non-fatal, return original size
            return Path(png_path).stat().st_size
