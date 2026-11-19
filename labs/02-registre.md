# Lab 02 — Publier son image dans un registre et la relancer

Séquence 1.11 · 35 min · Objectif O2

## Objectif

Démarrer un registre d'images local, y pousser l'image de l'API construite au
lab 01, supprimer l'image locale, puis relancer l'API **depuis le registre**.

## Palier socle — registre local, push, pull

1. Démarrez un registre (le registre officiel CNCF Distribution) :

   ```bash
   podman run -d --name registre -p 5000:5000 docker.io/library/registry:3.1.2
   ```

   > macOS : le port 5000 est souvent pris par le récepteur AirPlay. Utilisez
   > alors `-p 5001:5000` et `localhost:5001` dans toute la suite.

2. Donnez à votre image un nom qui désigne ce registre :

   ```bash
   podman tag quiz-api:standard localhost:5000/quiz-api:1.0
   ```

3. Poussez-la. Le registre local parle HTTP et non HTTPS : il faut le dire
   explicitement à Podman.

   ```bash
   podman push --tls-verify=false localhost:5000/quiz-api:1.0
   ```

4. Vérifiez ce que contient le registre (c'est une API HTTP) :

   ```bash
   curl http://localhost:5000/v2/_catalog
   curl http://localhost:5000/v2/quiz-api/tags/list
   ```

5. Supprimez l'image locale, puis relancez l'API depuis le registre :

   ```bash
   podman rmi localhost:5000/quiz-api:1.0
   podman run -d --name api-registre -p 8001:8000 --tls-verify=false \
     localhost:5000/quiz-api:1.0
   podman logs api-registre
   ```

**Résultat attendu :** `podman run` télécharge l'image depuis `localhost:5000`
et le conteneur démarre (il attend une base : c'est normal ici).

## Palier standard — tags et versions

1. Poussez une deuxième version `1.1` (modifiez un texte dans `questions.json`
   et reconstruisez), et faites pointer un tag `latest` sur la `1.1`.
2. Comparez les digests : `podman images --digests`,
   `podman inspect --format '{{.Digest}}' ...`.
3. Relancez la `1.0` **par son digest** (`localhost:5000/quiz-api@sha256:...`).
   Pourquoi un digest est-il plus sûr qu'un tag ?

**Résultat attendu :** vous savez expliquer la différence entre un tag (une
étiquette déplaçable) et un digest (l'empreinte immuable du contenu).

## Palier bonus — un registre persistant et déclaré « non sécurisé »

1. Recréez le registre avec un volume pour ses données
   (`-v quiz-registre:/var/lib/registry`) : supprimez-le, recréez-le, vos images
   y sont toujours.
2. Au lieu de `--tls-verify=false` à chaque commande, déclarez le registre comme
   non sécurisé dans `registries.conf` (fichier `~/.config/containers/registries.conf`
   sous Linux, **dans la podman machine** sous Windows et macOS : `podman machine ssh`).
   Pourquoi est-ce une mauvaise idée pour un registre qui n'est pas sur `localhost` ?
3. Si vous avez un compte Quay.io ou Docker Hub : poussez-y l'image
   (`podman login quay.io`), puis supprimez-la.

## Pour finir

```bash
podman rm -f api-registre
# gardez le registre si vous voulez l'utiliser plus tard, sinon :
podman rm -f registre
```
