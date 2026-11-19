# Lab 03 — Persister la base PostgreSQL

Séquence 2.3 · 35 min · Objectif O3

## Objectif

Faire en sorte que les données de PostgreSQL survivent à la suppression du
conteneur, d'abord avec un volume nommé, puis avec un bind mount, et comprendre
ce que deviennent les UID en mode rootless.

## Palier socle — volume nommé

1. Créez un volume et lancez PostgreSQL dessus :

   ```bash
   podman volume create quiz-pgdata
   podman run -d --name db \
     -e POSTGRES_DB=quiz -e POSTGRES_USER=quiz -e POSTGRES_PASSWORD=change-moi \
     -v quiz-pgdata:/var/lib/postgresql \
     docker.io/library/postgres:18.7-trixie
   ```

   > **PostgreSQL 18 a changé de répertoire de données.** Le volume se monte sur
   > `/var/lib/postgresql` (les données vont dans `/var/lib/postgresql/18/docker`).
   > Beaucoup de tutoriels montrent encore `/var/lib/postgresql/data` : avec
   > l'image 18, le conteneur refuse alors de démarrer. Lisez son message dans
   > `podman logs db` si cela vous arrive.

2. Écrivez quelque chose dans la base :

   ```bash
   podman exec -it db psql -U quiz -d quiz
   ```

   ```sql
   CREATE TABLE preuve (id serial, texte text);
   INSERT INTO preuve (texte) VALUES ('je survis au conteneur');
   \q
   ```

3. Supprimez le conteneur, **pas** le volume, puis recréez-le avec la même
   commande qu'à l'étape 1.

   ```bash
   podman rm -f db
   ```

4. Vérifiez que la ligne est toujours là (`SELECT * FROM preuve;`).

**Résultat attendu :** la table et sa ligne existent toujours. `podman volume ls`
et `podman volume inspect quiz-pgdata` montrent le volume et son emplacement.

## Palier standard — l'API sur une base persistante, et les UID

1. Faites de même avec la stack du lab 01 : la base sur `quiz-pgdata`, l'API
   (votre image) qui s'y connecte. Jouez une partie avec `curl` :

   ```bash
   curl -X POST http://localhost:8000/api/scores \
     -H "Content-Type: application/json" \
     -d '{"pseudo": "moi", "reponses": {"1": 0, "2": 1}}'
   curl http://localhost:8000/api/leaderboard
   ```

   Supprimez puis recréez la base et l'API : le classement est-il conservé ?

2. Qui possède les fichiers du volume ?

   ```bash
   podman exec db ls -ln /var/lib/postgresql/18/docker | head
   podman unshare ls -ln "$(podman volume inspect --format '{{.Mountpoint}}' quiz-pgdata)/18/docker" | head
   ls -ln "$(podman volume inspect --format '{{.Mountpoint}}' quiz-pgdata)" 
   ```

   (sous Windows et macOS, lancez ces commandes dans `podman machine ssh`).
   Expliquez les trois résultats : UID dans le conteneur, UID dans l'espace de
   noms utilisateur, UID réel sur l'hôte (`cat /etc/subuid`).

**Résultat attendu :** vous savez expliquer pourquoi l'utilisateur `postgres`
(UID 999 dans le conteneur) apparaît sous un grand UID sur l'hôte.

## Palier bonus — bind mount, `:Z` et `--userns=keep-id`

1. Remplacez le volume nommé par un dossier de votre choix sur l'hôte
   (`-v ./pgdata:/var/lib/postgresql:Z`). Que contient ce dossier vu depuis l'hôte ?
   Pouvez-vous le supprimer avec `rm -rf` sans `podman unshare` ?
2. Sous Fedora ou RHEL (SELinux) : essayez sans `:Z`. Quel message obtenez-vous ?
   Quelle est la différence entre `:z` et `:Z` ?
3. Lancez `podman run --rm --userns=keep-id -v ./front:/data:Z docker.io/library/python:3.14.10-slim-trixie ls -ln /data`
   puis la même commande sans `--userns=keep-id`. Que change cette option ?

## Pour finir

```bash
podman rm -f db api
podman volume rm quiz-pgdata    # seulement quand vous n'en avez plus besoin
```
