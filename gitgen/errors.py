class GitGenError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NoChangesError(GitGenError):
    def __init__(self, message: str = '변경 사항이 없습니다.'):
        super().__init__(message)


class ApiKeyMissingError(GitGenError):
    def __init__(self, message: str = 'AI_API_KEY 환경변수가 설정되지 않았습니다.'):
        super().__init__(message)


class ApiCallError(GitGenError):
    def __init__(self, message: str, cause: str | None = None):
        self.cause = cause
        full_message = f'{message}: {cause}' if cause else message
        super().__init__(full_message)


class GitError(GitGenError):
    def __init__(self, message: str):
        super().__init__(message)
