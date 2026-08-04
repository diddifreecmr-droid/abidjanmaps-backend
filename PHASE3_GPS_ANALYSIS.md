# AbidjanMaps - Phase 3 analyse des traces GPS

Ce document explique ce qu'est une trace GPS, pourquoi elle est importante pour
AbidjanMaps, et comment le backend doit progressivement l'exploiter.

## Idee simple

Une trace GPS est la suite des positions envoyees par le telephone pendant un
trajet reel.

Exemple:

```json
[
  {
    "lng": -4.02003,
    "lat": 5.3329,
    "accuracy_m": 8,
    "speed_mps": 4.2,
    "recorded_at": "2026-07-27T10:01:00Z"
  },
  {
    "lng": -4.0195,
    "lat": 5.3331,
    "accuracy_m": 7,
    "speed_mps": 5.1,
    "recorded_at": "2026-07-27T10:01:10Z"
  }
]
```

Chaque point dit:

- ou etait le vehicule;
- quand il etait la;
- avec quelle precision GPS;
- a quelle vitesse approximative il roulait.

Pris seul, un point ne raconte pas grand-chose. Pris ensemble, les points
forment une ligne: c'est la trace du trajet.

## Pourquoi c'est important

OSRM calcule une route avec OpenStreetMap. C'est tres utile, mais ce n'est pas
encore la realite terrain d'Abidjan.

Les traces GPS peuvent montrer:

- une route proposee par OSRM mais jamais prise par les chauffeurs;
- une route courte mais lente en vrai;
- une zone ou les vehicules ralentissent souvent;
- un detour recurrent;
- une route bloquee ou impraticable;
- une difference entre duree theorique OSRM et duree reelle;
- des vitesses moyennes par zone ou par troncon;
- des problemes saisonniers si les traces changent pendant la pluie.

Le but n'est pas de remplacer OSRM tout de suite. Le but est d'ajouter une
couche de realite locale au-dessus du calcul OSRM.

## Ce que le backend collecte deja

La Phase 3 V1 a deja prepare:

- `journeys`: stockage actuel de la trace globale Map Core;
- `journey_positions`: les points GPS de la trace;
- demarrage d'un trajet;
- ajout de positions par batch;
- fin d'un trajet;
- distance reelle simple;
- duree reelle simple;
- lecture d'une trace.

Endpoints actuels:

```text
POST /api/v1/map-traces/start
POST /api/v1/map-traces/{trace_id}/positions
POST /api/v1/map-traces/{trace_id}/finish
GET  /api/v1/map-traces/{trace_id}
GET  /api/v1/map-traces
```

## Ce que veut dire analyser une trace

Analyser une trace GPS, ce n'est pas juste stocker des points.

C'est transformer des points bruts en informations utiles:

- distance reelle parcourue;
- duree reelle du trajet;
- vitesse moyenne;
- nombre de points recus;
- qualite de la trace;
- trous dans la trace GPS;
- points GPS trop imprecis;
- ecart entre route OSRM et route reelle;
- zones lentes;
- detours;
- suggestions de signalement.

## Exemple concret

OSRM dit:

```text
distance prevue: 8.4 km
duree prevue: 26 min
```

Le trajet reel montre:

```text
distance reelle: 10.1 km
duree reelle: 48 min
```

Le backend peut conclure:

- l'utilisateur a fait un gros detour;
- la duree reelle est beaucoup plus longue;
- il faut verifier si la route OSRM est bloquee, lente ou impraticable;
- une suggestion de `route_report` peut etre creee, mais pas validee
  automatiquement.

## Qualite d'une trace

Toutes les traces GPS ne sont pas bonnes.

Une trace est probablement bonne si:

- elle a assez de points;
- les points sont dans le bon ordre;
- la precision GPS est acceptable;
- il n'y a pas de gros trous de temps;
- les vitesses ne sont pas absurdes;
- les points restent dans la zone attendue.

Une trace est probablement mauvaise si:

- elle a seulement 1 ou 2 points;
- elle saute de plusieurs kilometres en quelques secondes;
- la precision GPS est tres mauvaise;
- le telephone a coupe le GPS;
- les points sont envoyes trop rarement.

Donc avant d'utiliser une trace pour influencer le scoring, le backend doit
d'abord calculer un `quality_score`.

## Pipeline propose

Phase 3 V2 devrait ajouter une analyse simple et robuste.

Etapes:

1. Lire les positions d'une trace terminee.
2. Trier les positions par date.
3. Supprimer ou marquer les points suspects.
4. Calculer les statistiques de base.
5. Comparer le trajet reel au trajet OSRM prevu.
6. Produire un resume lisible.
7. Ne rien modifier automatiquement dans `roads` ou `route_reports`.

Phase 3 V3 pourra ensuite produire des suggestions terrain.

Etapes:

1. Detecter les ecarts importants.
2. Creer des suggestions internes.
3. Laisser un admin valider ou rejeter.
4. Transformer une suggestion validee en `route_report` ou enrichissement `road`.

## Donnees d'analyse a produire

Une premiere analyse peut retourner:

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

## Comment cela aide le scoring plus tard

Aujourd'hui le scoring utilise surtout:

- les routes locales `roads`;
- les signalements `route_reports`;
- les contraintes vehicule;
- les peages;
- les points de controle;
- les risques saisonniers.

Avec les traces GPS, on pourra ajouter:

- temps reel moyen par troncon;
- fiabilite d'un troncon;
- congestion frequente;
- detours frequents;
- ecarts entre OSRM et la realite;
- detection de routes evitees par les chauffeurs.

Important: au debut, les traces ne doivent pas changer directement le score.
Elles doivent produire des observations, puis des suggestions, puis passer par
la validation.

## Protection et vie privee

Une trace GPS est une donnee sensible.

Regles importantes:

- ne jamais envoyer `user_id` depuis le frontend;
- utiliser le token pour identifier l'utilisateur;
- limiter l'acces aux traces de l'utilisateur;
- eviter d'exposer les traces completes publiquement;
- prevoir plus tard une anonymisation pour les analyses globales;
- ne pas afficher les traces d'autres utilisateurs sans role admin.

## Etape backend implementee

Le backend dispose maintenant d'une premiere analyse simple:

```text
Analyser les traces Map Core terminees.
```

Disponible:

- `POST /api/v1/map-traces/{trace_id}/analyze`;
- `GET /api/v1/map-traces/{trace_id}/analysis`;
- calculer un resume;
- stocker le resultat;
- ajouter des tests automatises;
- ne pas encore modifier le Map Core automatiquement.

Ce rythme reste volontairement prudent. Il donne de la valeur sans casser le
systeme de scoring Phase 2, car une analyse GPS est une observation, pas encore
une verite metier validee.

## Insights Map Core

Lorsqu'une analyse detecte des evenements, le backend cree des
`map_trace_insights`.

Un insight est une observation a revoir:

```text
trace GPS
-> analyse
-> insight proposed
-> revue admin
-> validated ou rejected
```

Chaque insight peut aussi avoir une `duplicate_key`. Cette cle combine le type
d'observation et une zone approximative. Elle evite de creer plusieurs insights
actifs pour le meme probleme au meme endroit.

Le champ `evidence_count` compte les confirmations par traces differentes.
Si la meme trace ou la meme analyse repropose la meme observation, c'est un
doublon technique et il est ignore. Si une autre trace arrive avec la meme
`duplicate_key`, ce n'est plus seulement un doublon: c'est une confirmation
terrain, et le compteur augmente sur l'insight actif existant.

Exemples:

- `low_point_count`;
- `low_gps_quality`;
- `duration_much_longer_than_planned`;
- `slow_journey`;
- `possible_slow_segment`;
- `possible_blocked_road`;
- `possible_detour`;
- `gps_time_gap`;
- `suspicious_gps_jump`.

Un insight valide ne modifie pas encore automatiquement `roads` ou
`route_reports`. La conversion vers un enrichissement Map Core viendra plus tard,
avec une action explicite.

La conversion controlee cree un `route_report` en statut `proposed`, jamais en
`validated` directement. Cela garde deux decisions separees:

- valider que l'observation GPS merite attention;
- valider que l'information terrain doit influencer le Map Core.

## Calcul de la vitesse

La vitesse fiable pour l'analyse backend est calculee entre deux points:

```text
distance entre point A et point B / temps entre point A et point B
```

Exemple:

```text
distance = 50 metres
temps = 10 secondes
vitesse = 5 m/s = 18 km/h
```

Le backend utilise la formule Haversine pour estimer la distance entre deux
coordonnees GPS. Ensuite il convertit:

```text
km/h = m/s * 3.6
```

Pourquoi ne pas faire confiance uniquement au champ `speed_mps` du telephone?

- il peut etre absent;
- il peut varier selon le modele du telephone;
- il peut etre bruite si le signal GPS est mauvais;
- il n'explique pas toujours la distance reelle parcourue.

Donc l'analyse garde deux informations:

- `average_speed_kmh`: vitesse moyenne calculee par le backend;
- `phone_average_speed_kmh`: moyenne des vitesses envoyees par le telephone si
  elles existent.

L'analyse garde aussi des indicateurs de qualite:

- `moving_time_s`: temps estime en mouvement;
- `stopped_time_s`: temps estime a l'arret;
- `max_speed_kmh`: vitesse maximale credible;
- `gps_gap_count`: nombre de trous GPS importants;
- `suspicious_jump_count`: nombre de sauts GPS improbables filtres.

Les vitesses absurdes sont filtrees pour eviter qu'un saut GPS fausse l'analyse.
