from fastapi import APIRouter

from app.envelope import unavailable

router = APIRouter()

_TWIN_MSG = (
    "Digital twin module is not implemented in the repository yet. "
    "This API does not synthesise cluster scores or placements."
)
_DECISION_MSG = (
    "Migration decision engine is not implemented yet. "
    "No KEEP/MIGRATE rows are generated for demonstration."
)
_MIGRATION_MSG = (
    "Migration controller is not implemented yet. History is empty until reschedules are recorded."
)
_EXPERIMENT_MSG = (
    "Experiment manager is not implemented yet. No evaluation runs are stored."
)


@router.get("/twin/state")
def twin_state():
    return unavailable("none", _TWIN_MSG, data={"nodes": [], "links": [], "workloads": []})


@router.get("/decisions")
def decisions():
    return unavailable("none", _DECISION_MSG, data={"recommendations": []})


@router.get("/migrations")
def migrations():
    return unavailable("none", _MIGRATION_MSG, data={"events": []})


@router.get("/experiments")
def experiments():
    return unavailable("none", _EXPERIMENT_MSG, data={"runs": []})
