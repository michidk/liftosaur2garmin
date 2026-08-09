# liftosaur2garmin Helm chart

This chart deploys the liftosaur2garmin FastAPI dashboard as one Kubernetes
Deployment and exposes it on port 8123.

## Secrets

The application normally needs these Secret keys:

| Key | Requirement |
| --- | --- |
| `LIFTOSAUR_API_KEY` | Required for Liftosaur API access |
| `GARMIN_EMAIL` | Required for the Garmin account |
| `DATABASE_URL` | Strongly recommended on Kubernetes for PostgreSQL-backed state |
| `GARMIN_PASSWORD` | Optional; direct login only |
| `L2G_PASSWORD` | Optional; enables dashboard password authentication |

Use `secret.existingSecret` for a Secret managed by `kubectl`, Sealed Secrets,
1Password Operator, or another secret backend. Alternatively, set
`secret.create: true` and provide values under `secret.data`; avoid committing
real credentials to source control.

For example, an out-of-band Secret can be created from shell variables:

```sh
kubectl create namespace liftosaur2garmin
kubectl -n liftosaur2garmin create secret generic liftosaur2garmin-env \
  --from-literal=LIFTOSAUR_API_KEY="$LIFTOSAUR_API_KEY" \
  --from-literal=GARMIN_EMAIL="$GARMIN_EMAIL" \
  --from-literal=DATABASE_URL="$DATABASE_URL"
```

## Install

Copy `values-example.yaml`, adjust the hostname, image tag, and Secret name,
then install from the repository root:

```sh
helm install liftosaur2garmin ./helm/liftosaur2garmin \
  -n liftosaur2garmin \
  --create-namespace \
  -f my-values.yaml
```

Without an Ingress, follow the post-install port-forward instructions printed
by Helm.

## Configuration and storage

`config.GARMIN_AUTH_WORKER_BASE_URL` and `config.LIFTOSAUR_API_BASE_URL` are
non-secret settings rendered into a ConfigMap only when non-empty. A change to a
chart-managed ConfigMap or Secret updates a checksum annotation and rolls the
Pod.

With `DATABASE_URL`, the application stores configuration, credentials, and
Garmin OAuth tokens in PostgreSQL, so persistence should remain disabled. For a
local-filesystem deployment, enable `persistence.enabled`; the PVC is mounted at
`/home/app`, covering both `/home/app/.liftosaur2garmin` and
`/home/app/.garminconnect`.

Keep `replicaCount: 1`. Sync coordination and autosync scheduling are
in-process, so horizontal scaling can cause duplicate work.

The liveness and readiness probes call `GET /`. Kubernetes accepts any 2xx or
3xx response, including the `/login` redirect used when `L2G_PASSWORD` is set.
