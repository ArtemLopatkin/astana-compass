"""An optional generator selects verifiable facts, never unrestricted factual prose."""

from dataclasses import dataclass
from typing import Literal, Protocol

from astana_contracts import JSON


@dataclass(frozen=True)
class GroundedReason:
    """Reference an existing known fact and its exact supporting evidence IDs."""

    fact_key: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class GroundedExplanation:
    """The service renders these references in the user's language.

    Restricting generated reasons to existing facts prevents a true citation from
    being attached to a fabricated claim. Activities are generic suggestions, not
    assertions that an amenity, service or event exists.
    """

    why: tuple[GroundedReason, ...]
    suggested_activity: Literal["observe", "explore", "take_break"] = "observe"


class ExplanationGenerator(Protocol):
    async def generate(
        self,
        *,
        locale: str,
        query: str,
        place: JSON,
        constraint_evaluations: list[JSON],
    ) -> GroundedExplanation:
        """Select grounded reasons; receives no private origin or raw request."""
        ...
