# Lab 04 — API et PostgreSQL : réseau, puis pod, puis Kubernetes

Séquences 2.5 (60 min) et 2.7 (20 min) · Objectif O3

## Objectif

Faire communiquer l'API et PostgreSQL de deux façons : deux conteneurs sur un
réseau Podman (ils se trouvent par leur nom), puis deux conteneurs dans un pod
(ils partagent `localhost`). Enfin, générer le manifeste Kubernetes du pod et
le rejouer.

Image de l'API : celle que vous avez construite au lab 01 (ci-dessous
`quiz-api:standard`, adaptez le nom).

## Partie 1 (2.5) — Réseau

### Palier socle

1. Créez un réseau et lancez la base dessus, avec un nom :

   ```bash
   podman network create quiz
   podman run -d --name db --network quiz \
     -e POSTGRES_DB=quiz -e POSTGRES_USER=quiz -e POSTGRES_PASSWORD=change-moi \
     -v quiz-pgdata:/var/lib/postgresql \
     docker.io/library/postgres:18.7-trixie
   ```

2. Lancez l'API sur le même réseau, en lui donnant le **nom** de la base :

   ```bash
   podman run -d --name api --network quiz -p 8000:8000 \
     -e DB_HOST=db -e DB_PASSWORD=change-moi quiz-api:standard
   curl http://localhost:8000/health
   ```

3. Observez la résolution de noms :

   ```bash
   podman exec api python -c "import socket; print(socket.gethostbyname('db'))"
   podman inspect db --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
   podman network inspect quiz
   ```

**Résultat attendu :** `/health` répond 200 ; le nom `db` se résout en l'adresse
IP du conteneur `db`.

### Palier standard

1. Lancez l'API **sans** `--network quiz` (réseau par défaut). Que dit
   `podman logs api` ? Pourquoi le nom `db` n'est-il pas résolu ?
2. La base n'est publiée sur aucun port de l'hôte : pourquoi l'API y accède-t-elle
   quand même ? Que faudrait-il pour y accéder avec un client installé sur votre
   poste ? Est-ce souhaitable ?
3. Ajoutez Redis sur le réseau (`docker.io/library/redis:8.10.3-alpine3.23`,
   nom `redis`) et `-e REDIS_HOST=redis` à l'API. Le champ `source` de
   `/api/leaderboard` doit passer de `postgres` à `redis`.

### Palier bonus

1. Ajoutez le front (voir la commande du README) sur le réseau et jouez une
   partie dans le navigateur.
2. Créez un second réseau `quiz-back` : la base et Redis seulement sur lui,
   l'API sur les deux (`podman network connect`), le front seulement sur `quiz`.
   Vérifiez que le front ne peut pas joindre la base.

Nettoyage avant la partie 2 : `podman rm -f api db redis front`
(gardez le volume).

## Partie 2 (2.5) — Pod

### Palier socle

1. Créez un pod. Les ports se publient **sur le pod**, pas sur les conteneurs :

   ```bash
   podman pod create --name quiz -p 8000:8000
   ```

2. Lancez la base et l'API dans le pod :

   ```bash
   podman run -d --pod quiz --name quiz-db \
     -e POSTGRES_DB=quiz -e POSTGRES_USER=quiz -e POSTGRES_PASSWORD=change-moi \
     -v quiz-pgdata:/var/lib/postgresql \
     docker.io/library/postgres:18.7-trixie
   podman run -d --pod quiz --name quiz-api \
     -e DB_HOST=127.0.0.1 -e DB_PASSWORD=change-moi quiz-api:standard
   curl http://localhost:8000/health
   ```

3. `podman pod ps`, `podman ps --pod` : combien de conteneurs voyez-vous ?
   À quoi sert le conteneur `infra` ?

**Résultat attendu :** l'API joint la base sur `127.0.0.1` ; le pod se gère
d'un bloc (`podman pod stop quiz`, `podman pod start quiz`).

### Palier standard

Débriefing 2.6 : réseau ou pod ? Préparez deux arguments pour chacun
(isolation, mise à l'échelle séparée, conflits de ports dans un pod,
proximité avec Kubernetes...).

## Partie 3 (2.7) — `podman kube generate` puis `kube play`

### Palier socle

1. Générez le manifeste du pod :

   ```bash
   podman kube generate quiz -f quiz-pod.yaml
   ```

   Lisez-le : où sont les conteneurs, les variables, le port, le volume ?
   Que remarquez-vous à propos du mot de passe ?

2. Supprimez le pod puis rejouez le manifeste :

   ```bash
   podman pod rm -f quiz
   podman kube play quiz-pod.yaml
   podman pod ps
   curl http://localhost:8000/health
   ```

3. Arrêtez et supprimez ce qui a été créé par le manifeste :

   ```bash
   podman kube down quiz-pod.yaml
   ```

**Résultat attendu :** le pod est recréé à l'identique depuis le YAML et les
données sont toujours là (le volume `quiz-pgdata` est réutilisé).

### Palier bonus

1. Générez aussi un `Service` (`podman kube generate --service ...`).
2. Sortez le mot de passe du manifeste : un objet `Secret` dans le même fichier
   et `valueFrom.secretKeyRef` dans le conteneur (`podman kube play` sait les lire).
3. Ajoutez un `securityContext` au conteneur de l'API (`runAsNonRoot: true`,
   `allowPrivilegeEscalation: false`). Rejouez.

## Pour finir

```bash
podman pod rm -f quiz
podman network rm quiz
podman volume rm quiz-pgdata   # si vous n'en avez plus besoin
```
