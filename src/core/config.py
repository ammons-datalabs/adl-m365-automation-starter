
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

    # Observability
    appinsights_connection_string: str | None = Field(default=None, alias="APPINSIGHTS_CONNECTION_STRING")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
