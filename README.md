# AbidjanMaps Backend

Backend FastAPI modulaire pour le routage OSRM et l'enrichissement local PostGIS.

## Stack

- FastAPI et Python
- PostgreSQL/PostGIS
- OSRM
- SQLAlchemy async
- Alembic
- JWT et Argon2
- Docker Compose

## Demarrage

Depuis `E:\AI DIDDI`:

```powershell
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8000/api/v1/health
```

Documentation OpenAPI: `http://127.0.0.1:8000/docs`

## Deploiement Portainer

Pour un deploiement depuis GitHub dans Portainer, utiliser:

```text
docker-compose.portainer.yaml
```

Ce fichier ne lance pas le service one-shot `init-db`. Le backend applique
`alembic upgrade head` au demarrage, puis lance FastAPI. C'est plus compatible
avec Portainer, qui peut traiter les conteneurs one-shot comme des erreurs de
stack.

Variables a definir dans Portainer:

```text
POSTGRES_DB=mapdb
POSTGRES_USER=mapuser
POSTGRES_PASSWORD=mot-de-passe-fort
AUTH_SECRET_KEY=long-secret-aleatoire
OSRM_DATA_PATH=/opt/abidjanmaps/osrm
BACKEND_PORT=8000
OSRM_PORT=5000
POSTGRES_PORT=5432
```

Le dossier serveur `OSRM_DATA_PATH` doit contenir les fichiers OSRM, dont
`ivory-coast-latest.osrm`. Ces fichiers ne sont pas suivis dans GitHub parce
qu'ils sont volumineux et regenerables.

## Premier administrateur

```powershell
docker compose exec backend python -m scripts.create_user --email admin@example.com --role admin
```

Le script demande le mot de passe deux fois sans l'afficher.

Reinitialisation du mot de passe d'un compte existant:

```powershell
docker compose exec backend python -m scripts.create_user --email admin@example.com --reset-password
```

Connexion:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/auth/login" `
  -H "Content-Type: application/json" `
  -d '{"email":"admin@example.com","password":"votre-mot-de-passe"}'
```

Les lectures et le calcul d'itineraire restent publics. Les ecritures demandent un
jeton Bearer. La validation, le rejet et la gestion des comptes demandent le role
`admin`.

## Tests

Depuis `E:\AI DIDDI\backend`, dans l'environnement virtuel:

```powershell
pytest
```

Test d'integration reel avec rollback:

```powershell
$env:RUN_POSTGIS_INTEGRATION="1"
$env:DATABASE_URL="postgresql+asyncpg://mapuser:mapdevpassword@127.0.0.1:5432/mapdb"
pytest tests/integration/test_patch_workflow_postgis.py
```

Consulter `guide.txt` pour le detail fichier par fichier,
`backend/ARCHITECTURE.md` pour les decisions d'architecture et
`DEPLOYMENT.md` pour le workflow GitHub, Portainer et Nginx Proxy Manager.
Le contrat API et les use cases cote frontend sont resumes dans
`FRONTEND_BRIEFING.md`.
