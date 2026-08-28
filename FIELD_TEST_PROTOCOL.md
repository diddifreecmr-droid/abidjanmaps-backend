# DiddiMap / DiddiGo - Protocole de test terrain

Ce document decrit comment tester le Map Core avec une petite equipe terrain.
L'ordre est volontaire:

1. tester DiddiMap seul;
2. tester DiddiGo branche sur DiddiMap.

Objectif: valider que la carte, le routing, l'autocomplete et les traces GPS
produisent des donnees utiles avant de passer a une phase plus large.

## 1. Organisation generale

Equipe recommandee:

- 5 chauffeurs testeurs;
- 1 coordinateur terrain;
- 1 admin backend/map;
- 1 dev frontend;
- 1 dev backend/devops.

Duree recommandee:

- 2 semaines minimum;
- 4 semaines idealement pour observer plusieurs zones et plusieurs horaires.

Zones a couvrir:

- Plateau;
- Cocody;
- Yopougon;
- Abobo;
- Marcory;
- Treichville;
- Koumassi;
- Bingerville;
- Aeroport.

Horaires a couvrir:

- matin: 06h30 - 09h30;
- midi: 11h30 - 14h00;
- soir: 17h00 - 20h00;
- nuit si possible: apres 21h00.

## 2. Pre-requis techniques

Avant test terrain:

- backend staging deploye;
- OSRM staging disponible;
- PostGIS staging disponible;
- migrations Alembic appliquees;
- base OSM importee;
- compte admin staging fonctionnel;
- frontend branche sur le backend staging;
- validation Docker OK;
- telephones avec GPS actif;
- reseau mobile disponible.

Commande de validation Docker avant lancement:

```bash
python -m scripts.validate_staging
```

Depuis Docker Compose local:

```cmd
docker compose --profile validation run --rm map-validation
```

Si on teste aussi les traces GPS:

```cmd
set "VALIDATE_STAGING_MODE=full"
set "PHASE3_TEST_EMAIL=admin@example.com"
set "PHASE3_TEST_PASSWORD=votre-mot-de-passe"
docker compose --profile validation run --rm map-validation
```

## 3. Phase A - Test DiddiMap seul

Cette phase teste la carte sans DiddiGo. Le but est de valider le moteur Map
Core lui-meme.

### A.1 Autocomplete

Action chauffeur/testeur:

- ouvrir l'interface carte;
- chercher des lieux connus;
- selectionner une suggestion;
- verifier que le point affiche correspond au lieu attendu.

Requetes backend concernees:

```http
GET /api/v1/geocoding/autocomplete?q=plateau&limit=8&bias_lat=5.33&bias_lng=-4.02
```

Donnees a noter:

- texte recherche;
- resultat trouve ou non;
- resultat correct ou incorrect;
- position approximative correcte ou non;
- temps de reponse ressenti.

Exemples de recherches:

- Plateau;
- Siporex;
- Carrefour Anador;
- CHU Cocody;
- Aeroport;
- Treichville;
- Marcory;
- Bingerville;
- Abobo;
- Riviera.

Resultat attendu:

- suggestions visibles en moins de 1 seconde;
- resultats proches remontes en premier si la position utilisateur est connue;
- aucun crash frontend;
- aucun `500` backend.

### A.2 Calcul de route simple

Action chauffeur/testeur:

- choisir un depart;
- choisir une destination;
- demander l'itineraire;
- verifier que la route affichee semble logique.

Requete backend concernee:

```http
POST /api/v1/route
```

Payload type:

```json
{
  "start": {
    "lat": 5.3367,
    "lng": -4.084
  },
  "end": {
    "lat": 5.3204,
    "lng": -4.016
  },
  "profile": "car"
}
```

Donnees a noter:

- depart;
- destination;
- distance retournee;
- duree retournee;
- route logique ou non;
- route impossible ou non.

Resultat attendu:

- une route est retournee;
- la distance semble plausible;
- la duree semble plausible;
- la geometrie s'affiche correctement sur la carte.

### A.3 Alternatives et scoring

Action chauffeur/testeur:

- calculer un trajet;
- afficher les alternatives;
- comparer la meilleure proposition avec la connaissance terrain.

Requete backend concernee:

```http
POST /api/v1/routes/proposals/detail
```

Donnees a noter:

- nombre d'alternatives;
- meilleure route proposee;
- route preferee par le chauffeur;
- raison si le chauffeur prefere une autre route;
- presence de peage, route degradee, embouteillage, zone lente.

Resultat attendu:

- `rank=1` correspond souvent a une route acceptable;
- les alternatives sont lisibles;
- le `score_breakdown` explique les malus;
- les enrichissements locaux apparaissent quand ils existent.

### A.4 Creation de signalements terrain

Action admin/testeur:

- creer un signalement `route_report`;
- le laisser en `proposed`;
- le valider avec un admin;
- recalculer une route qui passe dans la zone.

Endpoints concernes:

```http
POST /api/v1/route-reports
POST /api/v1/route-reports/{report_id}/validate
POST /api/v1/routes/proposals/detail
```

Types de signalements a tester:

- route degradee;
- route bloquee;
- zone inondable;
- point de controle;
- peage;
- route peu sure la nuit.

Resultat attendu:

- un report `proposed` n'influence pas encore le scoring;
- un report `validated` influence le scoring;
- l'historique garde les changements.

## 4. Phase B - Test traces GPS DiddiMap

Cette phase teste la collecte GPS directement dans DiddiMap.

### B.1 Demarrer une trace

Endpoint:

```http
POST /api/v1/map-traces/start
```

Donnees minimales:

```json
{
  "start": {
    "lat": 5.3367,
    "lng": -4.084
  },
  "end": {
    "lat": 5.3204,
    "lng": -4.016
  },
  "profile": "car",
  "planned_distance_m": 12300,
  "planned_duration_s": 1800,
  "planned_route_geometry": {
    "type": "LineString",
    "coordinates": [
      [-4.084, 5.3367],
      [-4.016, 5.3204]
    ]
  }
}
```

### B.2 Envoyer les positions GPS

Endpoint:

```http
POST /api/v1/map-traces/{trace_id}/positions
```

Frequence recommandee:

- toutes les 3 a 5 secondes si possible;
- sinon toutes les 10 secondes maximum.

Payload:

```json
{
  "positions": [
    {
      "lat": 5.3367,
      "lng": -4.084,
      "accuracy_m": 8,
      "speed_mps": 4.2,
      "recorded_at": "2026-08-25T10:00:00Z"
    }
  ]
}
```

### B.3 Terminer et analyser

Endpoints:

```http
POST /api/v1/map-traces/{trace_id}/finish
POST /api/v1/map-traces/{trace_id}/analyze
```

Resultat attendu:

- distance reelle calculee;
- duree reelle calculee;
- vitesse moyenne calculee;
- qualite de trace calculee;
- insight cree si un probleme probable est detecte.

### B.4 Revue admin des insights

Endpoints:

```http
GET  /api/v1/map-trace-insights/review-queue
GET  /api/v1/map-trace-insights/{insight_id}/detail
POST /api/v1/map-trace-insights/{insight_id}/validate
POST /api/v1/map-trace-insights/{insight_id}/reject
POST /api/v1/map-trace-insights/{insight_id}/convert-to-route-report
```

Regle:

```text
Une trace GPS ne modifie pas directement la carte.
```

Pipeline:

```text
trace GPS
-> analyse
-> insight proposed
-> validation admin
-> route_report proposed
-> validation route_report
-> scoring impacte
```

## 5. Phase C - Test DiddiGo branche sur DiddiMap

Cette phase commence apres validation de DiddiMap seul.

### C.1 Ce que DiddiGo doit utiliser

DiddiGo doit utiliser DiddiMap pour:

- autocomplete depart/destination;
- calcul route;
- alternatives;
- distance/duree pour estimation;
- envoi de trace GPS apres course.

Endpoints DiddiMap consommes:

```http
GET  /api/v1/geocoding/autocomplete
POST /api/v1/routes/proposals/detail
POST /api/v1/map-traces/start
POST /api/v1/map-traces/{trace_id}/positions
POST /api/v1/map-traces/{trace_id}/finish
POST /api/v1/map-traces/{trace_id}/analyze
```

### C.2 Donnees que DiddiGo doit envoyer

DiddiGo doit envoyer les faits, pas les conclusions.

Faits attendus:

- id externe de la course;
- profil vehicule;
- depart;
- destination;
- distance prevue;
- duree prevue;
- geometrie prevue;
- positions GPS;
- timestamp de chaque position;
- precision GPS si disponible;
- vitesse telephone si disponible.

DiddiMap decide ensuite s'il y a:

- segment lent;
- detour;
- route possiblement bloquee;
- mauvaise qualite GPS;
- signal a revoir.

### C.3 Frequence GPS recommandee DiddiGo

Pendant une course:

- envoyer une position toutes les 3 a 5 secondes cote DiddiGo;
- stocker localement si le reseau coupe;
- renvoyer par batch quand le reseau revient;
- ne pas envoyer de positions sans timestamp.

Pour DiddiMap, un batch est acceptable:

```text
plusieurs positions en une seule requete
```

### C.4 Donnees sensibles

Pour le test MVP:

- ne pas envoyer le nom du client;
- ne pas envoyer le numero de telephone du client;
- ne pas envoyer le prix final si inutile a la map;
- utiliser un `external_trip_id` technique.

DiddiMap n'a besoin que des donnees utiles a la carte.

## 6. Grille de resultats attendus

Sur 2 a 4 semaines, objectif minimum:

- 5 chauffeurs actifs;
- 20 recherches autocomplete par chauffeur;
- 10 calculs de route par chauffeur;
- 5 trajets GPS termines par chauffeur;
- 25 traces GPS minimum;
- 15 traces GPS exploitables;
- 5 insights utiles minimum;
- 2 route_reports valides minimum.

Seuils de succes:

- 95% des appels health OK;
- 90% des recherches courantes trouvent un resultat exploitable;
- 90% des calculs route retournent une route;
- 80% des traces GPS sont analysables;
- aucun crash backend non explique;
- aucun enrichissement automatique sans validation humaine.

## 7. Rapport quotidien

Chaque jour, noter:

- nombre de recherches;
- nombre de routes calculees;
- nombre de traces terminees;
- nombre d'erreurs;
- lieux introuvables;
- routes jugees mauvaises par les chauffeurs;
- insights crees;
- insights valides;
- route_reports crees;
- route_reports valides.

Format simple:

```text
Date:
Chauffeurs actifs:
Traces terminees:
Problemes observes:
Lieux introuvables:
Routes incorrectes:
Insights a revoir:
Actions admin:
Decision pour demain:
```

## 8. Decision fin de test

A la fin du test, classer les resultats:

- OK pour continuer vers DiddiGo pilote;
- OK mais besoin de plus de donnees Map Core;
- probleme routing OSRM;
- probleme geocoding/autocomplete;
- probleme qualite GPS;
- probleme UX frontend;
- probleme admin/moderation.

La sortie attendue n'est pas seulement du code qui marche. La sortie attendue
est une liste claire de corrections et d'ameliorations prioritaires.
