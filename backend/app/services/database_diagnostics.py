"""Log actionable driver diagnostics without SQL, bind parameters or credentials."""
import logging
from collections.abc import Mapping

logger = logging.getLogger(__name__)


def log_database_failure(path, exc):
    original = getattr(exc, "orig", None)
    state = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    params = getattr(exc, "params", None)
    boot_id = params.get("boot_id") if isinstance(params, Mapping) else None
    # Only numeric sample identity; never emit exception text/SQL/full parameter maps.
    if isinstance(boot_id, bool) or not isinstance(boot_id, int):
        boot_id = None
    reason = {"22003": "numeric_value_out_of_range", "22P02": "invalid_text_representation"}.get(state, "database_error")
    diagnostic = getattr(original, "diag", None)
    primary = getattr(diagnostic, "message_primary", None)
    # Exact safe PostgreSQL messages only: other messages can echo input values.
    safe_messages = {"integer out of range", "smallint out of range", "bigint out of range", "numeric field overflow"}
    message = primary if primary in safe_messages else "withheld"
    logger.error("database_failure path=%s type=%s driver=%s sqlstate=%s reason=%s boot_id=%s pg_message=%s",
                 path, type(exc).__name__, type(original).__name__, state, reason, boot_id, message)
