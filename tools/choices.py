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


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    R = {r['id']: r for r in ko.rows('script.tsv')}
    for rid, (c, w) in find().items():
        r = R.get(rid)
        if not r:
            continue
        f = fit(r['ko'], c, w)
        print(rid, c, w, r['jp'], '|', r['ko'], '→', f if f else '★안 맞음')
