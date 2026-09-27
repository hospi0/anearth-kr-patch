# -*- coding: utf-8 -*-
"""GAME.PRG SH-2 역어셈블(테라 프로젝트 sh2_disasm 재사용) — python tools/sh2dis.py 0x06036488 [개수]"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
LOAD = 0x06020000
_src = open(r'C:\claude\project\terra-kr-patch\tools\sh2_disasm.py', encoding='utf-8').read().split("if __name__")[0]
_ns = {}; exec(_src, _ns)


def dis(addr, n=80, g=None):
    g = g or open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    o = addr - LOAD
    return ['%08X  %04X  %s' % (a, w, t) for a, w, t in _ns['disasm_sh2'](g[o:o + n * 2], addr, n)]


def lit(addr, g=None):
    g = g or open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    return struct.unpack_from('>I', g, addr - LOAD)[0]


if __name__ == '__main__':
    a = int(sys.argv[1], 16); n = int(sys.argv[2]) if len(sys.argv) > 2 else 80
    print('\n'.join(dis(a, n)))
