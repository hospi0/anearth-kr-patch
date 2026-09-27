# -*- coding: utf-8 -*-
r"""실행 중에 이름을 끼우는 문구(상점 사기·팔기, 일부 획득)는 빌드 때 받침을 알 수 없다 → 조사 없는 문장으로 바꾼다
  (2026-09-27 실기 «배시 소드 은(는) 1개에 40룩솔입니다»)
  조각 바로 앞이 메시지 끝(00)이고 번역이 조사로 시작하는 줄만. 번호 고정 끼움은 josa.resolve_lead 가 고른다.
  python tools/josa_dyn.py → work/text/script_fix_josa_dyn.tsv (setko 로 반영)
"""
import os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ko, josa, lzss, scriptfit

RULES = [
    (r'^은\(는\) １개에\\n$', r'\\n１개에 '),                          # [이름] / １개에 ４０룩솔입니다.
    (r'^을\(를\)(\\n몇 개 .*)$', r'\1'),                              # [이름] / 몇 개 파시겠어요？
    (r'^(\{c:0f\})을\(를\) ５개 손에 넣었다$', r'\1 ５개 획득'),
    (r'^(\{c:0f\})을\(를\) 손에 넣었다(！?)$', r'\1 획득\2'),
    (r'^(\{c:0f\})을\(를\) 받았다(！?)$', r'\1 획득\2'),
    (r'^을\(를\)(\\n추가했습니다\.)$', r'\1'),
    (r'^은\(는\)(\\n로브아티스트만\\n쓸 수 있어)$', r'\1'),
]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    g = open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    R = {r['id']: r for r in ko.rows('script.tsv') if r['ko']}
    tr = scriptfit.by_block(); out_rows = []; left = []
    for off, cs, ds in scriptfit.blocks():
        if off not in tr:
            continue
        out, _ = lzss.decode(g, off + 8, ds); P = scriptfit.positions(out)
        for k, (s, e, t) in P.items():
            rid = '%06x:%s' % (off, k)
            if rid not in R:
                continue
            a = josa.resolve_lead(josa.resolve(R[rid]['ko'], g), out[max(0, s - 16):s], g)
            if not re.match(r'(?:\{[^}]*\})*[가-힣]?\([가-힣]+\)', a) or '{name' in a:
                continue
            for pat, rep in RULES:
                if re.match(pat, R[rid]['ko']):
                    out_rows.append((rid, re.sub(pat, rep, R[rid]['ko']))); break
            else:
                left.append((rid, R[rid]['ko']))
    with open(os.path.join(ROOT, 'work', 'text', 'script_fix_josa_dyn.tsv'), 'w', encoding='utf-8') as f:
        f.write('#번호\tKO — 실행 중 이름 끼움 뒤 조사 없애기(tools/josa_dyn.py 생성)\n')
        for rid, t in out_rows:
            f.write('%s\t%s\n' % (rid, t))
    print('바꿈', len(out_rows), '남음', len(left))
    for x in left:
        print('  ', x)


if __name__ == '__main__':
    main()
