# AbidjanMaps - Etat des phases backend

Ce document sert de point de controle pour savoir ou en est le backend.

## Phase 1 - Map Core de base

Statut backend:

```text
Terminee fonctionnellement
```

Ce qui est disponible:

- FastAPI structure;
- Docker local;
- Docker Portainer staging;
- OSRM branche;
- calcul de route simple;
- GeoJSON route pour la carte;
- distance;
- duree;
- prix estimatif;
- health backend;
- health database;
- tests automatises.

Endpoints principaux:

```text
GET  /api/v1/health
GET  /api/v1/db-health
POST /api/v1/route
```

Points a verifier avant de declarer Phase 1 fermee en staging:

- OSRM demarre bien sur le VPS;
- les fichiers OSRM sont presents dans `OSRM_DATA_PATH`;
- `GET /api/v1/health` repond correctement depuis le domaine staging;
- `POST /api/v1/route` retourne une vraie route depuis le domaine staging.

## Phase 2 - Enrichissement local du Map Core

Statut backend:

```text
Quasi terminee, reste validation staging et donnees de demonstration
```

Ce qui est disponible:

- tables PostGIS `roads`, `places`, `route_reports`;
- historiques `road_history`, `place_history`, `route_report_history`;
- workflow `proposed / validated / rejected`;
- seules les donnees `validated` influencent le scoring;
- creation et modification de roads;
- creation et modification de places;
- creation et modification de route reports;
- validation/rejet admin;
- recherche de places;
- taxonomies metier;
- alternatives OSRM;
- scoring backend des alternatives;
- score breakdown lisible;
- details d'enrichissement par route;
- profils vehicule `car`, `motorcycle`, `truck`;
- contraintes largeur et tonnage;
- authentification JWT;
- roles `user` et `admin`;
- documentation frontend;
- documentation deploiement;
- seed Phase 2 idempotent;
- script de verification scenario Phase 2.

Endpoints principaux:

```text
POST /api/v1/routes/proposals
POST /api/v1/routes/proposals/detail

GET    /api/v1/roads
GET    /api/v1/roads/{road_id}
POST   /api/v1/roads
PATCH  /api/v1/roads/{road_id}
POST   /api/v1/roads/{road_id}/validate
POST   /api/v1/roads/{road_id}/reject
GET    /api/v1/roads/{road_id}/history
GET    /api/v1/roads/taxonomy

GET    /api/v1/places
GET    /api/v1/places/search
GET    /api/v1/places/{place_id}
POST   /api/v1/places
PATCH  /api/v1/places/{place_id}
POST   /api/v1/places/{place_id}/validate
POST   /api/v1/places/{place_id}/reject
GET    /api/v1/places/{place_id}/history

GET    /api/v1/route-reports
GET    /api/v1/route-reports/{report_id}
POST   /api/v1/route-reports
PATCH  /api/v1/route-reports/{report_id}
POST   /api/v1/route-reports/{report_id}/validate
POST   /api/v1/route-reports/{report_id}/reject
GET    /api/v1/route-reports/{report_id}/history
GET    /api/v1/route-reports/taxonomy
```

Correction importante faite pour la carte:

- `roads` retourne maintenant `geometry`;
- `places` retourne maintenant `location`;
- `route_reports` retourne maintenant `geometry`.

Sans ces champs, le frontend pouvait lire les donnees metier mais ne pouvait pas
les afficher correctement sur une carte.

Checklist pour fermer officiellement Phase 2:

- appliquer la derniere version sur staging;
- creer ou reset un compte admin staging;
- charger les donnees OSRM sur le VPS;
- lancer les migrations Alembic;
- lancer le seed Phase 2;
- tester `/routes/proposals/detail` avec OSRM et PostGIS reels;
- verifier que les alternatives retournent `score_breakdown`;
- verifier que les roads/places/reports retournent leurs coordonnees;
- creer une road proposee depuis l'API;
- valider cette road avec admin;
- verifier qu'elle apparait dans le scoring;
- creer un route_report propose;
- valider le route_report;
- verifier qu'il influence le scoring;
- verifier les historiques.

Commande seed Phase 2:

```text
python -m scripts.seed_phase2
```

Commande scenario Phase 2:

```text
python -m scripts.check_phase2_scenarios
```

Ce script verifie que chaque profil obtient une meilleure proposition eligible
et que les contraintes vehicule sont bien detectees. Il ne force pas toutes les
alternatives a etre eligibles, car les alternatives OSRM peuvent varier entre
local et staging.

Commande de verification publique staging:

```text
python -m scripts.check_staging_public_api
```

Ce script controle les endpoints publics principaux que le frontend doit pouvoir
consommer.

## Phase 3 - Vraies donnees terrain

La Phase 3 ne doit pas etre confondue avec la Phase 2.

La Phase 2 donne les outils pour recevoir, valider et utiliser les donnees.
La Phase 3 commence quand on alimente le systeme avec de vraies donnees terrain.

Objectifs Phase 3:

- collecter des traces GPS reelles;
- enregistrer les traces GPS terrain de test;
- importer une base OSM exploitable pour les noms de routes et de lieux;
- importer ou saisir un volume plus important de roads;
- importer ou saisir plus de places locales;
- faire remonter les signalements terrain;
- analyser les traces pour identifier les ecarts OSRM/reel;
- detecter les temps reels par zone ou troncon;
- faire evoluer le scoring avec des donnees observees;
- ajouter des outils de qualite de donnees;
- preparer une moderation plus solide;
- preparer les premieres integrations mobiles ou chauffeurs test.

Modules probables Phase 3:

```text
map_traces
gps_traces
data_quality
field_collection
moderation
```

Use cases Phase 3:

- demarrer un trajet de collecte;
- envoyer des positions GPS pendant le trajet;
- terminer le trajet;
- comparer duree OSRM et duree reelle;
- transformer une trace GPS en suggestion de road/report;
- detecter une route souvent lente;
- detecter une route souvent contournee;
- proposer automatiquement un enrichissement;
- faire valider l'enrichissement par un admin.

Ce qu'il ne faut pas encore faire trop vite:

- extraire tous les modules en microservices physiques;
- recalculer le score de tous les troncons en temps reel;
- construire un moteur GPS avance avant d'avoir des donnees;
- automatiser OSRM pour la production sans stabiliser la methode de livraison.
- ajouter un profil pieton public avant d'avoir prepare un vrai moteur OSRM
  walking.

Decision OSRM actuelle:

```text
Le service osrm:5000 utilise les fichiers Cote d'Ivoire prepares pour le profil
driving. Les profils API car, motorcycle et truck restent des profils metier
backend, mais ils utilisent tous ce moteur OSRM driving pour le calcul de base.
```

Sujet futur:

```text
Ajouter un profil walking/pedestrian avec des fichiers OSRM separes et un
service OSRM dedie, par exemple osrm-walking.
```

Sujet important a traiter avant production:

```text
Automatiser la preparation ou la livraison des fichiers OSRM.
```

Options possibles:

- image Docker OSRM preconstruite;
- job Docker `osrm-prepare`;
- script VPS idempotent.

Pour le moment, la manipulation OSRM peut rester manuelle en staging, mais elle
devra etre automatisee avant production.

## Phase 3 V3 - Test terrain Map Core 1.4

Statut backend:

```text
Protocole pret
```

Objectif:

- organiser le test avec 5 chauffeurs;
- valider autocomplete, routing, alternatives et traces GPS;
- verifier que les traces produisent des insights utiles;
- faire valider les insights par un admin;
- convertir certains insights en route_reports;
- verifier que les route_reports valides influencent le scoring.

Document operationnel:

```text
FIELD_TEST_PROTOCOL.md
```

Contenu du protocole:

- test DiddiMap seul;
- test autocomplete;
- test route simple;
- test alternatives et scoring;
- test signalements terrain;
- test traces GPS Map Core;
- revue admin des insights;
- test DiddiGo branche sur DiddiMap;
- objectifs chiffres pour 2 a 4 semaines;
- rapport quotidien;
- criteres de decision en fin de test.

Pre-requis avant lancement:

- staging deploye;
- migrations appliquees;
- OSRM disponible;
- PostGIS disponible;
- compte admin staging fonctionnel;
- frontend branche sur staging;
- validation Docker OK;
- equipe DiddiGo prete a envoyer les traces GPS.

## Phase 3 V1 - Map Traces

Statut backend:

```text
Demarre
```

Ce qui est disponible:

- module vertical `journeys` avec API publique `map-traces`;
- table `journeys`;
- table `journey_positions`;
- stockage PostGIS des points GPS;
- demarrage d'un trajet de collecte;
- ajout de positions GPS par batch;
- cloture d'un trajet;
- calcul simple de distance reelle;
- calcul simple de duree reelle;
- lecture d'un trajet et de ses positions;
- liste des trajets de l'utilisateur connecte;
- migration Alembic `20260727_0005`.

Endpoints officiels Phase 3 V1:

```text
POST /api/v1/map-traces/start
POST /api/v1/map-traces/{trace_id}/positions
POST /api/v1/map-traces/{trace_id}/finish
GET  /api/v1/map-traces/{trace_id}
GET  /api/v1/map-traces
```

Regles:

- tous les endpoints `map-traces` demandent un token Bearer;
- une trace appartient a l'utilisateur connecte;
- le frontend ne choisit pas `user_id`;
- une trace `finished` ne peut plus recevoir de positions;
- l'analyse automatique des traces n'est pas encore activee.

Definition of Done Phase 3 V1:

- un utilisateur connecte peut demarrer un trajet;
- il peut envoyer plusieurs positions GPS;
- il peut terminer le trajet;
- le backend renvoie une distance reelle et une duree reelle;
- le trajet peut etre relu avec ses positions;
- les migrations passent en local et staging.
- le script `check_phase3_map_traces` passe sur local et staging.

## Phase 3 V2 - Analyse des traces GPS

Statut backend:

```text
Implementation V1 disponible
```

Objectif:

- analyser les traces Map Core terminees;
- produire un resume technique et metier;
- calculer un score de qualite;
- comparer distance/duree prevues avec distance/duree reelles;
- detecter des signaux simples comme zone lente ou detour;
- preparer des suggestions terrain sans modifier automatiquement le scoring;
- generer des insights Map Core `proposed` pour revue admin.
- detecter des candidats `possible_slow_segment`, `possible_blocked_road` et
  `possible_detour`.
- limiter les doublons d'insights actifs avec une `duplicate_key`.
- compter les confirmations terrain avec `evidence_count`: meme trace =
  doublon technique ignore, autre trace meme zone = preuve supplementaire.

Endpoints probables:

```text
POST /api/v1/map-traces/{trace_id}/analyze
GET  /api/v1/map-traces/{trace_id}/analysis
```

Stockage:

```text
journey_analyses
map_trace_insights
```

La vitesse moyenne principale est calculee par le backend avec la distance entre
points GPS divisee par le temps entre points. Le champ `speed_mps` du telephone
est conserve comme comparaison secondaire.

Documents ajoutes:

```text
PHASE3_GPS_ANALYSIS.md
FRONTEND_PHASE3_BRIEF.md
```

Script de verification:

```text
python -m scripts.check_phase3_map_traces
```

Endpoints de revue admin:

```text
GET  /api/v1/map-trace-insights
GET  /api/v1/map-trace-insights/review-queue
GET  /api/v1/map-trace-insights/route-report-candidates
GET  /api/v1/map-trace-insights/{insight_id}
GET  /api/v1/map-trace-insights/{insight_id}/detail
POST /api/v1/map-trace-insights/{insight_id}/validate
POST /api/v1/map-trace-insights/{insight_id}/reject
POST /api/v1/map-trace-insights/{insight_id}/convert-to-route-report
```

Filtres de lecture:

```text
status
insight_type
severity_min
trace_id
sort
order
```

Decision importante:

```text
Les traces GPS doivent d'abord etre analysees et validees humainement avant
d'influencer roads, route_reports ou le score des alternatives.
```

Conversion controlee:

```text
insight validated -> route_report proposed
```

La route `/route-report-candidates` aide l'admin a trouver les insights valides
qui ont assez de preuves pour etre convertis. Elle ne convertit rien toute seule.

Le `route_report` cree doit encore etre valide separement avant d'influencer le
scoring.

## Base OSM et geocodage local

Statut backend:

```text
Preparation disponible
```

Ce qui est ajoute:

- script `python -m scripts.import_osm_base`;
- import des routes OSM nommees vers `roads`;
- import des POI/places OSM nommes vers `places`;
- bbox Abidjan par defaut;
- endpoint `GET /api/v1/roads/search?q=...`;
- endpoint unifie `GET /api/v1/geocoding/search?q=...`.

Decision importante:

```text
OSM sert de base initiale. Les donnees terrain Diddi restent une couche locale
au-dessus, avec aliases, noms vernaculaires, validations et signalements.
```
