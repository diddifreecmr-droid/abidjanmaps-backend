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

## Premier administrateur

```powershell
docker compose exec backend python -m scripts.create_user --email admin@example.com --role admin
```

Le script demande le mot de passe deux fois sans l'afficher.

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

Consulter `guide.txt` pour le detail fichier par fichier et
`backend/ARCHITECTURE.md` pour les decisions d'architecture.
