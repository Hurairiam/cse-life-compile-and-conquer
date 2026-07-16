"""
assemble_sprite_sheet.py
CSE Life: Compile & Conquer -- dev4-ui-screens asset pipeline

Takes individually AI-generated frame images and assembles them into a
single sprite sheet PNG matching the exact spec required by the game
(48x48 px frames, transparent background). Works for both the Player
(4 directions x 4 frames) and NPC idle sheets (1 row x 2-4 frames) --
see --rows / --cols / --directions.

USAGE (Player sheet, default):
    python3 assemble_sprite_sheet.py --input raw_frames/player --output assets/sprites/player_walk.png

USAGE (NPC idle sheet, e.g. 1 row x 3 frames):
    python3 assemble_sprite_sheet.py --input raw_frames/npc_advisor --output assets/sprites/npc_advisor.png \
        --directions idle --cols 3

INPUT FOLDER NAMING CONVENTION (required):
    <direction>_<frame_number>.png   e.g. down_1.png, down_2.png ... up_4.png
    Frame numbers are 1-indexed and map left-to-right into columns.
    Any image size/format Pillow can open works -- this script resizes
    and re-keys transparency for you.

TRANSPARENCY:
    If your AI tool can't output true alpha transparency, generate frames
    on a flat chroma-key color (pure green #00FF00 or pure magenta #FF00FF
    both work well since neither is likely to appear in character art) and
    pass --chroma-key 00FF00. Pixels matching that color (within
    --tolerance) become fully transparent.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from PIL import Image

FRAME_SIZE = 48


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Converts a hex string like '00FF00' or '#00FF00' to an (R,G,B) tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore


def apply_chroma_key(img: Image.Image, key_rgb: tuple[int, int, int],
                      tolerance: int) -> Image.Image:
    """Returns a copy of img with pixels near key_rgb made transparent."""
    img = img.convert("RGBA")
    pixels = img.load()
    kr, kg, kb = key_rgb
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = pixels[x, y]
            if abs(r - kr) <= tolerance and abs(g - kg) <= tolerance \
                    and abs(b - kb) <= tolerance:
                pixels[x, y] = (r, g, b, 0)
    return img


def load_frame(path: Path, chroma_key: tuple[int, int, int] | None,
               tolerance: int) -> Image.Image:
    """Loads one raw frame, applies chroma-keying if requested, resizes to 48x48."""
    img = Image.open(path)
    if chroma_key is not None:
        img = apply_chroma_key(img, chroma_key, tolerance)
    else:
        img = img.convert("RGBA")
    if img.size != (FRAME_SIZE, FRAME_SIZE):
        img = img.resize((FRAME_SIZE, FRAME_SIZE), Image.LANCZOS)
    return img


def build_sheet(input_dir: Path, output_path: Path, directions: list[str],
                 cols: int, chroma_key: tuple[int, int, int] | None,
                 tolerance: int) -> None:
    """Assembles a sheet with len(directions) rows x cols columns."""
    sheet = Image.new("RGBA", (FRAME_SIZE * cols, FRAME_SIZE * len(directions)),
                       (0, 0, 0, 0))
    missing: list[str] = []

    for row, direction in enumerate(directions):
        for col in range(cols):
            frame_num = col + 1
            candidates = list(input_dir.glob(f"{direction}_{frame_num}.*"))
            if not candidates:
                missing.append(f"{direction}_{frame_num}")
                continue
            frame = load_frame(candidates[0], chroma_key, tolerance)
            sheet.paste(frame, (col * FRAME_SIZE, row * FRAME_SIZE), frame)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)

    print(f"Saved {output_path} ({sheet.width}x{sheet.height})")
    if missing:
        print(f"WARNING -- {len(missing)} frame(s) not found, left transparent: "
              + ", ".join(missing))


def main() -> None:
    """Parses CLI args and runs the assembly."""
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, type=Path,
                         help="Folder containing raw frame images")
    parser.add_argument("--output", required=True, type=Path,
                         help="Output sheet path, e.g. assets/sprites/player_walk.png")
    parser.add_argument("--directions", nargs="+",
                         default=["down", "left", "right", "up"],
                         help="Row order, default matches Player sheet spec")
    parser.add_argument("--cols", type=int, default=4,
                         help="Frames per row, default 4 (use 2-4 for NPC idle sheets)")
    parser.add_argument("--chroma-key", type=str, default=None,
                         help="Hex background color to key out, e.g. 00FF00")
    parser.add_argument("--tolerance", type=int, default=25,
                         help="Chroma-key color match tolerance, 0-255 (default 25)")
    args = parser.parse_args()

    if not args.input.is_dir():
        sys.exit(f"Input folder not found: {args.input}")

    chroma_rgb = hex_to_rgb(args.chroma_key) if args.chroma_key else None
    build_sheet(args.input, args.output, args.directions, args.cols,
                chroma_rgb, args.tolerance)


if __name__ == "__main__":
    main()
