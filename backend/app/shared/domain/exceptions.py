class DomainError(Exception):
    """Base class for domain errors."""


class InvalidCoordinateError(DomainError):
    """Raised when a coordinate is invalid."""


class OutOfCoverageError(DomainError):
    """Raised when coordinates are outside the Abidjan coverage area."""


class InvalidProfileError(DomainError):
    """Raised when the routing profile is unsupported."""


class NoRouteFoundError(DomainError):
    """Raised when no route can be found."""


class RoutingEngineUnavailableError(DomainError):
    """Raised when the routing engine is unavailable."""


class RoutingTimeoutError(DomainError):
    """Raised when the routing engine times out."""


class InvalidRoutingResponseError(DomainError):
    """Raised when the routing engine response is invalid."""
