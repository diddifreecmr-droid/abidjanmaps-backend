from app.modules.routing.domain.entities.price import Price
from app.modules.routing.domain.services.pricing import PricingService
from app.shared.configuration.settings import settings


class DefaultPricingService(PricingService):
    def calculate_price(self, distance_m: int, duration_s: int, profile: str) -> Price:
        distance_km = distance_m / 1000
        duration_min = duration_s / 60
        raw_amount = (
            settings.base_fare_xof
            + distance_km * settings.price_per_km_xof
            + duration_min * settings.price_per_minute_xof
        )
        amount = int(round(raw_amount / settings.fare_rounding_xof) * settings.fare_rounding_xof)
        amount = max(amount, settings.minimum_fare_xof)
        return Price(amount=amount)
