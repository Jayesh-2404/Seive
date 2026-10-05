"""Logging."""
import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app")
def audit(action, uid): log.info("audit %s uid=%s", action, uid)
