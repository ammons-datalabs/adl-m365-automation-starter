
from fastapi import FastAPI
from ..core.logging import setup_logging
from .routers import health, invoice

logger = setup_logging()
app = FastAPI(title="ADL M365 Automation Starter")

app.include_router(health.router)
app.include_router(invoice.router)
