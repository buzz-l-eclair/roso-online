"""
Rate-limiting minimal, en mémoire process.

Suffisant pour un MVP mono-instance Render. Limites :
- ne survit pas à un redeploy/restart (acceptable, ce n'est pas une donnée
  à conserver) ;
- ne fonctionne pas correctement si tu scales à plusieurs instances Render
  (chaque instance a son propre compteur). Si tu passes multi-instances un
  jour, remplace ceci par un compteur Redis partagé (ex. Render Key Value).
"""
import time
from collections import defaultdict
from fastapi import HTTPException

# user_id -> mode ("cli" ou "api") -> liste de timestamps des appels récents
_HISTORY: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

# Limites volontairement strictes : ces outils tapent des services tiers
# depuis l'IP partagée du serveur Render -> il faut éviter le flag/ban.
LIMITS = {
    "cli": {"max_calls": 10, "window_seconds": 600},   # 10 exécutions / 10 min
    "api": {"max_calls": 30, "window_seconds": 600},   # 30 appels API / 10 min
}


def enforce_rate_limit(user_id: int, mode: str):
    limit = LIMITS.get(mode, LIMITS["cli"])
    now = time.time()
    window_start = now - limit["window_seconds"]

    history = _HISTORY[user_id][mode]
    # purge des entrées trop vieilles
    while history and history[0] < window_start:
        history.pop(0)

    if len(history) >= limit["max_calls"]:
        retry_in = int(history[0] + limit["window_seconds"] - now)
        raise HTTPException(
            status_code=429,
            detail=f"Trop de requêtes ({mode}). Réessaie dans ~{max(retry_in, 1)}s.",
        )

    history.append(now)
