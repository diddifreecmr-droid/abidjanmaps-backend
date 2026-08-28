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
- Collecte GPS Map Core Phase 3 V1

## Demarrage

Depuis `E:\AI DIDDI`:

```cmd
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8000/api/v1/health
```

En developpement, le backend applique aussi les migrations Alembic au demarrage
avant de lancer Uvicorn avec `--reload`.

Si une table manque apres l'ajout d'une migration, lancer manuellement:

```cmd
docker compose exec backend alembic upgrade head
```

Documentation OpenAPI: `http://127.0.0.1:8000/docs`

Contrat OpenAPI brut pour le frontend:

```text
http://127.0.0.1:8000/openapi.json
```

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

Profil OSRM actuel:

```text
OSRM_PROFILE=driving
```

Les profils API `car`, `motorcycle` et `truck` sont des profils metier utilises
par le backend pour le prix, les contraintes et le scoring. Aujourd'hui, ils
passent tous par le meme moteur OSRM `driving`. Un futur profil pieton devra
etre prepare avec ses propres fichiers OSRM et probablement un service OSRM
dedie, par exemple `osrm-walking`.

Les donnees PostgreSQL/PostGIS sont conservees dans le volume Docker
`postgis_data`. Ne pas supprimer ce volume sans backup. En production, prevoir
une DB separee ou managée avec sauvegardes automatiques.

## Premier administrateur

```cmd
docker compose exec backend python -m scripts.create_user --email admin@example.com --role admin
```

Le script demande le mot de passe deux fois sans l'afficher.

Reinitialisation du mot de passe d'un compte existant:

```cmd
docker compose exec backend python -m scripts.create_user --email admin@example.com --reset-password
```

Connexion:

```cmd
curl.exe -X POST "http://127.0.0.1:8000/api/v1/auth/login" -H "Content-Type: application/json" -d "{\"email\":\"admin@example.com\",\"password\":\"votre-mot-de-passe\"}"
```

Les lectures et le calcul d'itineraire restent publics. Les ecritures demandent un
jeton Bearer. La validation, le rejet et la gestion des comptes demandent le role
`admin`.

## Tests

Depuis `E:\AI DIDDI\backend`, dans l'environnement virtuel:

```cmd
pytest
```

Test d'integration reel avec rollback:

```cmd
set "RUN_POSTGIS_INTEGRATION=1"
set "DATABASE_URL=postgresql+asyncpg://mapuser:mapdevpassword@127.0.0.1:5432/mapdb"
pytest tests/integration/test_patch_workflow_postgis.py
```

Check API Phase 3 map-traces contre un backend demarre:

```cmd
set "BACKEND_BASE_URL=http://127.0.0.1:8000"
set "PHASE3_TEST_EMAIL=admin@example.com"
set "PHASE3_TEST_PASSWORD=votre-mot-de-passe"
python -m scripts.check_phase3_map_traces
```

Validation staging complete contre l'URL publique ou depuis le conteneur backend:

```cmd
set "VALIDATE_STAGING_MODE=full"
set "BACKEND_BASE_URL=http://abidjanmaps-backend-staging.diddifree.com"
set "PHASE3_TEST_EMAIL=admin@example.com"
set "PHASE3_TEST_PASSWORD=votre-mot-de-passe"
python -m scripts.validate_staging
```

Validation via Docker Compose, sans entrer dans le conteneur:

```cmd
docker compose --profile validation run --rm map-validation
```

Par defaut, cette commande lance les checks publics: health, DB, recherche,
routing Abidjan et propositions de routes. Pour inclure le test complet des
traces GPS avec authentification:

```cmd
set "VALIDATE_STAGING_MODE=full"
set "PHASE3_TEST_EMAIL=admin@example.com"
set "PHASE3_TEST_PASSWORD=votre-mot-de-passe"
docker compose --profile validation run --rm map-validation
```

Le service `map-validation` appelle le backend par le reseau Docker interne avec:

```text
BACKEND_BASE_URL=http://backend:8000
```

Import de la base OSM locale depuis le fichier `.osm.pbf` monte dans Docker:

```bash
python -m scripts.import_osm_base
```

Par defaut, l'import utilise une bbox autour d'Abidjan et lit
`/data/osrm/ivory-coast-latest.osm.pbf`. Pour changer la zone:

```bash
export OSM_IMPORT_BBOX="-4.25,5.15,-3.70,5.55"
python -m scripts.import_osm_base
```

Recherche locale pour le frontend:

```text
GET /api/v1/geocoding/search?q=Anador
GET /api/v1/places/search?q=Anador
GET /api/v1/roads/search?q=Boulevard
```

Pour classer les resultats proches de l'utilisateur en premier:

```text
GET /api/v1/geocoding/search?q=Anador&bias_lat=5.33&bias_lng=-4.02
```

Consulter `guide.txt` pour le detail fichier par fichier,
`backend/ARCHITECTURE.md` pour les decisions d'architecture et
`DEPLOYMENT.md` pour le workflow GitHub, Portainer et Nginx Proxy Manager.
Le contrat API et les use cases cote frontend sont resumes dans
`FRONTEND_BRIEFING.md`. L'etat des phases backend est suivi dans
`PHASE_STATUS.md`. La collecte GPS et la future analyse des traces sont
expliquees dans `PHASE3_GPS_ANALYSIS.md` et `FRONTEND_PHASE3_BRIEF.md`. La
separation entre tests automatiques, staging et domaine est expliquee dans
`TESTING_GUIDE.md`. Le protocole operationnel pour les chauffeurs testeurs est
dans `FIELD_TEST_PROTOCOL.md`.
