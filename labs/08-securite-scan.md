# Lab 08 — Scanner et durcir l'image

Séquence 3.5 · 70 min · Objectif O6

## Objectif

Scanner les images de l'application avec Trivy, lire le rapport, puis durcir
l'image de l'API jusqu'à ce que le scan ne remonte plus de vulnérabilité
critique corrigeable.

## Trivy, en conteneur et épinglé

On n'installe pas Trivy : on le lance en conteneur, **à une version précise**.
En mars 2026, la chaîne d'approvisionnement de Trivy a été compromise
(version 0.69.4, images 0.69.5 et 0.69.6 malveillantes, avis
[GHSA-69fq-xp46-6x23](https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23)).
Un tag peut être déplacé ; un digest, non. On épingle donc tag **et** digest :

```bash
TRIVY=docker.io/aquasec/trivy:0.76.2@sha256:8f6bb947dbc528902e11f2f5be52f7b519f6a39d5d148f41166f2040499768fb
```

(PowerShell : `$TRIVY = "docker.io/aquasec/trivy:0.76.2@sha256:8f6bb9..."` en entier,
puis `$TRIVY` au lieu de `"$TRIVY"`.)

Trivy, dans son conteneur, ne voit pas les images de votre Podman. Le plus simple
et le plus portable : exporter l'image en archive et la lui donner.

```bash
podman save -o api-socle.tar quiz-api:socle
podman run --rm -v trivy-cache:/root/.cache -v ./api-socle.tar:/scan/image.tar:ro,Z \
  "$TRIVY" image --input /scan/image.tar
```

Le volume `trivy-cache` garde la base de vulnérabilités entre deux scans
(le premier téléchargement prend un moment).

## Palier socle — lire un rapport

1. Scannez l'image naïve du lab 01 (`python:3.14.10` complète). Limitez d'abord
   aux sévérités hautes : `--severity CRITICAL,HIGH`.
2. Pour trois vulnérabilités, notez : le paquet, la version installée, la version
   corrigée (si elle existe), et **d'où vient le paquet** (le système Debian ?
   une bibliothèque Python ?). L'application utilise-t-elle seulement ces paquets ?
3. Relancez avec `--ignore-unfixed`. Que signifie cette option et pourquoi le
   nombre baisse-t-il autant ?

**Résultat attendu :** vous savez lire une ligne du rapport et distinguer une
vulnérabilité corrigeable d'une vulnérabilité sans correctif.

## Palier standard — comparer et durcir

1. Scannez les images des autres paliers du lab 01 (multi-stage slim, puis
   non-root minimale) et remplissez :

   | Image | Base | Taille | CRITICAL | HIGH | dont corrigeables |
   |---|---|---|---|---|---|
   | socle | | | | | |
   | standard | | | | | |
   | bonus | | | | | |

2. Scannez aussi votre **Containerfile** (mauvaises pratiques, pas des CVE) :

   ```bash
   podman run --rm -v ./api:/src:ro,Z "$TRIVY" config /src
   ```

3. Durcissez l'image de l'API jusqu'à **zéro vulnérabilité critique
   corrigeable** et zéro alerte haute de `trivy config`. Pistes : base minimale,
   multi-stage, `USER` non-root, retirer ce qui ne sert pas à l'exécution
   (`pip` en est un bon exemple), versions épinglées.
4. Scannez l'image du front et celles de PostgreSQL et Redis. Si une image de
   base a des vulnérabilités corrigées dans une version plus récente, que
   faites-vous ? (changer de tag, attendre, reconstruire avec mise à jour des
   paquets ?)
5. Vérifiez qu'aucun secret n'est dans vos images : `podman history --no-trunc`,
   et `--scanners secret` dans Trivy.

**Résultat attendu :** le tableau rempli et une image d'API qui passe :

```bash
podman run --rm -v trivy-cache:/root/.cache -v ./api.tar:/scan/image.tar:ro,Z \
  "$TRIVY" image --severity CRITICAL --ignore-unfixed --exit-code 1 --input /scan/image.tar
echo $?    # 0
```

## Palier bonus — durcir l'exécution

1. Lancez l'API en durcissant aussi le conteneur, pas seulement l'image :
   `--read-only` (que faut-il rendre inscriptible ? `--tmpfs /tmp`),
   `--cap-drop=ALL`, `--security-opt no-new-privileges`. L'application
   fonctionne-t-elle toujours ? Reportez ces options dans `compose.yaml`
   (`read_only`, `cap_drop`, `security_opt`, `tmpfs`).
2. Produisez un SBOM : `--format cyclonedx --output /scan/sbom.json`
   (montez le dossier en écriture). À quoi sert-il ?
3. Épinglez vos images de base par digest dans le Containerfile. Quel est le
   prix à payer (mises à jour de sécurité) ? Quel outil pourrait vous aider
   (Renovate, Dependabot) ?

## Pour finir

```bash
rm -f *.tar           # PowerShell : Remove-Item *.tar
podman volume rm trivy-cache   # si vous voulez récupérer la place
```
