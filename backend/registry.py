"""
Registry des outils ROSO — première vague (10 outils) couvrant les 3 modes
d'exécution en ligne :

- cli  : subprocess exécuté côté serveur (binaire installé dans l'image Docker)
- api  : appel HTTP à une API tierce, avec la clé PERSONNELLE de l'utilisateur
         connecté (stockée chiffrée en base, jamais de clé partagée globale)
- link : carte avec deep-link préformaté, aucune exécution serveur

Chaque paramètre déclare un `pattern` (regex) utilisé pour la validation
stricte côté serveur avant construction de la commande ou de l'URL —
c'est la première ligne de défense contre l'injection / les abus, en plus
du rate-limiting et de shell=False.
"""

# Regex de validation réutilisables
RE_EMAIL = r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"
RE_USERNAME = r"^[A-Za-z0-9_\-.]{1,64}$"
RE_DOMAIN = r"^(?!-)[A-Za-z0-9\-\.]{1,253}(?<!-)$"
RE_IP = r"^(\d{1,3}\.){3}\d{1,3}$"
RE_HASH_OR_TEXT = r"^[A-Za-z0-9_\-.: ]{1,256}$"


def _p(key, label, pattern, placeholder="", required=True, help=""):
    return {
        "key": key,
        "label": label,
        "pattern": pattern,
        "placeholder": placeholder,
        "required": required,
        "help": help,
    }


TOOLS = [
    # ------------------------------------------------------------------ CLI
    {
        "id": "sherlock",
        "name": "Sherlock",
        "category": "Identité / pseudos",
        "mode": "cli",
        "repo": "sherlock-project/sherlock",
        "install": "pip install sherlock-project",
        "check_cmd": ["sherlock", "--version"],
        "params": [_p("username", "Pseudo", RE_USERNAME, "johndoe")],
        "build_cmd": lambda p: ["sherlock", p["username"], "--timeout", "8", "--print-found"],
        "timeout": 90,
        "notes": "Recherche un pseudo sur ~400 plateformes sociales.",
    },
    {
        "id": "maigret",
        "name": "Maigret",
        "category": "Identité / pseudos",
        "mode": "cli",
        "repo": "soxoj/maigret",
        "install": "pip install maigret",
        "check_cmd": ["maigret", "--version"],
        "params": [_p("username", "Pseudo", RE_USERNAME, "johndoe")],
        "build_cmd": lambda p: ["maigret", p["username"], "--timeout", "10", "-J", "simple"],
        "timeout": 120,
        "notes": "Recherche de pseudo plus poussée que Sherlock (analyse de profils).",
    },
    {
        "id": "holehe",
        "name": "Holehe",
        "category": "Identité / email",
        "mode": "cli",
        "repo": "megadose/holehe",
        "install": "pip install holehe",
        "check_cmd": ["holehe", "--help"],
        "params": [_p("email", "Email", RE_EMAIL, "cible@example.com")],
        "build_cmd": lambda p: ["holehe", p["email"], "--only-used"],
        "timeout": 60,
        "notes": "Vérifie sur quels sites un email est utilisé pour un compte.",
    },
    {
        "id": "theharvester",
        "name": "theHarvester",
        "category": "Infrastructure / recon",
        "mode": "cli",
        "repo": "laramies/theHarvester",
        "install": "voir Dockerfile (cloné + venv dédié)",
        "check_cmd": ["theHarvester", "-h"],
        "params": [
            _p("domain", "Domaine", RE_DOMAIN, "example.com"),
            _p("source", "Source", r"^[a-z]{2,20}$", "bing", required=False, help="ex: bing, crtsh, duckduckgo"),
        ],
        "build_cmd": lambda p: ["theHarvester", "-d", p["domain"], "-b", p.get("source") or "bing"],
        "timeout": 90,
        "notes": "Collecte emails / sous-domaines / hôtes liés à un domaine.",
    },
    {
        "id": "subfinder",
        "name": "Subfinder",
        "category": "Infrastructure / recon",
        "mode": "cli",
        "repo": "projectdiscovery/subfinder",
        "install": "go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
        "check_cmd": ["subfinder", "-version"],
        "params": [_p("domain", "Domaine", RE_DOMAIN, "example.com")],
        "build_cmd": lambda p: ["subfinder", "-d", p["domain"], "-silent"],
        "timeout": 60,
        "notes": "Énumération passive de sous-domaines (binaire Go).",
    },
    {
        "id": "amass",
        "name": "Amass",
        "category": "Infrastructure / recon",
        "mode": "cli",
        "repo": "owasp-amass/amass",
        "install": "go install github.com/owasp-amass/amass/v4/...@master",
        "check_cmd": ["amass", "-version"],
        "params": [_p("domain", "Domaine", RE_DOMAIN, "example.com")],
        "build_cmd": lambda p: ["amass", "enum", "-passive", "-d", p["domain"]],
        "timeout": 120,
        "notes": "Énumération DNS approfondie (passive par défaut, pas de bruteforce actif).",
    },

    # ------------------------------------------------------------------ API
    {
        "id": "shodan",
        "name": "Shodan",
        "category": "Infrastructure / API",
        "mode": "api",
        "service": "shodan",
        "requires_key": True,
        "params": [_p("ip", "Adresse IP", RE_IP, "8.8.8.8")],
        "build_request": lambda p, key: {
            "method": "GET",
            "url": f"https://api.shodan.io/shodan/host/{p['ip']}",
            "params": {"key": key},
        },
        "fallback_link": lambda p: f"https://www.shodan.io/host/{p['ip']}",
        "notes": "Bannières de services exposés pour une IP. Nécessite ta clé Shodan perso.",
    },
    {
        "id": "virustotal",
        "name": "VirusTotal",
        "category": "Threat Intel / API",
        "mode": "api",
        "service": "virustotal",
        "requires_key": True,
        "params": [_p("target", "Domaine / IP / hash", RE_HASH_OR_TEXT, "example.com ou hash SHA256")],
        "build_request": lambda p, key: _virustotal_request(p["target"], key),
        "fallback_link": lambda p: f"https://www.virustotal.com/gui/search/{p['target']}",
        "notes": "Réputation d'un domaine, IP ou hash de fichier. Nécessite ta clé VT perso.",
    },
    {
        "id": "hibp",
        "name": "Have I Been Pwned",
        "category": "Fuites de données / API",
        "mode": "api",
        "service": "hibp",
        "requires_key": True,
        "params": [_p("email", "Email", RE_EMAIL, "cible@example.com")],
        "build_request": lambda p, key: {
            "method": "GET",
            "url": f"https://haveibeenpwned.com/api/v3/breachedaccount/{p['email']}",
            "headers": {"hibp-api-key": key, "user-agent": "ROSO-OSINT-Platform"},
            "params": {"truncateResponse": "false"},
        },
        "fallback_link": lambda p: "https://haveibeenpwned.com/",
        "notes": "Fuites de données connues associées à un email. Nécessite ta clé HIBP perso (payante).",
    },
    {
        "id": "crtsh",
        "name": "crt.sh",
        "category": "Infrastructure / API",
        "mode": "api",
        "service": "crtsh",
        "requires_key": False,
        "params": [_p("domain", "Domaine", RE_DOMAIN, "example.com")],
        "build_request": lambda p, key: {
            "method": "GET",
            "url": "https://crt.sh/",
            "params": {"q": p["domain"], "output": "json"},
        },
        "fallback_link": lambda p: f"https://crt.sh/?q={p['domain']}",
        "notes": "Certificats TLS émis pour un domaine (souvent révèle des sous-domaines). API publique, pas de clé requise.",
    },

    {
        "id": "hunterio",
        "name": "Hunter.io",
        "category": "Identité / email / API",
        "mode": "api",
        "service": "hunterio",
        "requires_key": True,
        "params": [_p("domain", "Domaine", RE_DOMAIN, "example.com")],
        "build_request": lambda p, key: {
            "method": "GET",
            "url": "https://api.hunter.io/v2/domain-search",
            "params": {"domain": p["domain"], "api_key": key},
        },
        "fallback_link": lambda p: f"https://hunter.io/search/{p['domain']}",
        "notes": "Emails professionnels associés à un domaine. Nécessite ta clé Hunter.io perso.",
    },
    {
        "id": "emailrep",
        "name": "EmailRep",
        "category": "Identité / email / API",
        "mode": "api",
        "service": "emailrep",
        "requires_key": True,
        "params": [_p("email", "Email", RE_EMAIL, "cible@example.com")],
        "build_request": lambda p, key: {
            "method": "GET",
            "url": f"https://emailrep.io/{p['email']}",
            "headers": {"Key": key},
        },
        "fallback_link": lambda p: "https://emailrep.io/",
        "notes": "Réputation d'un email (âge, présence sur des sites, signaux de risque). Nécessite ta clé EmailRep perso.",
    },
    {
        "id": "ipinfo",
        "name": "IPinfo",
        "category": "Infrastructure / API",
        "mode": "api",
        "service": "ipinfo",
        "requires_key": True,
        "params": [_p("ip", "Adresse IP", RE_IP, "8.8.8.8")],
        "build_request": lambda p, key: {
            "method": "GET",
            "url": f"https://ipinfo.io/{p['ip']}/json",
            "params": {"token": key},
        },
        "fallback_link": lambda p: f"https://ipinfo.io/{p['ip']}",
        "notes": "Géolocalisation et informations réseau d'une IP. Nécessite ta clé IPinfo perso.",
    },

    # ----------------------------------------------------------------- LINK
    {
        "id": "opencorporates",
        "name": "OpenCorporates",
        "category": "Financier / entreprises / lien direct",
        "mode": "link",
        "params": [_p("name", "Nom d'entreprise", r"^[A-Za-z0-9 &.,'\-]{1,120}$", "Acme Corp")],
        "build_url": lambda p: f"https://opencorporates.com/companies?q={p['name'].replace(' ', '+')}",
        "notes": "Registre mondial d'entreprises (dirigeants, statuts, filiales).",
    },
    {
        "id": "etherscan",
        "name": "Etherscan",
        "category": "Financier / blockchain / lien direct",
        "mode": "link",
        "params": [_p("address", "Adresse Ethereum", r"^0x[a-fA-F0-9]{40}$", "0x...")],
        "build_url": lambda p: f"https://etherscan.io/address/{p['address']}",
        "notes": "Explorateur de transactions Ethereum pour une adresse donnée.",
    },
    {
        "id": "dnsdumpster",
        "name": "DNSDumpster",
        "category": "Infrastructure / lien direct",
        "mode": "link",
        "params": [_p("domain", "Domaine", RE_DOMAIN, "example.com")],
        "build_url": lambda p: f"https://dnsdumpster.com/",
        "notes": "Cartographie DNS d'un domaine. Site tiers protégé anti-bot : ouverture manuelle, requête à saisir toi-même.",
    },
]

TOOLS_BY_ID = {t["id"]: t for t in TOOLS}


def _virustotal_request(target: str, key: str) -> dict:
    # VT distingue endpoint selon que la cible ressemble à un hash, une IP ou un domaine
    import re
    if re.fullmatch(r"[A-Fa-f0-9]{32,64}", target):
        path = f"files/{target}"
    elif re.fullmatch(RE_IP, target):
        path = f"ip_addresses/{target}"
    else:
        path = f"domains/{target}"
    return {
        "method": "GET",
        "url": f"https://www.virustotal.com/api/v3/{path}",
        "headers": {"x-apikey": key},
    }
