# -*- coding: utf-8 -*-
r"""압축 블록 밖 평문 추출 → work/text/game_plain.tsv · work/text/battle.tsv
  GAME.PRG: LZSS 블록(work/blocks_game.txt) 범위는 뺀다(압축 데이터 속 리터럴 조각 오인 방지).
  본문 규칙은 tools/extract.py 와 같다(반각 히라가나·SJIS·`\`·%00/%04, 가나·한자 2자 이상).
  예산 = 원문 바이트(제자리) — 뒤따르는 NUL 은 예산에 넣지 않는다.
  번호 = G/B + 파일 오프셋
  python tools/extract_plain.py
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import extract as E

RUN = re.compile(rb'(' + E.TXT + rb'+)')


def blocks(path):
    out = []
    if os.path.exists(path):
        for l in open(path):
            off, cs, ds, _ = l.split(); off = int(off, 16)
            out.append((off, off + 8 + int(cs)))
    return out


def scan(data, skip, tag):
    rows = []
    sk = sorted(skip); j = 0
    for mm in RUN.finditer(data):
        s, e = mm.start(1), mm.end(1)
        while j < len(sk) and sk[j][1] <= s:
            j += 1
        if j < len(sk) and sk[j][0] <= s < sk[j][1]:
            continue
        if not any(a <= s < b for a, b in AREAS) or (e < len(data) and data[e] not in (0x00, 0x40)):   # 평문 구역 · NUL(또는 @) 끝
            continue
        t = E.render(data[s:e])
        if re.search(r'(.)\1\1\1', t.replace('　', '')) or re.search(r'\{[0-9a-f]{2}\}', t):   # 글꼴표·자료(«。。。「「「」」」…»)
            continue
        # 앞쪽에 붙은 잡음 글자(코드·표 바이트가 가나로 읽힘)는 «말뭉치에 없는 글자» 까지 잘라 낸다
        body = re.sub(r'\{[^}]*\}|\\n', '', t)
        real = E.REAL.findall(body)
        # ★가나 비율 기준은 한자 많은 아이템 이름·설명(«万能薬» «五元を打ち消す力を持つ魔法剣»)을 떨어뜨렸다(2026-09-26)
        #   → 모든 글자가 대본 말뭉치(script.tsv)에 나오는 글자 + 이름/짧은 말은 가타카나·한자 1자 이상
        if len(body) >= 2 and all(c in VOCAB for c in body) and len(real) >= 2 and (re.search(r'[ァ-ヶ一-龥々]', body) or len(body) >= 3):
            rows.append(('%s%07x' % (tag, s), e - s, t))
    return rows


LIMIT = 0x100000        # 그 뒤는 그림 데이터(반각 가나 바이트가 흔해 잡음이 수만 줄 나온다)
# 평문 구역 = 앞 1MB + GAME 0x43D7E00 이동 메뉴 지명표(«行き先を選んで下さい», 2026-09-26 bigram 점수 전수 검색으로 찾음)
AREAS = [(0, LIMIT), (0x43D7E00, 0x43D8000)]


SJ2 = re.compile(rb'((?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]|\x0a)+)')


def scan_sjis(data, tag):
    """BATTLE.PRG 보스 대사: 히라가나도 SJIS 2B · 줄바꿈 0x0A · 끝에 제어 바이트(«12 60 15 …») — 표기는 \\n"""
    rows = []
    for mm in SJ2.finditer(data[:LIMIT]):
        s, e = mm.start(1), mm.end(1)
        while s < e and data[s] == 0x0a:
            s += 1
        try:
            t = data[s:e].decode('cp932')
        except UnicodeDecodeError:
            continue
        t = t.replace('\n', '\\n')
        real = E.REAL.findall(t)
        if len(real) >= 3 and len(re.findall(r'[ぁ-んァ-ヶー]', t)) >= len(real) * 0.4 and not re.search(r'(.)\1\1\1', t):
            rows.append(('%s%07x' % (tag, s), e - s, t))
    return rows


def write(name, rows):
    os.makedirs(os.path.join(ROOT, 'work', 'text'), exist_ok=True)
    with open(os.path.join(ROOT, 'work', 'text', name), 'w', encoding='utf-8') as f:
        f.write('#위치\t예산(B)\tJP\tKO\n')
        for r in rows:
            f.write('%s\t%d\t%s\t\n' % r)


VOCAB = set()


def load_vocab():
    """대본(script.tsv) 에 나오는 글자 + 가나·전각 영숫자·부호 — 평문 판정의 글자 허용 목록"""
    for l in open(os.path.join(ROOT, 'work', 'text', 'script.tsv'), encoding='utf-8'):
        if not l.startswith('#'):
            VOCAB.update(re.sub(r'\{[^}]*\}|\\n', '', l.split('\t')[1]))
    VOCAB.update(chr(c) for c in range(ord('ぁ'), ord('ん') + 1))
    for lead in range(0x88, 0x99):                   # JIS 제1수준 한자(0x889F‥0x9872) — 대사엔 없고 아이템 설명에만 나오는 한자(勲·鎧…)
        for tr in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
            if 0x889F <= (lead << 8 | tr) <= 0x9872:
                try:
                    VOCAB.add(bytes([lead, tr]).decode('cp932'))
                except UnicodeDecodeError:
                    pass
    VOCAB.update(chr(c) for c in range(ord('ァ'), ord('ヶ') + 1))
    VOCAB.update('ー　‥！？、。・／（）＋－％：Ｘ×' + ''.join(chr(c) for c in range(0xFF10, 0xFF1A)) + ''.join(chr(c) for c in range(0xFF21, 0xFF3B)))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    load_vocab()
    g = open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    rg = scan(g, blocks(os.path.join(ROOT, 'work', 'blocks_game_all.txt')), 'G')
    write('game_plain.tsv', rg)
    b = open(os.path.join(ROOT, 'work', 'BATTLE.PRG'), 'rb').read()
    rb_ = scan(b, blocks(os.path.join(ROOT, 'work', 'blocks_battle_all.txt')), 'B')
    seen = {r[0] for r in rb_}
    rb_ += [r for r in scan_sjis(b, 'S') if r[0].replace('S', 'B') not in seen]   # S = SJIS 대사(보스전)
    write('battle.tsv', rb_)
    for name, rows in (('game_plain', rg), ('battle', rb_)):
        chars = sum(len(re.sub(r'\{[^}]*\}|\\n', '', t)) for _, _, t in rows)
        print(name, 'rows', len(rows), 'chars', chars)


if __name__ == '__main__':
    main()
