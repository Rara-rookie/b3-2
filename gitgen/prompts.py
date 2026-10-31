from .gitctx import GitContext


def _format_changed_files(changed_files: list[str]) -> str:
    if not changed_files:
        return '- (변경 파일 없음)'
    return '\n'.join(f'- {path}' for path in changed_files[:10])


def _format_diff(diff: str) -> str:
    return diff.strip() if diff.strip() else '(diff 없음)'


def build_commit_prompt(ctx: GitContext) -> tuple[str, str]:
    system_prompt = (
        '당신은 Git 변경 사항을 읽고 한국어 커밋 메시지를 작성하는 도우미입니다.\n'
        '반드시 변경 내용에 근거해서만 작성하세요.\n'
        '출력은 커밋 메시지 본문만 반환하세요. 설명, 인사, 코드펜스는 금지합니다.\n'
        '형식 규칙:\n'
        '1) 첫 줄은 커밋 제목 1줄입니다.\n'
        '2) 가능하면 conventional commit 스타일(feat, fix, refactor, docs, test, chore) 중 하나를 사용하세요.\n'
        '3) 제목은 간결하고 구체적으로 작성하세요.\n'
        '4) 본문을 포함한다면 빈 줄 뒤에 불릿 목록으로 작성하세요.\n'
        '5) 본문에는 변경된 파일 또는 모듈 1~3개 언급 또는 핵심 변경 사항 1~2개 요약 중 최소 하나를 포함하세요.\n'
        '6) 과장 표현, 확인 불가한 테스트 결과, 변경되지 않은 내용은 쓰지 마세요.'
    )

    user_prompt = (
        '다음 Git 변경 사항을 바탕으로 커밋 메시지를 생성하세요.\n\n'
        f'브랜치: {ctx.branch or "(알 수 없음)"}\n\n'
        '변경 파일:\n'
        f'{_format_changed_files(ctx.changed_files)}\n\n'
        'git status --porcelain:\n'
        f'{ctx.status.strip() or "(status 없음)"}\n\n'
        'git diff HEAD:\n'
        f'{_format_diff(ctx.diff)}'
    )
    return system_prompt, user_prompt


def build_pr_prompt(ctx: GitContext) -> tuple[str, str]:
    system_prompt = (
        '당신은 Git 변경 사항을 읽고 한국어 Pull Request 초안을 작성하는 도우미입니다.\n'
        '반드시 제공된 변경 내용에 근거해서만 작성하세요.\n'
        '출력은 아래 형식을 정확히 따르세요. 설명, 인사, 코드펜스는 금지합니다.\n'
        '첫 줄: PR 제목 1줄\n'
        '둘째 줄 이후: PR 본문\n\n'
        '본문 규칙:\n'
        '- 반드시 "## Why", "## What", "## How to Test" 섹션 헤더를 포함하세요.\n'
        '- 각 섹션에는 최소 1개 이상의 불릿(- )을 포함하세요.\n'
        '- PR 제목은 한 줄로 간결하게 작성하세요.\n'
        '- What 섹션에는 핵심 변경 사항을 구체적으로 쓰세요.\n'
        '- How to Test 섹션에는 실제로 확인 가능한 실행 또는 검증 방법만 쓰세요.\n'
        '- 변경 사실이 아닌 추측, 과장, 확인 불가 내용은 금지합니다.'
    )

    user_prompt = (
        '다음 Git 변경 사항을 바탕으로 PR 제목과 본문 초안을 작성하세요.\n\n'
        f'현재 브랜치: {ctx.branch or "(알 수 없음)"}\n\n'
        '변경 파일:\n'
        f'{_format_changed_files(ctx.changed_files)}\n\n'
        'git status --porcelain:\n'
        f'{ctx.status.strip() or "(status 없음)"}\n\n'
        'git diff HEAD:\n'
        f'{_format_diff(ctx.diff)}'
    )
    return system_prompt, user_prompt
