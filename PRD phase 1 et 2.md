Oui. Le bon découpage est :

* **Phase 1 : Map Core de base**
* **Phase 2 : outils d’enrichissement local**
* **Phase 3 : alimentation avec de vraies données terrain**
* **Phase 4 : exploitation complète, notamment VTC et logistique**

Les phases 1 et 2 restent donc uniquement centrées sur la carte et le moteur de routage, conformément au principe du document selon lequel le graphe cartographique est l’actif principal. 

# Phase 1 — Carte et moteur de base

## Description et objectif

Créer une première version fonctionnelle de la carte d’Abidjan à partir d’OpenStreetMap.

Cette phase doit permettre de choisir un départ et une destination, calculer plusieurs itinéraires, afficher la distance, la durée et un coût estimatif.

Il n’y a encore aucune donnée locale propriétaire.

## Livrables Frontend

### Interface cartographique

* Carte d’Abidjan.
* Position actuelle de l’utilisateur.
* Boutons de zoom.
* Bouton de recentrage.
* Marqueurs de départ et de destination.
* Affichage de la ligne de l’itinéraire.

### Sélection du trajet

L’utilisateur peut :

* utiliser sa position actuelle comme départ ;
* poser manuellement un point sur la carte ;
* déplacer les points ;
* choisir une destination ;
* inverser le départ et la destination ;
* supprimer la sélection.

### Affichage des itinéraires

Pour chaque proposition :

* distance ;
* durée estimée ;
* prix estimatif ;
* affichage distinct sur la carte.

Exemple :

```text
Itinéraire 1
8,4 km
26 minutes
2 750 FCFA

Itinéraire 2
9,1 km
23 minutes
2 900 FCFA
```

### Détail du prix

```text
Tarif de base : 500 FCFA
Distance : 1 680 FCFA
Durée estimée : 30 minutes
Supplément : 0 FCFA
Total estimé : 2 700 FCFA
```

Le frontend affiche uniquement les informations calculées par le backend.

### Suivi simple d’un parcours

* Bouton « Démarrer le parcours ».
* Statut du parcours en cours.
* Durée écoulée.
* Distance parcourue.
* Bouton « Terminer le parcours ».
* Envoi des positions GPS au backend.

Il s’agit uniquement d’une fonction de test et de collecte cartographique, pas d’une course VTC.

## Livrables Backend

### Carte et routage

* Données OpenStreetMap de la Côte d’Ivoire.
* Serveur OSRM opérationnel.
* Calcul d’itinéraires sur Abidjan.
* Retour de plusieurs itinéraires lorsque disponibles.
* Retour de la distance.
* Retour de la durée estimée.
* Retour de la géométrie du trajet à afficher sur la carte.

### Calcul du coût

Le backend calcule :

```text
Coût =
tarif de base
+ distance × tarif kilométrique
+ éventuels suppléments
```

Les tarifs doivent être configurables.

### Enregistrement minimal

Le backend enregistre :

* le départ ;
* la destination ;
* l’itinéraire proposé ;
* la distance ;
* la durée estimée ;
* le prix proposé ;
* les points GPS du parcours ;
* la durée réelle ;
* la distance réellement parcourue.

Cette collecte prépare les phases suivantes, mais les données ne sont pas encore utilisées pour modifier le moteur.

### API de base

Endpoints principaux :

```text
POST /routes/calculate
POST /journeys/start
POST /journeys/{id}/positions
POST /journeys/{id}/finish
GET  /pricing
```

## Livrable complet de la Phase 1

Une application Web responsive et une API capables de :

```text
Afficher la carte d’Abidjan
        ↓
Choisir un départ et une destination
        ↓
Calculer plusieurs itinéraires
        ↓
Afficher distance, durée et prix
        ↓
Démarrer un parcours
        ↓
Enregistrer le trajet GPS réel
```

La Phase 1 livre donc un **moteur cartographique de base fonctionnel**, sans enrichissement local et sans fonctionnalités VTC.

---

# Phase 2 — Système d’enrichissement local

## Description et objectif

Créer les outils permettant d’ajouter des informations locales à la carte.

Cette phase ne consiste pas encore à disposer de milliers de données réelles. Elle met en place la structure nécessaire pour les recevoir, les valider et les utiliser dans le routage.

Un petit jeu de données test peut être utilisé pour vérifier le fonctionnement.

## Livrables Frontend

### Affichage des informations locales

La carte doit pouvoir afficher différentes couches :

* état réel des routes ;
* routes dégradées ;
* routes inondables ;
* routes bloquées ;
* points de contrôle ;
* péages ;
* zones congestionnées ;
* lieux et noms locaux.

L’utilisateur peut activer ou désactiver chaque couche.

### Ajout d’une information locale

L’utilisateur autorisé peut :

* sélectionner une route ou un point ;
* choisir un type d’information ;
* saisir une valeur ;
* ajouter un commentaire ;
* envoyer la proposition.

Exemple :

```text
Route sélectionnée : Rue X
Surface réelle : latérite dégradée
Praticabilité : faible
Voiture : déconseillée
Moto : autorisée
```

### Ajout d’un lieu local

L’utilisateur peut :

* poser un point sur la carte ;
* saisir le nom officiel ;
* ajouter plusieurs alias ;
* ajouter une description.

Exemple :

```text
Nom : Carrefour de l’Indénié

Alias :
- Indénié
- Grand carrefour
- Carrefour Adjamé
```

### Interface de validation

L’administrateur peut :

* consulter les propositions ;
* voir leur position sur la carte ;
* modifier les informations ;
* valider ;
* rejeter.

Statuts :

```text
Proposé
Validé
Rejeté
```

### Affichage de l’impact sur le trajet

Lorsque les données locales modifient un itinéraire, le frontend affiche une explication simple.

Exemple :

```text
La route la plus courte a été évitée :
- route fortement dégradée ;
- risque d’inondation.
```

## Livrables Backend

### Structure des données locales

Le backend doit pouvoir enregistrer :

* type de revêtement ;
* état réel de la route ;
* praticabilité saisonnière ;
* route inondable ;
* point de contrôle ;
* péage ;
* largeur de voie ;
* sécurité de nuit ;
* éclairage ;
* types de véhicules autorisés ;
* lieu local ;
* alias d’un lieu ;
* temps moyen d’attente.

Ces informations correspondent au principe des tags propriétaires prévu dans le document. 

### API d’enrichissement

Endpoints principaux :

```text
POST /local-data
GET  /local-data
PUT  /local-data/{id}
POST /local-data/{id}/validate
POST /local-data/{id}/reject

POST /local-places
GET  /local-places/search
```

### Validation des données

Une donnée proposée ne modifie pas directement le routage.

Le processus est :

```text
Proposition
     ↓
Validation administrative
     ↓
Publication
     ↓
Utilisation par le moteur
```

### Intégration au moteur

Les données validées doivent pouvoir influencer les itinéraires.

Exemples :

* route bloquée : interdite ;
* route très dégradée : pénalisée ;
* route inondable : pénalisée selon la saison ;
* route étroite : interdite à certains véhicules ;
* point de contrôle : ajout de temps ;
* route non sécurisée : pénalisée la nuit.

Pour cette phase, l’intégration peut être testée avec un nombre limité de routes et de données manuelles.

### Historique et versionnement

Le backend conserve :

* l’ancienne valeur ;
* la nouvelle valeur ;
* la date de modification ;
* la personne ayant proposé ;
* la personne ayant validé ;
* la version du graphe utilisée.

## Livrable complet de la Phase 2

Une plateforme capable de :

```text
Ajouter une information locale
        ↓
La faire valider
        ↓
L’afficher sur la carte
        ↓
L’intégrer au moteur
        ↓
Modifier les itinéraires proposés
```

La Phase 2 livre donc **le mécanisme d’enrichissement du Map Core**, mais pas encore une base locale complète.

Les vraies données collectées à grande échelle, les analyses automatiques des traces GPS et l’amélioration continue du graphe appartiendront à la Phase 3.
