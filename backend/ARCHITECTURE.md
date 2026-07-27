# Architecture modulaire

Le backend est un monolithe modulaire : une seule application FastAPI et une seule base
PostgreSQL, mais le code est organise par responsabilite metier.

```text
app/
  modules/
    routing/       Calcul, OSRM, prix, alternatives et scoring.
    map_data/      Routes, lieux, alias et catalogue geographique.
    local_enrichment/  Signalements, validation et publication terrain.
    users/         Comptes, authentification et autorisations.
    journeys/      Collecte de traces GPS Map Core, pas de courses DiddiGo.
  shared/          Composants techniques communs, volontairement limites.
```

Chaque module contient ses couches `domain`, `application`, `infrastructure` et
`presentation` quand elles sont necessaires. Un module ne doit pas acceder directement
aux details internes d'un autre module : il passe par un port ou un DTO explicite.

La persistance suit la meme regle:

- `map_data` possede les modeles ORM et mappers de roads, places et historiques;
- `local_enrichment` possede les modeles ORM de route_reports et de leur historique;
- `users` possede le modele ORM et le repository des comptes;
- `journeys` possede les modeles ORM des traces GPS Map Core et positions GPS;
- `shared` possede uniquement la classe Base et la session SQLAlchemy;
- Alembic importe les modeles des modules pour construire une metadata unique.

Les anciens chemins horizontaux `app/domain`, `app/application`, `app/infrastructure` et
`app/presentation` ont ete supprimes. Le nouveau code metier doit etre ajoute dans
`app/modules/<metier>/`. La configuration, la session base de donnees, le logging et les
health checks communs vivent dans `app/shared/`. `app/bootstrap/` assemble les modules
sans contenir de regle metier.

Cette organisation garde la simplicite d'un monolithe aujourd'hui et prepare une future
separation en services sans imposer maintenant les couts des microservices.

## Authentification et autorisations

Le module `users` est vertical et autonome. Le domaine definit l'utilisateur et ses
roles, l'application orchestre creation et authentification, l'infrastructure fournit
SQLAlchemy, Argon2 et JWT, puis la presentation expose les endpoints HTTP.

Les lectures, les taxonomies et le calcul d'itineraire restent publics. Creer ou
modifier une route, un lieu ou un signalement exige un jeton Bearer valide. Les actions
`validate` et `reject`, ainsi que la gestion des comptes, exigent le role `admin`.

L'auteur d'une proposition, d'une modification ou d'une revue vient toujours du compte
authentifie. Un client ne peut donc pas falsifier `reported_by`, `changed_by` ou
`reviewed_by` dans son JSON.

Les mots de passe ne sont jamais stockes en clair: `pwdlib` utilise Argon2. Les jetons
sont signes avec `AUTH_SECRET_KEY` et expirent apres `AUTH_TOKEN_EXPIRE_MINUTES`.
La cle de developpement doit etre remplacee par un secret aleatoire avant tout
deploiement.

## Publication des enrichissements

Toute nouvelle route, tout nouveau lieu et tout nouveau signalement public est cree avec
le statut `proposed`. Une action administrative le fait ensuite passer a `validated` ou
`rejected`. Le module `routing` ne lit que les routes et signalements `validated` pour
construire le score d'un itineraire.

Le cas d'usage `RouteReportWorkflow` orchestre cette transition sans mettre la regle
metier dans le controleur FastAPI. Les repositories enregistrent les changements dans
les tables d'historique, avec l'auteur de la revue et une note optionnelle.

Les modifications passent par les cas d'usage `UpdateRoad`, `UpdatePlace` et
`RouteReportWorkflow.update`. Un objet deja valide qui est modifie repasse
automatiquement a `proposed`: son ancienne validation ne couvre pas la nouvelle valeur.
Pour les lieux, `verified` est donc remis a `false` jusqu'a la prochaine validation.

## Profils vehicule

La primitive partagee `VehicleContext` contient le profil, la largeur et le poids du
vehicule demande. Les profils canoniques sont `car`, `motorcycle` et `truck`.
`map_data` stocke les profils autorises, la largeur utile et le tonnage maximal de chaque
route. `routing` compare ces contraintes au contexte avant de classer les alternatives.

OSRM continue a produire des alternatives avec son profil `driving`. Le backend applique
ensuite les contraintes locales. Une alternative incompatible reste visible avec
`eligible=false` et un fort malus pour rendre la decision explicable pendant la Phase 2.

Le rapprochement entre une geometrie OSRM et les donnees locales utilise `ST_DWithin`
avec une tolerance configurable en metres. Cette tolerance evite de perdre une
information quand deux traces de la meme route ne sont pas superposees au centimetre.
Les colonnes geographiques possedent deja des index PostGIS GIST crees par GeoAlchemy.

Le fichier `phase2_roads.json` fournit un petit jeu de donnees de demonstration. Il est
charge par un script idempotent: une cle et une version de seed empechent les doublons.
Ces donnees servent a valider les regles, pas a constituer la future base de production.

## Collecte GPS Map Core Phase 3

Le module `journeys` ouvre la Phase 3 sans transformer le backend en plateforme VTC.
Son objectif est de collecter des traces GPS exploitables par le Map Core.
Le vocabulaire public utilise `map-traces` pour eviter la confusion avec les
futures courses DiddiGo.

Un utilisateur connecte peut demarrer une trace terrain, envoyer des positions GPS par batch,
terminer la trace et la relire. Les positions sont stockees en PostGIS `POINT`
afin de preparer les futures analyses spatiales: ecarts route prevue/reelle, troncons
lents, routes contournees et suggestions d'enrichissement.

Cette premiere version ne modifie pas encore automatiquement le scoring. Elle produit
des donnees propres; l'analyse et les suggestions automatiques viendront ensuite.
