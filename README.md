# Fleet OTA Hub 실습 프로젝트

## 프로젝트 개요

Linux 기반 IoT 디바이스 플릿 환경을 가정하고, 중앙 Hub 서버(FastAPI + systemd)와 디바이스 측 OTA Agent(shell script + systemd)를 구성하여 펌웨어 OTA 업데이트 흐름을 end-to-end로 검증한 프로젝트이다.

디바이스(Incus 컨테이너)는 주기적으로 Hub에 현재 펌웨어 버전을 전달하고, Hub는 최신 버전 기준에 따라 업데이트 필요 여부를 판단하여 펌웨어 다운로드 URL을 반환한다. 디바이스는 해당 펌웨어를 다운로드/실행하고 로컬 버전 파일을 갱신한다.

초기에는 서버 코드에 최신 버전을 하드코딩하는 방식으로 시작했으나, 이후 `update.json` 기반 외부 상태 관리 구조로 리팩토링하여 서버 코드 수정 및 재배포 없이 OTA 기준 버전을 변경할 수 있도록 개선했다.

---

## 문제정의

단순히 “파일 다운로드 API”를 만드는 것과 실제 OTA 운영은 다르다. 실제 OTA에서는 아래 문제가 동시에 존재한다.

- 디바이스와 Hub 간 네트워크 통신 확인 필요
- 버전 비교 기준(semver/문자열 포맷) 일관성 필요
- 디바이스 측 에이전트의 지속 실행 구조(systemd) 필요
- 서버/에이전트 장애 시 로그 기반 원인 추적 필요
- 펌웨어 버전이 늘어날 때 서버 코드 수정 없이 운영 가능한 구조 필요

초기 구현에서는 최신 버전을 서버 코드(`main.py`)에 하드코딩하여 OTA 여부를 판단했다. 이 방식은 버전이 증가할 때마다 코드 수정 및 서비스 재배포가 필요하여 운영 비용이 커지는 한계가 있었다.

---

## 목표

- FastAPI 기반 OTA Hub 서버 구현
- 디바이스 측 OTA Agent 구현 및 systemd 서비스화
- 버전 조회 → 다운로드 → 실행 → 버전 갱신까지 end-to-end 검증
- 버전 문자열 포맷 불일치 등 OTA 판단 오류 요소 제거
- OTA 기준 버전 관리를 `update.json`으로 분리하여 운영 편의성 개선
- 트러블슈팅 과정을 로그 중심으로 재현 가능하게 문서화

---

## 사용시나리오

1. 디바이스 OTA Agent가 주기적으로 Hub에 현재 버전을 전송
2. Hub가 최신 버전 기준과 비교하여 업데이트 필요 여부 판단
3. 업데이트가 필요하면 `download_url` 반환
4. 디바이스가 펌웨어 스크립트 다운로드 및 실행
5. 디바이스 로컬 버전 파일(`/etc/firmware_version`) 갱신
6. 다음 polling 시점부터는 최신 버전으로 인식되어 업데이트 미수행

---

## 시스템 아키텍처

### 구성 요소

- **Hub Server (Ubuntu VM / systemd)**
  - FastAPI + Uvicorn
  - `/firmware/latest` : 버전 체크 API
  - `/firmware/download/{version}` : 펌웨어 다운로드 API
  - `update.json` : OTA 기준 버전 외부 상태 관리

- **Device (Incus Container / systemd)**
  - OTA Agent (`/usr/local/bin/ota-agent.sh`)
  - 주기 polling (`while true + sleep`)
  - Hub 응답 기반 다운로드/실행
  - 버전 파일 갱신

- **Firmware Artifacts**
  - `firmware_v1.1.0.sh`
  - `firmware_v1.2.0.sh`
  - `firmware_v1.3.0.sh`

### 역할 분리 요약

- Hub는 **업데이트 필요 여부 판단 + 펌웨어 제공**
- Device Agent는 **주기 polling + 다운로드/실행**
- Firmware Script는 **실행 후 로컬 버전 파일 갱신**
- OTA 기준 버전은 `update.json`으로 분리하여 **서버 로직과 운영 정책을 분리**

---

## 실습 환경 구성 및 초기 검증

본격적인 OTA 자동화 검증 전에, 먼저 VM/컨테이너 환경이 정상 준비되었는지와 Hub–Device 간 요청 흐름의 기초 경로가 성립하는지 확인했다. 이 단계를 통해 이후 실패 원인을 네트워크/환경 문제와 애플리케이션 로직 문제로 분리해 볼 수 있도록 했다.

### 1) Hub/Device 실습 환경 초기 준비 및 접근 확인

- Ubuntu VM 초기 부팅 및 접속 준비 상태 확인
- 실습 환경에서 Hub와 Device 역할을 분리해 운영할 수 있는 기반 구성 확인

<img width="1364" height="1022" alt="image" src="https://github.com/user-attachments/assets/6949fbb2-d93c-46a7-a837-7e630b561b55" />



### 2) Hub API/펌웨어 제공 경로 초기 확인

- Hub 서버에서 펌웨어 파일을 제공할 수 있는지 확인
- Device 측에서 수동 호출 기반으로 다운로드 경로를 점검해 OTA 기본 경로 사전 검증

<img width="1364" height="1022" alt="image" src="https://github.com/user-attachments/assets/3effa00b-9b14-455e-98cc-128bec803421" />


---

## OTA 업데이트 생명주기

1. 디바이스 부팅 또는 OTA Agent 시작
2. 현재 버전 확인 (`/etc/firmware_version`)
3. Hub `/firmware/latest` 호출
4. 업데이트 필요 시 펌웨어 다운로드
5. 실행 권한 부여 후 펌웨어 실행
6. 버전 파일 갱신
7. 다음 주기부터 최신 버전으로 인식

---

## OTA 검증 타임라인 (버전별 의미와 검증 포인트)

단순히 버전을 올리는 것이 아니라, 각 버전마다 검증 목적을 분리했다. 아래는 각 단계에서 무엇을 바꾸었고, 어떤 로그/결과로 검증했는지에 대한 기록이다.

### v1.1.0 — 초기 OTA 흐름 검증 (수동 실행 중심)

초기 단계에서는 자동화 이전에 **OTA 기본 경로(조회 → 다운로드 → 실행 → 버전 파일 갱신)** 자체가 성립하는지 확인하는 데 집중했다. 디바이스에서 Hub API를 직접 호출하여 펌웨어를 내려받고, 실행 후 로컬 버전 파일 저장 결과를 점검했다.

- 검증 내용
  - Hub 다운로드 API 경로 동작 여부
  - 디바이스에서 펌웨어 스크립트 다운로드/실행 가능 여부
  - 실행 후 버전 파일 갱신 여부
- 발견한 문제
  - 버전 파일에 사람이 읽는 문장(`Firmware updated to v1.1.0`) 저장
- 개선 방향
  - 버전 비교 안정성을 위해 semver(`1.1.0`)만 저장하도록 수정

**확인 포인트**
- 수동 다운로드/실행 기반으로 OTA 기본 경로가 성립하는지
- 버전 파일 저장 포맷 이슈가 실제로 존재하는지

<img width="1364" height="1022" alt="image" src="https://github.com/user-attachments/assets/5878075a-9eb5-4c3e-af64-e15247982f26" />



---

### v1.2.0 — OTA Agent 자동화 도입 (systemd + polling)

v1.2.0에서는 수동 검증 단계를 넘어서, 디바이스 측 OTA Agent를 systemd 서비스로 등록하고 polling 기반으로 자동 업데이트가 수행되는지 end-to-end 검증했다.

초기 Agent는 1회 실행 후 종료되는 구조였고, systemd `Restart` 정책과 결합되며 빠른 재시작 반복으로 `start-limit-hit`가 발생했다. 이를 해결하기 위해 Agent 내부를 `while true + sleep` 기반 polling loop 구조로 리팩토링했다.

- 변경 사항
  - OTA Agent systemd 서비스 등록
  - 일회성 실행 → polling loop 구조로 변경
- 검증 목표
  - 주기적 버전 조회
  - 업데이트 감지 시 자동 다운로드/실행
  - 버전 갱신 후 다음 주기부터 `No Update Needed` 상태 유지

**확인 포인트**
- 로그에서 `Update Available` → 다운로드/실행 → `Firmware Updated` → 다음 주기 최신 버전 인식 흐름이 연속으로 나타나는지

<img width="682" height="543" alt="v1.2.0 OTA Agent 자동 업데이트 로그" src="https://github.com/user-attachments/assets/b0d0466b-39c7-4b9d-8523-70486c3339b2" />

---

### v1.3.0 — 운영 구조 개선 및 확장 검증

v1.3.0에서는 Hub 응답 구조 개선(예: `filename` 필드 포함)과 펌웨어 로그 출력 강화를 적용한 뒤, 기존 자동 OTA 흐름이 회귀(regression) 없이 유지되는지 재검증했다.

핵심은 **응답 구조를 바꿔도 Agent 자동 업데이트 흐름이 안정적으로 유지되는지**를 확인하는 것이다.

- 개선 내용
  - Hub 응답 구조 개선 (`filename` 필드 포함)
  - 펌웨어 로그 출력 강화로 검증 가시성 향상
- 검증 목표
  - Hub 응답 변경 이후에도 다운로드/실행 흐름 정상 유지
  - 버전 `1.2.0 → 1.3.0` 자동 반영 및 버전 파일 최종 갱신 확인

#### 1) Hub 응답 구조 개선 이후 재검증 (중간 확인 로그)

- `/firmware/latest` 응답 형태 점검
- `filename` 포함 응답 기반 다운로드 경로 재확인
- Device 측 테스트 다운로드 및 실행 전 단계 점검


#### 2) v1.3.0 OTA 최종 반영 확인

- 펌웨어 실행 로그(`OTA START`, 적용 버전 로그, `OTA DONE`) 확인
- `/etc/firmware_version` 값이 `1.3.0`으로 갱신되었는지 최종 확인

**확인 포인트**
- 자동 업데이트 실행 로그와 버전 파일 결과가 일치하는지 (`1.3.0`)

<img width="1364" height="1086" alt="v1.3.0 OTA 최종 반영 확인" src="https://github.com/user-attachments/assets/85dbf4f7-9075-4c7f-989d-a4fc85249164" />

---

## Firmware Version Check

### 초기 방식 (하드코딩)

초기에는 서버 코드(`main.py`) 내부에 최신 버전을 하드코딩하여 OTA 여부를 판단했다.

- 서버 기준 최신 버전 = `"1.2.0"`
- 디바이스 버전과 다르면 업데이트 수행

#### 한계

- 버전 증가 시마다 서버 코드 수정 필요
- 서비스 재배포 필요
- OTA 정책과 서버 로직이 강하게 결합됨

---

### 개선 방식 (`update.json` 기반 외부 상태 관리)

최신 버전 기준을 `update.json`으로 분리하여 서버 로직과 OTA 정책을 분리했다.

- `update.json`의 `latest` 값을 읽어 최신 버전 기준으로 사용
- 운영자는 JSON 값만 변경하면 OTA 기준 변경 가능

#### 효과

- 서버 코드 수정 없이 OTA 기준 변경 가능
- 재배포 빈도 감소
- 운영 편의성 및 확장성 개선

---

## Device Agent OTA Logic

OTA Agent는 일회성 스크립트가 아니라, systemd에 의해 지속 관리되는 주기 실행형 프로세스로 설계했다.

### 동작 로직

- 현재 버전 읽기 (`/etc/firmware_version`)
- Hub 버전 체크 API 호출 (`/firmware/latest`)
- `update == true`이면 펌웨어 다운로드
- 다운로드한 펌웨어 실행
- 버전 파일 갱신
- `sleep` 후 반복

### 설계 변경 배경

초기 Agent는 1회 실행 후 종료되는 구조였고, systemd `Restart` 정책과 결합되면서 빠른 재시작이 반복되어 `start-limit-hit`가 발생했다.

이를 해결하기 위해 스크립트 내부를 polling loop(`while true + sleep`) 구조로 변경했다. 이로써 systemd는 장기 실행 프로세스를 안정적으로 관리하고, OTA Agent는 주기적으로 Hub를 조회하는 역할에 집중하도록 분리했다.

---

## 트러블슈팅 요약

### 1) OTA Agent 재시작 폭주 (`start-limit-hit`)
- 원인: 1회 실행 후 종료되는 스크립트 + systemd restart 정책 충돌
- 해결: polling loop 구조로 변경

### 2) 버전 문자열 포맷 불일치
- 원인: 버전 파일에 사람이 읽는 문장 저장
- 해결: semver(`1.1.0`)만 저장하도록 수정

### 3) 포트 8000 충돌
- 원인: `pil-hub.service`가 이미 uvicorn 실행 중인데 수동 실행 시도
- 해결: systemd 기준으로 서비스 재시작 및 상태 확인 중심으로 운영

### 4) Hub/Device 서비스 위치 혼동
- 원인: `ota-agent.service`를 호스트에서 재시작 시도
- 해결: 컨테이너 내부에서 관리하도록 역할 분리

---

## 요약

FastAPI 기반 OTA Hub와 Incus 기반 디바이스 OTA Agent를 구성하여, 버전 체크–다운로드–실행–버전 갱신까지의 OTA 업데이트를 end-to-end로 검증했다. 또한 `start-limit-hit` 및 systemd 운영 이슈를 해결했으며, `update.json` 기반 외부 상태 관리로 OTA 기준 버전 운영 구조를 개선했다.
