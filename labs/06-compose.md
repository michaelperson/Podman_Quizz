# Lab 06 — Composer l'application « Quiz » complète

Séquence 2.10 · 90 min · Objectif O4

## Objectif

Décrire toute l'application dans un fichier `compose.yaml` à la racine du dépôt :
front nginx, API, PostgreSQL et Redis. Une seule commande doit tout démarrer :

```bash
podman compose up -d --build
```

Vérifiez d'abord votre fournisseur : `podman compose version`. `podman compose`
délègue à `docker-compose` s'il est installé, sinon à `podman-compose`, et leur
comportement diffère sur quelques points. Le formateur indique celui à utiliser.

## Ce que vous avez déjà

- l'image de l'API (lab 01) : dans compose, `build:` pointe vers `./api` ;
- pour le front, deux possibilités :
  - socle : l'image `docker.io/library/nginx:1.30.7-alpine3.24` avec deux bind
    mounts (`front/public` et `front/nginx`, voir le README) ;
  - standard : écrire `front/Containerfile` et le construire depuis compose.

## Palier socle — tout démarre

1. Créez `compose.yaml` avec quatre services : `front`, `api`, `db`, `redis`.
2. Le front est publié sur le port **8080** de l'hôte ; ni l'API, ni la base, ni
   Redis ne sont publiés.
3. Les services se trouvent par leur **nom de service** : `DB_HOST`,
   `REDIS_HOST`, `API_HOST`.
4. La base est persistée dans un volume nommé (rappel : PostgreSQL 18, voir lab 03).
5. Démarrez, jouez une partie, consultez les journaux :

   ```bash
   podman compose up -d --build
   podman compose ps
   podman compose logs -f api
   ```

**Résultat attendu :** le quiz fonctionne sur <http://localhost:8080> et le
classement indique la source `redis`. Après `podman compose down` puis `up -d`,
les scores sont toujours là.

## Palier standard — variables, secret, dépendances

1. **Variables** : sortez du `compose.yaml` ce qui varie d'un poste à l'autre
   (port publié, nom de la base, utilisateur, tags des images) dans un fichier
   `.env`, avec des valeurs par défaut dans le compose (`${FRONT_PORT:-8080}`).
   Contrôlez le résultat avec `podman compose config`.
2. **Secret** : le mot de passe de la base ne doit apparaître ni dans
   `compose.yaml`, ni dans `.env`, ni dans `podman inspect`.
   - créez `secrets/db_password.txt` (voir `secrets/README.md`) : ce dossier est
     ignoré par git ;
   - déclarez un secret `db_password` (`secrets:` au niveau racine, `file:`) et
     donnez-le à `db` et à `api` ;
   - PostgreSQL lit `POSTGRES_PASSWORD_FILE`, l'API lit `DB_PASSWORD_FILE`. Où le
     secret est-il monté dans le conteneur ?
   - vérifiez : `podman inspect` de l'API ne doit montrer aucun mot de passe.
3. **Dépendances** : `depends_on` pour que la base et Redis démarrent avant
   l'API, et l'API avant le front. Est-ce que « démarré » veut dire « prêt » ?
   (Le lab 07 complétera avec des healthchecks et `condition: service_healthy`.)
4. Construisez le front avec votre propre `front/Containerfile`, non-root,
   à l'écoute sur 8080.

**Résultat attendu :** `git status` ne montre aucun fichier de secret ;
`grep -ri password compose.yaml .env` ne révèle aucune valeur.

## Palier bonus

- Politique de redémarrage (`restart:`) : tuez le processus de l'API
  (`podman compose kill api`) et observez.
- Mettez à l'échelle : pourquoi `podman compose up -d --scale api=2` fonctionne-t-il
  ici (aucun port publié sur l'API) mais échouerait-il pour le front ?
- Un fichier `compose.override.yaml` pour le développement : le code de l'API
  monté en bind mount et `uvicorn --reload`.
- Redis perd-il le classement quand on recrée son conteneur ? Lisez la fonction
  `reconstruire_classement` dans `api/main.py`.

## Pour finir

```bash
podman compose down        # garde les volumes
podman compose down -v     # supprime aussi les volumes
```
