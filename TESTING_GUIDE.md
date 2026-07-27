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
docker compose exec backend python -m scripts.seed_phase2
docker compose exec backend python -m scripts.check_phase2_scenarios
```

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

## 6. Tests minimum pour fermer Phase 2

Avant de declarer la Phase 2 fermee:

- `pytest` passe en local;
- `seed_phase2` passe en Docker local;
- `check_phase2_scenarios` passe en Docker local;
- `seed_phase2` passe en staging;
- `check_phase2_scenarios` passe en staging;
- `/api/v1/health` repond depuis le domaine staging;
- `/api/v1/routes/proposals/detail` repond depuis le domaine staging;
- `/api/v1/roads` retourne des geometries;
- `/api/v1/places` retourne des locations;
- `/api/v1/route-reports` retourne des geometries quand disponibles.
