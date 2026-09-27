# -*- coding: utf-8 -*-
r"""이름용 작은 글꼴(8×8) 한글 — 메뉴(상태)·세이브·전투 화면의 주인공 이름
  구조(역어셈블 0x06036380): 이름 1바이트 코드 → 작은 글꼴 칸 R8
    보통 가나 R8 = 코드−0x60 · ﾞ 붙음 R8 = 코드−0x30(ｳﾞ = 0x9F) · ﾟ 붙음 R8 = 코드−0x4A · 숫자·영문 R8 = 코드−0x20
  ★글꼴 = UI 블록 0x24566F0(64KB 8bpp → VDP2 0x20000) 의 **맨 앞** + R8×64 — 메뉴 스테이트(2026-09-27, my files/새 폴더/…state)
    NBG1 이름 칸 = 문자 번호 0x1000+R8×2 로 확인(ホ = R8 0x6E). 바탕 47.
    ⛔7차(2026-09-27 오전)엔 0xDBC0 쪽 다른 가나 사본을 고쳐 화면에 안 나왔다(«새로 저장해도 가타카나»).
  칸: 0x46‥0x7D 기본 가나 · 0x80‥0x84 ﾟ(パ행) · 0x86‥0x9F ﾞ — 전부 이 블록 안.
  → 기본 칸 = 기본 음절, ﾞ 칸 = ㄴ받침형, ﾟ 칸 = ㅇ받침형(kbd.name_map). 받침형 코드 패치는 필요 없다(7차 패치 철회).
  모양: 7×7 글자, 줄마다 색 159·159·102·101·99·97·97, 오른쪽 아래 그림자 144.
  python tools/smallfont.py → my files/그래픽/이름글꼴_*.png
"""
import os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bdf, kbd

BLOCK = 0x24566F0
BASE = 0
BG = 47
F7 = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri7.bdf'
GRAD = [159, 159, 102, 101, 99, 97, 97]
# ★메뉴 동료 이름(2026-09-27): 메뉴 이름 함수는 GAME 0x16300 표(포인터 목록 0x16324, 메뉴 전용)를 이 글꼴로 그린다.
#   번역 이름은 자판 코드(1바이트)로 쓰고, 자판에 없는 음절은 안 쓰던 코드 0xE0‥ → 빈 칸(✕) 0x95‥ 로.
#   코드 패치: 0x060363F8 기호 갈래의 «그 밖» 분기를 기호 점프 표 안(0x21‥0x29 칸 — 이름에 안 나옴)에 넣은 20바이트로:
#     R0=EXTU.B R3; R0>=0xE0 이면 R8=R0−0x4B(칸) → 0x06036436(칸 찍기)
EXTRA_BASE, EXTRA_CODE = 0x95, 0xE0
EXTRA = '샤올베트릴'                         # 동료 이름(카심·나샤·올가·베스트릴) 중 자판에 없는 음절 — 칸 0x95‥0x99(5칸이 전부)
MENU_NAMES = [(0x16308, 0x1630C, '카심'), (0x1630C, 0x16314, '나샤'), (0x16314, 0x1631C, '올가'), (0x1631C, 0x16324, '베스트릴')]
PATCH = [(0x163F8, 0x8D1D, 0x8D07)] + list(zip(range(0x1640A, 0x1641C, 2), [0x002E] * 9,
         [0x603C, 0xE1E0, 0x611C, 0x3012, 0x8B01, 0x6803, 0x78B5, 0xA00D, 0x0009]))
# ★저장 화면은 같은 함수의 두 번째 사본(0x0603E268, 기호 갈래 0x1E340 — 바이트 동일)과 두 번째 이름 표(0x1E230, 포인터 0x1E254)를 쓴다
#   (2026-09-27 실기: 저장 화면 동료 이름이 «혁»). 두 사본 모두 위치 무관 코드라 같은 패치를 +0x7F50 에, 표는 +0x7F30 에.
SAVE_D, SAVE_T = 0x1E340 - 0x163F0, 0x1E230 - 0x16300
PATCH += [(a + SAVE_D, o, n) for a, o, n in PATCH]
MENU_NAMES += [(a + SAVE_T, z + SAVE_T, n) for a, z, n in MENU_NAMES]


def menu_bytes(s):
    """동료 이름 → 메뉴 표 바이트(자판 코드 + ﾞﾟ / 0xE0‥)"""
    m, _ = kbd.name_map()
    inv = {}
    for code, (b, n, o) in m.items():
        inv[b] = bytes([code])
        if n:
            inv[n] = bytes([code, 0xDE])
        if o:
            inv[o] = bytes([code, 0xDF])
    out = b''
    for ch in s:
        if ch in inv:
            out += inv[ch]
        else:
            assert ch in EXTRA, '메뉴 이름 음절 %s — 자판에도 EXTRA 에도 없음' % ch
            out += bytes([EXTRA_CODE + EXTRA.index(ch)])
    return out


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
    m = np.zeros((8, 8), np.uint8); m[:7, :7] = glyph7(F, ch)
    c = np.full((8, 8), BG, np.uint8)
    sh = np.zeros_like(m); sh[1:, 1:] |= m[:-1, :-1]; sh[:, 1:] |= m[:, :-1]; sh[1:, :] |= m[:-1, :]
    c[(sh == 1) & (m == 0)] = 144
    for y in range(7):
        c[y][m[y] == 1] = GRAD[y]
    return c


def slots():
    """[(R8, 음절)] — 기본 칸 + ﾞ(ㄴ) 칸 + ﾟ(ㅇ) 칸"""
    m, _ = kbd.name_map()
    out = []
    for code, (b, n, o) in sorted(m.items()):
        out.append((code - 0x60, b))
        if n:
            out.append((0x9F if code == 0xB3 else code - 0x30, n))
        if o:
            out.append((code - 0x4A, o))
    return out


def build(data):
    d = bytearray(data)
    F = bdf.Font(F7)
    used = {}
    for r8, ch in slots():
        assert r8 not in used, ('칸 겹침', hex(r8), used.get(r8), ch)
        assert 0x46 <= r8 <= 0x9F, hex(r8)
        used[r8] = ch
        o = BASE + r8 * 64
        d[o:o + 64] = cell(F, ch).tobytes()
    for i, ch in enumerate(EXTRA):
        r8 = EXTRA_BASE + i
        assert r8 not in used and EXTRA_CODE + i - 0x4B == r8
        d[BASE + r8 * 64:BASE + r8 * 64 + 64] = cell(F, ch).tobytes()
    return bytes(d), []


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    import lzss
    from PIL import Image
    g = open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    cs, ds = struct.unpack_from('<II', g, BLOCK)
    data, _ = lzss.decode(g, BLOCK + 8, ds)
    new, _ = build(data)
    s = open(os.path.join(ROOT, 'work', 'st_menu.bin'), 'rb').read()
    cram = bytearray(s[0x37CDAA:0x37CDAA + 0x1000]); cram[0::2], cram[1::2] = cram[1::2], cram[0::2]
    cw = struct.unpack('>2048H', bytes(cram))
    pal = np.array([[(cw[i] & 31) * 8, ((cw[i] >> 5) & 31) * 8, ((cw[i] >> 10) & 31) * 8] for i in range(256)], np.uint8)
    D = os.path.join(ROOT, 'my files', '그래픽')
    for nm, src in (('원본', data), ('한글', new)):
        a = np.frombuffer(src, np.uint8)
        cells = [a[r * 64:r * 64 + 64].reshape(8, 8) for r in range(0x40, 0xA0)]
        im = np.vstack([np.hstack(cells[i:i + 16]) for i in range(0, len(cells), 16)])
        Image.fromarray(pal[im]).resize((im.shape[1] * 6, im.shape[0] * 6), 0).save(os.path.join(D, '이름글꼴_%s.png' % nm))
    m, _ = kbd.name_map()
    inv = {v[0]: k for k, v in m.items()}
    a = np.frombuffer(new, np.uint8)
    ex = np.hstack([a[(inv[c] - 0x60) * 64:(inv[c] - 0x60) * 64 + 64].reshape(8, 8) for c in '하스피'])
    Image.fromarray(pal[ex]).resize((24 * 8, 8 * 8), 0).save(os.path.join(D, '이름글꼴_하스피.png'))
    print('칸', len(slots()))
