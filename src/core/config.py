
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = Field("adl-m365-automation-starter", alias="APP_NAME")
    app_env: str = Field("dev", alias="APP_ENV")

    # LLM (optional)
    llm_base_url: str | None = Field(default=None, alias="LLM_BASE_URL")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_deployment: str | None = Field(default=None, alias="LLM_DEPLOYMENT")

    # Azure Document Intelligence
    az_di_endpoint: str | None = Field(default=None, alias="AZ_DI_ENDPOINT")
    az_di_api_key: str | None = Field(default=None, alias="AZ_DI_API_KEY")

    # Microsoft Identity
    ms_tenant_id: str | None = Field(default=None, alias="MS_TENANT_ID")
    ms_client_id: str | None = Field(default=None, alias="MS_CLIENT_ID")
    ms_client_secret: str | None = Field(default=None, alias="MS_CLIENT_SECRET")

    # Graph
    graph_scope: str = Field("https://graph.microsoft.com/.default", alias="GRAPH_SCOPE")

    # Teams
    teams_webhook_url: str | None = Field(default=None, alias="TEAMS_WEBHOOK_URL")

    # API Base URL (for approval links in Teams cards)
    api_base_url: str = Field("http://127.0.0.1:8000", alias="API_BASE_URL")

    # CORS allowed origins (comma-separated list for production deployment)
    cors_origins: str = Field("http://localhost:3000,http://127.0.0.1:3000", alias="CORS_ORIGINS")

    # Observability
    appinsights_connection_string: str | None = Field(default=None, alias="APPINSIGHTS_CONNECTION_STRING")

    # Approval Rules Configuration
    approval_amount_threshold: float = Field(500.0, alias="APPROVAL_AMOUNT_THRESHOLD")
    approval_min_confidence: float = Field(0.85, alias="APPROVAL_MIN_CONFIDENCE")
    approval_require_invoice_keyword: bool = Field(True, alias="APPROVAL_REQUIRE_INVOICE_KEYWORD")
    approval_reject_receipt_keyword: bool = Field(True, alias="APPROVAL_REJECT_RECEIPT_KEYWORD")
    approval_allowed_bill_to_names: str = Field("", alias="APPROVAL_ALLOWED_BILL_TO_NAMES")  # Comma-separated list (empty = accept all)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
