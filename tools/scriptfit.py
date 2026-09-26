# -*- coding: utf-8 -*-
r"""대본 블록 되쓰기(메모리 안) — 번역을 넣고 표를 옮기고 재압축, 원래 자리에 들어가는지
  자리 = 다음 블록(또는 다른 자료) 시작까지. rebuild(g, off, cs, ds, rows) → (새 풀림, 새 압축)
  python tools/scriptfit.py   → 자리 넘는 블록 목록
"""
import os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lzss, lzss_enc, extract, kenc, ko


def positions(out):
    """번호(blk 제외 'k:n') → (시작, 끝) — extract.main 과 같은 순서"""
    pos = {}
    for k, a, b in extract.messages(out):
        for n, (s0, e0, t) in enumerate(extract.runs(out[a:b])):
            pos['%d:%d' % (k, n)] = (a + s0, a + e0, t)
    return pos


def rebuild(out, trs):
    """trs: {'k:n': KO} → 새 풀린 블록"""
    out = bytearray(out)
    pos = positions(bytes(out))
    t0 = struct.unpack_from('<I', out, 0)[0]
    tbl = list(struct.unpack_from('<%dI' % (t0 // 4), out, 0))
    edits = []
    for key, text in trs.items():
        s, e, jp = pos[key]
        edits.append((s, e, kenc.enc(text, keep_space=kenc.is_fixed(jp))))
    for s, e, kb in sorted(edits, reverse=True):       # 뒤에서부터 — 앞 위치가 안 흔들린다
        out[s:e] = kb
        d = len(kb) - (e - s)
        tbl = [v + d if v > s else v for v in tbl]
    struct.pack_into('<%dI' % len(tbl), out, 0, *tbl)
    return bytes(out)


def blocks():
    return [(int(o, 16), int(c), int(d)) for o, c, d, _ in (l.split() for l in open(os.path.join(ROOT, 'work', 'blocks_game_all.txt')))]


def by_block():
    tr = {}
    for r in ko.rows('script.tsv'):
        if r['ko']:
            blk, k, n = r['id'].split(':')
            tr.setdefault(int(blk, 16), {})['%s:%s' % (k, n)] = r['ko']
    return tr


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    g = open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    bl = blocks()
    starts = [b[0] for b in bl]
    tr = by_block()
    over = 0; tot_over = 0; grow = []
    for i, (off, cs, ds) in enumerate(bl):
        if off not in tr:
            continue
        out, _ = lzss.decode(g, off + 8, ds)
        new = rebuild(out, tr[off])
        enc = lzss_enc.encode_best(new) if '--best' in sys.argv else lzss_enc.encode(new)
        room = (starts[i + 1] if i + 1 < len(starts) else len(g)) - off - 8
        grow.append(len(new) - ds)
        if len(enc) > room:
            over += 1; tot_over += len(enc) - room
            print('%07x 풀림 %5d→%5d 압축 %5d→%5d 자리 %5d  넘침 %d' % (off, ds, len(new), cs, len(enc), room, len(enc) - room))
    print('블록', len(tr), '넘침', over, '합', tot_over, '풀림 증가 최대', max(grow), '평균 %.0f' % (sum(grow) / len(grow)))


if __name__ == '__main__':
    main()
