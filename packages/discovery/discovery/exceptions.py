"""Custom exceptions for the Lens discovery pipeline.

These exceptions allow distinguishing infrastructure failures (unavailable
provider, exhausted credits, bad credentials) from business results
("no candidates found"). An infrastructure failure should abort the run,
not silently return an empty list.
"""


class SourceUnavailable(Exception):
    """The data provider cannot serve requests at all.

    Caused by: 401 (bad credentials), 402 (credits exhausted),
    403 (forbidden), 429 (rate limited), or a circuit breaker opening.

    The run should abort immediately with status='failed' and a message
    that tells the user exactly what to do (e.g. "recargar en
    hikerapi.com/billing").
    """

    def __init__(self, message: str, status_code: int | None = None, provider: str = "hikerapi"):
        super().__init__(message)
        self.status_code = status_code
        self.provider = provider
        self.message = message

    def __repr__(self) -> str:
        return f"SourceUnavailable({self.provider}, status={self.status_code!r}, msg={self.message!r})"


class TransientSourceError(Exception):
    """A temporary source failure that may succeed on retry.

    Caused by: 5xx errors, timeouts.

    These should be counted by the circuit breaker. After N consecutive
    failures the circuit opens and SourceUnavailable is raised instead.
    """

    def __init__(self, message: str, status_code: int | None = None, provider: str = "hikerapi"):
        super().__init__(message)
        self.status_code = status_code
        self.provider = provider
        self.message = message

    def __repr__(self) -> str:
        return f"TransientSourceError({self.provider}, status={self.status_code!r}, msg={self.message!r})"


class BudgetExhausted(Exception):
    """Monthly budget or per-run call limit has been reached.

    The run should abort with status='partial' or 'failed' and a
    message indicating the budget state.
    """

    def __init__(self, message: str, current_usd: float | None = None, budget_usd: float | None = None):
        super().__init__(message)
        self.current_usd = current_usd
        self.budget_usd = budget_usd
