# -*- coding: utf-8 -*-
"""
tests/test_enhanced_features.py — Kiểm thử các tính năng khắc phục hạn chế:
  1. CSDL SQLite (ACID) thay thế Flat-file storage.
  2. Hỗ trợ đánh giá sớm cho sinh viên năm 1-3 (Partial Grades Assessment).
  3. Tự động hóa chu trình Retrain và Live Reload.
"""
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SAMPLE_SALARY_DATA = {
    "schema_version": 1,
    "type": "unavailable",
    "currency": "VND",
    "period": "month",
    "location": "Vietnam",
    "data_period": "not available",
    "role_scope": "exact_role",
    "proxy_role": None,
    "sample_size": None,
    "status": "unavailable",
    "reviewed_at": "2026-01-10",
    "source_count": 0,
    "observations": [],
    "note": "No salary figure published",
}

from career_ai import db, feedback_store, monitor_service
from career_ai.domain_knowledge import SUBJECTS, SUBJECT_KEYS, impute_missing_scores
from career_ai.model_exporter import validate_input_scores
from career_ai.retrain_service import (
    check_and_trigger_auto_retrain, register_reload_callback, notify_model_reloaded,
)

try:
    from fastapi.testclient import TestClient
    import api.main as api_main
    HAS_API = True
except Exception:
    HAS_API = False


class TestEnhancedFeatures(unittest.TestCase):
    def setUp(self):
        db.init_db()

    def test_student_survey_metrics_exclude_missing_answers(self):
        from career_ai.survey_metrics import summarize_student_survey

        summary = summarize_student_survey([
            {"survey": {"relevance": 5, "usefulness": 4, "explore_intent": "yes"}},
            {"survey": {"relevance": 3, "usefulness": 2, "explore_intent": "no"}},
            {"survey": {}},
            {},
        ])

        self.assertEqual(summary["response_count"], 2)
        self.assertEqual(summary["average_relevance"], 4.0)
        self.assertEqual(summary["relevance_positive_pct"], 50.0)
        self.assertEqual(summary["relevance_positive_ci95"], (9.5, 90.5))
        self.assertEqual(summary["average_usefulness"], 3.0)
        self.assertEqual(summary["usefulness_positive_pct"], 50.0)
        self.assertEqual(summary["usefulness_positive_ci95"], (9.5, 90.5))
        self.assertEqual(summary["explore_intent_yes_pct"], 50.0)
        self.assertEqual(summary["explore_intent_yes_ci95"], (9.5, 90.5))
        self.assertEqual(summary["minimum_recommended_sample"], 20)

    def test_legacy_feedback_table_is_migrated_for_survey_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "legacy.db")
            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE feedbacks (
                        id TEXT PRIMARY KEY, timestamp TEXT NOT NULL,
                        student_name TEXT DEFAULT '', top_group TEXT NOT NULL,
                        top_prob REAL NOT NULL, rating INTEGER NOT NULL,
                        liked_careers TEXT DEFAULT '[]',
                        disliked_careers TEXT DEFAULT '[]',
                        comment TEXT DEFAULT '', scores TEXT DEFAULT '{}'
                    )
                """)
            conn.close()
            with patch.object(db, "DB_PATH", db_path), \
                    patch.object(db, "FEEDBACK_JSON", os.path.join(tmp, "no-feedback.json")), \
                    patch.object(db, "INTERACTIONS_JSON", os.path.join(tmp, "no-interactions.json")), \
                    patch.object(db, "LOGS_JSONL", os.path.join(tmp, "no-logs.jsonl")):
                db.init_db()
                with db.get_connection() as conn:
                    columns = {
                        row["name"] for row in conn.execute("PRAGMA table_info(feedbacks)")
                    }

            self.assertIn("survey", columns)

    def test_survey_metrics_report_no_values_when_no_answers(self):
        from career_ai.survey_metrics import summarize_student_survey

        summary = summarize_student_survey([{}, {"survey": {}}])

        self.assertEqual(summary["response_count"], 0)
        self.assertIsNone(summary["average_relevance"])
        self.assertIsNone(summary["average_usefulness"])
        self.assertIsNone(summary["explore_intent_yes_pct"])
        self.assertIsNone(summary["relevance_positive_ci95"])
        self.assertIsNone(summary["usefulness_positive_ci95"])
        self.assertIsNone(summary["explore_intent_yes_ci95"])

    def test_student_survey_wilson_interval_reflects_small_sample_uncertainty(self):
        from career_ai.survey_metrics import summarize_student_survey

        summary = summarize_student_survey([
            {"survey": {"relevance": 5}},
        ])

        self.assertEqual(summary["relevance_positive_pct"], 100.0)
        self.assertEqual(summary["relevance_positive_ci95"], (20.7, 100.0))

    def test_career_catalog_audit_requires_citation_and_recent_review(self):
        from datetime import date
        from career_ai.catalog_audit import audit_career_catalog

        complete_record = {
            "salary_data": dict(SAMPLE_SALARY_DATA),
            "muc_luong": "Mức lương tham khảo",
            "xu_huong_thi_truong": "Ổn định",
            "khu_vuc": "Việt Nam",
            "nguon_du_lieu": "Báo cáo thị trường",
            "nguon_url": "https://example.com/report",
            "ngay_kiem_tra": "2026-01-10",
            "thoi_diem_cap_nhat": "2025-2026",
            "nguon_tham_khao": [{
                "ten": "Báo cáo thị trường",
                "url": "https://example.com/report",
                "ky_du_lieu": "2025-2026",
                "pham_vi": ["muc_luong", "xu_huong_thi_truong"],
            }],
        }
        clean = audit_career_catalog(
            {"C1": complete_record}, today=date(2026, 2, 1)
        )
        self.assertEqual(clean["issue_count"], 0)
        self.assertEqual(clean["ready_count"], 1)
        self.assertEqual(clean["sourced_claim_count"], 2)

        incomplete = audit_career_catalog(
            {"C1": {"nguon_du_lieu": "Báo cáo"}}, today=date(2026, 2, 1)
        )
        fields = {item["field"] for item in incomplete["issues"]}
        self.assertIn("muc_luong", fields)
        self.assertIn("xu_huong_thi_truong", fields)

    def test_catalog_accepts_explicitly_unavailable_market_claims(self):
        from datetime import date
        from career_ai.catalog_audit import audit_career_catalog

        result = audit_career_catalog({
            "C1": {
                "salary_data": dict(SAMPLE_SALARY_DATA),
                "muc_luong": "Chưa có dữ liệu được xác thực cho đúng chức danh này.",
                "xu_huong_thi_truong": "Chưa có dữ liệu được xác thực cho đúng chức danh này.",
                "khu_vuc": "Việt Nam",
                "nguon_tham_khao": [],
            },
        }, today=date(2026, 2, 1))

        self.assertEqual(result["issue_count"], 0)
        self.assertEqual(result["ready_count"], 1)
        self.assertEqual(result["sourced_claim_count"], 0)
        self.assertEqual(result["unavailable_claim_count"], 2)

    def test_catalog_requires_comparable_career_to_be_disclosed(self):
        from datetime import date
        from career_ai.catalog_audit import audit_career_catalog

        career = {
            "salary_data": {
                **SAMPLE_SALARY_DATA,
                "type": "proxy_median",
                "role_scope": "related_role_proxy",
                "proxy_role": "Kỹ sư AI/ML",
            },
            "muc_luong": "Tham khảo từ Kỹ sư AI/ML; không phải dữ liệu riêng cho nghề này.",
            "xu_huong_thi_truong": "Chưa có dữ liệu được xác thực cho đúng chức danh này.",
            "khu_vuc": "Việt Nam",
            "thoi_diem_cap_nhat": "2025",
            "ngay_kiem_tra": "2026-10-19",
            "nguon_du_lieu": "Báo cáo lương",
            "nguon_tham_khao": [{
                "ten": "Báo cáo lương",
                "url": "https://example.com/report",
                "ky_du_lieu": "2025",
                "pham_vi": ["muc_luong"],
                "loai_tham_chieu": "nghe_tuong_duong",
                "nghe_tham_chieu": "Kỹ sư AI/ML",
            }],
        }
        accepted = audit_career_catalog({"C1": career}, today=date(2026, 10, 19))
        self.assertEqual(accepted["issue_count"], 0, accepted["issues"])

        career["muc_luong"] = "Lương trung vị theo nguồn."
        rejected = audit_career_catalog({"C1": career}, today=date(2026, 10, 19))
        self.assertIn(
            "comparison_target_not_disclosed_in_claim",
            {item["issue"] for item in rejected["issues"]},
        )
        career["muc_luong"] = "Tham khảo từ Kỹ sư AI/ML; không phải dữ liệu riêng cho nghề này."
        career["nguon_tham_khao"][0]["nghe_tham_chieu"] = ""
        missing_comparator = audit_career_catalog(
            {"C1": career}, today=date(2026, 10, 19)
        )
        self.assertIn(
            "missing_comparison_target",
            {item["issue"] for item in missing_comparator["issues"]},
        )

    def test_structured_salary_summary_preserves_measurement_context(self):
        from web.ui_kit import _salary_summary

        summary = _salary_summary({
            "type": "experience_medians",
            "status": "historical_report",
            "data_period": "2023-2024; exact period uncertain",
            "location": "Vietnam",
            "observations": [{
                "statistic": "median",
                "value_vnd_per_month": 16_000_000,
                "experience": "1-2 years",
            }],
        }, "fallback")

        self.assertIn("Trung vị (1–2 năm): 16 triệu VND/tháng", summary)
        self.assertIn("Dữ liệu lịch sử", summary)
        self.assertIn("Kỳ dữ liệu: 2023-2024; exact period uncertain", summary)
        self.assertIn("Khu vực: Việt Nam", summary)

    def test_career_card_explains_recommendation_and_score_limit(self):
        from web.ui_kit import career_card

        card = career_card(0, {
            "career_name": "Backend",
            "career_group": "Phát triển phần mềm",
            "description": "Build APIs",
            "match_percentage": 74.5,
            "strengths": [{"subject": "Cơ sở dữ liệu"}],
            "soft_skill_matches": [{"label": "Giải quyết vấn đề"}],
            "improvements": [{"subject": "Mạng máy tính"}],
            "unstudied_core": [{"subject": "Linux"}],
        })

        self.assertIn("Vì sao nghề này được gợi ý?", card)
        self.assertIn("Cơ sở dữ liệu", card)
        self.assertIn("Giải quyết vấn đề", card)
        self.assertIn("Mạng máy tính", card)
        self.assertIn("Linux", card)
        self.assertIn("không dự đoán khả năng thành công", card)

    def test_source_checker_distinguishes_blocked_urls_and_expired_listings(self):
        from datetime import date
        from career_ai.source_check import check_market_sources, classify_http_status

        self.assertEqual(classify_http_status(403), "blocked_or_rate_limited")
        self.assertEqual(classify_http_status(404), "not_found")
        self.assertEqual(classify_http_status(200), "reachable")
        with patch(
            "career_ai.source_check._check_url",
            return_value={"url": "https://example.com", "status": "blocked_or_rate_limited"},
        ):
            result = check_market_sources({
                "C1": {
                    "nguon_tham_khao": [{
                        "url": "https://example.com",
                        "ky_du_lieu": "2025 survey",
                    }],
                    "salary_data": {
                        "observations": [{
                            "statistic": "advertised_range",
                            "expires_at": "2026-09-30",
                        }],
                    },
                },
            }, today=date(2026, 10, 1))

        self.assertEqual(result["urls"][0]["status"], "blocked_or_rate_limited")
        self.assertEqual(result["period_checks"][0]["status"], "not_checked_due_to_access")
        self.assertEqual(result["listings"][0]["status"], "expired")
        self.assertTrue(result["listings"][0]["manual_review_required"])

    def test_retention_uses_selected_windows_and_does_not_retrain_model(self):
        from datetime import datetime, timezone
        from career_ai import retention_service

        now = datetime(2026, 10, 20, tzinfo=timezone.utc)
        with patch.object(
            retention_service.db,
            "delete_expired_records",
            return_value={"feedbacks": 1, "interactions": 2, "prediction_logs": 3},
        ) as delete_records, patch.object(
            retention_service,
            "_prune_json",
            side_effect=[1, 2],
        ), patch.object(
            retention_service,
            "_prune_jsonl",
            return_value=3,
        ), patch.object(
            retention_service.feedback_store,
            "get_all_feedback",
            return_value=[],
        ), patch.object(
            retention_service,
            "_rebuild_feedback_training_rows",
            return_value=0,
        ), patch(
            "career_ai.cbf_recommender.cbf_recommender.reload"
        ) as reload_recommender:
            result = retention_service.purge_expired_data(now=now)

        cutoffs = delete_records.call_args.kwargs
        self.assertEqual(cutoffs["feedback_cutoff"], "2026-06-22T00:00:00")
        self.assertEqual(cutoffs["log_cutoff"], "2026-08-21T00:00:00")
        self.assertEqual(cutoffs["interaction_cutoff"], "2026-08-21T00:00:00")
        self.assertEqual(result["deleted_feedbacks"], 1)
        self.assertFalse(result["model_retrained"])
        reload_recommender.assert_called_once()

    def test_retention_removes_expired_sqlite_and_mirror_records_only(self):
        from datetime import datetime, timezone
        from career_ai import retention_service

        now = datetime(2026, 10, 20, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            feedback_path = os.path.join(tmp, "feedback.json")
            interaction_path = os.path.join(tmp, "interactions.json")
            logs_path = os.path.join(tmp, "prediction_logs.jsonl")
            with patch.object(db, "DB_PATH", os.path.join(tmp, "retention.db")), \
                    patch.object(db, "FEEDBACK_JSON", feedback_path), \
                    patch.object(db, "INTERACTIONS_JSON", interaction_path), \
                    patch.object(db, "LOGS_JSONL", logs_path), \
                    patch.object(feedback_store, "FEEDBACK_PATH", feedback_path), \
                    patch.object(feedback_store, "INTERACTIONS_PATH", interaction_path), \
                    patch.object(retention_service, "INTERACTIONS_JSON", interaction_path), \
                    patch.object(retention_service, "PREDICTION_LOGS_JSONL", logs_path):
                db.init_db()
                old_timestamp = "2026-01-01T00:00:00"
                current_timestamp = "2026-10-01T00:00:00"
                feedbacks = [
                    {
                        "id": "old-feedback",
                        "timestamp": old_timestamp,
                        "top_group": "Data",
                        "top_prob": 0.7,
                        "rating": 3,
                    },
                    {
                        "id": "current-feedback",
                        "timestamp": current_timestamp,
                        "top_group": "Data",
                        "top_prob": 0.8,
                        "rating": 5,
                    },
                ]
                for feedback in feedbacks:
                    db.insert_feedback(feedback)
                for record_id, timestamp in (
                    ("old-interaction", old_timestamp),
                    ("current-interaction", current_timestamp),
                ):
                    db.insert_interaction({
                        "id": record_id,
                        "timestamp": timestamp,
                        "event_type": "view",
                        "top_group": "Data",
                        "duration_seconds": 1,
                    })
                    db.insert_prediction_log({
                        "request_id": record_id,
                        "timestamp": timestamp,
                        "model_version": "test",
                        "predicted_group": "Data",
                        "top_probability": 0.7,
                        "latency_ms": 10,
                    })
                with open(feedback_path, "w", encoding="utf-8") as file:
                    json.dump(feedbacks, file)
                with open(interaction_path, "w", encoding="utf-8") as file:
                    json.dump([
                        {"id": "old-interaction", "timestamp": old_timestamp},
                        {"id": "current-interaction", "timestamp": current_timestamp},
                    ], file)
                with open(logs_path, "w", encoding="utf-8") as file:
                    file.write(json.dumps({"request_id": "old-interaction", "timestamp": old_timestamp}) + "\n")
                    file.write(json.dumps({"request_id": "current-interaction", "timestamp": current_timestamp}) + "\n")

                with patch.object(
                    retention_service,
                    "_rebuild_feedback_training_rows",
                    side_effect=lambda records: len(records),
                ), patch(
                    "career_ai.cbf_recommender.cbf_recommender.reload"
                ):
                    result = retention_service.purge_expired_data(now=now)

                self.assertEqual(
                    [row["id"] for row in db.get_all_feedbacks()],
                    ["current-feedback"],
                )
                with open(feedback_path, encoding="utf-8") as file:
                    self.assertEqual([row["id"] for row in json.load(file)], ["current-feedback"])
                with open(interaction_path, encoding="utf-8") as file:
                    self.assertEqual(
                        [row["id"] for row in json.load(file)],
                        ["current-interaction"],
                    )
                with open(logs_path, encoding="utf-8") as file:
                    kept_logs = [json.loads(line) for line in file if line.strip()]
                self.assertEqual([row["request_id"] for row in kept_logs], ["current-interaction"])
                self.assertTrue(result["deleted_feedbacks"])
                self.assertTrue(result["deleted_interactions"])
                self.assertTrue(result["deleted_prediction_logs"])
                self.assertFalse(result["model_retrained"])

    def test_computer_vision_shows_market_proxy_without_claiming_exact_salary(self):
        from career_ai.catalog_audit import CAREERS_PATH
        from web.ui_kit import career_explorer_card

        with CAREERS_PATH.open(encoding="utf-8") as file:
            career = json.load(file)["CV01"]

        self.assertIn("42,1%", career["xu_huong_thi_truong"])
        self.assertIn("không phải số liệu riêng cho Computer Vision", career["xu_huong_thi_truong"])
        self.assertIn("thỏa thuận, không công khai con số", career["muc_luong"])
        self.assertIn("hết hạn 09/05/2024", career["muc_luong"])

        card = career_explorer_card(career)
        self.assertIn("tham khảo, không riêng chức danh này: nhóm AI/Data/ML", card)
        self.assertIn("thỏa thuận, không công khai con số", card)

    def test_market_catalog_uses_role_specific_topcv_listings_as_historical_evidence(self):
        from career_ai.catalog_audit import CAREERS_PATH
        from web.ui_kit import career_explorer_card

        with CAREERS_PATH.open(encoding="utf-8") as file:
            careers = json.load(file)

        uiux = careers["UD01"]
        self.assertIn("15–20 triệu", uiux["muc_luong"])
        self.assertIn("hết hạn 23/07/2026", uiux["muc_luong"])
        self.assertIn("2212321.html", uiux["nguon_tham_khao"][0]["url"])
        uiux_card = career_explorer_card(uiux)
        self.assertIn("15–20 triệu", uiux_card)
        self.assertIn("TopCV — Nhân viên UI/UX Designer", uiux_card)

        vision = careers["CV01"]
        self.assertIn("thỏa thuận, không công khai con số", vision["muc_luong"])
        self.assertIn("hết hạn 09/05/2024", vision["muc_luong"])
        self.assertIn("j1296523.html", vision["nguon_tham_khao"][0]["url"])
        vision_card = career_explorer_card(vision)
        self.assertIn("thỏa thuận, không công khai con số", vision_card)
        self.assertNotIn("Chưa có số liệu lương đủ tin cậy", vision_card)

    def test_real_career_catalog_has_claim_scoped_evidence_or_clear_gaps(self):
        from career_ai.catalog_audit import CAREERS_PATH, audit_career_catalog

        with CAREERS_PATH.open(encoding="utf-8") as file:
            careers = json.load(file)
        result = audit_career_catalog(careers)

        self.assertEqual(result["career_count"], 21)
        self.assertEqual(result["issue_count"], 0, result["issues"])
        self.assertEqual(result["sourced_claim_count"], 42)
        self.assertEqual(result["unavailable_claim_count"], 0)
        self.assertEqual(result["ready_count"], 21)
        self.assertTrue(
            careers["BE01"]["muc_luong"].startswith("Lương trung vị theo năm kinh nghiệm")
        )
        self.assertFalse(
            careers["UD01"]["muc_luong"].startswith("Chưa có dữ liệu được xác thực")
        )
        for career_id in ("SG01", "SC01", "PT01"):
            with self.subTest(career_id=career_id):
                self.assertFalse(
                    careers[career_id]["muc_luong"].startswith("Chưa có dữ liệu được xác thực")
                )
                self.assertFalse(
                    careers[career_id]["xu_huong_thi_truong"].startswith("Chưa có dữ liệu được xác thực")
                )
                self.assertEqual(
                    set(careers[career_id]["pham_vi_nguon"]),
                    {"muc_luong", "xu_huong_thi_truong"},
                )
                from web.ui_kit import career_card

                career = careers[career_id]
                card = career_card(0, {
                    "career_name": career["career_name"],
                    "career_group": career["career_group"],
                    "description": career["mo_ta"],
                    "match_percentage": 80,
                    "salary": career["muc_luong"],
                    "trend": career["xu_huong_thi_truong"],
                    "region": career["khu_vuc"],
                    "sources": career["nguon_tham_khao"],
                })
                self.assertIn("topcv.vn", card)
                self.assertIn("en.nhandan.vn", card)
                self.assertNotIn("Chưa có nguồn tham khảo phù hợp", card)
                self.assertNotIn("SalaryExpert", career["muc_luong"])
                self.assertLess(len(career["muc_luong"]), 140)
                self.assertTrue(career["nguon_url"].startswith("https://www.topcv.vn/"))
        self.assertEqual(
            set(careers["AI01"]["pham_vi_nguon"]),
            {"muc_luong", "xu_huong_thi_truong"},
        )
        self.assertIn("hết hạn 08/05/2026", careers["AI01"]["muc_luong"])
        self.assertIn("14.335.767 VND/tháng", careers["SY01"]["muc_luong"])
        self.assertIn("13.857.347 VND/tháng", careers["IT01"]["muc_luong"])
        self.assertIn("12.369.709 VND/tháng", careers["GR01"]["muc_luong"])
        self.assertIn("CAGR dự báo 5,0%", careers["GR01"]["xu_huong_thi_truong"])
        self.assertIn("không phải số lượng tin tuyển dụng", careers["GR01"]["xu_huong_thi_truong"])
        from web.ui_kit import career_explorer_card

        self.assertIn(
            "tham khảo, không riêng chức danh này: số tin tuyển dụng IT trên ITviec",
            career_explorer_card(careers["IT01"]),
        )
        self.assertIn(
            "tham khảo, không riêng chức danh này: IT Support",
            career_explorer_card(careers["IT01"]),
        )
        self.assertIn(
            "tham khảo, không riêng chức danh này: Graphic Designer",
            career_explorer_card(careers["GR01"]),
        )

    def test_sqlite_storage_crud(self):
        """Kiểm thử tính năng 1: Ghi nhận và truy vấn dữ liệu từ CSDL SQLite."""
        with tempfile.TemporaryDirectory() as tmp:
            feedback_json = os.path.join(tmp, "feedback.json")
            interactions_json = os.path.join(tmp, "interactions.json")
            logs_jsonl = os.path.join(tmp, "prediction_logs.jsonl")
            with patch.object(db, "DB_PATH", os.path.join(tmp, "test.db")), \
                    patch.object(db, "FEEDBACK_JSON", feedback_json), \
                    patch.object(db, "INTERACTIONS_JSON", interactions_json), \
                    patch.object(db, "LOGS_JSONL", logs_jsonl), \
                    patch.object(feedback_store, "FEEDBACK_PATH", feedback_json), \
                    patch.object(feedback_store, "INTERACTIONS_PATH", interactions_json), \
                    patch.object(monitor_service, "LOGS_FILE", logs_jsonl):
                db.init_db()

                fb = feedback_store.add_feedback(
                    top_group="Dữ liệu & AI",
                    top_prob=0.88,
                    rating=5,
                    liked_careers=["DA01"],
                    disliked_careers=[],
                    comment="Kiểm thử SQLite",
                    scores={"ai": 9.0, "db": 8.5},
                    student_name="Sinh viên Test",
                    survey={"relevance": 4, "usefulness": 5, "explore_intent": "yes"},
                )
                self.assertTrue(fb.get("id"))

                all_fb = db.get_all_feedbacks(limit=10)
                self.assertEqual(len(all_fb), 1)
                saved_feedback = all_fb[0]
                self.assertEqual(saved_feedback["id"], fb["id"])
                self.assertEqual(saved_feedback["survey"]["relevance"], 4)
                self.assertEqual(saved_feedback["survey"]["explore_intent"], "yes")

                log = monitor_service.log_prediction(
                    input_scores={"ai": 9.0, "db": 8.5},
                    top_group="Dữ liệu & AI",
                    top_prob=0.88,
                    model_version="1.0.0",
                    latency_ms=12.5,
                    source="test_suite",
                    is_partial=True,
                )
                self.assertTrue(log.get("request_id"))
                all_logs = db.get_prediction_logs(limit=10)
                self.assertEqual(len(all_logs), 1)
                self.assertEqual(all_logs[0]["request_id"], log["request_id"])

    def test_missing_scores_imputation_and_validation(self):
        """Kiểm thử tính năng 2: Thuật toán Imputation và validation môn khuyết."""
        partial_scores = {
            "Công nghệ web": 9.0,
            "Công nghệ Java": 8.5,
            "Hệ quản trị CSDL": 8.0,
        }

        # Validate thông thường (allow_partial=False) phải từ chối
        valid, msg, _ = validate_input_scores(partial_scores, allow_partial=False)
        self.assertFalse(valid)
        self.assertIn("Thiếu điểm", msg)

        # Validate với allow_partial=True phải thành công và điền đủ 12 môn
        valid_p, msg_p, filled = validate_input_scores(partial_scores, allow_partial=True)
        self.assertTrue(valid_p)
        self.assertEqual(len(filled), 12)
        self.assertEqual(filled["web"], 9.0)
        self.assertEqual(filled["java"], 8.5)
        self.assertEqual(filled["db"], 8.0)

        # Kiểm tra hàm helper impute_missing_scores
        full_s, comp, miss = impute_missing_scores(partial_scores)
        self.assertEqual(len(comp), 3)
        self.assertEqual(len(miss), 9)
        self.assertEqual(len(full_s), 12)

    @unittest.skipUnless(HAS_API, "Cần FastAPI TestClient")
    def test_api_partial_assessment_endpoints(self):
        """Kiểm thử API Endpoint suy luận với dữ liệu thiếu môn."""
        client = TestClient(api_main.app)

        partial_body = {
            "web": 9.5,
            "java": 8.5,
            "csharp": 8.0,
            "db": 8.5,
            "allow_partial": True,
        }

        # 1. Gọi /decision với allow_partial=True
        r = client.post("/decision", json=partial_body)
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertTrue(data.get("is_partial_assessment"))
        self.assertEqual(data.get("completed_subjects_count"), 4)
        self.assertIn("missing_subjects", data)
        self.assertEqual(len(data["missing_subjects"]), 8)

        # Kiểm tra xem trong top_careers có phân tích unstudied_core không
        top_careers = data.get("top_careers", [])
        self.assertGreaterEqual(len(top_careers), 1)
        self.assertIn("explanation", top_careers[0])
        self.assertIn("score_note", top_careers[0]["explanation"])

        # 2. Gọi /decision/partial chuyên dụng
        r_part = client.post("/decision/partial", json={"web": 9.0, "db": 8.5})
        self.assertEqual(r_part.status_code, 200)
        self.assertTrue(r_part.json().get("is_partial_assessment"))

        # 3. Gửi thiếu môn mà KHÔNG bật allow_partial phải bị 422
        r_fail = client.post("/decision", json={"web": 9.0, "db": 8.5, "allow_partial": False})
        self.assertEqual(r_fail.status_code, 422)

    def test_auto_retrain_trigger_and_callback(self):
        """Kiểm thử tính năng 3: Cơ chế đăng ký callback và kiểm tra điều kiện Retrain."""
        reloaded = []

        def dummy_cb():
            reloaded.append(True)

        register_reload_callback(dummy_cb)
        notify_model_reloaded()
        self.assertIn(True, reloaded)

        # Kiểm tra check_and_trigger_auto_retrain khi chưa đủ feedback
        status_info = check_and_trigger_auto_retrain(min_feedback_count=999, force=False)
        self.assertIn(status_info.get("status"), ["waiting", "skipped", "error"])


if __name__ == "__main__":
    unittest.main()
