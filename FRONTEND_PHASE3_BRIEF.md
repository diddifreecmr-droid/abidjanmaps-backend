# AbidjanMaps - Brief frontend Phase 3 Map Core

Ce document est destine au developpeur frontend. Il explique ce qui est attendu
cote interface utilisateur pour la Phase 3: collecte GPS, visualisation de
traces, analyse simple et preparation des enrichissements terrain.

## Objectif Phase 3

La Phase 3 sert a passer de:

```text
routes calculees + donnees locales saisies manuellement
```

a:

```text
routes calculees + traces GPS reelles + analyse terrain
```

Le frontend doit donc permettre a un utilisateur connecte de collecter un vrai
trajet et de revoir ce qui a ete collecte.

## Ce qu'est une trace GPS

Une trace GPS est une liste de positions envoyees pendant un trajet.

Chaque position contient:

- `lat`: latitude;
- `lng`: longitude;
- `accuracy_m`: precision estimee du GPS en metres;
- `speed_mps`: vitesse en metres par seconde;
- `recorded_at`: date exacte mesuree par le telephone.

Le frontend ne doit pas envoyer une seule position finale. Il doit envoyer
plusieurs positions pendant le trajet, par exemple toutes les 5 a 15 secondes
selon le mode choisi.

## Base API

Local:

```text
http://127.0.0.1:8000/api/v1
```

Staging:

```text
http://abidjanmaps-backend-staging.diddifree.com/api/v1
```

Tous les endpoints Phase 3 demandent:

```text
Authorization: Bearer <access_token>
```

Le frontend ne doit jamais envoyer `user_id`. Le backend l'obtient depuis le
token JWT.

## Endpoints disponibles Phase 3 V1

```text
POST /map-traces/start
POST /map-traces/{trace_id}/positions
POST /map-traces/{trace_id}/finish
GET  /map-traces/{trace_id}
GET  /map-traces
```

## Profils de transport

Profils acceptes aujourd'hui par l'API:

```text
car
motorcycle
truck
```

Ces profils servent au backend pour adapter les contraintes, le scoring et les
lectures metier. Le moteur OSRM actuellement connecte reste `driving`. Donc le
frontend ne doit pas encore proposer officiellement un mode `walking` ou
`pedestrian`.

Le profil pieton est garde comme sujet futur. Il demandera un moteur OSRM
prepare pour la marche, pas seulement une nouvelle valeur dans un select.

## Use case 1: demarrer une collecte GPS

L'utilisateur choisit un depart, une destination et un profil vehicule.

Avant de demarrer, le frontend peut appeler:

```text
POST /routes/proposals
```

ou:

```text
POST /route
```

pour obtenir une route prevue, distance, duree et GeoJSON.

Ensuite il demarre la trace Map Core:

```http
POST /api/v1/map-traces/start
Authorization: Bearer <token>
Content-Type: application/json
```

Payload:

```json
{
  "start": {
    "lng": -4.02003,
    "lat": 5.3329
  },
  "end": {
    "lng": -3.97754,
    "lat": 5.33892
  },
  "profile": "car",
  "planned_distance_m": 8400,
  "planned_duration_s": 1560,
  "planned_route_geometry": {
    "type": "LineString",
    "coordinates": [
      [-4.02003, 5.3329],
      [-3.97754, 5.33892]
    ]
  }
}
```

Reponse:

```json
{
  "id": 12,
  "user_id": 3,
  "status": "started",
  "profile": "car",
  "start": {
    "lng": -4.02003,
    "lat": 5.3329
  },
  "end": {
    "lng": -3.97754,
    "lat": 5.33892
  },
  "planned_distance_m": 8400,
  "planned_duration_s": 1560,
  "planned_route_geometry": {
    "type": "LineString",
    "coordinates": [
      [-4.02003, 5.3329],
      [-3.97754, 5.33892]
    ]
  },
  "actual_distance_m": null,
  "actual_duration_s": null,
  "started_at": "2026-07-27T10:00:00Z",
  "finished_at": null,
  "created_at": "2026-07-27T10:00:00Z",
  "updated_at": "2026-07-27T10:00:00Z"
}
```

UX attendue:

- afficher un bouton `Demarrer la collecte`;
- demander la permission GPS avant l'appel ou juste apres;
- afficher un etat `Collecte en cours`;
- garder l'identifiant de trace en memoire locale tant que la collecte est active;
- empecher de demarrer deux collectes en meme temps dans la meme session.

## Use case 2: envoyer les positions GPS

Pendant le trajet, le frontend envoie des batches de positions.

```http
POST /api/v1/map-traces/12/positions
Authorization: Bearer <token>
Content-Type: application/json
```

Payload:

```json
{
  "positions": [
    {
      "lng": -4.0199,
      "lat": 5.333,
      "accuracy_m": 8,
      "speed_mps": 4.2,
      "recorded_at": "2026-07-27T10:01:00Z"
    },
    {
      "lng": -4.0194,
      "lat": 5.3333,
      "accuracy_m": 7,
      "speed_mps": 5.1,
      "recorded_at": "2026-07-27T10:01:10Z"
    }
  ]
}
```

Reponse:

```json
[
  {
    "id": 101,
    "trace_id": 12,
    "location": {
      "lng": -4.0199,
      "lat": 5.333
    },
    "accuracy_m": 8,
    "speed_mps": 4.2,
    "recorded_at": "2026-07-27T10:01:00Z",
    "created_at": "2026-07-27T10:01:02Z"
  }
]
```

Regles frontend recommandees:

- envoyer les positions par batch, pas une requete par point;
- batcher toutes les 10 a 30 secondes;
- limiter un batch a 500 points maximum;
- garder une file locale si le reseau coupe;
- reessayer l'envoi quand le reseau revient;
- ne pas envoyer de points si la permission GPS est refusee;
- afficher une erreur claire si le backend repond `401`, `404` ou `409`.

Codes utiles:

```text
401: utilisateur non connecte ou token invalide
404: trace introuvable ou n'appartient pas a l'utilisateur
409: trace terminee ou plus ouverte a la collecte
422: payload invalide
```

## Use case 3: terminer une collecte

Quand l'utilisateur arrive, il termine la trace.

```http
POST /api/v1/map-traces/12/finish
Authorization: Bearer <token>
Content-Type: application/json
```

Payload:

```json
{
  "finished_at": "2026-07-27T10:30:00Z"
}
```

Le payload peut aussi etre vide:

```json
{}
```

Dans ce cas, le backend utilise son heure serveur.

Reponse:

```json
{
  "id": 12,
  "user_id": 3,
  "status": "finished",
  "profile": "car",
  "start": {
    "lng": -4.02003,
    "lat": 5.3329
  },
  "end": {
    "lng": -3.97754,
    "lat": 5.33892
  },
  "planned_distance_m": 8400,
  "planned_duration_s": 1560,
  "planned_route_geometry": {
    "type": "LineString",
    "coordinates": []
  },
  "actual_distance_m": 10120.4,
  "actual_duration_s": 1800,
  "started_at": "2026-07-27T10:00:00Z",
  "finished_at": "2026-07-27T10:30:00Z",
  "created_at": "2026-07-27T10:00:00Z",
  "updated_at": "2026-07-27T10:30:00Z"
}
```

UX attendue:

- bouton `Terminer`;
- confirmation avant fermeture du trajet;
- affichage distance reelle;
- affichage duree reelle;
- comparaison avec distance/duree prevues;
- message si la collecte contient peu de points.

## Use case 4: afficher le detail d'un trajet

```http
GET /api/v1/map-traces/12
Authorization: Bearer <token>
```

Reponse:

```json
{
  "id": 12,
  "status": "finished",
  "profile": "car",
  "start": {
    "lng": -4.02003,
    "lat": 5.3329
  },
  "end": {
    "lng": -3.97754,
    "lat": 5.33892
  },
  "planned_distance_m": 8400,
  "planned_duration_s": 1560,
  "actual_distance_m": 10120.4,
  "actual_duration_s": 1800,
  "positions": [
    {
      "id": 101,
      "trace_id": 12,
      "location": {
        "lng": -4.0199,
        "lat": 5.333
      },
      "accuracy_m": 8,
      "speed_mps": 4.2,
      "recorded_at": "2026-07-27T10:01:00Z",
      "created_at": "2026-07-27T10:01:02Z"
    }
  ]
}
```

Affichage carte:

- route prevue: utiliser `planned_route_geometry`;
- trace reelle: convertir `positions` en LineString;
- depart et destination: marqueurs;
- afficher les points GPS en debug seulement;
- sur mobile, eviter d'afficher tous les points si la trace est longue.

Important GeoJSON:

```text
GeoJSON = [lng, lat]
Formulaires = lat/lng ou lng/lat selon composant
```

Ici les `positions` reviennent sous forme:

```json
{
  "location": {
    "lng": -4.0199,
    "lat": 5.333
  }
}
```

Pour dessiner une LineString:

```json
{
  "type": "LineString",
  "coordinates": [
    [-4.0199, 5.333],
    [-4.0194, 5.3333]
  ]
}
```

## Use case 5: lister mes trajets

```http
GET /api/v1/map-traces
Authorization: Bearer <token>
```

Use case frontend:

- page `Mes collectes`;
- statut `started` ou `finished`;
- date de debut;
- duree;
- distance;
- profil vehicule;
- lien vers le detail.

## Ecrans Phase 3 V1

Ecrans minimum:

- page carte avec bouton de collecte;
- panneau de permission GPS;
- panneau collecte en cours;
- panneau fin de collecte;
- page liste des collectes;
- page detail d'une collecte.

Ecrans utiles pour admin plus tard:

- liste des traces collectees;
- carte des traces anonymisees;
- tableau qualite des traces;
- suggestions terrain a valider.

## Etat frontend pendant une collecte

Le frontend devrait gerer explicitement:

```text
idle
requesting_permission
starting
recording
syncing
finishing
finished
failed
```

Cela evite les bugs ou l'utilisateur clique plusieurs fois.

## Recommandation GPS mobile/web

Si le frontend est web:

- utiliser `navigator.geolocation.watchPosition`;
- activer `enableHighAccuracy` pour les tests terrain;
- choisir un intervalle raisonnable cote logique applicative;
- surveiller la batterie;
- prevoir le cas ou le navigateur bloque le GPS en arriere-plan.

Si le frontend devient mobile natif:

- utiliser une librairie GPS fiable;
- prevoir l'envoi en arriere-plan;
- prevoir une file locale hors-ligne;
- demander les permissions proprement.

## Analyse GPS Phase 3 V2

Le backend peut analyser une trace terminee pour produire un resume.

Endpoints:

```text
POST /api/v1/map-traces/{trace_id}/analyze
GET  /api/v1/map-traces/{trace_id}/analysis
```

Format:

```json
{
  "trace_id": 12,
  "status": "analyzed",
  "points_count": 74,
  "usable_points_count": 69,
  "quality_score": 0.88,
  "quality_label": "good",
  "actual_distance_m": 10120.4,
  "actual_duration_s": 2880,
  "average_speed_kmh": 12.65,
  "phone_average_speed_kmh": 13.2,
  "moving_time_s": 2500,
  "stopped_time_s": 380,
  "max_speed_kmh": 41.7,
  "gps_gap_count": 0,
  "suspicious_jump_count": 0,
  "planned_distance_m": 8400,
  "planned_duration_s": 1560,
  "distance_delta_m": 1720.4,
  "duration_delta_s": 1320,
  "duration_ratio": 1.85,
  "detected_events": [
    {
      "type": "slow_zone",
      "severity": 3,
      "message": "Vitesse faible detectee sur une partie du trajet"
    }
  ],
  "recommendation": "review_needed"
}
```

La vitesse principale `average_speed_kmh` est calculee par le backend avec:

```text
distance entre les points GPS / temps entre les points GPS
```

Le champ `phone_average_speed_kmh` vient des valeurs `speed_mps` envoyees par le
telephone. Il est utile pour comparer, mais ce n'est pas la reference principale.

Nouveaux champs de qualite terrain:

- `moving_time_s`: temps estime en mouvement;
- `stopped_time_s`: temps estime a l'arret;
- `max_speed_kmh`: vitesse maximale credible calculee par le backend;
- `gps_gap_count`: nombre de gros trous temporels entre deux points GPS;
- `suspicious_jump_count`: nombre de sauts GPS impossibles filtres par le backend.

Use case frontend V2:

- bouton admin ou debug `Analyser cette trace`;
- affichage score qualite;
- affichage ecart OSRM/reel;
- affichage des evenements detectes;
- badge `A verifier` si l'analyse recommande une revue humaine.

## Revue admin des insights Map Core

Quand l'analyse detecte des evenements, le backend cree des insights `proposed`.
Ce sont des observations a revoir, pas encore des signalements routiers valides.

Endpoints admin:

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

Filtres disponibles:

```text
status=proposed|validated|rejected
insight_type=duration_much_longer_than_planned
insight_type=possible_slow_segment
insight_type=possible_blocked_road
insight_type=possible_detour
severity_min=3
trace_id=12
sort=priority|severity|evidence|confidence|newest
order=desc|asc
```

Exemple:

```json
{
  "id": 7,
  "trace_id": 12,
  "analysis_id": 4,
  "insight_type": "duration_much_longer_than_planned",
  "severity": 4,
  "confidence_score": 0.76,
  "message": "Le trajet reel est nettement plus long que la duree OSRM prevue.",
  "duplicate_key": "duration_much_longer_than_planned:-4.018:5.334",
  "evidence_count": 1,
  "latest_evidence_trace_id": 12,
  "status": "proposed"
}
```

File de revue admin:

```text
GET /api/v1/map-trace-insights/review-queue
```

Cette route renvoie les insights `proposed` les plus importants en premier. Le
backend calcule `review_priority_score` avec la gravite, le nombre de traces qui
confirment, la confiance et le statut.

Exemple:

```json
{
  "id": 12,
  "trace_id": 44,
  "insight_type": "possible_blocked_road",
  "severity": 5,
  "confidence_score": 0.78,
  "evidence_count": 3,
  "review_priority_score": 0.834,
  "recommended_action": "review_priority",
  "conversion_ready": false,
  "status": "proposed"
}
```

Candidats a convertir:

```text
GET /api/v1/map-trace-insights/route-report-candidates
```

Cette route renvoie seulement les insights deja `validated`, convertibles et
assez solides. Par defaut:

```text
min_evidence_count=2
min_confidence_score=0.6
min_severity=3
```

Le frontend peut afficher un bouton "Creer un signalement routier" pour ces
lignes. Le clic appelle ensuite:

```text
POST /api/v1/map-trace-insights/{insight_id}/convert-to-route-report
```

Use case admin:

- voir les insights proposes;
- traiter d'abord `/review-queue`;
- afficher la trace et l'analyse associees;
- utiliser `/detail` pour charger l'insight, la trace et l'analyse en une seule requete;
- valider si l'observation semble utile;
- rejeter si la trace est mauvaise ou non pertinente;
- ne pas modifier automatiquement le Map Core depuis cette action.
- voir les insights valides qui sont prets dans `/route-report-candidates`;
- convertir un insight valide en `route_report proposed` si l'observation doit
  entrer dans le workflow Map Core.

Types d'insights metier utiles:

- `duration_much_longer_than_planned`: la duree reelle depasse fortement OSRM;
- `slow_journey`: toute la trace semble lente;
- `possible_slow_segment`: une partie du trajet semble lente;
- `possible_blocked_road`: la trace suggere une route bloquee ou tres difficile;
- `possible_detour`: la trace reelle est beaucoup plus longue que la route prevue;
- `gps_time_gap`: il y a un trou temporel dans la collecte GPS;
- `suspicious_gps_jump`: le backend a filtre un saut GPS improbable.

Le champ `duplicate_key` sert au backend a eviter de proposer plusieurs fois le
meme probleme au meme endroit. Le frontend peut l'afficher en debug admin, mais
ne doit pas le modifier.

Le champ `evidence_count` indique combien de traces differentes ont confirme le
meme probleme dans la meme zone. Ce n'est pas un compteur de clics: si la meme
trace est analysee deux fois, cela reste un doublon technique et le compteur ne
doit pas augmenter. Si une autre trace confirme le meme probleme, le backend
augmente `evidence_count` sur l'insight actif existant.

La conversion ne valide pas le `route_report`. Elle cree seulement une
proposition:

```text
insight validated
-> route_report proposed
-> validation route_report separee
-> impact scoring seulement apres validation du route_report
```

## Comment cela prepare Waze local

La Phase 3 ne doit pas faire confiance aveuglement a une seule trace.

Bon fonctionnement attendu:

1. Les utilisateurs collectent des trajets.
2. Le backend analyse les traces.
3. Le backend detecte des tendances.
4. Le backend propose des enrichissements.
5. Un admin valide.
6. Les donnees validees influencent le scoring.

Donc le frontend doit aider a collecter proprement et a expliquer les resultats,
pas seulement envoyer des points GPS en silence.

## Points de vigilance frontend

- Ne pas lancer la collecte sans consentement utilisateur.
- Ne pas envoyer `user_id`.
- Ne pas afficher les traces d'autres utilisateurs.
- Ne pas inverser `lat` et `lng`.
- Ne pas supposer que la collecte marche en arriere-plan sur web.
- Ne pas perdre les positions si le reseau coupe.
- Ne pas appeler `/finish` avant d'avoir envoye les derniers points.
- Ne pas faire confiance au GPS si `accuracy_m` est enorme.

## Definition of Done frontend Phase 3 V1

- l'utilisateur peut se connecter;
- il peut demarrer une collecte;
- le navigateur ou mobile demande la permission GPS;
- le frontend envoie des positions par batch;
- une coupure reseau courte ne fait pas perdre toute la trace;
- l'utilisateur peut terminer le trajet;
- le detail du trajet affiche route prevue et trace reelle;
- la liste des collectes fonctionne;
- les erreurs `401`, `404`, `409`, `422` sont affichees clairement.

## Definition of Done frontend Phase 3 V2

- l'utilisateur ou l'admin peut lancer une analyse de trace;
- l'analyse affiche qualite, distance, duree, ecarts et evenements;
- les traces de mauvaise qualite sont visibles comme telles;
- les suggestions terrain restent separees de la validation admin.
