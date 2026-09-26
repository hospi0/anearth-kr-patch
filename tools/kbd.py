# -*- coding: utf-8 -*-
r"""이름 입력 한글 자판
  구조(2026-09-27 역어셈블):
    · 글자판 칸 번호 → 1바이트 반각 코드(0x0603FAC8: 0‥37 → 0xB1+번호 = ｱ‥ﾖ, 40‥44 → ﾗ‥ﾛ, 46‥49 → ｬ‥ｯ …, 55 = ゛, 56 = ゜)
      이름 버퍼 0x0601BDF0(1바이트). ゛ 는 ｶ‥ﾄ·ｳ·ﾊ‥ﾎ(0x0605E050 목록) 뒤, ゜ 는 ﾊ‥ﾎ(0x0605E068) 뒤에만.
    · 대사 렌더러 0x0602900C: {name}(끝 바이트 00 = 주인공) 만 «가타카나 표»(GAME 0x3A8DC, 반각 0xA1‥0xDD → SJIS) 로 그린다.
      ﾞ 가 뒤따르면 SJIS +1, ﾟ 면 +2 → 칸도 +1·+2.
    · 화면 그림 = LZSS 블록 0x4506814(64KB, 8bpp 셀, 16×16 글자 = 2×2 셀, 한 줄 16글자) → VDP2 0x40000.
  한글화:
    · 가타카나 표를 «이름 전용 음절 칸»(제2수준 E047‥, 코드마다 3칸: 기본·ㄴ받침·ㅇ받침)으로 돌린다.
    · ゛ 버튼 = ㄴ받침, ゜ 버튼 = ㅇ받침(원래 탁음이 붙던 글자 자리에만 받침형을 그린다).
    · 화면 그림: 자판 글자 → 한글, «あなたの名前は？» → «당신의 이름은？», 戻る → 뒤로, 決定 → 결정, ゛゜ → ㄴㅇ.
  python tools/kbd.py   → work/kbd_preview.png (확인용)
"""
import os, struct, sys, unicodedata
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bdf

BLOCK = 0x4506814
KATA_TABLE = 0x3A8DC
NAME_LISTS = (0x3DFE0, 0x3FB5C)     # 이름 입력 화면 윗줄 표시용 SJIS 가타카나 목록(ｦ‥ﾝ 56칸) — 실기 «ホヤァ»
NAME_MAX = 0x1F760                  # `CMP/EQ #8,R0` — 이름 글자 수 한계(ﾞﾟ 제외하고 셈)
NAME_LEN = 4                        # 한글 4자(사용자 결정) — 대사 흘리기도 이름 자리를 4칸으로 친다(boxes.TOKW)
NAME_BASE = 0xE047                 # 이름 음절 칸 시작(코드마다 3칸)
F14 = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri14.bdf'
F9 = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri9.bdf'
F7P = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri7.bdf'

# 가타카나(자판 칸) → (기본, ㄴ받침, ㅇ받침) — 받침형은 원래 탁음·반탁음이 붙던 글자에만
VOICE_N = 'ウカキクケコサシスセソタチツテト'          # ゛ 가능(ㄴ받침)
VOICE_NO = 'ハヒフヘホ'                               # ゛゜ 가능(ㄴ·ㅇ받침)
# 세이브·상태 화면 작은 글꼴(tools/smallfont.py)은 ｱ‥ﾘ(0xB1‥0xD8) 칸만 글자가 있다(나머지 칸은 다른 그림)
#   → 자주 쓰는 음절은 앞(IN, 작은 글꼴에도 나옴), 드문 음절은 뒤(OUT, 세이브 화면에선 원래 게임처럼 제대로 안 나옴)
PLAIN_IN = 'アイエオナニヌネノマミムメモヤユヨラリ'
PLAIN_OUT = 'ワヲルレロンャュョッァィゥェォー'
PLAIN = PLAIN_IN + PLAIN_OUT
S_N = '가무미비사소수시오우유이저지차후'
S_NO = '서여조주하'
S_PLAIN = '강김나노리박상석송스심아안임장정최카피' + '경남류배백양용원재철태허혁홍황희'   # ★하·스·피 필수(사용자 이름 «하스피»)
MUST = '하스피'
assert all(c in S_N + S_NO + S_PLAIN[:len(PLAIN_IN)] for c in MUST), '자판에 하·스·피 필수(작은 글꼴에도 나오는 칸에)'
assert len(VOICE_N) == len(S_N) and len(VOICE_NO) == len(S_NO) and len(PLAIN) == len(S_PLAIN), (len(PLAIN), len(S_PLAIN))


def jong(s, j):
    """받침 붙이기 (j = 4 ㄴ / 21 ㅇ)"""
    c = ord(s) - 0xAC00
    return chr(0xAC00 + (c // 28) * 28 + j)


def kata_code(k):
    """전각 가타카나 → 반각 코드"""
    h = unicodedata.normalize('NFKC', k) if False else None
    table = 'ｦｧｨｩｪｫｬｭｮｯｰｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ'
    full = 'ヲァィゥェォャュョッーアイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワン'
    return 0xA6 + full.index(k)


def name_map():
    """반각 코드 → (기본, ㄴ형|None, ㅇ형|None), 자판 가타카나 → 기본 음절"""
    m = {}; by_kana = {}
    for k, s in zip(VOICE_N, S_N):
        m[kata_code(k)] = (s, jong(s, 4), None); by_kana[k] = s
    for k, s in zip(VOICE_NO, S_NO):
        m[kata_code(k)] = (s, jong(s, 4), jong(s, 21)); by_kana[k] = s
    for k, s in zip(PLAIN, S_PLAIN):
        m[kata_code(k)] = (s, None, None); by_kana[k] = s
    return m, by_kana


# 화면 그림의 글자 칸 번호(16×16, 한 줄 16칸)
SHEET = {}
for i, k in enumerate('アイウエオカキクケコ'):
    SHEET[k] = 1 + i
for i, k in enumerate('サシスセソタチツテト'):
    SHEET[k] = 16 + i
for i, k in enumerate('ナニヌネノハヒフヘホ'):
    SHEET[k] = 32 + i
for i, k in enumerate('マミムメモヤユヨワン'):
    SHEET[k] = 48 + i
for i, k in enumerate('ラリルレロャュョッ'):
    SHEET[k] = 64 + i
for i, k in enumerate('ァィゥェォー'):
    SHEET[k] = 80 + i
SHEET['ヲ'] = 97
LABELS = {11: '뒤', 12: '로', 13: '결', 14: '정',
          88: '당', 89: '신', 90: '의', 91: '　', 92: '이', 93: '름', 94: '은', 95: '？'}


def tile_rc(t):
    return (t // 16) * 16, (t % 16) * 16                # 픽셀 좌표(그림 256 폭)


def draw_glyph(F, ch, w=16, h=16):
    a = np.zeros((h, w), np.uint8)
    if ch.strip('　') == '':
        return a
    pts, _ = F.draw(ch)
    if not pts:
        return a
    xs = [x for x, _ in pts]; ys = [y for _, y in pts]
    ox = (w - 1 - (max(xs) - min(xs) + 1)) // 2 - min(xs)
    oy = (h - 1 - (max(ys) - min(ys) + 1)) // 2 - min(ys)
    for x, y in pts:
        if 0 <= x + ox < w and 0 <= y + oy < h:
            a[y + oy, x + ox] = 1
    return a


def style(mask):
    """흰 본체(15) + 오른쪽 아래 1픽셀 그림자(1) — 원래 글자 그림과 같은 규칙"""
    h, w = mask.shape
    out = np.zeros((h, w), np.uint8)
    sh = np.zeros_like(mask); sh[1:, 1:] = mask[:-1, :-1]
    out[(sh == 1) & (mask == 0)] = 1
    out[mask == 1] = 15
    return out


def build_sheet(data):
    """64KB 8bpp 셀 자료 → 한글 그림으로 바꾼 64KB"""
    a = np.frombuffer(data, np.uint8).copy()
    cells = a.reshape(-1, 8, 8); cols = 32; rows = len(cells) // cols
    im = cells.reshape(rows, cols, 8, 8).transpose(0, 2, 1, 3).reshape(rows * 8, cols * 8).copy()
    F = bdf.Font(F14); F9f = bdf.Font(F9)
    _, by_kana = name_map()
    todo = dict((SHEET[k], s) for k, s in by_kana.items())
    todo.update(LABELS)
    for t, ch in todo.items():
        y, x = tile_rc(t)
        im[y:y + 16, x:x + 16] = style(draw_glyph(F, ch))
    # ゛·゜ = 8×8 셀 32번(゛)·33번(゜) (타일 0 의 아래 두 셀). ★셀 0 은 화면 빈 곳이 쓰는 빈 셀 — 절대 건드리지 말 것
    #   (2026-09-27 셀 0 에 «ㄴ» 을 그려 이름 화면 전체에 세로 점선이 생겼다)
    F7 = bdf.Font(F7P)
    for cidx, ch in ((1, 'ㄴ'), (33, 'ㅇ')):          # 실기: ゛ 버튼 = 셀 1, ゜ 버튼 = 셀 33 (셀 32 는 안 씀)
        y, x = (cidx // 32) * 8, (cidx % 32) * 8
        im[y:y + 8, x:x + 8] = style(draw_glyph(F7, ch, 8, 8))
    out = im.reshape(rows, 8, cols, 8).transpose(0, 2, 1, 3).reshape(-1)
    return out.tobytes(), im


def name_cells():
    """[(SJIS 코드, 음절)] — 이름 음절 칸, 반각 코드 → 가타카나 표 값"""
    m, _ = name_map()
    cells = []; table = {}
    for i, code in enumerate(sorted(m)):
        base = NAME_BASE + 3 * i
        table[code] = base
        for k, s in enumerate(m[code]):
            if s:
                cells.append((base + k, s))
    return cells, table


def preview():
    from PIL import Image
    data = open(os.path.join(ROOT, 'work', 'kbd_tiles.bin'), 'rb').read()
    _, im = build_sheet(data)
    sub = im[:112, :256]
    pal = np.zeros((256, 3), np.uint8); pal[15] = (255, 255, 255); pal[1] = (60, 60, 120)
    for v in (4, 5, 6, 8, 9, 10, 12, 14):
        pal[v] = (180, 180, 180)
    Image.fromarray(pal[sub]).resize((256 * 3, 112 * 3), 0).save(os.path.join(ROOT, 'work', 'kbd_preview.png'))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    m, bk = name_map()
    print('자판 음절', len(bk), '받침형', sum(1 for v in m.values() for s in v[1:] if s))
    preview()
