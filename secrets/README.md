# Secrets

Ce dossier contient les secrets locaux. Il n'est **pas versionné** (voir `.gitignore`),
à l'exception de ce README.

Créer le mot de passe de la base avant `podman compose up` :

```bash
openssl rand -hex 16 > secrets/db_password.txt
```

Sans openssl, sous PowerShell :

```powershell
[guid]::NewGuid().ToString("N") | Out-File -NoNewline -Encoding ascii secrets/db_password.txt
```
