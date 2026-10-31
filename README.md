# gitgen - AI 기반 Git 커밋/PR 자동 생성 도우미

## 설치 및 실행 방법

### 요구사항
- Python 3.10 이상
- Git (이미 초기화된 리포지토리에서 실행)

### 설치
```bash
git clone <repository-url>
cd gitgen
```

### 환경변수 설정
AI API Key를 환경변수로 설정해야 합니다.

```bash
export AI_API_KEY="your-api-key-here"
```

선택적으로 AI API 게이트웨이 주소를 변경할 수 있습니다 (기본값: `https://copa.codyssey.kr/v1/chat/completions`):
```bash
export AI_API_BASE="https://your-custom-endpoint.com/v1/chat/completions"
```

### 기본 실행

커밋 메시지 생성:
```bash
python main.py commit
```

PR 제목/본문 생성:
```bash
python main.py pr
```

## 주요 명령 및 옵션

모든 명령은 다음 옵션을 지원합니다:

- `--model MODEL`: AI 모델 지정 (기본값: `gpt-5.4-mini`)
- `--temperature TEMPERATURE`: 생성 다양성 제어 (기본값: `0.2`, 범위: 0.0~2.0)
- `--max-tokens MAX_TOKENS`: 최대 생성 토큰 수 (기본값: `512`)
- `--safe-mode`: 민감정보 마스킹 및 diff 크기 제한 활성화 (플래그)

### 사용 예시

기본 커밋 메시지 생성:
```bash
python main.py commit
```

높은 창의성으로 PR 생성:
```bash
python main.py pr --temperature 0.7 --max-tokens 1024
```

안전 모드로 실행 (민감정보 보호):
```bash
python main.py commit --safe-mode
```

커스텀 모델 사용:
```bash
python main.py pr --model gpt-4 --temperature 0.3
```

## 실제 실행 예시

### 변경 사항이 있는 경우 - 커밋 메시지 생성

입력:
```bash
python main.py commit
```

출력:
```
[INFO] Git status 수집 완료: 3개 파일 변경 감지
[INFO] Git diff 수집 완료: 8줄
[INFO] AI API 호출 횟수: 1
[INFO] AI API 요청 중...
[DONE] 커밋 메시지 생성 완료

--- Commit Message ---
feat: a.txt 추가

- a.txt에 hello/world 내용을 새로 생성
- gitgen/와 main.py는 새로 추가된 상태로 표시됨
----------------------
```

### PR 제목/본문 생성

입력:
```bash
python main.py pr
```

출력:
```
[INFO] 현재 브랜치: feature/commit-pr-generator
[INFO] AI API 호출 횟수: 1
[INFO] AI API 요청 중...
[DONE] PR 초안 생성 완료

--- PR Title ---
feat: 커밋/PR 자동 생성 기능 추가
--- PR Body ---
## Why
- 팀 협업 시 커밋 메시지와 PR 설명 작성에 시간이 소요되어 자동 생성 도구가 필요했습니다.

## What
- git status, git diff 결과를 수집해 AI 입력 컨텍스트로 전달하는 로직 추가
- 커밋 메시지 자동 생성 기능 구현

## How to Test
- 환경변수 설정: export AI_API_KEY="YOUR_KEY"
- 커밋 메시지 생성: python main.py commit
- PR 초안 생성: python main.py pr
```

### 변경 사항 없는 경우

입력:
```bash
python main.py commit
```

출력:
```
[INFO] 변경 사항이 없습니다. 커밋 메시지를 생성하지 않고 종료합니다.
```

### 환경변수 미설정

입력:
```bash
python main.py commit
```

출력:
```
[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.
```

### 잘못된 옵션

입력:
```bash
python main.py commit --temperature abc
```

출력:
```
usage: gitgen commit [-h] [--model MODEL] [--temperature TEMPERATURE]
                     [--max-tokens MAX_TOKENS] [--safe-mode]
gitgen commit: error: argument --temperature: invalid float value: 'abc'
```

## 모듈 구조 및 책임

### `__init__.py`
패키지 초기화 파일 (비어있음)

### `__main__.py`
- 프로그램 진입점
- `python -m gitgen` 실행 시 `cli.main()`을 호출

### `cli.py`
- argparse 기반 CLI 명령 파싱
- `commit` / `pr` 서브커맨드 정의
- 수집 → AI 호출 → 후처리 → 출력 전체 흐름 조율
- 에러 처리 및 로깅

### `gitctx.py`
- `git status --porcelain`과 `git diff HEAD` 실행
- Git 변경 사항을 `GitContext` 객체로 반환
- 변경된 파일 목록 파싱

### `aiclient.py`
- OpenAI 호환 API 클라이언트
- urllib.request로 POST 요청 실행 (1회)
- API 응답 파싱 (`choices[0].message.content`)
- 인증 실패/네트워크 오류 처리

### `prompts.py`
- 커밋 메시지용 system/user 프롬프트 구성
- PR 제목/본문용 system/user 프롬프트 구성
- Git 컨텍스트를 프롬프트 텍스트로 포맷

### `formatter.py`
- 커밋 제목 72자 이내 자르기
- PR 제목 80자 이내 자르기
- PR 본문 `## Why` / `## What` / `## How to Test` 섹션 보증
- 각 섹션에 최소 1개 이상 불릿 포함 보증
- 구획된 출력 문자열 생성 (`--- Commit Message ---`, `--- PR Title ---` 등)

### `sanitize.py`
- 민감정보 마스킹 (이메일, API Key 토큰)
- Diff 파일/줄 수 제한 (최대 10개 파일, 200줄)
- `--safe-mode` 플래그로 활성화

### `errors.py`
- 프로그램 전역 예외 클래스 정의
- `GitGenError`: 기본 예외
- `NoChangesError`: 변경 사항 없음
- `ApiKeyMissingError`: API Key 미설정
- `ApiCallError`: API 호출 실패
- `GitError`: Git 명령 실행 실패

## 요구사항별 구현 위치

| 요구사항 | 구현 위치 | 설명 |
|---------|---------|------|
| Git status/diff 수집 | `gitctx.py: collect()` | 서브프로세스로 git 명령 실행 |
| 변경 사항 여부 확인 | `gitctx.py: has_changes()` | status와 diff 모두 확인 |
| AI API 연동 | `aiclient.py: AiClient.complete()` | urllib로 POST 요청, 응답 파싱 |
| 환경변수 처리 | `aiclient.py: from_env()` | `AI_API_KEY`, `AI_API_BASE` 읽기 |
| CLI 옵션 | `cli.py: build_parser()` | --model, --temperature, --max-tokens, --safe-mode |
| 커밋 메시지 생성 | `cli.py: run_commit()` | 프롬프트 구성 → API 호출 → 포맷 |
| PR 생성 | `cli.py: run_pr()` | 현재 브랜치 출력 → 프롬프트 → API → 포맷 |
| 커밋 제목 1줄 보증 | `formatter.py: render_commit()` | 첫 번째 줄만 추출 및 72자 제한 |
| PR 템플릿 (Why/What/How) | `formatter.py: ensure_pr_sections()` | 섹션 헤더 파싱 및 불릿 보증 |
| 길이 검증 | `formatter.py: trim_commit_title()`, `trim_pr_title()` | 72자/80자 제한 |
| 민감정보 마스킹 | `sanitize.py: mask_secrets()` | 이메일, API Key 토큰 대체 |
| Diff 크기 제한 | `sanitize.py: limit_diff()` | 10개 파일, 200줄 제한 |
| 에러 처리 | `errors.py`, `cli.py: run_commit/run_pr()` | 예외별 메시지 + exit code |

## 주의사항

### 민감정보 보호
- API Key, 개인 이메일, 액세스 토큰 등이 diff에 포함될 수 있습니다.
- `--safe-mode` 옵션으로 마스킹을 활성화하세요:
  ```bash
  python main.py commit --safe-mode
  ```
- Safe mode 활성화 시:
  - 이메일은 `[MASKED_EMAIL]`로 치환
  - `sk-`로 시작하는 20자 이상 토큰은 `[MASKED_KEY]`로 치환
  - `AI_API_KEY=` 뒤 값은 `[MASKED_KEY]`로 치환
  - Diff는 최대 10개 파일, 200줄까지만 전송

### 비용 및 요청 제한
- **API 호출 최소화**: 각 명령(`commit` / `pr`)당 정확히 1회만 API를 호출합니다.
- **토큰 제한**: 기본값은 `--max-tokens 512`로 설정되어 있습니다.
  - 더 짧은 결과: `--max-tokens 256`
  - 더 자세한 결과: `--max-tokens 1024`
- **온도 조절**: 기본값은 `--temperature 0.2`로 일관된 결과를 생성합니다.
  - 더 정확함: `--temperature 0.1`
  - 더 창의성: `--temperature 0.7`
- **Batch 작업**: 여러 파일을 한 번에 변경한 후 1회 실행하면 효율적입니다.

### 생성 결과 검토
- AI가 생성한 커밋 메시지와 PR은 **초안**입니다.
- 최종 적용 전 반드시 검토하고 필요에 따라 수정하세요.
- 변경되지 않은 내용이나 가정이 포함될 수 있으므로 확인이 필수입니다.

### 프롬프트 엔지니어링
- 더 나은 결과를 원하면:
  1. 모델 변경: `--model <다른-모델명>`
  2. 온도 조절: `--temperature 0.3`~`0.7` 시도
  3. 토큰 증가: `--max-tokens 1024`
- 특정 팀의 커밋/PR 컨벤션을 따르려면 코드의 `prompts.py`에서 system prompt를 수정하세요.
