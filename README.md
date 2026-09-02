# liftosaur2garmin

Sync Liftosaur workouts to Garmin Connect by converting Liftosaur history records into strength-training FIT files and uploading them to Garmin.

## What It Does

- Fetches workout history from Liftosaur with a personal API key
- Parses Liftosaur workout text into exercises, sets, reps, weights, and warmups
- Uses a Garmin FIT mapping and upload pipeline for Garmin Connect
- Declares a current FIT SDK profile so Garmin and downstream apps decode the same exercise taxonomy
- Supports CLI sync and the FastAPI dashboard flow

## Requirements

- A Liftosaur premium subscription with API access
- A Garmin Connect account
- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) for environment and dependency management

## Setup From Scratch

Clone the repo, create a virtual environment, activate it, and install the project itself:

```bash
uv venv
source .venv/bin/activate
UV_CACHE_DIR=.uv-cache uv pip install -e ".[dev]"
```

Why install with `-e ".[dev]"` instead of `-r requirements.txt`?

- `requirements.txt` installs dependencies only
- `uv pip install -e ".[dev]"` installs the `liftosaur2garmin` package and creates the `liftosaur2garmin` command in `.venv/bin/`

Check that the command exists:

```bash
which liftosaur2garmin
liftosaur2garmin --help
```

If you do not want to activate the virtual environment, you can run the CLI with either of these forms:

```bash
.venv/bin/liftosaur2garmin --help
.venv/bin/python -m liftosaur2garmin.cli --help
```

## Credentials And Config

Create a Liftosaur API key in the Liftosaur app:

1. Open Liftosaur
2. Go to `Settings`
3. Open `API Keys`
4. Create a key and copy it

The app can read credentials from:

- `~/.liftosaur2garmin/config.json`
- Environment variables
- CLI flags
- The web setup page

The main environment variables are:

- `LIFTOSAUR_API_KEY`
- `GARMIN_EMAIL`
- `GARMIN_AUTH_WORKER_BASE_URL`
- `L2G_PASSWORD`

`GARMIN_PASSWORD` is optional. It is still accepted for direct local CLI login, but the primary flow is to connect Garmin once and reuse the saved token file.

`GARMIN_AUTH_WORKER_BASE_URL` is optional. Set it on hosted deployments after you deploy the Cloudflare Worker in [worker-di](./worker-di). When it is present, the hosted setup page can connect to Garmin directly, including 2FA.

`L2G_PASSWORD` is optional. When set, the dashboard requires that password before showing pages or running API actions. When unset, dashboard auth is disabled.

Example:

```bash
LIFTOSAUR_API_KEY="your-liftosaur-api-key"
GARMIN_EMAIL="you@example.com"
L2G_PASSWORD="choose-a-dashboard-password"
```

If a `.env` file exists in your working directory, the app loads it automatically.

If you want the variables exported into your shell session as well, load it like this:

```bash
set -a
source .env
set +a
```

The local bootstrap flow is the simplest path for most users:

```bash
liftosaur2garmin init
```

That command:

- saves app settings to `~/.liftosaur2garmin/config.json`
- performs Garmin login on your own machine
- prompts for an MFA code if Garmin requests one
- writes the Garmin token file to `~/.garminconnect/garmin_tokens.json`

You can also use the dashboard for the same local flow:

```bash
liftosaur2garmin serve
```

Then open the local setup page and use `Connect Garmin`.

Hosted deployments use local bootstrap too. Connect Garmin locally first, then upload the exported token file in the hosted setup page.

If `GARMIN_AUTH_WORKER_BASE_URL` is configured on the hosted app, the setup page can also connect Garmin directly:

- enter Garmin email and password on the hosted setup page
- if Garmin requires 2FA, enter the 6-digit code inline
- if Garmin rejects the direct login, the page reveals a browser sign-in fallback and keeps token-file upload as a backup path

The Garmin token file can be exported with:

```bash
liftosaur2garmin export-garmin-token
```

## CLI

```bash
liftosaur2garmin init
liftosaur2garmin sync
liftosaur2garmin list
liftosaur2garmin status
liftosaur2garmin unmapped
liftosaur2garmin export-garmin-token
liftosaur2garmin serve
```

You can still pass credentials as flags for one-off local runs:

```bash
liftosaur2garmin sync \
  --liftosaur-api-key "$LIFTOSAUR_API_KEY" \
  --garmin-email "$GARMIN_EMAIL"
```

If you want the CLI to attempt a fresh local Garmin login instead of reusing saved tokens, you can also add:

```bash
liftosaur2garmin sync \
  --liftosaur-api-key "$LIFTOSAUR_API_KEY" \
  --garmin-email "$GARMIN_EMAIL" \
  --garmin-password "$GARMIN_PASSWORD"
```

## First Run

One clean way to get started is:

```bash
uv venv
source .venv/bin/activate
UV_CACHE_DIR=.uv-cache uv pip install -e ".[dev]"
export LIFTOSAUR_API_KEY="your-liftosaur-api-key"
liftosaur2garmin init
liftosaur2garmin export-garmin-token
liftosaur2garmin list
liftosaur2garmin sync --dry-run
```

## Tests

```bash
UV_CACHE_DIR=.uv-cache uv run pytest -q
```

Worker tests:

```bash
node --test worker-di/index.test.js
```

## Garmin-to-Strava Exercise Compatibility

Garmin and Strava classify strength sets from the FIT `category` and
`category_subtype` numbers; Strava does not copy the exercise label rendered by
Garmin Connect. Strava documents support for all FIT SDK exercises, with some
mapped to broader names in Strava.

The previous `fit-tool` 0.9.15 dependency generated files declaring FIT profile
21.60, while this project's exercise table contains 17 concrete pairs introduced
in Garmin profile 21.171. Garmin Connect tolerated that mismatch, but downstream
importers could interpret the newer numbers as unknown. `fit-tool` 0.9.16 uses
profile 21.212, which contains every concrete pair currently emitted here.

The tests audit every mapping against the installed FIT profile and verify that
the generated file header declares that same profile. This catches future
mappings that require a newer SDK before they can produce inconsistent files.
Custom mappings are validated against the same profile before they are saved,
and invalid mappings already present in local or cloud storage are ignored.

References: [Strava FIT upload support](https://developers.strava.com/docs/uploads/),
[Garmin FIT SDK 21.171](https://github.com/garmin/fit-python-sdk/tree/21.171.0),
[Garmin FIT SDK 21.212](https://github.com/garmin/fit-python-sdk/tree/21.212.0),
[`fit-tool` 0.9.16](https://github.com/shaonianche/python_fit_tool/releases/tag/v0.9.16),
and the upstream project's independent report of the
[stale-profile limitation](https://github.com/drkostas/hevy2garmin/issues/328).

## Acknowledgements

This project builds on the open-source work in [`drkostas/hevy2garmin`](https://github.com/drkostas/hevy2garmin) by Konstantinos Georgiou. Liftosaur integration targets the REST API documented at [liftosaur.com/doc/api](https://www.liftosaur.com/doc/api).

## Notes

- The Liftosaur client normalizes history records into the workout structure expected by the existing Garmin sync pipeline.
- Exercise mapping includes compatibility logic for Liftosaur-style names such as `Bench Press, Barbell`.
- Every concrete numeric exercise category and subtype is validated against the installed FIT SDK profile. Generated file headers declare that same profile version so Garmin and downstream apps such as Strava interpret newer exercise values consistently.
- Hosted Garmin login can run through the repo-owned Cloudflare Worker in [worker-di](./worker-di). Without `GARMIN_AUTH_WORKER_BASE_URL`, hosted setup falls back to token-file import from a local `init` or `serve` flow.
