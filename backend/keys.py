from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User, ApiKey
from schemas import ApiKeySetRequest
from security import encrypt_secret
from auth import get_current_user
from registry import TOOLS

router = APIRouter(prefix="/api/keys", tags=["keys"])

VALID_SERVICES = {t["service"] for t in TOOLS if t["mode"] == "api" and t.get("requires_key")}


@router.get("")
def list_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Ne renvoie JAMAIS la valeur en clair, seulement quels services sont configurés."""
    configured = {k.service for k in db.query(ApiKey).filter(ApiKey.user_id == user.id).all()}
    return [{"service": s, "configured": s in configured} for s in sorted(VALID_SERVICES)]


@router.post("")
def set_key(body: ApiKeySetRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.service not in VALID_SERVICES:
        raise HTTPException(status_code=422, detail="Service inconnu")

    existing = db.query(ApiKey).filter(ApiKey.user_id == user.id, ApiKey.service == body.service).first()
    encrypted = encrypt_secret(body.value)
    if existing:
        existing.encrypted_value = encrypted
    else:
        db.add(ApiKey(user_id=user.id, service=body.service, encrypted_value=encrypted))
    db.commit()
    return {"ok": True}


@router.delete("/{service}")
def delete_key(service: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(ApiKey).filter(ApiKey.user_id == user.id, ApiKey.service == service).first()
    if existing:
        db.delete(existing)
        db.commit()
    return {"ok": True}
