import subprocess

from .errors import GitError


class GitContext:
    def __init__(self, branch: str, status: str, changed_files: list[str], diff: str):
        self.branch = branch
        self.status = status
        self.changed_files = changed_files
        self.diff = diff


def _run_git(args: list[str], cwd: str, strip: bool = True) -> str:
    try:
        completed = subprocess.run(
            ['git', *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
        )
        return completed.stdout.strip() if strip else completed.stdout
    except FileNotFoundError as exc:
        raise GitError('git 명령을 찾을 수 없습니다.') from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or 'git 명령 실행에 실패했습니다.'
        raise GitError(message) from exc


def _parse_changed_files(status: str) -> list[str]:
    files: list[str] = []
    for line in status.splitlines():
        if not line.strip():
            continue
        path_part = line[3:] if len(line) >= 3 else ''
        if not path_part:
            continue
        if ' -> ' in path_part:
            path_part = path_part.split(' -> ', 1)[1]
        files.append(path_part)
    return files


def collect(cwd: str = '.') -> GitContext:
    branch = _run_git(['branch', '--show-current'], cwd)
    status = _run_git(['status', '--porcelain'], cwd)
    diff = _run_git(['diff', 'HEAD'], cwd, strip=False)
    changed_files = _parse_changed_files(status)
    return GitContext(branch=branch, status=status, changed_files=changed_files, diff=diff)


def has_changes(ctx: GitContext) -> bool:
    return bool(ctx.status.strip() or ctx.diff.strip())
