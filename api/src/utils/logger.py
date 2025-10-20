import logging

import google.cloud.logging
from src.settings import settings

logger = logging.getLogger(__name__)

if settings.ENVIRONMENT == "PROD":
    # Use Google Cloud Logging for production
    client = google.cloud.logging.Client()
    client.setup_logging()
    logger.setLevel(getattr(logging, settings.LOGGING_LEVEL))
else:
    # Use basic logging for local development
    logging.basicConfig(
        level=getattr(logging, settings.LOGGING_LEVEL), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
