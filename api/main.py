# -*- coding: utf-8 -*-
"""
api/main.py — Bước 2: Xây dựng REST API bằng FastAPI (PDF Mục 3.4).

API có các nhiệm vụ chính:
1. Nạp model một lần ở cấp module khi khởi động (không nạp lại trong mỗi request).
2. Đọc metadata cấu hình từ models/current/metadata.json.
3. Khai báo và kiểm tra dữ liệu đầu vào bằng Pydantic (ràng buộc 12 môn [0.0, 10.0], từ chối lỗi với mã 422).
4. Các endpoints:
   - GET  /health      : Sức khỏe dịch vụ, model version, uptime.
   - GET  /model-info  : Cung cấp metadata, schema đầu vào, danh mục môn học, nhóm nghề để Web render động.
   - POST /predict     : Suy luận phân loại nhóm nghề (ML Inference thuần túy).
   - POST /decision    : Hệ hỗ trợ quyết định toàn diện (ML Tầng 1 + CBF Tầng 2 + Groq LLM diễn giải).
5. Kích hoạt CORSMiddleware để hỗ trợ giao diện Web Streamlit.
"""
import asyncio
import logging
import os
import sqlite3
import sys
import time
import json
import math
import secrets

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from typing import Any, AsyncIterator, Dict, List, Literal, Optional, Union, ClassVar
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status, BackgroundTasks
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, model_validator
import pandas as pd
import numpy as np
import joblib

# Thiết lập đường dẫn thư mục gốc
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR) if os.path.basename(CURRENT_DIR) == "api" else CURRENT_DIR

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Các module dùng chung (CBF, feedback_store, monitor_service...) đọc data/ bằng đường dẫn tương đối so với thư mục gốc.
# Chuyển thư mục làm việc về gốc để API chạy đúng dù khởi động từ api/ (như PDF) hay từ thư mục gốc.
os.chdir(PROJECT_ROOT)

from career_ai.domain_knowledge import (
    SUBJECTS, SUBJECT_KEYS, KEY_TO_SUBJECT, CAREER_GROUPS,
    SOFT_SKILL_OPTIONS, INTEREST_OPTIONS, SKILL_LEVEL_CHOICES, SKILL_LEVEL_LABELS,
)
from career_ai.cbf_recommender import ContentBasedFilteringRecommender
from career_ai import feedback_store
from api.llm_explain import DISCLAIMER, explain_with_llm
from career_ai.decision_core import apply_interest_and_skill_boost, clean_skill_levels
from career_ai.model_exporter import (
    METADATA_FILE, MODEL_FILE, sklearn_version_warning, validate_deployable_pipeline,
)
from career_ai.monitor_service import log_prediction
from career_ai.retrain_service import (
    register_reload_callback, check_and_trigger_auto_retrain, retrain_from_explicit_feedback,
    rebuild_feedback_training_data,
)
from career_ai.storage_paths import data_file

START_TIME = time.time()
logger = logging.getLogger(__name__)
admin_basic = HTTPBasic(auto_error=False)


async def _run_retention_cleanup() -> None:
    from career_ai.retention_service import purge_expired_data

    try:
        result = await asyncio.to_thread(purge_expired_data)
    except (OSError, ValueError, sqlite3.Error, json.JSONDecodeError):
        logger.exception("Automatic retention cleanup failed")
    else:
        if any(value for key, value in result.items() if key.startswith("deleted_")):
            logger.info("Automatic retention cleanup removed expired records: %s", result)


async def _retention_cleanup_loop() -> None:
    while True:
        await asyncio.sleep(24 * 60 * 60)
        await _run_retention_cleanup()


@asynccontextmanager
async def app_lifespan(_app) -> AsyncIterator[None]:
    await _run_retention_cleanup()
    cleanup_task = asyncio.create_task(_retention_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        await asyncio.gather(cleanup_task, return_exceptions=True)


def require_admin(credentials: Optional[HTTPBasicCredentials] = Depends(admin_basic)):
    username = os.environ.get("ADMIN_USERNAME", "").strip()
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin authentication is not configured.",
        )
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )

    username_matches = secrets.compare_digest(
        credentials.username.encode("utf-8"), username.encode("utf-8")
    )
    password_matches = secrets.compare_digest(
        credentials.password.encode("utf-8"), password.encode("utf-8")
    )
    if not (username_matches and password_matches):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials

# ---------------------------------------------------------------------------
# 1. NẠP MODEL VÀ METADATA MỘT LẦN Ở CẤP MODULE
# ---------------------------------------------------------------------------
# NGUỒN SỰ THẬT DUY NHẤT: models/current/ chứa pipeline đã triển khai và metadata.
# models/v<phiên bản>/ chỉ là bản lưu trữ lịch sử, không được nạp ở đây.
MODEL_PATH = os.path.join(PROJECT_ROOT, MODEL_FILE)
METADATA_PATH = os.path.join(PROJECT_ROOT, METADATA_FILE)

if not os.path.exists(MODEL_PATH) or not os.path.exists(METADATA_PATH):
    raise RuntimeError(
        "Chưa có models/current/model_pipeline.joblib / metadata.json. "
        "Hãy chạy `python -m career_ai.prepare_data` rồi `python -m career_ai.train` trước khi khởi động API."
    )

print(f"[API] Đang nạp model từ: {MODEL_PATH}")
pipe = validate_deployable_pipeline(joblib.load(MODEL_PATH))

print(f"[API] Đang nạp metadata từ: {METADATA_PATH}")
with open(METADATA_PATH, encoding="utf-8") as f:
    META = json.load(f)

_ver_warn = sklearn_version_warning(META)
if _ver_warn:
    print(f"[API][CẢNH BÁO] {_ver_warn}")

# Metadata dùng schema của model_exporter.py: model_version, input_schema, target_schema, evaluation_metrics.
MODEL_VERSION = META.get("model_version", "unknown")
ALGORITHM = META.get("algorithm", "unknown")
FEATURE_COLS = META.get("input_schema", {}).get("feature_order") or [SUBJECT_KEYS[s] for s in SUBJECTS]
FEATURE_RANGES = {
    f["feature_key"]: [f["min_value"], f["max_value"]]
    for f in META.get("input_schema", {}).get("features", [])
} or {c: [0.0, 10.0] for c in FEATURE_COLS}
CAREER_GROUP_LIST = META.get("target_schema", {}).get("classes") or CAREER_GROUPS
_ev = META.get("evaluation_metrics", {})
# Giữ tên khóa cũ (f1_score, f1_cv_5fold) để giao diện Web không phải sửa.
METRICS_PUBLIC = {
    "accuracy": _ev.get("accuracy"),
    "precision": _ev.get("precision"),
    "recall": _ev.get("recall"),
    "f1_score": _ev.get("f1_test"),
    "f1_cv_5fold": _ev.get("f1_cv_5fold_mean"),
    "f1_cv_5fold_std": _ev.get("f1_cv_5fold_std"),
    "brier_score_cv": _ev.get("brier_score_cv"),
    "log_loss_cv": _ev.get("log_loss_cv"),
    "expected_calibration_error_cv": _ev.get("expected_calibration_error_cv"),
    "uncalibrated_expected_calibration_error_cv": _ev.get(
        "uncalibrated_expected_calibration_error_cv"
    ),
}
METRICS_NOTE = (
    "Các chỉ số đánh giá và hiệu chuẩn xác suất được tính trên nhãn hiện có, chủ yếu là nhãn SUY RA từ bảng điểm; "
    "chúng không đo độ chính xác hay xác suất phù hợp nghề nghiệp ngoài thực tế."
)
PROBABILITY_NOTE = (
    "Xác suất nhóm nghề được hiệu chuẩn bằng temperature scaling qua cross-validation theo nhãn huấn luyện hiện có "
    "(chủ yếu là nhãn suy ra từ điểm). Chưa có đủ nhãn nghề nghiệp thực tế để diễn giải thành xác suất "
    "thành công hoặc mức độ phù hợp thực tế. Sở thích và kỹ năng làm thay đổi thứ hạng bằng quy tắc riêng, "
    "không làm thay đổi xác suất mô hình."
)

recommender = ContentBasedFilteringRecommender(
    students_csv_path=os.path.join(PROJECT_ROOT, "data", "students.csv"),
    careers_json_path=os.path.join(PROJECT_ROOT, "data", "careers.json"),
    feedback_json_path=data_file("feedback.json"),
)


def reload_model():
    """Live-reload model và metadata mới vào bộ nhớ API khi có phiên bản retrain thành công."""
    global pipe, META, MODEL_VERSION, ALGORITHM, FEATURE_COLS, FEATURE_RANGES, CAREER_GROUP_LIST, METRICS_PUBLIC
    if os.path.exists(MODEL_PATH) and os.path.exists(METADATA_PATH):
        try:
            pipe = validate_deployable_pipeline(joblib.load(MODEL_PATH))
            with open(METADATA_PATH, encoding="utf-8") as f:
                META = json.load(f)
            MODEL_VERSION = META.get("model_version", "unknown")
            ALGORITHM = META.get("algorithm", "unknown")
            _ev = META.get("evaluation_metrics", {})
            METRICS_PUBLIC = {
                "accuracy": _ev.get("accuracy"),
                "precision": _ev.get("precision"),
                "recall": _ev.get("recall"),
                "f1_score": _ev.get("f1_test"),
                "f1_cv_5fold": _ev.get("f1_cv_5fold_mean"),
                "f1_cv_5fold_std": _ev.get("f1_cv_5fold_std"),
                "brier_score_cv": _ev.get("brier_score_cv"),
                "log_loss_cv": _ev.get("log_loss_cv"),
                "expected_calibration_error_cv": _ev.get("expected_calibration_error_cv"),
                "uncalibrated_expected_calibration_error_cv": _ev.get(
                    "uncalibrated_expected_calibration_error_cv"
                ),
            }
            recommender.reload()
            print(f"[API] Live-reload thành công: {MODEL_VERSION} ({ALGORITHM})")
        except Exception as e:
            print(f"[API][LỖI] Live-reload thất bại: {e}")


register_reload_callback(reload_model)


# ---------------------------------------------------------------------------
# 2. KHAI BÁO VÀ KIỂM TRA DỮ LIỆU ĐẦU VÀO BẰNG PYDANTIC
# ---------------------------------------------------------------------------
class SubjectScoresInput(BaseModel):
    """Điểm 12 môn học bắt buộc trong khoảng [0.0, 10.0]."""
    sec: float = Field(..., ge=0.0, le=10.0, description="An toàn và bảo mật HTTT")
    se: float = Field(..., ge=0.0, le=10.0, description="Công nghệ phần mềm")
    linux: float = Field(..., ge=0.0, le=10.0, description="Hệ điều hành Linux")
    db: float = Field(..., ge=0.0, le=10.0, description="Hệ quản trị CSDL")
    graphics: float = Field(..., ge=0.0, le=10.0, description="Kỹ thuật đồ hoạ máy tính")
    network: float = Field(..., ge=0.0, le=10.0, description="Mạng máy tính")
    analysis: float = Field(..., ge=0.0, le=10.0, description="Phân tích thiết kế HTTT")
    image: float = Field(..., ge=0.0, le=10.0, description="Xử lý ảnh")
    java: float = Field(..., ge=0.0, le=10.0, description="Công nghệ Java")
    csharp: float = Field(..., ge=0.0, le=10.0, description="Ngôn ngữ C# và công nghệ .NET")
    web: float = Field(..., ge=0.0, le=10.0, description="Công nghệ web")
    ai: float = Field(..., ge=0.0, le=10.0, description="Trí tuệ nhân tạo")


class PredictRequest(BaseModel):
    """Hỗ trợ cả định dạng phẳng lẫn bọc trong object 'scores' hoặc tên môn tiếng Việt."""
    scores: Optional[Dict[str, float]] = None
    sec: Optional[float] = Field(None, ge=0.0, le=10.0)
    se: Optional[float] = Field(None, ge=0.0, le=10.0)
    linux: Optional[float] = Field(None, ge=0.0, le=10.0)
    db: Optional[float] = Field(None, ge=0.0, le=10.0)
    graphics: Optional[float] = Field(None, ge=0.0, le=10.0)
    network: Optional[float] = Field(None, ge=0.0, le=10.0)
    analysis: Optional[float] = Field(None, ge=0.0, le=10.0)
    image: Optional[float] = Field(None, ge=0.0, le=10.0)
    java: Optional[float] = Field(None, ge=0.0, le=10.0)
    csharp: Optional[float] = Field(None, ge=0.0, le=10.0)
    web: Optional[float] = Field(None, ge=0.0, le=10.0)
    ai: Optional[float] = Field(None, ge=0.0, le=10.0)
    allow_partial: Optional[bool] = Field(False, description="Cho phép đánh giá sớm khi chưa đủ 12 môn (năm 1-3)")
    completed_subjects: Optional[List[str]] = Field(default_factory=list, description="Danh sách các môn đã học")
    missing_subjects: Optional[List[str]] = Field(default_factory=list, description="Danh sách các môn chưa học")

    _default_allow_partial: ClassVar[bool] = False

    @model_validator(mode="before")
    @classmethod
    def validate_and_unify_scores(cls, data):
        if not isinstance(data, dict):
            return data
        
        # Nếu đã có trường scores bọc bên ngoài
        scores_dict = data.get("scores")
        flat_data = {k: v for k, v in data.items() if k not in ("scores", "allow_partial", "completed_subjects", "missing_subjects")}
        allow_partial = bool(data.get("allow_partial") if data.get("allow_partial") is not None else getattr(cls, "_default_allow_partial", False))
        data["allow_partial"] = allow_partial
        
        extracted = {}
        # Ưu tiên lấy từ scores nếu có
        if isinstance(scores_dict, dict):
            for k, v in scores_dict.items():
                norm_k = SUBJECT_KEYS.get(k, k)
                extracted[norm_k] = v
        # Lấy bổ sung từ flat_data
        for k, v in flat_data.items():
            norm_k = SUBJECT_KEYS.get(k, k)
            if norm_k in FEATURE_COLS and v is not None:
                extracted[norm_k] = v

        # Kiểm tra khoảng giá trị [0.0, 10.0] và kiểu dữ liệu cho các môn được truyền lên
        for k, val in list(extracted.items()):
            if k not in FEATURE_COLS:
                continue
            if isinstance(val, bool):
                raise ValueError(f"Điểm môn '{KEY_TO_SUBJECT.get(k, k)}' phải là số, không phải true/false")
            try:
                fval = float(val)
            except (ValueError, TypeError):
                raise ValueError(f"Điểm môn '{KEY_TO_SUBJECT.get(k, k)}' phải là số hợp lệ, nhận được: {val}")
            if not math.isfinite(fval):  # NaN/Infinity lọt qua phép so sánh khoảng và gây lỗi 500
                raise ValueError(f"Điểm môn '{KEY_TO_SUBJECT.get(k, k)}' phải là số hữu hạn")
            if fval < 0.0 or fval > 10.0:
                raise ValueError(f"Điểm môn '{KEY_TO_SUBJECT.get(k, k)}' phải nằm trong khoảng [0.0, 10.0], nhận được: {fval}")
            extracted[k] = fval

        provided_keys = [f for f in FEATURE_COLS if f in extracted]
        missing = [f for f in FEATURE_COLS if f not in extracted]

        if not allow_partial:
            # Kiểm tra đầy đủ 12 môn
            if missing:
                missing_names = [KEY_TO_SUBJECT.get(m, m) for m in missing]
                raise ValueError(f"Thiếu điểm các môn học: {', '.join(missing_names)}")
        else:
            # Chế độ đánh giá sớm: yêu cầu tối thiểu 1 môn
            if len(provided_keys) == 0:
                raise ValueError("Cần cung cấp điểm của ít nhất 1 môn học để thực hiện phân tích định hướng.")
            # Điền giá trị trung bình toàn trường cho các môn khuyết (Imputation)
            from career_ai.domain_knowledge import SUBJECT_STATS
            for m in missing:
                subj_name = KEY_TO_SUBJECT.get(m, m)
                mean_val, _ = SUBJECT_STATS.get(subj_name, (7.5, 1.0))
                extracted[m] = float(round(mean_val, 2))

        data["scores"] = extracted
        data["completed_subjects"] = [KEY_TO_SUBJECT.get(k, k) for k in provided_keys]
        data["missing_subjects"] = [KEY_TO_SUBJECT.get(k, k) for k in missing]
        return data


class PredictPartialRequest(PredictRequest):
    """Yêu cầu suy luận ML với chế độ thiếu môn được bật mặc định."""
    _default_allow_partial: ClassVar[bool] = True
    allow_partial: Optional[bool] = Field(True, description="Mặc định bật đánh giá sớm khi thiếu môn")


class DecisionRequest(PredictRequest):
    """Request đầy đủ cho hệ hỗ trợ quyết định: điểm 12 môn, kỹ năng mềm, sở thích."""
    _default_allow_partial: ClassVar[bool] = False
    skills: Optional[Dict[str, str]] = Field(default_factory=dict, max_length=20, description="Kỹ năng mềm")
    interests: Optional[List[str]] = Field(default_factory=list, max_length=20, description="Lĩnh vực quan tâm")
    student_name: Optional[str] = Field(default="Sinh viên", max_length=100, description="Họ tên sinh viên")
    store_scores_in_logs: bool = Field(
        False, description="Cho phép lưu điểm trong nhật ký để giám sát chất lượng."
    )

    @field_validator("skills")
    @classmethod
    def validate_skills(cls, v):
        """Khóa kỹ năng phải có trong danh mục; cấp độ phải là weak/medium/strong/excellent hoặc rỗng (= chưa đánh giá)."""
        valid_keys = {o["key"] for o in SOFT_SKILL_OPTIONS}
        for k, lvl in (v or {}).items():
            if k not in valid_keys:
                raise ValueError(f"Kỹ năng không hợp lệ: '{k}'. Hợp lệ: {sorted(valid_keys)}")
            if lvl not in SKILL_LEVEL_LABELS and lvl not in ("", "unassessed"):
                raise ValueError(f"Cấp độ kỹ năng '{lvl}' không hợp lệ. Hợp lệ: {sorted(SKILL_LEVEL_LABELS)} hoặc rỗng")
        return v or {}

    @field_validator("interests")
    @classmethod
    def validate_interests(cls, v):
        bad = [i for i in (v or []) if i not in INTEREST_OPTIONS]
        if bad:
            raise ValueError(f"Lĩnh vực quan tâm không hợp lệ: {bad}. Hợp lệ: {INTEREST_OPTIONS}")
        return v or []


class DecisionPartialRequest(DecisionRequest):
    """Yêu cầu hỗ trợ quyết định toàn diện với chế độ thiếu môn được bật mặc định."""
    _default_allow_partial: ClassVar[bool] = True
    allow_partial: Optional[bool] = Field(True, description="Mặc định bật đánh giá sớm khi thiếu môn")


class StudentSurveyRequest(BaseModel):
    """Optional structured survey about recommendation relevance and usefulness."""
    relevance: Optional[int] = Field(None, ge=1, le=5, strict=True)
    usefulness: Optional[int] = Field(None, ge=1, le=5, strict=True)
    explore_intent: Optional[Literal["yes", "maybe", "no"]] = None


class FeedbackRequest(BaseModel):
    """Phản hồi cho nghề được xếp hạng; lưu điểm chỉ khi người gửi đồng ý rõ ràng."""
    career_id: str = Field(..., min_length=1, max_length=32)
    top_group: str = Field(..., min_length=1, max_length=100)
    top_prob: float = Field(..., ge=0.0, le=1.0)
    liked: bool
    scores: Optional[Dict[str, float]] = None
    include_scores: bool = Field(
        False, description="Cho phép lưu điểm môn học cùng phản hồi để cải thiện gợi ý."
    )
    comment: Optional[str] = ""
    rating: Optional[int] = Field(None, ge=1, le=5)
    survey: Optional[StudentSurveyRequest] = None


class FeedbackBackupRecord(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    timestamp: str = Field(..., min_length=1, max_length=64)
    student_name: str = "Sinh viên"
    top_group: str = Field(..., min_length=1, max_length=100)
    top_prob: float = Field(..., ge=0.0, le=1.0)
    rating: int = Field(..., ge=1, le=5, strict=True)
    liked_careers: List[str] = Field(default_factory=list)
    disliked_careers: List[str] = Field(default_factory=list)
    comment: str = ""
    scores: Dict[str, float] = Field(default_factory=dict)
    survey: Dict[str, Any] = Field(default_factory=dict)


class FeedbackBackupRequest(BaseModel):
    feedbacks: List[FeedbackBackupRecord] = Field(..., max_length=10000)


# ---------------------------------------------------------------------------
# 3. FASTAPI APP KHỞI TẠO VÀ CORS
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Career Recommendation DSS API",
    description="Hệ thống hỗ trợ quyết định định hướng nghề nghiệp CNTT dựa trên mô hình học máy và lọc dựa trên nội dung (CBF).",
    version=MODEL_VERSION,
    lifespan=app_lifespan,
)

# Danh sách nguồn được phép, cách nhau bằng dấu phẩy, cấu hình qua biến môi trường CORS_ORIGINS.
# Mặc định chỉ cho phép localhost; không dùng "*" cùng allow_credentials=True (không hợp lệ và thiếu an toàn).
_cors_origins = [o.strip() for o in os.environ.get(
    "CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501,http://localhost:5000,http://127.0.0.1:5000"
).split(",") if o.strip()]

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Trả 422 gọn, KHÔNG phản chiếu lại 'input' (NaN/Infinity làm JSON encode lỗi -> 500; input dài làm phình phản hồi)."""
    errors = [{"loc": list(e.get("loc", [])), "msg": str(e.get("msg", "")), "type": e.get("type", "")}
              for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _predict_raw(scores_dict: Dict[str, float]) -> dict:
    """Gửi trực tiếp 12 điểm thô vào Pipeline đã đóng gói cả tiền xử lý và model."""
    row = {k: scores_dict[k] for k in FEATURE_COLS}
    X = pd.DataFrame([row])[FEATURE_COLS]
    
    pred_group = str(pipe.predict(X)[0])
    classes = list(pipe.classes_)
    probas = pipe.predict_proba(X)[0]
    
    prob_dict = {cls_name: round(float(p) * 100, 2) for cls_name, p in zip(classes, probas)}
    # Sắp xếp các nhóm nghề theo xác suất giảm dần
    sorted_groups = sorted(prob_dict.items(), key=lambda kv: kv[1], reverse=True)
    confidence = round(float(prob_dict.get(pred_group, max(probas) * 100)), 2)

    return {
        "predicted_group": pred_group,
        "confidence": confidence,
        "probabilities": prob_dict,
        "sorted_groups": sorted_groups,
        "model_version": MODEL_VERSION,
        "algorithm": ALGORITHM,
    }


# ---------------------------------------------------------------------------
# 4. ENDPOINTS
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    """Kiểm tra tình trạng hoạt động của API và phiên bản mô hình."""
    uptime = round(time.time() - START_TIME, 2)
    return {
        "status": "healthy",
        "service": "Career Recommendation AI Serving API",
        "model_version": MODEL_VERSION,
        "algorithm": ALGORITHM,
        "uptime_seconds": uptime,
    }


@app.get("/model-info")
def model_info():
    """Trả về metadata để client dựng form nhập liệu và kiểm tra đầu vào."""
    return {
        "model_name": META.get("model_name", "career_recommendation_model"),
        "version": MODEL_VERSION,
        "algorithm": ALGORITHM,
        "numeric_features": FEATURE_COLS,
        "subject_names": SUBJECTS,
        "subject_keys": SUBJECT_KEYS,
        "key_to_subject": KEY_TO_SUBJECT,
        "feature_ranges": FEATURE_RANGES,
        "career_groups": CAREER_GROUP_LIST,
        "soft_skills": SOFT_SKILL_OPTIONS,
        "skill_levels": SKILL_LEVEL_CHOICES,
        "interest_options": INTEREST_OPTIONS,
        "metrics_test": METRICS_PUBLIC,
        "metrics_note": METRICS_NOTE,
        "probability_note": PROBABILITY_NOTE,
        "disclaimer": DISCLAIMER,
    }


@app.post("/predict")
def predict_endpoint(req: PredictRequest):
    """
    Endpoint /predict: Suy luận phân loại nhóm nghề (ML Tầng 1).
    Nhận điểm 12 môn học -> kiểm tra hợp lệ -> trả về nhóm nghề và phân phối xác suất.
    """
    t0 = time.time()
    scores = req.scores
    result = _predict_raw(scores)
    result["latency_ms"] = round((time.time() - t0) * 1000, 2)
    return result


@app.post("/decision")
def decision_endpoint(req: DecisionRequest):
    """
    Endpoint /decision: Logic hỗ trợ quyết định toàn diện (PDF Mục 3.4).
    Kết hợp:
      1. Dự đoán nhóm ngành hàng đầu bằng mô hình học máy (Tầng 1).
      2. Xếp hạng và đề xuất Top 3 nghề cụ thể trong 21 nghề IT bằng Content-Based Filtering (Tầng 2).
      3. Phân tích môn học thế mạnh, môn cần cải thiện và sự tương thích kỹ năng mềm.
      4. Tạo diễn giải tự nhiên thông minh từ GroqCloud API (Bước 4).
    """
    t0 = time.time()
    scores = req.scores
    skills = req.skills or {}
    interests = req.interests or []
    student_name = "Sinh viên"

    # Quy đổi điểm về dạng tên môn tiếng Việt để chuyển cho CBF
    subject_scores_vn = {KEY_TO_SUBJECT[k]: scores[k] for k in FEATURE_COLS}

    # 1. Dự đoán Tầng 1 (mô hình học máy) rồi điều chỉnh theo sở thích/kỹ năng mềm.
    ml_result = _predict_raw(scores)
    skill_levels = clean_skill_levels(skills)  # "Chưa đánh giá" bị bỏ qua, không cộng/trừ điểm
    raw_ranked = [(g, p / 100.0) for g, p in ml_result["sorted_groups"]]
    ranked_groups = apply_interest_and_skill_boost(raw_ranked, interests, skill_levels)
    adjusted = bool(interests or skill_levels)
    pred_group, top_prob = ranked_groups[0]
    confidence = ml_result["confidence"]
    preference_adjusted_score = round(top_prob * 100, 2)
    probabilities_adjusted = {g: round(p * 100, 2) for g, p in ranked_groups}

    # 2. Khuyến nghị Tầng 2: CBF
    missing_vn = req.missing_subjects or []
    completed_vn = req.completed_subjects or []
    is_partial = bool(req.allow_partial and missing_vn)

    top_careers, remaining = recommender.recommend_top_careers(
        ranked_groups_with_prob=ranked_groups,
        student_scores=subject_scores_vn,
        skills_selected=skill_levels,
        n=3,
        missing_subjects=missing_vn,
    )

    # 3. Phân tích điểm mạnh & điểm cần cải thiện tổng thể
    sorted_scores = sorted(subject_scores_vn.items(), key=lambda kv: kv[1], reverse=True)
    strengths = [f"{s} ({val}đ)" for s, val in sorted_scores if val >= 7.5 and s not in missing_vn][:4]
    improvements = [f"{s} ({val}đ)" for s, val in sorted_scores[::-1] if val < 6.5 and s not in missing_vn][:3]

    # Định dạng kết quả Top 3 nghề
    formatted_top_careers = []
    for c in top_careers:
        formatted_top_careers.append({
            "career_id": c["career_id"],
            "career_name": c["career_name"],
            "career_group": c["career_group"],
            "match_percentage": c["cbf_score_pct"],
            "description": c["description"],
            "salary": c["salary"],
            "salary_data": c.get("salary_data"),
            "trend": c["trend"],
            "region": c.get("region", "Việt Nam (Hà Nội, TP.HCM, Đà Nẵng)"),
            "source": c.get("source", "Báo cáo thị trường IT TopCV & ITviec Tech Salary Report"),
            "sources": c.get("sources", []),
            "source_scope": c.get("source_scope", []),
            "updated_at": c.get("updated_at", "2025 - 2026"),
            "source_reviewed_at": c.get("source_reviewed_at", ""),
            "strengths": c.get("strengths", []),
            "improvements": c.get("improvements", []),
            "unstudied_core": c.get("unstudied_core", []),
            "soft_skill_matches": c.get("soft_skill_matches", []),
            "soft_skill_improvements": c.get("soft_skill_improvements", []),
            "explanation": {
                "matched_subjects": c.get("strengths", []),
                "matched_skills": c.get("soft_skill_matches", []),
                "subjects_to_strengthen": c.get("improvements", []),
                "core_subjects_not_yet_studied": c.get("unstudied_core", []),
                "is_group_fill": c.get("is_group_fill", False),
                "score_note": "Điểm khớp tham khảo, không dự đoán khả năng thành công ngoài thực tế.",
            },
            "is_group_fill": c.get("is_group_fill", False),
        })

    # Tóm tắt khuyến nghị
    top_career_name = formatted_top_careers[0]["career_name"] if formatted_top_careers else ""
    partial_note = f" (Định hướng sơ bộ dựa trên {len(completed_vn)}/12 môn đã học)" if is_partial else ""
    rec_summary = (
        f"Mô hình dự đoán nhóm '{ml_result['predicted_group']}' với mức "
        f"{confidence:.1f}% theo nhãn huấn luyện. "
    )
    if adjusted:
        rec_summary += (
            f"Sau khi cân nhắc sở thích và kỹ năng, gợi ý xếp hạng là '{pred_group}' "
            f"(điểm xếp hạng {preference_adjusted_score:.1f}%, không phải xác suất)."
        )
    else:
        rec_summary += f"Gợi ý nhóm nghề là '{pred_group}'."
    rec_summary += partial_note
    if formatted_top_careers:
        rec_summary += (
            f" Nghề khớp hồ sơ môn học nhất: {top_career_name} "
            f"({formatted_top_careers[0]['match_percentage']:.1f}%)."
        )

    intermediate_decision = {
        "predicted_group": ml_result["predicted_group"],
        "recommendation_group": pred_group,
        "confidence": confidence,
        "model_confidence": confidence,
        "recommendation_ranking_score": preference_adjusted_score,
        "top_careers": formatted_top_careers,
        "strengths": [s.split(" (")[0] for s in strengths],
        "improvements": [s.split(" (")[0] for s in improvements],
        "recommendation_summary": rec_summary,
    }

    # 4. Bước 4: Diễn giải bằng GroqCloud API
    student_meta = {
        "scores": subject_scores_vn,
        "skills": skills,
        "interests": interests,
        "student_name": student_name,
    }
    llm_res = explain_with_llm(student_meta, intermediate_decision)

    latency = round((time.time() - t0) * 1000, 2)

    # Giai đoạn 5 (Monitor): ghi nhật ký lượt dự đoán vào SQLite + JSONL để phát hiện drift.
    try:
        log_prediction(
            input_scores=scores if req.store_scores_in_logs else {},
            top_group=ml_result["predicted_group"],
            top_prob=max(ml_result["probabilities"].values()) / 100.0,
            model_version=MODEL_VERSION, latency_ms=latency, source="fastapi",
            is_partial=is_partial,
        )
    except OSError as e:  # lỗi ghi log không được làm hỏng phản hồi
        print(f"[API][CẢNH BÁO] Không ghi được log giám sát: {type(e).__name__}")

    return {
        "student_name": student_name,
        "predicted_group": pred_group,
        "recommendation_group": pred_group,
        "model_predicted_group": ml_result["predicted_group"],
        "confidence": confidence,
        "model_confidence": confidence,
        "preference_adjusted_score": preference_adjusted_score,
        "recommendation_ranking_score": preference_adjusted_score,
        "model_probability_for_recommendation_group": ml_result["probabilities"][pred_group],
        "probabilities": probabilities_adjusted,
        "recommendation_ranking_scores": probabilities_adjusted,
        "probabilities_model_only": ml_result["probabilities"],
        "adjusted_by_preferences": adjusted,
        "top_careers": formatted_top_careers,
        "remaining_careers": [
            {
                "career_id": r["career_id"],
                "career_name": r["career_name"],
                "match_percentage": r["cbf_score_pct"],
                "salary": r["salary"],
            }
            for r in remaining
        ],
        "strengths": strengths,
        "improvements": improvements,
        "recommendation_summary": rec_summary,
        "explanation_llm": llm_res,
        "disclaimer": DISCLAIMER,
        "probability_note": PROBABILITY_NOTE,
        "model_version": MODEL_VERSION,
        "response_time_ms": latency,
        "is_partial_assessment": is_partial,
        "completed_subjects_count": len(completed_vn) if completed_vn else len(FEATURE_COLS),
        "missing_subjects": missing_vn,
    }


@app.post("/predict/partial")
def predict_partial_endpoint(req: PredictPartialRequest):
    """Tiện ích suy luận nhóm nghề cho sinh viên năm 1-3 (tự động bật allow_partial=True)."""
    return predict_endpoint(req)


@app.post("/decision/partial")
def decision_partial_endpoint(req: DecisionPartialRequest):
    """Tiện ích ra quyết định định hướng sớm cho sinh viên năm 1-3 (tự động bật allow_partial=True)."""
    return decision_endpoint(req)


@app.post("/feedback", status_code=status.HTTP_201_CREATED)
def submit_feedback(req: FeedbackRequest, background_tasks: BackgroundTasks = None):
    """
    Lưu phản hồi vào CSDL SQLite (ACID) đồng thời cập nhật mirror JSON.
    Nếu phản hồi chứa bảng điểm và đánh giá tích cực, kích hoạt kiểm tra tự động Retrain trong nền.
    """
    if req.career_id not in recommender.career_ids:
        raise HTTPException(status_code=422, detail="Nghề nghiệp không hợp lệ.")
    if req.top_group not in CAREER_GROUP_LIST:
        raise HTTPException(status_code=422, detail="Nhóm nghề không hợp lệ.")

    try:
        record = feedback_store.add_feedback(
            top_group=req.top_group,
            top_prob=req.top_prob,
            rating=req.rating or (5 if req.liked else 1),
            liked_careers=[req.career_id] if req.liked else [],
            disliked_careers=[] if req.liked else [req.career_id],
            comment=req.comment or "",
            scores=(req.scores or {}) if req.include_scores else {},
            student_name="",
            survey=req.survey.model_dump(exclude_none=True) if req.survey else {},
        )
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"[API][CẢNH BÁO] Không lưu được phản hồi: {type(exc).__name__}")
        raise HTTPException(status_code=500, detail="Không thể lưu phản hồi.") from exc

    mirror_synced = record["mirror_synced"]
    recommender_updated = False
    if mirror_synced:
        try:
            recommender.reload()
            recommender_updated = True
        except (OSError, ValueError) as exc:
            print(f"[API][CẢNH BÁO] Đã lưu phản hồi nhưng chưa cập nhật được bộ gợi ý: {type(exc).__name__}")
    else:
        print("[API][CẢNH BÁO] Đã lưu phản hồi vào SQLite nhưng chưa cập nhật được bộ gợi ý.")

    # Tự động kích hoạt kiểm tra Retrain trong nền nếu có phản hồi tích cực kèm bảng điểm
    if req.liked and req.include_scores and req.scores and background_tasks is not None:
        background_tasks.add_task(check_and_trigger_auto_retrain, min_feedback_count=5)

    return {
        "status": "saved",
        "feedback_id": record["id"],
        "recommender_updated": recommender_updated,
        "mirror_synced": mirror_synced,
    }


@app.post("/retrain")
def retrain_endpoint(force: bool = False, _admin: HTTPBasicCredentials = Depends(require_admin)):
    """
    Endpoint kích hoạt chu trình Huấn luyện lại (Retrain Loop):
    Đọc phản hồi từ SQLite/JSON -> Lọc mẫu hợp lệ -> Clone & Train pipeline ->
    Kiểm tra Quality Gate -> Export Model Package -> Live-reload API không cần restart.
    """
    res = check_and_trigger_auto_retrain(min_feedback_count=5, force=force)
    return res


@app.get("/admin/auth")
def admin_auth_endpoint(_admin: HTTPBasicCredentials = Depends(require_admin)):
    """Confirms credentials for the Streamlit admin login without exposing admin data."""
    return {"authenticated": True}


@app.get("/admin/stats")
def admin_stats_endpoint(_admin: HTTPBasicCredentials = Depends(require_admin)):
    """Thống kê tổng quan cho Admin Dashboard (Feedbacks, Logs, Model Health)."""
    from career_ai import db
    from career_ai.survey_metrics import summarize_student_survey
    feedbacks = db.get_all_feedbacks()
    logs = db.get_prediction_logs(limit=500)

    total_feedbacks = len(feedbacks)
    liked_count = sum(1 for f in feedbacks if (f.get("liked_careers") and len(f["liked_careers"]) > 0) or f.get("rating", 0) >= 4)
    avg_rating = round(sum(f.get("rating", 5) for f in feedbacks) / max(total_feedbacks, 1), 2) if total_feedbacks else 0.0

    total_predictions = db.count_prediction_logs()
    partial_predictions = sum(1 for l in logs if l.get("is_partial"))
    avg_latency = round(
        sum(l.get("latency_ms", 0.0) for l in logs) / len(logs), 2
    ) if logs else 0.0

    # Phân bố nhóm ngành dự đoán
    group_counts = {}
    for l in logs:
        g = l.get("predicted_group", "Khác")
        group_counts[g] = group_counts.get(g, 0) + 1

    uptime = round(time.time() - START_TIME, 2)
    return {
        "model_version": MODEL_VERSION,
        "algorithm": ALGORITHM,
        "uptime_seconds": uptime,
        "metrics": METRICS_PUBLIC,
        "total_feedbacks": total_feedbacks,
        "liked_feedbacks": liked_count,
        "feedback_satisfaction_pct": round((liked_count / max(total_feedbacks, 1)) * 100, 1) if total_feedbacks else 0.0,
        "avg_rating": avg_rating,
        "student_survey": summarize_student_survey(feedbacks),
        "total_predictions": total_predictions,
        "partial_predictions": partial_predictions,
        "avg_latency_ms": avg_latency,
        "group_distribution": group_counts,
    }


@app.get("/admin/feedbacks")
def admin_feedbacks_endpoint(limit: int = 50, _admin: HTTPBasicCredentials = Depends(require_admin)):
    """
    Lấy danh sách các phản hồi sinh viên mới nhất từ SQLite/Turso.
    Tự động fallback và bắt lỗi chi tiết nếu kết nối CSDL bị gián đoạn.
    """
    from career_ai import db
    try:
        feedbacks = db.get_all_feedbacks(limit=limit)
        return {
            "status": "success",
            "count": len(feedbacks),
            "using_turso": db.using_turso(),
            "feedbacks": feedbacks
        }
    except Exception as exc:
        print(f"[API][LỖI ADMIN FEEDBACKS]: {exc}")
        raise HTTPException(
            status_code=500, 
            detail=f"Không thể truy vấn CSDL: {str(exc)}"
        ) from exc


@app.post("/admin/feedbacks/restore")
def restore_admin_feedbacks_endpoint(
    req: FeedbackBackupRequest, _admin: HTTPBasicCredentials = Depends(require_admin)
):
    """Restore an exported feedback backup without overwriting existing feedback IDs."""
    try:
        imported, mirror_synced = feedback_store.restore_feedbacks(
            [record.model_dump() for record in req.feedbacks]
        )
        if not mirror_synced:
            raise HTTPException(
                status_code=500,
                detail="Đã nhập phản hồi vào SQLite nhưng không đồng bộ được bản mirror.",
            )
        rebuild_feedback_training_data(feedback_store.get_all_feedback())
        recommender.reload()
    except HTTPException:
        raise
    except (OSError, ValueError, sqlite3.Error, json.JSONDecodeError) as exc:
        logger.exception("Failed to restore feedback backup")
        raise HTTPException(status_code=500, detail="Không thể khôi phục bản sao lưu phản hồi.") from exc
    return {
        "status": "restored",
        "imported_feedbacks": imported,
        "total_feedbacks": len(feedback_store.get_all_feedback()),
    }

@app.get("/debug/valid-careers")
def debug_valid_careers():
    try:
        return {
            "career_ids": getattr(recommender, "career_ids", []),
            "career_groups": CAREER_GROUP_LIST
        }
    except Exception as exc:
        return {"error": str(exc)}
    
    @app.get("/debug/db-check")
def debug_db_check():
    from career_ai import db
    import os
    
    turso_url = os.environ.get("TURSO_DATABASE_URL", "")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN", "")
    
    info = {
        "using_turso_env": db.using_turso(),
        "has_url": bool(turso_url),
        "has_token": bool(turso_token),
        "url_preview": turso_url[:15] + "..." if turso_url else "MISSING",
    }
    
    try:
        with db.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM feedbacks")
            count = cursor.fetchone()[0]
            info["status"] = "SUCCESS"
            info["feedbacks_count"] = count
    except Exception as exc:
        info["status"] = "ERROR"
        info["error_type"] = type(exc).__name__
        info["error_detail"] = str(exc)
        
    return info
@app.delete("/admin/feedbacks/{feedback_id}")
def delete_admin_feedback_endpoint(
    feedback_id: str, _admin: HTTPBasicCredentials = Depends(require_admin)
):
    """Xóa phản hồi khỏi SQLite và bản mirror JSON."""
    try:
        deleted, mirror_synced = feedback_store.delete_feedback(feedback_id)
    except (OSError, ValueError, sqlite3.Error) as exc:
        logger.exception("Failed to delete feedback %s", feedback_id)
        raise HTTPException(status_code=500, detail="Không thể xóa phản hồi.") from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Không tìm thấy phản hồi.")
    training_data_synced = False
    try:
        rebuild_feedback_training_data(feedback_store.get_all_feedback())
        training_data_synced = True
    except (OSError, ValueError, sqlite3.Error, json.JSONDecodeError):
        logger.exception("Deleted feedback %s but failed to update training data", feedback_id)
    if not mirror_synced or not training_data_synced:
        raise HTTPException(
            status_code=500,
            detail="Phản hồi đã bị xóa, nhưng không thể đồng bộ toàn bộ dữ liệu liên quan.",
        )
    recommender_updated = False
    try:
        recommender.reload()
        recommender_updated = True
    except (OSError, ValueError, json.JSONDecodeError):
        logger.exception("Deleted feedback %s but failed to update recommender", feedback_id)
        raise HTTPException(
            status_code=500,
            detail="Phản hồi đã bị xóa, nhưng chưa thể cập nhật bộ gợi ý.",
        )
    return {
        "status": "deleted",
        "feedback_id": feedback_id,
        "mirror_synced": mirror_synced,
        "training_data_synced": training_data_synced,
        "recommender_updated": recommender_updated,
    }


@app.post("/admin/maintenance/retention")
def run_retention_cleanup_endpoint(_admin: HTTPBasicCredentials = Depends(require_admin)):
    """Run the configured data-retention cleanup immediately."""
    from career_ai.retention_service import purge_expired_data

    try:
        return purge_expired_data()
    except (OSError, ValueError, sqlite3.Error, json.JSONDecodeError) as exc:
        logger.exception("Manual retention cleanup failed")
        raise HTTPException(status_code=500, detail="Không thể dọn dữ liệu quá hạn.") from exc


@app.get("/admin/logs")
def admin_logs_endpoint(limit: int = 50, _admin: HTTPBasicCredentials = Depends(require_admin)):
    """Lấy danh sách nhật ký dự đoán mới nhất từ SQLite."""
    from career_ai import db
    return {"logs": db.get_prediction_logs(limit=limit)}
