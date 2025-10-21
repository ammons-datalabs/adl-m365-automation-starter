
import json
import httpx
from ..core.config import settings

# Lightweight demo approval: post an Adaptive Card to a Teams Incoming Webhook.
# In production, consider Graph APIs or Dataverse Approvals.

ADAPTIVE_CARD_TEMPLATE = {
    "type": "message",
    "attachments": [{
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {"type": "TextBlock", "weight": "Bolder", "size": "Medium", "text": "Invoice Approval"},
                {"type": "FactSet", "facts": []}
            ],
            "actions": [
                {"type": "Action.OpenUrl", "title": "Approve", "url": "https://example.com/approve"},
                {"type": "Action.OpenUrl", "title": "Reject", "url": "https://example.com/reject"}
            ]
        }
    }]
}

async def post_approval_card(fields: dict, approval_id: str) -> dict:
    if not settings.teams_webhook_url:
        return {"status": "skipped", "reason": "TEAMS_WEBHOOK_URL not set"}

    # Use configured API base URL (supports both local and deployed environments)
    base_url = settings.api_base_url

    card = json.loads(json.dumps(ADAPTIVE_CARD_TEMPLATE))
    facts = card["attachments"][0]["content"]["body"][1]["facts"]
    for k in ["vendor","invoice_number","invoice_date","total","currency","confidence"]:
        if k in fields and fields[k] is not None:
            facts.append({"title": k, "value": str(fields[k])})

    # Update the action buttons with actual approval URLs
    card["attachments"][0]["content"]["actions"] = [
        {
            "type": "Action.OpenUrl",
            "title": "Approve",
            "url": f"{base_url}/invoices/approval/{approval_id}/approve"
        },
        {
            "type": "Action.OpenUrl",
            "title": "Reject",
            "url": f"{base_url}/invoices/approval/{approval_id}/reject"
        }
    ]

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(settings.teams_webhook_url, json=card)
        return {"status": "sent", "http_status": r.status_code}
