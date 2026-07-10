# ROSO Online

Version hébergée de ROSO : comptes utilisateurs individuels, clés API tierces
chiffrées par utilisateur, exécution des outils CLI dans l'image Docker du
serveur, et cartes "lien direct" vers les ressources publiques qui ne peuvent
pas être exécutées côté serveur.

## Ce qui a changé par rapport à la version locale

| | Version locale | ROSO Online |
|---|---|---|
| Auth | aucune | comptes email/mdp, session JWT en cookie httpOnly |
| Clés API tierces | — | stockées chiffrées (Fernet), une par utilisateur, jamais partagées |
| Outils CLI | binaires installés sur ton poste | binaires installés dans l'image Docker du serveur |
| Base de données | — | Postgres (Render), SQLite en fallback dev |
| Rate-limiting | — | oui, par utilisateur, séparé cli / api |
| Journalisation | — | table `audit_logs` : qui a lancé quoi, quand |

Les 16 outils de cette première vague sont répartis en 3 modes déclarés dans
`backend/registry.py` :

- **cli** (Sherlock, Maigret, Holehe, theHarvester, Subfinder, Amass) — exécutés
  côté serveur, dans l'image Docker.
- **api** (Shodan, VirusTotal, HIBP, crt.sh, Hunter.io, EmailRep, IPinfo) —
  appel HTTP avec la clé personnelle de l'utilisateur connecté (sauf crt.sh,
  API publique sans clé).
- **link** (DNSDumpster, OpenCorporates, Etherscan) — carte avec deep-link
  préformaté, ouverture dans un nouvel onglet, aucune exécution serveur.

## Déploiement sur Render

1. Pousse ce dossier sur un dépôt GitHub.
2. Sur [render.com](https://render.com) : **New > Blueprint**, connecte le
   dépôt. Render lit `render.yaml` et crée automatiquement :
   - le service web (build via `Dockerfile`)
   - la base Postgres `roso-db`
   - les variables `JWT_SECRET` et `SERVER_SECRET_KEY` (générées aléatoirement)
3. Premier déploiement : compte 5-10 min, le build Docker installe Go,
   Subfinder, Amass, et clone theHarvester.
4. Une fois en ligne, crée ton premier compte via `/login.html` (onglet
   "Créer un compte") — pas de compte admin préconfiguré, le premier inscrit
   n'a pas de droits particuliers dans cette version (à ajouter si tu veux un
   rôle admin distinct plus tard).
5. Va dans **🔑 Mes clés API** pour brancher tes clés Shodan / VirusTotal /
   HIBP / Hunter.io / EmailRep / IPinfo personnelles. crt.sh ne demande rien.

### Variables d'environnement (auto-générées par render.yaml)

- `DATABASE_URL` — injectée depuis la base Postgres Render
- `JWT_SECRET` — signature des sessions
- `SERVER_SECRET_KEY` — chiffrement des clés API stockées
- `CORS_ORIGINS` — à restreindre à ton domaine `*.onrender.com` une fois connu

## Lancer en local (sans Docker, pour développer)

```bash
cp .env.example .env
# édite .env : mets de vraies valeurs pour JWT_SECRET et SERVER_SECRET_KEY
export $(grep -v '^#' .env | xargs)

cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Ouvre `http://127.0.0.1:8000`. Les outils `cli` ne fonctionneront que si les
binaires (sherlock, maigret, holehe, theHarvester, subfinder, amass) sont
installés sur ta machine — sinon la carte affichera "non détecté" avec la
commande d'installation, exactement comme dans la version locale.

## Lancer en local avec Docker (pour tester l'image de prod)

```bash
docker build -t roso-online .
docker run -p 8000:8000 \
  -e JWT_SECRET=dev_secret_local \
  -e SERVER_SECRET_KEY=dev_secret_local2 \
  -e DATABASE_URL=sqlite:////app/backend/roso_dev.db \
  roso-online
```

## Sécurité — ce qui est déjà en place et ce qu'il reste à durcir

**En place** :
- `subprocess` toujours en `shell=False`, arguments en liste jamais en chaîne
- validation stricte par regex de chaque paramètre avant construction de la
  commande ou de l'URL (`backend/runner.py::validate_params`)
- clés API chiffrées (Fernet), jamais renvoyées en clair par l'API
- rate-limiting par utilisateur (10 cli / 10 min, 30 api / 10 min)
- audit log de chaque exécution

**À durcir avant un usage à plusieurs personnes non triées** :
- `CORS_ORIGINS` doit être restreint à ton domaine réel, pas `*`
- le rate-limiter est en mémoire process : si tu passes à plusieurs instances
  Render, remplace-le par un compteur partagé (Redis / Render Key Value)
- pas de vérification d'email à l'inscription : n'importe qui avec une adresse
  email peut créer un compte — ajoute une confirmation par email si tu ouvres
  l'accès au-delà de toi-même
- pas de rôle admin séparé pour l'instant (tous les comptes ont les mêmes
  droits)

## Prochaine vague d'outils

Le reste de ta liste (~120 entrées) est catégorisé mais pas encore câblé.
Ajouter un outil = une entrée dans `backend/registry.py`, sur le modèle des
16 existantes (mode `cli` / `api` / `link`) ; rien d'autre à modifier, le
frontend génère formulaire et panneau automatiquement.

## Rappel légal et éthique

Ces outils permettent de construire un profil détaillé sur une personne
réelle. Utilise cette plateforme pour des recherches que tu es légalement
autorisé·e à mener, jamais pour harceler ou surveiller quelqu'un sans son
consentement.
