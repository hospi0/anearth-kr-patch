# -*- coding: utf-8 -*-
r"""마법책 주문 이름 그림 — UI 블록 0x24566F0(8bpp, 셀 32칸/줄 → 256×256 그림) 안
  펼친 책(행 12‥23) 4개 + 아래 띠(행 26‥29) 4개: ヒーリング·アンロック·サーチ·テレポート → 힐링·언록·서치·텔레포트
  (번역표 game_plain 과 같은 이름). 영문(HEALING 등)은 둔다.
  글자 = 진한 129 + 가장자리 130‥135, 배경 = 칸 안에서 가장 흔한 값. 가타카나 자리를 배경으로 지우고 한글을 129 로.
"""
import collections, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bdf

FB = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11-Bold.bdf'
# (x0, x1, y0, y1, 한글) — 그림 좌표(256×256)
LABELS = [(12, 82, 121, 136, '힐링'), (100, 168, 121, 136, '언록'),
          (18, 70, 161, 175, '서치', 1), (100, 168, 161, 175, '텔레포트', 1),   # 사용자: 너무 위 → 2픽셀 내림 → «한 도트 올려» → 1픽셀
            # 영문 SEARCH·TELEPORT 는 152‥159 — 건드리지 말 것
          (55, 127, 207, 223, '힐링'), (128, 197, 207, 223, '언록'),
          (68, 118, 224, 240, '서치'), (127, 200, 224, 240, '텔레포트')]


def to_img(d):
    return d.reshape(-1, 8, 8)[:1024].reshape(32, 32, 8, 8).transpose(0, 2, 1, 3).reshape(256, 256)


def from_img(im, d):
    out = bytearray(d)
    out[:65536] = im.reshape(32, 8, 32, 8).transpose(0, 2, 1, 3).reshape(-1).tobytes()
    return bytes(out)


def mask(F, s, w, h):
    pts = []; x = 0
    for ch in s:
        p, adv = F.draw(ch)
        pts += [(px + x, py) for px, py in p]
        x += adv or 12
    m = np.zeros((h, w), np.uint8)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ox = (w - (max(xs) - min(xs) + 1)) // 2 - min(xs); oy = (h - (max(ys) - min(ys) + 1)) // 2 - min(ys)
    for px, py in pts:
        if 0 <= px + ox < w and 0 <= py + oy < h:
            m[py + oy, px + ox] = 1
    return m


def build(data):
    im = to_img(np.frombuffer(data, np.uint8)).copy()
    F = bdf.Font(FB)
    for lab in LABELS:
        x0, x1, y0, y1, s = lab[:5]; dy = lab[5] if len(lab) > 5 else 0
        box = im[y0:y1, x0:x1]
        bg = collections.Counter(box.ravel().tolist()).most_common(1)[0][0]
        faded = y0 >= 200                                   # 아래 띠 = 흐린 판(아직 못 얻은 주문) — 글자 133(가장자리 134·135)
        ink = 133 if faded else 129                         # 책 쪽 = 진한 판(얻은 뒤) — 129
        dark = (box >= 129) & (box <= 135) & (box != bg)
        ys, xs = np.nonzero(dark)
        if not len(ys):
            continue
        ty0, ty1, tx0, tx1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1      # 가타카나가 차지한 자리
        sub = box[ty0:ty1, tx0:tx1]
        box[ty0:ty1, tx0:tx1] = np.where((sub >= 129) & (sub <= 135), bg, sub)
        h = ty1 - ty0; w = x1 - x0 - 2
        m = mask(F, s, w, max(h, 11) + 2)                  # 한 줄 여유(«힐» 아랫줄 잘림 방지)
        oy = ty0 - (m.shape[0] - h) // 2 + dy
        for y in range(m.shape[0]):
            for x in range(m.shape[1]):
                if m[y, x] and 0 <= oy + y < box.shape[0]:
                    box[oy + y, 1 + x] = ink
                    if 1 + x + 1 < box.shape[1] and not m[y, x + 1] if x + 1 < m.shape[1] else False:
                        pass
    return from_img(im, data)


if __name__ == '__main__':
    import struct
    from PIL import Image
    import lzss
    g = open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    cs, ds = struct.unpack_from('<II', g, 0x24566F0)
    data, _ = lzss.decode(g, 0x24566F0 + 8, ds)
    new = build(data)
    s = open(os.path.join(ROOT, 'work', 'st4.bin'), 'rb').read()
    cram = bytearray(s[0x37CDAA:0x37CDAA + 0x1000]); cram[0::2], cram[1::2] = cram[1::2], cram[0::2]
    cw = struct.unpack('>2048H', bytes(cram))
    pal = np.array([[(cw[i] & 31) * 8, ((cw[i] >> 5) & 31) * 8, ((cw[i] >> 10) & 31) * 8] for i in range(256)], np.uint8)
    for nm, src in (('원본', data), ('한글', new)):
        im = to_img(np.frombuffer(src, np.uint8))[96:244, 0:210]
        Image.fromarray(pal[im]).resize((210 * 3, 148 * 3), 0).save(os.path.join(ROOT, 'my files', '그래픽', '마법책_%s2.png' % nm))
