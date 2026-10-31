# gitgen — AI 기반 Git 커밋/PR 자동 생성 도우미

## 요구사항 분해

### 기능 요구사항 맵핑

| 요구사항 | 담당 모듈 | 구현 상태 |
|---------|---------|---------|
| Git 변경 사항 수집 (status, diff) | `gitctx.py` | 완료 |
| AI API 연동 (environ 기반 API Key) | `aiclient.py` | 완료 |
| 커밋 메시지 자동 생성 | `cli.py` (run_commit), `prompts.py` | 완료 |
| PR 제목/본문 자동 생성 | `cli.py` (run_pr), `prompts.py`, `formatter.py` | 완료 |
| CLI 서브커맨드 (commit, pr) | `cli.py` | 완료 |
| 옵션 파라미터 (--model, --temperature, --max-tokens, --safe-mode) | `cli.py` (argparse) | 완료 |
| 출력 형식 검증 및 다듬기 | `formatter.py` | 완료 |
| 안전 모드 (마스킹, diff 제한) | `sanitize.py` | 완료 |
| 변경 사항 없음 처리 | `cli.py` (has_changes 체크) | 완료 |
| API Key 미설정 처리 | `aiclient.py`, `cli.py` | 완료 |
| 에러 처리 (네트워크, 파싱) | `errors.py`, `aiclient.py` | 완료 |

### 논리 흐름

```
사용자 입력 (python main.py commit/pr)
  ↓
CLI 파싱 (argparse)
  ↓
Git 변경 사항 수집 (status, diff)
  ↓
변경 여부 판단
  ├─ 없음 → "[INFO] 변경 사항이 없습니다." → 종료
  └─ 있음 → 계속
  ↓
safe-mode 적용 (마스킹, 크기 제한)
  ↓
AI API Key 검증 (환경변수)
  ├─ 미설정 → "[ERROR] AI_API_KEY..." → 종료
  └─ 설정됨 → 계속
  ↓
프롬프트 구성 (system + user)
  ↓
AI API 호출 (urllib, 1회)
  ├─ 성공 → 응답 파싱
  ├─ 실패 (HTTP/네트워크) → "[ERROR] AI API 호출 실패..."
  └─ 응답 파싱 오류 → "[ERROR] AI API 응답 파싱 실패..."
  ↓
출력 후처리 (길이 제한, 구획 마킹)
  ↓
터미널 출력
  ↓
프로세스 종료 (exit code 0 또는 1)
```

---

## 모듈 계약과 설계 결정

### 패키지 구조

```
gitgen/
├── __init__.py           (빈 파일)
├── __main__.py           (진입점)
├── cli.py                (명령 파싱, 흐름 조율)
├── aiclient.py           (OpenAI 호환 API 호출)
├── errors.py             (예외 정의)
├── gitctx.py             (Git 상태/diff 수집)
├── prompts.py            (commit/pr 프롬프트 구성)
├── formatter.py          (출력 형식 가공)
└── sanitize.py           (마스킹, 크기 제한)
```

### 주요 설계 결정

| 항목 | 결정 사항 | 근거 |
|------|---------|------|
| **CLI 프레임워크** | argparse | 표준 라이브러리, 서브커맨드 지원 |
| **API 클라이언트** | urllib.request | 표준 라이브러리, 외부 의존성 없음 |
| **Git 연동** | subprocess (git status/diff) | 프로세스 격리, 오류 핸들링 |
| **API 호출 횟수** | 명령당 정확히 1회 | 비용 제어, 명확한 로그 |
| **API Key 관리** | os.environ 환경변수 | 보안, 코드 하드코딩 방지 |
| **API Gateway** | AI_API_BASE (기본값 제공) | 다중 엔드포인트 지원, 유연성 |
| **온도(temperature)** | 기본 0.2 | 낮은 온도 → 일관성, 안정성 |
| **max_tokens** | 기본 512 | 커밋/PR 길이 제한 |
| **안전 모드** | 마스킹(정규식) + 크기 제한 | 민감정보 보호, 토큰 비용 절감 |
| **출력 구획** | 헤더줄 (`--- Commit Message ---`) | 파싱 용이, 시각적 구분 |
| **exit code** | 0 성공, 1 오류 | POSIX 관례 |

### 에러 처리 전략

| 상황 | 예외 클래스 | 메시지 | exit code |
|------|-----------|--------|----------|
| API Key 미설정 | `ApiKeyMissingError` | `[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.` | 1 |
| 변경 사항 없음 | 예외 없음 (has_changes 체크) | `[INFO] 변경 사항이 없습니다...` | 0 |
| API 호출 실패 (HTTP) | `ApiCallError` | `[ERROR] AI API 호출 실패: <원인>` | 1 |
| API 응답 파싱 오류 | `ApiCallError` | `[ERROR] AI API 응답 파싱 실패: <원인>` | 1 |
| Git 명령 오류 | `GitError` | `[ERROR] git <명령> 실패: <stderr>` | 1 |
| 예기치 않은 오류 | 기본 Exception | `[ERROR] 예기치 않은 오류가 발생했습니다: ...` | 1 |

### 프롬프트 엔지니어링

#### Commit 프롬프트

**System Prompt 역할:**
- 한국어 커밋 메시지 작성 도우미 지정
- Conventional Commit 스타일 권장 (feat, fix, refactor, docs, test, chore)
- 제목 1줄 + 선택적 본문 구조
- 본문 요구사항: 변경 파일 1~3개 언급 또는 핵심 변경 사항 1~2개 (최소 1개)
- 과장/추측 금지

**User Prompt 구성:**
```
브랜치, 변경 파일 목록, git status --porcelain, git diff HEAD
```

#### PR 프롬프트

**System Prompt 역할:**
- 한국어 PR 제목/본문 작성 도우미
- 반드시 `## Why`, `## What`, `## How to Test` 섹션 포함
- 각 섹션 최소 1개 이상 불릿
- 실제 확인 가능한 테스트 방법만 기재

**User Prompt 구성:**
```
현재 브랜치, 변경 파일, git status, git diff HEAD
```

### 길이/형식 규칙 (후처리)

| 항목 | 제한 | 적용 함수 |
|------|------|----------|
| 커밋 제목 | 72자 이내 | `trim_commit_title()` |
| PR 제목 | 80자 이내 | `trim_pr_title()` |
| PR 본문 | 필수 섹션 + 각 1개 이상 불릿 | `ensure_pr_sections()` |

### 안전 모드 규칙

**마스킹 대상:**
- 이메일: `[MASKED_EMAIL]`
- `sk-`로 시작하는 20자 이상 토큰: `[MASKED_KEY]`
- `AI_API_KEY=` 뒤 값: `[MASKED_KEY]`

**크기 제한:**
- 최대 10개 파일
- 최대 200줄

---

## 단계별 실행 계획

### Phase 1: 환경 준비
1. 프로젝트 디렉토리 생성
2. Git 초기화 (`git init`)
3. Git 사용자 설정 (`git config user.email`, `git config user.name`)
4. 초기 커밋 (`git commit --allow-empty`)

### Phase 2: 변경 사항 생성
1. 파일 생성/수정
2. `git add` (스테이징)
3. **커밋하지 않음** (unstaged 상태 유지)

### Phase 3: CLI 실행

#### commit 명령
```bash
python main.py commit [--model MODEL] [--temperature TEMP] [--max-tokens N] [--safe-mode]
```

**검증 포인트:**
- `[INFO] Git status 수집 완료: N개 파일 변경 감지`
- `[INFO] Git diff 수집 완료: M줄`
- `[INFO] AI API 호출 횟수: 1`
- `[INFO] AI API 요청 중...`
- `[DONE] 커밋 메시지 생성 완료`
- 출력 구획: `--- Commit Message ---` + 메시지 + `----------------------`

#### pr 명령
```bash
python main.py pr [--model MODEL] [--temperature TEMP] [--max-tokens N] [--safe-mode]
```

**검증 포인트:**
- `[INFO] 현재 브랜치: <branch>`
- `[INFO] AI API 호출 횟수: 1`
- PR 제목 (1줄)
- PR 본문 (## Why / ## What / ## How to Test + 불릿)

### Phase 4: 오류 조건 테스트

| 시나리오 | 예상 출력 |
|---------|---------|
| API Key 미설정 | `[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.` |
| 변경 사항 없음 | `[INFO] 변경 사항이 없습니다. 커밋 메시지를 생성하지 않고 종료합니다.` |
| 잘못된 옵션 (예: `--temperature abc`) | argparse 사용법 출력 + `error: argument --temperature: invalid float value: 'abc'` |
| 존재하지 않는 명령 (예: `bogus`) | argparse 사용법 + `error: argument command: invalid choice: 'bogus'` |
| 불완전한 명령 (예: 명령 생략) | argparse 사용법 (required 서브커맨드 필수) |

### Phase 5: 정상 흐름 전체 테스트

1. **커밋 메시지 생성**
   - Git 변경 수집
   - AI API 호출
   - 메시지 검증 (제목 존재, 본문 선택적)
   - 출력 확인

2. **PR 초안 생성**
   - Git 변경 수집
   - AI API 호출
   - 제목 + 본문 (Why/What/How to Test) 검증
   - 출력 확인

---

## 인수 시험 목록

### 1. 정상 경로 테스트

#### Test 1.1: 커밋 메시지 생성 (정상)
```bash
# 준비: 파일 수정 후 git add
python main.py commit
```
**검증:**
- `[INFO] Git status 수집 완료: N개 파일 변경 감지` 출력
- `[INFO] Git diff 수집 완료: M줄` 출력
- `[INFO] AI API 호출 횟수: 1` 출력
- `[DONE] 커밋 메시지 생성 완료` 출력
- `--- Commit Message ---` 헤더 출력
- 커밋 메시지 본문 (feat/fix 등 포함) 출력
- `----------------------` 바닥글 출력
- exit code: 0

#### Test 1.2: PR 초안 생성 (정상)
```bash
python main.py pr
```
**검증:**
- `[INFO] 현재 브랜치: <branch>` 출력
- `[INFO] AI API 호출 횟수: 1` 출력
- `--- PR Title ---` 헤더 출력
- PR 제목 (1줄, 80자 이내) 출력
- `--- PR Body ---` 헤더 출력
- `## Why` 섹션 + 최소 1개 불릿
- `## What` 섹션 + 최소 1개 불릿
- `## How to Test` 섹션 + 최소 1개 불릿
- exit code: 0

#### Test 1.3: 옵션 파라미터 사용 (정상)
```bash
python main.py commit --model gpt-4o --temperature 0.5 --max-tokens 1024
```
**검증:**
- 명령 정상 실행
- 지정한 파라미터로 API 호출
- exit code: 0

#### Test 1.4: 안전 모드 활성화 (정상)
```bash
python main.py commit --safe-mode
```
**검증:**
- 명령 정상 실행
- diff에서 민감정보 마스킹 적용
-
