# -*- coding: utf-8 -*-
r"""전투 말풍선 대사(동료·적 외침) — BATTLE.PRG 0x440F4‥0x457xx (2026-09-27 실기 «섞乱ッ！» = 虎乱ッ！ 미번역)
  레코드 = 포인터 표(0x2FF24‥)가 가리키는 자리부터 다음 레코드까지:
    [11 02]? <대사: SJIS · 0A 줄바꿈 · 14 xx 인라인 · 반각 ASCII> 12 <시간> 가 이어지고 0 채움(4바이트 정렬)
  → 레코드마다 번역을 넣어 다시 짜고 남는 자리는 0 (레코드 길이 안). 한글은 2바이트 코드(말풍선은 SJIS 렌더러).
  python tools/battle_shout.py extract  → work/text/battle_shout.tsv (번호=Z레코드:조각, 예산=레코드 길이)
"""
import os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

LOAD = 0x06020000
LO, HI = 0x44000, 0x45800
HEAD = bytes([0x11, 0x02])
TSV = os.path.join(ROOT, 'work', 'text', 'battle_shout.tsv')
NL = '\\n'                      # 표기 속 줄바꿈(두 글자 역슬래시 n)


def parse_text(b, p):
    """대사 바이트 → (표기, 0x12 위치)"""
    out = []
    while True:
        c = b[p]
        if c == 0x12 or c == 0x00:                      # 0x00 = 12 없이 끝나는 조각(«x15» 등)
            return ''.join(out), p
        if 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF:
            out.append(b[p:p + 2].decode('cp932')); p += 2
        elif c == 0x0A:
            out.append(NL); p += 1
        elif c in (0x14, 0x10):
            out.append('{%02x:%02x}' % (c, b[p + 1])); p += 2
        elif 0x20 <= c < 0x7F:
            out.append(chr(c)); p += 1
        elif 0xA1 <= c <= 0xDF:                         # 반각 가나(｡ 등)
            out.append(bytes([c]).decode('cp932')); p += 1
        else:
            raise ValueError('모르는 바이트 %02x @%x' % (c, p))


def records(b):
    """[(시작, 끝, [(표기, 시간, 앞에 11 02 있었나)])]"""
    tg = set()
    for i in range(0, 0x45950 - 3, 2):
        v = struct.unpack_from('>I', b, i)[0] - LOAD
        if LO <= v < HI and b[v:v + 2] == HEAD:
            tg.add(v)
    tg = sorted(tg)
    # 단위 = 0 으로 끝나는 명령 줄(시작은 고정 — 포인터·오프셋이 가리킬 수 있다). 포인터 레코드 안에도 여러 단위가 있다.
    out = []; p = tg[0]; last = tg[-1]
    while True:
        while b[p] == 0:
            p += 1
        s = p; segs = []
        while True:
            pre = b''                                    # 조각 앞 명령(첫 바이트 < 0x20 인 2바이트: 11 02 · 11 01 · 15 00 · 0A 00 · 10 10 …)
            while b[p] != 0 and b[p] < 0x20 and not (b[p] == 0x0A and b[p + 1] >= 0x20):   # «0A 글자» = 줄바꿈으로 이어지는 대사
                pre += b[p:p + 2]; p += 2
            if b[p] == 0:
                if pre:
                    segs.append((None, None, pre, b''))  # 글 없이 명령만
                break
            q = p
            t, p = parse_text(b, p)
            if b[p] == 0:
                segs.append((t, None, pre, b[q:p]))              # 12 없이 끝남
                break
            segs.append((t, b[p + 1], pre, b[q:p])); p += 2       # (표기, 시간, 앞 명령, 원래 바이트)
        e = p
        while b[e] == 0:
            e += 1
        out.append((s, e, segs))
        p = e
        if e > last:                                     # 마지막 포인터 자리를 지난 단위까지
            break
    return out


def extract():
    b = open(os.path.join(ROOT, 'work', 'BATTLE.PRG'), 'rb').read()
    R = records(b)
    old = {}
    if os.path.exists(TSV):
        for l in open(TSV, encoding='utf-8'):
            a = l.rstrip('\n').split('\t')
            if len(a) >= 4 and not l.startswith('#'):
                old[a[0]] = a[3]
    with open(TSV, 'w', encoding='utf-8') as f:
        f.write('#번호\t예산(B)\tJP\tKO\n')
        for s, e, segs in R:
            for n, (t, dur, head, raw) in enumerate(segs):
                if t is None or dur is None or not re.search(r'[ぁ-んァ-ヶ一-龥]', t):
                    continue
                rid = 'Z%05x:%d' % (s, n)
                f.write('%s\t%d\t%s\t%s\n' % (rid, e - s, t, old.get(rid, '')))
    print('레코드', len(R), '조각', sum(len(x[2]) for x in R))


TOK = re.compile(r'(\{1[04]:[0-9a-f]{2}\}|\\n|[ -~])')


def enc(t):
    """표기 → 바이트(한글·전각은 kenc 2바이트, {14:xx}·줄바꿈·반각 ASCII 는 그대로)"""
    import kenc
    out = b''
    for part in TOK.split(t):
        if not part:
            continue
        if re.fullmatch(r'\{1[04]:[0-9a-f]{2}\}', part):
            out += bytes([int(part[1:3], 16), int(part[4:6], 16)])
        elif part == NL:
            out += bytes([0x0A])
        elif len(part) == 1 and ' ' <= part <= '~':
            out += part.encode()
        else:
            out += kenc.enc(part, sjis_only=True)
    return out


def build(b):
    """b = BATTLE.PRG bytearray — 번역 있는 레코드를 다시 짠다"""
    tr = {}
    for l in open(TSV, encoding='utf-8'):
        if l.startswith('#'):
            continue
        a = l.rstrip('\n').split('\t')
        if len(a) >= 4 and a[3]:
            tr[a[0]] = a[3]
    n = 0
    for s, e, segs in records(bytes(b)):
        ids = ['Z%05x:%d' % (s, k) for k in range(len(segs))]
        if not any(i in tr for i in ids):
            continue
        rec = b''
        for i, (t, dur, head, raw) in zip(ids, segs):
            if t is None:
                rec += head; continue
            rec += head + (enc(tr[i]) if i in tr else raw) + (bytes([0x12, dur]) if dur is not None else b'')
        if len(rec) > e - s:
            raise SystemExit('⛔ 전투 말풍선 넘침 %s %d > %d: %s' % (ids[0], len(rec), e - s, [tr.get(i) for i in ids]))
        b[s:e] = rec + bytes(e - s - len(rec))
        n += 1
    return n


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if sys.argv[1:] == ['extract']:
        extract()
