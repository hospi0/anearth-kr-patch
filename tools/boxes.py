# -*- coding: utf-8 -*-
r"""대사 상자 폭·줄 수 추정 + 한국어 줄 다시 흘리기
  상자 = `%0a SS XX`(SS = 창 종류, XX = 같은 블록의 이름표 메시지 번호) 뒤 본문.
  원문 통계(2026-09-27): 초상화 있는 인물은 줄 ≤ 12칸(오르가·나샤·베스트릴 … 12 넘는 줄 0), 초상화 없는 NPC 는 16칸.
    이름표 있는 상자 = 이름 1줄 + 본문 3줄, 없는 상자 = 본문 4줄(원문 4줄 292회, 5줄 이상 거의 없음).
  ★실기(2026-09-26): 초상화 창에 13칸 줄 → 엔진이 자동 줄바꿈 → 줄이 넘쳐 다음 상자로 «기다림 없이» 넘어가 앞 상자가 사라진다.
  폭 결정 = (창 종류, 이름표) 별 원문 줄 중 12칸 넘는 비율 ≤ 5% 면 12, 아니면 16.
  python tools/boxes.py  → work/boxes.tsv(키 · 폭 · 줄 수) + 들어가지 않는 줄 보고
"""
import collections, os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lzss, extract, kenc

BS = '\\n'
PATH = os.path.join(ROOT, 'work', 'boxes.tsv')


def box_key(out, tbl, m, s):
    """본문 조각 앞의 상자 키 — '종류:이름' / '종류:-' / 'none'"""
    p = m.rfind(b'%\x0a', 0, s)
    if p < 0 or p + 3 >= len(m):
        return 'none', False
    sub, arg = m[p + 2], m[p + 3]
    nm = None
    if arg < len(tbl):
        a = tbl[arg]; mm = out[a:a + 60]
        j = mm.find(b'%\x04\x07')
        if 0 <= j <= 12:
            k = mm.find(b'\x5c', j)
            nm = extract.render(mm[j + 3:k]) if k > 0 else None
    return '%02x:%s' % (sub, nm or '-'), bool(nm)


def width(t):
    return [len(re.sub(r'\{[^}]*\}', '', x)) for x in t.split(BS)]


def learn(g, blocks, tr):
    """키 → (폭, 줄 수)"""
    L = collections.defaultdict(collections.Counter); labeled = {}
    for off, cs, ds in blocks:
        if off not in tr:
            continue
        out, _ = lzss.decode(g, off + 8, ds)
        t0 = struct.unpack_from('<I', out, 0)[0]
        tbl = struct.unpack_from('<%dI' % (t0 // 4), out, 0)
        for k, a, b in extract.messages(out):
            m = out[a:b]
            for s, e, t in extract.runs(m):
                if '{c:07}' in t:
                    continue
                key, lab = box_key(out, tbl, m, s)
                labeled[key] = lab
                if BS in t:
                    for x in width(t.rstrip(BS)):
                        L[key][x] += 1
    res = {}
    for key in labeled:
        c = L[key]; n = sum(c.values())
        over = sum(v for k, v in c.items() if k > 12)
        w = 12 if n and over <= 0.05 * n else 16
        if not n:
            w = 12                                      # 자료 없음 → 좁은 쪽
        res[key] = (w, 3 if labeled[key] else 4)
    return res


def wrap(text, W, H):
    """낱말 단위 다시 흘리기. 제어 표기({…})는 낱말에 붙여 둔다. 들어가면 새 표기, 아니면 None
       ★글자 단위로 자르지 않는다(규칙) — 낱말 하나가 W 보다 길면 None"""
    t = kenc.normalize(text)
    lead = re.match(r'^((?:\{[^}]*\}|\\n)*)', t).group(1)          # 앞 제어·빈 줄 유지
    tail = re.search(r'((?:\{[^}]*\}|\\n)*)$', t[len(lead):]).group(1)
    core = t[len(lead):len(t) - len(tail)] if tail else t[len(lead):]
    lead_lines = lead.count(BS)
    # 1) 번역자 줄바꿈을 지키고 긴 줄만 나눈다 → 2) 안 되면 색 바뀜 앞 줄바꿈(책 제목 «{c:0b}제목\n{c:0f}본문»)만 지키고 이어 흘린다
    for paras in (core.split(BS), re.split(r'\\n(?=\{c:)', core)):
        lines = _flow(paras, W)
        if lines is not None and len(lines) + lead_lines <= H:
            return lead + BS.join(lines) + tail
    return None


def _flow(paras, W):
    lines = []
    for para in paras:
        words = [w for w in re.split(r'[ 　]|\\n', para) if w != '']
        cur, n = '', 0
        for w in words:
            wl = len(re.sub(r'\{[^}]*\}', '', w))
            if wl > W:
                return None
            if not cur:
                cur, n = w, wl
            elif n + 1 + wl <= W:
                cur += ' ' + w; n += 1 + wl
            else:
                lines.append(cur); cur, n = w, wl
        if cur:
            lines.append(cur)
    return lines


def fits(text, W, H):
    t = kenc.normalize(text)
    ws = width(t)
    return max(ws) <= W and len(ws) - (1 if t.endswith(BS) else 0) <= H


def load():
    return {k: (int(w), int(h)) for k, w, h in (l.rstrip('\n').split('\t') for l in open(PATH, encoding='utf-8') if not l.startswith('#'))}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    import scriptfit, ko
    g = open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    tr = scriptfit.by_block()
    res = learn(g, scriptfit.blocks(), tr)
    with open(PATH, 'w', encoding='utf-8') as f:
        f.write('#상자키\t폭\t줄\n')
        for k in sorted(res):
            f.write('%s\t%d\t%d\n' % (k, *res[k]))
    print('상자 종류', len(res), collections.Counter(v for v in res.values()))


if __name__ == '__main__':
    main()


def run_keys(g, blocks, tr):
    """번호 → 상자 키"""
    keys = {}
    for off, cs, ds in blocks:
        if off not in tr:
            continue
        out, _ = lzss.decode(g, off + 8, ds)
        t0 = struct.unpack_from('<I', out, 0)[0]
        tbl = struct.unpack_from('<%dI' % (t0 // 4), out, 0)
        for k, a, b in extract.messages(out):
            m = out[a:b]
            for n, (s, e, t) in enumerate(extract.runs(m)):
                keys['%06x:%d:%d' % (off, k, n)] = box_key(out, tbl, m, s)[0]
    return keys


def report():
    sys.stdout.reconfigure(encoding='utf-8')
    import scriptfit, ko
    g = open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    tr = scriptfit.by_block()
    keys = run_keys(g, scriptfit.blocks(), tr)
    B = load()
    cnt = collections.Counter(); ex = []
    for r in ko.rows('script.tsv'):
        if not r['ko'] or '{c:07}' in r['ko']:
            continue
        W, H = B.get(keys.get(r['id']), (16, 4))
        new, st = layout(r['ko'], r['jp'], W, H)
        cnt[st] += 1
        if st == 'fail' and len(ex) < 40:
            ex.append((r['id'], W, H, r['ko']))
    print(dict(cnt))
    for e in ex:
        print(*e)


SEG = re.compile(r'(\{0a:[0-9a-f]+\})')          # 조각 안에서 새 상자(화자 바뀜)


def layout(ko, jp, W, H):
    """→ (새 표기, 상태) 상태: ok 그대로 · rewrap 낱말 단위로 다시 흘림 · jpover 원문도 창 모델에 안 맞음(원문 모양 기준 검사) · fail
       원문도 안 맞는 조각(책·긴 설명 — 엔진이 알아서 접거나 다른 창)은 «원문 최대 줄 폭·줄 수» 를 창으로 삼는다."""
    ks = SEG.split(kenc.normalize(ko)); js = SEG.split(jp)
    if len(ks) != len(js):
        js = [jp] * len(ks)
    out = []; states = set()
    for k, j in zip(ks, js):
        if SEG.fullmatch(k) or not k:
            out.append(k); continue
        w, h = W, H
        jc = re.sub(r'\{[^}]*\}', '', j)
        if '　　　' in j or (len(jc) >= 32 and len(jc) % 16 == 0 and '　' in jc):   # 16칸 칸 맞춤 목록·선택지 — 손대지 않는다
            out.append(k); states.add('fixed'); continue
        jw = width(j.rstrip(BS) if not j.startswith(BS) else j)
        eff = sum(max(1, -(-x // W)) for x in jw)       # 엔진 자동 줄바꿈까지 친 원문 줄 수
        if eff > H:                                     # 원문도 창 모델 밖 → 원문 줄 수까지 허용
            h = eff; states.add('jpover')
        if fits(k, w, h):
            out.append(k); continue
        r = wrap(k, w, h)
        if r is None:
            states.add('fail'); out.append(k)
        else:
            states.add('rewrap'); out.append(r)
    st = 'fail' if 'fail' in states else 'rewrap' if 'rewrap' in states else 'jpover' if 'jpover' in states else 'ok'
    return ''.join(out), st


def failing():
    """들어가지 않는 번역(고유 KO) → [(ko, jp, W, H, 번호들)]"""
    import scriptfit, ko
    g = open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    tr = scriptfit.by_block()
    keys = run_keys(g, scriptfit.blocks(), tr)
    B = load()
    res = collections.OrderedDict()
    for r in ko.rows('script.tsv'):
        if not r['ko'] or '{c:07}' in r['ko']:
            continue
        W, H = B.get(keys.get(r['id']), (16, 4))
        new, st = layout(r['ko'], r['jp'], W, H)
        if st == 'fail':
            k = (r['ko'], W, H)
            res.setdefault(k, [r['jp'], []])[1].append(r['id'])
    return [(k[0], v[0], k[1], k[2], v[1]) for k, v in res.items()]
