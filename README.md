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

## Versioned OTA Experiments

본 프로젝트는 OTA 업데이트 흐름을 단일 버전이 아닌,
v1.1.0 → v1.2.0 → v1.3.0 순으로 확장하며 단계적으로 검증했다.


### v1.1.0 – 초기 OTA 실행 검증
> Figure 1. v1.1.0 펌웨어 수동 다운로드 및 실행을 통한 OTA 흐름 초기 검증

<img width="1364" height="1022" alt="image" src="https://github.com/user-attachments/assets/33a1c652-97e8-49b1-9a12-3eea9bfec52d" />

- Hub API를 통한 버전 확인 및 펌웨어 다운로드 경로 검증
- 디바이스에서 펌웨어 스크립트 다운로드/실행 성공 확인
- 버전 상태 파일 갱신 확인
- 초기 버전 문자열 저장 포맷 이슈(`Firmware updated to v1.1.0`)를 발견하고, semver(`1.1.0`)만 저장하도록 수정하여 비교 안정성 개선



### v1.2.0 – OTA Agent 자동 감지 도입
> Figure 2. OTA Agent polling을 통한 v1.2.0 업데이트 감지 및 다운로드 시작 로그

<img width="1364" height="1022" alt="image" src="https://github.com/user-attachments/assets/8784fbd4-8487-4a1b-bdc5-4563fa527408" />

- 디바이스 측 OTA Agent를 `systemd` 서비스로 등록
- 주기적 버전 체크(polling) → 업데이트 감지 → 다운로드 → 실행까지 end-to-end 검증
- `start-limit-hit` 문제를 해결하기 위해 1회 실행형 스크립트에서 `while true + sleep` 구조로 리팩토링



### v1.3.0 – 확장 버전 적용 검증
> Figure 3. v1.3.0 펌웨어 적용 후 디바이스 버전 파일 갱신 검증

<img width="682" height="511" alt="image" src="https://github.com/user-attachments/assets/f1721a87-b2d1-424b-839e-3dadd6c65cdc" />

- Hub 응답 구조 개선(`filename` 필드 포함 검토/반영)
- 서버 장애 발생 시 `journalctl` 기반 원인 추적 및 `main.py` 재작성으로 복구
- 펌웨어 스크립트 로그 출력 강화(OTA START/DONE)로 검증 가시성 개선
- 디바이스 `/etc/firmware_version` 기준 최종 반영까지 재검증

## OTA 기준 버전 관리 리팩토링 (하드코딩 → update.json)

초기에는 최신 펌웨어 버전을 서버 코드(`main.py`)에 하드코딩하여
OTA 업데이트 여부를 판단하는 구조를 사용했다.

이 방식은 버전이 증가할 때마다 서버 코드 수정 및 재배포가 필요하다는 운영상 한계가 있었다.

이를 개선하기 위해 최신 버전 기준을 `update.json` 기반 외부 상태관리 방식으로 분리하였다.
그 결과, 서버 로직을 수정하지 않고도 `update.json` 값 변경만으로 OTA 기준 버전을 변경할 수 있게 되었고,
운영 편의성과 확장성을 높일 수 있었다.

- 개선 전: 코드 수정 + 서비스 재배포 필요
- 개선 후: `update.json` 수정으로 OTA 기준 버전 변경 가능
