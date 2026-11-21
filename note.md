# gitgen — AI 기반 Git 커밋/PR 자동 생성 도구

## 개념 및 원리

### AI API 연동의 핵심 원리

AI API는 REST 기반 HTTP 요청으로 작동한다. 사용자가 입력 텍스트(프롬프트)를 서버로 전송하면, 서버는 학습된 모델을 이용해 응답 텍스트를 생성하고 반환한다. 이 도구는 `urllib.request`를 이용해 JSON 페이로드를 구성하고 POST 요청을 보낸 뒤, 응답의 `choices[0].message.content` 필드에서 생성 결과를 추출한다.

**핵심 설계 결정:**
- **환경변수 기반 인증**: API Key(`AI_API_KEY`)를 환경변수에서 읽어 하드코딩을 피한다.
- **게이트웨이 주소 설정**: `AI_API_BASE` 환경변수로 엔드포인트를 지정하며, 기본값은 `https://copa.codyssey.kr/v1/chat/completions`이다.
- **파라미터 제어**: `temperature`(창의성, 0.2~1.0), `max_tokens`(응답 길이, 512)를 CLI 옵션으로 제공하여 결과 품질을 직접 조정할 수 있다.

### 프롬프트 설계를 통한 품질 제어

AI가 원하는 형식의 결과를 생성하도록 하려면 **시스템 프롬프트**(역할 정의)와 **사용자 프롬프트**(구체적 지시)를 명확히 구성해야 한다.

- **커밋 메시지**: conventional commit 스타일(feat/fix/refactor)을 강제하고, 변경된 파일과 핵심 내용 포함을 요구한다.
- **PR 본문**: Why/What/How to Test 섹션 구조를 필수화하고 각 섹션 최소 1개 불릿을 보장한다.

이를 통해 AI 생성 결과가 팀 규칙을 자동으로 따르도록 한다.

### Git 맥락 수집 및 자동화 흐름

1. `git status --porcelain`: 변경 상태 파일 목록 수집
2. `git diff HEAD`: 실제 코드 변경 내용(diff) 수집
3. 변경 여부 판단: status와 diff가 모두 빈 상태면 "변경 사항 없음" 처리
4. AI 프롬프트 구성: 변경 파일 목록, status, diff를 컨텍스트로 제공
5. 생성 결과 후처리: 제목 길이 트림, 섹션 검증, 구획 마크업 적용
6. 터미널 출력: 사용자가 결과를 검토하고 복사하여 실제 커밋/PR에 적용

### 보안 — safe-mode의 민감정보 처리

프로그래밍 코드의 diff에는 API Key, 개인정보, 민감한 설정값이 포함될 수 있다. `--safe-mode` 옵션 활성화 시:
- **마스킹**: 이메일(`user@example.com` → `[MASKED_EMAIL]`), 토큰(`sk-xxx` → `[MASKED_KEY]`), 환경변수 할당값 치환
- **크기 제한**: 최대 10개 파일, 최대 200줄까지만 AI에 전송하여 과도한 노출 방지

## 구현 상세

### 모듈 계층 구조

| 모듈 | 책임 |
|------|------|
| `cli.py` | argparse 명령 파싱, 워크플로 조율 |
| `gitctx.py` | `git status/diff` 수집, GitContext 생성 |
| `aiclient.py` | urllib을 이용한 OpenAI 호환 API 호출 |
| `prompts.py` | 커밋/PR용 system/user 프롬프트 구성 |
| `formatter.py` | 길이 트림, 섹션 검증, 구획 마크업 적용 |
| `sanitize.py` | safe-mode: 마스킹, diff 크기 제한 |
| `errors.py` | 전역 예외 정의 |

### 워크플로: commit 서브커맨드 실행 예시

```
python main.py commit --temperature 0.3 --max-tokens 256

1. [gitctx.collect] → git status/diff 수집
2. [has_changes 검사] → 변경 사항 없으면 'INFO' 메시지 후 종료
3. [정보 출력] → 파일 수, diff 줄 수 로깅
4. [safe-mode 적용] → --safe-mode 활성화 시 마스킹 & 크기 제한
5. [prompts.build_commit_prompt] → system/user 프롬프트 생성
6. [AiClient.from_env] → 환경변수에서 API Key 읽기 (없으면 예외)
7. [AI 호출] → '[INFO] AI API 호출 횟수: 1' 후 complete() 실행
8. [formatter.render_commit] → 결과 트림 & 구획 마크업
9. [터미널 출력] → '--- Commit Message ---' ~ '----------------------'
```

각 단계에서 발생하는 예외(`ApiKeyMissingError`, `ApiCallError`, `GitError`)는 `run_commit` 핸들러가 잡아 에러 메시지 출력 후 exit code 1로 종료한다.

### 핵심 함수 동작

#### `aiclient.AiClient.complete(system_prompt, user_prompt)`

```python
# urllib을 이용한 POST 요청
payload = {
    'model': 'gpt-5.4-mini',
    'messages': [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt}
    ],
    'temperature': 0.2,
    'max_tokens': 512
}
# HTTP 401/400/500 → ApiCallError 변환
# JSON 파싱 실패 → ApiCallError 변환
return response_data['choices'][0]['message']['content']
```

#### `formatter.ensure_pr_sections(body)`

AI 응답을 파싱하여 `## Why`, `## What`, `## How to Test` 섹션 존재 확인. 섹션이 빈 경우 기본 불릿(`- 변경 배경을 검토해 주세요.`)을 삽입하여 구조 보장.

#### `sanitize.apply_safe_mode(diff, enabled=False)`

활성화 시 `mask_secrets()` → 이메일/토큰 치환, `limit_diff()` → 파일/줄 수 제한을 순차 적용.

---

## 실행 방법 및 결과

### 설치

```bash
git clone <repository-url>
cd gitgen
export AI_API_KEY="your-api-key-here"
```

### 환경변수 설정

```bash
# 필수
export AI_API_KEY="sk-..."

# 선택적 (기본값: https://copa.codyssey.kr/v1/chat/completions)
export AI_API_BASE="https://your-custom-gateway/v1/chat/completions"
```

### 커밋 메시지 생성

```bash
python main.py commit
```

**출력 예시:**
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

### Pull Request 초안 생성

```bash
python main.py pr
```

**출력 예시:**
```
[INFO] 현재 브랜치: feature/my-branch
[INFO] AI API 호출 횟수: 1
[INFO] AI API 요청 중...
[DONE] PR 초안 생성 완료

--- PR Title ---
feat: Git 커밋/PR 자동 생성 기능 추가

--- PR Body ---
## Why
- 팀 협업 시 커밋 메시지와 PR 설명 작성에 시간이 소요되어 자동 생성 도구가 필요했습니다.

## What
- git status/diff를 수집해 AI 입력 컨텍스트로 제공
- OpenAI 호환 API를 urllib로 호출하여 메시지 생성

## How to Test
- 환경변수 설정: export AI_API_KEY="YOUR_KEY"
- 커밋 생성: python main.py commit
- PR 생성: python main.py pr
```

### CLI 옵션

```bash
python main.py commit --model gpt-4 --temperature 0.5 --max-tokens 1024 --safe-mode
python main.py pr --temperature 0.1 --max-tokens 256
```

- `--model`: AI 모델명 (기본값: `gpt-5.4-mini`)
- `--temperature`: 창의성 (0.0~1.0, 기본값: `0.2` — 낮을수록 일관적)
- `--max-tokens`: 응답 최대 길이 (기본값: `512`)
- `--safe-mode`: 민감정보 마스킹 & diff 크기 제한 (플래그)

### 오류 상황

**API Key 미설정:**
```bash
python main.py commit
# [ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.
# exit code: 1
```

**변경 사항 없음:**
```bash
python main.py commit
# [INFO] 변경 사항이 없습니다. 커밋 메시지를 생성하지 않고 종료합니다.
# exit code: 0
```

**잘못된 옵션:**
```bash
python main.py commit --temperature abc
# usage: gitgen commit [-h] [--model MODEL] [--temperature TEMPERATURE] ...
# gitgen commit: error: argument --temperature: invalid float value: 'abc'
```

**API 호출 실패:**
```bash
python main.py commit
# [ERROR] AI API 호출 실패: <HTTP 401 Unauthorized>
# exit code: 1
```

---

## 설계 결정 근거

### 왜 표준 라이브러리만 사용하는가?

외부 의존성 없이 `urllib.request`, `json`, `subprocess`, `argparse`, `os`, `re` 만으로 전체 기능을 구현함. 이를 통해 배포 복잡도를 낮추고, 네트워크/프로세스 관리 기초를 직접 다룬다.

### 왜 API를 명령당 정확히 1회만 호출하는가?

- 비용 제어: 반복 호출 방지
- 간결성: 여러 번 시도하는 재시도 로직 불필요
- 명확성: 사용자가 요청 횟수를 추적할 수 있음 (`[INFO] AI API 호출 횟수: 1`)

### 왜 후처리(trim, ensure_sections)를 별도 함수로 분리했는가?

- 단위 테스트 용이
- AI 응답이 항상 완벽하지 않으므로 보정 로직을 명시적으로 표시
- 향후 커스터마이징(길이 규칙 변경 등)을 쉽게 반영

### 길이·형식 규칙을 재생성이 아니라 후처리로 푼 이유는? (평가표 항목)

과제 원문은 "검증 후 재생성 또는 후처리 중 택1"이다. 이 도구는 후처리를 택했다. 비교와 근거는 README 의 `길이·형식 규칙: 재생성 대신 후처리를 선택한 이유` 에 표로 정리했다.

- 제목 72자·80자, `## Why/What/How to Test` 섹션과 섹션당 불릿 1개는 기계적으로 판정되는 규칙이라 코드(`formatter.py`)가 항상 만족시킬 수 있다. 재생성은 AI 가 규칙을 지킬 때까지 보장하지 못한다.
- 재생성은 호출이 늘어 토큰·지연이 증가한다. 후처리는 호출 1회로 고정되어 `[INFO] AI API 호출 횟수: 1` 과도 일관된다.
- 같은 AI 응답은 항상 같은 출력이 되어 API 없이 단위 시험이 가능하다.
- 한계: 자르기는 문장을 중간에서 끊을 수 있고 화면에 알리지 않는다. 내용 품질은 보정하지 못하므로 결과는 초안으로 검토한다.

### 왜 safe-mode는 선택적인가?

- 기본값 비활성화: 대부분의 업무 코드는 민감정보를 포함하지 않음
- 명시적 옵션: 사용자가 필요할 때만 보안 강화 선택
- 규제 환경(금융, 의료 등)에서 필수 요구사항으로 적용 가능

---

## 평가자가 물을 만한 질문과 답

### Q1. temperature와 max_tokens이 결과에 어떤 영향을 주나?

**A**: 
- `temperature`: 0.0~1.0 사이의 값. 낮을수록(예: 0.1) AI가 가장 확률 높은 단어만 선택해 일관적이고 보수적인 커밋 메시지 생성. 높을수록(예: 0.8) 다양한 표현을 시도해 창의적이나 불안정할 수 있음. 이 도구는 기본값 0.2로 설정해 일관성을 우선함.
- `max_tokens`: 생성 응답의 최대 길이(토큰 단위). 512는 커밋 제목+본문 몇 줄, PR 제목+3개 섹션(각 2~3개 불릿)에 충분함. 초과 시 응답이 잘림.

**코드 근거**: `aiclient.py` line 18-20, `cli.py` line 37-38

### Q2. git diff가 없는데도 git status에 변경이 있는 경우는?

**A**:
- 수집 명령이 둘이라 관점이 다르다. `git status --porcelain` 은 작업 트리 전체의 상태(수정·삭제·이름 변경·추적 안 되는 파일 `??`)를 보여 주고, `git diff HEAD` 는 **추적 중인 파일**의 HEAD 대비 줄 단위 변경만 보여 준다.
- 그래서 새로 만든 파일을 아직 `git add` 하지 않았다면 status 에는 `?? new.py` 로 나오지만 diff 는 비어 있을 수 있다. 이 도구는 `has_changes()` 가 status 와 diff 중 하나라도 비어 있지 않으면 "변경 있음"으로 판단하므로 이 경우에도 종료하지 않고 파일 목록을 프롬프트에 넣는다. 반대로 둘 다 비어 있을 때만 `[INFO] 변경 사항이 없습니다.` 를 출력하고 exit code 0 으로 끝낸다(API 호출 없음).
- 이름만 바뀌었거나 권한 비트만 바뀐 경우처럼 diff 본문이 거의 없는 변경도 status 에는 남는다. 이름 변경은 `old -> new` 형태로 나오므로 `_parse_changed_files` 가 화살표 뒤의 새 경로를 파일 목록에 넣는다.
- 한계: 커밋이 하나도 없는 저장소에서는 `git diff HEAD` 가 실패(`bad revision 'HEAD'`)해 `GitError` 로 종료한다. 추적 안 되는 파일의 내용은 diff 에 없으므로 AI 는 파일명만 근거로 쓴다.

**코드 근거**: `gitgen/gitctx.py` 의 `collect`, `_parse_changed_files`, `has_changes`

### Q3. API 호출에서 요청 구성, 응답 처리, 예외 대응은 어떤 흐름인가?

**A**:
1. **요청 구성**: 환경변수에서 `AI_API_KEY`·`AI_API_BASE` 를 읽고, 모델·`temperature`·`max_tokens`·`messages`(system + user)를 JSON 으로 직렬화해 `Authorization: Bearer <키>` 헤더와 함께 POST 한다.
2. **응답 처리**: 응답 JSON 에서 `choices[0].message.content` 를 꺼낸다. 필드 구조가 다르면(`KeyError`) 오류로 본다. 내용이 빈 문자열인 경우는 별도로 검사하지 않고 후처리 단계의 기본 문구로 채운다.
3. **예외 대응**: 키 누락은 `ApiKeyMissingError`, HTTP 4xx/5xx·네트워크 오류·JSON 파싱 실패·필드 누락은 `ApiCallError` 로 변환한다. CLI 는 이를 `[ERROR] ...` 한 줄로 출력하고 exit code 1 로 끝내므로 스택 트레이스가 사용자에게 노출되지 않는다. 키 값 자체는 오류 문구에 넣지 않는다.
4. 호출은 명령당 정확히 1회이며 실패해도 자동 재시도하지 않는다(설계 근거는 위 "왜 API를 명령당 정확히 1회만 호출하는가?").

**코드 근거**: `gitgen/aiclient.py`, `gitgen/errors.py`, `gitgen/cli.py` 의 `main`

### Q4. Git 명령 결과를 프로그램 입력으로 어떻게 연결하나?

**A**: `subprocess.run(['git', ...], capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)` 로 명령을 실행하고 표준 출력을 문자열로 받는다. 셸을 거치지 않고 인자를 리스트로 넘겨 명령 주입 위험을 피하며, `git` 이 없으면 `FileNotFoundError`, 비정상 종료면 `CalledProcessError` 를 `GitError` 로 바꿔 사용자에게 한 줄로 알린다. 받은 문자열은 `GitContext(branch, status, changed_files, diff)` 한 객체로 묶여 프롬프트 빌더로 전달된다. `--porcelain` 을 쓰는 이유는 사람이 읽는 형식이 아니라 버전이 바뀌어도 안정적인 기계 판독용 출력이기 때문이다.

### Q5. 프롬프트에 어떤 맥락을 넣어야 요구사항에 맞는 결과가 나오나?

**A**: 시스템 프롬프트는 "누가, 어떤 형식으로" 쓰는지(역할·conventional commit·Why/What/How to Test)를 고정하고, 사용자 프롬프트는 "무엇에 대해" 쓰는지(브랜치, 변경 파일 목록, status, diff)를 준다. 양식을 프롬프트에 명시해야 AI 가 팀 규칙에 맞춰 쓰고, diff 를 넣어야 실제 변경에 근거한 설명이 나온다. 다만 프롬프트는 부탁일 뿐 보장이 아니므로 길이·섹션 규칙은 `formatter.py` 후처리가 강제한다. 변경 이유(Why)는 diff 만으로 알 수 없어 AI 가 추정하게 되므로, 생성 결과를 그대로 쓰지 않고 사람이 검토하는 전제로 설계했다.

### Q6. 생성 결과를 왜, 어떻게 검증하고 다듬나?

**A**: AI 출력은 확률적이라 같은 요청에도 제목이 길거나 섹션이 빠질 수 있다. 그래서 (1) 커밋 제목을 길이 한도에 맞춰 자르고, (2) PR 본문에 `## Why`, `## What`, `## How to Test` 가 모두 있는지 확인해 빠진 섹션은 기본 문구로 채우며, (3) 섹션마다 불릿이 최소 1개 있도록 정리한다. 재생성 대신 후처리를 고른 이유와 한계는 위 "길이·형식 규칙을 재생성이 아니라 후처리로 푼 이유는?" 에 있다.

### Q7. `--safe-mode` 는 무엇을 막고 무엇을 못 막나?

**A**: diff 를 AI 서버로 보내기 전에 이메일·키 형태 문자열·환경변수 할당값을 마스킹하고 전송 분량을 10개 파일·200줄로 제한한다. 패턴 기반이므로 모든 비밀을 잡지는 못한다(형식이 다른 토큰, 일반 문장 속 개인정보 등). 따라서 safe-mode 는 노출을 줄이는 보조 수단이고, 민감한 저장소에서는 diff 를 보내도 되는지 먼저 판단해야 한다.

**코드 근거**: `gitgen/sanitize.py` 의 `apply_safe_mode`
