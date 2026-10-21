"""Retention and cleanup for feedback, interaction, and prediction data."""

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone

from . import db
from . import feedback_store
from .retrain_service import rebuild_feedback_training_data
from .storage_paths import data_file

logger = logging.getLogger(__name__)

LOG_RETENTION_DAYS = 60
INTERACTION_RETENTION_DAYS = 60
INTERACTIONS_JSON = data_file("interactions.json")
PREDICTION_LOGS_JSONL = data_file("prediction_logs.jsonl")


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        timestamp = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
    return timestamp


def _atomic_write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    directory = os.path.dirname(path) or "."
    file_descriptor, temporary_path = tempfile.mkstemp(dir=directory, prefix=".retention-")
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as file:
            file.write(content)
        os.replace(temporary_path, path)
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)


def _prune_json(path: str, cutoff: datetime) -> int:
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8") as file:
        records = json.load(file)
    if not isinstance(records, list):
        raise ValueError(f"Expected a JSON list in {path}")
    kept = []
    for record in records:
        if not isinstance(record, dict):
            kept.append(record)
            continue
        timestamp = _parse_timestamp(record.get("timestamp"))
        if timestamp is None:
            logger.warning("Retention kept a feedback/interactions mirror record without a valid timestamp in %s", path)
            kept.append(record)
        elif timestamp >= cutoff:
            kept.append(record)
    removed_count = len(records) - len(kept)
    if removed_count:
        _atomic_write(path, json.dumps(kept, ensure_ascii=False, indent=2) + "\n")
    return removed_count


def _prune_jsonl(path: str, cutoff: datetime) -> int:
    if not os.path.exists(path):
        return 0
    kept_lines = []
    removed_count = 0
    with open(path, encoding="utf-8") as file:
        for line in file:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Retention kept an invalid JSON line in %s", path)
                kept_lines.append(line)
                continue
            if not isinstance(record, dict):
                kept_lines.append(line)
                continue
            timestamp = _parse_timestamp(record.get("timestamp"))
            if timestamp is None:
                logger.warning("Retention kept a prediction log without a valid timestamp in %s", path)
                kept_lines.append(line)
            elif timestamp >= cutoff:
                kept_lines.append(line)
            else:
                removed_count += 1
    if removed_count:
        _atomic_write(path, "".join(kept_lines))
    return removed_count


def _rebuild_feedback_training_rows(feedbacks: list[dict]) -> int:
    return rebuild_feedback_training_data(feedbacks)


def purge_expired_data(now: datetime | None = None) -> dict:
    """Delete data past the configured retention windows from SQLite and mirrors."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is not None:
        current = current.astimezone(timezone.utc).replace(tzinfo=None)

    log_cutoff = current - timedelta(days=LOG_RETENTION_DAYS)
    interaction_cutoff = current - timedelta(days=INTERACTION_RETENTION_DAYS)

    deleted = db.delete_expired_records(
        log_cutoff=log_cutoff.isoformat(timespec="seconds"),
        interaction_cutoff=interaction_cutoff.isoformat(timespec="seconds"),
    )

    feedbacks = feedback_store.get_all_feedback()
    training_rows = _rebuild_feedback_training_rows(feedbacks)

    interactions_removed = _prune_json(INTERACTIONS_JSON, interaction_cutoff)
    logs_removed = _prune_jsonl(PREDICTION_LOGS_JSONL, log_cutoff)

    result = {
        "feedback_cutoff": None,
        "log_cutoff": log_cutoff.isoformat(timespec="seconds"),
        "interaction_cutoff": interaction_cutoff.isoformat(timespec="seconds"),
        "deleted_feedbacks": deleted["feedbacks"],
        "deleted_interactions": deleted["interactions"],
        "deleted_prediction_logs": deleted["prediction_logs"],
        "deleted_feedback_mirror_records": 0,
        "deleted_interaction_mirror_records": interactions_removed,
        "deleted_prediction_log_mirror_records": logs_removed,
        "remaining_feedback_training_rows": training_rows,
        "model_retrained": False,
    }
    if any((
        deleted["feedbacks"], deleted["interactions"], deleted["prediction_logs"],
        interactions_removed, logs_removed,
    )):
        logger.info("Retention cleanup completed: %s", result)
    return result
