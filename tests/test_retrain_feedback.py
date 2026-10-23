import json
import os
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from career_ai import retrain_service
from career_ai.domain_knowledge import (
    LABEL_DERIVED,
    LABEL_SOURCE_COL,
    SUBJECT_KEYS,
    SUBJECTS,
)


class TestRetrainFeedback(unittest.TestCase):
    def test_feedback_rows_require_complete_valid_scores(self):
        feedback = {
            "scores": {
                SUBJECT_KEYS[subject]: 7.5
                for subject in SUBJECTS[:-1]
            },
            "liked_careers": ["C1"],
        }

        rows = retrain_service._feedback_training_rows(
            [feedback],
            {"C1": {"career_group": "Test Group"}},
        )

        self.assertEqual(rows, [])

    def test_retraining_reports_when_all_feedback_is_already_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            feedback_path = os.path.join(tmp, "feedback.json")
            careers_path = os.path.join(tmp, "careers.json")
            students_path = os.path.join(tmp, "students.csv")
            scores = {SUBJECT_KEYS[subject]: 7.5 for subject in SUBJECTS}
            feedbacks = [
                {"scores": scores, "liked_careers": ["C1"]},
                {"scores": scores, "liked_careers": ["C1"]},
            ]
            with open(feedback_path, "w", encoding="utf-8") as file:
                json.dump(feedbacks, file)
            with open(careers_path, "w", encoding="utf-8") as file:
                json.dump({"C1": {"career_group": "Test Group"}}, file)
            training_row = {
                **scores,
                "career_group": "Test Group",
                LABEL_SOURCE_COL: LABEL_DERIVED,
            }
            pd.DataFrame([training_row]).to_csv(students_path, index=False)

            with patch.object(retrain_service, "FEEDBACK_PATH", feedback_path), \
                    patch.object(retrain_service, "CAREERS_PATH", careers_path), \
                    patch.object(retrain_service, "DATA_PATH", students_path):
                result = retrain_service.check_and_trigger_auto_retrain(
                    min_feedback_count=1,
                    force=False,
                )

            self.assertEqual(result["status"], "waiting")
            self.assertEqual(result["ready_count"], 0)
            self.assertEqual(result["feedback_count"], 2)


if __name__ == "__main__":
    unittest.main()
