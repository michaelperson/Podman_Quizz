# Quiz conteneurs — application fil rouge « Podman pour développeurs »

Un petit quiz de culture conteneurs : dix questions sur Podman, un pseudo, un score
et un classement. L'application est **fournie toute faite** : dans cette formation,
vous ne codez pas l'application, vous la **conteneurisez**, la composez, la
diagnostiquez et la durcissez.

La branche `main` est votre point de départ : le code de l'application, sans
Containerfile ni `compose.yaml`. C'est à vous de les écrire, lab après lab.

> **Vous êtes sur la branche `solutions`.** Elle ajoute les Containerfiles, le
> `compose.yaml` complet, la correction du diagnostic, les manifestes kube, les
> unités Quadlet et le workflow CI. Explications pour le formateur :
> [SOLUTIONS.md](SOLUTIONS.md). Démarrage rapide :
> `openssl rand -hex 16 > secrets/db_password.txt` puis
> `podman compose up -d --build`, et <http://localhost:8080>.

## Architecture

```
                 navigateur
                     │  http://localhost:8080
                     ▼
        ┌─────────────────────────┐
        │ front  (nginx, :8080)    │  fichiers statiques HTML/CSS/JS
        │  /api/*  ──► proxy       │
        └────────────┬────────────┘
                     │ http://${API_HOST}:${API_PORT}   (ex. http://api:8000)
                     ▼
        ┌─────────────────────────┐
        │ api  (FastAPI, :8000)    │  /api/questions, /api/scores,
        │                          │  /api/leaderboard, /health, /ready
        └──────┬───────────┬──────┘
               │           │
               ▼           ▼
     ┌──────────────┐  ┌──────────────┐
     │ db           │  │ redis        │
     │ PostgreSQL   │  │ classement   │
     │ :5432        │  │ (sorted set) │
     │ questions,   │  │ :6379        │
     │ scores       │  │ (optionnel)  │
     └──────────────┘  └──────────────┘
```

- **front** : HTML/CSS/JS sans framework ni étape de build, servis par nginx.
  nginx relaie tout ce qui commence par `/api` vers l'API.
- **api** : Python 3.14, FastAPI et uvicorn. Au démarrage, elle attend la base
  (plusieurs tentatives), crée les tables et insère les questions si la base est vide.
- **db** : PostgreSQL stocke les questions et tous les scores.
- **redis** : le classement (meilleur score par joueur). Facultatif : sans Redis,
  le classement est calculé dans PostgreSQL. Si Redis repart à vide, l'API
  reconstruit le classement depuis PostgreSQL au démarrage.

## Contenu du dépôt

```
api/                   code de l'API (FastAPI)
  main.py              routes et accès aux données
  config.py            lecture des variables d'environnement
  healthcheck.py       sonde pour les healthchecks (sans curl)
  questions.json       les questions insérées au premier démarrage
  requirements.txt     dépendances épinglées
front/
  public/              index.html, style.css, app.js
  nginx/default.conf.template   configuration nginx (template envsubst)
labs/                  un énoncé par lab
  05-diagnostic/       une stack volontairement cassée, prête à lancer
secrets/               vos secrets locaux (non versionnés)
```

## Variables d'environnement

### API

| Variable | Défaut | Rôle |
|---|---|---|
| `DB_HOST` | `localhost` | hôte PostgreSQL (nom du conteneur ou du service) |
| `DB_PORT` | `5432` | port PostgreSQL |
| `DB_NAME` | `quiz` | nom de la base |
| `DB_USER` | `quiz` | utilisateur |
| `DB_PASSWORD` | *(vide)* | mot de passe, en clair |
| `DB_PASSWORD_FILE` | *(vide)* | chemin d'un fichier contenant le mot de passe (secret monté, par exemple `/run/secrets/db_password`). **Prioritaire** sur `DB_PASSWORD` |
| `DB_CONNECT_RETRIES` | `15` | nombre de tentatives de connexion au démarrage |
| `DB_CONNECT_DELAY` | `2` | secondes entre deux tentatives |
| `REDIS_HOST` | *(vide)* | hôte Redis. Vide : pas de Redis, classement calculé dans PostgreSQL |
| `REDIS_PORT` | `6379` | port Redis |
| `FORCE_UNHEALTHY` | *(vide)* | `1` : `/health` répond toujours 503 (lab healthchecks) |
| `UNHEALTHY_FILE` | `/tmp/unhealthy` | si ce fichier existe, `/health` répond 503 (bascule sans redémarrer) |

L'API écoute sur `0.0.0.0:8000` (`uvicorn main:app --host 0.0.0.0 --port 8000`).

### Front (nginx)

| Variable | Exemple | Rôle |
|---|---|---|
| `API_HOST` | `api` | nom DNS de l'API vu depuis le conteneur nginx |
| `API_PORT` | `8000` | port de l'API |
| `NGINX_ENTRYPOINT_LOCAL_RESOLVERS` | `1` | obligatoire : fournit à nginx l'adresse du DNS du conteneur |

nginx écoute sur **8080** dans le conteneur (jamais 80 : en rootless, et pour un
nginx non-root, les ports inférieurs à 1024 sont privilégiés).

## Routes de l'API

| Méthode et chemin | Rôle |
|---|---|
| `GET /api/questions` | les questions, sans les réponses |
| `POST /api/scores` | `{"pseudo": "...", "reponses": {"1": 0, "2": 3}}` ; renvoie le score et la correction |
| `GET /api/leaderboard` | les 10 meilleurs joueurs et la source (`redis` ou `postgres`) |
| `GET /health` | 200 si PostgreSQL (et Redis, s'il est configuré) répondent, 503 sinon, avec le détail |
| `GET /ready` | 200 quand le démarrage (connexion, tables, questions) est terminé |
| `GET /docs` | documentation interactive générée par FastAPI |

## Lancer chaque morceau à la main

Les commandes ci-dessous fonctionnent sous Linux, macOS et Windows (PowerShell ou
WSL). Les noms d'images sont **complets** (`docker.io/...`) : Podman n'a pas de
registre implicite.

```bash
# 1. Un réseau pour que les conteneurs se trouvent par leur nom
podman network create quiz

# 2. PostgreSQL (PostgreSQL 18 : le volume se monte sur /var/lib/postgresql)
podman run -d --name db --network quiz \
  -e POSTGRES_DB=quiz -e POSTGRES_USER=quiz -e POSTGRES_PASSWORD=change-moi \
  -v quiz-pgdata:/var/lib/postgresql \
  docker.io/library/postgres:18.7-trixie

# 3. Redis (facultatif)
podman run -d --name redis --network quiz docker.io/library/redis:8.10.3-alpine3.23

# 4. L'API, sans Containerfile : on monte le code dans une image Python
#    (c'est lent et fragile : le lab 01 consiste justement à faire mieux)
podman run -d --name api --network quiz -p 8000:8000 \
  -e DB_HOST=db -e DB_PASSWORD=change-moi -e REDIS_HOST=redis \
  -v ./api:/app:Z -w /app \
  docker.io/library/python:3.14.10-slim-trixie \
  sh -c "pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000"

# 5. Le front : l'image nginx officielle, avec le site et le template montés
podman run -d --name front --network quiz -p 8080:8080 \
  -e API_HOST=api -e API_PORT=8000 -e NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1 \
  -v ./front/public:/usr/share/nginx/html:ro,Z \
  -v ./front/nginx:/etc/nginx/templates:ro,Z \
  docker.io/library/nginx:1.30.7-alpine3.24
```

Puis : <http://localhost:8080> (le quiz), <http://localhost:8000/health>,
<http://localhost:8000/docs>.

Sous PowerShell, remplacez les `\` de fin de ligne par des accents graves `` ` ``
(ou écrivez chaque commande sur une seule ligne).

Pour tout nettoyer :

```bash
podman rm -f front api redis db
podman network rm quiz
podman volume rm quiz-pgdata
```

Sans conteneur, l'API se lance aussi en local avec Python 3.14 :
`python -m venv .venv`, activer l'environnement, `pip install -r requirements.txt`,
puis `uvicorn main:app --port 8000` depuis `api/`, avec `DB_HOST=localhost` et une
base publiée sur le port 5432 (`-p 5432:5432`).

## Les labs

| Lab | Séquence | Énoncé |
|---|---|---|
| 01 | 1.8 Conteneuriser l'API | [labs/01-containerfile.md](labs/01-containerfile.md) |
| 02 | 1.11 Publier l'image dans un registre | [labs/02-registre.md](labs/02-registre.md) |
| 03 | 2.3 Persister PostgreSQL | [labs/03-volumes.md](labs/03-volumes.md) |
| 04 | 2.5 et 2.7 Réseau, pod, kube | [labs/04-reseau-pod-kube.md](labs/04-reseau-pod-kube.md) |
| 05 | 2.8 Diagnostic n° 1 | [labs/05-diagnostic/README.md](labs/05-diagnostic/README.md) |
| 06 | 2.10 Composer l'application | [labs/06-compose.md](labs/06-compose.md) |
| 07 | 3.3 Healthchecks | [labs/07-healthchecks.md](labs/07-healthchecks.md) |
| 08 | 3.5 Scanner et durcir | [labs/08-securite-scan.md](labs/08-securite-scan.md) |
| Bonus | 3.7 Quadlet | [labs/bonus-quadlet.md](labs/bonus-quadlet.md) |
| Bonus | 3.7 GitHub Actions | [labs/bonus-ci.md](labs/bonus-ci.md) |

Chaque lab a trois paliers : **socle** (l'essentiel, pour tout le monde),
**standard** (l'objectif visé) et **bonus** (pour aller plus loin).

## Versions retenues

Vérifiées le 2026-11-20 sur les sources officielles. Toutes les images sont
épinglées sur un tag précis : jamais `latest`.

| Composant | Tag | Source | Pourquoi ce choix |
|---|---|---|---|
| Python (image d'exécution) | `python:3.14.10-slim-trixie`, `python:3.14.10-alpine3.24` | [Docker Hub library/python](https://hub.docker.com/_/python), [endoflife.date/python](https://endoflife.date/python) | 3.14 est maintenue jusqu'en octobre 2030. 3.15.2 existe aussi, mais l'application a été testée en 3.14 |
| Python (point de départ « naïf ») | `python:3.14.10` | idem | image complète Debian, environ 1 Go : sert de comparaison (lab 01) et de cible de scan (lab 08) |
| PostgreSQL | `postgres:18.7-trixie` | [Docker Hub library/postgres](https://hub.docker.com/_/postgres), [endoflife.date/postgresql](https://endoflife.date/postgresql) | 18 est la dernière majeure, maintenue jusqu'en novembre 2030 |
| Redis | `redis:8.10.3-alpine3.23` | [Docker Hub library/redis](https://hub.docker.com/_/redis), [endoflife.date/redis](https://endoflife.date/redis) | dernière version stable (8.10) |
| nginx | `nginx:1.30.7-alpine3.24` | [Docker Hub library/nginx](https://hub.docker.com/_/nginx), [endoflife.date/nginx](https://endoflife.date/nginx) | branche stable 1.30. `nginxinc/nginx-unprivileged` n'existe qu'en 1.30.6, qui a des CVE critiques corrigées en 1.30.7 |
| Registre | `registry:3.1.2` | [Docker Hub library/registry](https://hub.docker.com/_/registry) | dernière version (registre CNCF Distribution) |
| Trivy | `aquasec/trivy:0.76.2` (digest `sha256:8f6bb947dbc528902e11f2f5be52f7b519f6a39d5d148f41166f2040499768fb`) | [Docker Hub aquasec/trivy](https://hub.docker.com/r/aquasec/trivy), [releases GitHub](https://github.com/aquasecurity/trivy/releases), [avis GHSA-69fq-xp46-6x23](https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23) | publiée le 2026-11-05. **N'utilisez jamais** 0.69.4, 0.69.5 ni 0.69.6 (compromission de mars 2026) |

Dépendances Python (`api/requirements.txt`, source : [PyPI](https://pypi.org)) :
fastapi 0.162.0, uvicorn 0.54.0, psycopg[binary] 3.3.8, redis 8.1.0, pydantic 2.14.3,
toutes publiées au moins deux semaines avant le 2026-11-20 (délai de « refroidissement »
contre les versions piégées fraîchement publiées).

## Remarques pour Windows

- Le dépôt impose des fins de ligne LF (`.gitattributes`) : les fichiers copiés
  dans les conteneurs doivent rester des fichiers Linux.
- Avec **Git Bash**, les chemins commençant par `/` sont réécrits en chemins Windows :
  `podman exec api touch /tmp/unhealthy` devient `.../AppData/Local/Temp/unhealthy`.
  Préfixez la commande avec `MSYS_NO_PATHCONV=1`, ou utilisez PowerShell ou WSL.
- Dans **Windows PowerShell 5.1**, `curl` est un alias d'`Invoke-WebRequest` :
  tapez `curl.exe`. PowerShell 7 n'a plus cet alias.
- **Docker Desktop** lancé à côté de Podman peut déjà occuper les ports des labs
  (8000, 8080, 5432...) : `address already in use`. Arrêtez les conteneurs Docker
  concernés, ou changez le port publié.
- Installez Podman **pour Windows** (`winget install Podman.CLI`) et pilotez-le
  depuis PowerShell. N'installez pas Podman avec `apt` dans une distribution WSL :
  la version y est beaucoup trop ancienne.

## Licence

Voir [LICENSE](LICENSE).
