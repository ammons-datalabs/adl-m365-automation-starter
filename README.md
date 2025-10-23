
# ADL M365 Automation Starter

![CI & Deploy](https://github.com/ammons-datalabs/adl-m365-automation-starter/actions/workflows/ci-deploy.yml/badge.svg)

Production‑ready starter for **Microsoft 365 intelligent automation** using **Azure Logic Apps** + **Azure Document Intelligence** with CI via **Azure DevOps**.

**Why this repo**
- Ship a real M365 automation: document → extract → intelligent routing → human‑in‑the‑loop approval.
- Demonstrate Azure AI capabilities (Document Intelligence, Logic Apps) with SharePoint and Teams integration.
- Provide a repeatable pattern for invoice processing with auto-approval logic.

## Architecture (MVP)
- **Azure Logic Apps**: watches a SharePoint library; extracts invoice data with Document Intelligence; evaluates approval criteria (≤$500, >85% confidence); routes to Approved/Pending folders; updates metadata; notifies Teams.
- **Azure Document Intelligence**: prebuilt invoice model extracts vendor, total, line items, dates, tax details.
- **SharePoint Online**: document storage with automated folder routing and status tracking.
- **Microsoft Teams**: webhook notifications for approved and pending invoices.

See `docs/LOGIC_APPS_SETUP.md` for detailed setup and `docs/architecture.md` for the diagram.

## Quick start

### Prerequisites
- Azure subscription
- SharePoint Online site
- Microsoft Teams channel
- Azure Document Intelligence resource

### Setup Steps

1. **Create SharePoint library structure:**
   ```
   Invoices/
   ├── Incoming/     # Drop new invoices here
   ├── Approved/     # Auto-approved (≤$500, high confidence)
   └── Pending/      # Manual review required
   ```

2. **Create Azure Document Intelligence resource:**
   ```bash
   az cognitiveservices account create \
     --name adl-invoice-extraction \
     --resource-group rg-adl-m365 \
     --kind FormRecognizer \
     --sku S0 \
     --location westus2
   ```

3. **Configure Teams webhook:**
   - Go to Teams channel → Connectors → Incoming Webhook
   - Copy the webhook URL

4. **Deploy Logic App:**
   - Create Logic App in Azure Portal
   - Import `infra/logic-app-definition.json` or build manually using Designer
   - Update connection strings and secrets

5. **Test the workflow:**
   - Upload a sample invoice to SharePoint `/Invoices/Incoming/`
   - Check Teams for notification
   - Verify invoice moved to Approved or Pending folder

See `docs/LOGIC_APPS_SETUP.md` for detailed configuration.

### Logic App Workflow

1. **Trigger**: When a file is created in SharePoint `/Invoices/Incoming/`
2. **Get file content** from SharePoint
3. **HTTP POST**: Submit to Document Intelligence for analysis
4. **Wait**: 5 seconds for processing
5. **HTTP GET**: Retrieve analysis results
6. **Compose**: Parse the Document Intelligence response
7. **Condition**: Evaluate approval criteria:
   - Invoice total ≤ $500
   - Document confidence > 85%
   - Content contains "invoice" (not "receipt")
8. **If approved**:
   - Update SharePoint status to "Approved"
   - Move to `/Invoices/Approved/`
   - Send Teams notification
9. **If pending**:
   - Update SharePoint status to "Pending"
   - Move to `/Invoices/Pending/`
   - Send Teams notification for manual review

Example definition is in `infra/logic-app-definition.json`.

## Azure DevOps CI/CD
- Pipeline file: `pipelines/azure-pipelines.yml`
- Stages: install → test (pytest) → package → (optional) deploy to Azure Web App
- Configure a Service Connection and variable group (`AZURE_SUBSCRIPTION`, `WEBAPP_NAME`, etc.)
- Tests validate Document Intelligence integration and invoice processing logic

## Responsible AI & Security
- Uses Azure Document Intelligence prebuilt models (Microsoft-validated)
- Confidence thresholds (>85%) prevent low-quality extractions from auto-approval
- Document type validation prevents processing non-invoice documents
- Secrets managed via Azure Key Vault (recommended) or Logic App parameters
- All processing happens within Azure tenant (no data leaves Microsoft cloud)

## Repo layout
```
src/                          # FastAPI app, services, models (optional API layer)
docs/                         # Setup guides and architecture
├── LOGIC_APPS_SETUP.md      # Detailed Logic Apps configuration
├── SHAREPOINT_SETUP.md      # SharePoint library setup
├── POWER_AUTOMATE_INTEGRATION.md  # Alternative Power Automate approach
└── architecture.md          # System architecture diagram
infra/                       # Infrastructure as code
├── bicep/                   # Bicep templates (optional)
└── logic-app-definition.json # Logic App workflow definition
pipelines/                   # Azure DevOps YAML
samples/                     # Sample invoices for testing
tests/                       # pytest suite for validation
```

## Demo script (5 minutes)
1. Upload sample invoice to SharePoint → Logic App triggers
2. Document Intelligence extracts fields (vendor, total, line items, confidence)
3. Logic App evaluates: amount ≤ $500 and confidence > 85%
4. Invoice auto-routed to Approved or Pending folder
5. SharePoint status column updated
6. Teams notification sent with invoice details

## License
MIT (see `LICENSE`).
