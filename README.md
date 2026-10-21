# HỆ THỐNG HỖ TRỢ QUYẾT ĐỊNH ĐỊNH HƯỚNG NGHỀ NGHIỆP CNTT (AI CAREER DSS)
> **Ứng dụng tích hợp Model AI trên nền tảng Web theo chuẩn Bộ môn KHMT-CNPM**
> **Kiến trúc kết hợp:** Model Học máy tự huấn luyện (Tầng 1) + Lọc dựa trên nội dung CBF (Tầng 2) + GroqCloud API (Bước 4)

---

## 1. Giới thiệu Bài toán & Mục tiêu

Sinh viên ngành Công nghệ Thông tin (CNTT) thường gặp khó khăn trong việc chọn hướng chuyên sâu phù hợp với năng lực học tập và thế mạnh cá nhân giữa rất nhiều định hướng nghề nghiệp khác nhau (AI, Dữ liệu, Web, Di động, An toàn thông tin, Hạ tầng mạng, Quản lý dự án,...).

Dự án này xây dựng một **Hệ Thống Hỗ Trợ Quyết Định (Decision Support System - DSS)** hoàn chỉnh, đưa model AI từ nghiên cứu ra ứng dụng thực tế trên nền tảng **Web** theo đúng quy trình 5 giai đoạn được hướng dẫn trong tài liệu:
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   1. Train   │ ──► │  2. Export   │ ──► │   3. Serve   │ ──► │ 4. Integrate │ ──► │  5. Monitor  │
│  Huấn luyện  │     │  Lưu model   │     │  Nạp model,  │     │ Tích hợp vào │     │ Theo dõi, thu│
│  (Jupyter)   │     │  + metadata  │     │  mở API/SDK  │     │     Web      │     │ thập feedback│
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
       ▲                                                                                   │
       └───────────────────────── Dữ liệu mới / Retrain Loop ──────────────────────────────┘
```

### Quy trình ra khuyến nghị (3 Tầng AI phối hợp):
1. **Tầng 1 — Phân loại Nhóm nghề (Machine Learning):** Điểm 12 môn học -> `StandardScaler` -> bộ phân loại được hiệu chuẩn nhiệt độ qua cross-validation -> phân phối xác suất theo nhãn huấn luyện giữa 7 nhóm CNTT. Đây không phải xác suất phù hợp nghề nghiệp ngoài đời.
2. **Tầng 2 — Xếp hạng nghề nghiệp cụ thể (Content-Based Filtering - CBF):** Kết hợp Cosine Similarity, độ thuần thục môn cốt lõi (Core Subject Mastery), mức độ đáp ứng kỹ năng mềm và phản hồi cộng đồng để chọn ra **Top 3 nghề nghiệp triển vọng nhất** trong 21 nghề IT.
3. **Tầng 3 / Bước 4 — Diễn giải tự nhiên (GroqCloud API):** Mô hình Groq diễn đạt kết quả Tầng 1, Tầng 2 và dữ liệu thị trường đã có thành lời tư vấn tiếng Việt; hệ thống kiểm tra để loại số liệu không được cung cấp.

---

## 2. Kiến trúc Triển khai (Server / REST API)

Hệ thống được tổ chức theo kiến trúc **Server / REST API** (Kiến trúc b trong tài liệu hướng dẫn):
- **Model Server (Backend):** Sử dụng **FastAPI**, nạp pipeline model một lần khi khởi động, kiểm tra dữ liệu bằng **Pydantic**, mở các RESTful endpoints:
  - `GET /health`: Kiểm tra sức khỏe hệ thống, phiên bản model, thời gian hoạt động.
  - `GET /model-info`: Cung cấp siêu dữ liệu (metadata), tên 12 môn học, khoảng điểm hợp lệ `[0.0, 10.0]`, danh mục kỹ năng để giao diện render động.
  - `POST /predict`: Suy luận ML thuần túy (nhóm nghề dự đoán, xác suất 7 nhóm).
  - `POST /decision`: Hệ hỗ trợ quyết định toàn diện (ML Tầng 1 + CBF Tầng 2 + Groq LLM diễn giải).
  - `POST /feedback`: Lưu phản hồi tự nguyện cho nghề được gợi ý đầu tiên; không cần tên và chỉ lưu điểm khi người dùng đồng ý.
- **Web Frontend:** Sử dụng **Streamlit** (tại `web/app.py`), kết nối qua HTTP/JSON tới API backend thông qua biến môi trường `API_URL`.

```
                    ┌────────────────────────┐
                    │  GroqCloud API       │
                    └───────────┬────────────┘
                                │ (Bước 4)
                                ▼
 ┌──────────────────────┐  HTTP/JSON  ┌──────────────────────────────────────────────┐
 │ Giao diện Web        │◄───────────►│             FASTAPI BACKEND                  │
 │ (Streamlit: web/)    │             │              (api/main.py)                   │
 └──────────────────────┘             │                                              │
                                      │  - POST /predict   (ML Inference Tầng 1)     │
                                      │  - POST /decision  (ML + CBF + Groq LLM)      │
                                      │  - GET  /model-info (Dynamic Metadata)       │
                                      │  - GET  /health    (Service Health)          │
                                      └──────────────────────┬───────────────────────┘
                                                             │ nạp 1 lần
                                                             ▼
                                              ┌──────────────────────────────┐
                                              │ models/current/              │
                                              │ pipeline + metadata          │
                                              └──────────────────────────────┘
```

---

### Luồng chạy ứng dụng

- **Luồng chạy duy nhất:** `api/main.py` (FastAPI) nạp model một lần và phục vụ suy luận; `web/app.py` (Streamlit) là giao diện người dùng duy nhất và gọi API.

---

## 3. Cấu trúc Thư mục

Cấu trúc dự án được chuẩn hóa theo đúng Mục 3.2 trong tài liệu hướng dẫn:

```
career_recommendation_v2/
├── career_ai/                    # Mã nguồn lõi: dữ liệu, model, train, đánh giá, giám sát
│   ├── domain_knowledge.py
│   ├── cbf_recommender.py
│   ├── decision_core.py
│   ├── model_exporter.py
│   ├── monitor_service.py
│   ├── feedback_store.py
│   ├── retrain_service.py
│   ├── prepare_data.py
│   ├── train.py
│   └── eval_system.py
├── data/
│   ├── DATASET.xlsx              # Dữ liệu nguồn
│   ├── students.csv              # Dữ liệu huấn luyện đã chuẩn bị (355 sinh viên)
│   ├── careers.json              # Danh mục 21 nghề thuộc 7 nhóm ngành CNTT
│   ├── feedback.json             # Phản hồi tường minh (Like/Dislike) từ người dùng (ban đầu rỗng)
│   └── interactions.json         # Nhật ký tương tác (ban đầu rỗng)
│                                 # (prediction_logs.jsonl được tạo tự động khi có lượt dự đoán, phục vụ giám sát drift)
├── models/
│   ├── current/                  # Pipeline triển khai và metadata đang dùng
│   └── v<phiên bản>/             # Các bản snapshot lịch sử
├── model/
│   └── 01_train_export_model.ipynb # Notebook EDA và huấn luyện
├── api/
│   ├── main.py                   # Bước 2: REST API phục vụ suy luận bằng FastAPI
│   ├── llm_explain.py            # Bước 4: Giải thích kết quả bằng GroqCloud API
│   └── test_api.py               # Bước 5: Script kiểm thử tự động API (hợp lệ & không hợp lệ)
├── web/
│   └── app.py                    # Bước 3: Giao diện web tương tác bằng Streamlit
├── tests/
│   ├── test_system.py            # Kiểm thử hồi quy logic nghiệp vụ và độ nhất quán
│   ├── test_lifecycle.py         # Kiểm thử toàn diện 5 giai đoạn vòng đời mô hình
│   ├── test_llm_and_model.py     # Kiểm thử lớp LLM (trung thực, chịu lỗi), nhất quán model/metadata, bảo mật
│   └── test_consistency.py       # Kiểm tra API, đầu vào, log giám sát; chạy từ api/
├── .streamlit/
│   └── config.toml               # Cấu hình theme và server cho Streamlit
├── Dockerfile                    # Docker container hóa phục vụ triển khai cloud
├── render.yaml                   # Cấu hình triển khai tự động lên nền tảng Render
├── Procfile                      # File cấu hình tiến trình PaaS
├── start.sh                      # Kịch bản khởi chạy đồng thời API và Web
├── requirements.txt              # Danh sách thư viện phụ thuộc
├── .env.example                  # Mẫu biến môi trường (tự tạo .env từ file này; KHÔNG nộp/commit .env)
└── README.md                     # Tài liệu hướng dẫn sử dụng và triển khai
```

---

## 4. Hướng dẫn Cài đặt & Chuẩn bị Môi trường

### 4.1. Yêu cầu môi trường
- Python 3.11 hoặc 3.14 (hỗ trợ Windows, Linux, macOS).
- Trình quản lý gói `pip`.

### 4.2. Cài đặt thư viện
Tại thư mục gốc của dự án, chạy:
```bash
pip install --require-hashes -r requirements.lock
```

### 4.3. Cấu hình biến môi trường
Tạo/cập nhật file `.env` trong thư mục gốc, giữ các thiết lập hiện có và thêm/cập nhật các dòng sau:
```ini
GROQ_API_KEY=              # để trống thì dùng giải thích theo quy tắc; lấy key tại https://console.groq.com/keys
GROQ_MODEL=openai/gpt-oss-120b
GROQ_TIMEOUT_MS=10000      # thời gian chờ tối đa khi gọi Groq
API_URL=http://127.0.0.1:8000
CORS_ORIGINS=http://localhost:8501,http://127.0.0.1:8501
```
Trên Windows, mở `.env` bằng VS Code/Notepad và dán API key của bạn vào bên phải `GROQ_API_KEY=`. Không gửi key qua chat. Sau khi lưu, dừng backend bằng `Ctrl+C` rồi khởi động lại:
```powershell
python -m uvicorn api.main:app --reload --port 8000
```
> **Lưu ý về Bảo mật:** Tuyệt đối không lưu khóa `GROQ_API_KEY` trong code JavaScript client hay public repo. API key chỉ được backend đọc từ biến môi trường. Nếu chưa cấu hình key, hệ thống tự động kích hoạt bộ sinh giải thích quy tắc chuyên gia (Rule-based engine) mà không sập ứng dụng. Groq có gói miễn phí với giới hạn RPM/TPM/RPD theo model và tài khoản; giới hạn có thể thay đổi, hãy xem trang Limits trong GroqCloud.
>
> **Khắc phục Groq:** Với HTTP 401, kiểm tra key trong `.env`; với HTTP 429, chờ giới hạn được làm mới hoặc kiểm tra RPM/TPM/RPD trong [GroqCloud Limits](https://console.groq.com/settings/limits). Backend không ghi API key hoặc nội dung lỗi thô của nhà cung cấp vào log.

---

## 5. Trình Tự Thực Thi Từng Bước (Theo Tài Liệu Hướng Dẫn)

### Bước 1: Huấn luyện & Export Model
Quy trình khảo sát dữ liệu, tiền xử lý, huấn luyện và đánh giá được trình bày trong file Jupyter Notebook [`model/01_train_export_model.ipynb`](model/01_train_export_model.ipynb). Mở notebook và chạy lần lượt các cell để xem biểu đồ EDA, so sánh 3 mô hình (`Logistic Regression`, `Random Forest`, `Gradient Boosting`), kết quả 5-fold CV, ma trận nhầm lẫn và xuất mô hình tốt nhất.

Có thể chạy quy trình huấn luyện tương đương từ dòng lệnh:
```bash
python -m career_ai.prepare_data
python -m career_ai.train
```

`prepare_data` đọc sheet `DỮ LIỆU NGHỀ NGHIỆP` và `DỮ LIỆU ĐIỂM SINH VIÊN` trong `data/DATASET.xlsx`. Nó xuất danh mục thô sang `data/careers_from_dataset.json` và bảng điểm sang `data/students.csv`; không ghi đè `data/careers.json`, vì file này chứa mô tả cùng nguồn dữ liệu thị trường đã được biên tập riêng.

Ba mô hình cơ sở được so sánh bằng F1 5-fold CV trên nhãn hiện có; mô hình có F1 cao nhất được đưa vào bộ hiệu chuẩn nhiệt độ. Pipeline triển khai, phiên bản scikit-learn và chỉ số hiện hành được lưu trong `models/current/metadata.json`; không dùng số liệu tĩnh trong tài liệu làm số liệu của model đang chạy.

Các xác suất được hiệu chuẩn bằng temperature scaling: mô hình cơ sở được fit trong từng fold, và một nhiệt độ duy nhất được tối ưu trên dự đoán out-of-fold để giảm log loss. Brier score, log loss và Expected Calibration Error được tính out-of-fold; giá trị thấp hơn là tốt hơn. Tại model v1.0.28, Brier giảm từ 0.2601 xuống 0.2257, log loss từ 0.5003 xuống 0.4315 và ECE từ 0.1436 xuống 0.0467 so với phân phối chưa hiệu chuẩn. Các số này đo độ hiệu chuẩn so với nhãn huấn luyện hiện có, phần lớn là nhãn suy ra từ điểm, nên **không chứng minh độ chính xác hay độ tin cậy đối với nghề nghiệp thực tế**. Cần dữ liệu nghề nghiệp do người dùng xác nhận và đánh giá độc lập để kết luận điều đó.

> **Đây là độ khớp với nhãn SUY RA từ bảng điểm, không phải độ chính xác dự đoán nghề nghiệp thực tế** (xem Mục 7).

---

### Bước 2: Khởi động REST API Backend (FastAPI)
Chạy server API phục vụ tại cổng 8000:
```bash
uvicorn api.main:app --reload --port 8000
```
- Trang tài liệu tương tác Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Trang tài liệu ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- Kiểm tra sức khỏe: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Cũng chạy được theo đúng cách trong PDF (từ trong thư mục `api/`): `cd api && uvicorn main:app --reload --port 8000` (API tự chuyển thư mục làm việc về thư mục gốc để đọc `data/`).
- Endpoint: `POST /predict` (chỉ mô hình học máy, không điều chỉnh), `POST /decision` (mô hình + sở thích/kỹ năng + CBF + giải thích), `GET /model-info`, `GET /health`. Đầu vào không hợp lệ bị từ chối với mã 422 (điểm âm/vượt 10, thiếu môn, NaN/Infinity, giá trị true/false, tên quá 100 ký tự, kỹ năng hoặc sở thích ngoài danh mục); thông báo lỗi không phản chiếu lại dữ liệu đã gửi.

---

### Bước 3: Khởi động Giao diện Web (Streamlit)
Mở cửa sổ dòng lệnh thứ hai và chạy:
```bash
streamlit run web/app.py
```
Ứng dụng web tự động mở tại: **[http://localhost:8501](http://localhost:8501)**
- Giao diện trực quan cho phép:
  - Chọn nhanh các hồ sơ mẫu sinh viên (AI/Data, Bảo mật, Web, Game).
  - Tải file bảng điểm Excel/CSV hoặc kéo thanh trượt điểm 12 môn học.
  - Chọn các mức độ kỹ năng mềm và lĩnh vực hứng thú.
  - Bấm nút **Phân Tích Định Hướng** để nhận báo cáo khuyến nghị toàn diện kèm biểu đồ và lời giải thích AI.

---

### Bước 4: Tích hợp GroqCloud API để diễn giải kết quả
Module `api/llm_explain.py` dùng SDK OpenAI tương thích để gọi endpoint GroqCloud:
- Khi có `GROQ_API_KEY`, `/decision` gọi Groq để viết lời giải thích và tư vấn 3-5 câu. Có **timeout** (`GROQ_TIMEOUT_MS`) và **cache** cho các yêu cầu giống nhau.
- Model mặc định là `openai/gpt-oss-120b`; danh sách model và giới hạn miễn phí có thể thay đổi, hãy chọn model đang hoạt động trong GroqCloud.
- Groq chỉ diễn đạt lại kết quả và dữ liệu thị trường đã nạp từ `careers.json`; phiên bản này không tự tra cứu web hoặc cập nhật dữ liệu thời gian thực.
- Không gửi tên sinh viên hay thông tin nhận dạng cá nhân cho Groq. Prompt chỉ nhận điểm/kỹ năng/sở thích và các kết quả tổng hợp cần cho tư vấn.
- Câu trả lời sử dụng **nguồn, thời điểm rà soát và khu vực** đã có trong danh mục. Nếu không tìm thấy nguồn tin cậy, hệ thống phải nói rõ là chưa có dữ liệu thị trường thay vì phỏng đoán.
- Prompt nói rõ **tỷ lệ % chỉ là mức khớp giữa điểm các môn và hồ sơ môn học của nghề**, và cấm các cách nói khẳng định ("chắc chắn", "tối ưu", "bạn sẽ thành công"). Kết quả luôn kèm câu miễn trừ "gợi ý tham khảo".
- **Kiểm soát đầu ra hai lớp (Two-tier Output Validation):**
  1. *Số liệu học thuật:* Xác suất nhóm đã hiệu chuẩn theo nhãn huấn luyện và tỷ lệ khớp hồ sơ môn học phải khớp với kết quả do hệ thống tính ra (dung sai 0.6%); các tỷ lệ bịa đặt đều bị loại. Không gọi xác suất này là xác suất phù hợp nghề ngoài đời.
  2. *Số liệu thị trường lao động:* Cho phép các con số mức lương và năm cập nhật đã có trong dữ liệu nghề (`careers.json`); Groq không được tự bổ sung số liệu chưa được cung cấp.
- Khi thiếu API key, hết hạn mức, mất mạng hoặc quá thời gian: tự động chuyển sang giải thích theo quy tắc (kết hợp dữ liệu thị trường có sẵn trong `careers.json`, không điền giá trị phỏng đoán). Giao diện nêu loại lỗi có thể xử lý; backend chỉ ghi loại exception và mã HTTP, không ghi API key hay nội dung lỗi từ nhà cung cấp.
- Dữ liệu nhập tự do (sở thích, kỹ năng) được làm sạch trước khi đưa vào prompt; giao diện web escape HTML khi hiển thị nội dung LLM.

---

### Bước 5: Chạy Thử và Kiểm Tra Tự Động (API Testing)
Chạy kịch bản kiểm thử tự động tại `api/test_api.py`:
```bash
python api/test_api.py        # (khi API đang chạy)  hoặc: cd api && python test_api.py
python -m unittest discover -s tests   # bộ kiểm thử đơn vị/tích hợp (không cần bật API)
```
Kịch bản kiểm thử bao gồm các ca hợp lệ, các ca biên, và các ca dữ liệu lỗi (điểm âm, điểm vượt 10, thiếu trường, sai định dạng). Kết quả chạy thực tế:

```text
==============================================================================
BẮT ĐẦU KIỂM THỬ TỰ ĐỘNG BỘ REST API (Bước 5 - PDF Mục 3.8)
==============================================================================
[OK ] Health check                             HTTP 200 (mong đợi 200) -   3 ms
[OK ] Lấy Model Info (Metadata)                HTTP 200 (mong đợi 200) -   3 ms
[OK ] SV thế mạnh Dữ liệu & AI                 HTTP 200 (mong đợi 200) -  33 ms
      -> Dự đoán: Dữ liệu & AI | Nghề #1: Chuyên viên phân tích dữ liệu / Nhà khoa học dữ liệu (98.5%)
[OK ] SV thế mạnh An toàn & Bảo mật            HTTP 200 (mong đợi 200) -  24 ms
      -> Dự đoán: An toàn thông tin | Nghề #1: Chuyên viên phân tích an ninh mạng (98.5%)
[OK ] SV thế mạnh Phát triển Web               HTTP 200 (mong đợi 200) -   6 ms
      -> Dự đoán: Phát triển Web | Nghề #1: Lập trình viên Frontend (98.5%)
[OK ] Điểm âm (ai = -2.0)                      HTTP 422 (mong đợi 422) -  23 ms
[OK ] Điểm vượt trần (db = 15.0)               HTTP 422 (mong đợi 422) -   3 ms
[OK ] Thiếu trường môn học (chỉ gửi 10 môn)    HTTP 422 (mong đợi 422) -   2 ms
[OK ] Sai kiểu dữ liệu (điểm là chuỗi chữ 'abc') HTTP 422 (mong đợi 422) -   2 ms
==============================================================================
[✓] TẤT CẢ CÁC CA KIỂM THỬ ĐỀU ĐẠT CHUẨN!
==============================================================================
```

Ngoài ra, chạy toàn bộ bộ kiểm thử hồi quy và vòng đời:
```bash
python -m unittest discover -s tests -v
```
---

## 6. Hướng Dẫn Triển Khai Trực Tuyến (Online Deployment)

Để người dùng có thể truy cập qua trình duyệt mà không cần cài đặt code, dự án đã chuẩn bị sẵn đầy đủ file cấu hình cho các nền tảng đám mây phổ biến:

### Lựa chọn 1: Triển khai trên Streamlit Community Cloud (Nhanh nhất cho Web)
1. Đẩy mã nguồn dự án lên một kho GitHub (công khai hoặc riêng tư).
2. Truy cập [share.streamlit.io](https://share.streamlit.io/) và đăng nhập bằng tài khoản GitHub.
3. Nhấp **"New app"**, chọn kho lưu trữ và nhánh tương ứng.
4. Tại mục **Main file path**, điền: `web/app.py`.
5. Trong phần **Advanced settings -> Secrets**, thêm địa chỉ backend API:
   ```toml
   API_URL = "https://your-api-service.onrender.com"
   ```
   `API_URL` được đọc trực tiếp từ Streamlit Secrets. Không đặt `GROQ_API_KEY` ở giao diện; khóa Groq chỉ cấu hình trong biến môi trường của dịch vụ FastAPI backend.
6. Bấm **Deploy**. Sau 2-3 phút, bạn sẽ có đường link trực tuyến công khai (dạng `https://career-ai.streamlit.app`).

### Lựa chọn 2: Triển khai toàn bộ trên Render (render.com)
Dự án đã có sẵn file `render.yaml` chuẩn hóa blueprint:
1. Đăng ký tài khoản tại [render.com](https://render.com).
2. Kết nối tài khoản GitHub của bạn với Render.
3. Tạo mới **Blueprint** và chọn repo này. Render sẽ tự động đọc `render.yaml` và tạo 2 dịch vụ:
   - `career-ai-api`: Chạy FastAPI backend (`uvicorn api.main:app --port $PORT`).
   - `career-ai-web`: Chạy Streamlit frontend (`streamlit run web/app.py`).
4. Nhập biến môi trường bí mật `GROQ_API_KEY`, `ADMIN_USERNAME` và `ADMIN_PASSWORD` cho dịch vụ `career-ai-api` trong Dashboard của Render. Hai biến quản trị được đánh dấu `sync: false`; hãy đặt tên đăng nhập và mật khẩu dài, riêng biệt, không dùng thông tin mặc định hoặc mật khẩu dùng ở nơi khác.
5. API dùng gói Render Starter và Persistent Disk 1 GB ở `/var/data`; `CAREER_AI_DATA_DIR` lưu SQLite, phản hồi, tương tác và prediction logs trên ổ này để dữ liệu còn sau deploy/restart. Disk chỉ dùng được với gói trả phí, gắn với một instance; không scale API thành nhiều instance nếu chưa chuyển dữ liệu sang kho dùng chung.
6. Dịch vụ tự động build và cung cấp 2 đường link HTTPS. Chỉ đăng nhập quản trị qua kết nối HTTPS; không đưa thông tin đăng nhập vào URL, mã nguồn hoặc log.

**Chuyển API hiện có từ Render Free:** filesystem của gói Free là tạm thời; disk mới không tự mang dữ liệu cũ sang. Trước khi áp dụng Blueprint/nâng gói, sao lưu phản hồi từ API hiện tại, dùng PowerShell và thay URL API:

```powershell
$api = "https://<api-host>"
$credential = Get-Credential
$backup = Invoke-RestMethod -Uri "$api/admin/feedbacks?limit=10000" -Credential $credential
$backup | ConvertTo-Json -Depth 100 | Set-Content -Encoding utf8 feedback-backup.json
```

Sau khi triển khai phiên bản mới và Persistent Disk đã được mount, khôi phục bản sao lưu vào cùng API:

```powershell
$backup = Get-Content -Raw feedback-backup.json
Invoke-RestMethod -Method Post -Uri "$api/admin/feedbacks/restore" `
  -Credential $credential -ContentType "application/json" -Body $backup
```

Endpoint khôi phục chỉ dành cho quản trị viên; bản ghi trùng ID được bỏ qua, không ghi đè dữ liệu hiện có. Giữ lại `feedback-backup.json` đến khi xác nhận dashboard hiển thị đủ phản hồi. Bản ghi đã mất trước khi sao lưu chỉ khôi phục được nếu có bản sao lưu khác.

Màn hình quản trị xác thực trực tiếp với API. Các endpoint `/admin/*` và `/retrain` đều yêu cầu HTTP Basic Authentication ở backend; khi chưa cấu hình đủ cả hai biến quản trị, API từ chối truy cập bằng HTTP 503. Với chạy cục bộ, đặt hai biến trong `.env` (sao chép từ `.env.example`) trước khi khởi động API. Tài khoản nhập ở trang đăng nhập được lưu trong phiên Streamlit để gọi các API quản trị và bị xóa khi đăng xuất.

### Lựa chọn 3: Triển khai trên Hugging Face Spaces (Docker Space)
1. Tạo một Space mới trên [huggingface.co/spaces](https://huggingface.co/spaces), chọn SDK là **Docker**.
2. Đẩy toàn bộ source code (bao gồm `Dockerfile` và `start.sh`) lên repo Space.
3. Trong mục **Settings -> Variables and secrets**, thêm `GROQ_API_KEY`.
4. Hugging Face sẽ tự động build image Docker và chạy cả backend lẫn frontend.

---

## 7. Giới Hạn và Ý Nghĩa Khoa Học

1. **Nhãn suy ra từ bảng điểm (Pseudo-labeling):** Vì `data/DATASET.xlsx` là bảng điểm thực tế của sinh viên nhưng không ghi nghề nghiệp thực tế của từng bạn sau khi ra trường, nhãn `career_group` được xác định thông qua ma trận tri thức chuyên gia (`career_ai/domain_knowledge.py`). F1, Brier score, log loss, ECE và xác suất đã hiệu chuẩn đều được tính so với nhãn huấn luyện hiện có; chúng không phải độ chính xác, độ hiệu chuẩn hay xác suất phù hợp nghề nghiệp ngoài đời thực.
2. **Phản hồi và dữ liệu người dùng:** Không yêu cầu tên để tư vấn hoặc lưu phản hồi. Phản hồi tự nguyện gồm đánh giá, điểm sao, nhận xét và câu trả lời khảo sát; điểm môn học chỉ được lưu cùng phản hồi khi người dùng chọn đồng ý. Nhật ký lượt tư vấn cũng chỉ ghi điểm khi người dùng bật lựa chọn đồng ý lưu nhật ký; nếu không, nhật ký không chứa điểm. Không nhập thông tin nhận dạng cá nhân vào ô nhận xét. Dữ liệu phản hồi được lưu trong SQLite và mirror sang `feedback.json`; phản hồi không tự hết hạn và chỉ bị xóa khi quản trị viên chủ động xóa từng phiếu trong tab phản hồi. Nhật ký tư vấn/tương tác được tự dọn sau 60 ngày khi API khởi động, sau đó kiểm tra mỗi ngày; quản trị viên cũng có thể chạy dọn ngay trong bảng điều khiển. Việc xóa dữ liệu nguồn đồng bộ lại `students.csv` nhưng không tự huấn luyện lại hoặc xóa model/snapshot hiện hành. Model cũ có thể vẫn chịu ảnh hưởng từ phản hồi đã xóa cho đến khi được thay thế theo quy trình huấn luyện riêng.
3. **Hiệu chuẩn xác suất không thay thế nhãn sự thật:** Temperature scaling hiệu chỉnh độ sắc của phân phối để giảm log loss trên dự đoán out-of-fold. Vì nhãn dùng để hiệu chuẩn phần lớn được suy ra từ điểm, xác suất chỉ nên hiểu là mức độ mô hình dự đoán từng nhãn đó; chưa thể diễn giải là xác suất một người thật sự phù hợp hoặc thành công trong nghề.
4. **Sở thích và kỹ năng mềm không nằm trong dữ liệu huấn luyện.** Mô hình chỉ học từ 12 điểm môn; sở thích và kỹ năng mềm điều chỉnh thứ hạng bằng quy tắc sau khi mô hình dự đoán. Quy tắc này nằm ở `career_ai/decision_core.py`; `POST /predict` trả phân phối xác suất đã hiệu chuẩn theo nhãn học. `/decision` trả phân phối đó ở `probabilities_model_only` cùng thứ hạng phần trăm sau điều chỉnh ở `probabilities`; phân phối sau điều chỉnh là điểm xếp hạng được chuẩn hóa, **không phải xác suất đã hiệu chuẩn**. Kỹ năng "Chưa đánh giá" bị bỏ qua.
5. **Tách xác suất model và điểm xếp hạng:** phản hồi `/decision` nêu `model_predicted_group`/`model_confidence` riêng với `recommendation_group`/`recommendation_ranking_score`. Các trường `probabilities_model_only` là xác suất model theo nhãn huấn luyện; `recommendation_ranking_scores` là điểm xếp hạng sau điều chỉnh theo sở thích/kỹ năng, không phải xác suất.
6. **Tầng LLM chỉ diễn đạt lại kết quả,** không bổ sung thông tin về thị trường lao động hay năng lực thực tế của sinh viên. Thứ tự nhóm nghề và Top nghề được tính trước bởi ML/CBF; LLM không có quyền thay đổi thứ hạng. Nếu Groq thiếu key, lỗi hoặc trả lời vi phạm kiểm tra số liệu, API trả giải thích theo quy tắc để không làm gián đoạn khuyến nghị.
7. **Bảo mật khi triển khai:** không nộp/commit file `.env`; chỉ cấu hình khóa Groq ở backend và đặt `CORS_ORIGINS` đúng địa chỉ giao diện khi triển khai.

### Biện pháp giảm thiểu các giới hạn đã biết

- **Dữ liệu thị trường:** từng thẻ nghề hiển thị nguồn và ngày rà soát; dữ liệu lương có cấu trúc theo loại thống kê, đơn vị, kỳ dữ liệu, kinh nghiệm, địa điểm, cỡ mẫu và tình trạng tin nếu có. Dữ liệu lịch sử, proxy và tin đã hết hạn được ghi rõ, không nên so sánh trực tiếp như cùng một thước đo. Chạy `python -m career_ai.catalog_audit` để kiểm tra cấu trúc/trích dẫn và `python -m career_ai.source_check` để kiểm tra trạng thái HTTP, năm trong mẫu nội dung trang và ngày hết hạn đã ghi nhận. Lần rà soát ngày 2026-10-20 ghi nhận 10/23 URL trả HTTP 200, 13/23 bị chặn với HTTP 403 và không có URL nào được xác nhận trả 404/410; 4 tin đã quá hạn và 6 bản ghi tin chưa có ngày hết hạn. Việc tìm thấy năm chỉ là gợi ý rà soát, không chứng minh số liệu khớp kỳ dữ liệu. Mã 403/429 hoặc lỗi mạng là kết quả chưa xác định, không phải bằng chứng link hỏng; nội dung trang và tính đúng kỳ dữ liệu vẫn cần được rà soát thủ công.
- **Môi trường triển khai:** `requirements.lock` khóa phụ thuộc bắc cầu và hash cho Python 3.11; Render cài từ lockfile. Sau khi thay đổi `requirements.txt`, tạo lại lock bằng `uv pip compile requirements.txt --python-version 3.11 --universal --generate-hashes -o requirements.lock` rồi kiểm tra build trên Render.
- **Khảo sát người dùng:** dashboard hiển thị số câu trả lời hợp lệ theo từng chỉ số và khoảng tin cậy Wilson 95% cho các tỷ lệ. Khi tổng phiếu dưới 20, dashboard cảnh báo không nên diễn giải xu hướng. Khoảng tin cậy chỉ mô tả bất định do cỡ mẫu; không loại bỏ thiên lệch do khảo sát tự nguyện, nên khảo sát vẫn không được dùng như độ chính xác khách quan của mô hình.
- **LLM:** LLM chỉ tạo phần diễn giải, không thay đổi nhóm nghề hoặc thứ tự Top nghề. Dịch vụ ngoài có thể gián đoạn; khi đó hệ thống giữ nguyên kết quả ML/CBF và chuyển sang lời giải thích theo quy tắc. LLM không được xem là thành phần làm tăng độ chính xác khuyến nghị.

---

## 8. Đánh giá hiệu quả thực tế và cập nhật dữ liệu nghề nghiệp

### Khảo sát người dùng

Sau khi xem kết quả, sinh viên có thể mở **Khảo sát ngắn (không bắt buộc)** và trả lời:

- Mức phù hợp với mối quan tâm: thang 1–5.
- Mức hữu ích của kết quả: thang 1–5.
- Ý định tìm hiểu thêm nghề đứng đầu: Có / Có thể / Không.

Dashboard quản trị báo số phiếu hợp lệ, điểm trung bình từng câu và tỷ lệ điểm 4–5; mỗi chỉ số chỉ tính các câu đã trả lời. `n` và khoảng tin cậy Wilson 95% được hiển thị bên cạnh tỷ lệ. Đây là **cảm nhận tự báo cáo**, không phải độ chính xác của mô hình hoặc bằng chứng nghề đó phù hợp khách quan. Dashboard cảnh báo khi có dưới 20 phiếu; mốc 20 chỉ là ngưỡng tối thiểu để tránh diễn giải từ mẫu rất nhỏ, không thay thế tính cỡ mẫu hay kiểm định thống kê. Khoảng tin cậy không hiệu chỉnh thiên lệch do người tự chọn tham gia khảo sát.

### Kiểm định độc lập với lựa chọn nghề do người dùng xác nhận

Chạy `python -m career_ai.eval_system`. Phần kiểm định dùng các phản hồi có đủ điểm môn và nghề được người dùng đánh dấu phù hợp; pipeline đánh giá chỉ huấn luyện trên nhãn suy ra, rồi đo:

- **Top-1:** tỷ lệ trường hợp nhóm nghề đã xác nhận đứng đầu.
- **Top-3:** tỷ lệ trường hợp nhóm nghề đã xác nhận nằm trong ba nhóm đầu.

Chương trình báo số mẫu hợp lệ `n` và không kết luận khi chưa đạt `MIN_FEEDBACK_FOR_VALIDATION` (hiện là 20). Cần ghi cả `n`, Top-1 và Top-3 trong báo cáo. Nếu thiếu dữ liệu hoặc chưa đủ mẫu, ghi “chưa đủ dữ liệu đánh giá độc lập”; không thay bằng F1 hay chỉ số hiệu chuẩn cross-validation trên nhãn suy ra.

### Rà soát dữ liệu nghề nghiệp

`data/careers.json` ghi riêng `nguon_tham_khao` theo phạm vi nội dung (`muc_luong`, `xu_huong_thi_truong`), URL HTTPS, kỳ dữ liệu và ngày rà soát. Ngày **2026-10-15**, ba nghề Security Engineer, SOC Analyst và Penetration Tester được bổ sung mức lương từ các tin tuyển dụng cụ thể trên TopCV, hiển thị theo tin/cấp độ thay vì xem như mức trung bình thị trường. Các tin có thể hết hạn hoặc thay đổi; cần bấm nguồn để kiểm tra trạng thái hiện tại. Cả ba nghề cũng được gắn với bối cảnh thiếu hụt nhân lực an ninh mạng theo nhận định tại Vietnam Security Summit 2025 được Nhân Dân Online dẫn lại; đây là xu hướng toàn ngành, không phải dự báo riêng từng chức danh.

Ngày **2026-10-19**, danh mục được bổ sung 5 chỉ báo tuyển dụng Q3-2025 cho Backend, Frontend, DevOps/SRE, QA và Computer Vision; các chỉ báo dựa trên từ khóa kỹ năng hoặc nhóm vai trò nên được gắn nhãn **proxy**, không đại diện trực tiếp cho riêng chức danh. Cùng kỳ, chỉ báo tổng thể trên ITviec là lượng tin tuyển dụng IT tăng 2,7% YoY và 0,5% QoQ; đây là proxy nền theo ngành, được ghi rõ cho UI/UX, Mobile, Business Analyst, System Administrator, Game Developer, Software Engineer, System Analyst, IT Support/Consultant và Network Engineer, không phải xu hướng riêng của từng nghề. Software Engineer có thêm lương Back-end Developer làm tham khảo tương đương.

Các nguồn lương mới cần đọc đúng phạm vi và thời điểm: AI Engineer có một tin TopCV tới 35 triệu đồng gross/tháng (yêu cầu 3 năm, hết hạn 08/05/2026); System Administrator có một tin 15–17 triệu (hết hạn 09/08/2026); Game Developer có một tin 20–40 triệu (hết hạn 22/04/2023). Đây là mức ghi trong từng tin, không phải trung vị hiện tại; tin Game Developer đã cũ. Indeed hiển thị mức trung bình 14.335.767 đồng/tháng cho Systems Analyst, 13.857.347 đồng/tháng cho IT Support (61 mức lương được báo cáo; cập nhật 12/10/2026) và 12.369.709 đồng/tháng cho Graphic Designer (303 mức lương; cập nhật 11/10/2026) khi rà soát ngày 19/10/2026. Các mức Indeed là dữ liệu tổng hợp nền tảng, không phải mức lương bảo đảm; IT Support chỉ đại diện cho chức danh đó, không đại diện riêng cho phần tư vấn CNTT. Mức Graphic Designer là proxy cho Graphic & 3D Artist. Riêng xu hướng Graphic & 3D Artist dùng proxy quy mô thị trường thiết kế đồ họa: NextMSC ước tính thị trường Việt Nam đạt 1,19 tỷ USD năm 2021 và dự báo 1,84 tỷ USD năm 2030 (CAGR 5,0% trong 2022–2030); đây là dự báo quy mô ngành dịch vụ, không phải thống kê tuyển dụng hay tăng trưởng việc làm. Với UI/UX Designer, một tin TopCV hết hạn 23/07/2026 ghi 15–20 triệu đồng/tháng (yêu cầu 2 năm); đây cũng không phải trung vị hiện tại. Với Computer Vision Engineer, tin VNPAY hết hạn 09/05/2024 chỉ ghi “thỏa thuận”, không công khai số tiền, nên không dùng để suy ra con số lương. Danh mục hiện có **21 thông tin lương** và **21 thông tin xu hướng** có nguồn; các proxy được ghi trong dữ liệu và gắn nhãn trên giao diện. Không còn trường lương/xu hướng nào để trống vì thiếu nguồn; các con số proxy hoặc một tin đơn lẻ vẫn không phải mức lương hay xu hướng tuyển dụng được bảo đảm.

Một số nguồn tiêu biểu được đối chiếu: [ITviec — báo cáo lương Data Scientist 2025–2026](https://itviec.com/blog/luong-data-scientist/), [ITviec — Tester Roadmap](https://itviec.com/blog/tester-roadmap/), [ITviec — Network Engineer](https://itviec.com/blog/network-engineer-la-gi/), [ITviec — tuyển dụng CNTT Q3-2025](https://itviec.com/blog/vietnam-it-job-market-q3-2025-shifting-skill-requirements/), [TopCV — AI Engineer](https://www.topcv.vn/viec-lam/ai-engineer-tai-ha-noi-luong-upto-35-trieu/2113812.html), [TopCV — System Administrator](https://www.topcv.vn/viec-lam/nhan-vien-quan-tri-he-thong/2231899.html), [TopCV — Game Developer](https://www.topcv.vn/viec-lam/game-developer-thu-nhap-tu-20-40-trieu/645199.html), [Indeed — Systems Analyst](https://vn.indeed.com/career/systems-analyst/salaries), [Indeed — IT Support](https://jobs.vn.indeed.com/career/it-support/salaries), [Indeed — Graphic Designer](https://vn.indeed.com/career/graphic-designer/salaries), [NextMSC — Vietnam Graphic Design Market](https://www.nextmsc.com/report/vietnam-graphic-design-market), [TopCV — UI/UX Designer](https://www.topcv.vn/viec-lam/nhan-vien-ui-ux-designer-thu-nhap-up-to-20-trieu/2212321.html), [TopCV — Computer Vision Engineer tại VNPAY](https://www.topcv.vn/brand/thanhtoanvietnam/tuyen-dung/computer-vision-engineer-j1296523.html) và [ITviec — báo cáo lương/thị trường 2025–2026](https://itviec.com/bao-cao/luong-it-va-thi-truong-tuyen-dung-it-vietnam). Kỳ dữ liệu cụ thể và ngày kiểm tra được ghi trong từng nghề. Các số liệu proxy thị trường được phân biệt rõ với thống kê nhu cầu tuyển dụng theo chức danh.

Quy trình cập nhật tiếp:

1. Đối chiếu từng nghề với nguồn gốc cho đúng chức danh; không suy rộng từ nghề gần giống nếu nguồn không nói rõ.
2. Ghi nguồn vào `nguon_tham_khao` và chỉ thêm claim tương ứng vào `pham_vi`; lưu URL HTTPS, ngày rà soát (`YYYY-MM-DD`) và kỳ dữ liệu. Nếu không có bằng chứng, giữ câu trạng thái chưa xác thực.
   - Nếu nguồn là proxy (nghề tương đương hoặc chỉ báo kỹ năng/tin tuyển dụng), đánh dấu nguồn bằng `"loai_tham_chieu"` và ghi đối tượng trong `"nghe_tham_chieu"` hoặc `"doi_tuong_tham_chieu"`. Nội dung lương/xu hướng phải nêu rõ đối tượng tham chiếu; giao diện sẽ hiển thị nhãn này để tránh hiểu nhầm là số liệu riêng cho chức danh đang xem.
3. Chạy `python -m career_ai.catalog_audit`. Công cụ xác nhận mỗi claim đã có URL thuộc đúng phạm vi hoặc được đánh dấu chưa có dữ liệu; trả lỗi nếu có claim thiếu dẫn chứng, URL không an toàn, kỳ dữ liệu tương lai hay rà soát quá 365 ngày.
4. Khởi động lại FastAPI để nạp dữ liệu mới. Thay đổi mô tả/lương không tự huấn luyện lại mô hình; nếu thay hồ sơ môn học/nghề trong `career_ai/domain_knowledge.py`, chạy lại quy trình đánh giá và huấn luyện tương ứng.

---

## 9. Các Giải Pháp Đã Nâng Cấp Khắc Phục Hạn Chế

Dự án đã triển khai **3 giải pháp nâng cấp cốt lõi** giải quyết trực tiếp các hạn chế về dữ liệu, lưu trữ và tự động hóa:

1. **Hỗ trợ đánh giá với bảng điểm chưa đủ 12 môn (Partial Assessment & Imputation):**
   - Giao diện cho phép để trống môn chưa học, không cần tích checkbox; tự bật `allow_partial=True` khi bảng điểm chưa đủ 12 môn hoặc qua các endpoint chuyên dụng: `POST /predict/partial`, `POST /decision/partial`.
   - Các môn chưa học được tự động điền giá trị chuẩn hóa kỳ vọng của toàn trường ($z = 0$, tương ứng `SUBJECT_STATS`), không phạt oan hay thiên vị các môn sinh viên chưa được học.
   - Bổ sung phân tích **môn cốt lõi chưa học** (`unstudied_core`), chỉ ra các học phần chuyên sâu sinh viên cần ưu tiên đăng ký trong các học kỳ tiếp theo.
   - Sinh viên năm 1-3 có thể đánh giá sớm; các môn chưa có điểm được tự ước lượng và hiển thị trong kết quả.

2. **Chuyển đổi lưu trữ sang CSDL SQLite chuẩn ACID (`career_ai/db.py`):**
   - Loại bỏ rủi ro xung đột ghi dữ liệu (race conditions) của flat-file khi có nhiều yêu cầu đồng thời, sử dụng kết nối SQLite với chế độ `WAL (Write-Ahead Logging)` và timeout an toàn.
   - Duy trì cơ chế đồng bộ hai chiều (mirror) sang các file `feedback.json`, `prediction_logs.jsonl` để bảo đảm tính tương thích ngược tuyệt đối với các script và test case cũ.

3. **Tự động hóa vòng lặp Huấn luyện lại (Automated Retrain Loop & Live Reload):**
   - Endpoint `POST /feedback` tiếp nhận bảng điểm thực tế và tự động kích hoạt kiểm tra điều kiện Retrain trong tác vụ nền (`BackgroundTasks`).
   - Cung cấp endpoint `POST /retrain` để kích hoạt thủ công hoặc qua Webhook.
   - Cơ chế callback `live-reload` giúp FastAPI tự động nạp pipeline mô hình và metadata mới vào bộ nhớ ngay khi huấn luyện lại thành công mà không cần khởi động lại máy chủ.
