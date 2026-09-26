import struct, sys, re
sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\claude\roms\ss\AnEarth Fantasy Stories - The First Volume (Japan)\AnEarth Fantasy Stories - The First Volume (Japan) (Track 1).bin'
f = open(P, 'rb')
def sec(l, n=1):
    out = b''
    for i in range(n):
        f.seek((l + i) * 2352 + 16); out += f.read(2048)
    return out
pvd = sec(16)
print(pvd[1:6], pvd[40:72].decode('latin1').strip())
root = pvd[156:190]
def walk(l, s, base, out):
    d = sec(l, (s + 2047) // 2048)
    i = 0
    while i < len(d):
        n = d[i]
        if n == 0:
            i = (i // 2048 + 1) * 2048; continue
        rec = d[i:i + n]
        ll, ss = struct.unpack_from('<I', rec, 2)[0], struct.unpack_from('<I', rec, 10)[0]
        fl = rec[25]; nl = rec[32]; name = rec[33:33 + nl].decode('latin1').split(';')[0]
        if name not in ('\x00', '\x01'):
            if fl & 2:
                walk(ll, ss, base + '/' + name, out)
            else:
                out.append((base + '/' + name, ll, ss))
        i += n
    return out
fs = walk(struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0], '', [])
tot = 0
for p, l, s in fs:
    print('%-40s %7d %10d' % (p, l, s)); tot += s
print(len(fs), tot)
