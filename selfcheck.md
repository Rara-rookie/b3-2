| 요구사항 | 상태 | 근거 |
|---|---|---|
| Git이 초기화된 루트에서 실행, git status 수집 | 충족 | `gitctx.py` `_run_git(['status','--porcelain'],cwd)`, 실행: `[INFO] Git status 수집 완료: 3개 파일 변경 감지` |
| git diff 결과 수집 | 충족 | `gitctx.py` `_run_git(['diff','HEAD'],cwd)`, 실행: `[INFO] Git diff 수집 완료: 8줄` |
| 변경 사항 없을 때 안내 후 종료 | 충족 | `cli.py` `has_changes(ctx)` 미충족 시 `[INFO] 변경 사항이 없습니다...` return 0 (`gitctx.has_changes`가 status/diff 모두 확인) |
| API Key 환경변수 관리, 하드코딩 금지 | 충족 | `aiclient.py` `os.environ.get('AI_API_KEY')`, 없으면 `ApiKeyMissingError`; 실행: `[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.` |
| AI API 호출 후 커밋/PR 텍스트 출력 | 충족 | 실행: `[DONE] 커밋 메시지 생성 완료` + `--- Commit Message ---` 블록 출력 (인터프리터가 실제 응답 렌더) |
| API 호출 실패 시 원인 포함 메시지 | 충족 | `aiclient.py` HTTPError/URLError→`ApiCallError('AI API 호출 실패', 원인)`, `cli.py` `[ERROR] AI API 호출 실패: {cause}` |
| 파라미터를 CLI 옵션으로 변경 가능 | 충족 | `cli.py` `--model`,`--temperature`,`--max-tokens` argparse; 실행: `--temperature abc` → invalid float value 에러 |
| commit 명령으로 커밋 메시지 생성/출력 | 충족 | `cli.py run_commit`, 실행 출력에 `--- Commit Message ---` 및 `feat: a.txt 추가` |
| 커밋 제목 1줄 필수 포함 | 충족 | `formatter.render_commit` `title=trim_commit_title(lines[0])`, 실행: `feat: a.txt 추가` |
| 커밋 본문 선택적/요약 품질 기준 | 충족 | 프롬프트 `prompts.build_commit_prompt` 본문 규칙 명시, 실행 본문에 파일 언급 불릿 존재 |
| PR 제목/본문 생성 명령 | 충족 | `cli.py run_pr`, `formatter.render_pr` `--- PR Title ---`/`--- PR Body ---` |
| PR 본문 Why/What/How to Test 헤더 포함 | 충족 | `formatter.ensure_pr_sections` 세 섹션 항상 생성 |
| 각 섹션 최소 1개 불릿 | 충족 | `formatter._normalize_section_content` fallback 불릿 삽입 보장 |
| PR 제목 1줄 출력 | 충족 | `formatter.render_pr` `title=trim_pr_title(lines[0])` |
| 커밋 제목 72자 이내 | 충족 | `formatter.trim_commit_title(max_len=72)` |
| PR 제목 80자 이내 | 충족 | `formatter.trim_pr_title(max_len=80)` |
| 최종 출력 구획 구분 | 충족 | `formatter` 헤더/바닥글 `--- Commit Message ---`/`----------------------`, `--- PR Title ---` |
| safe-mode 마스킹/diff 제한 옵션 | 충족 | `cli.py --safe-mode`, `sanitize.apply_safe_mode`→`mask_secrets`,`limit_diff(max_files=10,max_lines=200)` |
| 명령당 API 1회 호출 및 로그 | 충족 | `cli.py` `[INFO] AI API 호출 횟수: 1` 후 `client.complete` 1회; 실행 출력 확인 |
| GitHub 리포지토리 push | 미흡 | 제공된 파일/실행 결과에 원격 저장소나 push 증빙 없음 |
| README 설치/환경변수/사용예시/출력예시/민감정보 또는 비용 | 충족 | `README.md`에 설치, `export AI_API_KEY`, commit/pr 예시, 출력 예시, 민감정보 보호 및 비용/요청 제한 섹션 존재 |
