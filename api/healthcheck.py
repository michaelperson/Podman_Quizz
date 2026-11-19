"""Sonde de healthcheck, sans curl ni wget (absents des images Python minimales).

Usage : python healthcheck.py [chemin]   (par défaut /health)
Code de sortie 0 si l'API répond 200, 1 sinon : c'est ce qu'attend
un HEALTHCHECK (Containerfile), --health-cmd (podman run) ou compose.
"""

import sys
import urllib.request

chemin = sys.argv[1] if len(sys.argv) > 1 else "/health"
try:
    with urllib.request.urlopen(f"http://127.0.0.1:8000{chemin}", timeout=3) as reponse:
        sys.exit(0 if reponse.status == 200 else 1)
except Exception as erreur:  # 503, connexion refusée, délai dépassé...
    print(f"healthcheck {chemin} en échec : {erreur}")
    sys.exit(1)
