from src.settings import settings

if settings.SERVICE_TYPE == "mcp":
    from src.mcp_server import create_mcp_app

    application = create_mcp_app()
else:
    from src.api import get_application

    application = get_application()
