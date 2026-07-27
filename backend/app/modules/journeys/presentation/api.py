from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.journeys.application.use_cases.manage_journeys import (
    JourneyNotFoundError,
    JourneyNotStartedError,
    JourneyService,
)
from app.modules.journeys.domain.entities.journey import Journey, JourneyDetail, JourneyPosition
from app.modules.journeys.infrastructure.persistence.journey_repository import (
    SQLAlchemyJourneyRepository,
)
from app.modules.journeys.presentation.schemas import (
    JourneyDetailReadSchema,
    JourneyFinishSchema,
    JourneyPositionReadSchema,
    JourneyPositionsBatchSchema,
    JourneyReadSchema,
    JourneyStartSchema,
)
from app.modules.users.domain.entities.user import User
from app.modules.users.presentation.dependencies import get_current_user
from app.shared.infrastructure.db import get_async_session


router = APIRouter(tags=["journeys"])


def get_journey_service(
    session: AsyncSession = Depends(get_async_session),
) -> JourneyService:
    return JourneyService(SQLAlchemyJourneyRepository(session))


def _journey_response(journey: Journey) -> JourneyReadSchema:
    if journey.id is None:
        raise RuntimeError("Persisted journey has no identifier")
    return JourneyReadSchema(
        id=journey.id,
        user_id=journey.user_id,
        status=journey.status,
        profile=journey.profile,
        start=journey.start_location,
        end=journey.end_location,
        planned_distance_m=journey.planned_distance_m,
        planned_duration_s=journey.planned_duration_s,
        planned_route_geometry=journey.planned_route_geometry,
        actual_distance_m=journey.actual_distance_m,
        actual_duration_s=journey.actual_duration_s,
        started_at=journey.started_at,
        finished_at=journey.finished_at,
        created_at=journey.created_at,
        updated_at=journey.updated_at,
    )


def _position_response(position: JourneyPosition) -> JourneyPositionReadSchema:
    if position.id is None:
        raise RuntimeError("Persisted journey position has no identifier")
    return JourneyPositionReadSchema(
        id=position.id,
        journey_id=position.journey_id,
        location=position.location,
        accuracy_m=position.accuracy_m,
        speed_mps=position.speed_mps,
        recorded_at=position.recorded_at,
        created_at=position.created_at,
    )


def _detail_response(detail: JourneyDetail) -> JourneyDetailReadSchema:
    journey = _journey_response(detail.journey)
    return JourneyDetailReadSchema(
        **journey.model_dump(),
        positions=[_position_response(position) for position in detail.positions],
    )


@router.post("/journeys/start", response_model=JourneyReadSchema, status_code=201)
async def start_journey(
    payload: JourneyStartSchema,
    current_user: User = Depends(get_current_user),
    service: JourneyService = Depends(get_journey_service),
) -> JourneyReadSchema:
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    journey = await service.start_journey(
        Journey(
            user_id=current_user.id,
            profile=payload.profile,
            start_location=payload.start.model_dump(),
            end_location=payload.end.model_dump(),
            planned_distance_m=payload.planned_distance_m,
            planned_duration_s=payload.planned_duration_s,
            planned_route_geometry=payload.planned_route_geometry,
        )
    )
    return _journey_response(journey)


@router.post(
    "/journeys/{journey_id}/positions",
    response_model=list[JourneyPositionReadSchema],
    status_code=201,
)
async def add_journey_positions(
    journey_id: int,
    payload: JourneyPositionsBatchSchema,
    current_user: User = Depends(get_current_user),
    service: JourneyService = Depends(get_journey_service),
) -> list[JourneyPositionReadSchema]:
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        positions = await service.add_positions(
            journey_id=journey_id,
            user_id=current_user.id,
            positions=[
                JourneyPosition(
                    journey_id=journey_id,
                    location={"lat": item.lat, "lng": item.lng},
                    accuracy_m=item.accuracy_m,
                    speed_mps=item.speed_mps,
                    recorded_at=item.recorded_at,
                )
                for item in payload.positions
            ],
        )
    except JourneyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except JourneyNotStartedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return [_position_response(position) for position in positions]


@router.post("/journeys/{journey_id}/finish", response_model=JourneyReadSchema)
async def finish_journey(
    journey_id: int,
    payload: JourneyFinishSchema | None = None,
    current_user: User = Depends(get_current_user),
    service: JourneyService = Depends(get_journey_service),
) -> JourneyReadSchema:
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        journey = await service.finish_journey(
            journey_id=journey_id,
            user_id=current_user.id,
            finished_at=(payload or JourneyFinishSchema()).finished_at,
        )
    except JourneyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except JourneyNotStartedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _journey_response(journey)


@router.get("/journeys/{journey_id}", response_model=JourneyDetailReadSchema)
async def get_journey(
    journey_id: int,
    current_user: User = Depends(get_current_user),
    service: JourneyService = Depends(get_journey_service),
) -> JourneyDetailReadSchema:
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        detail = await service.get_journey(journey_id=journey_id, user_id=current_user.id)
    except JourneyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _detail_response(detail)


@router.get("/journeys", response_model=list[JourneyReadSchema])
async def list_journeys(
    current_user: User = Depends(get_current_user),
    service: JourneyService = Depends(get_journey_service),
) -> list[JourneyReadSchema]:
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return [
        _journey_response(journey)
        for journey in await service.list_journeys(user_id=current_user.id)
    ]
