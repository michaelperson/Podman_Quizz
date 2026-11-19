# Solutions — notes pour le formateur

Branche `solutions` du dépôt « Quiz ». Elle contient tout ce que les apprenants
doivent produire pendant les labs. **Ne pas la montrer avant les débriefings.**
La branche `main` est le point de départ des apprenants.

## Ce que contient cette branche (en plus de `main`)

```
api/Containerfile.socle        lab 01, palier socle (image complète, root)
api/Containerfile.standard     lab 01, palier standard (multi-stage, slim)
api/Containerfile              lab 01, palier bonus = image finale (Alpine, non-root, sans pip, HEALTHCHECK)
api/.containerignore
front/Containerfile            lab 06 standard (nginx non-root, 8080)
front/.containerignore
compose.yaml                   labs 06, 07, 08 (secret, .env, depends_on healthy, healthchecks, durcissement)
.env                           variables non secrètes lues par compose.yaml
labs/05-diagnostic/compose.corrige.yaml   les 4 pannes corrigées et commentées
kube/quiz-pod.yaml             lab 04 partie 3 (forme de « podman kube generate »)
kube/quiz-pod-durci.yaml       lab 04 bonus (Secret, Redis, sondes, securityContext)
quadlet/                       bonus Quadlet (.pod, .volume, .container, variante .kube)
.github/workflows/build.yml    bonus CI (build Podman, scan Trivy, push ghcr.io)
```

Démarrage complet de la solution :

```bash
openssl rand -hex 16 > secrets/db_password.txt
podman compose up -d --build
# http://localhost:8080
```

---

## Lab 01 — Containerfile de l'API (1.8)

| Palier | Fichier | Base | Taille mesurée* | Utilisateur |
|---|---|---|---|---|
| socle | `api/Containerfile.socle` | `python:3.14.10` (Debian complète) | ~1,17 Go | root |
| standard | `api/Containerfile.standard` | `python:3.14.10-slim-trixie`, multi-stage | ~177 Mo | root |
| bonus | `api/Containerfile` | `python:3.14.10-alpine3.24`, multi-stage | ~96 Mo | `quiz` (UID 10001) |

\* Mesuré avec Docker 29 (stockage containerd) ; `podman images` donnera des
chiffres un peu différents, l'ordre de grandeur reste le même.

Points à faire sortir au débriefing (1.9) :

- **Cache** : copier `requirements.txt` et faire `pip install` *avant* `COPY . .`.
  Le socle le fait déjà ; c'est l'étape 4 du palier socle.
- **Forme exec** de `CMD` : uvicorn est le PID 1 et reçoit SIGTERM ; en forme
  shell, `sh` est PID 1 et `podman stop` attend 10 s puis tue.
- `0.0.0.0` : sinon l'API n'écoute que sur le loopback du conteneur et le port
  publié ne mène nulle part.
- `EXPOSE` documente, ne publie pas.
- **Multi-stage** : ici le gain vient surtout de l'image `slim`, le multi-stage
  apporte un venv propre et sans cache pip. Avec des dépendances à compiler
  (gcc, en-têtes), le gain du multi-stage serait bien plus visible.
- **Bonus** : la même libc dans les deux étapes (on ne copie pas un venv glibc
  dans une Alpine musl). `psycopg-binary` et `pydantic-core` ont des roues
  musllinux : aucune compilation. `pip` retiré du venv et de l'image de base
  (il embarque des bibliothèques qui remontent au scan). Code appartenant à root,
  `USER 10001:10001` numérique (vérifiable par `runAsNonRoot`).
- Alternative au bonus : image « distroless » ou Chainguard/Wolfi ; vérifier que
  la version de Python correspond à celle du venv.
- Les images de base sont nommées en entier (`docker.io/library/...`) : Podman
  n'a pas de registre implicite (`unqualified-search-registries`).

Avec Podman, `podman build .` trouve tout seul `Containerfile`. (Docker, lui,
exige `-f Containerfile`.)

## Lab 02 — Registre (1.11)

Rien à versionner. Commandes de référence :

```bash
podman run -d --name registre -p 5000:5000 docker.io/library/registry:3.1.2
podman tag quiz-api:standard localhost:5000/quiz-api:1.0
podman push --tls-verify=false localhost:5000/quiz-api:1.0
curl http://localhost:5000/v2/_catalog
podman rmi localhost:5000/quiz-api:1.0
podman run -d --name api-registre --tls-verify=false localhost:5000/quiz-api:1.0
```

Pièges : port 5000 pris par AirPlay sous macOS ; sous Windows et macOS le registre
tourne **dans la podman machine**, `localhost:5000` est donc joignable par Podman
(et par le navigateur grâce au transfert de ports). Bonus `registries.conf` :
le fichier à modifier est celui de la machine (`podman machine ssh`).

## Lab 03 — Volumes (2.3)

Point clé : **PostgreSQL 18** monte `/var/lib/postgresql` (données dans
`/var/lib/postgresql/18/docker`). Un montage sur `/var/lib/postgresql/data`
(tous les vieux tutoriels) fait échouer le démarrage avec un message explicite.
C'est aussi la panne 3 du lab 05 : en parler au lab 03 sans trop insister.

UID : `postgres` = 999 dans le conteneur ; avec `podman unshare` on voit 999 ;
sur l'hôte on voit `subuid_debut + 999 - 1` (ex. 100998). Le root du conteneur
est l'utilisateur lui-même.

## Lab 04 — Réseau, pod, kube (2.5, 2.7)

- Réseau : `podman network create quiz`, `--network quiz`, `DB_HOST=db`. Le
  réseau par défaut (`podman`) n'a pas de DNS : d'où l'échec au palier standard.
- Pod : `podman pod create --name quiz -p 8000:8000`, `--pod quiz`,
  `DB_HOST=127.0.0.1`. Le conteneur `infra` (pause) porte les espaces de noms.
- Kube : `kube/quiz-pod.yaml` montre la forme attendue. **Il a été écrit à la
  main** (Podman indisponible lors de la préparation) : régénérez-le une fois
  sous Podman 6 avec les commandes en tête du fichier et remplacez-le.
- `kube/quiz-pod-durci.yaml` (bonus) : `Secret` + `secretKeyRef`, Redis dans le
  pod, sondes, `securityContext`. **Non testé** : à rejouer avec
  `podman kube play` avant la session.

## Lab 05 — Diagnostic (2.8) : les 4 pannes

Fichier cassé : `labs/05-diagnostic/compose.yaml` (sur `main`).
Corrigé commenté : `labs/05-diagnostic/compose.corrige.yaml`.

| # | Service | Type | Ce qui est semé | Symptôme | Correction |
|---|---|---|---|---|---|
| 1 | front | port | `ports: "8080:80"` | conteneur `Up`, mais `curl localhost:8080` : réponse vide / connexion réinitialisée (nginx écoute sur 8080, rien sur 80) | `"8080:8080"` |
| 2 | api | DNS / nom de service | `DB_HOST: postgres` alors que le service s'appelle `db` | l'API reste `Up` 1 à 2 minutes en journalisant `failed to resolve host 'postgres'`, puis s'arrête (`Exited (1)`, « Abandon : impossible de joindre PostgreSQL ») | `DB_HOST: db` |
| 3 | db | volume | volume monté sur `/var/lib/postgresql/data` avec PostgreSQL 18 | `db` en `Exited (1)` immédiatement ; le journal explique le nouveau chemin | monter sur `/var/lib/postgresql` |
| 4 | redis | permissions / UID rootless | `user: "1000:1000"` (« pour coller à mon UID hôte ») + volume `/data` + `--appendonly yes` | `redis` en `Exited (1)` : `Can't open or create append-only dir appendonlydir: Permission denied` | supprimer `user:` (l'image tourne déjà en utilisateur `redis`, UID 999) |

Les pannes sont **indépendantes** : chacune touche un service différent, a son
propre symptôme dès le lancement et se corrige sans toucher aux autres. Les quatre ont été reproduites avec Docker 29
(voir « Tests » plus bas), puis la stack corrigée a été vérifiée.

Méthode à faire verbaliser : `podman ps -a` (qui est arrêté, avec quel code),
`podman logs`, `podman inspect` (env, montages, utilisateur), `podman port`,
`podman exec ... nginx -T`, résolution DNS depuis l'API.

Pédagogie de la panne 4 : le contresens « aligner l'UID du conteneur sur celui
de l'hôte ». En rootless, l'UID 1000 du conteneur est mappé sur un subuid de
l'hôte, pas sur l'utilisateur ; et le volume a été initialisé avec le
propriétaire de `/data` dans l'image (999). La bonne solution, quand on veut
vraiment ses UID hôte dans un bind mount, est `--userns=keep-id` (compose :
`userns_mode: keep-id`), pas `user:`.

Variante rootless à évoquer à l'oral (non semée, car elle ne se reproduit pas
partout) : publier `80:8080` échoue en rootless sous Linux
(`net.ipv4.ip_unprivileged_port_start=1024`). Selon la configuration de la
podman machine (Windows, macOS), ce n'est pas forcément le cas.

## Lab 06 — Compose (2.10)

`compose.yaml` à la racine. Points de correction :

- quatre services, seul le front publié (`${FRONT_PORT:-8080}:8080`) ;
- `.env` sans secret (versionné ici volontairement, il ne contient que des
  valeurs non sensibles) ;
- secret `db_password` en `file:` (`secrets/db_password.txt`, ignoré par git),
  monté dans `/run/secrets/db_password`, lu via `POSTGRES_PASSWORD_FILE` et
  `DB_PASSWORD_FILE`. Vérifié : le mot de passe n'apparaît pas dans
  `inspect` ;
- `depends_on` avec `condition: service_healthy` (lab 07) ;
- volume nommé `pgdata` sur `/var/lib/postgresql` ;
- Redis sans volume : l'API reconstruit le classement depuis PostgreSQL au
  démarrage (fonction `reconstruire_classement`), vérifié après `down`/`up`.

Front : `front/Containerfile` part de `nginx:1.30.7-alpine3.24` et le rend
non-root (PID dans `/tmp`, `chown` de `/var/cache/nginx` et `/etc/nginx/conf.d`,
`USER 101`). Raison : `nginxinc/nginx-unprivileged` n'existe qu'en 1.30.6 au
2026-11-20, avec 5 CVE critiques (nginx) corrigées en 1.30.7 ; un
`apk upgrade` ne les corrige pas (nginx vient du dépôt nginx.org, pas d'Alpine).
Dès que `nginx-unprivileged:1.30.7` existe, on peut y revenir.

Fournisseur compose : `podman compose` délègue à `docker-compose` ou à
`podman-compose`. **Tests faits avec docker compose uniquement** : à rejouer
avec le fournisseur choisi pour la salle (support de
`depends_on.condition: service_healthy`, `secrets: file:`, `read_only`,
`tmpfs`, `cap_drop` par podman-compose à vérifier).

## Lab 07 — Healthchecks (3.3)

- Déclarés dans `compose.yaml` pour les 4 services (`pg_isready`,
  `redis-cli ping`, `python healthcheck.py`, `wget --spider /nginx-health`).
- `HEALTHCHECK` aussi présent dans `api/Containerfile` et `front/Containerfile`,
  **ignoré** au format OCI : `podman build --format docker` pour le conserver
  (le workflow CI le fait). Démonstration : `podman image inspect <image>`
  (chercher « Healthcheck ») sur deux builds, avec et sans `--format docker`.
- Faire échouer : `FORCE_UNHEALTHY=1` (dans `.env` puis
  `podman compose up -d api`) ou `podman exec <api> touch /tmp/unhealthy`
  (bascule à chaud ; `rm` pour revenir). Vérifié : passage `unhealthy` en
  ~30 s (3 échecs à 10 s), retour `healthy` après suppression du fichier.
  `podman inspect` → `State.Health.Log` affiche
  `healthcheck /health en échec : HTTP Error 503`.
- Sous Podman, les healthchecks sont exécutés par des timers **systemd**
  transitoires. Sans systemd (certains environnements WSL), le statut reste
  `starting` : `podman healthcheck run <conteneur>` permet de vérifier à la main.
- `--health-on-failure=restart|kill|stop` est propre à Podman : bonne démo.
- Piège Git Bash : `/tmp/unhealthy` réécrit en chemin Windows
  (`MSYS_NO_PATHCONV=1`).

## Lab 08 — Scan et durcissement (3.5)

Trivy `0.76.2@sha256:8f6bb947dbc528902e11f2f5be52f7b519f6a39d5d148f41166f2040499768fb`.
L'avis GHSA-69fq-xp46-6x23 précise que les images **référencées par digest**
n'étaient pas touchées par l'incident : bon argument pour le digest.

Résultats mesurés le 2026-11-20 (base de vulnérabilités du jour, les chiffres
changeront) :

| Image | CRITICAL | HIGH | MEDIUM | Remarque |
|---|---|---|---|---|
| `quiz-api:socle` (python:3.14.10) | 15 (4 corrigeables) | 495 | 876 | paquets Debian de dev (mariadb, openexr, libxml2...) inutiles à l'appli |
| `quiz-api:standard` (slim) | 0 | 53 | 112 | plus 8 vulnérabilités dans les bibliothèques embarquées par pip |
| `quiz-api:1.0` (Alpine, sans pip) | 0 | 0 | 11 | |
| `quiz-front:1.0` (nginx 1.30.7) | 0 | 0 | 11 | |
| `nginx-unprivileged:1.30.6-alpine3.24` | 5 | 14 | 17 | pour comparaison : pourquoi on ne l'utilise pas |
| `postgres:18.7-trixie` | 2 (1 corrigeable) | 149 | 212 | image officielle : on attend le correctif amont |
| `redis:8.10.3-alpine3.23` | 0 | 0 | 1 | |

`trivy config api/` : `Containerfile.socle` et `.standard` → DS-0002 (HIGH,
pas de `USER`) et DS-0026 (LOW, pas de `HEALTHCHECK`) ; `Containerfile` final → 0.

Durcissement à l'exécution (palier bonus), dans `compose.yaml` : API en
`read_only` + `tmpfs: /tmp` + `cap_drop: ALL` + `no-new-privileges` ; front en
`cap_drop: ALL` + `no-new-privileges`. Vérifié : l'application et la bascule
`/tmp/unhealthy` fonctionnent toujours.

Scan dans Trivy en conteneur : par archive (`podman save` + `--input`), méthode
portable Windows/macOS/Linux, sans socket Podman.

## Bonus Quadlet

`quadlet/` : `quiz.pod` (publie 8080), `quiz-db.volume`, quatre `.container`
(`Pod=quiz.pod`, `Secret=quiz-db-password`, `HealthCmd`, `Notify=healthy`,
`Restart=always`, durcissement sur l'API), et la variante `quiz.kube`.

Installation (Linux, ou dans `podman machine ssh`) :

```bash
podman build -t quiz-api:1.0 api/ && podman build -t quiz-front:1.0 front/
printf '%s' 'un-mot-de-passe' | podman secret create quiz-db-password -
mkdir -p ~/.config/containers/systemd
cp quadlet/quiz.pod quadlet/quiz-db.volume quadlet/*.container ~/.config/containers/systemd/
systemctl --user daemon-reload
systemctl --user start quiz-pod.service
curl http://localhost:8080/api/leaderboard
```

**Non testé** (pas de Podman ni de systemd lors de la préparation). À vérifier :
le nom d'unité du pod (`quiz-pod.service`), le démarrage des conteneurs avec le
pod, `Notify=healthy`, le montage du secret dans `/run/secrets/quiz-db-password`.
`/usr/libexec/podman/quadlet -dryrun -user` montre les unités générées.

## Bonus CI

`.github/workflows/build.yml` : matrice `api`/`front`, `podman build --format docker`,
scan Trivy (digest épinglé, échec sur CRITICAL corrigeable), push sur
`ghcr.io/<propriétaire>/<dépôt>-api|front` avec le SHA court, `latest` depuis
`main`, version depuis un tag `v*`. `actions/checkout` épinglé par SHA
(`3d3c42e…`, v7.0.1), `persist-credentials: false`, permissions minimales.

Le workflow ne se déclenche que sur `main` (et les PR) : sur cette branche il
est inerte. **Non exécuté** : pour le tester, le copier sur une branche d'un fork
et pousser. Les paquets ghcr.io sont privés par défaut.

---

## Tests effectués pendant la préparation (Docker 29, Windows 11)

Podman n'était pas disponible : tout a été testé avec **Docker 29.8 et docker
compose**, sans aucune fonctionnalité propre à Docker (pas de port < 1024, images
nommées en entier, nginx sur 8080).

Vérifié :

- build des 4 images (`docker build -f ...`) ;
- `compose.yaml` : les 4 services `healthy`, quiz jouable via nginx, scores
  enregistrés, classement Redis correct (meilleur score par joueur conservé),
  validation (pseudo vide → 422) ;
- persistance après `down`/`up` et reconstruction du classement Redis ;
- `FORCE_UNHEALTHY=1` et `/tmp/unhealthy` → `unhealthy`, retour au vert ;
- nginx suit l'API recréée (résolution DNS dynamique) ;
- API sans Redis (`REDIS_HOST` vide) → classement depuis PostgreSQL ;
- front sans Containerfile (bind mounts, commande du README) ;
- secret absent de `docker inspect` ; API en UID 10001, front en UID 101 ;
- stack de diagnostic : les 4 symptômes reproduits, puis la stack corrigée
  fonctionne ;
- scans Trivy 0.76.2 (images et `trivy config`), y compris la méthode par archive
  avec le digest épinglé.

**Non vérifié — à faire sous Podman avant la première session :**

1. Tous les labs avec Podman 6 rootless, sous Windows (WSL), macOS et Linux.
2. `podman compose` avec le fournisseur retenu (podman-compose ou docker-compose) :
   `secrets: file:`, `depends_on: condition: service_healthy`, `read_only`,
   `cap_drop`, `tmpfs`, et le chemin `dockerfile: ../labs/05-diagnostic/Containerfile.api`
   (relatif au contexte) de la stack de diagnostic.
3. Les bind mounts relatifs (`-v ./api:/app:Z`) depuis PowerShell avec la
   podman machine.
4. La panne 4 sous Podman rootless : le volume nommé doit bien hériter du
   propriétaire de `/data` de l'image (copie à l'initialisation), sinon le
   symptôme diffère.
5. `NGINX_ENTRYPOINT_LOCAL_RESOLVERS` avec aardvark-dns (réseau compose) et dans
   un pod (Quadlet : API sur `127.0.0.1`).
6. Régénérer `kube/quiz-pod.yaml` avec `podman kube generate`, rejouer
   `kube/quiz-pod-durci.yaml`.
7. Les unités Quadlet et le workflow GitHub Actions (jamais exécutés).
8. L'avertissement de `podman build` sur `HEALTHCHECK` au format OCI et
   la différence avec `--format docker`.
9. Les durées de démarrage : avec la panne 2, l'API abandonne après 15 tentatives
   (environ 2 minutes, la résolution DNS ajoutant son délai à chaque essai).
