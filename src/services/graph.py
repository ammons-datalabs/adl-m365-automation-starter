
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
                {"type": "Action.Submit", "title": "Approve", "data": {"action": "approve"}},
                {"type": "Action.Submit", "title": "Reject", "data": {"action": "reject"}}
            ]
        }
    }]
}

async def post_approval_card(fields: dict) -> dict:
    if not settings.teams_webhook_url:
        return {"status": "skipped", "reason": "TEAMS_WEBHOOK_URL not set"}

    card = json.loads(json.dumps(ADAPTIVE_CARD_TEMPLATE))
    facts = card["attachments"][0]["content"]["body"][1]["facts"]
    for k in ["vendor","invoice_number","invoice_date","total","currency","confidence"]:
        if k in fields and fields[k] is not None:
            facts.append({"title": k, "value": str(fields[k])})

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(settings.teams_webhook_url, json=card)
        return {"status": "sent", "http_status": r.status_code}
