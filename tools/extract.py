# -*- coding: utf-8 -*-
r"""대본 추출 → work/text/script.tsv  (열: 번호 · JP · KO)
  대본 블록 = GAME.PRG LZSS 블록(tools/scanblocks.py 목록 work/blocks_game.txt) 중 «u32 LE 오프셋 표 + 스크립트» 꼴.
  메시지 = 표의 칸. 본문 뽑기 두 틀:
    대사: `%\n 01 XX`(0x25 0x0A 0x01 화자) 뒤 ‥ `@`(0x40) 앞
    서술: `%L XX 00 03 00`(0x25 0x4C + 4B) 뒤 ‥ `%M`(0x25 0x4D) 앞
  본문 표기: 히라가나(반각 1B → 히라가나로 읽음, tools/aecode.py) · SJIS · `\` 줄바꿈 ·
            `{name:XXXX}` = %00 + u16(이름 끼움) · `{c:XX}` = %04 + 1B(색) · 그 밖 바이트 `{xx}`
  번호 = 블록오프셋:메시지:조각
  python tools/extract.py
"""
import os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lzss, aecode

GAME = os.path.join(ROOT, 'work', 'GAME.PRG')


def is_script(out):
    if len(out) < 16:
        return False
    t0 = struct.unpack_from('<I', out, 0)[0]
    if not (8 <= t0 < len(out) and t0 % 4 == 0):
        return False
    tbl = struct.unpack_from('<%dI' % (t0 // 4), out, 0)
    if any(not (t0 <= v <= len(out)) for v in tbl):      # ★표는 정렬돼 있지 않다(0xAF67C 블록 — 겨울 마을이 빠졌던 이유)
        return False
    body = out[t0:]
    return body.count(b'%') >= 5 and sum(1 for b in body if 0xA6 <= b <= 0xDD) >= 10   # 50 은 짧은 대본(보물 문구 0x7C3590 = 49)을 놓쳤다


def messages(out):
    """(표 칸 번호, 시작, 끝) — 표 값을 정렬한 경계로 자른다. 같은 오프셋을 가리키는 칸은 첫 칸 번호로 한 번만"""
    t0 = struct.unpack_from('<I', out, 0)[0]
    tbl = list(struct.unpack_from('<%dI' % (t0 // 4), out, 0))
    bounds = sorted(set(tbl)) + [len(out)]
    first = {}
    for k, v in enumerate(tbl):
        first.setdefault(v, k)
    return [(first[bounds[j]], bounds[j], bounds[j + 1]) for j in range(len(bounds) - 1)]


def render(b):
    """본문 바이트 → 표기"""
    s, i = [], 0
    while i < len(b):
        x = b[i]
        if x == 0x25 and i + 3 < len(b) + 1 and b[i + 1] == 0x00:
            s.append('{name:%02x%02x}' % (b[i + 2], b[i + 3])); i += 4; continue
        if x == 0x25 and i + 2 < len(b) + 1 and b[i + 1] == 0x04:
            s.append('{c:%02x}' % b[i + 2]); i += 3; continue
        if x == 0x5C:
            s.append('\\n'); i += 1; continue
        if 0xA1 <= x <= 0xDF:
            s.append(aecode.dec(bytes([x]))); i += 1; continue
        if (0x81 <= x <= 0x9F or 0xE0 <= x <= 0xEF) and i + 1 < len(b):
            try:
                c = b[i:i + 2].decode('cp932')
                if len(c) == 1 and c.encode('cp932') == b[i:i + 2]:
                    s.append(c); i += 2; continue
            except UnicodeDecodeError:
                pass
        s.append('{%02x}' % x); i += 1
    # 탁음 합치기(반각 ﾞﾟ 가 따로 읽힌 경우)
    return ''.join(s)


TXT = rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]|[\xa1-\xdf\x5c]|\x25\x00..|\x25\x04.)'
# ★본문 글자만 허용 — 느슨한 .*? 는 여러 메시지·명령을 삼켰다(2026-09-26 사용자 «제대로 추출이 하나도 안됨»)
RUN_OLD = re.compile(rb'\x25\x0a\x01.(' + TXT + rb'+)\x40|\x25\x4c....(' + TXT + rb'*)\x25\x4d', re.S)
# 틀이 여럿이라(%05 XX · %0a 00/04 XX 뒤, 메시지 첫머리, 가운데 %14 기다림 …) «본문 글자가 이어지는 구간» 전부를 뽑는다.
#   명령 인수가 우연히 글자로 읽히는 것을 막으려고 가나·한자가 2자 이상인 구간만.
RUN = re.compile(rb'(' + TXT + rb'+)', re.S)
REAL = re.compile(r'[ぁ-んァ-ヶ一-龥々]')


# 본문 앞에 자주 오는 명령의 인수 길이(바이트) — 인수가 글자로 읽혀 본문에 붙는 것을 막는다(«そウパウパ…» = 화자 0xBF)
ARGLEN = {0x0a: 2, 0x05: 1, 0x01: 2, 0x03: 2, 0x4c: 4, 0x14: 5, 0x73: 1, 0x4b: 1, 0x81: 1, 0x35: 3, 0x37: 2, 0x5d: 3, 0x49: 1, 0x59: 1, 0x44: 1,
          0x3d: 1, 0x39: 3, 0x3c: 3, 0x75: 4, 0x30: 1, 0x13: 4, 0x32: 6, 0x06: 5}


# 문장 한가운데 끼는 명령(조각 사이 틈 통계, 2026-09-26): 기다림 %14+5B · %05+1B · 낱말 끼움 %01/%03+2B · 창 %0a+2B
INLINE = {0x14: 5, 0x05: 1, 0x01: 2, 0x03: 2, 0x0a: 2}


def inline_gap(gap):
    """틈이 INLINE 명령으로만 되어 있으면 표기 문자열, 아니면 None"""
    out, i = [], 0
    while i < len(gap):
        if gap[i] == 0x25 and i + 1 < len(gap) and gap[i + 1] in INLINE and i + 2 + INLINE[gap[i + 1]] <= len(gap):
            n = INLINE[gap[i + 1]]
            out.append('{%02x:%s}' % (gap[i + 1], gap[i + 2:i + 2 + n].hex())); i += 2 + n
        else:
            return None
    return ''.join(out)


def runs(m):
    """본문 구간(시작, 끝, 표기) — INLINE 명령만 끼인 이웃 구간은 합친다"""
    merged = []
    for s, e, t in runs_raw(m):
        if merged:
            ps, pe, pt = merged[-1]
            g = inline_gap(m[pe:s])
            if g is not None and s - pe <= 24:
                merged[-1] = (ps, e, pt + g + t); continue
        merged.append((s, e, t))
    return merged


def runs_raw(m):
    for mm in RUN.finditer(m):
        s, e = mm.start(1), mm.end(1)
        if s > 0 and m[s - 1] == 0x25:                  # «%» 바로 뒤 = 연산 바이트(«%86» 등) — 본문 아님
            s += 1
        for back in range(2, 8):                       # 바로 앞 «% op 인수…» 가 구간 안까지 뻗으면 시작을 민다
            p = s - back
            if p >= 0 and m[p] == 0x25 and m[p + 1] in ARGLEN and p + 2 + ARGLEN[m[p + 1]] > s:
                s = p + 2 + ARGLEN[m[p + 1]]
                break
        if s >= e:
            continue
        t = render(m[s:e])
        if keep(t):
            yield s, e, t


SHORT = re.compile(r'[‥！？ー、。…Ａ-Ｚ０-９]')


def keep(t):
    """본문 판정 — 가나·한자 2자 이상, 또는 짧은 말(«ん‥‥？» «‥‥ッ！！» «５歳» «ＨＯＬＩＸ»)
    ★2자 기준만 쓰면 짧은 대사·아이템 분류 라벨이 빠졌다(2026-09-26). 명령 인수(1바이트)는 부호가 안 붙으므로 걸러진다."""
    if re.search(r'\{[0-9a-f]{2}\}', t):
        return False
    body = re.sub(r'\{[^}]*\}|\\n', '', t)
    n = len(REAL.findall(body))
    if n >= 2:
        return True
    return len(body) >= 2 and len(SHORT.findall(body)) >= 1 and (n >= 1 or len(SHORT.findall(body)) == len(body.replace('　', '')))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    g = open(GAME, 'rb').read()
    rows, odd = [], 0
    for l in open(os.path.join(ROOT, 'work', 'blocks_game_all.txt')):
        off, cs, ds, _ = l.split(); off = int(off, 16); ds = int(ds)
        out, _ = lzss.decode(g, off + 8, ds)
        if not is_script(out):
            continue
        for k, a, b in messages(out):
            m = out[a:b]
            for n, (s0, e0, t) in enumerate(runs(m)):
                if re.search(r'\{[0-9a-f]{2}\}', t):
                    odd += 1
                rows.append(('%06x:%d:%d' % (off, k, n), t))
    os.makedirs(os.path.join(ROOT, 'work', 'text'), exist_ok=True)
    with open(os.path.join(ROOT, 'work', 'text', 'script.tsv'), 'w', encoding='utf-8') as f:
        f.write('#블록:메시지:조각\tJP\tKO\n')
        for r in rows:
            f.write('%s\t%s\t\n' % r)
    chars = sum(len(re.sub(r'\{[^}]*\}|\\n', '', t)) for _, t in rows)
    print('rows', len(rows), 'chars', chars, 'rows with unknown bytes', odd)


if __name__ == '__main__':
    main()
