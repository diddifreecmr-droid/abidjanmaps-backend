from datetime import datetime, timezone
from math import atan2, cos, radians, sin, sqrt

from app.modules.journeys.application.ports.journey_repository import JourneyRepository
from app.modules.journeys.domain.entities.journey import (
    JourneyAnalysis,
    Journey,
    JourneyDetail,
    JourneyPosition,
    MapTraceInsight,
    MAP_TRACE_INSIGHT_STATUSES,
)


class JourneyNotFoundError(Exception):
    pass


class JourneyNotStartedError(Exception):
    pass


class JourneyNotFinishedError(Exception):
    pass


class JourneyAnalysisNotFoundError(Exception):
    pass


class MapTraceInsightNotFoundError(Exception):
    pass


class InvalidMapTraceInsightStatusError(Exception):
    pass


class JourneyService:
    def __init__(self, repository: JourneyRepository) -> None:
        self.repository = repository

    async def start_journey(self, journey: Journey) -> Journey:
        return await self.repository.create(journey)

    async def add_positions(
        self,
        *,
        journey_id: int,
        user_id: int,
        positions: list[JourneyPosition],
    ) -> list[JourneyPosition]:
        detail = await self.repository.get_detail(journey_id, user_id)
        if detail is None:
            raise JourneyNotFoundError("Journey not found")
        if detail.journey.status != "started":
            raise JourneyNotStartedError("Journey is not accepting positions")
        saved = await self.repository.add_positions(journey_id, positions)
        if saved is None:
            raise JourneyNotFoundError("Journey not found")
        return saved

    async def finish_journey(
        self,
        *,
        journey_id: int,
        user_id: int,
        finished_at: datetime | None = None,
    ) -> Journey:
        detail = await self.repository.get_detail(journey_id, user_id)
        if detail is None:
            raise JourneyNotFoundError("Journey not found")
        if detail.journey.status != "started":
            raise JourneyNotStartedError("Journey is not started")

        final_finished_at = _ensure_aware(finished_at or datetime.now(timezone.utc))
        started_at = _ensure_aware(detail.journey.started_at or final_finished_at)
        actual_duration_s = max(int((final_finished_at - started_at).total_seconds()), 0)
        actual_distance_m = _total_distance_m(detail.positions)
        finished = await self.repository.finish(
            journey_id,
            user_id,
            finished_at=final_finished_at,
            actual_distance_m=actual_distance_m,
            actual_duration_s=actual_duration_s,
        )
        if finished is None:
            raise JourneyNotFoundError("Journey not found")
        return finished

    async def get_journey(self, *, journey_id: int, user_id: int) -> JourneyDetail:
        detail = await self.repository.get_detail(journey_id, user_id)
        if detail is None:
            raise JourneyNotFoundError("Journey not found")
        return detail

    async def get_trace_detail_for_admin(self, *, trace_id: int) -> JourneyDetail:
        detail = await self.repository.get_detail_for_admin(trace_id)
        if detail is None:
            raise JourneyNotFoundError("Map trace not found")
        return detail

    async def list_journeys(self, *, user_id: int) -> list[Journey]:
        return await self.repository.list_for_user(user_id)

    async def analyze_journey(self, *, journey_id: int, user_id: int) -> JourneyAnalysis:
        detail = await self.repository.get_detail(journey_id, user_id)
        if detail is None:
            raise JourneyNotFoundError("Journey not found")
        if detail.journey.status != "finished":
            raise JourneyNotFinishedError("Journey must be finished before analysis")
        analysis = _analyze_detail(detail)
        saved = await self.repository.save_analysis(journey_id, user_id, analysis)
        if saved is None:
            raise JourneyNotFoundError("Journey not found")
        if saved.id is not None:
            await self.repository.replace_proposed_insights(
                saved.id,
                _insights_from_analysis(saved, detail),
            )
        return saved

    async def get_analysis(self, *, journey_id: int, user_id: int) -> JourneyAnalysis:
        analysis = await self.repository.get_analysis(journey_id, user_id)
        if analysis is None:
            raise JourneyAnalysisNotFoundError("Journey analysis not found")
        return analysis

    async def list_insights(
        self,
        *,
        status: str | None = None,
        insight_type: str | None = None,
        severity_min: int | None = None,
        trace_id: int | None = None,
    ) -> list[MapTraceInsight]:
        if status is not None and status not in MAP_TRACE_INSIGHT_STATUSES:
            raise InvalidMapTraceInsightStatusError(f"Unsupported insight status: {status}")
        if severity_min is not None and not 1 <= severity_min <= 5:
            raise InvalidMapTraceInsightStatusError("severity_min must be between 1 and 5")
        return await self.repository.list_insights(
            status=status,
            insight_type=insight_type,
            severity_min=severity_min,
            trace_id=trace_id,
        )

    async def get_insight(self, *, insight_id: int) -> MapTraceInsight:
        insight = await self.repository.get_insight(insight_id)
        if insight is None:
            raise MapTraceInsightNotFoundError("Map trace insight not found")
        return insight

    async def review_insight(
        self,
        *,
        insight_id: int,
        status: str,
        reviewed_by: int,
        review_note: str | None = None,
    ) -> MapTraceInsight:
        if status not in {"validated", "rejected"}:
            raise InvalidMapTraceInsightStatusError(f"Unsupported review status: {status}")
        insight = await self.repository.review_insight(
            insight_id,
            status=status,
            reviewed_by=reviewed_by,
            review_note=review_note,
            reviewed_at=datetime.now(timezone.utc),
        )
        if insight is None:
            raise MapTraceInsightNotFoundError("Map trace insight not found")
        return insight


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _total_distance_m(positions: list[JourneyPosition]) -> float:
    if len(positions) < 2:
        return 0.0
    ordered = sorted(
        positions,
        key=lambda position: (
            position.recorded_at or datetime.min.replace(tzinfo=timezone.utc),
            position.id or 0,
        ),
    )
    return round(
        sum(
            _distance_m(
                ordered[index - 1].location["lat"],
                ordered[index - 1].location["lng"],
                ordered[index].location["lat"],
                ordered[index].location["lng"],
            )
            for index in range(1, len(ordered))
        ),
        2,
    )


def _distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    earth_radius_m = 6_371_000
    phi1 = radians(lat1)
    phi2 = radians(lat2)
    delta_phi = radians(lat2 - lat1)
    delta_lambda = radians(lng2 - lng1)

    haversine = (
        sin(delta_phi / 2) ** 2
        + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
    )
    return earth_radius_m * 2 * atan2(sqrt(haversine), sqrt(1 - haversine))


MAX_CREDIBLE_SPEED_MPS = 45.0
MAX_GOOD_ACCURACY_M = 50.0
MAX_ACCEPTABLE_TIME_GAP_S = 300
STOPPED_SPEED_MPS = 0.8
SLOW_SEGMENT_SPEED_MPS = 2.2
SLOW_SEGMENT_MIN_DURATION_S = 120
BLOCKED_ROAD_MIN_DURATION_RATIO = 2.5
BLOCKED_ROAD_MAX_AVERAGE_SPEED_KMH = 4.0
DETOUR_MIN_DISTANCE_RATIO = 1.35
DETOUR_MIN_DISTANCE_DELTA_M = 500


def _analyze_detail(detail: JourneyDetail) -> JourneyAnalysis:
    ordered = _ordered_positions(detail.positions)
    points_count = len(ordered)
    usable_positions = [
        position
        for position in ordered
        if position.accuracy_m is None or position.accuracy_m <= MAX_GOOD_ACCURACY_M
    ]
    segment_metrics = _segment_metrics(usable_positions)
    segments = segment_metrics["segments"]
    actual_distance_m = round(sum(segment["distance_m"] for segment in segments), 2)
    actual_duration_s = _analysis_duration_s(detail)
    average_speed_kmh = _speed_kmh(actual_distance_m, actual_duration_s)
    phone_average_speed_kmh = _phone_average_speed_kmh(usable_positions)
    moving_time_s = int(
        sum(
            segment["elapsed_s"]
            for segment in segments
            if segment["speed_mps"] >= STOPPED_SPEED_MPS
        )
    )
    stopped_time_s = int(
        sum(
            segment["elapsed_s"]
            for segment in segments
            if segment["speed_mps"] < STOPPED_SPEED_MPS
        )
    )
    max_speed_kmh = round(
        max([segment["speed_mps"] for segment in segments], default=0) * 3.6,
        2,
    )
    gps_gap_count = int(segment_metrics["gps_gap_count"])
    suspicious_jump_count = int(segment_metrics["suspicious_jump_count"])
    quality_score = _quality_score(
        points_count,
        len(usable_positions),
        segments,
        gps_gap_count=gps_gap_count,
        suspicious_jump_count=suspicious_jump_count,
    )
    quality_label = _quality_label(quality_score)
    distance_delta_m = (
        round(actual_distance_m - detail.journey.planned_distance_m, 2)
        if detail.journey.planned_distance_m is not None
        else None
    )
    duration_delta_s = (
        actual_duration_s - detail.journey.planned_duration_s
        if detail.journey.planned_duration_s is not None
        else None
    )
    duration_ratio = (
        round(actual_duration_s / detail.journey.planned_duration_s, 2)
        if detail.journey.planned_duration_s
        else None
    )
    events = _detected_events(
        points_count=points_count,
        usable_points_count=len(usable_positions),
        actual_duration_s=actual_duration_s,
        actual_distance_m=actual_distance_m,
        planned_distance_m=detail.journey.planned_distance_m,
        duration_ratio=duration_ratio,
        average_speed_kmh=average_speed_kmh,
        segments=segments,
        gps_gap_count=gps_gap_count,
        suspicious_jump_count=suspicious_jump_count,
    )
    recommendation = _recommendation(quality_label, events)
    return JourneyAnalysis(
        journey_id=detail.journey.id or 0,
        points_count=points_count,
        usable_points_count=len(usable_positions),
        quality_score=quality_score,
        quality_label=quality_label,
        actual_distance_m=actual_distance_m,
        actual_duration_s=actual_duration_s,
        average_speed_kmh=average_speed_kmh,
        phone_average_speed_kmh=phone_average_speed_kmh,
        moving_time_s=moving_time_s,
        stopped_time_s=stopped_time_s,
        max_speed_kmh=max_speed_kmh,
        gps_gap_count=gps_gap_count,
        suspicious_jump_count=suspicious_jump_count,
        planned_distance_m=detail.journey.planned_distance_m,
        planned_duration_s=detail.journey.planned_duration_s,
        distance_delta_m=distance_delta_m,
        duration_delta_s=duration_delta_s,
        duration_ratio=duration_ratio,
        detected_events=events,
        recommendation=recommendation,
    )


def _ordered_positions(positions: list[JourneyPosition]) -> list[JourneyPosition]:
    return sorted(
        positions,
        key=lambda position: (
            _ensure_aware(position.recorded_at or datetime.min.replace(tzinfo=timezone.utc)),
            position.id or 0,
        ),
    )


def _segment_metrics(positions: list[JourneyPosition]) -> dict[str, object]:
    segments: list[dict[str, float]] = []
    gps_gap_count = 0
    suspicious_jump_count = 0
    for index in range(1, len(positions)):
        previous = positions[index - 1]
        current = positions[index]
        if previous.recorded_at is None or current.recorded_at is None:
            continue
        elapsed_s = (
            _ensure_aware(current.recorded_at) - _ensure_aware(previous.recorded_at)
        ).total_seconds()
        if elapsed_s <= 0:
            continue
        if elapsed_s > MAX_ACCEPTABLE_TIME_GAP_S:
            gps_gap_count += 1
        distance_m = _distance_m(
            previous.location["lat"],
            previous.location["lng"],
            current.location["lat"],
            current.location["lng"],
        )
        speed_mps = distance_m / elapsed_s
        if speed_mps > MAX_CREDIBLE_SPEED_MPS:
            suspicious_jump_count += 1
            continue
        segments.append(
            {
                "distance_m": distance_m,
                "elapsed_s": elapsed_s,
                "speed_mps": speed_mps,
            }
        )
    return {
        "segments": segments,
        "gps_gap_count": gps_gap_count,
        "suspicious_jump_count": suspicious_jump_count,
    }


def _analysis_duration_s(detail: JourneyDetail) -> int:
    if detail.journey.actual_duration_s is not None:
        return detail.journey.actual_duration_s
    if detail.journey.started_at and detail.journey.finished_at:
        return max(
            int(
                (
                    _ensure_aware(detail.journey.finished_at)
                    - _ensure_aware(detail.journey.started_at)
                ).total_seconds()
            ),
            0,
        )
    ordered = _ordered_positions(detail.positions)
    dated = [position for position in ordered if position.recorded_at is not None]
    if len(dated) < 2:
        return 0
    return max(
        int(
            (
                _ensure_aware(dated[-1].recorded_at)  # type: ignore[arg-type]
                - _ensure_aware(dated[0].recorded_at)  # type: ignore[arg-type]
            ).total_seconds()
        ),
        0,
    )


def _speed_kmh(distance_m: float, duration_s: int) -> float:
    if duration_s <= 0:
        return 0.0
    return round((distance_m / duration_s) * 3.6, 2)


def _phone_average_speed_kmh(positions: list[JourneyPosition]) -> float | None:
    speeds = [
        position.speed_mps
        for position in positions
        if position.speed_mps is not None and position.speed_mps <= MAX_CREDIBLE_SPEED_MPS
    ]
    if not speeds:
        return None
    return round((sum(speeds) / len(speeds)) * 3.6, 2)


def _quality_score(
    points_count: int,
    usable_points_count: int,
    segments: list[dict[str, float]],
    *,
    gps_gap_count: int = 0,
    suspicious_jump_count: int = 0,
) -> float:
    if points_count == 0:
        return 0.0
    point_volume_score = min(points_count / 20, 1)
    usable_ratio_score = usable_points_count / points_count
    segment_ratio_score = len(segments) / max(usable_points_count - 1, 1)
    long_gap_ratio = gps_gap_count / max(len(segments) + gps_gap_count, 1)
    suspicious_ratio = suspicious_jump_count / max(len(segments) + suspicious_jump_count, 1)
    score = (
        point_volume_score * 0.30
        + usable_ratio_score * 0.35
        + segment_ratio_score * 0.25
        + (1 - long_gap_ratio) * 0.10
    )
    score -= min(suspicious_ratio * 0.20, 0.20)
    return round(max(min(score, 1), 0), 2)


def _quality_label(quality_score: float) -> str:
    if quality_score >= 0.8:
        return "good"
    if quality_score >= 0.5:
        return "usable"
    if quality_score > 0:
        return "weak"
    return "bad"


def _detected_events(
    *,
    points_count: int,
    usable_points_count: int,
    actual_duration_s: int,
    actual_distance_m: float,
    planned_distance_m: int | None,
    duration_ratio: float | None,
    average_speed_kmh: float,
    segments: list[dict[str, float]],
    gps_gap_count: int = 0,
    suspicious_jump_count: int = 0,
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    if points_count < 5:
        events.append(
            {
                "type": "low_point_count",
                "severity": 2,
                "message": "Trace courte: peu de positions GPS ont ete recues.",
            }
        )
    if points_count and usable_points_count / points_count < 0.7:
        events.append(
            {
                "type": "low_gps_quality",
                "severity": 3,
                "message": "Plusieurs points GPS sont trop imprecis.",
            }
        )
    if duration_ratio is not None and duration_ratio >= 1.5:
        events.append(
            {
                "type": "duration_much_longer_than_planned",
                "severity": 4,
                "message": "Le trajet reel est nettement plus long que la duree OSRM prevue.",
            }
        )
    if actual_duration_s >= 300 and average_speed_kmh <= 8:
        events.append(
            {
                "type": "slow_journey",
                "severity": 3,
                "message": "La vitesse moyenne calculee est faible.",
            }
        )
    slow_summary = _slow_segment_summary(segments)
    if slow_summary["duration_s"] >= SLOW_SEGMENT_MIN_DURATION_S:
        events.append(
            {
                "type": "possible_slow_segment",
                "severity": 3,
                "message": "Une partie de la trace semble anormalement lente.",
                "slow_duration_s": slow_summary["duration_s"],
                "slow_distance_m": slow_summary["distance_m"],
                "slow_segments_count": slow_summary["count"],
            }
        )
    if (
        duration_ratio is not None
        and duration_ratio >= BLOCKED_ROAD_MIN_DURATION_RATIO
        and actual_duration_s >= 300
        and average_speed_kmh <= BLOCKED_ROAD_MAX_AVERAGE_SPEED_KMH
    ):
        events.append(
            {
                "type": "possible_blocked_road",
                "severity": 5,
                "message": "La trace suggere une route possiblement bloquee ou tres difficile.",
            }
        )
    if planned_distance_m and planned_distance_m > 0:
        distance_ratio = actual_distance_m / planned_distance_m
        distance_delta_m = actual_distance_m - planned_distance_m
        if (
            distance_ratio >= DETOUR_MIN_DISTANCE_RATIO
            and distance_delta_m >= DETOUR_MIN_DISTANCE_DELTA_M
        ):
            events.append(
                {
                    "type": "possible_detour",
                    "severity": 4,
                    "message": "La trace reelle est beaucoup plus longue que la route prevue.",
                    "distance_ratio": round(distance_ratio, 2),
                    "distance_delta_m": round(distance_delta_m, 2),
                }
            )
    if gps_gap_count > 0:
        events.append(
            {
                "type": "gps_time_gap",
                "severity": 2,
                "message": "La trace contient un ou plusieurs trous de temps importants.",
                "count": gps_gap_count,
            }
        )
    if suspicious_jump_count > 0:
        events.append(
            {
                "type": "suspicious_gps_jump",
                "severity": 3,
                "message": "La trace contient un ou plusieurs sauts GPS improbables.",
                "count": suspicious_jump_count,
            }
        )
    return events


def _slow_segment_summary(segments: list[dict[str, float]]) -> dict[str, float | int]:
    slow_segments = [
        segment
        for segment in segments
        if segment["speed_mps"] <= SLOW_SEGMENT_SPEED_MPS
    ]
    return {
        "count": len(slow_segments),
        "duration_s": int(sum(segment["elapsed_s"] for segment in slow_segments)),
        "distance_m": round(sum(segment["distance_m"] for segment in slow_segments), 2),
    }


def _recommendation(quality_label: str, events: list[dict[str, object]]) -> str:
    if quality_label in {"bad", "weak"}:
        return "ignore_for_scoring"
    if any(event.get("severity", 0) >= 4 for event in events):
        return "review_needed"
    return "ok"


def _insights_from_analysis(
    analysis: JourneyAnalysis,
    detail: JourneyDetail,
) -> list[MapTraceInsight]:
    if analysis.id is None:
        return []
    insights: list[MapTraceInsight] = []
    for event in analysis.detected_events:
        insight_type = str(event.get("type", "unknown"))
        geometry = detail.journey.planned_route_geometry
        insights.append(
            MapTraceInsight(
                journey_id=analysis.journey_id,
                analysis_id=analysis.id,
                insight_type=insight_type,
                severity=_event_severity(event),
                confidence_score=_event_confidence(
                    analysis.quality_score,
                    _event_severity(event),
                ),
                message=str(event.get("message", "Observation GPS a revoir.")),
                geometry=geometry,
                duplicate_key=_insight_duplicate_key(insight_type, geometry),
                latest_evidence_trace_id=analysis.journey_id,
            )
        )
    if analysis.recommendation == "ignore_for_scoring" and not insights:
        insight_type = "low_gps_quality"
        geometry = detail.journey.planned_route_geometry
        insights.append(
            MapTraceInsight(
                journey_id=analysis.journey_id,
                analysis_id=analysis.id,
                insight_type=insight_type,
                severity=3,
                confidence_score=round(max(1 - analysis.quality_score, 0.1), 2),
                message="Trace GPS trop faible pour influencer le Map Core.",
                geometry=geometry,
                duplicate_key=_insight_duplicate_key(insight_type, geometry),
                latest_evidence_trace_id=analysis.journey_id,
            )
        )
    return insights


def _insight_duplicate_key(insight_type: str, geometry: dict | None) -> str | None:
    point = _representative_coordinate(geometry)
    if point is None:
        return None
    lng, lat = point
    return f"{insight_type}:{round(lng, 3):.3f}:{round(lat, 3):.3f}"


def _representative_coordinate(geometry: dict | None) -> tuple[float, float] | None:
    if not geometry:
        return None
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Point" and _is_coordinate_pair(coordinates):
        return float(coordinates[0]), float(coordinates[1])
    if geometry_type == "LineString" and isinstance(coordinates, list) and coordinates:
        midpoint = coordinates[len(coordinates) // 2]
        if _is_coordinate_pair(midpoint):
            return float(midpoint[0]), float(midpoint[1])
    return None


def _is_coordinate_pair(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) >= 2
        and isinstance(value[0], (int, float))
        and isinstance(value[1], (int, float))
    )


def _event_severity(event: dict[str, object]) -> int:
    raw = event.get("severity", 1)
    if not isinstance(raw, int):
        return 1
    return max(min(raw, 5), 1)


def _event_confidence(quality_score: float, severity: int) -> float:
    return round(max(min(quality_score * (0.5 + severity / 10), 1), 0.1), 2)
