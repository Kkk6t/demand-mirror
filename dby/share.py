"""生成 3:4 的分享图（适合小红书），把体检结果盖章展示。只用 Pillow，不需要联网。"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import STATUS_MEANING, Project, Stance, Status
from .rules import evaluate

W, H = 1080, 1440
PAPER = (246, 248, 251)
SHEET = (255, 255, 255)
INK = (29, 42, 68)
MUTED = (92, 106, 128)
RULE = (202, 214, 228)
MARK = (255, 241, 184)
STAMP = {Status.unverified: (114, 124, 140), Status.negative: (179, 52, 43), Status.paid: (46, 118, 80)}

_SANS = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
]
_SANS_BOLD = [
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
]
_SERIF_BOLD = [
    "C:/Windows/Fonts/STZHONGS.TTF",
    "C:/Windows/Fonts/simsun.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Black.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
] + _SANS_BOLD


def _font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default(size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int, max_lines: int) -> list[str]:
    """按像素宽度逐字换行（中文没有空格，只能逐字算）。"""
    lines, cur = [], ""
    no_start = "，。、；：！？）」』》,.;:!?)"
    for ch in text.replace("\n", " "):
        if draw.textlength(cur + ch, font=font) > width and ch not in no_start:
            lines.append(cur)
            cur = ch
            if len(lines) == max_lines:
                break
        else:
            cur += ch
    else:
        if cur:
            lines.append(cur)
    if len(lines) == max_lines and "".join(lines) != text.replace("\n", " "):
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > width:
            last = last[:-1]
        lines[-1] = last + "…"
    return lines


def _stamp(text: str, color: tuple[int, int, int], size: int) -> Image.Image:
    f = _font(_SERIF_BOLD, size)
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    tw = probe.textlength(text, font=f) + size * 0.15 * (len(text) - 1)
    pad_x, pad_y = int(size * 0.6), int(size * 0.45)
    w, h = int(tw + pad_x * 2), int(size + pad_y * 2)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = color + (235,)
    d.rounded_rectangle((3, 3, w - 4, h - 4), radius=10, outline=c, width=7)
    d.rounded_rectangle((15, 15, w - 16, h - 16), radius=6, outline=c, width=3)
    x = pad_x
    for ch in text:
        d.text((x, pad_y - size * 0.12), ch, font=f, fill=c)
        x += probe.textlength(ch, font=f) + size * 0.15
    return img.rotate(7, expand=True, resample=Image.BICUBIC)


def render(p: Project, now: datetime) -> bytes:
    v = evaluate(p, now)
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    M = 80
    title_f = _font(_SERIF_BOLD, 54)
    h_f = _font(_SANS_BOLD, 34)
    body_f = _font(_SANS, 32)
    small_f = _font(_SANS, 26)

    # 抬头
    d.text((M, 70), "我的点子做了一次体检", font=title_f, fill=INK)
    d.line((M, 150, W - M, 150), fill=INK, width=3)
    d.line((M, 157, W - M, 157), fill=INK, width=1)

    # 点子
    y = 190
    for line in _wrap(d, f"「{p.idea.strip()}」", body_f, W - 2 * M, 3):
        d.text((M, y), line, font=body_f, fill=MUTED)
        y += 48

    # 印章
    y += 20
    st = _stamp(v.status.value, STAMP[v.status], 110)
    img.paste(st, (M - 10, y), st)
    meaning_x = M + st.width + 20
    my = y + 30
    for line in _wrap(d, STATUS_MEANING[v.status], body_f, W - M - meaning_x, 4):
        d.text((meaning_x, my), line, font=body_f, fill=INK)
        my += 46
    y = max(y + st.height, my) + 30

    # 最该担心的事
    worries = [e.claim for e in p.evidence if e.stance == Stance.against][:3]
    if not worries:
        worries = [a.statement for a in p.assumptions][:3]
    if worries:
        d.text((M, y), "最该担心的事", font=h_f, fill=INK)
        y += 62
        for w in worries:
            lines = _wrap(d, w, body_f, W - 2 * M - 40, 2)
            for i, line in enumerate(lines):
                lw = d.textlength(line, font=body_f)
                d.rectangle((M + 40, y + 24, M + 40 + lw, y + 42), fill=MARK)
                d.text((M + 40, y), line, font=body_f, fill=INK)
                if i == 0:
                    d.rectangle((M + 6, y + 14, M + 20, y + 28), fill=STAMP[Status.negative])
                y += 46
            y += 14

    # 放弃线
    if p.criteria and y < H - 330:
        y += 10
        d.text((M, y), "我给自己定的放弃线", font=h_f, fill=INK)
        y += 62
        for c in p.criteria[:2]:
            for line in _wrap(d, c.sentence(), body_f, W - 2 * M - 40, 2):
                d.text((M + 40, y), line, font=body_f, fill=INK)
                y += 46
            y += 10

    # 页脚
    d.line((M, H - 140, W - M, H - 140), fill=RULE, width=2)
    d.text((M, H - 115), "先别做 · 不预测点子行不行，只找能推翻它的证据", font=small_f, fill=MUTED)
    d.text((M, H - 75), "github.com/Kkk6t/dont-build-yet", font=small_f, fill=MUTED)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()

