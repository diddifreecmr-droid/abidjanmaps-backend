from dataclasses import dataclass


@dataclass(frozen=True)
class Price:
    amount: int
    currency: str = "XOF"
