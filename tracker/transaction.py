from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping


@dataclass(frozen=True)
class Transaction:
    category: str
    amount: float
    timestamp: datetime

    @classmethod
    def from_parsed_email(cls, data: Mapping[str, Any]):
        amount = data.get("Amount")
        note = data.get("Note", "unknown")
        date = data.get("Date")

        if amount is None or date is None or not isinstance(date, datetime):
            return None

        try:
            amount_value = float(amount)
        except (TypeError, ValueError):
            return None

        category = note.strip().lower() if isinstance(note, str) and note.strip() else "unknown"
        return cls(category=category, amount=amount_value, timestamp=date)