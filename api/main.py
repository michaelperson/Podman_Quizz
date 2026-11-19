"""API du quiz « Culture conteneurs ».

Lancement : uvicorn main:app --host 0.0.0.0 --port 8000

Routes :
  GET  /api/questions    questions du quiz (sans les réponses)
  POST /api/scores       envoie les réponses d'un joueur, renvoie son score
  GET  /api/leaderboard  les 10 meilleurs joueurs
  GET  /health           état de l'API et de ses dépendances (base, Redis)
  GET  /ready            l'API a fini de démarrer
"""

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

import psycopg
import redis
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("quiz")

CLE_CLASSEMENT = "quiz:classement"  # sorted set Redis : pseudo -> meilleur score
etat = {"pret": False}  # passe à True quand le démarrage est terminé


# --- Accès aux données -------------------------------------------------------

def connexion_db() -> psycopg.Connection:
    """Ouvre une connexion PostgreSQL (une par requête : l'appli est petite)."""
    return psycopg.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        connect_timeout=3,
    )


def client_redis() -> redis.Redis | None:
    """Client Redis, ou None si REDIS_HOST n'est pas défini."""
    if not config.REDIS_HOST:
        return None
    return redis.Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        socket_timeout=2,
        decode_responses=True,
    )


def attendre_la_base() -> None:
    """Réessaie la connexion tant que la base n'est pas joignable."""
    for tentative in range(1, config.DB_CONNECT_RETRIES + 1):
        try:
            with connexion_db():
                log.info("PostgreSQL joignable sur %s:%s", config.DB_HOST, config.DB_PORT)
                return
        except psycopg.OperationalError as erreur:
            log.warning(
                "PostgreSQL injoignable sur %s:%s (tentative %d/%d) : %s",
                config.DB_HOST, config.DB_PORT, tentative, config.DB_CONNECT_RETRIES,
                str(erreur).strip(),
            )
            time.sleep(config.DB_CONNECT_DELAY)
    raise SystemExit(f"Abandon : impossible de joindre PostgreSQL sur {config.DB_HOST}:{config.DB_PORT}")


def initialiser_la_base() -> None:
    """Crée les tables et insère les questions si la base est vide."""
    with connexion_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id            SERIAL PRIMARY KEY,
                texte         TEXT NOT NULL,
                choix         JSONB NOT NULL,
                bonne_reponse INTEGER NOT NULL,
                explication   TEXT NOT NULL
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id      SERIAL PRIMARY KEY,
                pseudo  VARCHAR(30) NOT NULL,
                score   INTEGER NOT NULL,
                total   INTEGER NOT NULL,
                cree_le TIMESTAMPTZ NOT NULL DEFAULT now()
            )""")
        deja_la = conn.execute("SELECT count(*) FROM questions").fetchone()[0]
        if deja_la == 0:
            questions = json.loads(Path(__file__).with_name("questions.json").read_text(encoding="utf-8"))
            for q in questions:
                conn.execute(
                    "INSERT INTO questions (texte, choix, bonne_reponse, explication) VALUES (%s, %s, %s, %s)",
                    (q["texte"], json.dumps(q["choix"]), q["bonne_reponse"], q["explication"]),
                )
            log.info("Base initialisée avec %d questions", len(questions))
        else:
            log.info("Base déjà initialisée (%d questions)", deja_la)


def reconstruire_classement() -> None:
    """Si Redis a perdu le classement (pas de volume), on le recalcule depuis PostgreSQL."""
    r = client_redis()
    if r is None:
        return
    try:
        if r.exists(CLE_CLASSEMENT):
            return
        with connexion_db() as conn:
            lignes = conn.execute("SELECT pseudo, max(score) FROM scores GROUP BY pseudo").fetchall()
        if lignes:
            r.zadd(CLE_CLASSEMENT, {pseudo: score for pseudo, score in lignes})
            log.info("Classement Redis reconstruit (%d joueurs)", len(lignes))
    except redis.RedisError as erreur:
        # Redis absent au démarrage : on continue, /health le signalera.
        log.warning("Redis injoignable sur %s:%s : %s", config.REDIS_HOST, config.REDIS_PORT, erreur)


@asynccontextmanager
async def demarrage(app: FastAPI):
    attendre_la_base()
    initialiser_la_base()
    reconstruire_classement()
    etat["pret"] = True
    log.info("API prête")
    yield


app = FastAPI(title="Quiz conteneurs", lifespan=demarrage)


# --- Routes du quiz ------------------------------------------------------------

class Reponses(BaseModel):
    pseudo: str = Field(min_length=1, max_length=30)
    # identifiant de question (en texte, car c'est du JSON) -> indice du choix
    reponses: dict[str, int]


@app.get("/api/questions")
def lister_questions():
    with connexion_db() as conn:
        lignes = conn.execute("SELECT id, texte, choix FROM questions ORDER BY id").fetchall()
    return [{"id": i, "texte": t, "choix": c} for i, t, c in lignes]


@app.post("/api/scores")
def enregistrer_score(envoi: Reponses):
    pseudo = envoi.pseudo.strip()
    if not pseudo:
        raise HTTPException(status_code=422, detail="Le pseudo est vide")

    with connexion_db() as conn:
        questions = conn.execute(
            "SELECT id, bonne_reponse, explication FROM questions ORDER BY id"
        ).fetchall()
        correction = []
        for qid, bonne, explication in questions:
            donnee = envoi.reponses.get(str(qid))
            correction.append({
                "id": qid,
                "correct": donnee == bonne,
                "bonne_reponse": bonne,
                "explication": explication,
            })
        score = sum(1 for c in correction if c["correct"])
        conn.execute(
            "INSERT INTO scores (pseudo, score, total) VALUES (%s, %s, %s)",
            (pseudo, score, len(questions)),
        )

    r = client_redis()
    if r is not None:
        # GT : on ne garde que le meilleur score de chaque joueur
        r.zadd(CLE_CLASSEMENT, {pseudo: score}, gt=True)

    return {"pseudo": pseudo, "score": score, "total": len(questions), "correction": correction}


@app.get("/api/leaderboard")
def classement():
    r = client_redis()
    if r is not None:
        top = r.zrevrange(CLE_CLASSEMENT, 0, 9, withscores=True)
        source = "redis"
    else:
        with connexion_db() as conn:
            top = conn.execute(
                "SELECT pseudo, max(score) AS s FROM scores GROUP BY pseudo ORDER BY s DESC, pseudo LIMIT 10"
            ).fetchall()
        source = "postgres"
    return {
        "source": source,
        "classement": [{"pseudo": p, "score": int(s)} for p, s in top],
    }


# --- Sondes pour les healthchecks -------------------------------------------

@app.get("/health")
def sante():
    """200 si la base (et Redis, s'il est configuré) répondent, 503 sinon."""
    verifs = {}
    if config.FORCE_UNHEALTHY or os.path.exists(config.UNHEALTHY_FILE):
        verifs["force"] = "échec forcé (FORCE_UNHEALTHY ou fichier " + config.UNHEALTHY_FILE + ")"
    try:
        with connexion_db() as conn:
            conn.execute("SELECT 1")
        verifs["postgres"] = "ok"
    except psycopg.Error as erreur:
        verifs["postgres"] = f"erreur : {str(erreur).strip()}"
    r = client_redis()
    if r is not None:
        try:
            r.ping()
            verifs["redis"] = "ok"
        except redis.RedisError as erreur:
            verifs["redis"] = f"erreur : {erreur}"

    tout_va_bien = all(v == "ok" for v in verifs.values())
    return JSONResponse(
        status_code=200 if tout_va_bien else 503,
        content={"statut": "ok" if tout_va_bien else "ko", "verifications": verifs},
    )


@app.get("/ready")
def pret():
    """200 dès que l'initialisation (connexion, tables, questions) est terminée."""
    if etat["pret"]:
        return {"statut": "prêt"}
    return JSONResponse(status_code=503, content={"statut": "en cours de démarrage"})
