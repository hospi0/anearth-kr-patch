# -*- coding: utf-8 -*-
r"""구운 UI 그림 한글화 — GAME.PRG 블록 0x2454018(8bpp 셀 64KB → VDP2 0x20000, 셀 번호 0x800+n)
  (2026-09-27 스테이트 VDP2 패턴 네임 표로 찾음: 메뉴 창 = 셀 0x801‥0x848 가로 6×세로 12, 금액 창 = 셀 0x850‥0x88F 가로 16×세로 4)
  · 메뉴 라벨 5개(32×16, 창 안 x8·y8+16k): 道具 魔法 装備 状態 設定 → 도구 마법 장비 상태 설정
    글자 = 색 144(굵은 2픽셀), 배경 = 53‥55 질감 → 글자 픽셀을 배경으로 지우고 한글을 144 로.
  · 금액 창 «ルクソル»(기울임, 159→101→99→96 그라데이션 + 테두리 16) → «룩솔»
  python tools/uigfx.py  → work/uigfx_preview.png
"""
import os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bdf

BLOCK = 0x2454018
SLOT = 9936
FB = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11-Bold.bdf'
F14 = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri14.bdf'
MENU = ['도구', '마법', '장비', '상태', '설정']
MENU_CELL0, MENU_W, MENU_H = 1, 6, 12
MONEY_CELL0, MONEY_W, MONEY_H = 0x50, 16, 4
MONEY_BOX = (8, 24, 82, 124)          # 금액 창 안 «ルクソル» 자리 (y0, y1, x0, x1)
BG = (51, 52, 53, 54, 55, 56)


def panel(cells, first, w, h):
    return np.vstack([np.hstack([cells[first + r * w + c] for c in range(w)]) for r in range(h)])


def unpanel(cells, first, w, h, p):
    for r in range(h):
        for c in range(w):
            cells[first + r * w + c] = p[r * 8:(r + 1) * 8, c * 8:(c + 1) * 8]


def glyph_mask(F, s, w, h):
    """문자열을 w×h 안에 가운데로(픽셀 마스크)"""
    pts_all = []; x = 0
    for ch in s:
        pts, adv = F.draw(ch)
        for px, py in pts:
            pts_all.append((px + x, py))
        x += adv if adv else 12
    m = np.zeros((h, w), np.uint8)
    if not pts_all:
        return m
    xs = [p[0] for p in pts_all]; ys = [p[1] for p in pts_all]
    ox = (w - (max(xs) - min(xs) + 1)) // 2 - min(xs)
    oy = (h - (max(ys) - min(ys) + 1)) // 2 - min(ys)
    for px, py in pts_all:
        if 0 <= px + ox < w and 0 <= py + oy < h:
            m[py + oy, px + ox] = 1
    return m


def fill_bg(area):
    """글자 픽셀(배경 값 아닌 것)을 같은 줄의 배경 값으로 — 질감은 왼쪽 이웃을 복사"""
    a = area.copy()
    for y in range(a.shape[0]):
        for x in range(a.shape[1]):
            if a[y, x] not in BG:
                a[y, x] = a[y, x - 1] if x > 0 and a[y, x - 1] in BG else 54
    return a


def build(data):
    d = np.frombuffer(data, np.uint8).copy()
    cells = d.reshape(-1, 8, 8)
    F = bdf.Font(FB)
    # 메뉴
    p = panel(cells, MENU_CELL0, MENU_W, MENU_H)
    for k, s in enumerate(MENU):
        y0, x0 = 8 + 16 * k, 8
        box = p[y0 + 2:y0 + 14, x0 + 2:x0 + 30]          # 테두리 1픽셀 안쪽
        box[:] = fill_bg(box)
        m = glyph_mask(F, s, 28, 12)
        box[m == 1] = 144
    unpanel(cells, MENU_CELL0, MENU_W, MENU_H, p)
    # 금액 «룩솔»
    p = panel(cells, MONEY_CELL0, MONEY_W, MONEY_H)
    y0, y1, x0, x1 = MONEY_BOX
    box = p[y0:y1, x0:x1]
    box[:] = fill_bg(box)
    h, w = box.shape
    m = glyph_mask(bdf.Font(F14), '룩솔', w - 8, h - 2)     # 갈무리14 그대로(굵게 하면 뭉개진다)
    it = np.zeros((h, w), np.uint8)                        # 기울임: 아래로 갈수록 왼쪽(원문과 같은 방향)
    for y in range(h - 2):
        sh = (h - 2 - y) // 3
        for x in range(m.shape[1]):
            if m[y, x] and x + sh + 2 < w:
                it[y + 1, x + sh + 2] = 1
    rows = [y for y in range(h) if it[y].any()]
    top, bot = min(rows), max(rows)
    span = max(1, bot - top)
    for y in range(h):
        for x in range(w):
            if it[y, x]:
                f = (y - top) / span                        # 위 흰색 → 아래 보라(원래 «ルクソル» 색 순서)
                box[y, x] = 159 if f < 0.45 else 101 if f < 0.65 else 99 if f < 0.85 else 96
            elif (y > 0 and x > 0 and it[y - 1, x - 1]) or (x > 0 and it[y, x - 1]) or (y > 0 and it[y - 1, x]):
                box[y, x] = 16                              # 오른쪽·아래 테두리
    unpanel(cells, MONEY_CELL0, MONEY_W, MONEY_H, p)
    return cells.reshape(-1).tobytes()


def preview():
    from PIL import Image
    sys.path.insert(0, HERE)
    import lzss
    g = open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    cs, ds = struct.unpack_from('<II', g, BLOCK)
    data, _ = lzss.decode(g, BLOCK + 8, ds)
    new = np.frombuffer(build(data), np.uint8).reshape(-1, 8, 8)
    a = panel(new, MENU_CELL0, MENU_W, MENU_H); b = panel(new, MONEY_CELL0, MONEY_W, MONEY_H)
    canvas = np.zeros((96, 48 + 8 + 128), np.uint8)
    canvas[:, :48] = a; canvas[:32, 56:] = b
    Image.fromarray(np.stack([canvas] * 3, 2) * 1).resize((canvas.shape[1] * 4, 96 * 4), 0).save(os.path.join(ROOT, 'work', 'uigfx_preview.png'))


if __name__ == '__main__':
    preview()
