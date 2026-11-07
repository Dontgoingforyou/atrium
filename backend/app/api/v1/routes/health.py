from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Проверка живости процесса")
async def health() -> dict[str, str]:
    return {"status": "ok"}
