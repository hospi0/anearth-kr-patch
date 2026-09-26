import numpy as np
from PIL import Image
S = r'C:\Users\kbwor\AppData\Local\Temp\claude\C--claude\a1252d0f-e3a5-42ed-a16d-6181944a2a0b\scratchpad\\'
g = open(S + 'GAME.PRG', 'rb').read()
def render(buf, cols=32, n=512):
    n = min(n, len(buf) // 32)
    a = np.unpackbits(np.frombuffer(buf[:n * 32], np.uint8)).reshape(n, 16, 16)
    rows = (n + cols - 1) // cols
    img = np.ones((rows * 17, cols * 17), np.uint8)
    for i in range(n):
        r, c = divmod(i, cols); img[r * 17:r * 17 + 16, c * 17:c * 17 + 16] = 1 - a[i]
    return img * 255
base = 0x2560000
img = render(g[base:base + 32 * 512])
Image.fromarray(img).save(S + 'font_a.png')
print(img.shape)
