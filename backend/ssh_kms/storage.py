import errno
import fcntl
import json
import os
import re
import uuid
from contextlib import contextmanager
from pathlib import Path

from .config import KEY_FILE, KEY_FORMAT, KEY_ID_PATTERN


def serialize_key(key):
    """Return a key entry formatted for API responses with its stable ID."""
    return config_key_to_api_key(key)


def config_key_to_api_key(key):
    """Convert one JSON config key entry into the API field naming format."""
    api_key = dict(key)
    api_key["ssh_key"] = api_key.pop("ssh-key")
    return api_key


def api_key_to_config_key(key, existing_ids):
    """Convert a validated API key entry into the on-disk JSON format."""
    submitted_key = key.model_dump(exclude_none=True, by_alias=True)
    config_key = {
        "id": generate_key_id(existing_ids),
        "user": submitted_key["user"].strip(),
    }

    if "hostname" in submitted_key:
        config_key["hostname"] = submitted_key["hostname"].strip()
    if "hostname_regex" in submitted_key:
        config_key["hostname_regex"] = submitted_key["hostname_regex"].strip()

    config_key["ssh-key"] = submitted_key["ssh-key"].strip()
    return config_key


def filter_keys(user, hostname):
    """Filter configured keys by exact user and exact or regex hostname."""
    filtered_keys = []
    keys = read_key_json()

    for key in keys:
        hostname_match = False
        user_match = bool(user == key["user"])

        if "hostname" in key:
            hostname_match = bool(hostname == key["hostname"])
        else:
            hostname_match = bool(re.match(key["hostname_regex"], hostname))

        if user_match and hostname_match:
            filtered_keys.append(key)

    return filtered_keys


def read_key_json():
    """Read and validate the SSH key JSON configuration file."""
    with key_file_lock(exclusive=False):
        return read_key_json_unlocked()


def read_key_json_unlocked():
    """Read and validate the SSH key JSON configuration without taking a lock."""
    if not os.path.isfile(KEY_FILE):
        raise Exception(f"Key file {KEY_FILE} does not exist!")

    try:
        with open(KEY_FILE, "r", encoding="utf-8") as key_file:
            key_str = key_file.read()
        keys = json.loads(key_str)

        if not isinstance(keys, list):
            raise Exception(f"Key file format is not correct, use the next format: {KEY_FORMAT}")

        allowed_key_fields = {"id", "user", "hostname", "hostname_regex", "ssh-key"}
        seen_ids = set()

        for key in keys:
            validate_key_entry(key, allowed_key_fields, seen_ids)

        return keys
    except FileNotFoundError as e:
        raise Exception(f"Could not find key file {KEY_FILE}!") from e
    except PermissionError as e:
        raise Exception(f"Yo do not have permission to read key file {KEY_FILE}!") from e
    except json.decoder.JSONDecodeError as e:
        raise Exception(f"Key file {KEY_FILE} is not a valid json file!, {e}") from e


def validate_key_entry(key, allowed_key_fields, seen_ids):
    """Validate one raw key entry read from the JSON configuration file."""
    if not isinstance(key, dict):
        raise Exception(f"Key file format is not correct, use the next format: {KEY_FORMAT}")
    if set(key) - allowed_key_fields:
        raise Exception(f"Key file format is not correct, use the next format: {KEY_FORMAT}")
    for required_field in ("id", "ssh-key", "user"):
        if required_field not in key:
            raise Exception(f"Key file format is not correct, use the next format: {KEY_FORMAT}")
    if ("hostname" in key) == ("hostname_regex" in key):
        raise Exception(f"Key file format is not correct, use the next format: {KEY_FORMAT}")

    for field_name in ("id", "user", "hostname", "hostname_regex", "ssh-key"):
        if field_name in key and (not isinstance(key[field_name], str) or not key[field_name].strip()):
            raise Exception(f"Key file format is not correct, use the next format: {KEY_FORMAT}")

    validate_key_id(key["id"], seen_ids)
    if "hostname_regex" in key:
        try:
            re.compile(key["hostname_regex"])
        except re.error as e:
            raise Exception(f"hostname_regex is invalid: {e}") from e


def validate_key_id(key_id, seen_ids):
    """Validate one stable key ID and track duplicate values."""
    if not KEY_ID_PATTERN.match(key_id):
        raise Exception(f"Key id {key_id} is not valid")
    if key_id in seen_ids:
        raise Exception(f"Key id {key_id} is duplicated")
    seen_ids.add(key_id)


def write_key_json(keys):
    """Persist key entries to the JSON configuration file under an exclusive lock."""
    with key_file_lock(exclusive=True):
        write_key_json_unlocked(keys)


def write_key_json_unlocked(keys):
    """Persist key entries without taking a file lock."""
    key_file = Path(KEY_FILE)
    key_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file = key_file.with_suffix(f"{key_file.suffix}.tmp")
    content = json.dumps(order_key_entries(keys), indent=4) + "\n"

    with open(temp_file, "w", encoding="utf-8") as output_file:
        output_file.write(content)
        output_file.flush()
        os.fsync(output_file.fileno())

    try:
        os.replace(temp_file, key_file)
    except OSError as e:
        if e.errno != errno.EBUSY:
            raise

        write_key_json_in_place(key_file, content)
        temp_file.unlink(missing_ok=True)


def write_key_json_in_place(key_file, content):
    """Rewrite Docker file bind mounts that cannot be replaced by rename."""
    with open(key_file, "w", encoding="utf-8") as output_file:
        output_file.write(content)
        output_file.flush()
        os.fsync(output_file.fileno())


@contextmanager
def key_file_lock(exclusive):
    """Hold a shared or exclusive lock for the SSH key configuration file."""
    lock_file = Path(f"{KEY_FILE}.lock")
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH

    with open(lock_file, "w", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle, lock_mode)
        try:
            yield
        finally:
            fcntl.flock(lock_handle, fcntl.LOCK_UN)


def generate_key_id(existing_ids):
    """Generate a URL-safe key entry ID that is unique within the config."""
    while True:
        key_id = f"key_{uuid.uuid4().hex[:16]}"
        if key_id not in existing_ids:
            return key_id


def order_key_entries(keys):
    """Return key entries with a stable field order for readable JSON exports."""
    return [order_key_entry(key) for key in keys]


def order_key_entry(key):
    """Return one key entry with id, user, host matcher and SSH key fields ordered."""
    ordered_key = {
        "id": key["id"],
        "user": key["user"],
    }

    if "hostname" in key:
        ordered_key["hostname"] = key["hostname"]
    if "hostname_regex" in key:
        ordered_key["hostname_regex"] = key["hostname_regex"]

    ordered_key["ssh-key"] = key["ssh-key"]
    return ordered_key
