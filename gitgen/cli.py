import argparse

from .aiclient import AiClient
from .errors import ApiCallError, ApiKeyMissingError, GitError
from .formatter import render_commit, render_pr
from .gitctx import collect, has_changes
from .prompts import build_commit_prompt, build_pr_prompt
from .sanitize import apply_safe_mode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='gitgen')
    subparsers = parser.add_subparsers(dest='command', required=True)

    def _add_common_options(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument('--model', default='gpt-5.4-mini')
        subparser.add_argument('--temperature', type=float, default=0.2)
        subparser.add_argument('--max-tokens', type=int, default=512)
        subparser.add_argument('--safe-mode', action='store_true', default=False)

    commit_parser = subparsers.add_parser('commit')
    _add_common_options(commit_parser)

    pr_parser = subparsers.add_parser('pr')
    _add_common_options(pr_parser)

    return parser


def run_commit(args: argparse.Namespace) -> int:
    try:
        ctx = collect('.')
        if not has_changes(ctx):
            print('[INFO] 변경 사항이 없습니다. 커밋 메시지를 생성하지 않고 종료합니다.')
            return 0

        print(f'[INFO] Git status 수집 완료: {len(ctx.changed_files)}개 파일 변경 감지')
        diff_for_prompt = apply_safe_mode(ctx.diff, args.safe_mode)
        diff_lines = len(diff_for_prompt.splitlines()) if diff_for_prompt else 0
        print(f'[INFO] Git diff 수집 완료: {diff_lines}줄')

        ctx.diff = diff_for_prompt
        system_prompt, user_prompt = build_commit_prompt(ctx)

        client = AiClient.from_env(
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )

        print('[INFO] AI API 호출 횟수: 1')
        print('[INFO] AI API 요청 중...')
        raw = client.complete(system_prompt, user_prompt)
        print('[DONE] 커밋 메시지 생성 완료')
        print()
        print(render_commit(raw))
        return 0
    except ApiKeyMissingError:
        print('[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.')
        return 1
    except ApiCallError as exc:
        cause = exc.cause if exc.cause else exc.message
        print(f'[ERROR] AI API 호출 실패: {cause}')
        return 1
    except GitError as exc:
        print(f'[ERROR] {exc.message}')
        return 1
    except Exception as exc:
        print(f'[ERROR] 예기치 않은 오류가 발생했습니다: {exc}')
        return 1


def run_pr(args: argparse.Namespace) -> int:
    try:
        ctx = collect('.')
        if not has_changes(ctx):
            print('[INFO] 변경 사항이 없습니다. 커밋 메시지를 생성하지 않고 종료합니다.')
            return 0

        print(f'[INFO] 현재 브랜치: {ctx.branch or "(알 수 없음)"}')
        diff_for_prompt = apply_safe_mode(ctx.diff, args.safe_mode)
        ctx.diff = diff_for_prompt
        system_prompt, user_prompt = build_pr_prompt(ctx)

        client = AiClient.from_env(
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )

        print('[INFO] AI API 호출 횟수: 1')
        print('[INFO] AI API 요청 중...')
        raw = client.complete(system_prompt, user_prompt)
        print('[DONE] PR 초안 생성 완료')
        print()
        print(render_pr(raw))
        return 0
    except ApiKeyMissingError:
        print('[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.')
        return 1
    except ApiCallError as exc:
        cause = exc.cause if exc.cause else exc.message
        print(f'[ERROR] AI API 호출 실패: {cause}')
        return 1
    except GitError as exc:
        print(f'[ERROR] {exc.message}')
        return 1
    except Exception as exc:
        print(f'[ERROR] 예기치 않은 오류가 발생했습니다: {exc}')
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == 'commit':
        return run_commit(args)
    if args.command == 'pr':
        return run_pr(args)
    parser.print_help()
    return 1
