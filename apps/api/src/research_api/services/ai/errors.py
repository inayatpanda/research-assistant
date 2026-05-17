class AIError(Exception):
    """Base for AI adapter errors."""

    def __init__(self, message: str, *, provider: str = "?") -> None:
        super().__init__(message)
        self.provider = provider


class AIProviderUnavailable(AIError):
    """Provider is unreachable, misconfigured, or all chained models exhausted."""


class AIRateLimited(AIError):
    """Provider returned 429 after exhausting retries."""


class AISafetyBlocked(AIError):
    """Provider's safety filter rejected the output."""


class AISourceInsufficient(AIError):
    """The prompt's source text was too sparse for grounded extraction."""
