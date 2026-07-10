import os
import base64
import hashlib
import datetime
from passlib.context import CryptContext
from jose import jwt, JWTError
from cryptography.fernet import Fernet

# ---------- Mots de passe ----------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


# ---------- JWT (session utilisateur, cookie httpOnly) ----------
JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET manquant dans l'environnement. "
        "Défini automatiquement par render.yaml en production ; "
        "en local, exporte une valeur aléatoire avant de lancer le serveur."
    )
JWT_ALGO = "HS256"
JWT_EXPIRE_HOURS = 12


def create_access_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except JWTError:
        return None


# ---------- Chiffrement des clés API tierces (Fernet, clé serveur) ----------
SERVER_SECRET_KEY = os.environ.get("SERVER_SECRET_KEY")
if not SERVER_SECRET_KEY:
    raise RuntimeError(
        "SERVER_SECRET_KEY manquant. Génère-le une fois avec "
        "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"` "
        "et mets-le en variable d'environnement (render.yaml le génère automatiquement en prod)."
    )
# Render (comme d'autres secrets managers) génère une chaîne aléatoire
# quelconque, pas forcément un token Fernet valide (32 octets base64 urlsafe).
# On dérive donc systématiquement une clé Fernet valide à partir du secret
# fourni, quelle que soit sa forme d'origine.
_derived_key = base64.urlsafe_b64encode(hashlib.sha256(SERVER_SECRET_KEY.encode()).digest())
_fernet = Fernet(_derived_key)


def encrypt_secret(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    return _fernet.decrypt(ciphertext.encode()).decode()
