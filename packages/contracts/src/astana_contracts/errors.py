"""Safe public validation errors: never include payload values or provider details."""
from __future__ import annotations


class ContractError(ValueError):
    """Base contract failure with a safe, structured description."""


class ContractValidationError(ContractError):
    def __init__(
        self, *, definition: str, code: str, message: str,
        path: tuple[str | int, ...] = (), stage: str = "schema",
    ) -> None:
        self.definition = definition
        self.code = code
        self.message = message
        self.path = path
        self.stage = stage
        super().__init__(message)

    def as_dict(self) -> dict[str, object]:
        """Return safe diagnostics suitable for an API error mapper."""
        return {"definition": self.definition, "code": self.code,
                "message": self.message, "path": list(self.path), "stage": self.stage}
