# -*- coding: utf-8 -*-
r"""첫 장면 PoC — 겨울 마을 대사 4개(블록 0xAF67C 메시지 2)를 한글로
  1) 한글 음절 → 어느 글에도 안 쓰인 제2수준 한자 SJIS 코드(0xE040‥)를 빌림, 그 칸 글리프를 갈무리14 로 덮음
     글꼴 칸 = (앞바이트-0x81)×189 + (뒤바이트-0x40) + 64 (앞바이트 ≥0xE0 은 -0x40), 주소 = 0x254C000 + 칸×32 (16×16 1bpp)
  2) 풀린 블록에서 원문 바이트를 한글 바이트로 바꾸고 오프셋 표를 옮김(표는 정렬 안 됨 — 값마다 옮긴다)
  3) LZSS 재압축(tools/lzss_enc.py) — 다음 블록 전까지 들어가야 한다
  4) 트랙 1 섹터 교체 + MODE1 EDC/ECC(tools/cdmode1.py) → work/out/
  python tools/poc.py [--write]
"""
import os, re, shutil, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lzss, lzss_enc, aecode, bdf, cdmode1, extract

SRC_DIR = r'C:\claude\roms\ss\AnEarth Fantasy Stories - The First Volume (Japan)'
BASE = 'AnEarth Fantasy Stories - The First Volume (Japan)'
OUT_DIR = os.path.join(ROOT, 'work', 'out')
GAME_LBA = 120
FONT = 0x254C000
GALMURI = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri14.bdf'

BLOCK, NEXT = 0xAF67C, 0xAFD78
LINE_MAX = 11
LINES = [
    ('うう‥寒い寒い\\nこう冷えこんじゃあ\\nたまらねえよな', '으으‥ 추워 추워\\n이리 추워서야\\n못 견디겠군'),
    ('あんたも歳だからねえ\\n心臓とまんないように\\n気をつけたほうがいいよ', '당신도 나이가 있으니\\n심장 멎지 않게\\n조심해야지'),
    ('そのくらいで\\nマーシュが死ぬかしら', '그 정도로\\n마슈가 죽겠어？'),
    ('きゃははは‥\\n酔って転んで頭うっても\\n大丈夫だもんね', '꺄하하하‥\\n취해 넘어져 머리\\n박아도 끄떡없어'),
    # 화자 이름표 = 같은 블록의 짧은 메시지 `%04 07`(노랑) 이름 `\` `%04 0f`
    ('{c:07}マーシュ\\n{c:0f}', '{c:07}마슈\\n{c:0f}'),
    ('{c:07}オリベラ\\n{c:0f}', '{c:07}오리베라\\n{c:0f}'),
    ('{c:07}リンダ\\n{c:0f}', '{c:07}린다\\n{c:0f}'),
    ('{c:07}ユキ\\n{c:0f}', '{c:07}유키\\n{c:0f}'),
    ('{c:07}グレゴリー爺さん\\n{c:0f}', '{c:07}그레고리 영감\\n{c:0f}'),
    ('{c:07}マクガイア\\n{c:0f}', '{c:07}맥가이어\\n{c:0f}'),
    ('{c:07}シスターマリア\\n{c:0f}', '{c:07}시스터 마리아\\n{c:0f}'),
    ('{c:07}忍者\\n{c:0f}', '{c:07}닌자\\n{c:0f}'),
]


def cell(code):
    lead, tr = code >> 8, code & 0xFF
    L = lead - 0x81 if lead < 0xA0 else lead - 0x81 - 0x40
    return L * 189 + (tr - 0x40) + 64


def used_codes():
    used = set()
    for fn in ('script.tsv', 'game_plain.tsv', 'battle.tsv'):
        p = os.path.join(ROOT, 'work', 'text', fn)
        for l in open(p, encoding='utf-8'):
            if l.startswith('#'):
                continue
            t = l.split('\t')[1] if fn == 'script.tsv' else l.split('\t')[2]
            for ch in t:
                try:
                    b = ch.encode('cp932')
                except UnicodeEncodeError:
                    continue
                if len(b) == 2:
                    used.add(b[0] << 8 | b[1])
    return used


def donors(n, used):
    out = []
    for lead in range(0xE0, 0xEB):
        for tr in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
            c = lead << 8 | tr
            try:
                ch = bytes([lead, tr]).decode('cp932')
            except UnicodeDecodeError:
                continue
            if c not in used and len(ch) == 1:
                out.append(c)
                if len(out) == n:
                    return out
    raise SystemExit('빌릴 칸 부족')


def enc_ko(t, m):
    out = b''
    t = t.replace(' ', '　')                           # 반각 공백 대신 전각(렌더러 미확인)
    i = 0
    while i < len(t):
        if t.startswith('\\n', i):
            out += b'\x5c'; i += 2; continue
        mc = re.match(r'\{c:([0-9a-f]{2})\}', t[i:])
        if mc:
            out += b'\x25\x04' + bytes([int(mc.group(1), 16)]); i += mc.end(); continue
        ch = t[i]
        out += struct.pack('>H', m[ch]) if ch in m else ch.encode('cp932')
        i += 1
    return out


def glyph(F, ch):
    pts, _ = F.draw(ch)
    xs = [x for x, _ in pts]; ys = [y for _, y in pts]
    a = np.zeros((16, 16), np.uint8)
    ox = (16 - (max(xs) - min(xs) + 1)) // 2 - min(xs)
    oy = (16 - (max(ys) - min(ys) + 1)) // 2 - min(ys)
    for x, y in pts:
        if 0 <= x + ox < 16 and 0 <= y + oy < 16:
            a[y + oy, x + ox] = 1
    return np.packbits(a).tobytes()


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    g = bytearray(open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read())
    orig = bytes(g)
    sylls = sorted({c for _, ko in LINES for c in ko if '가' <= c <= '힣'})
    m = dict(zip(sylls, donors(len(sylls), used_codes())))
    F = bdf.Font(GALMURI)
    for ch, code in m.items():
        o = FONT + cell(code) * 32
        g[o:o + 32] = glyph(F, ch)
    cs, ds = struct.unpack_from('<II', g, BLOCK)
    out, _ = lzss.decode(g, BLOCK + 8, ds)
    out = bytearray(out)
    t0 = struct.unpack_from('<I', out, 0)[0]
    tbl = list(struct.unpack_from('<%dI' % (t0 // 4), out, 0))
    for jp, ko in LINES:                               # 원문 위치는 추출기 표기로 찾는다(탁음 히라가나는 SJIS 2B — «じ»=82B6)
        hit = [(a + s0, a + e0) for _, a, b in extract.messages(bytes(out))
               for s0, e0, t in extract.runs(bytes(out[a:b])) if t == jp]
        assert len(hit) == 1, (jp, hit)
        pos, end = hit[0]
        # ★초상화 대화창 한 줄 = 11칸(원문 줄 길이 분포의 벼랑, 넘치면 엔진이 멈춤 없이 다음 박스로 넘긴다)
        for ln in re.sub(r'\{[^}]*\}', '', ko).split('\\n'):
            assert len(ln) <= LINE_MAX, ('줄 폭 초과', ln, len(ln))
        kb = enc_ko(ko, m)
        out[pos:end] = kb
        d = len(kb) - (end - pos)
        tbl = [v + d if v > pos else v for v in tbl]
        struct.pack_into('<%dI' % len(tbl), out, 0, *tbl)   # 다음 줄 찾기가 새 경계를 쓰도록 바로 반영
    struct.pack_into('<%dI' % len(tbl), out, 0, *tbl)
    enc = lzss_enc.encode_best(bytes(out))
    room = NEXT - (BLOCK + 8)
    print('음절 %d · 풀림 %d → %d · 압축 %d / 자리 %d' % (len(sylls), ds, len(out), len(enc), room))
    if len(enc) > room:
        raise SystemExit('⛔ 압축본이 자리를 넘는다 %d' % (len(enc) - room))
    struct.pack_into('<II', g, BLOCK, len(enc), len(out))
    g[BLOCK + 8:BLOCK + 8 + len(enc)] = enc
    g[BLOCK + 8 + len(enc):NEXT] = bytes(NEXT - BLOCK - 8 - len(enc))
    if '--write' not in sys.argv:
        print('예행 끝 — 쓰려면 --write'); return
    os.makedirs(OUT_DIR, exist_ok=True)
    t1 = os.path.join(OUT_DIR, BASE + ' (Track 1).bin')
    shutil.copyfile(os.path.join(SRC_DIR, BASE + ' (Track 1).bin'), t1)
    n = 0
    with open(t1, 'r+b') as fh:
        for k in range(0, len(g), 2048):
            if g[k:k + 2048] != orig[k:k + 2048]:
                lba = GAME_LBA + k // 2048
                fh.seek(lba * 2352); sec = bytearray(fh.read(2352))
                sec[16:16 + 2048] = g[k:k + 2048]
                fh.seek(lba * 2352); fh.write(cdmode1.fix(sec)); n += 1
    for tr in (2, 3, 4):
        dst = os.path.join(OUT_DIR, BASE + ' (Track %d).bin' % tr)
        if not os.path.exists(dst):
            shutil.copyfile(os.path.join(SRC_DIR, BASE + ' (Track %d).bin' % tr), dst)
    shutil.copyfile(os.path.join(SRC_DIR, BASE + '.cue'), os.path.join(OUT_DIR, BASE + '.cue'))
    print('섹터 %d개 교체 → %s' % (n, OUT_DIR))


if __name__ == '__main__':
    main()
