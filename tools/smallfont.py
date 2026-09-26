# -*- coding: utf-8 -*-
r"""이름용 작은 글꼴(8×8) 한글 — 세이브·상태 화면의 주인공 이름
  구조(2026-09-27 역어셈블 0x06036380): 이름 1바이트 코드 → 작은 글꼴 칸 R8
    보통 가나 R8 = 코드−0x60 · ﾞ 붙음 R8 = 코드−0x30 · ﾟ 붙음 R8 = 코드−0x4A · 숫자·영문 R8 = 코드−0x20
  글꼴 = UI 블록 0x24566F0(64KB 8bpp → VDP2 0x20000) 의 0xDBC0 + R8×64 (ア = R8 0x51 확인).
    ※ R8 0x89 이상(ﾞﾟ 받침형 대부분)은 블록 끝(0x10000)을 넘는다 — 다른 블록에서 오는 자리(미확인)
  모양: 7×7 글자, 줄마다 색 159·159·102·101·99·97·97, 오른쪽 아래 그림자 144.
  python tools/smallfont.py → my files/그래픽/세이브이름_*.png
"""
import os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bdf, kbd

BLOCK = 0x24566F0
BASE = 0xDBC0
F7 = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri7.bdf'
GRAD = [159, 159, 102, 101, 99, 97, 97]


def glyph7(F, ch):
    pts, _ = F.draw(ch)
    m = np.zeros((7, 7), np.uint8)
    if not pts:
        return m
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ox = (7 - (max(xs) - min(xs) + 1)) // 2 - min(xs)
    oy = (7 - (max(ys) - min(ys) + 1)) // 2 - min(ys)
    for x, y in pts:
        if 0 <= x + ox < 7 and 0 <= y + oy < 7:
            m[y + oy, x + ox] = 1
    return m


def cell(F, ch):
    m = glyph7(F, ch)
    c = np.zeros((8, 8), np.uint8)
    for y in range(7):
        for x in range(7):
            if m[y, x]:
                c[y, x] = GRAD[y]
    for y in range(8):
        for x in range(8):
            if c[y, x] == 0 and ((y > 0 and x > 0 and m[y - 1, x - 1] if y - 1 < 7 and x - 1 < 7 else 0) or (x > 0 and y < 7 and x - 1 < 7 and m[y, x - 1]) or (y > 0 and x < 7 and y - 1 < 7 and m[y - 1, x])):
                c[y, x] = 144
    return c


GLYPH_R8 = range(0x51, 0x79)       # 작은 글꼴에 실제 글자가 있는 칸(ｱ‥ﾘ) — 나머지 칸은 다른 그림이라 ⛔덮어쓰지 말 것


def slots():
    """[(R8, 음절)] — 이름 자판 기본 음절(코드−0x60) 중 글자 칸(ｱ‥ﾘ)에 드는 것.
       받침형(ﾞ·ﾟ)은 코드 패치(PATCH)로 기본 칸을 쓰게 한다(세이브 화면에서 «한» → «하»)"""
    m, _ = kbd.name_map()
    return [(code - 0x60, b) for code, (b, n, o) in sorted(m.items()) if code - 0x60 in GLYPH_R8]


# 받침형도 기본 칸으로(0x06036380 함수): ﾞ → R8 = 코드−0x60, ﾟ → 코드−0x60 (원래 코드−0x30·−0x4A 는 다른 그림 칸·빈 칸)
PATCH = [(0x163D6, 0x6863, 0x6833),     # ﾞ: MOV R6,R8 → MOV R3,R8
         (0x163D8, 0xE89F, 0x6833),     # ｳﾞ: MOV #0x9F,R8 → MOV R3,R8
         (0x163DA, 0xA02C, 0xA007),     # BRA 끝 → BRA 0x060363EC(ADD #0xA0,R8 거쳐 끝)
         (0x163E6, 0x78B6, 0x78A0)]     # ﾟ: ADD #0xB6,R8 → ADD #0xA0,R8


def build(data):
    d = bytearray(data)
    F = bdf.Font(F7)
    miss = []
    for r8, ch in slots():
        o = BASE + r8 * 64
        if o + 64 > len(d):
            miss.append(ch); continue
        d[o:o + 64] = cell(F, ch).tobytes()
    return bytes(d), miss


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    import lzss
    from PIL import Image
    g = open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    cs, ds = struct.unpack_from('<II', g, BLOCK)
    data, _ = lzss.decode(g, BLOCK + 8, ds)
    new, miss = build(data)
    print('블록 밖이라 못 그린 받침형', len(miss), ''.join(miss))
    s = open(os.path.join(ROOT, 'work', 'stsave.bin'), 'rb').read()
    cram = bytearray(s[0x37CDAA:0x37CDAA + 0x1000]); cram[0::2], cram[1::2] = cram[1::2], cram[0::2]
    cw = struct.unpack('>2048H', bytes(cram))
    pal = np.array([[(cw[i] & 31) * 8, ((cw[i] >> 5) & 31) * 8, ((cw[i] >> 10) & 31) * 8] for i in range(256)], np.uint8)
    for nm, src in (('원본', data), ('한글', new)):
        a = np.frombuffer(src, np.uint8)
        cells = [a[BASE + r * 64:BASE + r * 64 + 64].reshape(8, 8) for r in range(0x46, 0x7E)]
        im = np.vstack([np.hstack(cells[i:i + 14]) for i in range(0, len(cells), 14)])
        Image.fromarray(pal[im]).resize((im.shape[1] * 6, im.shape[0] * 6), 0).save(os.path.join(ROOT, 'my files', '그래픽', '세이브이름_%s.png' % nm))
    # 이름 «하스피» 예시
    m, _ = kbd.name_map()
    inv = {v[0]: k for k, v in m.items()}
    a = np.frombuffer(new, np.uint8)
    ex = np.hstack([a[BASE + (inv[c] - 0x60) * 64:BASE + (inv[c] - 0x60) * 64 + 64].reshape(8, 8) for c in '하스피'])
    Image.fromarray(pal[ex]).resize((24 * 8, 8 * 8), 0).save(os.path.join(ROOT, 'my files', '그래픽', '세이브이름_하스피.png'))
