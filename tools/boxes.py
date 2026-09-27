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


def _label(out, tbl, arg, strict=False):
    if arg >= len(tbl) or tbl[arg] >= len(out):
        return None
    a = tbl[arg]; mm = out[a:a + 60]
    j = mm.find(b'%\x04\x07')
    if strict:                                          # 순수 이름표 메시지만: (%5b/%05/%4b …) %04 07 이름 [\] %04 0f … 끝(짧음)
        end = tbl[arg + 1] if arg + 1 < len(tbl) else len(out)
        if not 0 <= j <= 12 or end - a > 48:
            return None
        k = mm.find(b'%\x04\x0f', j)
        nm = mm[j + 3:k].rstrip(b'\x5c') if k > 0 else b''
        return extract.render(nm) if nm and b'%' not in nm else None
    if 0 <= j <= 12:
        k = mm.find(b'\x5c', j)
        return extract.render(mm[j + 3:k]) if k > 0 else None
    return None


def box_key(out, tbl, m, s, sibs=()):
    """본문 조각 앞의 상자 키 — '종류:이름' / '종류:-' / 'none'
    ★이름표 메시지는 같은 블록이 아니라 «같은 장면 묶음의 다른 블록»에 있을 수 있다(2026-09-27 실기: 올가·마리아 초상화 창을
      이름 없는 16칸 창으로 알고 흘려 엔진이 13칸째에서 자동 줄바꿈 → «싶지/만», «호/릭스도»). sibs = 같은 묶음 블록의 (풀림, 표)"""
    p = m.rfind(b'%\x0a', 0, s)
    if p < 0 or p + 3 >= len(m):
        return 'none', False
    sub, arg = m[p + 2], m[p + 3]
    nm = _label(out, tbl, arg) or _label(out, tbl, arg, strict=True)
    for o2, t2 in sibs:
        if nm:
            break
        nm = _label(o2, t2, arg, strict=True)
    return '%02x:%s' % (sub, nm or '-'), bool(nm)


_SIBS = {}


def siblings(g, off):
    """같은 장면 묶음(groups)의 다른 블록들 [(풀림, 오프셋 표)]"""
    if not _SIBS:
        import groups
        dec = {}
        for grp, start, end in groups.groups(g):
            offs = [b[0] for b in grp]
            for o in offs:
                if o not in dec:
                    cs, ds = struct.unpack_from('<II', g, o); d, _ = lzss.decode(g, o + 8, ds)
                    t0 = struct.unpack_from('<I', d, 0)[0]
                    dec[o] = (d, struct.unpack_from('<%dI' % (t0 // 4), d, 0)) if t0 % 4 == 0 and 4 <= t0 <= len(d) else None
            for o in offs:
                _SIBS.setdefault(o, []).extend(dec[x] for x in offs if x != o and dec[x])
    return _SIBS.get(off, [])


NAME_W = 4          # {name:…} 자리 칸 수(주인공 이름 한글 4자 제한 — kbd.NAME_LEN, 동료 이름도 4자 이내)


def vis(t):
    """화면 칸 수 — 제어 0칸, 이름 자리 NAME_W 칸"""
    t = re.sub(r'\{name:[^}]*\}', '#' * NAME_W, t)
    # {01:07XX} = 아이템 이름(번호로 번역 이름 길이를 안다, tools/josa.py) · {03:00XX} = 아이콘(실기: 이름 뒤 틈 + 16px) → 2칸
    #   (2026-09-27 전엔 {03} 을 4칸·{01} 을 0칸으로 쳐서 «…넣었다» 뒤 «！» 가 다음 상자로 넘어갔다)
    def item(m):
        import josa
        x = int(m.group(1), 16); w = josa.width(x)
        return '#' * (w or NAME_W)                     # 원문 폭(공백 채움 포함) — 2026-09-27 실기 «실버 코인   [아이콘]을…»
    t = re.sub(r'\{01:07([0-9a-f]{2})\}', item, t)
    t = re.sub(r'\{01:[^}]*\}', '#' * NAME_W, t)
    t = re.sub(r'\{03:[^}]*\}', '##', t)
    return len(re.sub(r'\{[^}]*\}', '', t))


def width(t):
    return [vis(x) for x in t.split(BS)]


def _old_width(t):
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
                key, lab = box_key(out, tbl, m, s, siblings(g, off))
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
    lines = _flow_dp(core, W, H - lead_lines)
    if lines is None:
        return None
    return lead + BS.join(lines) + tail


def _pieces(core):
    """[(조각, 앞 공백, 앞이 번역자 줄바꿈, 앞이 강제 줄바꿈)] — 낱말 단위, «‥» 뒤도 끊을 자리(공백 없이 붙음)
       강제 줄바꿈 = 색 바뀜 앞 줄바꿈(책 제목 «{c:0b}제목\n{c:0f}본문»)"""
    out = []
    for hi, para in enumerate(re.split(r'\\n(?=\{c:)', core)):
        for li, line in enumerate(para.split(BS)):
            words = [x for x in re.split(r'[ 　]', line) if x != '']
            for wi, w in enumerate(words):
                parts = re.findall(r'(?:\{[^}]*\}|[^‥…])*[‥…]+(?:\{[^}]*\})*|(?:\{[^}]*\}|[^‥…])+', w)
                for pj, pt in enumerate(parts):
                    first = wi == 0 and pj == 0
                    out.append((pt, pj == 0 and not first, first and li > 0, first and li == 0 and hi > 0))
    return out


def _flow_dp(core, W, maxlines):
    """최적 줄 나누기(2026-09-27 «줄바꿈 좀 예쁘게») — 줄 길이를 고르게(남는 칸²), 번역자 줄바꿈·문장부호 뒤를 우선,
       강제 줄바꿈 지킴, 줄 수 ≤ maxlines. ★글자 한복판은 안 자른다 — 조각 하나가 W 보다 길면 None"""
    import functools
    P = _pieces(core)
    n = len(P)
    if n == 0:
        return ['']
    wid = [vis(p[0]) for p in P]
    if max(wid) > W:
        return None

    @functools.lru_cache(None)
    def best(i, k):
        if i == n:
            return (0, ())
        if k <= 0:
            return None
        res = None; w = 0
        for j in range(i, n):
            if j > i:
                if P[j][3]:
                    break
                w += 1 if (P[j][1] or P[j][2]) else 0
            w += wid[j]
            if w > W:
                break
            rest = best(j + 1, k - 1)
            if rest is None:
                continue
            end_para = j + 1 == n or P[j + 1][3]
            c = 0 if end_para else (W - w)          # 남는 칸(선형 — 제곱은 번역자 줄바꿈을 삼키게 만든다)
            if w < 5 and not (end_para and i == 0):
                c += 8                                  # 너무 짧은 줄(«라이오스 / 님은…», 끝줄 «있어！» 외톨이)
            if not end_para:
                if P[j + 1][2]:
                    c -= 12                             # 번역자 줄바꿈 자리
                elif re.search(r'[.．！？!?,，‥…」』）)]$', re.sub(r'\{[^}]*\}$', '', P[j][0])):
                    c -= 4                              # 문장부호 뒤
                if not P[j + 1][1] and not P[j + 1][2]:
                    c += 4                              # 공백 없이 붙은 자리(‥ 뒤)
            c += 10 * sum(1 for q in range(i + 1, j + 1) if P[q][2])  # 번역자 줄바꿈을 삼킴
            tot = (c + rest[0], (j + 1,) + rest[1])
            if res is None or tot[0] < res[0]:
                res = tot
        return res

    r = best(0, maxlines)
    if r is None:
        return None
    lines = []; i = 0
    for e in r[1]:
        seg = ''
        for q in range(i, e):
            pt, sp, tb, hb = P[q]
            if q > i and (sp or tb):
                seg += ' '
            seg += pt
        lines.append(seg); i = e
    return lines


def _flow(paras, W):
    """낱말 단위 채우기. 낱말 안에서도 «‥» 뒤(부호 뒤 공백을 지워 붙은 곳)는 줄을 바꿀 수 있다 — 글자 한복판은 안 자른다"""
    lines = []
    for para in paras:
        pieces = []                                     # (조각, 앞 공백 여부)
        for w in re.split(r'[ 　]|\\n', para):
            if w == '':
                continue
            parts = re.findall(r'(?:\{[^}]*\}|[^‥…])*[‥…]+(?:\{[^}]*\})*|(?:\{[^}]*\}|[^‥…])+', w)
            for j, pt in enumerate(parts):
                pieces.append((pt, j == 0))
        cur, n = '', 0
        for pt, sp in pieces:
            wl = len(re.sub(r'\{[^}]*\}', '', pt))
            if wl > W:
                return None
            add = (1 if sp else 0)
            if not cur:
                cur, n = pt, wl
            elif n + add + wl <= W:
                cur += (' ' if sp else '') + pt; n += add + wl
            else:
                lines.append(cur); cur, n = pt, wl
        if cur:
            lines.append(cur)
    return lines


def fits(text, W, H):
    t = kenc.normalize(text)
    ws = width(t)
    return max(ws) <= W and len(ws) - (1 if t.endswith(BS) else 0) <= H


def size(B, key, ko, jp):
    """(폭, 줄 수) — 원문이 «\\n» 으로 시작하면 이름표 줄 끝의 개행이라(이름표 메시지에 개행 없음) 줄 하나 더"""
    W, H = B.get(key, (16, 4))
    if ko.startswith(BS) and jp.startswith(BS):
        H += 1
    # ★«ＴＲＥＡＳＵＲＥ»·«ＴＯＯＬ» 같은 영문 제목 알림(원문 본문 1줄)은 제목+본문 1줄짜리 작은 창
    #   (2026-09-27 실기: «구세의 부적[아이콘]을 / 손에 넣었다！» 가 둘째 줄로 넘어가 다음 상자로 밀림)
    if is_notice(jp):
        W, H = 16, 2
    return W, H


def is_notice(jp):
    # 색 명령 {c:0b} 가 조각 앞(조각 밖)에 있으면 조각이 «ＨＯＬＩＸ\n…» 로 바로 시작한다(2026-09-27 «이테르를 손에 넣었다» 57줄 남음)
    return bool(re.match(r'(?:\{[^}]*\})*[Ａ-Ｚ][Ａ-Ｚ　]+\\n', jp)) and jp.count(BS) == 1


NOTICE_SHORT = [(r'([을를]) 손에 넣었다(！?)$', r' 획득！'), (r'([을를]) 손에 쥐었다(！?)$', r' 획득！'), (r'([을를]) ([０-９]개) 받았다！$', r' \2 획득！'),
                (r'([을를]) ([０-９]개) 손에 넣었다！?$', r' \2 획득！'), (r'([을를]) 받았다！$', r' 획득！')]


def notice_fit(t, jp, W, H):
    """알림 창(제목+1줄)에 안 들어가면 아이템 획득 문구를 «○○ 획득！» 으로 줄인다(josa.resolve 뒤 문자열)"""
    if not is_notice(jp):
        return t
    new, st = layout(t, jp, W, H)
    if st != 'fail' and '{01:07' not in t:         # 아이템 획득 알림은 늘 «○○ 획득！»(사용자 2026-09-27 «다 조사도 없애고 획득으로»)
        return t
    for a, b in NOTICE_SHORT:
        t2 = re.sub(a, b, t)
        if t2 != t:
            return t2
    return t


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
                keys['%06x:%d:%d' % (off, k, n)] = box_key(out, tbl, m, s, siblings(g, off))[0]
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
        if r['ko'] == r['jp']:
            continue
        import josa
        t = josa.resolve(r['ko'], g)                     # 빌더와 같게 — 조사 먼저 고른다
        W, H = size(B, keys.get(r['id']), t, r['jp'])
        t = notice_fit(t, r['jp'], W, H)
        new, st = layout(t, r['jp'], W, H)
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
    ks = SEG.split(kenc.normalize(ko, kenc.is_fixed(jp))); js = SEG.split(jp)
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
    # ★조각 가운데 {0a:…}(이름표 찍고 새 박스)는 «지금 커서 자리» 에 이름표를 찍는다 — 원문은 그 앞에서 박스를 꽉 채우거나
    #   줄바꿈으로 끝나 이름표가 박스 밖으로 밀려 자동으로 다음 박스가 열린다(2026-09-27 «오빠» 가 첫 박스 끝에 붙음).
    #   → {0a} 앞 번역 조각의 커서 줄을 원문과 같게(모자라면 줄바꿈 추가)
    if len(ks) == len(js):
        for i in range(len(out) - 1):
            if SEG.fullmatch(out[i + 1] or '') and out[i] and not SEG.fullmatch(out[i]):
                need = cursor_line(js[i], W) - cursor_line(out[i], W)
                if need > 0:
                    out[i] = out[i] + BS * need
                    states.add('rewrap')
    st = 'fail' if 'fail' in states else 'rewrap' if 'rewrap' in states else 'jpover' if 'jpover' in states else 'ok'
    return ''.join(out), st


def cursor_line(t, W):
    """조각을 다 찍은 뒤 커서가 있는 줄(1부터) — 엔진 자동 줄바꿈(W칸) 포함, 꽉 찬 줄 끝이면 다음 줄"""
    lines = [vis(x) for x in t.split(BS)]
    n = sum(max(1, -(-x // W)) for x in lines)
    last = lines[-1]
    if last and last % W == 0:
        n += 1
    return n


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
        if r['ko'] == r['jp']:
            continue
        import josa
        t = josa.resolve(r['ko'], g)                     # 빌더와 같게 — 조사 먼저 고른다
        W, H = size(B, keys.get(r['id']), t, r['jp'])
        t = notice_fit(t, r['jp'], W, H)
        new, st = layout(t, r['jp'], W, H)
        if st == 'fail':
            k = (r['ko'], W, H)
            res.setdefault(k, [r['jp'], []])[1].append(r['id'])
    return [(k[0], v[0], k[1], k[2], v[1]) for k, v in res.items()]
