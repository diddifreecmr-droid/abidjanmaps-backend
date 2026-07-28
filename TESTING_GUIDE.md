# AbidjanMaps - Guide de tests

Ce document explique quels tests sont automatiques, quels tests sont a lancer en
staging, et quels tests restent des validations metier humaines.

## 1. Tests automatiques backend

Ces tests sont pour le developpeur backend.

Commande locale:

```text
cd backend
pytest
```

Ils verifient:

- les endpoints principaux;
- les regles de validation;
- l'authentification;
- les repositories;
- le scoring;
- les taxonomies;
- les reponses utiles au frontend;
- les workflows `proposed / validated / rejected`.

Ces tests ne prouvent pas que le VPS est bien configure. Ils prouvent que le
code backend est coherent.

## 2. Tests Docker local

Ces tests verifient que la stack locale fonctionne avec Docker, PostGIS et OSRM.

Depuis la racine du projet:

```text
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m scripts.seed_phase2
docker compose exec backend python -m scripts.check_phase2_scenarios
```

La commande Alembic est normalement lancee automatiquement au demarrage du
backend en developpement. Elle reste indiquee ici comme commande de secours si
une table manque apres une nouvelle migration.

Le seed peut retourner:

```json
{"created": 0, "updated": 0, "validated": 0, "skipped": 4}
```

Cela veut dire que les donnees existaient deja et que le script n'a pas cree de
doublons.

## 3. Tests staging Portainer

Ces tests sont a lancer dans le conteneur `backend` de la stack staging.

```text
python -m scripts.seed_phase2
python -m scripts.check_phase2_scenarios
python -m scripts.check_staging_public_api
```

Commande recommandee maintenant:

```text
python -m scripts.validate_staging
```

Ce script regroupe les checks staging dans une sortie JSON claire:

- `public-api`: health, db-health, roads, places, reports et propositions;
- `phase3-map-traces`: login, creation de trace, analyse, insight, revue admin
  et conversion en `route_report proposed`;
- `seed-phase2`: optionnel si `VALIDATE_STAGING_SEED_PHASE2=1`.

Mode public uniquement:

```text
VALIDATE_STAGING_MODE=public python -m scripts.validate_staging
```

Mode complet:

```text
PHASE3_TEST_EMAIL=admin@example.com PHASE3_TEST_PASSWORD=mot-de-passe python -m scripts.validate_staging
```

Dans Portainer, si tu es deja dans le conteneur `backend`, tu peux utiliser:

```text
export VALIDATE_STAGING_MODE=full
export BACKEND_BASE_URL=http://127.0.0.1:8000
export PHASE3_TEST_EMAIL=admin@example.com
export PHASE3_TEST_PASSWORD=mot-de-passe
python -m scripts.validate_staging
```

Depuis ton Terminal Windows/CMD contre l'URL publique staging:

```cmd
cd E:\AI DIDDI\backend
set "VALIDATE_STAGING_MODE=full"
set "BACKEND_BASE_URL=http://abidjanmaps-backend-staging.diddifree.com"
set "PHASE3_TEST_EMAIL=admin@example.com"
set "PHASE3_TEST_PASSWORD=mot-de-passe"
python -m scripts.validate_staging
```

Le script `check_phase2_scenarios` verifie:

- le backend repond;
- OSRM retourne des propositions;
- PostGIS retrouve les troncons locaux;
- le scoring renvoie une meilleure route eligible;
- les contraintes vehicule sont presentes dans la reponse.

Il ne cherche pas a prouver que toutes les alternatives sont eligibles. Selon la
version OSRM, les fichiers carte et les donnees locales, certaines alternatives
peuvent devenir incompatibles. Ce qui compte pour la Phase 2 est que le backend
detecte cette incompatibilite et classe une meilleure route eligible.

Le script `check_staging_public_api` verifie:

- `/api/v1/health`;
- `/api/v1/db-health`;
- `/api/v1/roads`;
- `/api/v1/geocoding/search`;
- `/api/v1/places`;
- `/api/v1/route-reports`;
- `/api/v1/routes/proposals/detail`.

Il est utile pour confirmer que le domaine public expose bien les endpoints
attendus par le frontend.

Avant un redeploiement staging avec donnees importantes, verifier aussi:

- que le volume PostgreSQL n'est pas supprime;
- qu'aucune commande `down -v` n'est utilisee sans decision explicite;
- qu'un backup existe si les donnees ont de la valeur.

## 3.1. Import OSM de base

Le backend peut importer les noms OSM depuis le fichier PBF utilise pour OSRM:

```text
python -m scripts.import_osm_base
```

Par defaut:

- fichier: `/data/osrm/ivory-coast-latest.osm.pbf`;
- zone: bbox Abidjan `-4.25,5.15,-3.70,5.55`;
- objets importes: routes OSM nommees et POI/places OSM nommes;
- statut: `validated`;
- origine: `extra_metadata.source = "osm"`;
- anti-doublon: `osm_type + osm_id` dans `extra_metadata`.

Dans Portainer/VPS:

```text
export OSM_IMPORT_BBOX="-4.25,5.15,-3.70,5.55"
python -m scripts.import_osm_base
python -m scripts.validate_staging
```

Depuis Terminal Windows/CMD contre Docker local:

```cmd
docker compose exec backend python -m scripts.import_osm_base
```

Si le script dit que `osmium` manque, il faut rebuild l'image backend car la
dependance a ete ajoutee:

```cmd
docker compose build --no-cache backend
docker compose up -d
```

## 4. Tests domaine

Ces tests sont a faire humainement, avec les yeux d'un utilisateur ou d'un
responsable produit.

Ils verifient:

- est-ce que la route recommandee semble plausible?
- est-ce que le badge `Peage` apparait au bon endroit?
- est-ce que les routes etroites sont bien expliquees?
- est-ce que les points de controle sont visibles?
- est-ce que le frontend affiche les raisons du classement?
- est-ce que les donnees locales sont bien visibles sur la carte?
- est-ce que les admins comprennent comment valider ou rejeter une donnee?

Ces tests ne doivent pas etre entierement automatises au debut, car ils
dependent de la realite terrain et de la comprehension utilisateur.

## 5. Qui fait quoi?

Backend:

- ecrire les tests unitaires et API;
- maintenir `pytest`;
- maintenir les scripts `seed_phase2` et `check_phase2_scenarios`;
- verifier les logs backend;
- corriger les erreurs techniques.

Owner projet / testeur domaine:

- lancer les checks staging apres deploiement;
- tester les URLs publiques;
- verifier que la carte et les resultats ont du sens;
- remonter les cas terrain incoherents.

Frontend:

- tester le rendu carte;
- tester l'utilisation du GeoJSON;
- tester les erreurs API;
- tester les flux login/moderation;
- verifier mobile et desktop.
- utiliser `/openapi.json` pour generer ou verifier les types API si possible.

## 6. Tests minimum pour fermer Phase 2

Avant de declarer la Phase 2 fermee:

- `pytest` passe en local;
- `seed_phase2` passe en Docker local;
- `check_phase2_scenarios` passe en Docker local;
- `seed_phase2` passe en staging;
- `check_phase2_scenarios` passe en staging;
- `check_staging_public_api` passe en staging;
- `/api/v1/health` repond depuis le domaine staging;
- `/api/v1/routes/proposals/detail` repond depuis le domaine staging;
- `/api/v1/roads` retourne des geometries;
- `/api/v1/places` retourne des locations;
- `/api/v1/route-reports` retourne des geometries quand disponibles.

## 7. Tests Phase 3 map-traces

Ces tests verifieront la collecte GPS.

Minimum technique:

- creer ou utiliser un utilisateur connecte;
- demarrer une trace Map Core;
- envoyer plusieurs positions;
- terminer la trace;
- relire le detail;
- verifier que `actual_distance_m` et `actual_duration_s` sont calcules.

Minimum frontend:

- permission GPS demandee clairement;
- positions envoyees par batch;
- trace reelle visible sur la carte;
- route prevue visible a cote de la trace reelle;
- erreurs `401`, `404`, `409`, `422` affichees clairement.

Minimum analyse Phase 3 V2:

- analyser une trace terminee;
- obtenir un score qualite;
- comparer prevu et reel;
- afficher les evenements detectes;
- ne pas transformer automatiquement une trace en donnee validee.

Commandes API a verifier:

```text
POST /api/v1/map-traces/{trace_id}/analyze
GET  /api/v1/map-traces/{trace_id}/analysis
```

Points attendus:

- `average_speed_kmh` est calcule par le backend;
- `phone_average_speed_kmh` est secondaire;
- les traces faibles retournent `quality_label=weak` ou `bad`;
- les traces non terminees doivent retourner une erreur `409`.

Script de verification API:

```text
python -m scripts.check_phase3_map_traces
```

`scripts.check_phase3_journeys` existe encore comme alias temporaire.

Le script demande un utilisateur existant via variables d'environnement:

```cmd
set "BACKEND_BASE_URL=http://127.0.0.1:8000"
set "PHASE3_TEST_EMAIL=admin@example.com"
set "PHASE3_TEST_PASSWORD=mot-de-passe"
```

Important pour Windows CMD: utiliser `set "VAR=value"`. Eviter
`set VAR="value"` car les guillemets peuvent devenir une partie de la valeur.

Il teste:

- login;
- demarrage d'une trace Map Core;
- envoi de 4 positions GPS;
- fin de la trace;
- lecture du detail;
- analyse GPS;
- lecture de l'analyse stockee;
- creation d'au moins un insight Map Core;
- validation admin d'un insight;
- conversion de l'insight valide en `route_report proposed`;
- presence de `duplicate_key`, `evidence_count` et des metadonnees de preuve
  utiles a la revue admin.

Endpoints admin utiles a tester manuellement:

```text
GET /api/v1/map-trace-insights?sort=evidence&order=desc
GET /api/v1/map-trace-insights/review-queue
GET /api/v1/map-trace-insights/route-report-candidates
```
