# -*- coding: utf-8 -*-
r"""지명 표기 통일(사용자 2026-09-27)
  유피토촌·유피토마을 → 유피토 마을(띄어 씀) · 마로아 항구 마을·마로아 마을 → 마로아 항구
  피스로 촌 → 피스로 어촌 · 우리쿠리 부락 → 우리쿠리 마을 · ○○의 섬 → ○○ 섬(콘롤·베고리안·퓨라길)
  + «잘 지내‥ 야» → «잘 지내‥»
  받침이 바뀌는 곳(마을→항구, 부락→마을)은 뒤 조사도 고친다. 평문(G/B) 예산이 모자라면 붙여 쓴다(유피토마을).
  python tools/term_places.py → work/text/script_fix_places.tsv (setko 로 반영)
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ko

# 받침 있음→없음 조사
TO_OPEN = {'은': '는', '이': '가', '을': '를', '과': '와', '으로': '로', '이라': '라', '이야': '야'}
TO_RIEUL = {'으로': '로'}          # 받침 → ㄹ받침: 으로 → 로


def swap(t, old, new, josa):
    return re.sub(re.escape(old) + r'(으로|이라|이야|은|이|을|과)?(?![가-힣])' if False else re.escape(old) + r'(으로|이라|이야|은|이|을|과)?',
                  lambda m: new + (josa.get(m.group(1), m.group(1)) if m.group(1) else ''), t)


def fix(t):
    t = t.replace('잘 지내‥ 야', '잘 지내‥')
    t = swap(t, '유피토촌', '유피토 마을', TO_RIEUL)
    t = t.replace('유피토마을', '유피토 마을')
    t = swap(t, '마로아 항구 마을', '마로아 항구', TO_OPEN)
    t = swap(t, '마로아 마을', '마로아 항구', TO_OPEN)
    t = t.replace('피스로 촌', '피스로 어촌')
    t = swap(t, '우리쿠리 부락', '우리쿠리 마을', TO_RIEUL)
    for n in ('콘롤', '베고리안', '퓨라길'):
        t = t.replace(n + '의 섬', n + ' 섬')
    return t


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    rows = []
    for name in ('script.tsv', 'game_plain.tsv', 'battle.tsv'):
        for r in ko.rows(name):
            if r['ko'] and fix(r['ko']) != r['ko']:
                t = fix(r['ko'])
                if name != 'script.tsv' and r.get('budget') and len(t.replace(' ', '')) * 2 + t.count(' ') * 2 > r['budget']:
                    t = t.replace('유피토 마을', '유피토마을')      # 평문 예산(원문 ユピトの村 = 10 바이트) — 붙여 쓴다
                rows.append((r['id'], t))
    with open(os.path.join(ROOT, 'work', 'text', 'script_fix_places.tsv'), 'w', encoding='utf-8') as f:
        f.write('#번호\tKO — 지명 표기 통일(tools/term_places.py 생성)\n')
        for i, t in rows:
            f.write('%s\t%s\n' % (i, t))
    print(len(rows))
