from abc import ABC, abstractmethod

from app.modules.routing.domain.entities.price import Price


class PricingService(ABC):
    @abstractmethod
    def calculate_price(self, distance_m: int, duration_s: int, profile: str) -> Price:
        raise NotImplementedError
