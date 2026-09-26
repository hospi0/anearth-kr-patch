# -*- coding: utf-8 -*-
r"""대본 블록 되쓰기(메모리 안) — 번역을 넣고 표를 옮기고 재압축, 원래 자리에 들어가는지
  자리 = 다음 블록(또는 다른 자료) 시작까지. rebuild(g, off, cs, ds, rows) → (새 풀림, 새 압축)
  python tools/scriptfit.py   → 자리 넘는 블록 목록
"""
import os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lzss, lzss_enc, extract, kenc, ko, bytestyle


def positions(out):
    """번호(blk 제외 'k:n') → (시작, 끝, 표기) — extract.main 과 같은 순서. LEAD[번호] = 앞에 보존할 INLINE 명령 바이트"""
    pos = {}
    LEAD.clear()                                        # 블록마다 새로(번호 'k:n' 은 블록 안에서만 유일)
    for k, a, b in extract.messages(out):
        for n, r in enumerate(extract.runs(out[a:b])):
            s0, e0, t = r
            pos['%d:%d' % (k, n)] = (a + s0, a + e0, t)
            if r.lead:
                LEAD['%d:%d' % (k, n)] = r.lead
    return pos


LEAD = {}


def inner_ptrs(out):
    """블록 안의 두 번째 오프셋 표 — u32 LE 값이 «NUL 바로 뒤»(문자열 시작)를 가리키고 2개 이상 연속.
    ★2026-09-27 상점 대사 «…게에 솔입니다»: `%7a XX YY ZZ` 뒤 u32 17개가 NUL 로 나뉜 상점 문구를 가리킨다 — 안 옮기면 문구 경계가 어긋난다"""
    t0 = struct.unpack_from('<I', out, 0)[0]; n = len(out)
    found = []
    i = t0
    while i < n - 8:
        j = i; run = []
        while j + 4 <= n:
            v = struct.unpack_from('<I', out, j)[0]
            if t0 < v < n and out[v - 1] == 0:
                run.append(j); j += 4
            else:
                break
        if len(run) >= 2:
            found += run; i = j
        else:
            i += 1
    return found


def rebuild(out, trs, keep=()):
    """trs: {'k:n': KO} → 새 풀린 블록 (머리 표 + 블록 안 오프셋 표를 함께 옮긴다). keep = 공백 그대로 둘 번호(선택지 칸 채움)"""
    out = bytearray(out)
    pos = positions(bytes(out))
    t0 = struct.unpack_from('<I', out, 0)[0]
    tbl = list(struct.unpack_from('<%dI' % (t0 // 4), out, 0))
    ptrs = [[i, struct.unpack_from('<I', out, i)[0]] for i in inner_ptrs(out)]   # [위치, 값]
    edits = []
    for key, text in trs.items():
        s, e, jp = pos[key]
        kb = kenc.enc(text, keep_space=key in keep or kenc.is_fixed(jp))
        lead = LEAD.get(key, b'')
        if lead and not kb.startswith(lead):
            kb = lead + kb                              # 되찾은 앞 글자와 함께 삼킨 기다림·표정 명령 보존
        edits.append((s, e, kb))   # 대본은 대사 렌더러(0x0602900C, 1바이트 처리) — 2바이트 규칙은 평문만
    for s, e, kb in sorted(edits, reverse=True):       # 뒤에서부터 — 앞 위치가 안 흔들린다
        for i, v in ptrs:
            assert not (s <= i < e), '오프셋 표가 번역 조각 안에 있다 %x' % i
        out[s:e] = kb
        d = len(kb) - (e - s)
        tbl = [v + d if v > s else v for v in tbl]
        for p in ptrs:
            if p[0] > s:
                p[0] += d
            if p[1] > s:
                p[1] += d
    struct.pack_into('<%dI' % len(tbl), out, 0, *tbl)
    for i, v in ptrs:
        struct.pack_into('<I', out, i, v)
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
