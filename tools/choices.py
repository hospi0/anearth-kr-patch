# -*- coding: utf-8 -*-
r"""선택지 — `%06 ..` 창 뒤 문자열 + `%05 ff %56 00 NN (x y w ?)*` 항목 정의
  항목 폭 = w/2 칸. 문자열은 항목마다 정확히 그 칸 수로 채워 엔진 자동 줄바꿈으로 한 줄에 한 항목씩 나온다.
  (2026-09-27 실기 «먹는다　안 먹는다» → 창에 «다» 만: 둘째 항목 5칸이 4칸 폭을 넘음)
  → 번역을 항목으로 나눠(전각/반각 공백 경계) 칸 수 맞춤. 넘치면 오류.
"""
import os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lzss, extract, scriptfit, ko


def find(g=None):
    """번호 → (항목 수, 항목 폭 칸)"""
    g = g or open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    tr = scriptfit.by_block(); res = {}
    for off, cs, ds in scriptfit.blocks():
        if off not in tr:
            continue
        out, _ = lzss.decode(g, off + 8, ds)
        for k, a, b in extract.messages(out):
            m = out[a:b]
            for n, (s, e, t) in enumerate(extract.runs(m)):
                tail = m[e:e + 12]
                if not (len(tail) >= 9 and tail[:5] == b'%\x05\xff%\x56'):
                    continue
                cnt = tail[8]                                   # %56 00 XX 01 NN (x y w h)×NN
                items = m[e + 9:e + 9 + 4 * cnt]
                if cnt == 0 or len(items) < 4 * cnt:
                    continue
                ws = {items[i * 4 + 2] for i in range(cnt)}
                if len(ws) == 1:
                    res['%06x:%d:%d' % (off, k, n)] = (cnt, ws.pop() // 2)
    return res


def fit(text, cnt, w):
    """번역 → 항목 cnt 개를 w 칸씩. 항목 경계 = 전각 공백 뭉치(없으면 반각 공백)"""
    t = text.strip()
    parts = [p for p in re.split(r'　+', t) if p]
    if len(parts) != cnt:
        parts = [p for p in re.split(r'[ 　]+', t) if p]
    if len(parts) != cnt:
        return None
    if any(len(p) > w for p in parts):
        return None
    return ''.join(p + '　' * (w - len(p)) for p in parts[:-1]) + parts[-1] + '　' * (w - len(parts[-1]))


def refit(jp, ko):
    """원문이 «항목마다 앞 들여쓰기 i 칸 + 줄 폭 L 칸» 꼴(전각 공백 채움)이면 번역도 같은 꼴로 → 문자열, 아니면 None
    ★2026-09-27 실기: `%05 ff %07 %56 …` 선택지(«　　みんなで行こう　…»)는 항목마다 2칸 들여쓰기 16칸 — 선택 막대가 그 자리에서
      시작한다. 번역이 첫 항목만 들여쓰고 나머지는 채움이 어긋나 «가운데 정렬» 막대와 글자가 어긋났다."""
    pre = re.match(r'(?:\{[^}]*\})*', ko).group()                 # 앞 색 명령({c:04} 등)은 그대로
    jp = re.sub(r'^(?:\{[^}]*\})*', '', jp); ko = ko[len(pre):]
    if '\\n' in jp or '{' in jp:
        return None
    for L in (16, 18, 14, 12, 20):
        if len(jp) % L:
            continue
        chunks = [jp[k:k + L] for k in range(0, len(jp), L)]
        i = min(len(c) - len(c.lstrip('　')) for c in chunks)
        if len(chunks) >= 2 and all(c.startswith('　' * i) and c.strip('　') and '　' not in c.strip('　') for c in chunks):
            break
    else:
        return None
    n = len(chunks)
    parts = [p for p in re.split(r'　+|(?<=[？！])(?=[^　 ])', ko.strip('　')) if p.strip()]   # 항목 경계 = 전각 공백 뭉치 또는 ？！ 뒤 바로 붙은 글자
    parts = [p.strip() for p in parts]
    if len(parts) != n or any(len(p) > L - 2 * i for p in parts):    # 선택 막대 = 줄 폭에서 양쪽 i 칸씩 뺀 길이(사용자 실기 확인)
        return None
    return pre + ''.join('　' * i + p + '　' * (L - i - len(p)) for p in parts)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    R = {r['id']: r for r in ko.rows('script.tsv')}
    for rid, (c, w) in find().items():
        r = R.get(rid)
        if not r:
            continue
        f = fit(r['ko'], c, w)
        print(rid, c, w, r['jp'], '|', r['ko'], '→', f if f else '★안 맞음')
