# -*- coding: utf-8 -*-
r"""세이브 화면 구운 글자 — (2026-09-27 실기 «세이브 그래픽 찾고 넣자», my files/새 폴더/세이브.state)
  찾은 법: 세이브스테이트 VDP1 명령 표(0x220 72×16 @(104,16) / 0x240 112×16 @(192,16), 8bpp) + VDP2 NBG1 이름 표(2워드, 256색)
  A) «本体RAM» 탭 72×16 8bpp — 블록 0x24884D8(→VDP1 0x5D780): 선택(초록) 4장(반짝임) 0x000‥0x1200 + «カートリッジRAM» 흐린 판 0x1200
     블록 0x2488CAC(→VDP1 0x5F088): «本体RAM» 흐린 판 0x000 + «カートリッジRAM» 선택 4장 0x480‥
     초록 = 테두리 103 · 채움 106(가장자리 104·105) · 바탕 줄마다 156→151 / 흐린 = 146 · 149(148) · 바탕 153→148(1픽셀 오른쪽 아래로 눌림)
     «RAM» 은 그대로 두고 한자·가나 자리만 바꾼다: 本体 x5‥31 → 본체, カートリッジ x3‥68 → 카트리지
  B) «L・Rで切り替え» — 블록 0x245A46C(→VDP2 0x40000, 256색 셀, 그림 폭 32셀) 셀 13‥23(윗줄)·45‥54(아랫줄), 팔레트 256+
     글자 테두리 65 · 채움 66(밝음)→70(어두움) · 바탕 무늬 = 셀 1‥4 / 33‥36 반복 → «L·R 로 전환»
  python tools/savegfx.py → my files/그래픽/세이브탭_*.png · 세이브LR_*.png
"""
import collections, os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bdf

TAB_A, TAB_B, LR_BLOCK = 0x24884D8, 0x2488CAC, 0x245A46C
FB = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11-Bold.bdf'
F11 = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.bdf'
HON = ('본체', 72)                # 글자·폭 — 지우는 칸·R 위치는 TAB_GEOM
CART = ('카트리지', 112)
# (탭, 흐린 판?) → (지울 x 시작, 끝, R 왼쪽 테두리 x) — 한글 끝 테두리는 R-2 까지(한 칸 띄움, 사용자 2026-09-27 «어두운 쪽처럼 한 칸 띄워»)
#   ★초록 本体 판의 R 왼쪽 테두리는 x31 — 지우는 범위에 넣으면 R 이 잘린다(사용자 실기 지적)
TAB_GEOM = {('본체', False): (5, 31, 31), ('본체', True): (6, 33, 33),
            ('카트리지', False): (3, 73, 73), ('카트리지', True): (4, 75, 75)}


def mask(F, s, w, h, gap=0, pad=None):
    """pad = {글자: 앞뒤 여백 픽셀} — «·» 가 L·R 에 딱 붙는다(사용자 지적) → 앞뒤 2픽셀"""
    pts = []; x = 0
    for ch in s:
        e = (pad or {}).get(ch, 0)
        x += e
        p, adv = F.draw(ch)
        pts += [(px + x, py) for px, py in p]; x += (adv or 12) + gap + e
    m = np.zeros((h, w), np.uint8)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ox = (w - (max(xs) - min(xs) + 1)) // 2 - min(xs); oy = (h - (max(ys) - min(ys) + 1)) // 2 - min(ys)
    for px, py in pts:
        if 0 <= px + ox < w and 0 <= py + oy < h:
            m[py + oy, px + ox] = 1
    return m


def ring(m):
    """글자 둘레 1픽셀(8방향)"""
    h, w = m.shape; r = np.zeros_like(m)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            s = np.zeros_like(m)
            s[max(0, dy):h + min(0, dy), max(0, dx):w + min(0, dx)] = m[max(0, -dy):h - max(0, dy), max(0, -dx):w - max(0, dx)]
            r |= s
    return r & (1 - m)


def tab_frame(f, spec, F):
    """탭 한 장(16×W) — 한자·가나 자리를 줄 바탕으로 지우고 한글(테두리·채움)을 R 앞 한 칸 띄워 그린다"""
    s, W = spec
    f = f.reshape(16, W).copy()
    grey = f[0, 0] == 50                                # 흐린 판: 1픽셀 오른쪽 아래로 눌려 있다
    ex0, ex1, rx = TAB_GEOM[(s, bool(grey))]
    y0, y1, bx = (2, 15, 3) if grey else (1, 14, 2)
    if grey:
        outline, fill = 146, 149                        # 흐린 판은 채움 149 가 바탕 줄 색과 같아 세지 못한다
    else:
        txt = [v for v in f[y0:y1, ex0:ex1].ravel().tolist() if v not in set(f[y0:y1, bx].tolist())]
        c = collections.Counter(txt).most_common()
        outline, fill = sorted([c[0][0], c[1][0]])      # 테두리 103 < 채움 106
    for y in range(y0, y1):
        f[y, ex0:ex1] = f[y, bx]
    m = mask(F, s, 80, y1 - y0 - 2, gap=1)
    cols = np.nonzero(m.any(0))[0]; m = m[:, cols.min():cols.max() + 1]
    big = np.zeros((y1 - y0, m.shape[1] + 2), np.uint8); big[1:-1, 1:-1] = m
    rg = ring(big)
    ox = rx - 1 - big.shape[1]                          # 마지막 테두리 열 = R-2
    for y in range(big.shape[0]):
        for x in range(big.shape[1]):
            if big[y, x]:
                f[y0 + y, ox + x] = fill
            elif rg[y, x]:
                f[y0 + y, ox + x] = outline
    return f.reshape(-1)


def build_tabs(a, b):
    """a = 블록 0x24884D8, b = 블록 0x2488CAC (풀린 자료) → 새 자료 둘"""
    F = bdf.Font(FB)
    a = np.frombuffer(a, np.uint8).copy(); b = np.frombuffer(b, np.uint8).copy()

    def cart(buf, o, hon, grey):
        f = tab_frame(buf[o:o + 1792], CART, F).reshape(16, 112)
        h = hon.reshape(16, 72)                         # 같은 판(초록 i / 흐린)의 원본 本体 탭 «RAM» — 줄 바탕도 같다
        if grey:                                        # ジ 탁점이 R 윗줄에 겹쳐 있어 RAM 을 本体 판에서 다시 복사
            f[2:15, 75:109] = h[2:15, 33:67]
        else:
            f[1:14, 73:108] = h[1:14, 31:66]
        buf[o:o + 1792] = f.reshape(-1)

    for i in range(4):
        orig = a[i * 1152:(i + 1) * 1152].copy()
        cart(b, 1152 + i * 1792, orig, False)
        a[i * 1152:(i + 1) * 1152] = tab_frame(orig, HON, F)
    orig = b[0:1152].copy()
    cart(a, 0x1200, orig, True)
    b[0:1152] = tab_frame(orig, HON, F)
    return a.tobytes(), b.tobytes()


LR_TOP, LR_BOT, LR_N = 13, 45, 11
GRAD = [66, 66, 67, 67, 67, 68, 68, 68, 69, 69, 70, 70, 70]


def build_lr(data):
    d = np.frombuffer(data, np.uint8).copy()
    c = d.reshape(-1, 8, 8)
    p = np.zeros((16, 8 * LR_N), np.uint8)
    for k in range(LR_N):                               # 바탕 무늬 되살리기(셀 1‥4 / 33‥36 반복)
        p[0:8, k * 8:k * 8 + 8] = c[1 + k % 4]
        p[8:16, k * 8:k * 8 + 8] = c[33 + k % 4]
    bg = collections.Counter(p[p < 64].tolist()).most_common(1)[0][0]
    p[p >= 64] = bg                                     # 바탕 무늬 셀에 섞인 글자색 점(오른쪽 아래 «찌꺼기», 사용자 지적) 지우기
    m = mask(bdf.Font(F11), 'L·R 로 전환', 8 * (LR_N - 1) - 2, 13, pad={'·': 2})     # 사용자 문구(2026-09-27)
    big = np.zeros((15, 8 * (LR_N - 1)), np.uint8); big[1:14, 1:-1] = m
    rg = ring(big)
    rows = [y for y in range(15) if big[y].any()]; top = min(rows)
    for y in range(15):
        for x in range(big.shape[1]):
            if big[y, x]:
                p[y, x] = GRAD[min(len(GRAD) - 1, y - top)]
            elif rg[y, x]:
                p[y, x] = 65
    for k in range(LR_N):
        c[LR_TOP + k] = p[0:8, k * 8:k * 8 + 8]
        if k < LR_N - 1:                                # 아랫줄 마지막 칸은 화면에서 바탕 셀(32)을 쓴다
            c[LR_BOT + k] = p[8:16, k * 8:k * 8 + 8]
    c[32] = c[35]           # 셀 32(화면 아랫줄 끝, NBG1 한 곳에서만 씀) = 바탕 셀 35 + «え» 꼬리 → 꼬리 지우기(사용자 «점 찌꺼기»)
    return c.reshape(-1).tobytes()


def pal_of(state):
    s = open(os.path.join(ROOT, 'work', state), 'rb').read()
    cram = bytearray(s[0x37CDAA:0x37CDAA + 0x1000]); cram[0::2], cram[1::2] = cram[1::2], cram[0::2]
    cw = struct.unpack('>2048H', bytes(cram))
    return np.array([[(cw[i] & 31) * 8, ((cw[i] >> 5) & 31) * 8, ((cw[i] >> 10) & 31) * 8] for i in range(2048)], np.uint8)


if __name__ == '__main__':
    import lzss
    from PIL import Image
    g = open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    D = os.path.join(ROOT, 'my files', '그래픽')
    dec = lambda o: lzss.decode(g, o + 8, struct.unpack_from('<II', g, o)[1])[0]
    a0, b0 = dec(TAB_A), dec(TAB_B)
    a1, b1 = build_tabs(a0, b0)
    pal = pal_of('stsave.bin')
    for nm, a, b in (('원본', a0, b0), ('한글', a1, b1)):
        A = np.frombuffer(a, np.uint8); B = np.frombuffer(b, np.uint8)
        hon = [A[i * 1152:(i + 1) * 1152].reshape(16, 72) for i in range(4)] + [B[:1152].reshape(16, 72)]
        cart = [B[1152 + i * 1792:1152 + (i + 1) * 1792].reshape(16, 112) for i in range(4)] + [A[0x1200:0x1200 + 1792].reshape(16, 112)]
        rows = [np.hstack([h, np.zeros((16, 8), np.uint8), c]) for h, c in zip(hon, cart)]
        im = np.vstack([np.vstack([r, np.zeros((2, r.shape[1]), np.uint8)]) for r in rows])
        Image.fromarray(pal[im]).resize((im.shape[1] * 5, im.shape[0] * 5), 0).save(os.path.join(D, '세이브탭_%s3.png' % nm))
    l0 = dec(LR_BLOCK); l1 = build_lr(l0)
    for nm, src in (('원본', l0), ('한글', l1)):
        c = np.frombuffer(src, np.uint8).reshape(-1, 8, 8)
        im = np.vstack([np.hstack([c[LR_TOP + k] for k in range(LR_N)]), np.hstack([c[LR_BOT + k] if k < LR_N - 1 else c[32] for k in range(LR_N)])])
        Image.fromarray(pal[im.astype(int) + 256]).resize((im.shape[1] * 6, 16 * 6), 0).save(os.path.join(D, '세이브LR_%s6.png' % nm))
    import lzss_enc
    for nm, o, new in (('탭A', TAB_A, a1), ('탭B', TAB_B, b1), ('LR', LR_BLOCK, l1)):
        print(nm, '압축', len(lzss_enc.encode_cached(new)), '/ 원래', struct.unpack_from('<I', g, o)[0])
