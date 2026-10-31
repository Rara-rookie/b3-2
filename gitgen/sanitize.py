import re


_EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
_SK_TOKEN_RE = re.compile(r'\bsk-[A-Za-z0-9_-]{17,}\b')
_API_KEY_ASSIGN_RE = re.compile(r'(AI_API_KEY\s*=\s*)([^\s\'"]+|".*?"|\'.*?\')')


def mask_secrets(text: str) -> str:
    masked = _EMAIL_RE.sub('[MASKED_EMAIL]', text)
    masked = _SK_TOKEN_RE.sub('[MASKED_KEY]', masked)
    masked = _API_KEY_ASSIGN_RE.sub(r'\1[MASKED_KEY]', masked)
    return masked


def limit_diff(diff: str, max_files: int = 10, max_lines: int = 200) -> str:
    if not diff:
        return diff

    lines = diff.splitlines()
    if not lines:
        return diff

    limited_lines: list[str] = []
    file_count = 0
    in_file = False

    for line in lines:
        if line.startswith('diff --git '):
            if file_count >= max_files:
                break
            file_count += 1
            in_file = True
        elif not in_file and file_count == 0:
            in_file = True

        if len(limited_lines) >= max_lines:
            break

        limited_lines.append(line)

    result = '\n'.join(limited_lines)
    if diff.endswith('\n') and result:
        result += '\n'
    return result


def apply_safe_mode(diff: str, enabled: bool) -> str:
    if not enabled:
        return diff
    return limit_diff(mask_secrets(diff), max_files=10, max_lines=200)
