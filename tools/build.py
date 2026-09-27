# -*- coding: utf-8 -*-
r"""AnEarth Fantasy Stories - The First Volume 한글 빌더
  1) 글꼴(GAME.PRG 0x254C000, 16×16 1bpp, 칸 = SJIS 189칸/앞바이트) — work/charmap.tsv 의 음절을 갈무리14 로 그림
     1바이트 코드(0xA1‥0xDD)는 변환표(0x3A956)가 가리키는 칸에 그린다. 。「」、・ー 6칸은 표를 제2수준 한자 칸으로 돌린다.
  2) 대본(script.tsv) — 블록마다 번역 넣기(boxes.layout 로 창 폭·줄 수 맞춤) → 오프셋 표 옮기기 → LZSS 최적 압축(캐시)
     → 묶음(같은 포인터 표) 안에서 차례로 다시 채우고 포인터 고침. 첫 블록은 안 움직인다.
  3) 평문(game_plain.tsv · battle.tsv) — 제자리(원문 바이트 예산, 이름표 구역은 NUL 채움 칸까지). S 줄(전투 SJIS)은 1바이트 금지·남는 칸 전각 공백.
  4) 트랙 1 섹터 교체 + MODE1 EDC/ECC → work/out/   (--install 이면 F: 에도)
  ★규칙은 쓰는 순간 강제(kenc: 부호 뒤 반각 공백 삭제·반각→전각·글꼴 밖 글자 오류, boxes: 창 폭·줄 수, 예산 초과 = 오류)
  python tools/build.py [--write] [--install]
"""
import hashlib, os, re, shutil, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lzss, lzss_enc, extract, kenc, charmap, boxes, groups, scriptfit, ko, bdf, cdmode1, kbd, bytestyle, choices, uigfx, smallfont, uigfx2, savegfx, bookgfx, josa

SRC_DIR = r'C:\claude\roms\ss\AnEarth Fantasy Stories - The First Volume (Japan)'
BASE = 'AnEarth Fantasy Stories - The First Volume (Japan)'
INSTALL = r'F:\hospi\roms\ss roms\AnEarth Fantasy Stories - The First Volume (Japan)'
OUT_DIR = os.path.join(ROOT, 'work', 'out')
LBA = {'GAME.PRG': 120, 'BATTLE.PRG': 36472}
FONT = 0x254C000
GALMURI = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri14.bdf'
COPY_GLYPH = {'　': None, '‥': 0x8164, '！': 0x8149, '？': 0x8148, '（': 0x8169, '）': 0x816A}
# 이름표 구역 — 문자열 뒤 NUL 채움까지 써도 된다(4바이트 정렬 칸, 2026-09-27 확인)
PADDED = [('G', 0x16300, 0x16340), ('G', 0x1E230, 0x1E270), ('B', 0xCF30, 0xCF60), ('B', 0x24A00, 0x24E00)]


def cell(code):
    lead, tr = code >> 8, code & 0xFF
    L = lead - 0x81 if lead < 0xA0 else lead - 0x81 - 0x40
    return L * 189 + (tr - 0x40) + 64


def glyph(F, ch):
    pts, _ = F.draw(ch)
    a = np.zeros((16, 16), np.uint8)
    if pts:
        xs = [x for x, _ in pts]; ys = [y for _, y in pts]
        ox = (16 - (max(xs) - min(xs) + 1)) // 2 - min(xs)
        oy = (16 - (max(ys) - min(ys) + 1)) // 2 - min(ys)
        for x, y in pts:
            if 0 <= x + ox < 16 and 0 <= y + oy < 16:
                a[y + oy, x + ox] = 1
    return np.packbits(a).tobytes()


def build_font(g, orig):
    m = charmap.load()
    kt = kenc.kana_table(orig)
    for c, tgt in charmap.ONE_REMAP.items():                      # 변환표 6칸 돌리기
        struct.pack_into('>H', g, kenc.KANA_TABLE + 2 * (c - 0xA1), tgt)
    F = bdf.Font(GALMURI)
    n = 0
    for ch, code in m.items():
        tgt = kt[code] if code < 0x100 else code
        o = FONT + cell(tgt) * 32
        if ch in COPY_GLYPH:
            src = COPY_GLYPH[ch]
            g[o:o + 32] = bytes(32) if src is None else orig[FONT + cell(src) * 32:FONT + cell(src) * 32 + 32]
        else:
            g[o:o + 32] = glyph(F, ch)
        n += 1
    return n


def build_script(g, orig):
    tr = scriptfit.by_block()
    keys = boxes.run_keys(orig, scriptfit.blocks(), tr)
    B = boxes.load()
    stats = {'블록': 0, '다시흘림': 0, '옮긴 블록': 0, '선택지': 0}
    errs = []
    CH = choices.find(orig)                                     # 선택지: 항목 폭(%56) 맞춤 — 흘리기 대신
    for grp, start, end in groups.groups(orig):
        if not any(b[0] in tr for b in grp):
            continue
        pos = start; seg = []
        for i, (off, cs, ds, q, d) in enumerate(grp):
            if off in tr:
                out, _ = lzss.decode(orig, off + 8, ds)
                P = scriptfit.positions(out)
                t2 = {}; keep = set()
                for k, text in tr[off].items():
                    rid = '%06x:%s' % (off, k)
                    text = josa.resolve(text, orig)             # 아이템 이름 끼움 뒤 «을(를)» → 받침 따라 을/를(tools/josa.py)
                    text = josa.resolve_lead(text, out[max(0, P[k][0] - 16):P[k][0]], orig)   # 끼움이 조각 바로 앞에 있는 경우
                    if '{c:07}' in text:
                        t2[k] = text; continue
                    if rid in CH and '\\n' not in text:
                        cnt, w = CH[rid]
                        vis = len(re.sub(r'\{[^}]*\}', '', text))
                        f = text if vis == cnt * w else choices.fit(text, cnt, w)
                        if f is None:
                            errs.append('선택지 %s 항목 %d×%d칸에 안 맞음: %s' % (rid, cnt, w, text)); f = text
                        t2[k] = f; keep.add(k); stats['선택지'] += 1
                        continue
                    jp = P[k][2]
                    f = choices.refit(jp, text) if rid not in CH else None
                    if f:                                       # 들여쓰기+줄 폭 선택지(%05 ff %07 %56) — 원문 꼴대로 채움
                        t2[k] = f; keep.add(k); stats['선택지'] += 1
                        continue
                    if text == jp:                             # 번역 안 한 줄(디버그 «ＭＡＰ０１…» 등) — 원문 그대로
                        t2[k] = text; continue
                    W, H = boxes.size(B, keys.get(rid), text, jp)
                    new, st = boxes.layout(text, jp, W, H)
                    if st == 'fail':
                        raise SystemExit('⛔ 창에 안 들어감 %s: %s' % (rid, text))
                    if st == 'rewrap':
                        stats['다시흘림'] += 1
                    t2[k] = new
                new = scriptfit.rebuild(out, t2, keep)
                enc = lzss_enc.encode_cached(new)
                blob = struct.pack('<II', len(enc), len(new)) + enc
                stats['블록'] += 1
                seg.append('%x' % off)
            else:
                # ★대본 아닌 블록(그림 등)은 절대 안 움직인다 — 다른 곳이 주소로 부를 수 있다(2026-09-27 방어구점 그림 사라짐)
                if pos > off:
                    errs.append('묶음 %x: 고정 블록 %x 앞 대본 %s 넘침 %d' % (start, off, ' '.join(seg), pos - off))
                    pos = off
                g[pos:off] = bytes(off - pos)
                seg = []
                g[off:off + 8 + cs] = orig[off:off + 8 + cs]
                pos = (off + 8 + cs + 3) & ~3
                continue
            if i == 0:
                assert pos == off
            elif pos != off:
                struct.pack_into('>I', g, q, (pos + d) & 0xFFFFFFFF)
                stats['옮긴 블록'] += 1
            g[pos:pos + len(blob)] = blob
            e = pos + len(blob)
            pos = (e + 3) & ~3
            g[e:pos] = bytes(pos - e)                                # 정렬 틈 0
        if pos > end:
            errs.append('묶음 %x 끝: 대본 %s 넘침 %d' % (start, ' '.join(seg), pos - end))
            continue
        # 남는 자리 0 채움(원래 블록 뒤 찌꺼기 방지) — 마지막 블록 끝 ~ 자리 끝
        last_end = pos
        g[last_end:end] = bytes(end - last_end)
    if errs:
        raise SystemExit('⛔ 자리 넘침 %d곳 — ' % len(errs) + ' / '.join(errs))
    return stats


# 코드 안에 SJIS 상수로 박힌 글자(문자열 추출에 안 걸림) — (GAME.PRG 위치, 원래 코드, 한글)
CODE_CHARS = [(0x1110E, 0x8CC2, '개')]      # 상점 수량 «１個»(실기 «1녹» — 個 칸이 한글 칸이 됨, 2026-09-27)


def build_code_chars(g, orig):
    m = charmap.load(); kt = kenc.kana_table(orig)
    for off, old, ch in CODE_CHARS:
        assert struct.unpack_from('>H', orig, off)[0] == old
        c = m[ch]
        struct.pack_into('>H', g, off, kt[c] if c < 0x100 else c)
    return len(CODE_CHARS)


def build_uigfx(g, orig):
    """구운 UI 그림(메뉴 라벨·금액 «룩솔», tools/uigfx.py) — 블록 0x2454018 제자리(사용자 «완벽해» 2026-09-27)"""
    cs, ds = struct.unpack_from('<II', orig, uigfx.BLOCK)
    data, _ = lzss.decode(orig, uigfx.BLOCK + 8, ds)
    new = uigfx.build(data)
    enc = lzss_enc.encode_cached(new)
    if len(enc) > uigfx.SLOT:
        raise SystemExit('⛔ UI 그림 자리 넘침 %d > %d' % (len(enc), uigfx.SLOT))
    g[uigfx.BLOCK:uigfx.BLOCK + 8 + uigfx.SLOT] = struct.pack('<II', len(enc), len(new)) + enc + bytes(uigfx.SLOT - len(enc))
    return len(enc)


def build_smallfont(g, orig):
    """세이브·상태 화면 이름 작은 글꼴(tools/smallfont.py) — 블록 0x24566F0 제자리 + 받침형 칸 코드 패치"""
    cs, ds = struct.unpack_from('<II', orig, smallfont.BLOCK)
    data, _ = lzss.decode(orig, smallfont.BLOCK + 8, ds)
    new, _ = smallfont.build(data)
    new = bookgfx.build(new)                                    # 같은 블록의 마법책 주문 이름(힐링·언록·서치·텔레포트, 진한/흐린 판)
    GFX[smallfont.BLOCK] = new
    enc = lzss_enc.encode_cached(new)
    if len(enc) > cs:
        raise SystemExit('⛔ 작은 글꼴 블록 자리 넘침 %d > %d' % (len(enc), cs))
    g[smallfont.BLOCK:smallfont.BLOCK + 8 + cs] = struct.pack('<II', len(enc), len(new)) + enc + bytes(cs - len(enc))
    for off, old, nw in smallfont.PATCH:
        assert struct.unpack_from('>H', orig, off)[0] == old
        struct.pack_into('>H', g, off, nw)
    return len(enc), cs


GFX = {}        # 그림 단계가 바꾼 블록 → 새 풀림(verify 가 원본 대신 이것과 비교)


def inplace(g, orig, off, fn, slot=None, name=''):
    """압축 블록 하나를 제자리에서 바꾼다 — 자리 = slot(다음 자료까지 잰 값) 또는 원래 압축 크기"""
    cs, ds = struct.unpack_from('<II', orig, off)
    data, _ = lzss.decode(orig, off + 8, ds)
    new = fn(data)
    assert len(new) == ds, (name, len(new), ds)
    enc = lzss_enc.encode_cached(new)
    room = slot or cs
    if len(enc) > room:
        raise SystemExit('⛔ %s 그림 자리 넘침 %d > %d' % (name, len(enc), room))
    g[off:off + 8 + room] = struct.pack('<II', len(enc), len(new)) + enc + bytes(room - len(enc))
    GFX[off] = new
    return '%s %d/%d' % (name, len(enc), room)


def build_gfx2(g, orig):
    """2026-09-27 사용자 판정 받은 구운 그림: 선택된 메뉴 라벨·상점 «룩솔»(uigfx2) · 세이브 탭·«L·R 로 전환»(savegfx)
       (마법책 주문 이름은 작은 글꼴과 같은 블록 — build_smallfont 에서)"""
    res = [inplace(g, orig, uigfx2.HL_BLOCK, uigfx2.build_hl, uigfx2.HL_SLOT, '선택 메뉴'),
           inplace(g, orig, uigfx2.SHOP_BLOCK, uigfx2.build_shop, None, '상점 룩솔'),
           inplace(g, orig, savegfx.LR_BLOCK, savegfx.build_lr, None, 'L·R')]
    da = lzss.decode(orig, savegfx.TAB_A + 8, struct.unpack_from('<II', orig, savegfx.TAB_A)[1])[0]
    db = lzss.decode(orig, savegfx.TAB_B + 8, struct.unpack_from('<II', orig, savegfx.TAB_B)[1])[0]
    na, nb = savegfx.build_tabs(da, db)
    res.append(inplace(g, orig, savegfx.TAB_A, lambda d: na, None, '세이브 탭A'))
    res.append(inplace(g, orig, savegfx.TAB_B, lambda d: nb, None, '세이브 탭B'))
    return ' · '.join(res)


def build_kbd(g, orig):
    """이름 입력 한글 자판(tools/kbd.py): 가타카나 표 → 이름 음절 칸, 음절 칸 그리기, 화면 그림 블록 제자리 교체"""
    cells, table = kbd.name_cells()
    F = bdf.Font(GALMURI)
    for code, s in cells:
        o = FONT + cell(code) * 32
        g[o:o + 32] = glyph(F, s)
    by = {s: c for c, s in cells}
    table[0xA1] = by['카']                                  # 기본 이름 «카심»(대사 표 1바이트 카 = 0xA1)
    for c, v in table.items():
        struct.pack_into('>H', g, kbd.KATA_TABLE + 2 * (c - 0xA1), v)
        if c >= 0xA6:
            for L in kbd.NAME_LISTS:                            # 이름 화면 윗줄 표시 목록
                assert 0x8140 <= struct.unpack_from('>H', orig, L + 2 * (c - 0xA6))[0] <= 0x8396   # 가타카나·ー
                struct.pack_into('>H', g, L + 2 * (c - 0xA6), v)
    # 이름 최대 글자 수 8 → 4 (0x0603F760 `CMP/EQ #8,R0` — 0x0603FA38 가 ﾞﾟ(받침 버튼)를 빼고 센 글자 수, 사용자 결정 2026-09-27)
    assert bytes(orig[kbd.NAME_MAX:kbd.NAME_MAX + 2]) == bytes([0x88, 0x08])
    g[kbd.NAME_MAX:kbd.NAME_MAX + 2] = bytes([0x88, kbd.NAME_LEN])
    cs, ds = struct.unpack_from('<II', orig, kbd.BLOCK)
    data, _ = lzss.decode(orig, kbd.BLOCK + 8, ds)
    new, _ = kbd.build_sheet(data)
    enc = lzss_enc.encode_cached(new)
    room = 9656                                             # 다음 블록(0x4508DD4) 전까지
    if len(enc) > room:
        raise SystemExit('⛔ 자판 그림 자리 넘침 %d > %d' % (len(enc), room))
    g[kbd.BLOCK:kbd.BLOCK + 8 + room] = struct.pack('<II', len(enc), len(new)) + enc + bytes(room - len(enc))
    return len(cells)


def verify(g, orig):
    """결과 검사: 묶음마다 포인터를 따라가 블록 머리 → 풀기 → 소비 바이트 = 압축 크기, 대본이면 표·본문 판정, 아니면 원본과 같은 내용"""
    tr = scriptfit.by_block()
    bad = 0; n = 0
    for grp, start, end in groups.groups(orig):
        if not any(b0[0] in tr for b0 in grp):
            continue
        for i, (off, cs, ds, q, d) in enumerate(grp):
            at = off if i == 0 else (struct.unpack_from('>I', g, q)[0] - d) & 0xFFFFFFFF
            ncs, nds = struct.unpack_from('<II', g, at)
            out, e = lzss.decode(g, at + 8, nds)
            ok = len(out) == nds and e - (at + 8) == ncs and start <= at and at + 8 + ncs <= end
            if off in tr:                                       # 표 구조로 판정(가나 개수 기준은 한글화 뒤 짧은 블록에서 떨어진다 — 0x19EDFBC)
                t0 = struct.unpack_from('<I', out, 0)[0] if len(out) >= 4 else 0
                ok = ok and 8 <= t0 < len(out) and t0 % 4 == 0 and \
                    all(t0 <= v <= len(out) for v in struct.unpack_from('<%dI' % (t0 // 4), out, 0)) and out[t0:].count(b'%') >= 5
            else:
                ok = ok and out == GFX.get(off, lzss.decode(orig, off + 8, ds)[0])
            n += 1
            if not ok:
                bad += 1; print('⛔ 검사 실패', hex(off), '→', hex(at))
    if bad:
        raise SystemExit('⛔ 검사 실패 %d' % bad)
    return n


def room(d, off, n):
    e = off + n
    while e < len(d) and d[e] == 0:
        e += 1
    return e - off - 1


def build_plain(g, b, orig):
    kt = kenc.kana_table(orig)
    cnt = 0
    for name in ('game_plain.tsv', 'battle.tsv'):
        for r in ko.rows(name):
            if not r['ko']:
                continue
            tag = r['id'][0]; off = int(r['id'][1:], 16)
            d = g if tag == 'G' else b
            sj = tag == 'S' or not bytestyle.has_one_byte(bytes(d[off:off + r['budget']]))   # 원문이 2바이트뿐이면 2바이트만
            kb = kenc.enc(r['ko'], sjis_only=sj, kt=kt, keep_space=kenc.is_fixed(r['jp']))
            cap = r['budget']
            if any(t == ('B' if tag in 'BS' else 'G') and a <= off < z for t, a, z in PADDED):
                cap = max(cap, room(d, off, r['budget']))
            if len(kb) > cap:
                raise SystemExit('⛔ 예산 초과 %s %d > %d: %s' % (r['id'], len(kb), cap, r['ko']))
            if sj:                                              # 전투 SJIS 대사: 남는 칸 = 전각 공백(+홀수면 0x20)
                pad = r['budget'] - len(kb)
                kb += b'\x81\x40' * (pad // 2) + b' ' * (pad % 2)
                d[off:off + len(kb)] = kb
            else:
                span = max(r['budget'], len(kb))
                d[off:off + span] = kb + bytes(span - len(kb))
            cnt += 1
    return cnt


def write_disc(files, origs, install):
    os.makedirs(OUT_DIR, exist_ok=True)
    t1 = os.path.join(OUT_DIR, BASE + ' (Track 1).bin')
    shutil.copyfile(os.path.join(SRC_DIR, BASE + ' (Track 1).bin'), t1)
    n = 0
    with open(t1, 'r+b') as fh:
        for name, data in files.items():
            o = origs[name]
            for k in range(0, len(data), 2048):
                if data[k:k + 2048] != o[k:k + 2048]:
                    lba = LBA[name] + k // 2048
                    fh.seek(lba * 2352); sec = bytearray(fh.read(2352))
                    chunk = bytes(data[k:k + 2048]); chunk += bytes(2048 - len(chunk))
                    sec[16:16 + 2048] = chunk
                    fh.seek(lba * 2352); fh.write(cdmode1.fix(sec)); n += 1
    for tr in (2, 3, 4):
        dst = os.path.join(OUT_DIR, BASE + ' (Track %d).bin' % tr)
        if not os.path.exists(dst):
            shutil.copyfile(os.path.join(SRC_DIR, BASE + ' (Track %d).bin' % tr), dst)
    shutil.copyfile(os.path.join(SRC_DIR, BASE + '.cue'), os.path.join(OUT_DIR, BASE + '.cue'))
    h = hashlib.md5(open(t1, 'rb').read()).hexdigest().upper()
    print('섹터 %d개 교체 → %s  md5 %s' % (n, t1, h))
    if install:
        shutil.copyfile(t1, os.path.join(INSTALL, BASE + ' (Track 1).bin'))
        print('설치 →', INSTALL)
    return h


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    og = open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    ob = open(os.path.join(ROOT, 'work', 'BATTLE.PRG'), 'rb').read()
    g = bytearray(og); b = bytearray(ob)
    charmap.build()                                             # 새 음절만 뒤에 붙는다
    kenc._map = None
    print('글꼴', build_font(g, og), '칸')
    print('대본', build_script(g, og))
    print('평문', build_plain(g, b, og), '줄')
    print('자판 음절 칸', build_kbd(g, og))
    print('코드 속 글자', build_code_chars(g, og))
    print('UI 그림 압축', build_uigfx(g, og), '/', uigfx.SLOT)
    print('이름 작은 글꼴·마법책 압축', build_smallfont(g, og))
    print('그림2', build_gfx2(g, og))
    print('검사 통과 블록', verify(g, og))
    if '--write' in sys.argv:
        write_disc({'GAME.PRG': g, 'BATTLE.PRG': b}, {'GAME.PRG': og, 'BATTLE.PRG': ob}, '--install' in sys.argv)
    else:
        print('예행 끝 — 쓰려면 --write')


if __name__ == '__main__':
    main()
