class ToolError(Exception):
    """Stable machine-readable error code; messages must not include user data."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
