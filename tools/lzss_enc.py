# -*- coding: utf-8 -*-
r"""LZSS 압축기 — 게임과 같은 규약(tools/lzss.py): 플래그 LSB 먼저·1=리터럴·참조 2B(오프셋 12비트·길이 3‥18)·창 4096·시작 0xFEE·사전 채움 창
  최장 일치 + 게으른 일치(다음 자리가 더 길면 한 글자 미룸) · 겹치는 참조 허용(디코더가 한 바이트씩 복사하므로 같다).
  창의 사전 채움도 후보. 결과는 decode 로 되풀어 원문과 같은지 확인한다.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lzss

W, R0, MINL, MAXL = 4096, 0xFEE, 3, 18


def encode(data):
    pre = lzss.prefill()
    H = bytes(pre[(R0 + j) % W] for j in range(W)) + bytes(data)   # H[i] 의 창 위치 = (R0 + i) % W
    end = len(H)
    idx = {}

    def add(p):
        if p + 3 <= end:
            idx.setdefault(H[p:p + 3], []).append(p)

    for p in range(W):
        add(p)

    def longest(cur):
        best_len, best_m = 0, 0
        for m in reversed(idx.get(H[cur:cur + 3], [])):
            if m >= cur:
                continue
            if cur - m > W:
                break
            L = 0
            while L < MAXL and cur + L < end and H[m + L] == H[cur + L]:
                L += 1
            if L > best_len:
                best_len, best_m = L, m
                if L == MAXL:
                    break
        return best_len, best_m

    out = bytearray()
    cur = W
    added = W
    while cur < end:
        flag_pos = len(out); out.append(0); flags = 0
        for bit in range(8):
            if cur >= end:
                break
            while added < cur:
                add(added); added += 1
            L, m = longest(cur) if cur + 3 <= end else (0, 0)
            if L >= MINL and cur + 1 < end:
                add(cur)
                L2, _ = longest(cur + 1) if cur + 4 <= end else (0, 0)
                if L2 > L + 1:                      # 게으른 일치: 한 글자를 리터럴로 보내고 다음 자리의 긴 일치를 쓴다
                    L = 0
            if L >= MINL:
                off = (R0 + m) % W
                out.append(off & 0xFF); out.append(((off >> 4) & 0xF0) | (L - 3))
                cur += L
            else:
                flags |= 1 << bit
                out.append(H[cur]); cur += 1
        out[flag_pos] = flags
    return bytes(out)


def encode_checked(data):
    enc = encode(data)
    dec, used = lzss.decode(enc + b'\x00' * 4, 0, len(data))
    assert dec == bytes(data), '압축 되풀기 불일치'
    return enc


def encode_opt(data):
    """최적 분할 — 각 자리에서 끝까지의 최소 비트(리터럴 9 · 참조 17)를 뒤에서부터 DP. 후보 길이는 최장 일치 이하 전부"""
    pre = lzss.prefill()
    H = bytes(pre[(R0 + j) % W] for j in range(W)) + bytes(data)
    end = len(H); n = len(data)
    idx = {}
    for p in range(end - 2):
        idx.setdefault(H[p:p + 3], []).append(p)
    import bisect
    best = [None] * n                                   # 자리별 (최장 길이, 그 길이별 가장 가까운 m 은 불필요 — 최장 m 하나로 모든 짧은 길이도 된다)
    for i in range(n):
        cur = W + i
        if cur + 3 > end:
            best[i] = (0, 0); continue
        lst = idx.get(H[cur:cur + 3], [])
        k = bisect.bisect_left(lst, cur)
        bl, bm = 0, 0
        for j in range(k - 1, -1, -1):
            m = lst[j]
            if cur - m > W - 1:                         # 창 안(자기 자신 위치 제외)
                break
            L = 0
            while L < MAXL and cur + L < end and H[m + L] == H[cur + L]:
                L += 1
            if L > bl:
                bl, bm = L, m
                if L == MAXL:
                    break
        best[i] = (bl, bm)
    INF = 1 << 60
    cost = [INF] * (n + 1); cost[n] = 0; choice = [0] * n
    for i in range(n - 1, -1, -1):
        c = 9 + cost[i + 1]; ch = 1
        bl, _ = best[i]
        for L in range(MINL, bl + 1):
            v = 17 + cost[i + L]
            if v < c:
                c, ch = v, L
        cost[i] = c; choice[i] = ch
    out = bytearray(); i = 0
    while i < n:
        flag_pos = len(out); out.append(0); flags = 0
        for bit in range(8):
            if i >= n:
                break
            L = choice[i]
            if L >= MINL:
                off = (R0 + best[i][1]) % W
                out.append(off & 0xFF); out.append(((off >> 4) & 0xF0) | (L - 3)); i += L
            else:
                flags |= 1 << bit; out.append(data[i]); i += 1
        out[flag_pos] = flags
    return bytes(out)


def encode_best(data):
    cands = [encode(data), encode_opt(data)]
    for enc in cands:
        dec, _ = lzss.decode(enc + b'\x00' * 4, 0, len(data))
        assert dec == bytes(data), '압축 되풀기 불일치'
    return min(cands, key=len)


def encode_cached(data):
    """encode_best + 디스크 캐시(work/cache/lz/<md5>.bin) — 같은 내용은 다시 안 누른다"""
    import hashlib
    d = os.path.join(os.path.dirname(HERE), 'work', 'cache', 'lz')
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, hashlib.md5(bytes(data)).hexdigest() + '.bin')
    if os.path.exists(p):
        return open(p, 'rb').read()
    enc = encode_best(data)
    open(p, 'wb').write(enc)
    return enc
