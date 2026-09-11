# MedScan on Vercel

The independent deployment is `https://medscan-assistant.vercel.app`.
It does not proxy requests to the former customer's server and contains no
customer dataset or migrated patient records.

## Components

- Vite/React frontend, build output `dist/public`.
- FastAPI in `api/index.py`, Python 3.12, same-origin `/api/*` routing.
- Separate Neon PostgreSQL resource `medscan-data` (Free plan), owned by this
  Vercel project. Runtime tables: `medscan_studies`, `medscan_images`,
  `medscan_messages`. Schema initialization never replaces existing records.
- ReportLab PDF with bundled, openly licensed Noto Sans fonts.

`vercel.json` deliberately specifies `npm ci --include=dev`: automatic Vercel
dependency detection otherwise selects the root Python requirements before the
Vite build, using a different build-image interpreter. The Python function
builder separately installs `pyproject.toml` dependencies for Python 3.12.
Keep `pyproject.toml`, `requirements.txt`, and `server/requirements.txt` in sync.

## Configuration

Required production/preview variables:

- `DATABASE_URL` (set by the dedicated Neon integration).
- `JWT_SECRET`: randomly generated, at least 32 bytes.
- `MEDSCAN_ADMIN_EMAIL`, `MEDSCAN_ADMIN_PASSWORD_HASH`: one owner account;
  Passlib PBKDF2-SHA256, 600,000 iterations. There is no built-in demo password.
- Optional `MEDSCAN_ADMIN_NAME`, `VITE_APP_ID`.
- For AI: `BUILT_IN_FORGE_API_KEY`, `BUILT_IN_FORGE_API_URL` (default
  `https://openrouter.ai/api`), `LLM_MODEL` (a vision-capable model).

`scripts/configure_vercel.py` creates/stores private local login details in
`.private/medscan-access.json` and submits secrets via stdin, never command-line
arguments or stdout. `--ai-env PATH` is an explicit operator action: only use an
authorized AI account. It imports only AI settings, not the old database or JWT.
Do not commit or upload `.private`, `.env*`, datasets, or runtime data.

## Verification

```powershell
npm.cmd ci --include=dev
npm.cmd run check
npm.cmd run build
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt pypdf
.\.venv\Scripts\python.exe -m unittest discover -s tests -b
.\.venv\Scripts\python.exe scripts/smoke_test.py
```

The offline tests use temporary databases, synthetic images, and mock AI.
The deployment smoke test creates and deletes only its own synthetic study.
Add `--ai` only when authorized to make two real, potentially billable provider
calls using a synthetic image. `/api/health` reports storage readiness and
whether authentication/AI are configured; it does not expose secret values.

## Current limits

- PNG, JPEG, WebP, GIF originals up to 3 MiB. No automatic alteration of uploaded
  originals. Image downloads require the authenticated owner and are not cached.
- PDF and DICOM input are not implemented in the published baseline.
- PDF includes a labelled viewing preview (up to 1600 px, JPEG quality 90).
  The original remains available in the study. PDF output is limited to 3 MiB.
- This remains an AI-assisted demo/MVP, not a clinically validated diagnostic
  system. Real patient data requires a separate privacy, access, clinical, and
  hosting-compliance review. No accuracy or regulatory certification is implied.
- The owner's separate, unfinished local modifications were not included in
  this restoration. Port them deliberately and test them against this API.

## Rollback and data safety

Use Vercel's deployment rollback or deploy a reviewed Git revision. Do not drop
the database to roll back code. Keep the Neon resource and its backups separate
from deployment lifecycle. Free-plan limits can suspend service when exceeded;
upgrades must be explicitly approved by the owner.
