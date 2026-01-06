"""
Generate Icon Files from SVG

This script converts the SVG icon to various formats needed for:
- Windows: ICO (16x16, 32x32, 48x48, 64x64, 128x128, 256x256)
- MacOS: ICNS (multiple resolutions)
- Linux: PNG (various sizes)

Requirements:
    pip install cairosvg pillow
"""

import os
from pathlib import Path

try:
    import cairosvg
    from PIL import Image
    import io
except ImportError:
    print("Please install required packages:")
    print("  pip install cairosvg pillow")
    exit(1)


def svg_to_png(svg_path: str, output_path: str, size: int):
    """Convert SVG to PNG at specified size"""
    cairosvg.svg2png(
        url=svg_path,
        write_to=output_path,
        output_width=size,
        output_height=size
    )
    print(f"✓ Generated PNG: {output_path} ({size}x{size})")


def create_ico_from_pngs(png_paths: list, output_path: str):
    """Create ICO file from multiple PNG files"""
    images = []
    for png_path in png_paths:
        img = Image.open(png_path)
        images.append(img)

    # Save as ICO with multiple sizes
    images[0].save(
        output_path,
        format='ICO',
        sizes=[(img.size[0], img.size[1]) for img in images]
    )
    print(f"✓ Generated ICO: {output_path}")


def create_icns_from_pngs(png_paths: list, output_path: str):
    """Create ICNS file from multiple PNG files (requires iconutil on macOS)"""
    import subprocess
    import tempfile
    import shutil

    # Create iconset directory
    with tempfile.TemporaryDirectory() as tmpdir:
        iconset_dir = Path(tmpdir) / "icon.iconset"
        iconset_dir.mkdir()

        # Map sizes to iconset naming convention
        size_map = {
            16: "icon_16x16.png",
            32: ["icon_16x16@2x.png", "icon_32x32.png"],
            64: "icon_32x32@2x.png",
            128: ["icon_128x128.png", "icon_64x64@2x.png"],
            256: ["icon_128x128@2x.png", "icon_256x256.png"],
            512: ["icon_256x256@2x.png", "icon_512x512.png"],
            1024: "icon_512x512@2x.png"
        }

        # Copy PNGs to iconset with proper naming
        for png_path in png_paths:
            size = Image.open(png_path).size[0]
            if size in size_map:
                names = size_map[size]
                if isinstance(names, str):
                    names = [names]
                for name in names:
                    shutil.copy(png_path, iconset_dir / name)

        # Convert iconset to icns using iconutil (macOS only)
        try:
            subprocess.run(
                ['iconutil', '-c', 'icns', str(iconset_dir), '-o', output_path],
                check=True
            )
            print(f"✓ Generated ICNS: {output_path}")
        except FileNotFoundError:
            print("⚠ iconutil not found (only available on macOS)")
            print("  ICNS file generation skipped")
        except subprocess.CalledProcessError as e:
            print(f"⚠ Failed to generate ICNS: {e}")


def main():
    """Generate all icon files"""
    assets_dir = Path(__file__).parent
    icons_dir = assets_dir / "icons"
    svg_path = icons_dir / "icon.svg"

    if not svg_path.exists():
        print(f"✗ SVG file not found: {svg_path}")
        return

    print("Generating icon files from SVG...")
    print("=" * 50)

    # Generate PNGs at various sizes
    sizes = [16, 32, 48, 64, 128, 256, 512, 1024]
    png_paths = []

    for size in sizes:
        png_path = icons_dir / f"icon_{size}x{size}.png"
        svg_to_png(str(svg_path), str(png_path), size)
        png_paths.append(str(png_path))

    # Generate Windows ICO (multiple sizes embedded)
    ico_sizes_to_include = [16, 32, 48, 64, 128, 256]
    ico_pngs = [icons_dir / f"icon_{s}x{s}.png" for s in ico_sizes_to_include]
    ico_path = icons_dir / "icon.ico"
    create_ico_from_pngs([str(p) for p in ico_pngs], str(ico_path))

    # Generate MacOS ICNS (requires macOS)
    icns_path = icons_dir / "icon.icns"
    create_icns_from_pngs(png_paths, str(icns_path))

    print("\n" + "=" * 50)
    print("Icon generation complete!")
    print(f"\nGenerated files in: {icons_dir}")
    print("- icon.ico (Windows)")
    print("- icon.icns (macOS)")
    print("- icon_*.png (various sizes)")


if __name__ == "__main__":
    main()
