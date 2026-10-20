# -*- coding: utf-8 -*-
"""
Kiểm thử parser bảng điểm, đầu vào bất thường, chỉ số và đường dẫn.
Chạy: python -m unittest discover -s tests -v
"""
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
import warnings
from unittest.mock import patch

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
warnings.filterwarnings("ignore")

try:
    from fastapi.testclient import TestClient
    HAS_FASTAPI = True
except Exception:
    HAS_FASTAPI = False

KEYS = ["sec", "se", "linux", "db", "graphics", "network", "analysis", "image", "java", "csharp", "web", "ai"]
BASE_JSON = "{" + ", ".join(f'"{k}": 6.5' for k in KEYS) + "}"


@unittest.skipUnless(HAS_FASTAPI, "cần fastapi + httpx")
class TestApiHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["GROQ_API_KEY"] = ""
        import api.main as api_main
        cls.client = TestClient(api_main.app)

    def _post(self, body: str):
        return self.client.post("/decision", content=body, headers={"Content-Type": "application/json"})

    def test_nan_and_infinity_rejected_with_422_not_500(self):
        for bad in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(value=bad):
                r = self._post(BASE_JSON.replace('"ai": 6.5', f'"ai": {bad}'))
                self.assertEqual(r.status_code, 422, r.text[:200])

    def test_boolean_score_rejected(self):
        r = self._post(BASE_JSON.replace('"ai": 6.5', '"ai": true'))
        self.assertEqual(r.status_code, 422)

    def test_overlong_name_rejected_and_input_not_echoed(self):
        r = self._post(BASE_JSON[:-1] + ', "student_name": "' + "x" * 5000 + '"}')
        self.assertEqual(r.status_code, 422)
        self.assertLess(len(r.text), 1000, "phản hồi lỗi không được phản chiếu lại input dài")

    def test_boundaries_accepted(self):
        for v in ("0.0", "10.0"):
            r = self.client.post("/predict", json={k: float(v) for k in KEYS})
            self.assertEqual(r.status_code, 200, v)

    def test_feedback_survey_is_saved_and_updates_recommender(self):
        from career_ai import feedback_store
        import api.main as api_main

        career_id = api_main.recommender.career_ids[0]
        with tempfile.TemporaryDirectory() as tmp:
            feedback_path = os.path.join(tmp, "feedback.json")
            with patch.object(feedback_store, "FEEDBACK_PATH", feedback_path), \
                    patch.object(api_main.recommender, "feedback_json_path", feedback_path), \
                    patch.object(feedback_store.db, "insert_feedback", side_effect=lambda record: record):
                response = self.client.post("/feedback", json={
                    "career_id": career_id,
                    "top_group": api_main.CAREER_GROUP_LIST[0],
                    "top_prob": 0.75,
                    "liked": True,
                    "scores": {"sec": 8.0},
                    "survey": {
                        "relevance": 4,
                        "usefulness": 5,
                        "explore_intent": "yes",
                    },
                })
                self.assertEqual(response.status_code, 201, response.text)
                with open(feedback_path, encoding="utf-8") as file:
                    records = json.load(file)
                self.assertEqual(records[0]["liked_careers"], [career_id])
                self.assertEqual(records[0]["scores"], {})
                self.assertEqual(records[0]["student_name"], "Sinh viên")
                self.assertEqual(records[0]["survey"]["relevance"], 4)
                self.assertEqual(records[0]["survey"]["explore_intent"], "yes")
                self.assertEqual(api_main.recommender.career_net_likes[career_id], 1)
        api_main.recommender.reload()

    def test_feedback_scores_are_saved_only_with_explicit_consent(self):
        from career_ai import feedback_store
        import api.main as api_main

        career_id = api_main.recommender.career_ids[0]
        with tempfile.TemporaryDirectory() as tmp:
            feedback_path = os.path.join(tmp, "feedback.json")
            with patch.object(feedback_store, "FEEDBACK_PATH", feedback_path), \
                    patch.object(api_main.recommender, "feedback_json_path", feedback_path), \
                    patch.object(feedback_store.db, "insert_feedback", side_effect=lambda record: record):
                response = self.client.post("/feedback", json={
                    "career_id": career_id,
                    "top_group": api_main.CAREER_GROUP_LIST[0],
                    "top_prob": 0.75,
                    "liked": True,
                    "scores": {"sec": 8.0},
                    "include_scores": True,
                })
                self.assertEqual(response.status_code, 201, response.text)
                with open(feedback_path, encoding="utf-8") as file:
                    records = json.load(file)
                self.assertEqual(records[0]["scores"], {"sec": 8.0})
                self.assertEqual(records[0]["student_name"], "Sinh viên")
        api_main.recommender.reload()

    def test_feedback_database_failure_returns_error_without_json_success_record(self):
        from career_ai import feedback_store
        import api.main as api_main

        career_id = api_main.recommender.career_ids[0]
        with tempfile.TemporaryDirectory() as tmp:
            feedback_path = os.path.join(tmp, "feedback.json")
            with patch.object(feedback_store, "FEEDBACK_PATH", feedback_path), \
                    patch.object(api_main.recommender, "feedback_json_path", feedback_path), \
                    patch.object(feedback_store.db, "insert_feedback", side_effect=sqlite3.OperationalError("disk full")), \
                    patch.object(api_main.recommender, "reload"):
                response = self.client.post("/feedback", json={
                    "career_id": career_id,
                    "top_group": api_main.CAREER_GROUP_LIST[0],
                    "top_prob": 0.75,
                    "liked": True,
                })
            self.assertEqual(response.status_code, 500)
            self.assertFalse(os.path.exists(feedback_path))

    def test_prediction_logs_omit_scores_without_opt_in(self):
        import api.main as api_main

        logged = {}

        def capture_log(**record):
            logged.update(record)

        with patch.object(api_main, "log_prediction", side_effect=capture_log):
            response = self.client.post("/decision", json={"scores": {key: 6.5 for key in KEYS}})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(logged["input_scores"], {})

    def test_admin_can_delete_a_feedback_record(self):
        from career_ai import feedback_store
        import api.main as api_main

        feedback_id = "feedback-to-delete"
        with tempfile.TemporaryDirectory() as tmp:
            feedback_path = os.path.join(tmp, "feedback.json")
            with open(feedback_path, "w", encoding="utf-8") as file:
                json.dump([{"id": feedback_id}], file)
            with patch.object(feedback_store, "FEEDBACK_PATH", feedback_path), \
                    patch.object(feedback_store.db, "delete_feedback", return_value=True), \
                    patch.object(api_main, "rebuild_feedback_training_data"), \
                    patch.object(api_main.recommender, "reload"):
                with patch.dict(os.environ, {"ADMIN_USERNAME": "test-admin", "ADMIN_PASSWORD": "test-secret"}):
                    response = self.client.delete(
                        f"/admin/feedbacks/{feedback_id}",
                        auth=("test-admin", "test-secret"),
                    )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertTrue(response.json()["mirror_synced"])
                self.assertTrue(response.json()["training_data_synced"])
                self.assertTrue(response.json()["recommender_updated"])
                with open(feedback_path, encoding="utf-8") as file:
                    self.assertEqual(json.load(file), [])

    def test_feedback_rejects_out_of_range_survey_scores(self):
        import api.main as api_main

        response = self.client.post("/feedback", json={
            "career_id": api_main.recommender.career_ids[0],
            "top_group": api_main.CAREER_GROUP_LIST[0],
            "top_prob": 0.75,
            "liked": True,
            "survey": {"relevance": 6},
        })
        self.assertEqual(response.status_code, 422)

    def test_admin_stats_include_distinct_student_survey_metrics(self):
        with patch.dict(os.environ, {"ADMIN_USERNAME": "test-admin", "ADMIN_PASSWORD": "test-secret"}):
            response = self.client.get(
                "/admin/stats", auth=("test-admin", "test-secret")
            )
        self.assertEqual(response.status_code, 200, response.text)
        survey = response.json()["student_survey"]
        self.assertIn("response_count", survey)
        self.assertIn("average_relevance", survey)
        self.assertIn("average_usefulness", survey)
        self.assertEqual(survey["minimum_recommended_sample"], 20)

    def test_admin_and_retrain_routes_reject_unauthenticated_requests(self):
        import api.main as api_main

        with patch.dict(os.environ, {"ADMIN_USERNAME": "test-admin", "ADMIN_PASSWORD": "test-secret"}), \
                patch.object(api_main, "check_and_trigger_auto_retrain") as retrain:
            requests = (
                ("get", "/admin/auth"),
                ("get", "/admin/stats"),
                ("get", "/admin/feedbacks"),
                ("get", "/admin/logs"),
                ("post", "/retrain?force=true"),
            )
            for method, path in requests:
                with self.subTest(path=path):
                    response = getattr(self.client, method)(path)
                    self.assertEqual(response.status_code, 401, response.text)
                    self.assertEqual(response.headers.get("www-authenticate"), "Basic")
            retrain.assert_not_called()

    def test_admin_and_retrain_routes_accept_configured_credentials(self):
        import api.main as api_main

        with patch.dict(os.environ, {"ADMIN_USERNAME": "test-admin", "ADMIN_PASSWORD": "test-secret"}), \
                patch.object(api_main, "check_and_trigger_auto_retrain", return_value={"retrained": False}) as retrain:
            invalid = self.client.get(
                "/admin/auth", auth=("test-admin", "wrong-secret")
            )
            self.assertEqual(invalid.status_code, 401)

            for path in ("/admin/auth", "/admin/stats", "/admin/feedbacks", "/admin/logs"):
                with self.subTest(path=path):
                    response = self.client.get(path, auth=("test-admin", "test-secret"))
                    self.assertEqual(response.status_code, 200, response.text)

            response = self.client.post(
                "/retrain?force=true", auth=("test-admin", "test-secret")
            )
            self.assertEqual(response.status_code, 200, response.text)
            retrain.assert_called_once_with(min_feedback_count=5, force=True)

    def test_admin_routes_fail_closed_when_credentials_are_not_configured(self):
        import api.main as api_main

        with patch.dict(os.environ, {"ADMIN_USERNAME": "", "ADMIN_PASSWORD": ""}), \
                patch.object(api_main, "check_and_trigger_auto_retrain") as retrain:
            for method, path in (
                ("get", "/admin/auth"),
                ("get", "/admin/stats"),
                ("get", "/admin/feedbacks"),
                ("get", "/admin/logs"),
                ("post", "/retrain"),
            ):
                with self.subTest(path=path):
                    response = getattr(self.client, method)(path)
                    self.assertEqual(response.status_code, 503, response.text)
            retrain.assert_not_called()

    def test_feedback_validation_uses_only_complete_user_confirmations(self):
        from career_ai.domain_knowledge import CAREER_GROUPS, SUBJECTS
        from career_ai.train import validate_on_feedback
        from unittest.mock import Mock

        feedbacks = [
            {
                "scores": {subject: 7.0 for subject in SUBJECTS},
                "liked_careers": ["confirmed"],
            },
            {
                "scores": {"Trí tuệ nhân tạo": 7.0},
                "liked_careers": ["confirmed"],
            },
            {
                "scores": {subject: 7.0 for subject in SUBJECTS},
                "liked_careers": ["not-in-catalog"],
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            feedback_path = os.path.join(tmp, "feedback.json")
            careers_path = os.path.join(tmp, "careers.json")
            with open(feedback_path, "w", encoding="utf-8") as file:
                json.dump(feedbacks, file)
            with open(careers_path, "w", encoding="utf-8") as file:
                json.dump({"confirmed": {"career_group": CAREER_GROUPS[0]}}, file)

            pipeline = Mock()
            pipeline.classes_ = CAREER_GROUPS
            pipeline.predict_proba.return_value = [[1.0] + [0.0] * (len(CAREER_GROUPS) - 1)]
            result = validate_on_feedback(pipeline, feedback_path, careers_path)

        self.assertEqual(result, {"n": 1, "top1": 1, "top3": 1})
        pipeline.predict_proba.assert_called_once()

    def test_feedback_validation_reports_insufficient_sample_without_accuracy_claim(self):
        from io import StringIO
        from career_ai.train import MIN_FEEDBACK_FOR_VALIDATION, print_feedback_validation

        report = StringIO()
        with patch("sys.stdout", report):
            print_feedback_validation({"n": MIN_FEEDBACK_FOR_VALIDATION - 1, "top1": 0, "top3": 0})

        self.assertIn("Chưa đủ phản hồi để kết luận", report.getvalue())
        self.assertIn(str(MIN_FEEDBACK_FOR_VALIDATION), report.getvalue())
        self.assertNotIn("Top-1:", report.getvalue())

    def test_feedback_validation_reports_top1_and_top3_after_minimum_sample(self):
        from io import StringIO
        from career_ai.train import MIN_FEEDBACK_FOR_VALIDATION, print_feedback_validation

        report = StringIO()
        with patch("sys.stdout", report):
            print_feedback_validation({
                "n": MIN_FEEDBACK_FOR_VALIDATION,
                "top1": 15,
                "top3": 18,
            })

        self.assertIn(f"Số phản hồi hợp lệ: {MIN_FEEDBACK_FOR_VALIDATION}", report.getvalue())
        self.assertIn("Top-1: 75.0%", report.getvalue())
        self.assertIn("Top-3: 90.0%", report.getvalue())

    def test_feedback_rejects_unknown_career(self):
        response = self.client.post("/feedback", json={
            "career_id": "unknown-career",
            "top_group": "Dữ liệu & AI",
            "top_prob": 0.75,
            "liked": True,
        })
        self.assertEqual(response.status_code, 422)

    def test_llm_explanation_cannot_change_recommendation_ranking(self):
        import api.main as api_main

        llm_results = [
            {
                "explanation": "Tư vấn theo đúng dữ liệu đầu vào.",
                "is_ai_generated": True,
                "model_used": "test",
                "note": "",
                "disclaimer": "",
            },
            {
                "explanation": "Hãy chọn một nghề khác hoàn toàn.",
                "is_ai_generated": True,
                "model_used": "test",
                "note": "",
                "disclaimer": "",
            },
        ]
        with patch.object(api_main, "log_prediction"), \
                patch.object(api_main, "explain_with_llm", side_effect=llm_results):
            first = self.client.post("/decision", json={"scores": {key: 6.5 for key in KEYS}})
            second = self.client.post("/decision", json={"scores": {key: 6.5 for key in KEYS}})

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        first_body, second_body = first.json(), second.json()
        self.assertEqual(first_body["predicted_group"], second_body["predicted_group"])
        self.assertEqual(first_body["top_careers"], second_body["top_careers"])
        self.assertNotEqual(
            first_body["explanation_llm"]["explanation"],
            second_body["explanation_llm"]["explanation"],
        )


class TestUploadParsing(unittest.TestCase):
    def test_parse_uploaded_scores_handles_horizontal_and_vertical_excel_rows(self):
        import web.app as web_app

        subject_names = [
            "An toàn và bảo mật HTTT",
            "Công nghệ phần mềm",
            "Hệ điều hành Linux",
            "Hệ quản trị CSDL",
            "Kỹ thuật đồ hoạ máy tính",
            "Mạng máy tính",
            "Phân tích thiết kế HTTT",
            "Xử lý ảnh",
            "Công nghệ Java",
            "Ngôn ngữ C# và công nghệ .NET",
            "Công nghệ web",
            "Trí tuệ nhân tạo",
        ]
        subject_keys = {
            "An toàn và bảo mật HTTT": "sec",
            "Công nghệ phần mềm": "se",
            "Hệ điều hành Linux": "linux",
            "Hệ quản trị CSDL": "db",
            "Kỹ thuật đồ hoạ máy tính": "graphics",
            "Mạng máy tính": "network",
            "Phân tích thiết kế HTTT": "analysis",
            "Xử lý ảnh": "image",
            "Công nghệ Java": "java",
            "Ngôn ngữ C# và công nghệ .NET": "csharp",
            "Công nghệ web": "web",
            "Trí tuệ nhân tạo": "ai",
        }

        horizontal = pd.DataFrame([
            [8.0, 7.5, 9.0, 6.5, 7.0, 8.5, 7.8, 6.2, 9.3, 8.1, 8.8, 9.1]
        ], columns=list(subject_keys.values()))
        vertical = pd.DataFrame([
            ["An toàn và bảo mật HTTT", 8.0],
            ["Công nghệ phần mềm", 7.5],
            ["Hệ điều hành Linux", 9.0],
            ["Hệ quản trị CSDL", 6.5],
            ["Kỹ thuật đồ hoạ máy tính", 7.0],
            ["Mạng máy tính", 8.5],
            ["Phân tích thiết kế HTTT", 7.8],
            ["Xử lý ảnh", 6.2],
            ["Công nghệ Java", 9.3],
            ["Ngôn ngữ C# và công nghệ .NET", 8.1],
            ["Công nghệ web", 8.8],
            ["Trí tuệ nhân tạo", 9.1],
        ], columns=["Tên môn", "Điểm TBCHP"])

        self.assertEqual(len(web_app.parse_uploaded_scores(horizontal, subject_names, subject_keys)), 12)
        self.assertEqual(len(web_app.parse_uploaded_scores(vertical, subject_names, subject_keys)), 12)

    def test_parse_uploaded_workbook_with_title_row_course_codes_and_final_grade(self):
        import web.app as web_app

        subject_names = [
            "An toàn và bảo mật HTTT", "Công nghệ phần mềm", "Hệ điều hành Linux",
            "Hệ quản trị CSDL", "Kỹ thuật đồ hoạ máy tính", "Mạng máy tính",
            "Phân tích thiết kế HTTT", "Xử lý ảnh", "Công nghệ Java",
            "Ngôn ngữ C# và công nghệ .NET", "Công nghệ web", "Trí tuệ nhân tạo",
        ]
        subject_keys = {
            "An toàn và bảo mật HTTT": "sec", "Công nghệ phần mềm": "se",
            "Hệ điều hành Linux": "linux", "Hệ quản trị CSDL": "db",
            "Kỹ thuật đồ hoạ máy tính": "graphics", "Mạng máy tính": "network",
            "Phân tích thiết kế HTTT": "analysis", "Xử lý ảnh": "image",
            "Công nghệ Java": "java", "Ngôn ngữ C# và công nghệ .NET": "csharp",
            "Công nghệ web": "web", "Trí tuệ nhân tạo": "ai",
        }
        course_codes = [
            "TH 5210", "TH 4306", "TH 5211", "TH 5221", "TH 5231", "TH 5206",
            "TH 5208", "TH 5209", "TH 4316", "TH 4315", "TH 4309", "TH 4320",
        ]
        workbook = io.BytesIO()
        with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
            pd.DataFrame([
                ["BẢNG ĐIỂM SINH VIÊN"],
                ["Mã học phần", "Tên học phần", "Số tín chỉ", "Điểm quá trình", "Điểm tổng kết"],
                *[
                    [code, subject, 3, 5.0, 7.0 + index / 10]
                    for index, (code, subject) in enumerate(zip(course_codes, subject_names))
                ],
            ]).to_excel(writer, sheet_name="Bảng điểm", header=False, index=False)
        workbook.seek(0)

        parsed, columns = web_app.parse_uploaded_file(
            workbook, "bang_diem.xlsx", subject_names, subject_keys
        )

        self.assertEqual(len(parsed), 12)
        self.assertEqual(columns, 5)
        self.assertEqual(parsed["sec"], 7.0)
        self.assertEqual(parsed["ai"], 8.1)


class TestOptionalGradeInputs(unittest.TestCase):
    def test_upload_prefills_optional_grades_and_partial_payload(self):
        from streamlit.testing.v1 import AppTest
        import web.app as web_app

        keys = [
            "network", "linux", "sec", "db", "analysis", "se",
            "java", "csharp", "graphics", "web", "ai", "image",
        ]
        names = [f"Môn {key}" for key in keys]
        meta = {
            "subject_names": names,
            "subject_keys": dict(zip(names, keys)),
            "key_to_subject": dict(zip(keys, names)),
            "soft_skills": [],
            "skill_levels": [],
            "interest_options": [],
        }
        original_fetch = web_app.fetch_model_info
        original_post = web_app.requests.post
        captured_payload = {}

        class ValidationResponse:
            status_code = 422

            @staticmethod
            def json():
                return {"detail": "test validation response"}

        def capture_post(url, json, timeout):
            self.assertTrue(url.endswith("/decision"))
            self.assertEqual(timeout, 25)
            captured_payload.update(json)
            return ValidationResponse()

        web_app.fetch_model_info = lambda: (meta, None)
        web_app.requests.post = capture_post
        try:
            test_app = AppTest.from_string(
                "import web.app as app_module\napp_module.main()",
                default_timeout=10,
            )
            test_app.session_state["pending_file_scores"] = {"se": 8.5, "db": 7.0}
            test_app.session_state["select_academic_year"] = "Năm 4"
            test_app.run()

            self.assertFalse(test_app.exception, test_app.exception)
            self.assertEqual(len(test_app.checkbox), 1)
            self.assertIn("Cho phép lưu điểm môn học", test_app.checkbox[0].label)
            self.assertEqual(test_app.radio[0].value, "Năm 4")
            self.assertEqual(test_app.radio[0].options, ["Năm 1", "Năm 2", "Năm 3", "Năm 4"])
            self.assertIn("Chọn một hoặc vài lĩnh vực", test_app.multiselect[0].placeholder)
            grades = {widget.key: widget.value for widget in test_app.number_input}
            self.assertEqual(grades["grade_input_se"], 8.5)
            self.assertEqual(grades["grade_input_db"], 7.0)
            self.assertTrue(
                all(
                    grades[f"grade_input_{key}"] is None
                    for key in keys
                    if key not in {"se", "db"}
                )
            )

            next(
                button for button in test_app.button
                if button.label.startswith("Khám phá hướng đi phù hợp")
            ).click().run()
            self.assertEqual(captured_payload["scores"], {"se": 8.5, "db": 7.0})
            self.assertTrue(captured_payload["allow_partial"])
            self.assertFalse(captured_payload["store_scores_in_logs"])
            self.assertNotIn("student_name", captured_payload)
        finally:
            web_app.fetch_model_info = original_fetch
            web_app.requests.post = original_post


class TestStudentSurveyUI(unittest.TestCase):
    def test_survey_questions_render_without_preselected_answers(self):
        from streamlit.testing.v1 import AppTest

        result = {
            "data": {
                "predicted_group": "Dữ liệu & AI",
                "confidence": 75.0,
                "top_careers": [{
                    "career_id": "DA01",
                    "career_name": "Chuyên viên dữ liệu",
                    "career_group": "Dữ liệu & AI",
                    "description": "Phân tích dữ liệu.",
                    "salary": "Tham khảo",
                    "trend": "Ổn định",
                    "match_percentage": 80.0,
                }],
                "probabilities": {"Dữ liệu & AI": 75.0},
                "strengths": [],
                "improvements": [],
                "explanation_llm": {
                    "explanation": "Gợi ý tham khảo.",
                    "note": "Nội dung minh họa.",
                    "is_ai_generated": False,
                },
                "disclaimer": "Gợi ý tham khảo.",
            },
            "scores": {"ai": 8.0},
        }
        test_app = AppTest.from_string(
            "from web.app import render_results\n"
            f"render_results({result!r})",
            default_timeout=10,
        ).run()

        self.assertFalse(test_app.exception, test_app.exception)
        survey_questions = [
            widget for widget in test_app.selectbox
            if widget.label.startswith(("Gợi ý phù hợp", "Kết quả hữu ích", "Bạn có dự định"))
        ]
        self.assertEqual(len(survey_questions), 3)
        self.assertTrue(all(widget.value == "Chưa trả lời" for widget in survey_questions))
        self.assertEqual(len(test_app.slider), 0)
        star_buttons = [
            button for button in test_app.button
            if button.key in {f"fb_rating_star_{value}" for value in range(1, 6)}
        ]
        self.assertEqual(len(star_buttons), 5)
        self.assertEqual(test_app.session_state["fb_rating"], 0)
        self.assertEqual([button.label for button in star_buttons], ["☆"] * 5)

        next(button for button in star_buttons if button.key == "fb_rating_star_3").click().run()
        self.assertFalse(test_app.exception, test_app.exception)
        self.assertEqual(test_app.session_state["fb_rating"], 3)
        self.assertNotIn("3/5 sao", " ".join(element.value for element in test_app.caption))
        star_buttons = [
            button for button in test_app.button
            if button.key in {f"fb_rating_star_{value}" for value in range(1, 6)}
        ]
        self.assertEqual(
            [button.label for button in star_buttons],
            ["★", "★", "★", "☆", "☆"],
        )
        from web import ui_kit
        self.assertIn("font-size: 1.35rem", ui_kit.CSS)
        self.assertIn("border: 0 !important", ui_kit.CSS)
        self.assertIn("st-key-fb_submit", ui_kit.CSS)
        self.assertIsNone(test_app.session_state.get("fb_liked"))

        next(button for button in test_app.button if button.key == "fb_like").click().run()
        self.assertFalse(test_app.exception, test_app.exception)
        self.assertIs(test_app.session_state["fb_liked"], True)
        self.assertIn("fb_submit", [button.key for button in test_app.button])

    def test_admin_login_is_available_from_sidebar(self):
        from streamlit.testing.v1 import AppTest
        from web import app as web_app

        with patch.object(web_app, "fetch_model_info", return_value=(None, "API unavailable")):
            test_app = AppTest.from_string(
                "from web.app import main\nmain()",
                default_timeout=10,
            ).run()

        self.assertFalse(test_app.exception, test_app.exception)
        self.assertIn("btn_goto_admin_login", [button.key for button in test_app.button])
        self.assertIn("btn_student_home", [button.key for button in test_app.button])
        self.assertNotIn("btn_header_admin", [button.key for button in test_app.button])
        self.assertNotIn("Quản trị viên", [button.label for button in test_app.button])
        self.assertNotIn("btn_reset_scores", [button.key for button in test_app.button])
        self.assertNotIn("Sẵn sàng đồng hành", " ".join(element.value for element in test_app.markdown))
        self.assertNotIn("Chỉ với 3 bước", " ".join(element.value for element in test_app.markdown))
        next(button for button in test_app.button if button.key == "btn_goto_admin_login").click().run()
        self.assertEqual(test_app.session_state["view_mode"], "admin")
        self.assertIn("btn_admin_login_home", [button.key for button in test_app.button])
        self.assertIn("admin-login-card", web_app.ui.CSS)
        self.assertIn('content: "☰"', web_app.ui.CSS)
        self.assertIn(".st-key-sidebar-sticky-top", web_app.ui.CSS)
        self.assertNotIn(
            "Thông tin đăng nhập được máy chủ API xác thực an toàn",
            " ".join(element.value for element in test_app.markdown),
        )
        self.assertNotIn(
            "login-lock-badge",
            " ".join(element.value for element in test_app.markdown),
        )
        self.assertIn("background: transparent !important", web_app.ui.CSS)
        next(button for button in test_app.button if button.key == "btn_admin_login_home").click().run()
        self.assertEqual(test_app.session_state["view_mode"], "student")
        self.assertIn("btn_goto_admin_login", [button.key for button in test_app.button])

    def test_explore_group_shows_all_career_details(self):
        from streamlit.testing.v1 import AppTest
        from web import app as web_app

        catalog = [
            {
                "career_id": "AI01",
                "career_group": "Dữ liệu & AI",
                "career_name": "Chuyên viên dữ liệu",
                "mo_ta": "Phân tích dữ liệu và xây dựng báo cáo.",
                "muc_luong": "Chưa có dữ liệu được xác thực.",
                "xu_huong_thi_truong": "Đang tăng nhu cầu.",
                "khu_vuc": "Hà Nội",
                "nguon_du_lieu": "Nguồn thử nghiệm",
                "ngay_kiem_tra": "2026-10-14",
                "nguon_tham_khao": [],
            },
            {
                "career_id": "AI02",
                "career_group": "Dữ liệu & AI",
                "career_name": "Kỹ sư học máy",
                "mo_ta": "Phát triển ứng dụng học máy.",
                "muc_luong": "Chưa có dữ liệu được xác thực.",
                "xu_huong_thi_truong": "Đang tăng nhu cầu.",
                "khu_vuc": "Hà Nội",
                "nguon_du_lieu": "Nguồn thử nghiệm",
                "ngay_kiem_tra": "2026-10-14",
                "nguon_tham_khao": [],
            },
        ]
        with (
            patch.object(web_app, "fetch_model_info", return_value=(None, "API unavailable")),
            patch.object(web_app, "_load_career_catalog", return_value=catalog),
        ):
            test_app = AppTest.from_string(
                "from web.app import main\nmain()",
                default_timeout=10,
            ).run()
            explore_button = next(
                button for button in test_app.button
                if button.label == "Dữ liệu & AI"
            )
            explore_button.click().run()

        self.assertFalse(test_app.exception, test_app.exception)
        rendered = " ".join(element.value for element in test_app.markdown)
        self.assertIn("Chuyên viên dữ liệu", rendered)
        self.assertIn("Kỹ sư học máy", rendered)
        self.assertIn("Phân tích dữ liệu và xây dựng báo cáo.", rendered)
        self.assertIn("Mức lương tham khảo", rendered)
        self.assertIn("Xu hướng thị trường", rendered)
        self.assertIn("btn_student_home", [button.key for button in test_app.button])
        self.assertNotIn("btn_back_from_career_explorer", [button.key for button in test_app.button])
        next(button for button in test_app.button if button.key == "btn_student_home").click().run()
        self.assertIsNone(test_app.session_state["explore_career_group"])
        self.assertIn("Khám phá thử", " ".join(element.value for element in test_app.markdown))

    def test_optional_survey_answers_are_sent_with_feedback(self):
        from types import SimpleNamespace
        from web import app as web_app

        with patch.object(
            web_app.requests,
            "post",
            return_value=SimpleNamespace(
                status_code=201,
                json=lambda: {"status": "saved", "recommender_updated": True},
            ),
        ) as post:
            web_app._send_feedback(
                {"predicted_group": "Dữ liệu & AI", "confidence": 0.75},
                [{"career_id": "DA01"}],
                liked=True,
                survey={
                    "relevance": 4,
                    "usefulness": 5,
                    "explore_intent": "yes",
                },
            )

        self.assertEqual(
            post.call_args.kwargs["json"]["survey"],
            {"relevance": 4, "usefulness": 5, "explore_intent": "yes"},
        )


class TestStudentFacingCopy(unittest.TestCase):
    def test_render_api_persists_mutable_data_on_disk(self):
        with open(os.path.join(ROOT, "render.yaml"), encoding="utf-8") as file:
            render_config = file.read()
        self.assertIn("mountPath: /var/data", render_config)
        self.assertIn("CAREER_AI_DATA_DIR", render_config)
        self.assertIn("value: /var/data", render_config)

    def test_streamlit_uses_current_width_parameter(self):
        from web import app as web_app

        with open(web_app.__file__, encoding="utf-8") as file:
            source = file.read()
        self.assertNotIn("use_container_width", source)

    def test_career_guidance_uses_plain_language(self):
        from web import ui_kit

        student_copy = " ".join(
            [
                ui_kit.hero("Minh Anh"),
                ui_kit.result_hero(
                    "Phát triển Web", 72.0, "Chuyên viên dữ liệu", 81.0, True,
                    "Minh Anh", score_based_group="Dữ liệu & AI",
                ),
                ui_kit.prob_bars({"Dữ liệu & AI": 72.0}),
                ui_kit.explain_card("Một gợi ý tham khảo.", "", True, "Kết quả mang tính tham khảo."),
                ui_kit.career_grid([{"career_name": "Chuyên viên dữ liệu", "match_percentage": 81.0}]),
            ]
        )

        for technical_term in (
            "Machine Learning",
            "Groq",
            "Content-Based Filtering",
            "xác suất",
            "Thuật toán",
            "Model",
            "điểm xếp hạng",
            "hiệu chuẩn",
            "cross-validation",
        ):
            self.assertNotIn(technical_term, student_copy)

        for friendly_label in (
            "Tìm hướng đi phù hợp với bạn",
            "Gợi ý theo điểm môn học",
            "Gợi ý sau khi cân nhắc sở thích",
            "Các nhóm ngành được gợi ý theo điểm môn học",
            "Mức dự đoán 72.0%",
            "Góc nhìn dành riêng cho bạn",
            "Gợi ý nổi bật",
        ):
            self.assertIn(friendly_label, student_copy)
        self.assertIn("Dữ liệu &amp; AI", student_copy)
        self.assertIn("Phát triển Web", student_copy)
        self.assertIn("không cho biết mức độ phù hợp hay khả năng thành công ngoài thực tế", student_copy)

    def test_admin_status_card_uses_plain_language(self):
        from web import ui_kit

        status = ui_kit.status_card(True, "1.2.3", "https://api.example.com")
        self.assertIn("Hệ thống đang hoạt động", status)
        self.assertIn("Phiên bản hệ thống", status)
        for technical_term in ("Thuật toán", "F1", "Model", "độ chính xác"):
            self.assertNotIn(technical_term, status)

    def test_career_card_links_only_https_source_urls(self):
        from web import ui_kit

        linked_card = ui_kit.career_grid([{
            "career_name": "Backend",
            "source": "ITviec",
            "sources": [{
                "ten": "ITviec salary report",
                "url": "https://example.com/report?a=1&b=2",
                "ky_du_lieu": "2025",
                "pham_vi": ["muc_luong"],
            }],
            "source_reviewed_at": "2026-10-14",
        }])
        self.assertIn("ITviec salary report", linked_card)
        self.assertIn("rel='noopener noreferrer'", linked_card)
        self.assertIn("Rà soát 2026-10-14", linked_card)
        self.assertIn("(lương)", linked_card)
        self.assertNotIn("(lương, 2025)", linked_card)
        self.assertIn("&amp;", linked_card)

        unsafe_card = ui_kit.career_grid([{
            "career_name": "Backend",
            "source_url": "javascript:alert(1)",
        }])
        self.assertNotIn("javascript:", unsafe_card)
        self.assertNotIn("Xem nguồn", unsafe_card)

    def test_career_card_warns_when_market_sources_are_not_recently_reviewed(self):
        from datetime import date
        from web import ui_kit

        status, is_recent = ui_kit.market_source_status(
            "2024-01-01", today=date(2026, 10, 15)
        )
        self.assertFalse(is_recent)
        self.assertIn("có thể đã cũ", status)

        missing_status, missing_is_recent = ui_kit.market_source_status(
            "", today=date(2026, 10, 15)
        )
        self.assertFalse(missing_is_recent)
        self.assertIn("Chưa có ngày rà soát", missing_status)

        card = ui_kit.career_grid([{
            "career_name": "Backend",
            "source_reviewed_at": "2024-01-01",
        }])
        self.assertIn("Nguồn có thể đã cũ", card)

    def test_feedback_panel_has_no_decorative_icons(self):
        from web import app as web_app
        from web import ui_kit

        with open(web_app.__file__, encoding="utf-8") as file:
            source = file.read()
        feedback_section = source.split("# Phản hồi từ sinh viên", 1)[1].split(
            "def _send_feedback", 1
        )[0]

        for decorative_icon in ("💬", "👍", "👎", "⭐"):
            self.assertNotIn(decorative_icon, feedback_section)
        for label in ("Gợi ý này có phù hợp với bạn?", "Phù hợp với mình", "Chưa phù hợp"):
            self.assertIn(label, feedback_section)
        self.assertIn(".st-key-feedback-panel", ui_kit.CSS)

    def test_subject_group_headers_have_no_decorative_icons(self):
        from web import ui_kit

        header = ui_kit.category_badge("Mạng & Hệ Thống", "Hạ tầng & An toàn thông tin", "sys")
        self.assertIn("Mạng &amp; Hệ Thống", header)
        self.assertIn("Hạ tầng &amp; An toàn thông tin", header)
        self.assertNotIn("🏛", header)
        self.assertNotIn("💾", header)


class TestConfig(unittest.TestCase):
    def test_env_example_has_no_secret_and_uses_groq_config(self):
        with open(os.path.join(ROOT, ".env.example"), encoding="utf-8") as file:
            values = dict(
                line.split("=", 1)
                for line in file
                if "=" in line and not line.lstrip().startswith("#")
            )
        self.assertEqual(values.get("GROQ_API_KEY", "").strip(), "")
        self.assertEqual(values.get("GROQ_MODEL", "").strip(), "openai/gpt-oss-120b")
        self.assertNotIn("OPENAI_API_KEY", values)
        self.assertNotIn("GEMINI_API_KEY", values)

    def test_unmeasured_metric_stays_none(self):
        from career_ai.model_exporter import _metric
        self.assertIsNone(_metric(None))
        self.assertEqual(_metric(0.123456), 0.1235)

    def test_default_data_paths_are_absolute(self):
        import inspect
        from career_ai.cbf_recommender import ContentBasedFilteringRecommender as C
        for name, p in inspect.signature(C.__init__).parameters.items():
            if name.endswith("_path"):
                self.assertTrue(os.path.isabs(p.default), f"{name} phải là đường dẫn tuyệt đối")

    def test_render_yaml_uses_hostport_for_api_url(self):
        src = open(os.path.join(ROOT, "render.yaml"), encoding="utf-8").read()
        self.assertIn("property: hostport", src)


if __name__ == "__main__":
    unittest.main()
