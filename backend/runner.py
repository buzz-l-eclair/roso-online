import re
import time
import shutil
import subprocess
import httpx
from fastapi import HTTPException

MAX_OUTPUT_CHARS = 20_000


def validate_params(tool: dict, params: dict) -> dict:
    """Valide chaque paramètre reçu contre le pattern regex déclaré dans le
    registry. Rejette tout ce qui ne matche pas, AVANT de construire la
    commande ou l'URL. C'est la validation stricte mentionnée dans le plan
    d'architecture — indispensable dès que l'endpoint est exposé en ligne."""
    clean = {}
    for p in tool.get("params", []):
        value = (params.get(p["key"]) or "").strip()
        if not value:
            if p["required"]:
                raise HTTPException(status_code=422, detail=f"Paramètre requis manquant : {p['label']}")
            clean[p["key"]] = ""
            continue
        if len(value) > 256:
            raise HTTPException(status_code=422, detail=f"Valeur trop longue pour : {p['label']}")
        if not re.fullmatch(p["pattern"], value):
            raise HTTPException(status_code=422, detail=f"Format invalide pour : {p['label']}")
        clean[p["key"]] = value
    return clean


def is_available(tool: dict) -> bool:
    if tool["mode"] != "cli":
        return True
    check_cmd = tool.get("check_cmd")
    if not check_cmd:
        return shutil.which(tool.get("build_cmd", lambda p: [""])({}).__getitem__(0) if False else "") is not None
    binary = check_cmd[0]
    if shutil.which(binary) is None:
        return False
    try:
        subprocess.run(check_cmd, capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def run_cli_tool(tool: dict, params: dict) -> dict:
    argv = tool["build_cmd"](params)  # toujours une LISTE d'arguments, jamais une string
    timeout = tool.get("timeout", 60)

    start = time.time()
    try:
        proc = subprocess.run(
            argv,
            shell=False,           # <- point de sécurité central : pas d'interprétation shell
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout = (proc.stdout or "")[:MAX_OUTPUT_CHARS]
        stderr = (proc.stderr or "")[:MAX_OUTPUT_CHARS]
        return {
            "stdout": stdout,
            "stderr": stderr,
            "returncode": proc.returncode,
            "duration": round(time.time() - start, 2),
        }
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail=f"Binaire introuvable dans l'image serveur : {argv[0]}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail=f"Délai dépassé ({timeout}s) — cible probablement trop lente à scanner.")


def run_api_tool(tool: dict, params: dict, api_key: str | None) -> dict:
    if tool.get("requires_key") and not api_key:
        raise HTTPException(
            status_code=400,
            detail=f"Clé API {tool['service']} manquante. Ajoute-la dans « Mes clés API ».",
        )

    req = tool["build_request"](params, api_key)
    start = time.time()
    try:
        with httpx.Client(timeout=20) as client:
            resp = client.request(
                req["method"],
                req["url"],
                params=req.get("params"),
                headers=req.get("headers"),
            )
        body_text = resp.text[:MAX_OUTPUT_CHARS]
        return {
            "status_code": resp.status_code,
            "body": body_text,
            "duration": round(time.time() - start, 2),
        }
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Le service tiers n'a pas répondu à temps.")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Erreur en contactant le service tiers : {e}")
