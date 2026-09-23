#!/usr/bin/env python3
"""Render assets/demo.gif from a canned CLI transcript.

Looks like a terminal: black background, monospace, green/white text,
lines appearing over time. Stdlib everywhere else; this tool needs Pillow.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "assets" / "demo.gif"
FONT_CANDIDATES = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"),
    Path("/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf"),
    Path("/usr/share/fonts/TTF/DejaVuSansMono.ttf"),
)

WIDTH = 900
HEIGHT = 480
MARGIN_X = 22
MARGIN_Y = 18
LINE_GAP = 6
FRAME_MS = 500
BG = (13, 17, 23)
DIM = (110, 118, 129)
GREEN = (63, 185, 80)
WHITE = (230, 237, 243)
YELLOW = (210, 153, 34)
BLUE = (88, 166, 255)
RED = (248, 81, 73)
MUTED = (139, 148, 158)

CLEAR = "---CLEAR---"

# Simulated CLI transcript. Progressive reveal is line-based.
# CLEAR starts a new terminal scene so the second example is not clipped.
TRANSCRIPT: list[str] = [
    "$ python3 main.py --classify \"Hola Sergio, recibido! Cualquier novedad te aviso.\"",
    "{",
    '  "classification": "simple_ack",',
    '  "route": "simple_ack",',
    '  "confidence": 1.0,',
    '  "choice": "acuse_simple",',
    '  "hot_flags": [],',
    '  "usage": {"cost": 0.000032}',
    "}",
    CLEAR,
    "$ python3 main.py --classify \"Could you share your salary expectations?\"",
    "{",
    '  "classification": "needs_judgment",',
    '  "route": "needs_judgment",',
    '  "confidence": 1.0,',
    '  "choice": "requiere_decision",',
    '  "hot_flags": ["pide_info", "menciona_salario"],',
    '  "usage": {"cost": 0.000032}',
    "}",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _line_color(line: str) -> tuple[int, int, int]:
    stripped = line.strip()
    if line.startswith("$"):
        return GREEN
    if stripped in {"{", "}"}:
        return MUTED
    if '"classification"' in line or '"route"' in line:
        return WHITE
    if '"confidence"' in line or '"choice"' in line:
        return BLUE
    if '"hot_flags"' in line:
        return YELLOW if "menciona_salario" in line or "pide_info" in line else DIM
    if '"usage"' in line:
        return DIM
    if not stripped:
        return BG
    return WHITE


def _draw_chrome(draw: ImageDraw.ImageDraw, font_small: ImageFont.ImageFont) -> None:
    """Traffic-light title bar so it reads as a terminal window."""
    draw.rectangle((0, 0, WIDTH, 28), fill=(22, 27, 34))
    for cx, color in ((16, RED), (34, YELLOW), (52, GREEN)):
        draw.ellipse((cx, 8, cx + 12, 20), fill=color)
    draw.text((72, 6), "ai-decision-engine — typed decisions", font=font_small, fill=DIM)


def render_frame(
    visible: list[str],
    font: ImageFont.ImageFont,
    font_small: ImageFont.ImageFont,
    line_h: int,
) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    _draw_chrome(draw, font_small)
    y = 40
    for line in visible:
        if y + line_h > HEIGHT - MARGIN_Y:
            break
        draw.text((MARGIN_X, y), line, font=font, fill=_line_color(line))
        y += line_h + LINE_GAP
    # blinking block cursor on the last non-empty frame
    if visible:
        last = visible[-1]
        cursor_y = 40 + (len(visible) - 1) * (line_h + LINE_GAP)
        bbox = draw.textbbox((MARGIN_X, cursor_y), last, font=font)
        draw.rectangle((bbox[2] + 3, cursor_y + 2, bbox[2] + 11, cursor_y + line_h - 2), fill=GREEN)
    return image


def build_frames() -> list[Image.Image]:
    font = _load_font(15)
    font_small = _load_font(12)
    probe = Image.new("RGB", (10, 10))
    probe_draw = ImageDraw.Draw(probe)
    line_h = probe_draw.textbbox((0, 0), "Ag", font=font)[3]

    frames: list[Image.Image] = []
    # Title-only beat
    frames.append(render_frame([], font, font_small, line_h))

    visible: list[str] = []
    for line in TRANSCRIPT:
        if line == CLEAR:
            frames.append(frames[-1].copy())
            visible = []
            frames.append(render_frame(visible, font, font_small, line_h))
            continue
        if line.startswith("$") and len(line) > 24:
            # type the command in two chunks so the gif feels alive
            prefix = line[: max(18, line.find("--classify") + len("--classify"))]
            visible.append(prefix)
            frames.append(render_frame(visible, font, font_small, line_h))
            visible[-1] = line
            frames.append(render_frame(visible, font, font_small, line_h))
            continue
        visible.append(line)
        frames.append(render_frame(visible, font, font_small, line_h))

    # hold the finished screen
    frames.append(frames[-1].copy())
    frames.append(frames[-1].copy())
    return frames


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frames = build_frames()
    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        duration=FRAME_MS,
        loop=0,
        optimize=True,
    )
    size = OUTPUT.stat().st_size
    print(f"wrote {OUTPUT} ({size} bytes, {len(frames)} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
