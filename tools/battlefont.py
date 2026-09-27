# -*- coding: utf-8 -*-
r"""전투 화면 이름(적·동료·주인공) 한글 — BATTLE.PRG 코드 패치 (2026-09-27)
  구조(정적 분석, my files/새 폴더/전투1·2.state):
    · BATTLE.PRG 는 0x06020000 에 올라간다(파일 오프셋 = RAM − 0x06020000). crt0 BSS = 0x06065950‥0x0606A4E0.
    · 이름 변환 0x0602CEB4(R4=출력 u32[], R5=문자열, R6=기준): 바이트 c, 다음이 ﾞ면 표D[c]·ﾟ면 표P[c]·아니면 표[c](u16)
      → 출력 = 표값 + R6. 표 주소 = 상수 0x0602CF00(D)·CF04(P)·CF08(기본). 기준 R6 = 0x2000(적 이름 등)·0x2240(윗 패널).
    · 글꼴 = VDP2 0x40000(기준 0x2000, 바탕 0) · 0x44800(기준 0x2240, 바탕 53/54 무늬) 8bpp 8×8, 가타카나 순.
    · 두 스테이트에서 비어 있는 VRAM: 0x49E00‥0x4D000(기준 0x2000 쪽), 그중 +0x4800 도 빈 창 0x4B400‥0x4BA00(24칸).
    · 0x0606A4E0 = 힙 머리(빈 블록 ~66KB, 끝에서부터 할당) → 앞쪽 0x0606A500‥ 에 데이터(파일 0x4A500‥, 파일에서 0).
  패치:
    ① 새 표 3개(원래 값 복사 + 새 코드) + 칸 목록([VRAM 주소 u32][64B]×N)을 0x0606A500 에.
    ② 표 주소 상수 3개 교체. ③ 함수 끝 0x0602CF0C «RTS» → 옛 표 자리(0x0602CC54, 이제 안 씀)의 짧은 코드로:
       목록 첫 칸의 VRAM 한 워드가 우리 값과 다르면 목록 전체를 VRAM 에 복사, 그리고 RTS(반환값 R0=R3 복원).
  칸: 자판 음절(기본·ㄴ·ㅇ) → 원래 가나 칸 두 사본 덮기 · 동료 추가 음절(샤올베트릴, 코드 0xE0‥) → 두 사본 창 ·
      적 전용 음절 → 코드 풀(0x01‥, 0x21‥, 0x5B‥, 0xE5‥) · 칸은 0x49E00‥ 한 사본.
"""
import os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bdf, kbd, ko, smallfont

LOAD = 0x06020000
T_D, T_P, T_B = 0x0602CF00, 0x0602CF04, 0x0602CF08      # 표 주소 상수 자리
OLD_D, OLD_P, OLD_B = 0x0602CD14, 0x0602CC54, 0x0602CCB4
FUNC_END = 0x0602CF0C
STUB = 0x0602CC54                                        # 옛 표 자리(참조는 위 상수 3개뿐 — 확인)
# ★2026-09-27 실기 «Address Error»: BATTLE.PRG 는 초기화된 데이터(파일 ~0x45950)까지만 올라온다 — 0x0606A500 은 로드 범위 밖(전부 0)
#   → 표·칸 데이터는 GAME.PRG 16×16 글꼴 영역(파일 0x254C000‥+0x3E000 → Low RAM 0x002C2000‥0x00300000, 전투 중에도 상주)의
#     안 쓰는 뒷부분(글꼴 오프셋 0x38000‥ = JIS E7xx 이후, 번역 글자는 0x8DCA·이름 칸 E047‥ 까지만)에 둔다.
FONT_FILE, FONT_RAM, BLOB_OFF, BLOB_MAX = 0x254C000, 0x002C2000, 0x38000, 0x3DD00
BLOB = FONT_RAM + BLOB_OFF
DUAL = (0x4B400, 0x4BA00)                                # +0x4800 도 빈 창(두 사본)
SINGLE = [(0x49E00, 0x4B400), (0x4BA00, 0x4D000)]
COPY1 = 0x4800                                           # 기준 0x2240 − 0x2000 = 0x240 문자 = 0x4800 바이트
GRAD = {0: 0x0F, 1: 0x0F, 2: 0x9E, 3: 0x9D, 4: 0x9C, 5: 0x9A, 6: 0x99}
SHADOW = 0x10
ENEMY = (0x24A00, 0x24E00)                               # battle.tsv 적 이름 구역
PARTY = [(0xCF3C, 0xCF44, '베스트릴'), (0xCF44, 0xCF4C, '올가'), (0xCF4C, 0xCF54, '나샤'), (0xCF54, 0xCF58, '카심')]
POOL = [c for c in list(range(0x01, 0x20)) + list(range(0x21, 0x30)) + list(range(0x5B, 0xA0)) + list(range(0xE5, 0x100))
        if c not in (0xDE, 0xDF)]


def cell(F, ch, bg):
    m = np.zeros((8, 8), np.uint8); m[:7, :7] = smallfont.glyph7(F, ch)
    c = np.frombuffer(bytes(bg), np.uint8).reshape(8, 8).copy()
    sh = np.zeros_like(m); sh[1:, 1:] |= m[:-1, :-1]; sh[:, 1:] |= m[:, :-1]; sh[1:, :] |= m[:-1, :]
    c[(sh == 1) & (m == 0)] = SHADOW
    for y in range(7):
        c[y][m[y] == 1] = GRAD[y]
    return c.tobytes()


def u16(b, a):
    return struct.unpack_from('>H', b, a - LOAD)[0]


def enemy_rows():
    return [r for r in ko.rows('battle.tsv') if r['ko'] and r['id'][0] == 'B' and ENEMY[0] <= int(r['id'][1:], 16) < ENEMY[1]]


def plan(b):
    """→ (코드표 dict 음절→bytes, 새 표 3개, 칸 목록 [(VRAM 주소, 음절, 사본)])"""
    m, _ = kbd.name_map()
    enc = {}; cells = []
    for code, (base, n, o) in sorted(m.items()):
        enc[base] = bytes([code]); cells += [(0x40000 + u16(b, OLD_B + 2 * code) * 32, base, k) for k in (0, 1)]
        if n:
            enc[n] = bytes([code, 0xDE]); cells += [(0x40000 + u16(b, OLD_D + 2 * code) * 32, n, k) for k in (0, 1)]
        if o:
            enc[o] = bytes([code, 0xDF]); cells += [(0x40000 + u16(b, OLD_P + 2 * code) * 32, o, k) for k in (0, 1)]
    NT = [u16(b, OLD_B + 2 * c) for c in range(256)]
    ND = [u16(b, OLD_D + 2 * c) for c in range(256)]
    NP = [u16(b, OLD_P + 2 * c) for c in range(256)]
    dual = list(range(DUAL[0], DUAL[1], 64))
    for i, ch in enumerate(smallfont.EXTRA):             # 동료 추가 음절 — 메뉴와 같은 코드 0xE0‥
        a = dual.pop(0); code = smallfont.EXTRA_CODE + i
        enc[ch] = bytes([code]); NT[code] = (a - 0x40000) // 32
        cells += [(a, ch, 0), (a, ch, 1)]
    need = []
    for r in enemy_rows():
        for ch in r['ko']:
            if '가' <= ch <= '힣' and ch not in enc and ch not in need:
                need.append(ch)
    single = [a for lo, hi in SINGLE for a in range(lo, hi, 64)] + dual
    assert len(need) <= len(POOL) and len(need) <= len(single), (len(need), len(POOL), len(single))
    for ch, code, a in zip(need, POOL, single):
        enc[ch] = bytes([code]); NT[code] = (a - 0x40000) // 32
        cells.append((a, ch, 0))
    return enc, (NT, ND, NP), cells


def encode(s, enc):
    out = b''
    for ch in s:
        if ch == ' ' or ch == '　':
            out += b' '
        elif ch in enc:
            out += enc[ch]
        elif '０' <= ch <= '９' or '0' <= ch <= '9':
            out += bytes([0x30 + int(ch.translate(str.maketrans('０１２３４５６７８９', '0123456789')))])
        else:
            raise ValueError('전투 이름에 못 쓰는 글자 %r (%s)' % (ch, s))
    return out


def stub_code(check_off):
    """0x0602CC54 에 넣을 기계어 — 목록 첫 칸 VRAM 워드 확인 후 전체 복사(개수 0 이면 바로 돌아감)"""
    w = []; fix = {}
    w += [None]                     # MOV.L @(L_blob,PC),R1 — 나중에
    w += [0x6216]                   # MOV.L @R1+,R2   (개수)
    w += [0x2228]                   # TST R2,R2
    fix['bt0'] = len(w); w += [None]    # BT done (데이터가 없으면 — 2026-09-27 Address Error 교훈)
    w += [0x6512]                   # MOV.L @R1,R5    (첫 칸 주소)
    w += [0x7500 | check_off]       # ADD #off,R5
    w += [0x6052]                   # MOV.L @R5,R0
    w += [0x5710 | ((4 + check_off) // 4)]  # MOV.L @(4+off,R1),R7
    w += [0x3070]                   # CMP/EQ R7,R0
    fix['bt1'] = len(w); w += [None]    # BT done
    loop = len(w) * 2
    w += [0x6516]                   # MOV.L @R1+,R5
    w += [0xE710]                   # MOV #16,R7
    inner = len(w) * 2
    w += [0x6016, 0x2502, 0x7504, 0x4710]   # MOV.L @R1+,R0 · MOV.L R0,@R5 · ADD #4,R5 · DT R7
    bf1 = len(w) * 2; w += [0x8B00 | (((inner - bf1 - 4) // 2) & 0xFF)]
    w += [0x4210]                   # DT R2
    bf2 = len(w) * 2; w += [0x8B00 | (((loop - bf2 - 4) // 2) & 0xFF)]
    done = len(w) * 2
    w += [0x000B, 0x6033]           # RTS · MOV R3,R0
    for k in ('bt0', 'bt1'):
        i = fix[k]; w[i] = 0x8900 | (((done - i * 2 - 4) // 2) & 0xFF)
    if len(w) % 2:
        w.append(0x0009)
    lit = len(w) * 2
    assert (STUB + lit) % 4 == 0
    w[0] = 0xD100 | ((lit - 4) // 4)
    return b''.join(struct.pack('>H', x) for x in w) + struct.pack('>I', BLOB + 3 * 512)


def build(b, g, state_vram=None):
    """b = BATTLE.PRG bytearray(원본 복사본) — 제자리 수정. 반환 (코드표, 칸 수)"""
    enc, (NT, ND, NP), cells = plan(bytes(b))
    F = bdf.Font(smallfont.F7)
    bg0 = bytes(64)
    bg1 = BG1
    data = []
    for a, ch, k in cells:
        data.append((a + (COPY1 if k else 0), cell(F, ch, bg1 if k else bg0)))
    # 확인 칸: 첫 칸(자판 가나 칸 사본 0)에서 원래 글꼴과 다른 0 아닌 워드
    first = data[0][1]
    off = next(o for o in range(0, 60, 4) if first[o:o + 4] != bytes(4) and (state_vram is None or first[o:o + 4] != state_vram[data[0][0] + o:data[0][0] + o + 4]))
    blob = b''.join(struct.pack('>256H', *t) for t in (NT, ND, NP)) + struct.pack('>I', len(data))
    blob += b''.join(struct.pack('>I', 0x25E00000 + a) + d for a, d in data)
    assert BLOB_OFF + len(blob) <= BLOB_MAX, '블롭 자리 넘침'
    o = FONT_FILE + BLOB_OFF
    g[o:o + len(blob)] = blob                          # GAME.PRG 글꼴 영역 뒷부분(→ Low RAM 0x002FA000)
    struct.pack_into('>I', b, T_B - LOAD, BLOB); struct.pack_into('>I', b, T_D - LOAD, BLOB + 512); struct.pack_into('>I', b, T_P - LOAD, BLOB + 1024)
    code = stub_code(off)
    assert STUB + len(code) <= OLD_B + 0x200
    b[STUB - LOAD:STUB - LOAD + len(code)] = code
    assert struct.unpack_from('>H', b, FUNC_END - LOAD)[0] == 0x000B
    struct.pack_into('>H', b, FUNC_END - LOAD, 0xA000 | (((STUB - FUNC_END - 4) // 2) & 0xFFF))
    for a, z, s in PARTY:
        kb = encode(s, enc); assert len(kb) < z - a
        b[a:z] = kb + bytes(z - a - len(kb))
    n = 0
    for r in enemy_rows():
        a = int(r['id'][1:], 16)
        e = a + r['budget']
        while e < ENEMY[1] and b[e] == 0:
            e += 1
        kb = encode(r['ko'], enc)
        assert len(kb) <= e - a - 1, (r['ko'], len(kb), e - a)
        b[a:a + len(kb) + 1] = kb + b'\0'
        n += 1
    return enc, len(data), n, len(blob)


# 0x44800 사본의 바탕 무늬(공백 칸) — 전투 스테이트에서 읽음(전투2.state1, 기준 0x2240 + 표[0x20])
BG1 = bytes.fromhex('36353535363635353535363535353635353636353635353635363635353635353535363635353536363536353536353635363536353535353535353536353536')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    b = bytearray(open(os.path.join(ROOT, 'work', 'BATTLE.PRG'), 'rb').read())
    g = bytearray(open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read())
    enc, nc, ne, nb = build(b, g)
    print('칸', nc, '적 이름', ne, '블롭', nb, '바이트')
    import sh2dis
    print('\n'.join(sh2dis.dis(STUB, 26, bytes(b))))
    print('\n'.join(sh2dis.dis(0x0602CEFA, 10, bytes(b))))
