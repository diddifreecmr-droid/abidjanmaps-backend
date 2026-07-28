# AbidjanMaps - Briefing frontend Phase 1, Phase 2 et Phase 3

Ce document explique au developpeur frontend ce que le backend permet deja de
faire, comment l'API fonctionne, et quels ecrans/use cases devraient exister
cote interface utilisateur pour couvrir les phases 1, 2 et 3.

Pour le detail complet de la collecte GPS et de l'analyse des traces, consulter
aussi:

```text
FRONTEND_PHASE3_BRIEF.md
PHASE3_GPS_ANALYSIS.md
```

## Base API

En staging:

```text
http://abidjanmaps-backend-staging.diddifree.com
```

En local:

```text
http://127.0.0.1:8000
```

Tous les endpoints backend sont prefixes par:

```text
/api/v1
```

Exemple:

```text
GET /api/v1/health
```

## Etat general du backend

Le backend sait deja:

- calculer un itineraire simple avec OSRM;
- retourner une geometrie GeoJSON utilisable par une carte frontend;
- calculer un prix estimatif;
- proposer plusieurs alternatives de route;
- enrichir les alternatives avec des donnees locales PostGIS;
- scorer les alternatives selon les routes bloquees, degradees, inondables,
  points de controle, peages, securite de nuit, largeur et tonnage;
- gerer des lieux locaux;
- gerer des troncons routiers locaux;
- gerer des signalements locaux;
- gerer un workflow de validation `proposed / validated / rejected`;
- historiser les changements;
- authentifier des utilisateurs avec JWT;
- proteger les actions d'ecriture et d'administration;
- collecter des traces GPS Map Core avec les endpoints `map-traces`.

## Swagger et contrat OpenAPI

Le frontend peut utiliser Swagger pour comprendre et tester les endpoints:

```text
http://abidjanmaps-backend-staging.diddifree.com/docs
```

Le contrat machine-readable est:

```text
http://abidjanmaps-backend-staging.diddifree.com/openapi.json
```

Ce fichier peut servir a generer les types TypeScript ou un client API.

Exemple simple:

```text
npx openapi-typescript http://abidjanmaps-backend-staging.diddifree.com/openapi.json -o src/api/schema.ts
```

Exemple avec Orval:

```text
npx orval --input http://abidjanmaps-backend-staging.diddifree.com/openapi.json --output src/api/generated
```

Recommandation:

- utiliser Swagger pour explorer;
- utiliser `openapi.json` pour typer le code frontend;
- ne pas recopier les payloads a la main si un client genere peut le faire;
- garder une variable `API_BASE_URL` par environnement.

## Authentification

Les lectures publiques ne demandent pas de token.

Les actions d'ecriture demandent:

```text
Authorization: Bearer <access_token>
```

Les actions de validation, rejet et gestion des utilisateurs demandent un role:

```text
admin
```

### Login

```http
POST /api/v1/auth/login
Content-Type: application/json
```

Payload:

```json
{
  "email": "admin@example.com",
  "password": "ADMIN12345"
}
```

Reponse:

```json
{
  "access_token": "jwt...",
  "token_type": "bearer",
  "expires_in_seconds": 28800
}
```

Use case frontend:

- afficher un formulaire login;
- stocker le token apres connexion;
- ajouter le header Bearer sur les actions protegees;
- rediriger les non-connectes si une action demande un compte;
- afficher un message clair si le login echoue.

### Utilisateur courant

```http
GET /api/v1/users/me
Authorization: Bearer <token>
```

Reponse:

```json
{
  "id": 1,
  "email": "admin@example.com",
  "role": "admin",
  "is_active": true,
  "created_at": "2026-07-25T10:00:00Z",
  "updated_at": "2026-07-25T10:00:00Z"
}
```

Use case frontend:

- savoir si l'utilisateur est connecte;
- savoir s'il est `admin`;
- afficher ou masquer les boutons de validation/rejet.

## Health et diagnostic

### Backend et OSRM

```http
GET /api/v1/health
```

Reponse attendue:

```json
{
  "status": "ok",
  "service": "map-routing-service",
  "routing_engine": "available"
}
```

### PostgreSQL/PostGIS

```http
GET /api/v1/db-health
```

Reponse:

```json
{
  "status": "ok",
  "service": "map-routing-service",
  "database": "available"
}
```

Use case frontend:

- page technique simple pour verifier si le backend est joignable;
- afficher un etat "routing disponible" dans un dashboard admin;
- utile en staging avant de tester la carte.

## Phase 1 - Map Core de base

La Phase 1 cote utilisateur doit permettre de demander un trajet et d'afficher
le resultat sur une carte.

### Use case 1: calculer une route simple

L'utilisateur choisit un depart et une destination.

```http
POST /api/v1/route
Content-Type: application/json
```

Payload:

```json
{
  "start": {
    "lat": 5.3329,
    "lng": -4.02003
  },
  "end": {
    "lat": 5.33892,
    "lng": -3.97754
  },
  "profile": "car"
}
```

Reponse:

```json
{
  "status": "ok",
  "route": {
    "geometry": {
      "type": "LineString",
      "coordinates": [
        [-4.02003, 5.3329],
        [-3.97754, 5.33892]
      ]
    },
    "distance_m": 1450,
    "duration_s": 360
  },
  "price": {
    "amount": 1100,
    "currency": "XOF"
  }
}
```

Important GeoJSON:

- les coordonnees GeoJSON sont dans l'ordre `[lng, lat]`;
- les champs de formulaire humain sont souvent `lat`, `lng`;
- ne pas inverser les deux quand on dessine sur la carte.

Use case frontend attendu:

- selection depart/destination sur la carte ou via champs;
- appel API;
- dessin de la LineString sur la carte;
- affichage distance en km;
- affichage duree en minutes;
- affichage prix en XOF;
- gestion des erreurs.

### Profils vehicule

Valeurs supportees:

```text
car
motorcycle
truck
```

Alias acceptes par le backend:

```text
voiture -> car
auto -> car
moto -> motorcycle
motorbike -> motorcycle
camion -> truck
poids_lourd -> truck
```

Le frontend peut afficher:

- Voiture;
- Moto;
- Camion.

Et envoyer:

```text
car
motorcycle
truck
```

### Erreurs importantes Phase 1

Exemple JSON invalide:

```json
{
  "status": "error",
  "code": "invalid_request",
  "message": "Invalid JSON body. Check quotes, commas and braces.",
  "details": [
    {
      "field": "body",
      "reason": "Invalid JSON body. Check quotes, commas and braces.",
      "type": "json_invalid"
    }
  ]
}
```

Autres codes possibles:

```text
invalid_request
out_of_coverage
no_route_found
routing_engine_unavailable
routing_timeout
invalid_routing_response
```

Use case frontend:

- afficher les erreurs backend de maniere lisible;
- ne pas afficher uniquement "erreur inconnue";
- differencier "aucune route trouvee" de "moteur indisponible".

## Phase 2 - Enrichissement local et alternatives

La Phase 2 ajoute l'intelligence locale: AbidjanMaps ne se contente plus de
demander une route a OSRM, il compare des alternatives selon les realites terrain.

### Use case 2: proposer plusieurs routes classees

```http
POST /api/v1/routes/proposals
Content-Type: application/json
```

Payload voiture:

```json
{
  "start": {
    "lat": 5.3329,
    "lng": -4.02003
  },
  "end": {
    "lat": 5.33892,
    "lng": -3.97754
  },
  "profile": "car"
}
```

Payload camion avec contraintes reelles:

```json
{
  "start": {
    "lat": 5.3329,
    "lng": -4.02003
  },
  "end": {
    "lat": 5.33892,
    "lng": -3.97754
  },
  "profile": "truck",
  "vehicle_width_m": 2.7,
  "vehicle_weight_t": 18
}
```

Reponse simplifiee:

```json
{
  "status": "ok",
  "proposals": [
    {
      "rank": 1,
      "score": 123.45,
      "route": {
        "geometry": {
          "type": "LineString",
          "coordinates": []
        },
        "distance_m": 8400,
        "duration_s": 1560
      },
      "price": {
        "amount": 2750,
        "currency": "XOF"
      },
      "score_breakdown": {
        "base": {
          "distance_component": 84,
          "duration_component": 26,
          "base_score": 110
        },
        "penalties": {
          "blocked": 0,
          "degraded": 12,
          "flood": 0,
          "control": 5,
          "unsafe_night": 0,
          "narrow_width": 8,
          "toll": 3,
          "seasonal": 0,
          "vehicle": 0
        },
        "vehicle_constraints": {
          "profile": "truck",
          "width_m": 2.7,
          "weight_t": 18,
          "forbidden": false,
          "overweight": false,
          "too_wide": false,
          "eligible": true
        },
        "total_score": 138
      },
      "enrichment": {
        "factors": {
          "blocked": false,
          "degraded": true,
          "flood_risk": false,
          "control_point": true,
          "unsafe_night": false,
          "narrow_width": true,
          "toll_present": true
        },
        "troncons": [],
        "reports": []
      }
    }
  ]
}
```

Regle d'affichage:

- `rank=1` est la meilleure route selon le backend;
- plus le `score` est faible, meilleure est la route;
- afficher les alternatives sur la carte avec des couleurs differentes;
- afficher les raisons du classement via `score_breakdown` et `enrichment`.

Use case frontend attendu:

- proposer une route recommandee;
- afficher 2 ou 3 alternatives si disponibles;
- afficher distance, duree, prix, score;
- afficher badges: route degradee, peage, point de controle, risque pluie,
  route etroite, non compatible camion;
- permettre a l'utilisateur de selectionner une alternative;
- pour camion, afficher les champs largeur et poids.

### Use case 3: detail enrichi par troncon

```http
POST /api/v1/routes/proposals/detail
```

Cet endpoint retourne le meme type de reponse que `/routes/proposals`, mais il
est destine a un affichage plus detaille.

Use case frontend:

- panneau "Pourquoi cette route?";
- liste des troncons detectes;
- liste des signalements associes;
- explication des penalites.

## Donnees locales: roads

Un `road` est un troncon local enrichi. Il peut representer une rue, un segment
de voie, un axe important, ou un troncon avec une contrainte terrain.

### Lister les roads

```http
GET /api/v1/roads
```

Public.

Chaque item retourne aussi:

```json
{
  "geometry": {
    "type": "LineString",
    "coordinates": [
      [-4.02, 5.33],
      [-3.99, 5.34]
    ]
  }
}
```

Le frontend peut donc dessiner les troncons locaux comme une couche cartographique.

### Lire une road

```http
GET /api/v1/roads/{road_id}
```

Public.

### Creer une road

```http
POST /api/v1/roads
Authorization: Bearer <token>
Content-Type: application/json
```

Payload:

```json
{
  "name": "Rue test Cocody",
  "geometry": {
    "type": "LineString",
    "coordinates": [
      [-4.02003, 5.3329],
      [-3.97754, 5.33892]
    ]
  },
  "surface_state": "degraded",
  "seasonal_practicability": "all_year",
  "surface_reel": "asphalt",
  "tonnage_max_reel_t": 12,
  "point_controle": "checkpoint",
  "temps_attente_p50_s": 120,
  "temps_attente_p90_s": 300,
  "eclairage": 3,
  "securite_nuit": 2,
  "width_usable_m": 2.5,
  "pente_max_pct": 5,
  "type_flux": "toll",
  "allowed_vehicle_profiles": ["car", "motorcycle"],
  "is_blocked": false,
  "extra_metadata": {}
}
```

Apres creation:

```text
validation_status = proposed
```

Cela signifie que la donnee est proposee mais ne devrait pas encore influencer
le scoring final tant qu'elle n'est pas validee.

### Modifier une road

```http
PATCH /api/v1/roads/{road_id}
Authorization: Bearer <token>
```

Payload partiel:

```json
{
  "surface_state": "bad",
  "note": "Signalement verifie sur place"
}
```

Une modification remet la donnee en:

```text
proposed
```

Use case frontend:

- formulaire d'edition;
- champ `note` pour expliquer la modification;
- avertir l'utilisateur qu'une modification devra etre revalidee.

### Valider ou rejeter une road

Admin seulement:

```http
POST /api/v1/roads/{road_id}/validate
POST /api/v1/roads/{road_id}/reject
```

Use case frontend:

- interface de moderation;
- boutons Valider/Rejeter visibles seulement pour `admin`;
- afficher l'historique avant decision.

### Historique road

```http
GET /api/v1/roads/{road_id}/history
```

Public actuellement.

Use case frontend:

- afficher qui a change quoi;
- afficher ancienne valeur / nouvelle valeur;
- afficher note et date.

## Donnees locales: places

Un `place` est un lieu local: quartier, repere, marche, entreprise, point connu,
etc.

### Lister les places

```http
GET /api/v1/places
```

Chaque item retourne aussi:

```json
{
  "location": {
    "lng": -4.0,
    "lat": 5.3
  }
}
```

### Rechercher une place

```http
GET /api/v1/places/search?q=plateau
```

Use case frontend Phase 1/2:

- champ de recherche depart/destination;
- autocompletion locale;
- recherche par nom, alias ou nom vernaculaire selon repository.

## Geocodage local: depart / destination

Endpoint recommande pour le frontend:

```http
GET /api/v1/geocoding/search?q=anador
```

Cet endpoint cherche dans les donnees locales importees/enrichies:

- `places`: lieux, POI, carrefours, gares, marches, points connus;
- `roads`: rues/routes nommees.

Exemple de reponse:

```json
[
  {
    "type": "place",
    "id": 2,
    "label": "Carrefour Anador",
    "category": "landmark",
    "location": {"lng": -4.0, "lat": 5.3},
    "source": "osm"
  },
  {
    "type": "road",
    "id": 9,
    "label": "Boulevard Latrille",
    "category": "road",
    "location": {"lng": -3.99, "lat": 5.34},
    "source": "osm"
  }
]
```

Use case frontend:

- utiliser cette route pour les champs depart et destination;
- afficher `label`;
- envoyer `location.lng` et `location.lat` a l'endpoint de calcul d'itineraire;
- afficher `type` pour distinguer une rue d'un lieu;
- garder `places/search` et `roads/search` comme endpoints specialises.

### Creer une place

```http
POST /api/v1/places
Authorization: Bearer <token>
```

Payload:

```json
{
  "name": "Gare de Bassam",
  "category": "transport",
  "location": {
    "lat": 5.3123,
    "lng": -3.9988
  },
  "aliases": ["gare bassam"],
  "vernacular_name": "Gare Bassam",
  "description": "Point de depart connu",
  "extra_metadata": {}
}
```

### Modifier / valider / rejeter une place

```http
PATCH /api/v1/places/{place_id}
POST /api/v1/places/{place_id}/validate
POST /api/v1/places/{place_id}/reject
GET /api/v1/places/{place_id}/history
```

Use case frontend:

- contribuer un nouveau lieu;
- moderer les lieux proposes;
- utiliser les lieux valides dans les champs depart/destination.

## Signalements: route_reports

Un `route_report` est un signalement terrain: route bloquee, route degradee,
inondation, peage, point de controle, risque de nuit, etc.

### Lister les signalements

```http
GET /api/v1/route-reports
GET /api/v1/route-reports?status=proposed
GET /api/v1/route-reports?status=validated
GET /api/v1/route-reports?status=rejected
```

Chaque signalement peut retourner:

```json
{
  "geometry": {
    "lng": -4.01,
    "lat": 5.31
  }
}
```

### Creer un signalement

```http
POST /api/v1/route-reports
Authorization: Bearer <token>
```

Payload:

```json
{
  "road_id": 12,
  "report_type": "blocked",
  "severity": 5,
  "message": "Route bloquee par travaux",
  "geometry": {
    "lat": 5.334,
    "lng": -4.021
  },
  "extra_metadata": {}
}
```

Regles:

- `severity` va de 1 a 5;
- `reported_by` vient du token, pas du JSON frontend;
- le signalement demarre en `proposed`;
- seuls les signalements valides influencent le scoring.

### Modifier / valider / rejeter un signalement

```http
PATCH /api/v1/route-reports/{report_id}
POST /api/v1/route-reports/{report_id}/validate
POST /api/v1/route-reports/{report_id}/reject
GET /api/v1/route-reports/{report_id}/history
```

Use case frontend:

- permettre a un utilisateur connecte de declarer un probleme;
- moderation admin des signalements;
- afficher les signalements proposes et valides avec des filtres;
- afficher une couleur selon `severity`.

## Taxonomies

Le frontend ne devrait pas hardcoder toutes les valeurs metier. Il peut charger
les taxonomies depuis le backend.

### Taxonomie roads

```http
GET /api/v1/roads/taxonomy
```

Contient:

```text
surface_state
seasonal_practicability
point_controle
type_flux
vehicle_profiles
```

### Taxonomie route reports

```http
GET /api/v1/route-reports/taxonomy
```

Contient:

```text
route_report_type
```

Valeurs importantes:

```text
blocked
degraded
flood
control_point
unsafe_night
toll
```

Use case frontend:

- remplir les listes deroulantes;
- afficher les labels traduits cote UI;
- envoyer les valeurs backend normalisees;
- garder une table de traduction frontend pour l'affichage humain.

## Administration utilisateurs

Admin seulement:

```http
POST /api/v1/users
GET /api/v1/users
```

Creation:

```json
{
  "email": "agent@example.com",
  "password": "motdepassefort123",
  "role": "user"
}
```

Use case frontend:

- page admin minimale pour creer un agent;
- page admin pour lister les comptes;
- ne pas exposer cette page aux utilisateurs non-admin.

## Ce qui devrait etre fait cote frontend pour Phase 1

Phase 1 frontend doit couvrir le parcours utilisateur minimum.

Use cases indispensables:

- voir une carte;
- choisir depart et destination;
- calculer une route simple;
- afficher la route en GeoJSON;
- afficher distance, duree, prix;
- gerer les erreurs;
- afficher l'etat health en environnement de test;
- permettre le choix du profil vehicule: voiture, moto, camion.

Ecrans minimum:

- ecran carte principale;
- panneau recherche depart/destination;
- panneau resultat route;
- composant d'erreur API;
- page ou panneau diagnostic staging.

Definition of Done Phase 1 frontend:

- un utilisateur peut obtenir une route visible sur la carte;
- le frontend consomme `/api/v1/route`;
- les coordonnees `[lng, lat]` sont bien interpretees;
- la route est lisible sur mobile et desktop;
- les erreurs principales sont affichees clairement.

## Ce qui devrait etre fait cote frontend pour Phase 2

Phase 2 frontend doit rendre visible la valeur metier locale.

Use cases utilisateur:

- demander plusieurs propositions de routes;
- comprendre pourquoi une route est recommandee;
- voir les alertes terrain sur une route;
- choisir un profil vehicule avance;
- declarer un probleme sur une route;
- proposer un lieu local.

Use cases admin/moderateur:

- se connecter;
- voir les roads proposees;
- voir les places proposees;
- voir les route_reports proposes;
- valider ou rejeter une donnee;
- consulter l'historique d'une donnee;
- creer un utilisateur agent.

Ecrans Phase 2 recommandes:

- carte avec alternatives;
- panneau de comparaison des routes;
- fiche detail route recommandee;
- formulaire de signalement;
- formulaire de proposition de lieu;
- interface moderation roads;
- interface moderation places;
- interface moderation route reports;
- page historique;
- page login;
- page utilisateurs admin.

Definition of Done Phase 2 frontend:

- le frontend consomme `/api/v1/routes/proposals`;
- le classement backend est respecte;
- les badges de risque sont visibles;
- les signalements peuvent etre proposes;
- les donnees peuvent etre moderees par admin;
- le token JWT est gere correctement;
- les erreurs API sont affichees avec le message backend;
- les taxonomies sont chargees depuis le backend.

## Recommandation UI

Pour la carte principale:

- utiliser une vraie carte interactive;
- afficher la route recommandee avec un style dominant;
- afficher les alternatives avec des styles plus discrets;
- afficher les points de signalement avec icones;
- afficher un panneau lateral ou bottom sheet mobile;
- eviter de surcharger la carte avec trop de texte;
- preferer des badges courts: `Peage`, `Controle`, `Inondable`, `Etroit`,
  `Nuit`, `Bloquee`.

Pour les scores:

- ne pas afficher uniquement un nombre brut;
- afficher "Recommandee", "Plus rapide", "Moins chere", "Risque pluie",
  "Non conseillee camion" selon les facteurs;
- garder le `score` pour debug/admin si besoin.

## Points encore sensibles

- En staging, OSRM doit avoir ses fichiers dans `OSRM_DATA_PATH`.
- Si OSRM est absent, `/route` et `/routes/proposals` ne seront pas fiables.
- Les donnees locales doivent etre validees pour influencer le scoring.
- Un user cree en local n'existe pas automatiquement dans la DB du VPS.
- Les endpoints admin doivent recevoir un token Bearer admin.
- Le frontend doit envoyer du JSON valide, surtout depuis les tests curl Windows.

## Ordre de travail conseille pour le frontend

1. Brancher health et configuration base URL.
2. Construire la carte et le rendu GeoJSON.
3. Brancher `/api/v1/route`.
4. Ajouter profils vehicule.
5. Brancher `/api/v1/routes/proposals`.
6. Ajouter affichage alternatives et badges.
7. Ajouter login JWT.
8. Ajouter signalements route_reports.
9. Ajouter moderation admin.
10. Ajouter places/search pour depart/destination.

## Contrat important avec le backend

Le frontend ne decide pas quelle route est la meilleure. Il affiche le classement
du backend.

Le backend est responsable de:

- calculer les routes;
- enrichir les alternatives;
- appliquer les penalites metier;
- classer les propositions;
- verifier les droits;
- historiser les modifications.

Le frontend est responsable de:

- rendre le parcours clair;
- afficher les raisons de decision;
- aider l'utilisateur a contribuer;
- aider l'admin a moderer;
- gerer proprement les erreurs API.

## Phase 3 V1 - Collecte GPS Map Core

La Phase 3 commence avec la collecte de trajets reels. Ce n'est pas encore une
course VTC complete: le but est d'enregistrer des traces GPS exploitables plus
tard pour enrichir le Map Core.

Tous les endpoints `map-traces` demandent:

```text
Authorization: Bearer <token>
```

### Demarrer un trajet

```http
POST /api/v1/map-traces/start
```

Payload:

```json
{
  "start": {
    "lng": -4.02,
    "lat": 5.33
  },
  "end": {
    "lng": -3.99,
    "lat": 5.34
  },
  "profile": "car",
  "planned_distance_m": 1450,
  "planned_duration_s": 360,
  "planned_route_geometry": {
    "type": "LineString",
    "coordinates": [
      [-4.02, 5.33],
      [-3.99, 5.34]
    ]
  }
}
```

### Envoyer des positions GPS

```http
POST /api/v1/map-traces/{trace_id}/positions
```

Payload:

```json
{
  "positions": [
    {
      "lng": -4.019,
      "lat": 5.331,
      "accuracy_m": 8,
      "speed_mps": 6.2,
      "recorded_at": "2026-07-27T10:01:00Z"
    }
  ]
}
```

### Terminer un trajet

```http
POST /api/v1/map-traces/{trace_id}/finish
```

Payload:

```json
{
  "finished_at": "2026-07-27T10:15:00Z"
}
```

Le backend retourne ensuite:

```json
{
  "status": "finished",
  "actual_distance_m": 1200.5,
  "actual_duration_s": 900
}
```

Use cases frontend Phase 3 V1:

- bouton "Demarrer collecte";
- envoi periodique de positions GPS;
- bouton "Terminer collecte";
- affichage statut du trajet;
- affichage distance reelle et duree reelle;
- page detail d'une trace;
- liste des traces collectees par l'utilisateur.

## Phase 3 V2 - Analyse des traces GPS

Une trace GPS est une suite de positions envoyees pendant un trajet. Le backend
doit ensuite transformer ces points bruts en informations utiles:

- qualite de la trace;
- distance reelle;
- duree reelle;
- vitesse moyenne;
- ecart avec la route OSRM prevue;
- detection de zones lentes;
- detection de detours;
- suggestions terrain a valider.

Le frontend doit se preparer a afficher:

- un score qualite;
- une comparaison `prevu / reel`;
- des badges `Trace bonne`, `Trace faible`, `A verifier`;
- une carte avec route prevue et trace reelle;
- les evenements detectes par le backend.

Endpoints probables a venir:

```text
POST /api/v1/map-traces/{trace_id}/analyze
GET  /api/v1/map-traces/{trace_id}/analysis
```

La regle produit importante:

```text
Une trace GPS ne modifie pas automatiquement le Map Core.
```

Elle sert d'abord a produire une observation. Plus tard, cette observation pourra
devenir une suggestion, puis une donnee validee par un admin.
