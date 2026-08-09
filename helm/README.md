# liftosaur2garmin Helm chart

This chart deploys the liftosaur2garmin FastAPI dashboard as one Kubernetes
Deployment and exposes it on port 8123. It's a generic chart with no
assumptions about your specific cluster (ingress controller, secret backend,
etc) - everything infra-specific is left to your own values file.

## Secrets

The application normally needs these Secret keys (unrelated to the database -
see "Storage" below for `DATABASE_URL`):

| Key | Requirement |
| --- | --- |
| `LIFTOSAUR_API_KEY` | Required for Liftosaur API access |
| `GARMIN_EMAIL` | Required for the Garmin account |
| `GARMIN_PASSWORD` | Optional; direct login only |
| `L2G_PASSWORD` | Optional; enables dashboard password authentication |

Use `secret.existingSecret` for a Secret managed by `kubectl`, Sealed Secrets,
1Password Operator, or another secret backend of your choice - the chart
doesn't care how the Secret was created. Alternatively, set `secret.create:
true` and provide values under `secret.data`; avoid committing real
credentials to source control.

For example, an out-of-band Secret can be created from shell variables:

```sh
kubectl create namespace liftosaur2garmin
kubectl -n liftosaur2garmin create secret generic liftosaur2garmin-env \
  --from-literal=LIFTOSAUR_API_KEY="$LIFTOSAUR_API_KEY" \
  --from-literal=GARMIN_EMAIL="$GARMIN_EMAIL"
```

## Install

Copy `values-example.yaml`, adjust the hostname, image tag, and Secret name,
then install from the repository root:

```sh
helm install liftosaur2garmin ./helm \
  -n liftosaur2garmin \
  --create-namespace \
  -f my-values.yaml
```

Without an Ingress, follow the post-install port-forward instructions printed
by Helm.

## Storage

Two independent strategies - pick one:

1. **Postgres (recommended)** - `postgresql.enabled: true` deploys a bundled
   Postgres StatefulSet alongside the app, or set `postgresql.existingSecret`
   (+ `existingSecretKey`) to point at an existing Secret holding a
   `postgresql://...` connection string for an external/managed database.
   Either way, `DATABASE_URL` is wired in automatically. Configuration,
   credentials, and Garmin OAuth tokens all persist in the database, so the
   pod is fully stateless - `persistence` should stay disabled.
2. **Local filesystem (fallback)** - with no Postgres configured at all, the
   app falls back to a local SQLite database and a Garmin token file under
   `$HOME`. Set `persistence.enabled: true` to mount a PVC there so that data
   survives pod restarts (`persistence.mountPath` defaults to `/home/app`,
   matching the non-root user baked into this chart's Dockerfile).

The app container runs with a read-only root filesystem. Its home directory is
always mounted writable: from the configured PVC when persistence is enabled,
or from an ephemeral `emptyDir` otherwise. `/tmp` is also backed by an
`emptyDir` for transient FIT generation and library runtime files.

## Configuration

`config.GARMIN_AUTH_WORKER_BASE_URL` and `config.LIFTOSAUR_API_BASE_URL` are
non-secret settings rendered into a ConfigMap only when non-empty. A change to
a chart-managed ConfigMap or Secret updates a checksum annotation and rolls
the Pod.

Keep `replicaCount: 1`. Sync coordination and autosync scheduling are
in-process, so horizontal scaling can cause duplicate work.

The liveness probe calls dependency-free `GET /healthz`. The readiness probe
calls `GET /readyz`, which verifies that the configured SQLite or PostgreSQL
storage is usable. Both bypass dashboard authentication and first-run setup.
