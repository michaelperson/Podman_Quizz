# Lab 07 — Healthchecks et diagnostic d'un échec

Séquence 3.3 · 35 min · Objectifs O4, O5

## Objectif

Déclarer des healthchecks sur l'application, les voir passer au vert, puis
provoquer volontairement un échec et le diagnostiquer.

## Ce que fournit l'application

- `GET /health` : 200 si PostgreSQL et Redis (s'il est configuré) répondent,
  503 sinon, avec le détail de chaque vérification ;
- `GET /ready` : 200 quand l'initialisation est terminée ;
- `api/healthcheck.py` : appelle `/health` et sort avec le code 0 ou 1. Les
  images Python minimales n'ont ni `curl` ni `wget` : on utilise Python.
- Deux façons de **faire échouer** `/health` volontairement :
  - la variable d'environnement `FORCE_UNHEALTHY=1` (au lancement) ;
  - le fichier `/tmp/unhealthy` dans le conteneur (à chaud, sans redémarrer) :
    `podman exec <api> touch /tmp/unhealthy`, puis `rm` pour revenir au vert.

> **Git Bash sous Windows** réécrit `/tmp/unhealthy` en chemin Windows.
> Préfixez la commande avec `MSYS_NO_PATHCONV=1`, ou utilisez PowerShell ou WSL.

## Le piège à connaître

`HEALTHCHECK` dans un Containerfile **n'existe pas au format OCI**, le format
par défaut de `podman build`. Podman affiche un avertissement et l'ignore :
l'image n'a pas de healthcheck. Trois solutions :

- construire au format Docker : `podman build --format docker ...`
  (ou la variable `BUILDAH_FORMAT=docker`) ;
- déclarer le healthcheck au lancement : `podman run --health-cmd ...` ;
- le déclarer dans `compose.yaml` (`healthcheck:`).

## Palier socle — un healthcheck au lancement

1. Lancez l'API (avec sa base, voir labs 04 ou 06) en déclarant le healthcheck :

   ```bash
   podman run -d --name api --network quiz -p 8000:8000 \
     -e DB_HOST=db -e DB_PASSWORD=change-moi \
     --health-cmd "python healthcheck.py" \
     --health-interval 10s --health-retries 3 --health-start-period 20s \
     quiz-api:standard
   ```

2. Observez : `podman ps` (colonne STATUS), `podman healthcheck run api`
   (code de sortie : `echo $?`), et
   `podman inspect api --format '{{json .State.Health}}'`.

**Résultat attendu :** `podman ps` affiche `(healthy)` après quelques secondes.

> Podman fait tourner les healthchecks grâce à des minuteries **systemd**. Si le
> statut reste bloqué sur `(starting)`, votre environnement n'a probablement pas
> systemd (certaines distributions WSL) : `podman healthcheck run api` lance la
> vérification à la main. Parlez-en au formateur.

## Palier standard — dans compose, puis provoquer un échec

1. Ajoutez un `healthcheck:` à chacun des quatre services de votre `compose.yaml` :
   - `db` : `pg_isready` ;
   - `redis` : `redis-cli ping` ;
   - `api` : `python healthcheck.py` ;
   - `front` : nginx répond sur `/nginx-health` (l'image Alpine a `wget`).
2. Remplacez les `depends_on` simples par `condition: service_healthy`.
   Lancez `podman compose up -d` et regardez l'ordre de démarrage.
3. Provoquez un échec et diagnostiquez-le :

   ```bash
   podman exec <conteneur-api> touch /tmp/unhealthy
   ```

   Au bout de combien de temps l'API passe-t-elle `unhealthy` ? Retrouvez la
   cause **uniquement** avec `podman inspect` (section `Health`, champ `Log`).
   Puis revenez au vert.
4. Recommencez avec `FORCE_UNHEALTHY=1` dans `.env` puis `podman compose up -d api`.
5. Arrêtez la base (`podman compose stop db`) : que deviennent le healthcheck de
   l'API et la réponse de `/health` ?

**Résultat attendu :** les quatre services sont `(healthy)` ; vous savez lire la
cause d'un échec dans `podman inspect`.

## Palier bonus

- Ajoutez `HEALTHCHECK` au Containerfile de l'API. Construisez avec et sans
  `--format docker` (deux tags différents), lisez l'avertissement du build et
  cherchez « Healthcheck » dans `podman image inspect` des deux images.
- Podman sait **réagir** à un échec : `podman run --health-on-failure=restart`
  (ou `kill`, `stop`). Essayez-le avec le fichier `/tmp/unhealthy`.
- Pourquoi est-ce une mauvaise idée que la sonde de **vie** (liveness) dépende de
  la base ? Quelle différence avec une sonde de **disponibilité** (readiness) ?
  Comment les deux routes `/health` et `/ready` se répartiraient-elles dans
  Kubernetes ?

## Pour finir

Gardez votre `compose.yaml` : il sert au lab 08.
