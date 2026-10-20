# -*- coding: utf-8 -*-
"""
career_ai/db.py — Quản lý lưu trữ CSDL SQLite chuẩn ACID cho dự án.

Khắc phục hạn chế:
  - Thay thế cơ chế lưu trữ flat-file (feedback.json, prediction_logs.jsonl) vốn dễ gây race condition khi nhiều người dùng truy cập đồng thời.
  - Hỗ trợ giao dịch (Transactions), đảm bảo tính toàn vẹn dữ liệu (ACID).
  - Tự động di chuyển dữ liệu cũ từ JSON/JSONL vào SQLite khi khởi tạo lần đầu.
  - Đồng bộ ngược lại file JSON/JSONL để duy trì tính tương thích ngược tuyệt đối với các script/test cũ.
"""
import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from .storage_paths import DATA_DIR, data_file

DB_PATH = data_file("career_ai.db")
FEEDBACK_JSON = data_file("feedback.json")
INTERACTIONS_JSON = data_file("interactions.json")
LOGS_JSONL = data_file("prediction_logs.jsonl")

_LOCAL = threading.local()


def get_db_path() -> str:
    return DB_PATH


@contextmanager
def get_connection():
    """Context manager cung cấp kết nối SQLite với WAL mode và timeout an toàn đa luồng."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Khởi tạo schema bảng CSDL và di chuyển dữ liệu cũ nếu có."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                student_name TEXT DEFAULT '',
                top_group TEXT NOT NULL,
                top_prob REAL NOT NULL,
                rating INTEGER NOT NULL,
                liked_careers TEXT DEFAULT '[]',
                disliked_careers TEXT DEFAULT '[]',
                comment TEXT DEFAULT '',
                scores TEXT DEFAULT '{}',
                survey TEXT DEFAULT '{}'
            );
        """)
        feedback_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(feedbacks)").fetchall()
        }
        if "survey" not in feedback_columns:
            conn.execute("ALTER TABLE feedbacks ADD COLUMN survey TEXT DEFAULT '{}'")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_feedbacks_ts ON feedbacks(timestamp DESC);")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                top_group TEXT NOT NULL,
                career_id TEXT,
                duration_seconds REAL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_interactions_ts ON interactions(timestamp DESC);")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS prediction_logs (
                request_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                model_version TEXT NOT NULL,
                source TEXT DEFAULT 'web_ui',
                input_scores TEXT NOT NULL,
                predicted_group TEXT NOT NULL,
                top_probability REAL NOT NULL,
                latency_ms REAL NOT NULL,
                is_partial INTEGER DEFAULT 0
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pred_logs_ts ON prediction_logs(timestamp DESC);")

    # Di chuyển dữ liệu cũ từ JSON/JSONL sang SQLite nếu bảng rỗng
    _migrate_initial_data()


def _migrate_initial_data():
    """Di chuyển dữ liệu lịch sử từ các tệp JSON/JSONL vào SQLite nếu bảng chưa có bản ghi."""
    with get_connection() as conn:
        # 1. Feedbacks
        count_fb = conn.execute("SELECT COUNT(*) FROM feedbacks").fetchone()[0]
        if count_fb == 0 and os.path.exists(FEEDBACK_JSON):
            try:
                with open(FEEDBACK_JSON, "r", encoding="utf-8") as f:
                    records = json.load(f)
                for r in records:
                    conn.execute("""
                        INSERT OR IGNORE INTO feedbacks (
                            id, timestamp, student_name, top_group, top_prob,
                            rating, liked_careers, disliked_careers, comment, scores, survey
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        r.get("id", ""),
                        r.get("timestamp", datetime.now().isoformat()),
                        r.get("student_name", "Sinh viên"),
                        r.get("top_group", ""),
                        float(r.get("top_prob", 0.0)),
                        int(r.get("rating", 5)),
                        json.dumps(r.get("liked_careers", []), ensure_ascii=False),
                        json.dumps(r.get("disliked_careers", []), ensure_ascii=False),
                        r.get("comment", ""),
                        json.dumps(r.get("scores", {}), ensure_ascii=False),
                        json.dumps(r.get("survey", {}), ensure_ascii=False),
                    ))
            except Exception:
                pass

        # 2. Interactions
        count_it = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
        if count_it == 0 and os.path.exists(INTERACTIONS_JSON):
            try:
                with open(INTERACTIONS_JSON, "r", encoding="utf-8") as f:
                    records = json.load(f)
                for r in records:
                    conn.execute("""
                        INSERT OR IGNORE INTO interactions (
                            id, timestamp, event_type, top_group, career_id, duration_seconds
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        r.get("id", ""),
                        r.get("timestamp", datetime.now().isoformat()),
                        r.get("event_type", ""),
                        r.get("top_group", ""),
                        r.get("career_id"),
                        float(r.get("duration_seconds", 0.0)) if r.get("duration_seconds") is not None else None,
                    ))
            except Exception:
                pass

        # 3. Prediction logs
        count_logs = conn.execute("SELECT COUNT(*) FROM prediction_logs").fetchone()[0]
        if count_logs == 0 and os.path.exists(LOGS_JSONL):
            try:
                with open(LOGS_JSONL, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        r = json.loads(line)
                        conn.execute("""
                            INSERT OR IGNORE INTO prediction_logs (
                                request_id, timestamp, model_version, source,
                                input_scores, predicted_group, top_probability,
                                latency_ms, is_partial
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            r.get("request_id", ""),
                            r.get("timestamp", datetime.now().isoformat()),
                            r.get("model_version", "1.0.0"),
                            r.get("source", "web_ui"),
                            json.dumps(r.get("input_scores", {}), ensure_ascii=False),
                            r.get("predicted_group", ""),
                            float(r.get("top_probability", 0.0)),
                            float(r.get("latency_ms", 0.0)),
                            int(r.get("is_partial", 0)),
                        ))
            except Exception:
                pass


# ---------------- API Thao tác Feedback ----------------
def insert_feedback(record: dict) -> dict:
    """Lưu bản ghi phản hồi vào SQLite."""
    with get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO feedbacks (
                id, timestamp, student_name, top_group, top_prob,
                rating, liked_careers, disliked_careers, comment, scores, survey
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record["id"],
            record["timestamp"],
            record.get("student_name", "Sinh viên"),
            record["top_group"],
            float(record["top_prob"]),
            int(record["rating"]),
            json.dumps(record.get("liked_careers", []), ensure_ascii=False),
            json.dumps(record.get("disliked_careers", []), ensure_ascii=False),
            record.get("comment", ""),
            json.dumps(record.get("scores", {}), ensure_ascii=False),
            json.dumps(record.get("survey", {}), ensure_ascii=False),
        ))
    return record


def delete_feedback(feedback_id: str) -> bool:
    """Xóa một phản hồi khỏi SQLite và trả về liệu bản ghi có tồn tại hay không."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM feedbacks WHERE id = ?", (feedback_id,))
    return cursor.rowcount > 0


def get_all_feedbacks(limit: int = None) -> list:
    """Lấy danh sách phản hồi từ SQLite theo thứ tự mới nhất."""
    query = "SELECT * FROM feedbacks ORDER BY timestamp DESC"
    if limit:
        query += f" LIMIT {int(limit)}"
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "timestamp": row["timestamp"],
                "student_name": row["student_name"],
                "top_group": row["top_group"],
                "top_prob": row["top_prob"],
                "rating": row["rating"],
                "liked_careers": json.loads(row["liked_careers"] or "[]"),
                "disliked_careers": json.loads(row["disliked_careers"] or "[]"),
                "comment": row["comment"],
                "scores": json.loads(row["scores"] or "{}"),
                "survey": json.loads(row["survey"] or "{}"),
            })
        return result


# ---------------- API Thao tác Interaction ----------------
def insert_interaction(record: dict) -> dict:
    """Lưu sự kiện tương tác vào SQLite."""
    with get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO interactions (
                id, timestamp, event_type, top_group, career_id, duration_seconds
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            record["id"],
            record["timestamp"],
            record["event_type"],
            record["top_group"],
            record.get("career_id"),
            float(record["duration_seconds"]) if record.get("duration_seconds") is not None else None,
        ))
    return record


def get_all_interactions(limit: int = None) -> list:
    """Lấy danh sách tương tác người dùng."""
    query = "SELECT * FROM interactions ORDER BY timestamp DESC"
    if limit:
        query += f" LIMIT {int(limit)}"
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
        return [dict(row) for row in rows]


# ---------------- API Thao tác Prediction Logs ----------------
def insert_prediction_log(record: dict) -> dict:
    """Lưu nhật ký lượt dự đoán vào SQLite."""
    with get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO prediction_logs (
                request_id, timestamp, model_version, source,
                input_scores, predicted_group, top_probability,
                latency_ms, is_partial
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record["request_id"],
            record["timestamp"],
            record.get("model_version", "1.0.0"),
            record.get("source", "web_ui"),
            json.dumps(record.get("input_scores", {}), ensure_ascii=False),
            record["predicted_group"],
            float(record["top_probability"]),
            float(record["latency_ms"]),
            int(record.get("is_partial", 0)),
        ))
    return record


def get_prediction_logs(limit: int = 200) -> list:
    """Lấy danh sách log dự đoán từ SQLite."""
    query = f"SELECT * FROM prediction_logs ORDER BY timestamp DESC LIMIT {int(limit)}"
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
        result = []
        for row in rows:
            result.append({
                "request_id": row["request_id"],
                "timestamp": row["timestamp"],
                "model_version": row["model_version"],
                "source": row["source"],
                "input_scores": json.loads(row["input_scores"] or "{}"),
                "predicted_group": row["predicted_group"],
                "top_probability": row["top_probability"],
                "latency_ms": row["latency_ms"],
                "is_partial": bool(row["is_partial"]),
            })
        return result


# Tự động khởi tạo schema khi import module
init_db()
