from __future__ import annotations


def trim_commit_title(title: str, max_len: int = 72) -> str:
    cleaned = " ".join(title.strip().split())
    return cleaned[:max_len]


def trim_pr_title(title: str, max_len: int = 80) -> str:
    cleaned = " ".join(title.strip().split())
    return cleaned[:max_len]


def ensure_pr_sections(body: str) -> str:
    normalized = body.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")

    sections = {
        "Why": [],
        "What": [],
        "How to Test": [],
    }
    current: str | None = None

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        if lower == "## why":
            current = "Why"
            continue
        if lower == "## what":
            current = "What"
            continue
        if lower == "## how to test":
            current = "How to Test"
            continue

        if current is not None:
            sections[current].append(line)

    def _normalize_section_content(items: list[str], fallback: str) -> list[str]:
        bullet_lines = [item.strip() for item in items if item.strip().startswith("- ")]
        if bullet_lines:
            return bullet_lines
        text_lines = [item.strip() for item in items if item.strip()]
        if text_lines:
            return [f"- {text_lines[0]}"]
        return [f"- {fallback}"]

    why_lines = _normalize_section_content(
        sections["Why"],
        "변경 배경을 검토해 주세요.",
    )
    what_lines = _normalize_section_content(
        sections["What"],
        "핵심 변경 사항을 검토해 주세요.",
    )
    how_lines = _normalize_section_content(
        sections["How to Test"],
        "변경 사항에 맞는 테스트 방법을 작성해 주세요.",
    )

    return (
        "## Why\n"
        + "\n".join(why_lines)
        + "\n\n## What\n"
        + "\n".join(what_lines)
        + "\n\n## How to Test\n"
        + "\n".join(how_lines)
    )


def render_commit(raw: str) -> str:
    normalized = raw.strip().replace("\r\n", "\n").replace("\r", "\n")
    if not normalized:
        commit_text = trim_commit_title("")
    else:
        lines = normalized.split("\n")
        title = trim_commit_title(lines[0])
        body_lines = [line.rstrip() for line in lines[1:]]
        while body_lines and not body_lines[0].strip():
            body_lines.pop(0)
        while body_lines and not body_lines[-1].strip():
            body_lines.pop()
        commit_text = title
        if body_lines:
            commit_text += "\n\n" + "\n".join(body_lines)

    return f"--- Commit Message ---\n{commit_text}\n----------------------"


def render_pr(raw: str) -> str:
    normalized = raw.strip().replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n") if normalized else []

    title = trim_pr_title(lines[0] if lines else "")

    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
    ensured_body = ensure_pr_sections(body)

    return f"--- PR Title ---\n{title}\n--- PR Body ---\n{ensured_body}"
