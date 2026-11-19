# Bonus — Construire et publier l'image avec GitHub Actions

Séquence 3.7 · bonus · nécessite un compte GitHub

## Objectif

À chaque push sur `main`, un workflow GitHub Actions construit les images de
l'API et du front avec Podman, les scanne avec Trivy et les publie sur le
registre de GitHub, `ghcr.io`.

## Prérequis

- Un fork de ce dépôt (ou votre propre dépôt avec vos Containerfiles).
- Les runners `ubuntu-24.04` de GitHub ont Podman préinstallé.

## Palier socle — build

1. Créez `.github/workflows/build.yml`, déclenché sur `push` vers `main` et sur
   `pull_request`.
2. Un job qui récupère le code (`actions/checkout`) et construit l'image de
   l'API avec `podman build`.
3. Poussez et suivez l'exécution dans l'onglet **Actions**.

**Résultat attendu :** le workflow est vert et le journal montre le build.

## Palier standard — publication sur ghcr.io

1. Donnez au workflow le droit d'écrire des paquets, et rien de plus :

   ```yaml
   permissions:
     contents: read
     packages: write
   ```

2. Connectez-vous à `ghcr.io` avec le jeton fourni par Actions
   (`secrets.GITHUB_TOKEN`), via `podman login --password-stdin`.
3. Nommez l'image `ghcr.io/<propriétaire>/<dépôt>-api` (en **minuscules** :
   les noms d'images n'acceptent pas les majuscules), taguez-la avec le SHA court
   du commit, et poussez-la. Ne poussez pas sur les `pull_request`.
4. Faites la même chose pour le front (une `matrix` évite de dupliquer le job).
5. Récupérez l'image publiée sur votre poste :
   `podman pull ghcr.io/<propriétaire>/<dépôt>-api:<sha>`.
   Le paquet est privé par défaut : rendez-le public dans ses réglages ou
   faites `podman login ghcr.io`.

## Palier bonus — chaîne d'approvisionnement

- Ajoutez une étape Trivy (en conteneur, version **et** digest épinglés) qui
  fait échouer le workflow s'il reste une vulnérabilité critique corrigeable.
- Épinglez `actions/checkout` par SHA de commit et non par tag. Pourquoi ?
  (Repensez à l'incident Trivy de mars 2026, qui passait aussi par des tags
  d'actions GitHub réécrits.)
- `persist-credentials: false` sur le checkout : qu'est-ce que cela évite ?
- Construisez au format Docker (`--format docker`) pour garder le `HEALTHCHECK`.
