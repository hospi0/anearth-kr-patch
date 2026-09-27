# -*- coding: utf-8 -*-
r"""대본 판정(1바이트 가나 10개 이상)에 걸려 추출에서 빠졌던 블록 11개의 조각을 script.tsv 에 추가(2026-09-27 실기 «구세의 부적！手었入녀자»)
  보물·방어구·도구·돈 획득 문구 + 화자 이름표. 조사는 빌더(josa.resolve)가 아이템 이름에 맞춰 고른다.
  python tools/add_missed.py
"""
import os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import scriptfit, lzss

BLOCKS = [0x67f3bc, 0x8567c4, 0xb5c640, 0x124a614, 0x1413e58, 0x16fe9a0, 0x1b14704, 0x1cddd6c, 0x1d64d64, 0x1fbfd14, 0x204ac90]
NAMES = {'ナーシャ': '나샤', 'ヴェストリル': '베스트릴', 'カシム': '카심', 'オルガ': '올가', '行商人': '행상인', 'レナ': '레나',
         'マリア': '마리아', 'マクガイア': '맥과이어', 'ティナ': '티나', 'エノーラ': '에노라'}


def tr(jp):
    m = re.fullmatch(r'\{c:07\}(.+)\\n\{c:0f\}', jp)
    if m:
        return '{c:07}%s\\n{c:0f}' % NAMES[m.group(1)]
    t = jp.replace('１００ルクソルを手に入れた！', '１００룩솔을 손에 넣었다！')
    t = t.replace('２つと', '２개와 ').replace('３つを手に入れた！', '３개를 손에 넣었다！')
    t = t.replace('を手に入れた！', '을(를) 손에 넣었다！').replace('を手に入れた', '을(를) 손에 넣었다！')
    assert not re.search(r'[ぁ-んァ-ヶ一-龥]', t), (jp, t)
    return t


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    g = open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    p = os.path.join(ROOT, 'work', 'text', 'script.tsv')
    have = set(l.split('\t', 1)[0] for l in open(p, encoding='utf-8'))
    add = []
    for off in BLOCKS:
        cs, ds = struct.unpack_from('<II', g, off); out, _ = lzss.decode(g, off + 8, ds)
        for k, (s, e, t) in scriptfit.positions(out).items():
            rid = '%06x:%s' % (off, k)
            if re.search(r'[ぁ-んァ-ヶ一-龥]', t) and rid not in have:
                add.append('%s\t%s\t%s\n' % (rid, t, tr(t)))
    with open(p, 'a', encoding='utf-8') as f:
        f.writelines(add)
    print('추가', len(add))
    for a in add:
        print(' ', a.rstrip())


if __name__ == '__main__':
    main()
