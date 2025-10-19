
from loguru import logger

def setup_logging():
    # In a real deployment, configure JSON logs + App Insights handler here
    logger.info("Logging initialised")
    return logger
