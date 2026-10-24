# -*- coding: utf-8 -*-
"""
web/app.py — Cổng Tư Vấn & Định Hướng Nghề Nghiệp CNTT Chuẩn DSS (Streamlit Client).

Nguyên tắc kiến trúc:
1. Giao diện KHÔNG nạp model trực tiếp; nó là Web Client kết nối với FastAPI REST API qua HTTP.
2. Trải nghiệm người dùng tách biệt rõ ràng & hợp lý:
   - Cổng Dành Cho Sinh Viên: Thiết kế hiện đại, tập trung vào trải nghiệm người dùng,
     nhập điểm theo nhóm môn học, hỗ trợ hồ sơ mẫu nhanh, upload bảng điểm cá nhân,
     và báo cáo tư vấn chuyên sâu từ AI (Groq).
   - Khu Vực Quản Trị Viên (Admin Portal): Được bảo vệ bằng đăng nhập bảo mật,
     cung cấp thống kê, phân tích phản hồi sinh viên, xem lịch sử tư vấn
     và điều khiển chu trình tự động Retrain.
3. Địa chỉ API đọc từ biến môi trường API_URL (mặc định: http://127.0.0.1:8000).

Cách chạy:
    streamlit run web/app.py
    hoặc: cd web && streamlit run app.py
"""
import html
import os
import sys
import io
import json
import time
import requests
import streamlit as st
import pandas as pd
# Thiết lập cấu hình trang
st.set_page_config(
    page_title="AI Career Compass — Cổng Định Hướng Nghề Nghiệp CNTT",
    layout="wide",
    initial_sidebar_state="expanded",
)

api_url = os.environ.get("API_URL")
if not api_url:
    try:
        api_url = st.secrets.get("API_URL")
    except FileNotFoundError:
        api_url = None

API_URL = (api_url or "http://127.0.0.1:8000").strip().rstrip("/")
if not API_URL.startswith(("http://", "https://")):
    API_URL = "http://" + API_URL  # Render chỉ cấp host:port, không kèm scheme

try:
    import ui_kit as ui  # CSS + thành phần HTML/SVG của giao diện hiện đại (web/ui_kit.py)
except ModuleNotFoundError:
    sys.path.insert(0, os.path.dirname(__file__))
    import ui_kit as ui

st.markdown(ui.CSS, unsafe_allow_html=True)

# Phân nhóm 4 khối môn học cho trải nghiệm nhập liệu trực quan
SUBJECT_CATEGORIES = {
    "sys": {
        "title": "Mạng & Hệ Thống",
        "desc": "Hạ tầng & An toàn thông tin",
        "keys": ["network", "linux", "sec"],
    },
    "data": {
        "title": "Dữ Liệu & Phân Tích",
        "desc": "CSDL & Hệ thống thông tin",
        "keys": ["db", "analysis"],
    },
    "dev": {
        "title": "Kỹ Thuật Phần Mềm & Web",
        "desc": "Lập trình ứng dụng & Thiết kế",
        "keys": ["se", "java", "csharp", "web", "graphics"],
    },
    "ai": {
        "title": "AI & Công Nghệ Mới",
        "desc": "Trí tuệ nhân tạo & Xử lý ảnh",
        "keys": ["ai", "image"],
    },
}


# ---------------------------------------------------------------------------
# CÁC HÀM XỬ LÝ PARSER BẢNG ĐIỂM (GIỮ NGUYÊN TƯƠNG THÍCH VỚI BỘ TEST)
# ---------------------------------------------------------------------------
def _normalize_text(value):
    """Chuẩn hoá chuỗi để so khớp tên môn học giữa Excel/CSV và SUBJECTS."""
    import unicodedata
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return " ".join(text.replace("_", " ").replace("-", " ").replace("/", " ").split())


def parse_uploaded_scores(df, subject_names, subject_keys):
    """Trích xuất điểm 12 môn học từ file Excel/CSV theo nhiều định dạng khác nhau."""
    if df is None or df.empty:
        return {}

    def normalize_piece(v):
        return " ".join(
            _normalize_text(v)
            .replace("\xa0", " ")
            .replace("đ", "d")
            .replace("ơ", "o")
            .replace("ư", "u")
            .split()
        )

    course_code_map = {
        "th4306": "Công nghệ phần mềm",
        "th4320": "Trí tuệ nhân tạo",
        "th5206": "Mạng máy tính",
        "th5209": "Xử lý ảnh",
        "th4316": "Công nghệ Java",
        "th5208": "Phân tích thiết kế HTTT",
        "th5221": "Hệ quản trị CSDL",
        "th4315": "Ngôn ngữ C# và công nghệ .NET",
        "th5210": "An toàn và bảo mật HTTT",
        "th5231": "Kỹ thuật đồ hoạ máy tính",
        "th5211": "Hệ điều hành Linux",
        "th4309": "Công nghệ web",
    }

    alias_to_subject = {}
    for subj in subject_names:
        key = subject_keys.get(subj)
        aliases = [subj, key]
        if key:
            aliases.append(key.lower())
        for alias in aliases:
            norm = normalize_piece(alias)
            if norm:
                alias_to_subject.setdefault(norm, subj)

        subject_aliases = {
            "An toàn và bảo mật HTTT": ["an toan va bao mat htnn", "attt", "atbm", "bao mat", "security", "sec"],
            "Công nghệ phần mềm": ["cong nghe phan mem", "phan mem", "software engineering", "se"],
            "Hệ điều hành Linux": ["he dieu hanh linux", "linux"],
            "Hệ quản trị CSDL": ["he quan tri csdl", "csdl", "sql", "db"],
            "Kỹ thuật đồ hoạ máy tính": ["ky thuat do hoa may tinh", "do hoa", "graphics"],
            "Mạng máy tính": ["mang may tinh", "mmt", "network"],
            "Phân tích thiết kế HTTT": ["phan tich thiet ke htnn", "analysis"],
            "Xử lý ảnh": ["xu ly anh", "image processing", "image"],
            "Công nghệ Java": ["cong nghe java", "java"],
            "Ngôn ngữ C# và công nghệ .NET": ["ngon ngu csharp", "csharp", "dotnet"],
            "Công nghệ web": ["cong nghe web", "web"],
            "Trí tuệ nhân tạo": ["tri tue nhan tao", "ai"],
        }
        for alias_name, extra_aliases in subject_aliases.items():
            if normalize_piece(alias_name) == normalize_piece(subj):
                for extra in extra_aliases:
                    alias_to_subject.setdefault(normalize_piece(extra), subj)
        for code, subject_name in course_code_map.items():
            if normalize_piece(subject_name) == normalize_piece(subj):
                alias_to_subject.setdefault(code.lower(), subj)

    def match_subject_name(label):
        norm = normalize_piece(label)
        if not norm:
            return None
        if norm in alias_to_subject:
            return alias_to_subject[norm]

        compact = "".join(char for char in norm if char.isalnum())
        for code, subject_name in course_code_map.items():
            if code in compact:
                return subject_name

        candidates = []
        for alias, subject in alias_to_subject.items():
            if len(alias) > 2 and alias in norm:
                candidates.append((len(alias), subject))
        if candidates:
            return max(candidates, key=lambda item: item[0])[1]
        return None

    def parse_score(raw_value):
        if raw_value is None or pd.isna(raw_value):
            return None
        try:
            value = float(str(raw_value).replace(",", ".").strip())
        except (TypeError, ValueError):
            return None
        return value if 0.0 <= value <= 10.0 else None

    def assign_score(subject_name, raw_value):
        val = parse_score(raw_value)
        if val is not None:
            key = subject_keys.get(subject_name)
            if key:
                scores[key] = val
                return True
        return False

    scores = {}

    # 1) Dạng ngang: cột tên môn hoặc mã môn là tên cột; lấy điểm từ cột đó.
    for subj in subject_names:
        if subject_keys.get(subj) in scores:
            continue
        for col in df.columns:
            if match_subject_name(col) == subj:
                for value in df[col].tolist():
                    if assign_score(subj, value):
                        break
                if subject_keys.get(subj) in scores:
                    break

    if len(scores) < len(subject_names):
        norm_cols = [normalize_piece(c) for c in df.columns]
        name_candidates = [
            i for i, c in enumerate(norm_cols)
            if any(token in c for token in [
                "ten mon", "ten hoc phan", "mon hoc", "hoc phan", "ma mon", "ma hoc phan",
                "ky hieu", "subject", "course", "course name", "subject name", "course code"
            ])
        ]
        score_candidates = [
            i for i, c in enumerate(norm_cols)
            if any(token in c for token in [
                "tbchp", "tbhp", "diem", "tong ket", "diem tb", "score", "marks",
                "grade", "point", "diem so", "final"
            ])
        ]
        if name_candidates and score_candidates:
            preferred_scores = sorted(
                score_candidates,
                key=lambda i: (
                    not any(token in norm_cols[i] for token in ("tbchp", "tbhp", "tong ket", "diem tb", "final")),
                    i,
                ),
            )
            best_scores = {}
            for name_idx in name_candidates:
                for score_idx in preferred_scores:
                    candidate_scores = {}
                    for _, row in df.iterrows():
                        matched = match_subject_name(row.iloc[name_idx])
                        value = parse_score(row.iloc[score_idx])
                        key = subject_keys.get(matched) if matched is not None else None
                        if key and value is not None:
                            candidate_scores[key] = value
                    if len(candidate_scores) > len(best_scores):
                        best_scores = candidate_scores
            scores.update(best_scores)

    if len(scores) < len(subject_names):
        for subj in subject_names:
            if subject_keys.get(subj) in scores:
                continue
            for _, row in df.iterrows():
                for col_name, raw_value in row.items():
                    if match_subject_name(col_name) == subj:
                        assign_score(subj, raw_value)
                    elif match_subject_name(raw_value) == subj:
                        assign_score(subj, raw_value)
                    if subject_keys.get(subj) in scores:
                        break
                if subject_keys.get(subj) in scores:
                    break

    return scores


def parse_uploaded_file(uploaded_file, filename, subject_names, subject_keys):
    """Parse CSV/XLSX sheets and try header rows near the top of each sheet."""
    if filename.lower().endswith(".csv"):
        sheets = {"CSV": pd.read_csv(uploaded_file, header=None)}
    else:
        sheets = pd.read_excel(uploaded_file, sheet_name=None, header=None)

    best_scores = {}
    max_columns = 0
    for raw_df in sheets.values():
        max_columns = max(max_columns, raw_df.shape[1])
        for header_row in range(min(len(raw_df), 12)):
            headers = raw_df.iloc[header_row].fillna("").astype(str).str.strip().tolist()
            if not any(headers):
                continue
            body = raw_df.iloc[header_row + 1:].copy()
            body.columns = headers
            parsed = parse_uploaded_scores(body, subject_names, subject_keys)
            if len(parsed) > len(best_scores):
                best_scores = parsed
            if len(best_scores) == len(subject_names):
                return best_scores, max_columns
    return best_scores, max_columns


# ---------------------------------------------------------------------------
# CÁC HÀM GỌI API BACKEND
# ---------------------------------------------------------------------------
@st.cache_data(ttl=60)
def _fetch_model_info(api_url: str):
    """Lấy thông tin mô hình và danh mục; chỉ cache khi API phản hồi thành công."""
    res = requests.get(f"{api_url}/model-info", timeout=(5, 90))
    res.raise_for_status()
    return res.json()


def fetch_model_info():
    """Lấy thông tin mô hình và danh mục từ endpoint /model-info."""
    try:
        return _fetch_model_info(API_URL), None
    except requests.exceptions.HTTPError as e:
        return None, f"API trả về mã lỗi HTTP {e.response.status_code}"
    except requests.exceptions.RequestException as e:
        return None, str(e)


@st.cache_data(ttl=600)
def _load_career_catalog():
    """Đọc danh mục nghề nghiệp để hiển thị trang khám phá theo nhóm."""
    catalog_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "careers.json")
    with open(catalog_path, encoding="utf-8") as catalog_file:
        catalog = json.load(catalog_file)
    if not isinstance(catalog, dict):
        raise ValueError("Danh mục nghề nghiệp cần có cấu trúc JSON dạng đối tượng.")
    return [career for career in catalog.values() if isinstance(career, dict)]


def _admin_request(method: str, path: str, timeout: int):
    """Gọi API quản trị bằng thông tin xác thực đã kiểm tra và lưu trong phiên."""
    auth = st.session_state.get("admin_api_auth")
    if not auth:
        st.error("Phiên quản trị đã hết hạn. Vui lòng đăng nhập lại.")
        return None
    try:
        response = requests.request(
            method, f"{API_URL}{path}", auth=auth, timeout=timeout
        )
        if response.status_code == 401:
            st.session_state["admin_authenticated"] = False
            st.session_state.pop("admin_api_auth", None)
            st.error("Thông tin đăng nhập quản trị không còn hợp lệ. Vui lòng đăng nhập lại.")
            return None
        if response.status_code == 503:
            st.error("Chưa cấu hình tài khoản quản trị trên máy chủ API.")
            return None
        if not response.ok:
            st.error(f"Yêu cầu quản trị thất bại (HTTP {response.status_code}).")
            return None
        return response.json()
    except requests.exceptions.RequestException as exc:
        st.error(f"Không thể truy cập chức năng quản trị ({type(exc).__name__}).")
        return None


def fetch_admin_stats():
    """Lấy số liệu thống kê quản trị từ endpoint /admin/stats."""
    return _admin_request("GET", "/admin/stats", timeout=4)


def fetch_admin_feedbacks(limit: int = 50):
    """Lấy danh sách phản hồi từ JSON qua /admin/feedbacks."""
    result = _admin_request("GET", f"/admin/feedbacks?limit={limit}", timeout=5)
    return result.get("feedbacks", []) if result else []


def fetch_admin_logs(limit: int = 50):
    """Lấy lịch sử tư vấn từ JSON qua /admin/logs."""
    result = _admin_request("GET", f"/admin/logs?limit={limit}", timeout=5)
    return result.get("logs", []) if result else []


# ---------------------------------------------------------------------------
# QUẢN LÝ TRẠNG THÁI (SESSION STATE)
# ---------------------------------------------------------------------------
def _init_session():
    if "view_mode" not in st.session_state:
        st.session_state["view_mode"] = "student"  # 'student' hoặc 'admin'
    if "admin_authenticated" not in st.session_state:
        st.session_state["admin_authenticated"] = False
    if "user_scores" not in st.session_state:
        st.session_state["user_scores"] = {}
    if "selected_skills" not in st.session_state:
        st.session_state["selected_skills"] = {}
    if "selected_interests" not in st.session_state:
        st.session_state["selected_interests"] = []

    if "explore_career_group" not in st.session_state:
        st.session_state["explore_career_group"] = None


# ---------------------------------------------------------------------------
# GIAO DIỆN CHÍNH
# ---------------------------------------------------------------------------
def main():
    _init_session()
    # Áp dụng điểm đã tải lên trước khi tạo bất kỳ widget nào trong lần chạy này.
    if "pending_file_scores" in st.session_state:
        pending = st.session_state.pop("pending_file_scores")
        for k, v in pending.items():
            st.session_state[f"grade_input_{k}"] = float(v)

    meta, error = fetch_model_info()

    # Xử lý điều hướng giữa Cổng Sinh Viên và Cổng Quản Trị
    view_mode = st.session_state.get("view_mode", "student")

    if view_mode == "admin":
        if not st.session_state.get("admin_authenticated"):
            render_admin_login()
        else:
            render_admin_portal(meta, error)
    else:
        render_student_portal(meta, error)


def render_career_group(group, career_catalog):
    """Hiển thị đầy đủ các nghề thuộc nhóm được chọn trong danh mục."""
    careers = [
        career for career in career_catalog
        if career.get("career_group") == group
    ]
    if not careers:
        st.error(f"Chưa có nghề nghiệp nào trong nhóm “{group}”.")
        return

    st.markdown(f"## {group}")
    st.caption(f"Khám phá {len(careers)} nghề thuộc nhóm này cùng mô tả, thông tin thị trường và nguồn tham khảo.")
    st.markdown(ui.career_explorer_grid(careers), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 1. CỔNG DÀNH CHO SINH VIÊN (STUDENT PORTAL)
# ---------------------------------------------------------------------------
def render_student_portal(meta, error):
    career_catalog = []
    catalog_error = None
    try:
        career_catalog = _load_career_catalog()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        catalog_error = f"Không thể tải danh mục nghề nghiệp: {exc}"

    with st.sidebar:
        selected_group = st.session_state.get("explore_career_group")
        with st.container(key="sidebar-sticky-top"):
            st.markdown(
                "<div class='sidebar-header'>"
                "<h2 class='sidebar-title'>Góc khám phá</h2>"
                "<p class='sidebar-tagline'>Bắt đầu từ điều bạn yêu thích và làm tốt.</p>"
                "</div>",
                unsafe_allow_html=True,
            )
            if st.button(
                "Trang chủ",
                key="btn_student_home",
                type="primary" if selected_group is None else "secondary",
                width="stretch",
                icon=":material/home:",
            ):
                st.session_state["explore_career_group"] = None
                st.rerun()

        with st.container(key="sidebar-menu-scroll"):
            st.markdown("---")
            st.markdown("#### Khám phá thử", help="Chọn nhóm nghề để xem các lựa chọn và thông tin tham khảo.")
            st.caption("Chọn một nhóm ngành để xem các nghề và thông tin liên quan:")

            if catalog_error:
                st.error(catalog_error)
            else:
                career_groups = list(dict.fromkeys(
                    str(career.get("career_group", "")).strip()
                    for career in career_catalog
                    if str(career.get("career_group", "")).strip()
                ))
                group_icons = {
                    "Phát triển phần mềm": ":material/code:",
                    "Phát triển Web": ":material/language:",
                    "Đồ họa & Game": ":material/sports_esports:",
                    "Dữ liệu & AI": ":material/bar_chart:",
                    "Hạ tầng & Bảo mật": ":material/dns:",
                    "Kiểm thử & Quản lý dự án": ":material/task_alt:",
                    "An toàn thông tin": ":material/shield:",
                }
                for idx, group in enumerate(career_groups):
                    if st.button(
                        group,
                        key=f"btn_explore_group_{idx}",
                        type="primary" if group == selected_group else "secondary",
                        width="stretch",
                        icon=group_icons.get(group, ":material/chevron_right:"),
                    ):
                        st.session_state["explore_career_group"] = group
                        st.rerun()

        with st.container(key="sidebar-footer"):
            if st.button(
                "Đăng nhập",
                key="btn_goto_admin_login",
                width="stretch",
                icon=":material/login:",
            ):
                st.session_state["view_mode"] = "admin"
                st.rerun()

    selected_group = st.session_state.get("explore_career_group")
    if selected_group:
        render_career_group(selected_group, career_catalog)
        return

    # Kiểm tra backend API
    if not meta:
        st.error(f"Chưa thể kết nối tới Backend API tại `{API_URL}`: {error}")
        if API_URL.startswith(("http://127.0.0.1", "http://localhost")):
            st.info("Đang chạy giao diện trên máy cá nhân? Hãy khởi động FastAPI trên cổng 8000.")
        else:
            st.info("Dịch vụ trực tuyến có thể đang khởi động lại. Hãy chờ một chút rồi thử kết nối lại; bạn không cần chạy code trên máy.")
        if st.button("Thử kết nối lại", key="retry_backend_connection"):
            st.rerun()
        return

    # Banner Hero
    st.markdown(ui.hero("Sinh viên"), unsafe_allow_html=True)

    # ------------------ BƯỚC 1: THÔNG TIN SINH VIÊN ------------------
    profile_intro, profile_form = st.columns([0.9, 1.8], gap="large", vertical_alignment="top")
    with profile_intro:
        st.markdown(
            "<div class='profile-editor-aside'>"
            "<span class='profile-editor-kicker'>HỒ SƠ CỦA BẠN</span>"
            "<div class='profile-editor-mark'>01</div>"
            "<h2>Mỗi hành trình<br>có một điểm bắt đầu.</h2>"
            "<p>Chọn năm học và chia sẻ những thông tin cần thiết cho gợi ý nghề nghiệp.</p>"
            "<div class='profile-editor-foot'><span></span> KHÔNG CẦN ĐIỀN TẤT CẢ</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    with profile_form:
        st.markdown(
            "<div class='profile-form-heading'>"
            "<span>THÔNG TIN CƠ BẢN</span>"
            "<p>Để những gợi ý bắt đầu gần với bạn hơn.</p>"
            "</div>",
            unsafe_allow_html=True,
        )

        academic_year = st.radio(
            "Bạn đang ở năm học nào?",
            options=["Năm 1", "Năm 2", "Năm 3", "Năm 4"],
            index=2,
            horizontal=True,
            help="Chọn năm gần với bạn nhất. Các môn chưa học vẫn có thể để trống.",
            key="select_academic_year",
        )

        is_early_student = academic_year in {"Năm 1", "Năm 2", "Năm 3"}
        if is_early_student:
            st.markdown(
                "<div class='profile-hint'>"
                "Môn nào chưa có điểm, bạn cứ để trống. Chỉ cần một môn đã có điểm là có thể bắt đầu."
                "</div>",
                unsafe_allow_html=True,
            )

    # ------------------ BƯỚC 2: BẢNG ĐIỂM HỌC PHẦN ------------------
    st.write("")
    with st.container(border=True, key="student-grade-card"):
        st.markdown(ui.section(2, "Những môn bạn đã học", "Nhập điểm các môn đã có kết quả. Môn chưa học cứ để trống, hoặc tải lên bảng điểm của bạn."), unsafe_allow_html=True)

        tab_manual, tab_file = st.tabs(["Nhập điểm", "Tải bảng điểm"])

        input_scores = {}
        subject_names = meta.get("subject_names", [])
        subject_keys = meta.get("subject_keys", {})
        key_to_name = meta.get("key_to_subject", {})

        with tab_manual:
            cols_cat = st.columns(2, gap="medium")

            for cat_idx, (cat_id, cat_info) in enumerate(SUBJECT_CATEGORIES.items()):
                c_block = cols_cat[cat_idx % 2]
                with c_block:
                    st.markdown(
                        ui.category_badge(cat_info["title"], cat_info["desc"], cat_id),
                        unsafe_allow_html=True,
                    )
                    for k in cat_info["keys"]:
                        subj_name = key_to_name.get(k, k)
                        grade_key = f"grade_input_{k}"
                        if grade_key not in st.session_state:
                            st.session_state[grade_key] = None
                        val = st.number_input(
                            subj_name,
                            min_value=0.0,
                            max_value=10.0,
                            value=None,
                            step=0.1,
                            format="%.1f",
                            placeholder="Để trống nếu chưa học",
                            key=grade_key,
                        )
                        if val is not None:
                            input_scores[k] = val

        with tab_file:
            uploaded_file = st.file_uploader(
                "Chọn hoặc kéo thả bảng điểm vào đây:",
                type=["xlsx", "csv"],
                help="Dùng bảng điểm Excel (.xlsx) hoặc CSV (.csv).",
                key="uploader_bang_diem",
            )
            if uploaded_file is not None:
                file_sig = f"{uploaded_file.name}_{uploaded_file.size}"
                if st.session_state.get("last_uploaded_sig") != file_sig:
                    try:
                        parsed_scores, column_count = parse_uploaded_file(
                            uploaded_file, uploaded_file.name, subject_names, subject_keys
                        )
                        if parsed_scores:
                            st.session_state["pending_file_scores"] = parsed_scores
                            st.session_state["last_uploaded_sig"] = file_sig
                            st.session_state["last_uploaded_name"] = uploaded_file.name
                            st.session_state["last_parsed_scores"] = parsed_scores
                            st.toast("Đã thêm các môn có điểm từ bảng điểm của bạn.")
                            st.rerun()
                        else:
                            st.warning("Chưa tìm thấy môn học phù hợp trong tệp này. Bạn có thể thử một bảng điểm khác hoặc nhập điểm thủ công.")
                    except Exception as e:
                        st.error(f"Lỗi khi đọc file: {str(e)}")
                else:
                    # File đã được xử lý xong, hiển thị kết quả và bảng xem trước
                    last_scores = st.session_state.get("last_parsed_scores", {})
                    st.success(f"Đã thêm điểm của {len(last_scores)} môn từ bảng điểm.")
                    input_scores.update(last_scores)
                    preview_data = [{"Môn học": key_to_name.get(k, k), "Điểm trích xuất": v} for k, v in last_scores.items()]
                    st.dataframe(pd.DataFrame(preview_data), width="stretch", hide_index=True)
            else:
                # Người dùng đã gỡ file
                st.session_state.pop("last_uploaded_sig", None)
                st.session_state.pop("last_uploaded_name", None)
                st.session_state.pop("last_parsed_scores", None)

    # ------------------ BƯỚC 3: KỸ NĂNG MỀM & SỞ THÍCH ------------------
    st.write("")
    with st.container(border=True, key="student-interests-card"):
        st.markdown(ui.section(3, "Điều bạn yêu thích & làm tốt", "Chọn những điều thể hiện con người và mối quan tâm của bạn."), unsafe_allow_html=True)
        col_skills, col_interests = st.columns(2, gap="medium")

        soft_skills_cfg = meta.get("soft_skills", [])
        skill_levels_cfg = meta.get("skill_levels", [])
        UNASSESSED_LABEL = "Chưa đánh giá"
        level_labels = [UNASSESSED_LABEL] + [opt["label"] for opt in skill_levels_cfg]
        level_keys = [""] + [opt["key"] for opt in skill_levels_cfg]

        user_skills = {}
        with col_skills:
            st.markdown(
                "<div class='sub-column-title'><span class='bar-accent'></span><strong>Kỹ năng tự tin</strong></div>",
                unsafe_allow_html=True,
            )
            cols_s = st.columns(2)
            for idx, sk in enumerate(soft_skills_cfg):
                sk_key = sk["key"]
                sk_label = sk["label"]
                col_s = cols_s[idx % 2]
                saved_key = st.session_state.get("selected_skills", {}).get(sk_key, "")
                saved_idx = level_keys.index(saved_key) if saved_key in level_keys else 0

                chosen_label = col_s.selectbox(
                    sk_label,
                    options=level_labels,
                    index=saved_idx,
                    key=f"skill_select_{sk_key}",
                )
                chosen_key = level_keys[level_labels.index(chosen_label)]
                if chosen_key:
                    user_skills[sk_key] = chosen_key

        with col_interests:
            st.markdown(
                "<div class='sub-column-title'><span class='bar-accent'></span><strong>Lĩnh vực yêu thích</strong></div>",
                unsafe_allow_html=True,
            )
            interest_options = meta.get("interest_options", [])
            saved_interests = [i for i in st.session_state.get("selected_interests", []) if i in interest_options]

            user_interests = st.multiselect(
                "Chọn những lĩnh vực bạn muốn tìm hiểu:",
                options=interest_options,
                default=saved_interests,
                placeholder="Chọn một hoặc vài lĩnh vực",
                key="interests_multiselect",
            )

    store_scores_in_logs = st.checkbox(
        "Cho phép lưu điểm môn học trong nhật ký để cải thiện chất lượng gợi ý.",
        value=False,
        key="store_scores_in_logs",
    )
    st.caption(
        "Nếu không chọn, hệ thống vẫn tạo gợi ý nhưng không lưu điểm vào nhật ký. "
        "Tên của bạn không cần thiết cho việc tư vấn."
    )

    # ------------------ NÚT HÀNH ĐỘNG PHÂN TÍCH ------------------
    st.write("")
    submit_button = st.button("Khám phá hướng đi phù hợp", type="primary", width="stretch", icon=":material/arrow_forward:")

    if submit_button:
        payload = {
            "scores": input_scores,
            "skills": user_skills,
            "interests": user_interests,
            "store_scores_in_logs": store_scores_in_logs,
            "allow_partial": is_early_student or len(input_scores) < len(subject_keys),
        }
        with st.spinner("Đang kết nối những điều bạn chia sẻ với các hướng nghề nghiệp..."):
            try:
                t0 = time.time()
                res = requests.post(f"{API_URL}/decision", json=payload, timeout=25)
                ms = round((time.time() - t0) * 1000)
                if res.status_code == 200:
                    st.session_state["result"] = {"data": res.json(), "scores": dict(input_scores), "ms": ms}
                    st.session_state.pop("error", None)
                    st.toast("Gợi ý dành cho bạn đã sẵn sàng.")
                elif res.status_code == 422:
                    st.session_state["error"] = f"Dữ liệu đầu vào chưa hợp lệ (HTTP 422): {res.json().get('detail')}"
                else:
                    st.session_state["error"] = f"Lỗi từ máy chủ API (HTTP {res.status_code}): {res.text[:300]}"
            except requests.exceptions.RequestException as ex:
                st.session_state["error"] = f"Không thể kết nối đến máy chủ API: {ex}"

    # Hiển thị lỗi hoặc Kết quả
    if st.session_state.get("error"):
        st.error(st.session_state["error"])
    elif st.session_state.get("result"):
        render_results(st.session_state["result"])


# ---------------------------------------------------------------------------
# HIỂN THỊ KẾT QUẢ TƯ VẤN (DSS RESULTS)
# ---------------------------------------------------------------------------
def render_results(r: dict):
    d, scores = r["data"], r["scores"]
    top = d.get("top_careers", []) or []
    llm = d.get("explanation_llm", {}) or {}
    student_name = "Sinh viên"

    st.markdown("<div id='ket-qua'></div>", unsafe_allow_html=True)
    st.write("")

    if d.get("is_partial_assessment"):
        st.info(
            f"Đây là những gợi ý ban đầu, dựa trên {d.get('completed_subjects_count', len(scores))} môn bạn đã có điểm. "
            "Khi hành trình học tập tiếp tục, bạn có thể quay lại để khám phá thêm."
        )

    # Thẻ Hero kết quả
    st.markdown(
        ui.result_hero(
            d.get("predicted_group", ""),
            float(d.get("confidence", 0) or 0),
            top[0].get("career_name", "") if top else "",
            float(top[0].get("match_percentage", 0)) if top else 0.0,
            bool(d.get("adjusted_by_preferences")),
            student_name=student_name,
            score_based_group=d.get("model_predicted_group", ""),
        ),
        unsafe_allow_html=True,
    )
    # Hồ sơ môn học và các lĩnh vực nổi bật
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.markdown(ui.radar_svg(scores), unsafe_allow_html=True)
    with c2:
        st.markdown(ui.prob_bars(d.get("probabilities_model_only", {})), unsafe_allow_html=True)

    # Lời khuyên cá nhân hóa
    st.write("")
    st.markdown(ui.section(4, "Một vài lời dành riêng cho bạn", "Góc nhìn tham khảo về những điểm mạnh và hướng phát triển có thể phù hợp."), unsafe_allow_html=True)
    st.markdown(
        ui.explain_card(
            llm.get("explanation", ""),
            llm.get("note", ""),
            bool(llm.get("is_ai_generated")),
            d.get("disclaimer", llm.get("disclaimer", "")),
        ),
        unsafe_allow_html=True,
    )

    # Các lựa chọn nghề nghiệp
    st.write("")
    st.markdown(ui.section(5, "Những nghề đáng để khám phá", "Một vài lựa chọn để bạn tìm hiểu thêm, không phải khuôn mẫu hay giới hạn."), unsafe_allow_html=True)
    st.markdown(ui.career_grid(top), unsafe_allow_html=True)

    # Khuyến nghị môn học kỳ tới (nếu có môn cốt lõi chưa học)
    unstudied_all = []
    for c in top:
        for u in c.get("unstudied_core", []):
            if u["subject"] not in unstudied_all:
                unstudied_all.append(u["subject"])
    if unstudied_all:
        st.warning(
            f"**Có thể tìm hiểu thêm:** Những môn như **{', '.join(unstudied_all)}** sẽ giúp bạn khám phá sâu hơn các hướng nghề này."
        )

    # Phân tích Thế mạnh & Môn cần cải thiện
    st.write("")
    st.markdown(ui.section(6, "Thế mạnh & những điều có thể bồi đắp"), unsafe_allow_html=True)
    a, b = st.columns(2, gap="medium")
    with a:
        st.markdown(ui.tags(d.get("strengths", []), "good", "Mỗi hành trình đều có điểm khởi đầu riêng.", "Điểm bạn đang làm tốt"), unsafe_allow_html=True)
    with b:
        st.markdown(ui.tags(d.get("improvements", []), "todo", "Hãy tiếp tục nuôi dưỡng những điều bạn yêu thích.", "Có thể tìm hiểu thêm"), unsafe_allow_html=True)

    # Phản hồi từ sinh viên
    st.write("")
    with st.container(key="feedback-panel", border=True):
        st.markdown(
            """
            <div class="feedback-heading">
                <p class="feedback-eyebrow">PHẢN HỒI CỦA BẠN</p>
                <h3>Gợi ý này có phù hợp với bạn?</h3>
                <p>Chia sẻ cảm nhận để những lần khám phá sau hữu ích hơn.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("Khảo sát nhanh (không bắt buộc)"):
            survey_scale = [
                "Chưa trả lời",
                "1 - Rất thấp",
                "2 - Thấp",
                "3 - Bình thường",
                "4 - Cao",
                "5 - Rất cao",
            ]
            relevance_choice = st.selectbox(
                "Gợi ý phù hợp với mối quan tâm của bạn ở mức nào?",
                survey_scale,
                key="fb_survey_relevance",
            )
            usefulness_choice = st.selectbox(
                "Kết quả hữu ích với bạn ở mức nào?",
                survey_scale,
                key="fb_survey_usefulness",
            )
            explore_choice = st.selectbox(
                "Bạn có dự định tìm hiểu thêm nghề được gợi ý không?",
                ["Chưa trả lời", "Có", "Có thể", "Không"],
                key="fb_survey_explore_intent",
            )

        survey = {}
        for key, choice in (
            ("relevance", relevance_choice),
            ("usefulness", usefulness_choice),
        ):
            if choice != "Chưa trả lời":
                survey[key] = int(choice[0])
        explore_intent = {
            "Có": "yes",
            "Có thể": "maybe",
            "Không": "no",
        }.get(explore_choice)
        if explore_intent:
            survey["explore_intent"] = explore_intent

        f_col1, f_col2 = st.columns(2, gap="medium")
        with f_col1:
            st.button(
                "Phù hợp",
                key="fb_like",
                type="primary" if st.session_state.get("fb_liked") is True else "secondary",
                width="stretch",
                on_click=_set_feedback_choice,
                args=(True,),
            )
        with f_col2:
            st.button(
                "Chưa phù hợp",
                key="fb_dislike",
                type="primary" if st.session_state.get("fb_liked") is False else "secondary",
                width="stretch",
                on_click=_set_feedback_choice,
                args=(False,),
            )

        st.markdown("**Mức độ phù hợp**")
        st.session_state.setdefault("fb_rating", 0)
        current_rating = int(st.session_state["fb_rating"])
        star_columns = st.columns([1, 1, 1, 1, 1, 14], gap="small")
        for star_value, star_column in enumerate(star_columns[:5], start=1):
            with star_column:
                star_label = "★" if star_value <= current_rating else "☆"
                st.button(
                    star_label,
                    key=f"fb_rating_star_{star_value}",
                    help=f"Chọn {star_value} trên 5 sao",
                    type="primary" if star_value <= current_rating else "secondary",
                    width="stretch",
                    on_click=_set_feedback_rating,
                    args=(star_value,),
                )
        rating_star = int(st.session_state["fb_rating"])
        fb_comment = st.text_area(
            "Chia sẻ thêm (không bắt buộc; vui lòng không ghi thông tin cá nhân)",
            placeholder="Ví dụ: Mình muốn tìm hiểu thêm về thiết kế giao diện...",
            key="fb_comment_text",
            height=72,
        )
        include_scores = st.checkbox(
            "Tôi đồng ý gửi kèm điểm môn học trong phản hồi để cải thiện gợi ý.",
            value=False,
            key="fb_include_scores",
        )
        st.caption(
            "Phản hồi sẽ được lưu để cải thiện hệ thống. Tên của bạn không được gửi; "
            "điểm chỉ được lưu nếu bạn chọn đồng ý ở trên."
        )

        if st.button(
            "Gửi phản hồi",
            key="fb_submit",
            type="primary",
            icon=":material/arrow_forward:",
            width="stretch",
        ):
            liked = st.session_state.get("fb_liked")
            if liked is None:
                st.warning("Vui lòng chọn phản hồi phù hợp hoặc chưa phù hợp.")
            else:
                _send_feedback(
                    d, top, liked=liked, rating=rating_star or None, comment=fb_comment,
                    survey=survey, include_scores=include_scores,
                )


def _set_feedback_choice(liked: bool) -> None:
    """Remember the selected fit response until the user submits the form."""
    st.session_state["fb_liked"] = liked


def _set_feedback_rating(rating: int) -> None:
    """Update the rating before Streamlit reruns the feedback section."""
    st.session_state["fb_rating"] = rating


def _send_feedback(
    decision: dict,
    top_careers: list,
    liked: bool,
    rating: int | None = None,
    comment: str = "",
    survey: dict | None = None,
    include_scores: bool = False,
):
    """Gửi phản hồi; chỉ kèm điểm nếu người dùng đã đồng ý."""
    if not top_careers:
        st.error("Không có nghề để ghi nhận phản hồi.")
        return
    scores = st.session_state.get("result", {}).get("scores", {}) if include_scores else {}
    payload = {
        "career_id": top_careers[0]["career_id"],
        "top_group": decision["predicted_group"],
        "top_prob": float(
            decision.get(
                "model_probability_for_recommendation_group",
                decision.get("confidence", 0.0),
            )
        ) / 100.0,
        "liked": liked,
        "rating": rating,
        "comment": comment,
        "scores": scores,
        "include_scores": include_scores,
        "survey": survey or {},
    }
    try:
        response = requests.post(f"{API_URL}/feedback", json=payload, timeout=20)
        if response.status_code == 201:
            result = response.json()
            if result.get("recommender_updated", True) and result.get("mirror_synced", True):
                st.toast("Cảm ơn bạn! Phản hồi đã được ghi nhận.")
            else:
                st.warning(
                    "Phản hồi đã được lưu, nhưng chưa cập nhật được bản mirror hoặc gợi ý. "
                    "Quản trị viên cần kiểm tra log máy chủ."
                )
        else:
            st.error(f"Không thể lưu phản hồi (HTTP {response.status_code}).")
    except requests.exceptions.RequestException as exc:
        st.error(f"Không thể gửi phản hồi tới máy chủ: {exc}")


# ---------------------------------------------------------------------------
# 2. KHU VỰC ĐĂNG NHẬP QUẢN TRỊ VIÊN (ADMIN LOGIN)
# ---------------------------------------------------------------------------
def render_admin_login():
    """Giao diện đăng nhập đồng bộ với cổng sinh viên."""
    with st.sidebar:
        with st.container(key="sidebar-sticky-top"):
            st.markdown(
                "<div class='sidebar-header'>"
                "<h2 class='sidebar-title'>Đăng nhập</h2>"
                "<p class='sidebar-tagline'>Khu vực dành cho cán bộ được cấp quyền.</p>"
                "</div>",
                unsafe_allow_html=True,
            )
            if st.button("Trang chủ", key="btn_admin_login_home", width="stretch", icon=":material/home:"):
                st.session_state["view_mode"] = "student"
                st.session_state["explore_career_group"] = None
                st.rerun()

    with st.container(key="admin-login-card", border=True):
        st.markdown(
            "<h2>Đăng nhập</h2>"
            "<p>Đăng nhập để quản lý dữ liệu phản hồi và hoạt động của hệ thống.</p>",
            unsafe_allow_html=True,
        )
        with st.form("admin_login_form"):
            username_input = st.text_input("Tên đăng nhập", value="", placeholder="Nhập tên đăng nhập")
            password_input = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu")
            login_submitted = st.form_submit_button("Đăng nhập", type="primary", width="stretch")

            if login_submitted:
                try:
                    response = requests.get(
                        f"{API_URL}/admin/auth",
                        auth=(username_input.strip(), password_input),
                        timeout=5,
                    )
                    if response.status_code == 200:
                        st.session_state["admin_api_auth"] = (
                            username_input.strip(), password_input
                        )
                        st.session_state["admin_authenticated"] = True
                        st.toast("Đăng nhập thành công.")
                        st.rerun()
                    elif response.status_code == 401:
                        st.error("Tên đăng nhập hoặc mật khẩu không chính xác.")
                    elif response.status_code == 503:
                        st.error("Chưa cấu hình tài khoản quản trị trên máy chủ API.")
                    else:
                        st.error(f"Không thể xác thực với máy chủ (HTTP {response.status_code}).")
                except requests.exceptions.RequestException as exc:
                    st.error(f"Không thể kết nối máy chủ xác thực ({type(exc).__name__}).")

# ---------------------------------------------------------------------------
# 3. BẢNG ĐIỀU KHIỂN QUẢN TRỊ VIÊN (ADMIN PORTAL DASHBOARD)
# ---------------------------------------------------------------------------
def render_admin_portal(meta, error):
    """Trang Dashboard Quản Trị với đầy đủ công cụ giám sát, feedback và retrain."""
    with st.sidebar:
        admin_auth = st.session_state.get("admin_api_auth", ("", ""))
        admin_user = html.escape(admin_auth[0]) if admin_auth[0] else "Quản trị viên"
        with st.container(key="sidebar-sticky-top"):
            st.markdown(
                "<div class='sidebar-header'>"
                "<div class='sidebar-admin-header'>"
                "<div class='sidebar-admin-badge'>"
                "<svg width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='#FFFFFF' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
                "<path d='M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'></path>"
                "</svg>"
                "</div>"
                "<div>"
                f"<h2 class='sidebar-title' style='margin:0;font-size:1.15rem'>Quản Trị Viên</h2>"
                f"<p class='sidebar-tagline' style='margin:0'>Xin chào, {admin_user}</p>"
                "</div>"
                "</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            st.markdown("---")

            if st.button("Trang chủ", key="btn_admin_home", width="stretch", icon=":material/home:"):
                st.session_state["view_mode"] = "student"
                st.session_state["explore_career_group"] = None
                st.rerun()

        with st.container(key="sidebar-menu-scroll"):
            if st.button("Đăng Xuất", key="btn_admin_logout", width="stretch", icon=":material/logout:"):
                st.session_state["admin_authenticated"] = False
                st.session_state.pop("admin_api_auth", None)
                st.session_state["view_mode"] = "student"
                st.toast("Đã đăng xuất khỏi tài khoản Quản trị viên.")
                st.rerun()

            st.markdown("---")
            st.markdown("#### Thao tác nhanh")
            if st.button("Làm mới dữ liệu", key="btn_refresh_admin_data", width="stretch", icon=":material/refresh:"):
                st.rerun()

    st.markdown("## Bảng Điều Khiển Quản Trị Hệ Thống")
    st.caption("Theo dõi hoạt động hệ thống, xem phản hồi sinh viên và cập nhật gợi ý từ ý kiến nhận được.")

    stats = fetch_admin_stats() or {}
    total_preds = stats.get('total_predictions') or 0
    total_feedbacks = stats.get('total_feedbacks') or 0
    satisfaction = stats.get('feedback_satisfaction_pct') or 0
    raw_latency = stats.get('avg_latency_ms') or 0
    try:
        latency_val = float(raw_latency) / 1000.0
    except (ValueError, TypeError):
        latency_val = 0.0

    def _render_kpi(t: str, v: str, s: str = "", ic: str = "bar") -> str:
        try:
            return ui.kpi_card(t, v, s, ic)
        except TypeError:
            return ui.kpi_card(t, v, s)

    # 4 Thẻ KPI thống kê nhanh
    st.markdown("<div class='kpi-grid'>"
                + _render_kpi("LƯỢT TƯ VẤN ĐÃ THỰC HIỆN", str(total_preds), "Số phiên được lưu (60 ngày gần nhất)", "bar")
                + _render_kpi("PHẢN HỒI ĐÃ NHẬN", str(total_feedbacks), "Ý kiến từ sinh viên", "mail")
                + _render_kpi("MỨC HÀI LÒNG", f"{satisfaction}%", "Đánh giá tích cực", "smile")
                + _render_kpi("THỜI GIAN PHẢN HỒI", f"{latency_val:.2f}s", "Độ trễ trung bình", "clock")
                + "</div>", unsafe_allow_html=True)

    tab_overview, tab_feedbacks, tab_logs, tab_retrain = st.tabs([
        "Tổng quan & Sức khỏe hệ thống",
        "Quản lý Phản hồi Sinh viên",
        "Lịch sử tư vấn",
        "Cập nhật hệ thống",
    ])

    # Tab 1: Tổng quan hệ thống
    with tab_overview:
        st.markdown("#### Lưu giữ và dọn dữ liệu")
        st.caption(
            "Phản hồi được giữ cho đến khi quản trị viên chủ động xóa; nhật ký tư vấn và tương tác "
            "được giữ 60 ngày. Dọn dữ liệu không tự huấn luyện lại model."
        )
        if st.button("Dọn dữ liệu đã quá hạn ngay", key="run_retention_cleanup"):
            cleanup_result = _admin_request(
                "POST", "/admin/maintenance/retention", timeout=30
            )
            if cleanup_result is not None:
                st.success("Đã hoàn tất dọn dữ liệu đến hạn.")
                st.json(cleanup_result)

        col_m1, col_m2 = st.columns(2, gap="medium")
        with col_m1:
            with st.container(border=True):
                st.markdown("#### Trạng thái hệ thống")
                if meta:
                    st.markdown(ui.status_card(True, meta.get("version", "1.0.0"), API_URL), unsafe_allow_html=True)
                else:
                    st.markdown(ui.status_card(False, "-", API_URL), unsafe_allow_html=True)

        with col_m2:
            with st.container(border=True):
                st.markdown(
                    "<div class='card-title-bar'><span class='bar-accent'></span><h4>Phân bổ nhóm ngành được gợi ý</h4></div>",
                    unsafe_allow_html=True,
                )
                group_dist = stats.get("group_distribution", {})
                if group_dist:
                    st.markdown(ui.admin_group_distribution(group_dist), unsafe_allow_html=True)
                else:
                    st.info("Chưa có đủ lượt tư vấn để hiển thị.")

    # Tab 2: Quản lý Phản hồi Sinh viên
    with tab_feedbacks:
        survey = stats.get("student_survey", {})
        survey_count = survey.get("response_count", 0)
        st.markdown("#### Khảo sát trải nghiệm sau gợi ý")
        survey_cols = st.columns(4)
        survey_cols[0].metric("Phiếu có trả lời", survey_count)
        relevance_avg = survey.get("average_relevance")
        survey_cols[1].metric(
            "Phù hợp mối quan tâm",
            f"{relevance_avg:.2f}/5" if relevance_avg is not None else "Chưa có",
            (
                f"Số phiếu: {survey.get('relevance_count', 0)} · "
                f"{survey.get('relevance_positive_pct', 0):.1f}% đánh giá tích cực"
                if relevance_avg is not None else None
            ),
            delta_color="off",
        )
        usefulness_avg = survey.get("average_usefulness")
        survey_cols[2].metric(
            "Mức hữu ích",
            f"{usefulness_avg:.2f}/5" if usefulness_avg is not None else "Chưa có",
            (
                f"Số phiếu: {survey.get('usefulness_count', 0)} · "
                f"{survey.get('usefulness_positive_pct', 0):.1f}% đánh giá tích cực"
                if usefulness_avg is not None else None
            ),
            delta_color="off",
        )
        intent_pct = survey.get("explore_intent_yes_pct")
        survey_cols[3].metric(
            "Có ý định tìm hiểu",
            f"{intent_pct:.1f}%" if intent_pct is not None else "Chưa có",
            (
                f"Số phiếu: {survey.get('intent_count', 0)}"
            ),
            delta_color="off",
        )
        if survey_count < survey.get("minimum_recommended_sample", 20):
            st.info(
                f"Hiện có {survey_count} phiếu. Nên chờ ít nhất "
                f"{survey.get('minimum_recommended_sample', 20)} phiếu trước khi kết luận về ý kiến chung. "
                "Đây là cảm nhận của người trả lời, không cho biết gợi ý nghề có chính xác hay không."
            )
        else:
            st.caption(
                "Các số liệu phản ánh cảm nhận của những người đã gửi ý kiến; "
                "không cho biết gợi ý nghề có chính xác hay không."
            )

        st.markdown("#### Danh sách phản hồi từ sinh viên")
        fb_list = fetch_admin_feedbacks(limit=100)
        if fb_list:
            fb_df_data = []
            for f in fb_list:
                liked = len(f.get("liked_careers", [])) > 0 or f.get("rating", 0) >= 4
                survey_answers = f.get("survey") or {}
                fb_df_data.append({
                    "Thời gian": f.get("timestamp", "")[:19].replace("T", " "),
                    "Sinh viên": f.get("student_name", "Sinh viên"),
                    "Nhóm ngành đề xuất": f.get("top_group", ""),
                    "Đánh giá": "Hài lòng" if liked else "Chưa phù hợp",
                    "Sao": f"{f.get('rating', 5)}/5",
                    "Phù hợp": survey_answers.get("relevance", "-"),
                    "Hữu ích": survey_answers.get("usefulness", "-"),
                    "Tìm hiểu thêm": {
                        "yes": "Có",
                        "maybe": "Có thể",
                        "no": "Không",
                    }.get(survey_answers.get("explore_intent"), "-"),
                    "Bình luận": f.get("comment", "") or "-",
                })
            st.dataframe(pd.DataFrame(fb_df_data), width="stretch", hide_index=True)
            selected_feedback = st.selectbox(
                "Chọn phản hồi cần xóa",
                options=fb_list,
                format_func=lambda feedback: (
                    f"{feedback.get('timestamp', '')[:19].replace('T', ' ')} "
                    f"· {feedback.get('id', '')[:8]}"
                ),
                key="admin_feedback_to_delete",
            )
            confirm_feedback_delete = st.checkbox(
                "Tôi xác nhận xóa vĩnh viễn phản hồi đã chọn.",
                key="confirm_feedback_delete",
            )
            if st.button(
                "Xóa phản hồi đã chọn",
                disabled=not confirm_feedback_delete,
                key="delete_selected_feedback",
            ):
                result = _admin_request(
                    "DELETE",
                    f"/admin/feedbacks/{selected_feedback['id']}",
                    timeout=5,
                )
                if result:
                    if (
                        result.get("mirror_synced", True)
                        and result.get("training_data_synced", True)
                        and result.get("recommender_updated", True)
                    ):
                        st.toast("Đã xóa phản hồi.")
                        st.rerun()
                    else:
                        st.warning(
                            "Đã xóa phản hồi khỏi SQLite nhưng chưa cập nhật được bản mirror, dữ liệu huấn luyện "
                            "hoặc gợi ý. "
                            "Hãy kiểm tra log máy chủ."
                        )
        else:
            st.info("Chưa có phản hồi nào được ghi nhận.")

    # Tab 3: Lịch sử tư vấn
    with tab_logs:
        st.markdown("#### Các lượt tư vấn gần đây")
        logs_list = fetch_admin_logs(limit=100)
        if logs_list:
            logs_df_data = []
            for l in logs_list:
                logs_df_data.append({
                    "Thời gian": l.get("timestamp", "")[:19].replace("T", " "),
                    "Nhóm được gợi ý": l.get("predicted_group", ""),
                    "Mức dự đoán": f"{float(l.get('top_probability', 0)) * 100:.1f}%",
                    "Thời gian phản hồi": f"{l.get('latency_ms', 0) / 1000:.2f} giây",
                    "Thông tin môn học": "Còn thiếu môn" if l.get("is_partial") else "Đủ 12 môn",
                    "Phiên bản": f"v{l.get('model_version', '1.0')}",
                })
            st.dataframe(pd.DataFrame(logs_df_data), width="stretch", hide_index=True)
        else:
            st.info("Chưa có lượt tư vấn nào được ghi nhận.")

    # Tab 4: Cập nhật hệ thống từ phản hồi
    with tab_retrain:
        st.markdown("#### Cập nhật hệ thống từ phản hồi")
        st.write("""
        Khi có đủ phản hồi kèm điểm môn học và lựa chọn nghề, hệ thống có thể tạo phiên bản mới.
        Phiên bản mới chỉ được sử dụng khi vượt qua bước kiểm tra chất lượng; nếu không, phiên bản hiện tại được giữ nguyên.
        """)

        with st.container(border=True):
            st.markdown("**Bắt đầu cập nhật:**")
            col_rt1, col_rt2 = st.columns([1.5, 2.5])
            with col_rt1:
                force_retrain = st.checkbox("Bỏ qua số phản hồi tối thiểu", value=False)
                trigger_btn = st.button("Cập nhật từ phản hồi", type="primary", width="stretch")

            if trigger_btn:
                with st.spinner("Đang kiểm tra phản hồi và cập nhật hệ thống..."):
                    retrain_res = _admin_request(
                        "POST",
                        f"/retrain?force={str(force_retrain).lower()}",
                        timeout=35,
                    )
                    if retrain_res and retrain_res.get("status") == "success":
                        st.success(
                            "Đã cập nhật hệ thống thành công. "
                            f"Số phản hồi được bổ sung: {retrain_res.get('samples_added', 0)}."
                        )
                    elif retrain_res:
                        status = retrain_res.get("status")
                        if status == "rejected":
                            st.warning(
                                "Phiên bản mới chưa vượt qua bước kiểm tra chất lượng. "
                                "Hệ thống vẫn giữ phiên bản hiện tại."
                            )
                        elif status == "waiting":
                            st.info(
                                "Chưa đủ phản hồi có điểm môn học và lựa chọn nghề: "
                                f"{retrain_res.get('ready_count', 0)}/"
                                f"{retrain_res.get('required_count', 0)}."
                            )
                        else:
                            st.info(retrain_res.get("message", "Chưa thể cập nhật hệ thống lúc này."))


if __name__ == "__main__":
    main()
