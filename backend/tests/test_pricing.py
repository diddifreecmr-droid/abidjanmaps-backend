from app.modules.routing.infrastructure.pricing.default_pricing_service import (
    DefaultPricingService,
)


def test_pricing_respects_minimum_fare() -> None:
    service = DefaultPricingService()
    price = service.calculate_price(distance_m=100, duration_s=60, profile="car")
    assert price.amount >= 1000
