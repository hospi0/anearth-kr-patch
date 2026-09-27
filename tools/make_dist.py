# -*- coding: utf-8 -*-
r"""배포 묶음 — dist/AnEarth_KR_<VER>/ : xdelta(트랙 1) + xdelta.exe + readme.txt(CP949) + 한글패치_적용.bat
  검증: 원본 트랙 1 → xdelta 적용 → md5 = 빌드 결과(work/out) md5.
  python tools/make_dist.py   (먼저 python tools/build.py --write)
"""
import hashlib, os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build

VER = 'v0.9'
XDELTA = r'C:\claude\utils\xdelta.exe'
BIN = build.BASE + ' (Track 1).bin'
NAME = 'AnEarth_KR_' + VER
TITLE = '세가 새턴 에이너스 판타지 스토리즈 - 더 퍼스트 볼륨 한글 패치 ' + VER


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest().upper()


README = """{title}
============================================================

4개의 트랙으로 이루어진 {rom} 의
트랙 1번에 패치하시면 됩니다.

원본md5 : {o}
패치md5 : {d}

입니다.


[ 적용 방법 ]

  1) 원본 "{bin}" 을 이 폴더에 복사
  2) 한글패치_적용.bat 실행 → "{kbin}" 이 만들어집니다
  3) 만든 파일 이름을 원본 트랙 1 이름으로 바꿔 넣고, 트랙 2‥4 와 cue 는 그대로 쓰세요

  직접 적용:
    xdelta.exe -d -s "{bin}" "{patch}" "결과 파일"
  (Delta Patcher 같은 xdelta3 GUI 도구로 적용해도 됩니다. 원본이 다르면 xdelta 가 적용을 거부합니다.)


[ 바뀌는 것 ]

  - 본편 대사 전부, 메뉴·아이템·마법·상점·전투 문구
  - 이름 입력 한글 자판(주인공 이름 한글 4자, 하·스·피 포함)
  - 메뉴·상태·저장·전투 화면의 이름(주인공·동료·적) 한글
  - 구운 그림 글자: 메뉴 라벨(보통/선택), 금액 '룩솔', 마법책 주문 이름, 저장 화면 탭·안내
  - 아이템 이름 뒤 조사(을/를·이/가 등)는 이름 받침에 맞게 자동


[ 알려진 점 ]

  - 이름 입력 화면에서 받침 글자는 'ㄴ'·'ㅇ' 버튼으로 만듭니다(그 버튼이 붙는 글자에만).
  - 한글판에서 새로 입력한 이름만 한글로 보입니다. 일본어판 세이브의 이름은 다시 입력하세요.
  - 게임이 실행 중에 이름을 끼워 넣는 문구(상점 등)는 조사 없이 쓴 곳이 있습니다.
"""

BAT = r"""@echo off
chcp 949 >nul
set "XD=%~dp0xdelta.exe"
set "SRC=%~dp0{bin}"
set "DST=%~dp0{kbin}"
if not exist "%SRC%" (
  echo   [오류] 원본 "{bin}" 을 이 폴더에 넣어 주세요.
  pause & exit /b 1
)
"%XD%" -d -f -s "%SRC%" "%~dp0{patch}" "%DST%"
if errorlevel 1 (
  echo   [오류] 패치 실패 - 원본이 다를 수 있습니다(readme 의 원본md5 확인).
  pause & exit /b 1
)
echo   완료: "{kbin}"
pause
"""


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    src = os.path.join(build.SRC_DIR, BIN)
    out = os.path.join(build.OUT_DIR, BIN)
    d = os.path.join(ROOT, 'dist', NAME)
    os.makedirs(d, exist_ok=True)
    patch = NAME + '.xdelta'
    pp = os.path.join(d, patch)
    subprocess.run([XDELTA, '-e', '-9', '-f', '-s', src, out, pp], check=True)
    chk = os.path.join(d, '_check.bin')
    subprocess.run([XDELTA, '-d', '-f', '-s', src, pp, chk], check=True)
    o, want, got = md5(src), md5(out), md5(chk)
    os.remove(chk)
    assert got == want, ('패치 적용 결과가 빌드와 다름', got, want)
    shutil.copy2(XDELTA, os.path.join(d, 'xdelta.exe'))
    kbin = build.BASE + ' (Track 1) [KR].bin'
    kw = dict(title=TITLE, rom=build.BASE, o=o, d=want, bin=BIN, kbin=kbin, patch=patch)
    open(os.path.join(d, 'readme.txt'), 'wb').write(README.format(**kw).replace('\n', '\r\n').encode('cp949'))
    open(os.path.join(d, '한글패치_적용.bat'), 'wb').write(BAT.format(**kw).replace('\n', '\r\n').encode('cp949'))
    print('✅', d)
    for f in sorted(os.listdir(d)):
        print('  %-50s %12d' % (f, os.path.getsize(os.path.join(d, f))))
    print('원본md5', o, '패치md5', want, '패치 파일md5', md5(pp))


if __name__ == '__main__':
    main()
