# Bonus — Quadlet : faire gérer le quiz par systemd

Séquence 3.7 · bonus

## Objectif

Décrire les conteneurs de l'application dans des fichiers Quadlet (`.container`,
`.pod`, `.volume` ou `.kube`) pour que **systemd** les démarre, les redémarre et
les relance au démarrage de la machine. Quadlet remplace `podman generate
systemd`, déprécié.

## Prérequis

- Un Linux avec systemd (une VM, WSL avec systemd activé, ou la podman machine
  elle-même : `podman machine ssh`).
- Les images de l'API et du front, construites **sur cette machine-là**
  (`podman images` doit les lister).

Les fichiers d'un utilisateur se placent dans `~/.config/containers/systemd/`.
Après chaque modification :

```bash
systemctl --user daemon-reload
```

Pour voir ce que Quadlet génère (et ses erreurs) :

```bash
/usr/libexec/podman/quadlet -dryrun -user
```

## Palier socle — un conteneur

1. Écrivez `quiz-db.container` pour PostgreSQL : section `[Container]` avec
   `Image=`, `Environment=`, `Volume=`, et une section `[Install]` avec
   `WantedBy=default.target`.
2. `systemctl --user daemon-reload`, puis `systemctl --user start quiz-db.service`.
3. `systemctl --user status quiz-db`, `journalctl --user -u quiz-db`,
   `podman ps`.

**Résultat attendu :** PostgreSQL tourne, géré par systemd ; `podman stop` puis
quelques secondes d'attente... que se passe-t-il avec `Restart=always` dans la
section `[Service]` ?

## Palier standard — l'application dans un pod

1. Un fichier `quiz.pod` qui publie le port 8080, sur le réseau bridge par
   défaut (`Network=podman`) : sans cela, `localhost:8080` ne répond pas depuis
   Windows ou macOS (voir l'encadré du lab 04).
2. Un `.volume` pour la base, un `.container` par service (`db`, `redis`, `api`,
   `front`) avec `Pod=quiz.pod`. Dans un pod, l'API joint la base sur `127.0.0.1`.
3. Le mot de passe dans un secret Podman, pas dans le fichier :

   ```bash
   printf '%s' 'un-mot-de-passe' | podman secret create quiz-db-password -
   ```

   puis `Secret=quiz-db-password` dans les `.container` concernés : où le secret
   est-il monté ?
4. Les healthchecks (`HealthCmd=`) et l'ordre de démarrage
   (`After=`/`Requires=` dans `[Unit]`, `Notify=healthy`).
5. Démarrez le pod (`systemctl --user start quiz-pod.service`) et jouez.

## Palier bonus

- Remplacez les fichiers `.pod`/`.container` par un seul `quiz.kube` qui pointe
  vers le manifeste généré au lab 04 (`Yaml=`).
- Survivre à la déconnexion et au redémarrage : `loginctl enable-linger`.
- `AutoUpdate=registry` et `podman auto-update` : à quoi cela sert-il, et quel
  lien avec l'épinglage des versions ?
