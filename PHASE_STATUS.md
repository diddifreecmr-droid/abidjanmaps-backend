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

## Phase 3 - Vraies donnees terrain

La Phase 3 ne doit pas etre confondue avec la Phase 2.

La Phase 2 donne les outils pour recevoir, valider et utiliser les donnees.
La Phase 3 commence quand on alimente le systeme avec de vraies donnees terrain.

Objectifs Phase 3:

- collecter des traces GPS reelles;
- enregistrer les journeys de test;
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
journeys
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
