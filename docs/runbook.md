
# Runbook

## Secrets
- Use Key Vault for `MS_CLIENT_SECRET`, `AZ_DI_API_KEY`, etc.
- For local dev, `.env` is supported (do not commit).

## Scaling
- Front the API with Azure Front Door or APIM for enterprise use.
- Queue long-running OCR to a worker (Service Bus).

## Monitoring
- Add App Insights SDK and request logging.
- Emit business KPIs: #processed, #human-review, latency.

## Disaster Recovery
- Keep flows and solution as managed; export regularly via pipeline.
