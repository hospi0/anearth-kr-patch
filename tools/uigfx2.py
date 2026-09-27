# -*- coding: utf-8 -*-
r"""구운 UI 그림 2 — (2026-09-27 실기 «메뉴 하나씩 더 있고 룩솔도 하나 더»)
  A) 선택된 메뉴 항목의 밝은 판 = VDP1 스프라이트 32×16 8bpp ×5, 블록 0x2484EF4(풀림 2560, 순서 設定·状態·装備·魔法·道具)
     글자 49, 배경 56‥61 → 설정·상태·장비·마법·도구. 자리 776 B(원래 775) — 빠듯
  B) 상점 금액 칸 «ルクソル» = 블록 0x2D76C(VDP2 셀 0xF02+n) 셀 0x43‥0x46(윗줄)·0x47‥0x4A(아랫줄) 32×16
     배경 23, 몸통 36(흰)→51(회) 그라데이션, 테두리 59‥62 → «룩솔»
  python tools/uigfx2.py → my files/그래픽/메뉴선택_*.png · 상점룩솔_*.png
"""
import collections, os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bdf

HL_BLOCK, HL_SLOT = 0x2484EF4, 776
HL_LABELS = ['설정', '상태', '장비', '마법', '도구']
SHOP_BLOCK = 0x2D76C
FB = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11-Bold.bdf'
F14 = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri14.bdf'


def mask(F, s, w, h):
    pts = []; x = 0
    for ch in s:
        p, adv = F.draw(ch)
        pts += [(px + x, py) for px, py in p]; x += adv or 12
    m = np.zeros((h, w), np.uint8)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ox = (w - (max(xs) - min(xs) + 1)) // 2 - min(xs); oy = (h - (max(ys) - min(ys) + 1)) // 2 - min(ys)
    for px, py in pts:
        if 0 <= px + ox < w and 0 <= py + oy < h:
            m[py + oy, px + ox] = 1
    return m


def build_hl(data):
    d = np.frombuffer(data, np.uint8).copy()
    F = bdf.Font(FB)
    for k, s in enumerate(HL_LABELS):
        lab = d[k * 512:(k + 1) * 512].reshape(16, 32)
        box = lab[2:14, 2:30]
        for y in range(box.shape[0]):                      # 글자(49) → 같은 줄 배경
            row = [v for v in box[y] if v != 49]
            fill = collections.Counter(row).most_common(1)[0][0] if row else 58
            box[y][box[y] == 49] = fill
        m = mask(F, s, 28, 12)
        box[m == 1] = 49
        d[k * 512:(k + 1) * 512] = lab.reshape(-1)
    return d.tobytes()


def build_shop(data):
    d = np.frombuffer(data, np.uint8).copy()
    cells = d.reshape(-1, 8, 8)
    p = np.vstack([np.hstack([cells[0x43 + c] for c in range(4)]), np.hstack([cells[0x47 + c] for c in range(4)])])
    p[:] = 23
    m = mask(bdf.Font(F14), '룩솔', 26, 14)
    it = np.zeros((16, 32), np.uint8)
    for y in range(14):
        sh = (14 - y) // 3
        for x in range(26):
            if m[y, x] and x + sh + 1 < 32:
                it[y + 1, x + sh + 1] = 1
    rows = [y for y in range(16) if it[y].any()]
    top, bot = min(rows), max(rows)
    grad = [36, 38, 40, 43, 45, 47, 49, 51]
    for y in range(16):
        for x in range(32):
            if it[y, x]:
                p[y, x] = grad[min(len(grad) - 1, (y - top) * len(grad) // max(1, bot - top + 1))]
            elif (x > 0 and it[y, x - 1]) or (y > 0 and it[y - 1, x]) or (y > 0 and x > 0 and it[y - 1, x - 1]):
                p[y, x] = 61
    for c in range(4):
        cells[0x43 + c] = p[0:8, c * 8:(c + 1) * 8]
        cells[0x47 + c] = p[8:16, c * 8:(c + 1) * 8]
    return cells.reshape(-1).tobytes()


def pal_of(state):
    s = open(os.path.join(ROOT, 'work', state), 'rb').read()
    cram = bytearray(s[0x37CDAA:0x37CDAA + 0x1000]); cram[0::2], cram[1::2] = cram[1::2], cram[0::2]
    cw = struct.unpack('>2048H', bytes(cram))
    return np.array([[(cw[i] & 31) * 8, ((cw[i] >> 5) & 31) * 8, ((cw[i] >> 10) & 31) * 8] for i in range(256)], np.uint8)


if __name__ == '__main__':
    import lzss
    from PIL import Image
    g = open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    D = os.path.join(ROOT, 'my files', '그래픽')
    cs, ds = struct.unpack_from('<II', g, HL_BLOCK); a, _ = lzss.decode(g, HL_BLOCK + 8, ds)
    b = build_hl(a)
    pal = pal_of('st3.bin')
    for nm, src in (('원본', a), ('한글', b)):
        im = np.vstack([np.frombuffer(src, np.uint8)[i * 512:(i + 1) * 512].reshape(16, 32) for i in range(5)][::-1])
        Image.fromarray(pal[im]).resize((32 * 6, 80 * 6), 0).save(os.path.join(D, '메뉴선택_%s.png' % nm))
    import lzss_enc
    print('선택판 압축', len(lzss_enc.encode_cached(b)), '/', HL_SLOT)
    cs, ds = struct.unpack_from('<II', g, SHOP_BLOCK); a, _ = lzss.decode(g, SHOP_BLOCK + 8, ds)
    b = build_shop(a)
    pal = pal_of('st_룩솔.bin')
    for nm, src in (('원본', a), ('한글', b)):
        c = np.frombuffer(src, np.uint8).reshape(-1, 8, 8)
        im = np.vstack([np.hstack([c[0x43 + k] for k in range(4)]), np.hstack([c[0x47 + k] for k in range(4)])])
        Image.fromarray(pal[im]).resize((32 * 8, 16 * 8), 0).save(os.path.join(D, '상점룩솔_%s.png' % nm))
