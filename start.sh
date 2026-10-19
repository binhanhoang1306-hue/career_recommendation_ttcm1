#!/bin/bash
# Khởi động đồng thời FastAPI Backend (port 8000) và Streamlit Frontend (port 8501)
echo "Đang khởi động FastAPI Backend trên cổng 8000..."
uvicorn api.main:app --host 0.0.0.0 --port 8000 &

# Chờ FastAPI sẵn sàng
sleep 2

echo "Đang khởi động Streamlit Frontend trên cổng 8501..."
API_URL=http://127.0.0.1:8000 streamlit run web/app.py --server.port 8501 --server.address 0.0.0.0
