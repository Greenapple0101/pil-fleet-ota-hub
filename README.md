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
  - firmware_v1.1.0.sh
  - firmware_v1.2.0.sh
  - firmware_v1.3.0.sh

---

<img width="2048" height="1397" alt="image" src="https://github.com/user-attachments/assets/a2f9fc76-54fc-4951-9085-40a176dd3c64" />



<img width="1364" height="1022" alt="image" src="https://github.com/user-attachments/assets/0cdd9567-a109-46a2-96c0-3760c14a5dc9" />


<img width="1364" height="1022" alt="image" src="https://github.com/user-attachments/assets/fb51b07a-56dc-4433-905b-3f943db422ad" />

<img width="1364" height="1022" alt="image" src="https://github.com/user-attachments/assets/d700f82b-6508-42e1-87dd-2aa38303575a" />

<img width="1364" height="1022" alt="image" src="https://github.com/user-attachments/assets/7b45a9f0-4772-4790-af68-1086dfd8f3fb" />

<img width="1364" height="1022" alt="image" src="https://github.com/user-attachments/assets/5441ab08-e9e6-4700-a6e3-f1a0c236110a" />

<img width="1364" height="1022" alt="image" src="https://github.com/user-attachments/assets/a32eba2a-8c24-4176-8dd2-1571640fd9f2" />




## OTA 업데이트 생명주기

1. 디바이스 부팅 또는 OTA Agent 시작
2. 현재 버전 확인 (`/etc/firmware_version`)
3. Hub `/firmware/latest` 호출
4. 업데이트 필요 시 펌웨어 다운로드
5. 실행 권한 부여 후 펌웨어 실행
6. 버전 파일 갱신
7. 다음 주기부터 최신 버전으로 인식

---

## OTA 검증 단계 (버전별 의미)

### v1.1.0 — 초기 OTA 흐름 검증 (수동 실행 중심)

- Hub API를 통한 버전 조회/다운로드 경로 확인
- 디바이스에서 펌웨어를 직접 다운로드/실행하여 OTA 흐름 1차 검증
- 버전 파일 저장 포맷 이슈 발견 및 수정  
  - 잘못된 예: `Firmware updated to v1.1.0`  
  - 수정 후: `1.1.0` (semver만 저장)

> 수동 다운로드/실행 기반 OTA 기본 경로 검증  
> Hub API를 통해 펌웨어를 제공하고, 디바이스에서 실행 후 버전 파일이 정상 갱신되는지 1차 확인

<img width="1364" height="1022" alt="image" src="https://github.com/user-attachments/assets/3e24571d-7df5-4d8a-a1e6-d5a9d751d78f" />


---

### v1.2.0 — OTA Agent 자동화 도입 (systemd + polling)

- 디바이스 측 OTA Agent를 systemd 서비스로 등록
- 주기적 polling으로 자동 감지/다운로드/실행까지 end-to-end 검증
- `start-limit-hit` 문제 해결  
  - 1회 실행 후 종료되는 스크립트를 `while true + sleep` 구조로 리팩토링

> systemd 기반 OTA Agent 자동 업데이트(E2E) 검증  
> 디바이스 측 Agent가 주기적으로 Hub에 버전 조회 후, 업데이트 감지 시 자동 다운로드/실행까지 수행

<img width="682" height="543" alt="image" src="https://github.com/user-attachments/assets/b0d0466b-39c7-4b9d-8523-70486c3339b2" />


---

### v1.3.0 — 운영 구조 개선 및 확장 검증

- Hub 응답 구조 개선 (`filename` 필드 포함 검토)
- 펌웨어 로그 출력 강화로 검증 가시성 개선
- 버전 1.2.0 → 1.3.0 반영까지 최종 검증

> Hub 응답 구조 개선 이후 OTA 재검증  
> 자동 업데이트 및 버전 갱신 정상 동작 확인

<img width="1364" height="1086" alt="image" src="https://github.com/user-attachments/assets/e59b9e7d-7804-4ec5-b0dc-b97e6b3217af" />
<img width="1364" height="1086" alt="image" src="https://github.com/user-attachments/assets/a7366c29-68d9-4fe5-ae4e-2d3e5e338e64" />
<img width="1364" height="1086" alt="image" src="https://github.com/user-attachments/assets/85dbf4f7-9075-4c7f-989d-a4fc85249164" />


---

## Firmware Version Check

### 초기 방식 (하드코딩)

초기에는 서버 코드(`main.py`) 내부에 최신 버전을 하드코딩하여 OTA 여부를 판단했다.

- 서버 기준 최신 버전 = `"1.2.0"`
- 디바이스 버전과 다르면 업데이트 수행

한계:

- 버전 증가 시마다 서버 코드 수정 필요
- 서비스 재배포 필요
- OTA 정책과 서버 로직이 강하게 결합됨

---

### 개선 방식 (`update.json` 기반 외부 상태 관리)

최신 버전 기준을 `update.json`으로 분리하여 서버 로직과 OTA 정책을 분리했다.

- `update.json`의 `latest` 값을 읽어 최신 버전 기준으로 사용
- 운영자는 JSON 값만 변경하면 OTA 기준 변경 가능

효과:

- 서버 코드 수정 없이 OTA 기준 변경 가능
- 재배포 빈도 감소
- 운영 편의성 및 확장성 개선

---

## Device Agent OTA Logic

OTA Agent는 일회성 스크립트가 아니라, systemd에 의해 지속 관리되는 주기 실행형 프로세스로 설계했다.

동작 로직:

- 현재 버전 읽기
- Hub 버전 체크 API 호출
- `update == true`이면 다운로드
- 펌웨어 실행
- 버전 파일 갱신
- `sleep` 후 반복

초기 Agent는 1회 실행 후 종료되는 구조였고, systemd Restart 정책과 결합되면서 빠른 재시작이 반복되어 `start-limit-hit`가 발생했다.

이를 해결하기 위해 스크립트 내부를 polling loop(`while true + sleep`) 구조로 변경했다.

---

## 트러블슈팅 요약

### 1) OTA Agent 재시작 폭주 (`start-limit-hit`)

- 원인: 1회 실행 후 종료되는 스크립트 + systemd restart 정책 충돌
- 해결: polling loop 구조로 변경

### 2) 버전 문자열 포맷 불일치

- 원인: 버전 파일에 사람이 읽는 문장 저장
- 해결: semver(`1.1.0`)만 저장하도록 수정

### 3) 포트 8000 충돌

- 원인: pil-hub.service가 이미 uvicorn 실행 중인데 수동 실행 시도
- 해결: systemd 기준으로 서비스 재시작

### 4) Hub/Device 서비스 위치 혼동

- 원인: ota-agent.service를 호스트에서 재시작 시도
- 해결: 컨테이너 내부에서 관리하도록 역할 분리

---

## 요약

FastAPI 기반 OTA Hub와 Incus 기반 디바이스 OTA Agent를 구성하여, 버전 체크–다운로드–실행–버전 갱신까지의 OTA 업데이트를 end-to-end로 검증했고, start-limit-hit 및 systemd 기반 운영 이슈를 해결했으며, update.json 기반 외부 상태 관리로 OTA 기준 버전 운영 구조를 개선했다.
