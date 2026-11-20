# Visrtx Renderer for basic

LAMMPS 시뮬레이션 구조를 Windows에서 PNG로 저장하는 개인용 앱입니다. OVITO의 무료 Python 패키지로 구조 분석과 렌더링을 실행합니다.

## 설치와 사용

1. [GitHub Releases](https://github.com/polar2251/visrtx-renderer-for-basic/releases/latest)에서 **VisrtxRendererForBasic-Setup-x64.exe**를 내려받아 실행합니다. Windows 10/11 x64용 설치 프로그램이며 Python은 함께 설치됩니다.
2. 시작 메뉴에서 **Visrtx Renderer for basic**을 열고 LAMMPS dump 파일(.dump, .lammpstrj, .hea 등)을 선택합니다.
3. 원자 색상에서 **PTM**, **CNA**(적응형), **원본 색상**을 선택합니다. 여러 프레임이 있으면 0부터 시작하는 프레임 번호를 입력합니다.
4. **미리보기**로 구도를 확인합니다. 카메라 위치와 세로 시야를 비워 두면 선택한 프레임에 맞춰 자동으로 구도를 잡습니다. OVITO Basic에서 구도를 옮기려면 투영 방식과 카메라 위치, 시선 방향을 입력합니다. 세로 시야는 원근에서 도(°), 직교에서 화면에 보이는 세로 범위의 절반입니다.
5. **VisRTX** 또는 **Tachyon**을 선택한 다음 **PNG 렌더링**을 누릅니다. 기본 크기는 2400 × 1800이고 투명 배경을 선택할 수 있습니다.

VisRTX에는 CUDA와 OptiX를 지원하는 NVIDIA 그래픽 드라이버가 필요합니다. 첫 실행 시 셰이더 컴파일로 몇 분이 걸릴 수 있습니다. LAMMPS 파일 미리보기에는 Tachyon(CPU)을 사용합니다. [OVITO VisRTX 문서](https://docs.ovito.org/reference/rendering/visrtx_renderer.html)

## 열린 OVITO Basic 3.14.1에서 가져오기

1. OVITO Basic에서 원하는 프레임과 뷰포트를 선택합니다.
2. 렌더러의 **열린 OVITO에서 가져오기**를 누릅니다. Windows가 OVITO 메뉴를 찾으면 **Export File**을 엽니다. 메뉴가 열리지 않으면 OVITO에서 **File → Export File**을 선택합니다.
3. 파일 형식에 **POV-Ray scene**을 선택하고, 파일 이름에 클립보드의 경로를 붙여 넣은 뒤 **현재 프레임**을 내보냅니다. 렌더러가 생성된 파일을 자동으로 가져옵니다. 이미 내보낸 `.pov` 파일은 **찾기**로 열 수 있습니다.
4. **미리보기**로 확인하고 PNG를 저장합니다. 가져온 화면비를 유지하면 원본 구도가 유지됩니다.

스냅샷에는 카메라 위치·방향·회전, 투영, 시야, 배경, 원자 위치·색상·반지름과 내보낸 실린더가 포함됩니다. PTM/CNA 색상은 최종 표시 결과로 전달됩니다. 편집 가능한 모디파이어 스택, 메시와 오버레이를 옮기는 기능은 지원 범위 밖입니다. 3.16에서는 POV-Ray 장면 내보내기 형식이 제거되었습니다. [OVITO 3.16 변경 이력](https://docs.ovito.org/new_features.html#version-3-16-0-14-aug-2026)

앱에 포함된 Python 패키지는 RTX 5070 Ti에서 검증한 OVITO 3.16.0입니다. 설치된 OVITO Basic 3.14.1과 독립적으로 실행됩니다.

## Windows 빌드

64비트 Python 3.12와 Inno Setup 7을 준비합니다. 가상 환경에서 패키지를 설치하고 아래 명령으로 빌드합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\packaging\build.ps1 -Python (Resolve-Path .venv\Scripts\python.exe) -InnoCompiler 'C:\Program Files\Inno Setup 7\ISCC.exe'
```

빌드 스크립트는 패키징된 실행 파일로 LAMMPS 샘플을 렌더링한 뒤 `dist`에 설치 EXE와 SHA-256 체크섬을 생성합니다. NVIDIA PC에서 GPU 경로를 추가로 검사할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe packaging/smoke.py dist/VisrtxRendererForBasic/VisrtxRendererForBasic.exe --engine VisRTX
```

의존성 라이선스는 [THIRD-PARTY.md](THIRD-PARTY.md)를 참조하세요.
