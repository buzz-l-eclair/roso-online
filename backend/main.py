import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import User, ApiKey, AuditLog
from schemas import RunToolRequest
from auth import router as auth_router, get_current_user
from keys import router as keys_router
from registry import TOOLS, TOOLS_BY_ID
from runner import validate_params, run_cli_tool, run_api_tool, is_available
from rate_limit import enforce_rate_limit
from security import decrypt_secret

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ROSO Online")

# En prod, restreins à ton propre domaine Render une fois connu.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(keys_router)


@app.get("/api/tools")
def list_tools(user: User = Depends(get_current_user)):
    out = []
    for t in TOOLS:
        out.append({
            "id": t["id"],
            "name": t["name"],
            "category": t["category"],
            "mode": t["mode"],
            "repo": t.get("repo", ""),
            "notes": t.get("notes", ""),
            "params": [{k: v for k, v in p.items() if k != "pattern"} for p in t.get("params", [])],
            "requires_key": t.get("requires_key", False),
            "service": t.get("service", ""),
            "available": is_available(t) if t["mode"] == "cli" else True,
        })
    return out


@app.post("/api/tools/{tool_id}/run")
def run_tool(tool_id: str, body: RunToolRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tool = TOOLS_BY_ID.get(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Outil inconnu")

    clean_params = validate_params(tool, body.params)
    log = AuditLog(user_id=user.id, tool_id=tool_id, mode=tool["mode"], success=True)

    try:
        if tool["mode"] == "cli":
            enforce_rate_limit(user.id, "cli")
            result = run_cli_tool(tool, clean_params)

        elif tool["mode"] == "api":
            enforce_rate_limit(user.id, "api")
            api_key = None
            if tool.get("requires_key"):
                row = db.query(ApiKey).filter(ApiKey.user_id == user.id, ApiKey.service == tool["service"]).first()
                if row:
                    api_key = decrypt_secret(row.encrypted_value)
            result = run_api_tool(tool, clean_params, api_key)

        elif tool["mode"] == "link":
            result = {"url": tool["build_url"](clean_params)}

        else:
            raise HTTPException(status_code=500, detail="Mode d'outil non supporté")

    except HTTPException:
        log.success = False
        db.add(log)
        db.commit()
        raise

    db.add(log)
    db.commit()
    return result


# ---------- Sert le frontend statique ----------
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
