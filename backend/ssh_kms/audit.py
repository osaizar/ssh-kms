import json
from datetime import datetime, timezone

from .auth import current_username


def audit_key_change(action, actor, key):
    """Write a structured audit log entry for key mutations."""
    print(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": current_username(actor),
        "action": action,
        "target_id": key.get("id"),
        "target_user": key.get("user"),
        "target_hostname": key.get("hostname"),
        "target_hostname_regex": key.get("hostname_regex"),
    }))
