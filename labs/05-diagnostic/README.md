# Lab 05 — Diagnostic n° 1 : une application cassée

Séquence 2.8 · 50 min · Objectif O5

## Objectif

La stack de ce dossier (`compose.yaml`) devrait faire tourner le quiz complet.
Elle contient **quatre pannes indépendantes**. Trouvez-les, expliquez-les,
corrigez-les. Le but n'est pas seulement de réparer, mais de suivre une
**méthode** : partir d'un symptôme, formuler une hypothèse, la vérifier avec un
outil, corriger, revérifier.

## Ce qui est attendu quand tout fonctionne

- `http://localhost:8080` affiche le quiz et permet de jouer une partie ;
- le classement s'affiche (source `redis`) ;
- les quatre conteneurs `front`, `api`, `db` et `redis` sont `Up` et le restent ;
- `podman compose exec api python healthcheck.py` se termine avec le code 0.

Le code de l'application (`api/`, `front/`) et `Containerfile.api` ne sont **pas**
en panne : seul `compose.yaml` l'est.

## Lancer la stack

Depuis ce dossier :

```bash
cd labs/05-diagnostic
podman compose up -d --build
```

## La boîte à outils

| Question | Outil |
|---|---|
| Quels conteneurs tournent, lesquels sont arrêtés, avec quel code ? | `podman ps -a`, `podman compose ps` |
| Que dit le processus ? | `podman logs <conteneur>`, `podman compose logs <service>` |
| Avec quelle configuration a-t-il été lancé ? | `podman inspect <conteneur>` (variables, montages, ports, utilisateur) |
| Quels ports sont publiés, vers quoi ? | `podman port <conteneur>` |
| Que voit-on depuis l'intérieur ? | `podman exec -it <conteneur> sh` |
| Le nom se résout-il ? | `podman exec api python -c "import socket; print(socket.gethostbyname('...'))"` |
| Qui possède les fichiers d'un volume ? | `podman exec`, `podman unshare ls -ln <chemin>` |
| Qu'écoute nginx ? | `podman exec <front> nginx -T` |

Après chaque correction : `podman compose up -d` (compose recrée seulement les
services modifiés), puis revérifiez **tous** les symptômes.

## Paliers

### Socle

Trouvez et corrigez **deux** pannes. Pour chacune, notez dans le tableau
ci-dessous le symptôme observé, la commande qui vous a mis sur la piste et la
correction.

| # | Service | Symptôme | Commande révélatrice | Cause | Correction |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |

### Standard

Les **quatre** pannes sont trouvées, corrigées et expliquées. Pour chacune, vous
savez dire pourquoi elle est fréquente « dans la vraie vie ».

### Bonus

- L'une des pannes ne se manifeste qu'au bout d'une trentaine de secondes
  (parfois plus, selon le poste). Laquelle,
  et pourquoi ? Comment rendre la stack plus parlante (indice : `healthcheck`
  et `depends_on: condition: service_healthy`, voir lab 06) ?
- Proposez une cinquième panne réaliste et faites-la trouver à votre voisin.

## Nettoyage

```bash
podman compose down -v     # -v supprime aussi les volumes de ce lab
```
