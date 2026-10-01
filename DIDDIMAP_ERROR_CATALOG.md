# DiddiMap Error Catalog

Ce document liste les erreurs publiques que DiddiMap peut retourner aux autres
services et au frontend.

Format standard:

```json
{
  "status": "error",
  "code": "validation_error",
  "message": "Invalid field 'positions[0].lat': Input should be less than or equal to 90",
  "details": []
}
```

## Requetes

| Code | HTTP | Retry | Sens |
| --- | ---: | --- | --- |
| `invalid_request` | 400 | Non | JSON invalide ou requete mal formee. |
| `validation_error` | 422 | Non | Champ invalide, par exemple latitude hors limites. |

## Auth

| Code | HTTP | Retry | Sens |
| --- | ---: | --- | --- |
| `authentication_required` | 401 | Non | Token utilisateur ou service manquant/invalide. |
| `forbidden` | 403 | Non | Role insuffisant. |
| `service_token_invalid` | 401 | Non | Token service S2S invalide ou signe par une cle inconnue. |
| `service_client_id_invalid` | 401 | Non | `X-Client-ID` ne correspond pas au token service. |
| `service_token_inactive` | 403 | Non | Client service S2S inactif. |
| `service_not_allowed` | 403 | Non | Service appelant non autorise sur cette integration. |
| `service_scope_invalid` | 403 | Non | Scope S2S manquant, par exemple `diddimap:traces:write`. |

## Traces GPS

| Code | HTTP | Retry | Sens |
| --- | ---: | --- | --- |
| `trace_not_found` | 404 | Non | Trace introuvable. |
| `trace_already_finished` | 409 | Non | Trace deja terminee. |
| `trace_not_accepting_positions` | 409 | Non | Trace qui n'accepte plus de positions. |
| `trace_not_started` | 409 | Non | Trace non demarree. |
| `trace_not_finished` | 409 | Non | Analyse demandee avant finalisation. |

Important: `recommendation: ignore_for_scoring` n'est pas une erreur. C'est un
resultat metier valide qui signifie que la course peut continuer avec le prix
estime, mais que la trace ne doit pas influencer le scoring Map Core.

## Routing

| Code | HTTP | Retry | Sens |
| --- | ---: | --- | --- |
| `out_of_coverage` | 409 | Non | Point hors zone couverte. |
| `no_route_found` | 404 | Non | Aucun itineraire trouve. |
| `routing_engine_unavailable` | 503 | Oui | OSRM indisponible. |
| `routing_timeout` | 504 | Oui | OSRM trop lent. |
| `invalid_routing_response` | 502 | Oui | Reponse OSRM invalide. |

## Serveur

| Code | HTTP | Retry | Sens |
| --- | ---: | --- | --- |
| `internal_error` | 500 | Oui | Erreur interne inattendue. |

## Endpoint catalogue

Le catalogue est aussi disponible via:

```text
GET /api/v1/errors/catalog
```
