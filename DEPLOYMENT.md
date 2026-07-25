# AbidjanMaps - Guide de deploiement

Ce document garde la convention de deploiement du projet. Il sert de reference
pour le backend actuel, puis pour les futurs services frontend et metier.

## Objectif

Le projet suit une progression simple:

```text
dev -> staging -> main
```

- `dev`: branche de travail active. On y ajoute les features et corrections.
- `staging`: branche candidate. On y merge une phase quand elle est coherente.
- `main`: branche stable. Elle represente la version prete pour production.

Pour l'instant, tous les changements de developpement partent sur `dev`.
Quand une phase est terminee et testee, on merge `dev` vers `staging`.
Si `staging` est stable sur le VPS, on merge ensuite vers `main`.

## Environnements

| Environnement | Branche Git | Role |
| --- | --- | --- |
| local | branche en cours | Developpement sur Windows avec Docker Compose |
| dev | `dev` | Integration continue des nouvelles features |
| staging | `staging` | Validation sur VPS avant production |
| production | `main` | Version stable |

## Convention de nommage

Utiliser des noms previsibles pour eviter la confusion quand plusieurs services
arriveront.

### Repositories

```text
abidjanmaps-backend
abidjanmaps-frontend
abidjanmaps-routing-service
abidjanmaps-user-service
```

Au debut, le backend peut rester un modular monolith. Les modules metier
pourront etre extraits plus tard en vrais microservices si le besoin devient
clair.

### Stacks Portainer

Format recommande:

```text
abidjanmaps-<service>-<environment>
```

Exemples:

```text
abidjanmaps-backend-dev
abidjanmaps-backend-staging
abidjanmaps-backend-prod
```

Le nom actuel `abidjanmaps-backend-staging-backend` fonctionne, mais il est plus
long que necessaire. On peut le garder temporairement si la stack existe deja.

### Domaines

Format recommande:

```text
<service>-<environment>.diddifree.com
```

Exemples:

```text
abidjanmaps-backend-dev.diddifree.com
abidjanmaps-backend-staging.diddifree.com
abidjanmaps-backend.diddifree.com
```

URL staging actuelle:

```text
http://abidjanmaps-backend-staging.diddifree.com/
```

Avec Nginx Proxy Manager, l'objectif est d'exposer les services publics en
HTTPS, puis de rediriger HTTP vers HTTPS.

## Backend actuel

Pour Portainer, utiliser:

```text
docker-compose.portainer.yaml
```

Ce fichier est adapte au deploiement depuis GitHub. Il ne depend pas du service
one-shot `init-db`. Le backend applique les migrations Alembic au demarrage:

```text
alembic upgrade head
```

puis lance FastAPI.

## Variables Portainer

Variables minimales pour le backend:

```text
POSTGRES_DB=mapdb
POSTGRES_USER=mapuser
POSTGRES_PASSWORD=mot-de-passe-fort
AUTH_SECRET_KEY=long-secret-aleatoire
OSRM_DATA_PATH=/opt/abidjanmaps/osrm
BACKEND_PORT=8001
OSRM_PORT=5000
POSTGRES_PORT=5432
```

Notes:

- `AUTH_SECRET_KEY` doit etre different par environnement.
- `POSTGRES_PASSWORD` doit etre fort et non commite dans Git.
- `BACKEND_PORT` doit etre libre sur le VPS.
- Si le port `8000` est deja occupe, utiliser `8001`, `8002` ou un autre port
  interne au serveur.

## Donnees OSRM

Les fichiers OSRM sont volumineux et ne sont pas suivis dans GitHub.

Le dossier serveur indique par `OSRM_DATA_PATH` doit contenir:

```text
ivory-coast-latest.osrm
ivory-coast-latest.osrm.*
```

Exemple de chemin serveur:

```text
/opt/abidjanmaps/osrm
```

Le conteneur OSRM monte ce dossier en lecture seule dans:

```text
/data
```

## Nginx Proxy Manager

Pour chaque service expose:

```text
Domain Names: abidjanmaps-backend-staging.diddifree.com
Forward Hostname / IP: IP_DU_VPS ou nom du conteneur selon le reseau
Forward Port: BACKEND_PORT
Scheme: http
```

Ensuite:

- activer SSL avec Let's Encrypt;
- forcer HTTPS;
- tester `/api/v1/health`.

## Checklist de deploiement

Avant de deployer:

- verifier que la branche cible est la bonne;
- verifier que `docker-compose.portainer.yaml` est present sur GitHub;
- verifier les variables Portainer;
- verifier que `BACKEND_PORT` est libre;
- verifier que `OSRM_DATA_PATH` existe sur le VPS;
- verifier que les fichiers OSRM sont presents;
- verifier que `AUTH_SECRET_KEY` n'est pas la valeur dev;
- verifier les logs `backend`, `db` et `osrm`;
- tester `GET /api/v1/health`;
- tester `GET /docs` seulement si l'environnement doit exposer la doc.

## Workflow de merge

1. Developper sur `dev`.
2. Lancer les tests localement.
3. Pousser `dev` sur GitHub.
4. Deployer ou redeployer la stack dev si elle existe.
5. Quand la phase est terminee, merger `dev` vers `staging`.
6. Deployer staging sur Portainer.
7. Tester l'API publique via Nginx Proxy Manager.
8. Si staging est stable, merger `staging` vers `main`.

## Verification rapide

Health:

```text
GET /api/v1/health
```

URL staging actuelle:

```text
http://abidjanmaps-backend-staging.diddifree.com/api/v1/health
```

Docs:

```text
http://abidjanmaps-backend-staging.diddifree.com/docs
```

## Comptes utilisateurs par environnement

Chaque environnement a sa propre base PostgreSQL. Un utilisateur cree en local
n'existe pas automatiquement sur staging ou production.

Pour creer le premier administrateur dans le conteneur backend staging:

```text
python -m scripts.create_user --email admin@example.com --role admin
```

Si l'utilisateur existe deja mais que le mot de passe ne fonctionne plus:

```text
python -m scripts.create_user --email admin@example.com --reset-password
```

Le script demande le mot de passe deux fois sans l'afficher.

## Regle importante

On garde le backend actuel comme modular monolith tant que les modules ne sont
pas encore assez independants pour justifier une extraction. Le code reste deja
prepare pour cela grace aux modules verticaux:

```text
routing
map_data
local_enrichment
users
```

Cette approche permet d'avancer vite maintenant, tout en gardant une porte
propre vers les microservices plus tard.
