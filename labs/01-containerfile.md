# Lab 01 — Conteneuriser l'API « Quiz »

Séquence 1.8 · 85 min · Objectif O2

## Objectif

Écrire le Containerfile de l'API (`api/`), construire l'image avec `podman build`
et lancer l'API dans un conteneur. Puis améliorer ce Containerfile palier par palier
et comparer la taille des images obtenues.

## Ce dont vous avez besoin

- Le dépôt cloné, Podman qui fonctionne (`podman info`).
- Lire `api/requirements.txt` et le haut de `api/main.py` : comment l'API se
  lance-t-elle ? Sur quel port écoute-t-elle ?

Pour ce lab, l'API peut tourner **sans base de données** : elle attend PostgreSQL
puis abandonne. Pour la voir répondre, lancez d'abord une base sur un réseau
(les réseaux seront expliqués au lab 04) :

```bash
podman network create quiz
podman run -d --name db --network quiz \
  -e POSTGRES_DB=quiz -e POSTGRES_USER=quiz -e POSTGRES_PASSWORD=change-moi \
  docker.io/library/postgres:18.7-trixie
```

## Palier socle — un Containerfile qui marche

1. Créez `api/Containerfile`. Point de départ suggéré :

   ```dockerfile
   FROM docker.io/library/python:3.14.10
   # à vous : dossier de travail, copie du code, installation des dépendances,
   # port documenté, commande de démarrage
   ```

   Instructions utiles : `WORKDIR`, `COPY`, `RUN`, `EXPOSE`, `CMD`.

2. Construisez l'image depuis le dossier `api/` :

   ```bash
   podman build -t quiz-api:socle .
   ```

3. Lancez-la et testez :

   ```bash
   podman run -d --name api --network quiz -p 8000:8000 \
     -e DB_HOST=db -e DB_PASSWORD=change-moi quiz-api:socle
   podman logs -f api          # Ctrl+C pour sortir
   curl http://localhost:8000/health
   curl http://localhost:8000/api/questions
   ```

4. Modifiez une ligne de `main.py` (un commentaire suffit) et reconstruisez.
   Observez quelles étapes sont reprises du cache (`Using cache`) et lesquelles
   sont rejouées. Réorganisez votre Containerfile pour que `pip install` ne soit
   **pas** rejoué quand seul le code change.

**Résultat attendu :** `/health` répond `{"statut": "ok", ...}` et une modification
du code ne réinstalle pas les dépendances.

Questions à se poser : pourquoi l'API doit-elle écouter sur `0.0.0.0` et pas sur
`127.0.0.1` ? `EXPOSE` publie-t-il le port ? Que se passe-t-il à `podman stop`
si la commande est écrite en forme « shell » (`CMD uvicorn ...`) plutôt qu'en
forme « exec » (`CMD ["uvicorn", ...]`) ?

## Palier standard — multi-stage et image slim

1. Réécrivez le Containerfile (gardez l'ancien sous un autre nom, par exemple
   `Containerfile.socle`, et construisez avec `-f`) :
   - une étape `build` qui installe les dépendances dans un environnement virtuel
     (`python -m venv /opt/venv`) ;
   - une étape finale, partant de `python:3.14.10-slim-trixie`, qui ne récupère
     que l'environnement virtuel (`COPY --from=build ...`) et le code utile.
2. Ajoutez un fichier `api/.containerignore` pour ne pas envoyer au build ce qui
   ne sert à rien (`__pycache__`, environnements virtuels locaux...).
3. Construisez `quiz-api:standard`, lancez-la comme au palier socle.

**Résultat attendu :** l'API répond comme avant ; l'image est nettement plus petite.

## Palier bonus — non-root et image minimale

1. Faites tourner l'API sous un utilisateur dédié, non-root, avec un UID
   numérique (`USER`). Le code doit appartenir à root : l'utilisateur de
   l'application ne doit pas pouvoir le modifier.
2. Essayez une base encore plus petite (`python:3.14.10-alpine3.24`, ou une image
   « distroless »). Attention : l'étape de build et l'étape finale doivent utiliser
   la même bibliothèque C (glibc ou musl).
3. L'outil `pip` est-il utile dans l'image finale ? Retirez-le.
4. Vérifiez :

   ```bash
   podman run --rm quiz-api:bonus id
   podman top api user huser pid args   # utilisateur dans le conteneur et sur l'hôte
   ```

5. Comparez les trois images :

   ```bash
   podman images --filter reference=quiz-api
   podman history quiz-api:socle
   ```

**Résultat attendu :** un tableau `palier / base / taille`, que vous présenterez
au débriefing (séquence 1.9). Ordre de grandeur : plus d'un gigaoctet au socle,
moins de 100 Mo au bonus.

## Pour finir

```bash
podman rm -f api
```

Gardez le réseau `quiz` et la base pour le lab suivant, ou supprimez-les
(`podman rm -f db && podman network rm quiz`).
