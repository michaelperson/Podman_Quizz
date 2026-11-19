"""Configuration de l'API, lue uniquement depuis les variables d'environnement.

Aucune valeur sensible n'est écrite en dur : le mot de passe de la base vient
de DB_PASSWORD, ou mieux, d'un fichier désigné par DB_PASSWORD_FILE
(c'est ainsi que Podman et compose montent les secrets : /run/secrets/...).
"""

import os


def _lire_mot_de_passe() -> str:
    """DB_PASSWORD_FILE est prioritaire sur DB_PASSWORD."""
    chemin = os.getenv("DB_PASSWORD_FILE")
    if chemin:
        with open(chemin, encoding="utf-8") as fichier:
            # strip() : un fichier de secret se termine souvent par un saut de ligne
            return fichier.read().strip()
    return os.getenv("DB_PASSWORD", "")


# PostgreSQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "quiz")
DB_USER = os.getenv("DB_USER", "quiz")
DB_PASSWORD = _lire_mot_de_passe()

# Tentatives de connexion au démarrage : la base met parfois quelques
# secondes à être prête, surtout au tout premier lancement.
DB_CONNECT_RETRIES = int(os.getenv("DB_CONNECT_RETRIES", "15"))
DB_CONNECT_DELAY = float(os.getenv("DB_CONNECT_DELAY", "2"))

# Redis (classement). REDIS_HOST vide = pas de Redis : le classement est
# alors calculé directement dans PostgreSQL (pratique pour les premiers labs).
REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Pour les labs de healthcheck : force /health à répondre 503.
# Valeurs acceptées : 1, true, yes, oui. On peut aussi créer le fichier
# UNHEALTHY_FILE dans le conteneur pour basculer sans redémarrer.
FORCE_UNHEALTHY = os.getenv("FORCE_UNHEALTHY", "").lower() in ("1", "true", "yes", "oui")
UNHEALTHY_FILE = os.getenv("UNHEALTHY_FILE", "/tmp/unhealthy")
