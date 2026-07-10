import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")  # "user" | "admin"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")


class ApiKey(Base):
    """
    Une clé API tierce (Shodan, VirusTotal, HIBP...) appartenant à UN utilisateur.
    La valeur est stockée chiffrée (Fernet) — jamais en clair en base.
    Il n'y a aucune clé "globale" partagée entre utilisateurs.
    """
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    service = Column(String, nullable=False)  # ex: "shodan", "virustotal", "hibp"
    encrypted_value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="api_keys")


class AuditLog(Base):
    """
    Trace qui a lancé quoi, quand — nécessaire dès qu'on ouvre ça en ligne
    (abus, débogage, et éventuelle demande légale sur l'usage de la plateforme).
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tool_id = Column(String, nullable=False)
    mode = Column(String, nullable=False)
    params_summary = Column(String, nullable=True)  # jamais la valeur brute d'une clé API
    success = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")
