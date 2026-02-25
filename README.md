## TL;DR

Incus 기반 디바이스 컨테이너를 활용해 Fleet OTA 환경을 구성하고,
Hub(FastAPI + systemd) – Device(OTA Agent + systemd) 간
펌웨어 버전 조회 → 다운로드 → 실행 → 버전 갱신까지의
End-to-End OTA 업데이트 흐름을 검증함.

초기에는 최신 버전을 서버 코드에 하드코딩하여 OTA 여부를 판단했으나,
update.json 기반 외부 상태 관리 구조로 리팩토링하여
펌웨어 버전 변경 시 서버 재배포 없이 OTA 정책 변경이 가능하도록 설계함.

## Key Contributions

- FastAPI 기반 OTA Hub 서버 구축 및 systemd 서비스화
- Incus 컨테이너 기반 디바이스 OTA Agent 구현
- Hub–Device 간 주기적 버전 체크 및 자동 펌웨어 다운로드/실행 검증
- firmware artifact(versioned shell script) 관리 구조 설계
- OTA Agent polling loop 설계 및 start-limit-hit 장애 해결
- semver 기반 버전 파일 관리로 OTA 판단 로직 안정화
- 운영 코드(main.py)와 OTA 정책(update.json) 분리
- 서버 재배포 없이 OTA 기준 버전 변경 가능한 구조로 리팩토링
- 운영 디렉터리와 Git 관리용 소스 디렉터리 분리

## Tech Stack

- Python / FastAPI / Uvicorn
- Linux / systemd
- Incus (Container-based Device Simulation)
- Shell Script (OTA Agent / Firmware)
- Git / GitHub

## Validation Result

- Device → Hub 버전 조회 API 통신 정상 확인
- 최신 버전 판단 후 OTA 필요 여부 응답
- Hub 다운로드 API 통해 펌웨어 스크립트 수신
- Device 측 펌웨어 실행 및 버전 파일 갱신
- 1.1.0 → 1.2.0 자동 OTA 업데이트 로그 검증
- 1.2.0 → 1.3.0 다운로드/실행 경로 직접 검증

## Design Insight

초기에는 최신 펌웨어 버전을 서버 코드에 하드코딩하여
OTA 업데이트 여부를 판단하는 구조를 사용하였으나,
update.json 기반 외부 상태 관리로 리팩토링하여
펌웨어 버전 증가 시 서버 코드 수정 및 재배포 없이
OTA 기준 버전을 변경할 수 있도록 개선함.

## Versioned OTA Experiments

본 프로젝트는 OTA 업데이트 흐름을 단일 버전이 아닌,
v1.1.0 → v1.2.0 → v1.3.0 순으로 확장하며 단계적으로 검증했다.


### v1.1.0 – 초기 OTA 실행 검증
> Figure 1. v1.1.0 펌웨어 수동 다운로드 및 실행을 통한 OTA 흐름 초기 검증

<img width="1364" height="1022" alt="image" src="https://github.com/user-attachments/assets/33a1c652-97e8-49b1-9a12-3eea9bfec52d" />



### v1.2.0 – OTA Agent 자동 감지 도입
> Figure 2. OTA Agent polling을 통한 v1.2.0 업데이트 감지 및 다운로드 시작 로그

<img width="1364" height="1022" alt="image" src="https://github.com/user-attachments/assets/8784fbd4-8487-4a1b-bdc5-4563fa527408" />



### v1.3.0 – 확장 버전 적용 검증
> Figure 3. v1.3.0 펌웨어 적용 후 디바이스 버전 파일 갱신 검증

<img width="682" height="511" alt="image" src="https://github.com/user-attachments/assets/f1721a87-b2d1-424b-839e-3dadd6c65cdc" />



