from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.modules.auth import service
from app.modules.auth.schemas import LoginRequest, TokenResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse, summary="管理员登录")
def login(data: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return service.login(db, data)
