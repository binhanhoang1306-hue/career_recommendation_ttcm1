FROM python:3.11-slim

WORKDIR /app

# Cài đặt các gói phụ thuộc hệ thống
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements và cài đặt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn
COPY . .

# Đảm bảo dữ liệu và model đã sẵn sàng
RUN python -m career_ai.prepare_data && python -m career_ai.train

# Cấp quyền thực thi cho start.sh
RUN chmod +x start.sh

# Expose các cổng phục vụ: 8000 (API), 8501 (Streamlit Web)
EXPOSE 8000 8501

CMD ["./start.sh"]
