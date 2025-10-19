
# ADL M365 Automation Starter

Production‑ready starter for **Microsoft 365 intelligent automation** using **FastAPI** + **Power Automate** with CI via **Azure DevOps**.

**Why this repo**
- Ship a real M365 automation: document → extract → human‑in‑the‑loop approval → route to a system of record.
- Demonstrate Azure chops (App Service, Key Vault, DevOps pipelines) and safe LLM usage hooks.
- Uplift citizen developers with a repeatable pattern and short lab.

## Architecture (MVP)
- **Power Automate**: watches a SharePoint library; calls FastAPI to extract fields; posts an approval card in Teams; routes the outcome.
- **FastAPI**: `/health`, `/invoices/extract`, `/invoices/approve`.
- **Azure Document Intelligence** (optional): extraction; stub fallback included.
- **Responsible AI hooks**: pre/post processors and an eval test placeholder.
- **Azure DevOps**: build → test → package → deploy to Azure Web App; posts release notes to Teams.

See `docs/architecture.md` for the diagram.

## Quick start (local)
```bash
python -m venv .venv && source .venv/bin/activate  # (PowerShell: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
cp .env.example .env  # fill in values
uvicorn src.api.main:app --reload
# Visit http://127.0.0.1:8000/health
```

### Minimal API surface
- `GET /health` – readiness probe.
- `POST /invoices/extract` – multipart/form‑data with file; returns extracted fields (stub or Azure DI).
- `POST /invoices/approve` – demo approval: posts an Adaptive Card to a Teams Incoming Webhook (or stub).

### Power Automate (sample flow)
1. **Trigger**: “When a file is created (properties only)” (SharePoint).
2. **Get file content** (SharePoint).
3. **HTTP** action:
   - Method: `POST`
   - URI: `https://<your-webapp>/invoices/extract`
   - Headers: `Content-Type: multipart/form-data`
   - Body: use “Form-data” with `file` = file content
4. **Condition** on `confidence >= 0.8`:
   - If yes → **HTTP** to `/invoices/approve` (or write straight to Dataverse).
   - If no → create an **Adaptive Card** approval in Teams for a human check.

Example definitions are in `samples/power-automate/`.

## Azure DevOps CI/CD
- Pipeline file: `pipelines/azure-pipelines.yml`
- Stages: install → test (pytest) → package → (optional) deploy to Azure Web App
- Configure a Service Connection and variable group (`AZURE_SUBSCRIPTION`, `WEBAPP_NAME`, etc.).

## Responsible AI notes
This starter exposes pre/post processor hooks and an eval test placeholder. Wire it to your LLM service (Azure OpenAI or OSS) and enforce safety tests before deploy.

## Repo layout
```
src/           # FastAPI app, services, models
docs/          # architecture, runbook, lab
infra/         # bicep placeholder
pipelines/     # Azure DevOps YAML
samples/       # Power Automate snippets
tests/         # pytest
```

## Demo script (5 minutes)
1) Upload sample invoice to SharePoint → flow triggers.
2) Flow calls `/invoices/extract` → returns fields + confidence.
3) Teams shows an approval card (webhook demo). Approve.
4) Webhook response logged; “ERP topic” placeholder prints in logs.

## License
MIT (see `LICENSE`).
