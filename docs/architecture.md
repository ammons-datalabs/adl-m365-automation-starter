
# Architecture

```mermaid
flowchart LR
    SP[SharePoint Library] -->|file created| PA[Power Automate Flow]
    PA -->|HTTP (multipart)| API[/FastAPI: /invoices/extract/]
    API -->|Azure Document Intelligence| DI[(Extraction)]
    API -->|fields + confidence| PA
    PA -->|Adaptive Card| Teams[Microsoft Teams]
    Teams --> User[Approver]
    User --> Teams --> PA
    PA -->|approved/rejected| SoR[(System of Record)]
```

- Power Automate orchestrates the process and shows a human-in-the-loop when confidence < threshold.
- FastAPI encapsulates extraction logic and exposes clean endpoints for flows and future apps.
- Teams webhooks demonstrate approvals quickly; replace with Graph/Dataverse approvals later.
