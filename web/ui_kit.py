# -*- coding: utf-8 -*-
"""
web/ui_kit.py — Bộ thành phần giao diện hiện đại & cao cấp cho web/app.py (CSS + hàm dựng HTML/SVG).
Không phụ thuộc thêm thư viện ngoài: biểu đồ radar, vòng tin cậy, thanh xác suất đều là HTML/SVG thuần.
Mọi chuỗi động đều đi qua html.escape() trước khi chèn vào HTML để phòng chống XSS.
"""
import html
import math
from datetime import date, datetime

PALETTE = ["#4F46E5", "#0EA5E9", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#64748B"]
AXIS_LABEL = {
    "sec": "ATBM", "se": "CNPM", "linux": "Linux", "db": "CSDL", "graphics": "Đồ họa", "network": "Mạng",
    "analysis": "PTTK", "image": "Xử lý ảnh", "java": "Java", "csharp": "C#/.NET", "web": "Web", "ai": "AI",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --ink: #0F172A;
    --ink-light: #334155;
    --muted: #64748B;
    --line: #E2E8F0;
    --line-light: #F1F5F9;
    --card: #FFFFFF;
    --bg: #F4F6FC;
    --brand: #4F46E5;
    --brand-dark: #3730A3;
    --brand-light: #EEF2FF;
    --brand2: #3B82F6;
    --brand2-light: #EFF6FF;
    --ok: #059669;
    --ok-bg: #ECFDF5;
    --warn: #D97706;
    --warn-bg: #FFFBEB;
    --danger: #DC2626;
    --danger-bg: #FEF2F2;
    --radius-sm: 10px;
    --radius-md: 18px;
    --radius-lg: 22px;
}

html, body, [class*="css"], .stApp, [data-testid="stAppViewContainer"] {
    font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    color: var(--ink);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
}

/* ================== App Ambient Canvas ================== */
.stApp {
    background-color: #F4F6FC !important;
    background-image:
        radial-gradient(1200px 550px at 88% -50px, rgba(99, 102, 241, 0.08) 0%, transparent 65%),
        radial-gradient(950px 500px at 10% 120px, rgba(14, 165, 233, 0.07) 0%, transparent 60%),
        radial-gradient(850px 650px at 50% 850px, rgba(168, 85, 247, 0.04) 0%, transparent 70%),
        radial-gradient(600px 400px at 85% 1350px, rgba(16, 185, 129, 0.035) 0%, transparent 60%) !important;
    background-attachment: fixed !important;
}

#MainMenu, footer, [data-testid="stDecoration"] {
    display: none !important;
}

header[data-testid="stHeader"] {
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    overflow: visible !important;
    background: transparent !important;
    box-shadow: none !important;
}

[data-testid="stToolbar"] {
    display: block !important;
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 0 !important;
    height: 0 !important;
    overflow: visible !important;
    z-index: 1002 !important;
    visibility: visible !important;
    pointer-events: none !important;
}

[data-testid="stToolbarActions"],
[data-testid="stToolbar"] [data-testid="stAppDeployButton"],
[data-testid="stToolbar"] [data-testid="stMainMenu"],
[data-testid="stToolbar"] [data-testid="stMainMenuButton"],
.stAppToolbar [data-testid="stAppDeployButton"],
.stAppToolbar [data-testid="stMainMenuButton"] {
    display: none !important;
}

[data-testid="stAppDeployButton"],
[data-testid="stMainMenu"],
[data-testid="stMainMenuButton"],
.stAppDeployButton {
    display: none !important;
}

[data-testid="stExpandSidebarButton"] {
    display: flex !important;
    position: fixed !important;
    align-items: center !important;
    justify-content: center !important;
    top: 0.65rem !important;
    left: 0.75rem !important;
    width: 2.6rem !important;
    min-width: 2.6rem !important;
    height: 2.6rem !important;
    padding: 0 !important;
    border: 1px solid rgba(226, 232, 240, 0.9) !important;
    border-radius: 12px !important;
    background: rgba(255, 255, 255, 0.95) !important;
    backdrop-filter: blur(8px) !important;
    color: var(--ink-light) !important;
    box-shadow: 0 4px 14px -3px rgba(15, 23, 42, 0.12) !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 1003 !important;
    pointer-events: auto !important;
    transition: all 0.2s ease !important;
}

[data-testid="stExpandSidebarButton"]:hover {
    border-color: #A5B4FC !important;
    box-shadow: 0 6px 18px -4px rgba(99, 102, 241, 0.25) !important;
    transform: scale(1.04);
}

[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"] {
    display: none !important;
}

[data-testid="stExpandSidebarButton"]::after {
    content: "☰";
    position: absolute;
    top: 50%;
    left: 50%;
    font-size: 1.35rem;
    line-height: 1;
    transform: translate(-50%, -50%);
}

[data-testid="stSidebarCollapseButton"] {
    display: flex !important;
    justify-content: flex-end !important;
    position: relative !important;
    visibility: visible !important;
    opacity: 1 !important;
}

[data-testid="stSidebarCollapseButton"] button {
    position: relative !important;
    visibility: visible !important;
    opacity: 1 !important;
    width: 2.4rem !important;
    min-width: 2.4rem !important;
    height: 2.4rem !important;
    padding: 0 !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 12px !important;
    background: rgba(255, 255, 255, 0.08) !important;
    box-shadow: none !important;
    color: #F8FAFC !important;
    font-size: 0 !important;
    transition: all 0.2s ease !important;
}

[data-testid="stSidebarCollapseButton"] button:hover {
    background: rgba(255, 255, 255, 0.16) !important;
    border-color: rgba(255, 255, 255, 0.25) !important;
}

[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"] {
    display: none !important;
}

[data-testid="stSidebarCollapseButton"] button::after {
    content: "☰";
    position: absolute;
    top: 50%;
    left: 50%;
    font-size: 1.25rem;
    line-height: 1;
    transform: translate(-50%, -50%);
    color: #F8FAFC !important;
}

.block-container {
    width: 100%;
    max-width: 1440px;
    padding: 2.2rem 2.6rem 3.5rem;
}

.main [data-testid="stVerticalBlock"] {
    gap: 1.15rem;
}

h1, h2, h3, h4 {
    letter-spacing: -0.025em;
    color: var(--ink);
    font-weight: 800;
}

[data-testid="stHeaderLink"],
a[aria-label="Link to heading"],
.stMarkdownContainer h1 a,
.stMarkdownContainer h2 a,
.stMarkdownContainer h3 a,
.stMarkdownContainer h4 a {
    display: none !important;
}

/* ================== Luxury Hero Banner (Góc khám phá) ================== */
.hero {
    position: relative;
    overflow: hidden;
    border-radius: var(--radius-lg);
    padding: 2.6rem 2.9rem;
    color: #fff;
    background:
        radial-gradient(circle at 86% 22%, rgba(59, 130, 246, 0.28) 0%, transparent 45%),
        radial-gradient(circle at 12% 85%, rgba(99, 102, 241, 0.32) 0%, transparent 50%),
        linear-gradient(135deg, #121638 0%, #171F52 45%, #233480 100%);
    border: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow: 0 20px 48px -16px rgba(15, 23, 42, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.06) inset;
    margin-bottom: 2rem;
}
.hero::after {
    content: "";
    position: absolute;
    right: -70px;
    top: -90px;
    width: 340px;
    height: 340px;
    border-radius: 50%;
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 0 0 35px rgba(255, 255, 255, 0.02), 0 0 0 75px rgba(255, 255, 255, 0.015);
    pointer-events: none;
}
.hero h1 {
    margin: 0 0 0.65rem;
    font-size: 2.35rem;
    font-weight: 800;
    color: #FFFFFF;
    line-height: 1.2;
    letter-spacing: -0.03em;
}
.hero p {
    margin: 0;
    color: rgba(241, 245, 249, 0.9);
    font-size: 1.05rem;
    max-width: 820px;
    line-height: 1.68;
    font-weight: 400;
}
.pills {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
    margin-top: 1.45rem;
}
.pill {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.18);
    padding: 0.45rem 1.15rem;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #F8FAFC;
    backdrop-filter: blur(12px);
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
    transition: all 0.2s ease;
}
.pill:hover {
    background: rgba(255, 255, 255, 0.15);
    border-color: rgba(255, 255, 255, 0.35);
    transform: translateY(-1px);
}

/* ================== Step Navigation & Section Titles ================== */
.sec-title {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    font-weight: 800;
    font-size: 1.25rem;
    margin: 0.1rem 0 0.45rem;
    color: #0F172A;
    letter-spacing: -0.025em;
}
.step {
    display: inline-grid;
    place-items: center;
    width: 32px;
    height: 32px;
    border-radius: 10px;
    background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
    color: #FFFFFF;
    font-size: 0.95rem;
    font-weight: 800;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
    flex-shrink: 0;
}
.sec-desc {
    color: #64748B;
    font-size: 0.9rem;
    margin-top: -0.1rem;
    margin-bottom: 1.15rem;
    line-height: 1.6;
}

/* ================== Premium Card Containers ================== */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 22px !important;
    box-shadow: 0 4px 24px -10px rgba(15, 23, 42, 0.05) !important;
    padding: 1.5rem 1.65rem !important;
    transition: all 0.22s ease !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: #CBD5E1 !important;
    box-shadow: 0 10px 30px -10px rgba(15, 23, 42, 0.08) !important;
}

.card {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    padding: 1.5rem 1.6rem;
    box-shadow: 0 4px 20px -8px rgba(15, 23, 42, 0.06);
    height: 100%;
    transition: all 0.2s ease;
}
.card:hover {
    border-color: #CBD5E1;
    box-shadow: 0 10px 24px -10px rgba(15, 23, 42, 0.1);
}
.card h4 {
    margin: 0 0 1rem;
    font-size: 1.12rem;
    font-weight: 800;
    color: var(--ink);
    letter-spacing: -0.02em;
}

/* ================== Profile Aside & Step 1 ================== */
.profile-editor-aside {
    position: relative;
    isolation: isolate;
    display: flex;
    min-height: 295px;
    height: 100%;
    flex-direction: column;
    overflow: hidden;
    padding: 1.85rem 1.95rem;
    border-radius: 20px;
    color: #fff;
    background:
        radial-gradient(circle at 90% 10%, rgba(59, 130, 246, 0.25), transparent 45%),
        radial-gradient(circle at 10% 90%, rgba(99, 102, 241, 0.3), transparent 50%),
        linear-gradient(150deg, #13173A 0%, #192154 50%, #24327C 100%);
    border: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow: 0 20px 48px -18px rgba(15, 23, 42, 0.5), inset 0 1px 1px rgba(255, 255, 255, 0.1);
}
.profile-editor-aside::after {
    position: absolute;
    z-index: -1;
    right: -58px;
    bottom: -86px;
    width: 220px;
    height: 220px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 50%;
    box-shadow: 0 0 0 24px rgba(255, 255, 255, 0.02), 0 0 0 52px rgba(255, 255, 255, 0.015);
    content: "";
}
.profile-editor-kicker,
.profile-form-heading > span {
    color: #A5B4FC;
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}
.profile-editor-mark {
    display: grid;
    width: 40px;
    height: 40px;
    margin-top: 1.25rem;
    place-items: center;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
    font-size: 0.95rem;
    font-weight: 800;
    backdrop-filter: blur(8px);
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15);
}
.profile-editor-aside h2 {
    margin: 0.9rem 0 0.6rem;
    color: #fff;
    font-size: clamp(1.3rem, 2vw, 1.78rem);
    font-weight: 800;
    line-height: 1.25;
    letter-spacing: -0.035em;
}
.profile-editor-aside p {
    max-width: 320px;
    margin: 0;
    color: rgba(241, 245, 249, 0.85);
    font-size: 0.88rem;
    line-height: 1.65;
}
.profile-editor-foot {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    margin-top: auto;
    padding-top: 1.4rem;
    color: rgba(224, 231, 255, 0.85);
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.12em;
}
.profile-editor-foot span {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #10B981;
    box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.22);
}
.profile-form-heading {
    margin: 0.1rem 0 1.2rem;
}
.profile-form-heading p {
    margin: 0.35rem 0 0;
    color: #64748B;
    font-size: 0.9rem;
    font-weight: 500;
}
.profile-hint {
    display: flex;
    align-items: flex-start;
    gap: 0.65rem;
    margin-top: 1rem;
    padding: 0.85rem 1.15rem;
    border-left: 4px solid #4F46E5;
    border-radius: 0 12px 12px 0;
    background: #EEF2FF;
    color: #312E81;
    font-size: 0.86rem;
    line-height: 1.55;
    font-weight: 550;
}

/* ================== Title Bars & Sub-Headers ================== */
.card-title-bar,
.sub-column-title {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    font-size: 1.05rem;
    font-weight: 800;
    color: #0F172A;
    margin: 0.2rem 0 0.85rem;
    letter-spacing: -0.015em;
}
.subj-bar-accent {
    width: 3.5px;
    height: 18px;
    border-radius: 3px;
    background: #3B82F6;
    display: inline-block;
    flex-shrink: 0;
}
.subj-group-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.35rem 0.1rem 0.55rem;
    margin: 0.3rem 0 0.55rem;
    background: transparent !important;
    border: none !important;
}
.subj-title-left {
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.subj-name {
    font-size: 0.96rem;
    font-weight: 750;
    color: #0F172A;
    letter-spacing: -0.01em;
}
.subj-desc {
    font-size: 0.78rem;
    font-weight: 550;
    color: #64748B;
    text-align: right;
}

/* ================== Form Controls, Inputs & Radios ================== */
[data-testid="stRadio"] [role="radiogroup"] {
    gap: 0.65rem;
}
[data-testid="stRadio"] [role="radiogroup"] label {
    min-height: 42px;
    justify-content: center;
    padding: 0.55rem 1.15rem;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
    background: #FFFFFF;
    color: #475569;
    font-weight: 600;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    transition: all 0.18s ease;
}
[data-testid="stRadio"] [role="radiogroup"] label:hover {
    border-color: #CBD5E1;
    background: #F8FAFC;
}
[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {
    border: 1.5px solid #3B82F6 !important;
    background: #EEF4FF !important;
    color: #1D4ED8 !important;
    font-weight: 750 !important;
    box-shadow: 0 4px 14px -3px rgba(59, 130, 246, 0.25) !important;
}

[data-testid="stTextInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label,
[data-testid="stNumberInput"] label {
    color: #1E293B !important;
    font-size: 0.88rem !important;
    font-weight: 650 !important;
    letter-spacing: -0.01em;
}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    min-height: 46px;
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    background: #F8FAFC !important;
    color: #0F172A !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    transition: all 0.2s ease;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: #3B82F6 !important;
    background: #FFFFFF !important;
    box-shadow: 0 0 0 3.5px rgba(59, 130, 246, 0.16) !important;
}

[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
    min-height: 46px;
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    background: #F8FAFC !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
[data-testid="stSelectbox"] [data-baseweb="select"]:focus-within > div,
[data-testid="stMultiSelect"] [data-baseweb="select"]:focus-within > div {
    border-color: #3B82F6 !important;
    background: #FFFFFF !important;
    box-shadow: 0 0 0 3.5px rgba(59, 130, 246, 0.16) !important;
}

/* File Uploader */
[data-testid="stFileUploader"] section {
    border: 2px dashed #A5B4FC !important;
    border-radius: 18px !important;
    background: linear-gradient(135deg, #F8FAFF 0%, #F1F5FD 100%) !important;
    padding: 1.6rem !important;
    transition: all 0.22s ease !important;
}
[data-testid="stFileUploader"] section:hover {
    border-color: #3B82F6 !important;
    background: #EEF2FF !important;
    box-shadow: 0 8px 24px -8px rgba(59, 130, 246, 0.2) !important;
}

/* ================== Button Styling (Góc khám phá) ================== */
.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #4A56E2 0%, #3B82F6 100%) !important;
    border: 0 !important;
    border-radius: 14px !important;
    padding: 0.85rem 1.6rem !important;
    font-weight: 750 !important;
    font-size: 1.02rem !important;
    letter-spacing: -0.01em;
    color: #FFFFFF !important;
    box-shadow: 0 10px 24px -6px rgba(59, 130, 246, 0.45) !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    cursor: pointer !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 14px 28px -6px rgba(59, 130, 246, 0.6) !important;
}
.stButton > button[kind="primary"]:active {
    transform: translateY(0) !important;
    box-shadow: 0 6px 16px -4px rgba(59, 130, 246, 0.45) !important;
}

.stButton > button[kind="secondary"] {
    border-radius: 12px !important;
    border: 1px solid var(--line) !important;
    font-weight: 650 !important;
    background: #FFFFFF !important;
    color: #334155 !important;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04) !important;
    transition: all 0.18s ease !important;
}
.stButton > button[kind="secondary"]:hover {
    background: #F8FAFC !important;
    border-color: #CBD5E1 !important;
    color: #0F172A !important;
}

/* ================== Luxury Dark Sidebar (Góc khám phá) ================== */
[data-testid="stSidebar"] {
    width: 280px !important;
    min-width: 280px !important;
    background:
        radial-gradient(circle at 10% 95%, rgba(67, 83, 232, 0.22) 0%, transparent 45%),
        radial-gradient(circle at -15% 90%, rgba(99, 102, 241, 0.18) 0%, transparent 55%),
        linear-gradient(165deg, #11152F 0%, #151B42 45%, #182046 100%) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    box-shadow: 6px 0 28px -6px rgba(15, 23, 42, 0.5) !important;
    transition: width 220ms cubic-bezier(0.4, 0, 0.2, 1) !important;
}
[data-testid="stSidebar"][aria-expanded="false"] {
    width: 0 !important;
    min-width: 0 !important;
}
[data-testid="stSidebar"] > div:first-child {
    width: 280px !important;
    background:
        radial-gradient(circle at 10% 95%, rgba(67, 83, 232, 0.22) 0%, transparent 45%),
        radial-gradient(circle at -15% 90%, rgba(99, 102, 241, 0.18) 0%, transparent 55%),
        linear-gradient(165deg, #11152F 0%, #151B42 45%, #182046 100%) !important;
}
[data-testid="stSidebar"][aria-expanded="false"] > div:first-child {
    width: 0 !important;
}

[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {
    position: sticky !important;
    top: 0 !important;
    z-index: 30 !important;
    height: 2.5rem !important;
    min-height: 2.5rem !important;
    margin-bottom: 0 !important;
    padding: 0 !important;
    justify-content: flex-end !important;
    background: transparent !important;
}
[data-testid="stSidebar"] [data-testid="stLogoSpacer"] {
    display: none !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding: 0 1.6rem 1rem !important;
    overflow: hidden !important;
}
[data-testid="stSidebar"] [data-testid="stLayoutWrapper"]:has(> .st-key-sidebar-sticky-top) {
    position: relative;
}
.st-key-sidebar-sticky-top {
    position: relative;
    margin: 0;
    padding: 0.25rem 0 0.5rem;
}
.st-key-sidebar-menu-scroll {
    max-height: max(3rem, calc(100vh - 24rem));
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-width: thin;
    scrollbar-color: rgba(255, 255, 255, 0.24) transparent;
}
.st-key-sidebar-footer {
    margin-top: 0.25rem;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h4,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] *,
.sidebar-header,
.sidebar-title,
.sidebar-tagline,
.sidebar-desc,
.sidebar-admin-title,
.sidebar-admin-sub,
.sidebar-admin-sub * {
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
    margin: 0.8rem 0 0.35rem;
    font-size: 1.08rem;
    font-weight: 800;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h4 {
    margin: 0.5rem 0 0.35rem;
    font-size: 0.95rem;
    font-weight: 700;
}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: #FFFFFF !important;
    opacity: 0.92;
    line-height: 1.5;
}
[data-testid="stSidebar"] hr,
.sidebar-divider {
    border: 0 !important;
    border-top: 1px solid rgba(255, 255, 255, 0.1) !important;
    margin: 1.1rem 0 !important;
}

/* Sidebar Custom Header Elements */
.sidebar-header {
    padding: 0.2rem 0 1.15rem;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
.sidebar-title {
    color: #FFFFFF !important;
    font-size: 1.48rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
    margin: 0 0 0.35rem !important;
    line-height: 1.25 !important;
}
.sidebar-tagline,
.sidebar-desc {
    color: #FFFFFF !important;
    opacity: 0.95;
    font-size: 0.88rem !important;
    line-height: 1.5 !important;
    margin: 0 !important;
    font-weight: 500 !important;
}
.sidebar-admin-header {
    display: flex;
    align-items: flex-start;
    gap: 0.85rem;
    padding: 0.3rem 0 1.15rem;
}
.sidebar-admin-header > div:last-child {
    padding-top: 0.15rem;
}
.sidebar-admin-header .sidebar-tagline {
    margin-top: -0.45rem !important;
}
.sidebar-admin-badge {
    width: 44px;
    height: 44px;
    border-radius: 13px;
    background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
    display: grid;
    place-items: center;
    color: #FFFFFF;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
    flex-shrink: 0;
}
.sidebar-admin-title {
    color: #FFFFFF;
    font-size: 1.12rem;
    font-weight: 800;
    letter-spacing: -0.015em;
    line-height: 1.2;
}
.sidebar-admin-sub {
    color: #FFFFFF !important;
    opacity: 0.92;
    font-size: 0.82rem;
    margin-top: 0.2rem;
}
.sidebar-admin-sub strong {
    color: #FFFFFF;
}

/* Sidebar Brand Emblem */
.sidebar-brand {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin: 0.2rem 0 1.5rem;
    color: #FFFFFF;
}
.sidebar-brand > span {
    display: grid;
    width: 44px;
    height: 44px;
    flex: 0 0 44px;
    place-items: center;
    border: 1px solid rgba(255, 255, 255, 0.22);
    border-radius: 14px;
    background: linear-gradient(135deg, #6366F1 0%, #4F46E5 50%, #0EA5E9 100%);
    color: #FFFFFF;
    font-size: 0.95rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    box-shadow: 0 8px 24px -6px rgba(99, 102, 241, 0.75), inset 0 1px 1px rgba(255, 255, 255, 0.4);
}
.sidebar-brand strong {
    color: #FFFFFF;
    font-size: 1.02rem;
    font-weight: 800;
    letter-spacing: -0.01em;
    line-height: 1.25;
}
.sidebar-brand small {
    display: block;
    margin-top: 0.2rem;
    color: #E2E8F0;
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}

/* Sidebar Buttons */
[data-testid="stSidebar"] .stButton > button {
    min-height: 2.9rem !important;
    border-radius: 14px !important;
    padding: 0.55rem 0.95rem !important;
    font-size: 0.88rem !important;
    font-weight: 650 !important;
    line-height: 1.3 !important;
    text-align: left !important;
    white-space: normal !important;
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] .stButton > button > div {
    width: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    gap: 0.75rem !important;
}
[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
    background: rgba(255, 255, 255, 0.06) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    box-shadow: none !important;
    transition: all 0.2s ease !important;
}
[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
    background: rgba(255, 255, 255, 0.13) !important;
    border-color: rgba(165, 180, 252, 0.35) !important;
    color: #FFFFFF !important;
    transform: translateX(2px) !important;
    box-shadow: 0 4px 16px -4px rgba(0, 0, 0, 0.3) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #4F46E5 0%, #3B82F6 100%) !important;
    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    box-shadow: 0 8px 22px -4px rgba(59, 130, 246, 0.55) !important;
    font-weight: 750 !important;
}
[data-testid="stSidebar"] .stButton > button [data-testid="stIconMaterial"] {
    background: transparent !important;
    border-radius: 0 !important;
    width: auto !important;
    height: auto !important;
    padding: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 1.15rem !important;
    color: #FFFFFF !important;
    flex-shrink: 0 !important;
}

/* Center-aligned Buttons: Trang chủ & Đăng nhập */
[data-testid="stSidebar"] div[class*="st-key-btn_student_home"] .stButton > button,
[data-testid="stSidebar"] div[class*="st-key-btn_admin_login_home"] .stButton > button,
[data-testid="stSidebar"] div[class*="st-key-btn_admin_home"] .stButton > button,
[data-testid="stSidebar"] div[class*="st-key-btn_goto_admin_login"] .stButton > button,
[data-testid="stSidebar"] div[class*="st-key-btn_admin_logout"] .stButton > button,
[data-testid="stSidebar"] div[class*="st-key-btn_refresh_admin_data"] .stButton > button,
[data-testid="stSidebar"] .st-key-sidebar-footer .stButton > button {
    text-align: center !important;
}
[data-testid="stSidebar"] div[class*="st-key-btn_student_home"] .stButton > button > div,
[data-testid="stSidebar"] div[class*="st-key-btn_admin_login_home"] .stButton > button > div,
[data-testid="stSidebar"] div[class*="st-key-btn_admin_home"] .stButton > button > div,
[data-testid="stSidebar"] div[class*="st-key-btn_goto_admin_login"] .stButton > button > div,
[data-testid="stSidebar"] div[class*="st-key-btn_admin_logout"] .stButton > button > div,
[data-testid="stSidebar"] div[class*="st-key-btn_refresh_admin_data"] .stButton > button > div,
[data-testid="stSidebar"] .st-key-sidebar-footer .stButton > button > div {
    justify-content: center !important;
}

[data-testid="stSidebar"] div[class*="st-key-btn_explore_group_"] button::after {
    content: "›";
    font-size: 1.35rem;
    line-height: 1;
    color: #FFFFFF;
    margin-left: auto;
    padding-left: 0.35rem;
    transition: transform 0.2s ease, color 0.2s ease;
}
[data-testid="stSidebar"] div[class*="st-key-btn_explore_group_"] button:hover::after {
    color: #FFFFFF;
    transform: translateX(2px);
}
[data-testid="stSidebar"] .stButton > button p {
    color: inherit !important;
    font-size: inherit !important;
    line-height: inherit !important;
}

/* Sidebar Sticky Footer */
[data-testid="stSidebar"] .st-key-sidebar-footer {
    position: relative;
    margin-top: 1.8rem;
    padding-top: 0.85rem;
    padding-bottom: 0.5rem;
    border-top: 1px solid rgba(255, 255, 255, 0.12);
    background: transparent !important;
}
[data-testid="stSidebar"] .st-key-sidebar-footer hr {
    display: none !important;
}
[data-testid="stSidebar"] .st-key-sidebar-footer .stButton > button {
    background: rgba(255, 255, 255, 0.08) !important;
    border: 1px solid rgba(255, 255, 255, 0.18) !important;
    box-shadow: none !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] .st-key-sidebar-footer .stButton > button:hover {
    background: rgba(255, 255, 255, 0.16) !important;
    border-color: rgba(255, 255, 255, 0.35) !important;
    color: #FFFFFF !important;
}

/* ================== Tabs System ================== */
[data-testid="stTabs"] {
    margin-top: 0.55rem;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 0.35rem;
    padding: 0.4rem;
    border: 1px solid #E2E8F0;
    border-radius: 16px;
    background: #EAEEF8;
}
[data-testid="stTabs"] button[data-baseweb="tab"] {
    height: auto;
    min-height: 42px;
    padding: 0.55rem 1.15rem;
    border: 0;
    border-radius: 12px;
    color: #475569;
    font-size: 0.88rem;
    font-weight: 650;
    transition: all 0.18s ease;
}
[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
    color: #1E293B;
    background: rgba(255, 255, 255, 0.6);
}
[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
    background: #FFFFFF;
    color: #373CE5;
    box-shadow: 0 4px 14px -2px rgba(67, 83, 232, 0.18);
    border: 0;
    font-weight: 750;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] {
    display: none;
}

/* ================== Result Hero Showcase (Góc khám phá) ================== */
.res {
    display: flex;
    gap: 2rem;
    align-items: center;
    justify-content: space-between;
    border-radius: 22px;
    padding: 2.4rem 2.8rem;
    color: #fff;
    background:
        radial-gradient(circle at 90% 15%, rgba(59, 130, 246, 0.28) 0%, transparent 45%),
        radial-gradient(circle at 10% 85%, rgba(99, 102, 241, 0.32) 0%, transparent 50%),
        linear-gradient(135deg, #111538 0%, #182258 45%, #233482 100%);
    border: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow: 0 24px 50px -18px rgba(15, 23, 42, 0.55), 0 0 0 1px rgba(255, 255, 255, 0.06) inset;
    margin: 1.4rem 0;
}
.res-content {
    flex: 1;
    min-width: 0;
}
.res .k {
    font-size: 0.76rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: #93C5FD;
    font-weight: 800;
}
.res .v {
    font-size: 2.3rem;
    font-weight: 800;
    line-height: 1.18;
    margin: 0.35rem 0 0.55rem;
    color: #FFFFFF;
    letter-spacing: -0.03em;
}
.res .s {
    color: rgba(241, 245, 249, 0.94);
    font-size: 1.05rem;
    line-height: 1.55;
}
.res .s b {
    color: #FFFFFF;
    font-weight: 750;
}
.res .model-note,
.res .adjusted-note {
    margin-top: 0.75rem;
    font-size: 0.88rem;
    line-height: 1.55;
    color: rgba(226, 232, 240, 0.88);
}
.res .model-note span,
.res .adjusted-note span {
    color: rgba(255, 255, 255, 0.72);
    font-size: 0.8rem;
}
.res-gauge {
    position: relative;
    width: 130px;
    height: 130px;
    flex-shrink: 0;
    display: grid;
    place-items: center;
}
.res-gauge .gauge-svg {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
}
.res-gauge .gauge-center {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 1;
}
.res-gauge .gauge-num {
    font-size: 1.65rem;
    font-weight: 800;
    color: #FFFFFF;
    letter-spacing: -0.02em;
    line-height: 1.1;
}
.res-gauge .gauge-sub {
    font-size: 0.72rem;
    color: #94A3B8;
    font-weight: 600;
    margin-top: 2px;
}
.chip {
    display: inline-block;
    margin: 0.65rem 0.45rem 0 0;
    padding: 0.35rem 0.95rem;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 650;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.22);
    backdrop-filter: blur(8px);
}
.chip.warn {
    background: rgba(254, 243, 199, 0.95);
    color: #92400E;
    border-color: #FCD34D;
}

/* ================== Probability Progress Bars ================== */
.bar {
    margin: 0.85rem 0;
}
.bar .t {
    display: flex;
    justify-content: space-between;
    font-size: 0.92rem;
    font-weight: 650;
    margin-bottom: 0.4rem;
    color: #1E293B;
}
.bar .tr {
    height: 12px;
    border-radius: 999px;
    background: #F1F5F9;
    overflow: hidden;
    box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.05);
}
.bar .fl {
    height: 100%;
    border-radius: 999px;
    transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ================== Career Cards & Subgrid Layout ================== */
.cgrid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 1.25rem;
    align-items: stretch;
}
.career {
    position: relative;
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 20px;
    padding: 1.5rem;
    box-shadow: 0 8px 24px -14px rgba(15, 23, 42, 0.1);
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    flex-direction: column;
}
.career:hover {
    transform: translateY(-4px);
    box-shadow: 0 20px 40px -16px rgba(79, 70, 229, 0.22);
    border-color: rgba(129, 140, 248, 0.7);
}
.career.first {
    border: 2px solid #818CF8;
    background: linear-gradient(180deg, #FFFFFF 0%, #F5F3FF 100%);
    box-shadow: 0 16px 36px -14px rgba(79, 70, 229, 0.25), 0 0 0 1px rgba(99, 102, 241, 0.15);
}
@media(min-width: 900px) {
    .cgrid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
        grid-template-rows: repeat(9, auto);
        column-gap: 1.25rem;
        row-gap: 0;
    }
    .career {
        grid-row: span 9;
        display: grid;
        grid-template-rows: subgrid;
    }
}
.career .kv.stack,
.career .kv.stack span:last-child {
    min-width: 0;
    overflow-wrap: anywhere;
    word-break: break-word;
}
.career .kv.stack span:last-child {
    line-height: 1.55;
}
.career .kv.stack a {
    overflow-wrap: anywhere;
    word-break: break-word;
}
.rank {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.8rem;
    font-weight: 750;
    color: #4338CA;
    background: #EEF2FF;
    padding: 0.32rem 0.85rem;
    border-radius: 999px;
    width: fit-content;
    border: 1px solid #C7D2FE;
}
.rank.highlight,
.rank.gold {
    background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%);
    color: #FFFFFF;
    border: none;
    box-shadow: 0 3px 10px rgba(99, 102, 241, 0.35);
}
.group-pill {
    font-size: 0.78rem;
    color: #475569;
    font-weight: 650;
    background: #F1F5F9;
    padding: 0.28rem 0.75rem;
    border-radius: 999px;
}
.career h3 {
    font-size: 1.18rem;
    font-weight: 800;
    margin: 0.85rem 0 0.5rem;
    line-height: 1.35;
    color: #0F172A;
    letter-spacing: -0.02em;
}
.career p {
    font-size: 0.88rem;
    color: #475569;
    line-height: 1.58;
    min-height: 64px;
    margin: 0 0 0.85rem;
    flex-grow: 1;
}
.meter {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.95rem;
}
.meter .tr {
    flex: 1;
    height: 10px;
    background: #EEF2F7;
    border-radius: 999px;
    overflow: hidden;
}
.meter .fl {
    height: 100%;
    background: linear-gradient(90deg, #4F46E5 0%, #06B6D4 100%);
    border-radius: 999px;
    box-shadow: 0 0 8px rgba(79, 70, 229, 0.4);
}
.meter b {
    font-size: 0.95rem;
    color: #4338CA;
    font-weight: 800;
}
.kv {
    display: flex;
    justify-content: space-between;
    gap: 0.65rem;
    font-size: 0.86rem;
    padding: 0.48rem 0;
    border-top: 1px dashed var(--line);
}
.kv span:first-child {
    color: var(--muted);
    white-space: nowrap;
}
.kv span:last-child {
    text-align: right;
    font-weight: 600;
    min-width: 0;
    overflow-wrap: anywhere;
}
.kv.stack {
    flex-direction: column;
    gap: 0.25rem;
}
.kv.stack span:first-child {
    white-space: normal;
    overflow-wrap: anywhere;
    font-size: 0.76rem;
    font-weight: 750;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #1E3A8A;
}
.kv.stack span:last-child {
    text-align: left;
    font-weight: 500;
    color: #334155;
    line-height: 1.52;
    overflow-wrap: anywhere;
}
.kv.stack a {
    overflow-wrap: anywhere;
}

/* ================== AI Advisor Explanation ================== */
.explain {
    border-radius: 18px;
    padding: 1.6rem 1.85rem;
    background: #F3F6FF;
    border: 1px solid #E0E7FF;
    position: relative;
    box-shadow: 0 8px 24px -10px rgba(79, 70, 229, 0.1);
}
.explain .advisor-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.85rem;
}
.explain .b {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.8rem;
    font-weight: 750;
    color: #FFFFFF;
    background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%);
    padding: 0.3rem 0.85rem;
    border-radius: 999px;
    box-shadow: 0 2px 8px rgba(79, 70, 229, 0.25);
}
.explain .advisor-sub {
    font-size: 0.82rem;
    color: #64748B;
    font-weight: 600;
}
.explain .x {
    font-size: 1.02rem;
    line-height: 1.75;
    color: #1E293B;
    font-weight: 500;
}
.explain .n {
    margin-top: 0.85rem;
    font-size: 0.84rem;
    color: #64748B;
}

.tag {
    display: inline-block;
    margin: 0.3rem 0.4rem 0.3rem 0;
    padding: 0.45rem 1.05rem;
    border-radius: 999px;
    font-size: 0.86rem;
    font-weight: 650;
    transition: all 0.2s ease;
}
.tag.good {
    background: #EEF8F3;
    color: #047857;
    border: 1px solid #D1FAE5;
    box-shadow: 0 2px 6px rgba(16, 185, 129, 0.08);
}
.tag.todo {
    background: #FFFBEB;
    color: #92400E;
    border: 1px solid #FDE68A;
    box-shadow: 0 2px 6px rgba(245, 158, 11, 0.08);
}
.note {
    font-size: 0.84rem;
    color: var(--muted);
    margin: 0.75rem 0 0;
    line-height: 1.55;
}

/* ================== Feedback Panel ================== */
.st-key-feedback-panel [data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #E2E8F0 !important;
    border-radius: 22px !important;
    background: #FFFFFF !important;
    box-shadow: 0 10px 32px -20px rgba(30, 41, 59, 0.22);
}
.feedback-heading {
    margin: 0 0 1.2rem;
}
.feedback-eyebrow {
    margin: 0 0 0.4rem;
    color: #3B82F6;
    font-size: 0.74rem;
    font-weight: 800;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}
.feedback-heading h3 {
    margin: 0;
    color: #0F172A;
    font-size: 1.25rem;
    font-weight: 800;
    letter-spacing: -0.025em;
}
.feedback-heading > p:last-child {
    margin: 0.45rem 0 0;
    color: #64748B;
    font-size: 0.86rem;
    line-height: 1.6;
}
.st-key-feedback-panel .stButton > button {
    min-height: 42px;
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    background: #FFFFFF !important;
    color: #334155 !important;
    font-size: 0.86rem !important;
    font-weight: 650 !important;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04) !important;
    transition: all 0.18s ease !important;
}
.st-key-feedback-panel .stButton > button:hover {
    border-color: #A5B4FC !important;
    background: #F8F9FF !important;
    color: #4338CA !important;
}
.st-key-feedback-panel .stButton > button[kind="primary"] {
    border-color: #3B82F6 !important;
    background: #EEF4FF !important;
    color: #1D4ED8 !important;
    box-shadow: 0 4px 12px -2px rgba(59, 130, 246, 0.25) !important;
}
.st-key-feedback-panel .st-key-fb_submit button {
    min-height: 48px;
    border: 0 !important;
    border-radius: 14px !important;
    background: linear-gradient(90deg, #4A56E2 0%, #3B82F6 100%) !important;
    color: #FFFFFF !important;
    font-weight: 750 !important;
    box-shadow: 0 10px 24px -10px rgba(59, 130, 246, 0.5) !important;
    transition: all 0.2s ease !important;
}
.st-key-feedback-panel .st-key-fb_submit button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 14px 28px -8px rgba(59, 130, 246, 0.65) !important;
}
.st-key-feedback-panel [data-testid="stTextArea"] textarea {
    min-height: 76px !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    background: #F8FAFC !important;
    box-shadow: none !important;
    font-size: 0.86rem !important;
    color: #0F172A !important;
}
.st-key-feedback-panel [data-testid="stTextArea"] textarea:focus {
    border-color: #3B82F6 !important;
    background: #FFFFFF !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
}
.st-key-feedback-panel [data-testid="stMarkdownContainer"] p,
.st-key-feedback-panel [data-testid="stTextInput"] label {
    color: #334155 !important;
    font-size: 0.84rem !important;
    font-weight: 650 !important;
}
div[class*="st-key-fb_rating_star_"] button {
    all: unset !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: auto !important;
    min-width: 34px !important;
    min-height: 34px !important;
    padding: 0 0.1rem !important;
    border: 0 !important;
    outline: 0 !important;
    border-radius: 0 !important;
    background: transparent !important;
    color: #929CC2 !important;
    font-size: 1.35rem !important;
    font-weight: 500 !important;
    font-family: inherit !important;
    line-height: 1 !important;
    cursor: pointer !important;
    box-shadow: none !important;
}
div[class*="st-key-fb_rating_star_"] button[kind="primary"] {
    color: #F59E0B !important;
    -webkit-text-fill-color: #F59E0B !important;
}
div[class*="st-key-fb_rating_star_"] button[kind="primary"] *,
div[class*="st-key-fb_rating_star_"] button[kind="primary"] p {
    color: #F59E0B !important;
    -webkit-text-fill-color: #F59E0B !important;
}
div[class*="st-key-fb_rating_star_"] button[kind="secondary"] {
    color: #CBD5E1 !important;
    -webkit-text-fill-color: #CBD5E1 !important;
}
div[class*="st-key-fb_rating_star_"] button[kind="secondary"] *,
div[class*="st-key-fb_rating_star_"] button[kind="secondary"] p {
    color: #CBD5E1 !important;
    -webkit-text-fill-color: #CBD5E1 !important;
}
div[class*="st-key-fb_rating_star_"] button:hover {
    all: unset !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: auto !important;
    min-width: 34px !important;
    min-height: 34px !important;
    padding: 0 0.1rem !important;
    border: none !important;
    background: transparent !important;
    color: #F59E0B !important;
    -webkit-text-fill-color: #F59E0B !important;
    box-shadow: none !important;
    font-size: 1.35rem !important;
    font-weight: 500 !important;
    font-family: inherit !important;
    line-height: 1 !important;
    cursor: pointer !important;
    transform: scale(1.15);
    transition: transform 0.15s ease;
}
div[class*="st-key-fb_rating_star_"] button:focus:not(:focus-visible) {
    box-shadow: none !important;
}

/* ================== Career Explorer Grid ================== */
.career-explorer-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
    gap: 1.25rem;
    align-items: stretch;
    margin-top: 1.35rem;
}
.career-explorer-card {
    min-width: 0;
    padding: 1.5rem;
    border: 1px solid #E2E8F0;
    border-radius: 20px;
    background: #FFFFFF;
    box-shadow: 0 8px 24px -14px rgba(15, 23, 42, 0.1);
    transition: all 0.22s ease;
}
.career-explorer-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 16px 36px -14px rgba(79, 70, 229, 0.18);
    border-color: rgba(129, 140, 248, 0.6);
}
.career-explorer-card h3 {
    margin: 0.85rem 0 0.5rem;
    font-size: 1.15rem;
    font-weight: 800;
    color: #0F172A;
}
.career-explorer-card p {
    color: #475569;
    font-size: 0.88rem;
    line-height: 1.62;
}
.career-explorer-card .kv.stack {
    align-items: stretch;
    min-width: 0;
}
.career-explorer-card .kv.stack > span:last-child,
.career-explorer-card .career-source-links {
    display: block;
    width: 100%;
    min-width: 0;
    text-align: left;
    line-height: 1.55;
    overflow-wrap: anywhere;
    word-break: break-word;
}
.career-explorer-card .career-source-links a {
    display: block;
    margin: 0.2rem 0;
    line-height: 1.55;
    overflow-wrap: anywhere;
    word-break: break-word;
    color: #4F46E5;
    text-decoration: none;
    font-weight: 600;
}
.career-explorer-card .career-source-links a:hover {
    text-decoration: underline;
}
.career-explorer-card .career-source-links .source-scope {
    color: var(--muted);
    font-size: 0.8rem;
}

/* ================== Admin Dashboard & KPI Cards (Góc khám phá) ================== */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1.15rem;
    margin: 1.35rem 0 1.6rem;
}
.kpi-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 20px;
    padding: 1.35rem 1.55rem;
    box-shadow: 0 4px 18px rgba(15, 23, 42, 0.04);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 120px;
    transition: all 0.22s ease;
}
.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 26px -8px rgba(15, 23, 42, 0.1);
    border-color: #CBD5E1;
}
.kpi-top {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.75rem;
}
.kpi-title {
    font-size: 0.74rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #64748B;
    font-weight: 750;
    line-height: 1.35;
    max-width: 155px;
}
.kpi-icon-badge {
    width: 36px;
    height: 36px;
    border-radius: 11px;
    background: #EEF2FF;
    display: grid;
    place-items: center;
    flex-shrink: 0;
}
.kpi-val {
    font-size: 2.15rem;
    font-weight: 800;
    color: #0F172A;
    line-height: 1.15;
    letter-spacing: -0.025em;
    margin-top: 0.5rem;
}
.kpi-sub {
    font-size: 0.8rem;
    color: var(--muted);
    margin-top: 0.35rem;
}

/* Admin Horizontal Distribution Bar Chart */
.admin-dist-container {
    padding: 0.4rem 0;
}
.admin-dist-row {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin: 0.75rem 0;
}
.admin-dist-label {
    width: 180px;
    font-size: 0.88rem;
    font-weight: 600;
    color: #334155;
    flex-shrink: 0;
}
.admin-dist-bar-wrap {
    flex: 1;
    height: 12px;
    background: #EEF2FF;
    border-radius: 999px;
    overflow: hidden;
}
.admin-dist-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #4F46E5 0%, #3B82F6 100%);
    border-radius: 999px;
}
.admin-dist-count {
    width: 45px;
    text-align: right;
    font-size: 0.88rem;
    font-weight: 750;
    color: #0F172A;
}
.admin-dist-caption {
    margin-top: 1rem;
    font-size: 0.82rem;
    color: #64748B;
}

/* Admin Retrain Action Banner */
.admin-retrain-banner {
    background: linear-gradient(135deg, #131738 0%, #171E4B 50%, #1E2860 100%);
    border-radius: 18px;
    padding: 1.6rem 1.8rem;
    color: #FFFFFF;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.5rem;
    box-shadow: 0 16px 36px -12px rgba(15, 23, 42, 0.4);
}

/* Status Pill */
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.4rem 0.95rem;
    border-radius: 999px;
    font-size: 0.86rem;
    font-weight: 700;
}
.status-pill.ok {
    background: #ECFDF5;
    color: #065F46;
    border: 1px solid #A7F3D0;
}
.status-pill.ok span {
    color: #10B981;
}
.status-pill.err {
    background: #FEF2F2;
    color: #991B1B;
    border: 1px solid #FECACA;
}
.status-pill.err span {
    color: #EF4444;
}

.main [data-testid="stMetric"] {
    min-height: 104px;
    padding: 1.1rem 1.25rem;
    border: 1px solid #E2E8F0;
    border-radius: 16px;
    background: #FFFFFF;
    box-shadow: 0 6px 18px -10px rgba(15, 23, 42, 0.08);
}
.main [data-testid="stMetricLabel"] {
    color: #64748B;
    font-size: 0.8rem;
    font-weight: 700;
}
.main [data-testid="stMetricValue"] {
    color: #0F172A;
    font-size: 1.65rem;
    font-weight: 800;
    letter-spacing: -0.02em;
}

/* ================== Admin Login Modal (Góc khám phá) ================== */
.st-key-admin-login-card {
    box-sizing: border-box;
    width: min(500px, 100%);
    margin: clamp(2rem, 7vh, 4.5rem) auto 2rem;
    padding: 2.6rem 2.8rem;
    border: 1px solid #E2E8F0 !important;
    border-radius: 24px !important;
    background: #FFFFFF !important;
    box-shadow: 0 20px 50px -20px rgba(15, 23, 42, 0.18), 0 0 0 1px rgba(255, 255, 255, 0.8) inset !important;
}
.login-lock-container {
    display: flex;
    justify-content: center;
    margin-bottom: 1.25rem;
}
.login-lock-badge {
    width: 52px;
    height: 52px;
    border-radius: 16px;
    background: #14193C;
    display: grid;
    place-items: center;
    box-shadow: 0 8px 20px -4px rgba(20, 25, 60, 0.4);
}
.login-title {
    text-align: center;
    font-size: 1.85rem !important;
    font-weight: 800 !important;
    color: #0F172A !important;
    margin: 0 0 0.4rem !important;
}
.login-desc {
    text-align: center;
    color: #64748B !important;
    font-size: 0.92rem !important;
    margin: 0 0 1.5rem !important;
}
.st-key-admin-login-card h2 {
    margin: 0 0 0.4rem;
    color: #0F172A;
    text-align: center;
    font-size: 1.85rem;
    font-weight: 800;
    letter-spacing: -0.03em;
}
.st-key-admin-login-card > div > [data-testid="stMarkdownContainer"] p {
    text-align: center;
    color: #64748B;
    font-size: 0.92rem;
    margin-bottom: 1.5rem;
}
.st-key-admin-login-card [data-testid="stForm"] {
    padding: 0;
    border: 0;
    background: transparent;
}
.st-key-admin-login-card [data-testid="stTextInput"] {
    margin: 0.45rem 0;
}
.st-key-admin-login-card [data-testid="stForm"] .stButton > button {
    min-height: 48px;
    font-size: 1.02rem !important;
    font-weight: 750 !important;
    border-radius: 14px !important;
    margin-top: 0.8rem;
    background: linear-gradient(90deg, #4A56E2 0%, #3B82F6 100%) !important;
}

[data-testid="stDataFrame"],
[data-testid="stTable"] {
    overflow: hidden;
    border: 1px solid #E2E8F0;
    border-radius: 16px;
    background: #FFFFFF;
    box-shadow: 0 4px 14px -6px rgba(15, 23, 42, 0.06);
}

/* ================== Responsive Breakpoints ================== */
@media (max-width: 1100px) {
    .block-container {
        padding-right: 1.6rem;
        padding-left: 1.6rem;
    }
    .kpi-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media (max-width: 768px) {
    [data-testid="stSidebar"] {
        width: min(280px, calc(100vw - 2rem)) !important;
        min-width: min(280px, calc(100vw - 2rem)) !important;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarHeader"] [data-testid="stSidebarCollapseButton"] {
        transform: translateY(0.65rem);
    }
    [data-testid="stSidebar"][aria-expanded="false"] {
        width: 0 !important;
        min-width: 0 !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        width: 100% !important;
    }
    [data-testid="stSidebar"][aria-expanded="false"] > div:first-child {
        width: 0 !important;
    }
    .st-key-sidebar-sticky-top {
        margin-top: -1.15rem;
    }
    .block-container {
        padding: 1.4rem 1.1rem 2.2rem;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        padding: 1.1rem !important;
    }
    .hero {
        padding: 1.8rem 1.6rem;
    }
    .hero h1 {
        font-size: 1.65rem;
    }
    .res {
        flex-direction: column;
        align-items: flex-start;
        padding: 1.7rem 1.6rem;
    }
    .res .v {
        font-size: 1.85rem;
    }
    .profile-editor-aside {
        min-height: 240px;
        padding: 1.4rem 1.5rem;
    }
    .kpi-grid {
        grid-template-columns: 1fr;
    }
    .st-key-admin-login-card {
        margin: 1.5rem auto;
        padding: 1.6rem;
    }
    [data-testid="stRadio"] [role="radiogroup"] {
        flex-wrap: wrap;
    }
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        overflow-x: auto;
        flex-wrap: nowrap;
    }
    [data-testid="stTabs"] button[data-baseweb="tab"] {
        white-space: nowrap;
    }
}
</style>
"""


def e(x) -> str:
    """Escape an toàn cho HTML để ngăn ngừa lỗi giao diện và tấn công XSS."""
    return html.escape(str(x if x is not None else ""))


def hero(student_name: str = "") -> str:
    """Banner mở đầu giới thiệu trải nghiệm định hướng nghề nghiệp."""
    pills = "".join(f"<span class='pill'>{e(t)}</span>" for t in [
        "Từ những môn học bạn yêu thích",
        "Tôn trọng sở thích và thế mạnh riêng",
        "Gợi mở bước đi tiếp theo"
    ])
    greeting = f"Chào {e(student_name)}, " if student_name and student_name != "Sinh viên" else "Chào bạn, "
    return (
        f"<div class='hero'>"
        f"  <h1>Tìm hướng đi phù hợp với bạn</h1>"
        f"  <p>{greeting}cùng nhìn lại những gì bạn học tốt, điều bạn quan tâm và những lựa chọn nghề nghiệp "
        f"  có thể khám phá trong thế giới công nghệ.</p>"
        f"  <div class='pills'>{pills}</div>"
        f"</div>"
    )


def section(n: int, title: str, subtitle: str = "") -> str:
    """Tiêu đề từng bước phân tích có số thứ tự nổi bật."""
    sub_html = f"<div class='sec-desc'>{e(subtitle)}</div>" if subtitle else ""
    return (
        f"<div class='sec-title'><span class='step'>{n}</span>{e(title)}</div>"
        f"{sub_html}"
    )


def category_badge(name: str, desc: str, kind: str) -> str:
    """Tiêu đề nhóm môn học có thanh nhấn dọc theo phong cách Góc Khám Phá."""
    return (
        f"<div class='subj-group-header {kind}'>"
        f"  <div class='subj-title-left'>"
        f"    <span class='subj-bar-accent'></span>"
        f"    <span>{e(name)}</span>"
        f"  </div>"
        f"  <span style='font-size:0.75rem;font-weight:600;color:#64748B;text-align:right'>{e(desc)}</span>"
        f"</div>"
    )


def status_card(ok: bool, version: str, api_url: str) -> str:
    """Thẻ trạng thái hệ thống dành cho quản trị viên."""
    txt = "Hệ thống đang hoạt động" if ok else "Không kết nối được hệ thống"
    pill_cls = "ok" if ok else "err"
    return (
        f"<div style='margin-bottom:0.9rem'>"
        f"  <span class='status-pill {pill_cls}'><span>●</span> {txt}</span>"
        f"</div>"
        f"<div class='kv'><span>Phiên bản hệ thống</span><b>v{e(version)}</b></div>"
        f"<div class='kv'><span>Địa chỉ dịch vụ</span><span style='font-size:.78rem;color:#64748B'>{e(api_url)}</span></div>"
    )


def result_hero(
    group: str,
    conf: float,
    top_name: str,
    top_pct: float,
    adjusted: bool,
    student_name: str = "Sinh viên",
    score_based_group: str = "",
) -> str:
    """Tách gợi ý theo điểm môn học khỏi gợi ý đã cân nhắc sở thích kèm đồng hồ tròn đo độ phù hợp."""
    score_based_group = score_based_group or group
    chips = ""
    if adjusted:
        chips += "<span class='chip'>Đã cân nhắc sở thích và thế mạnh của bạn</span>"
    if conf < 50:
        chips += "<span class='chip warn'>Điểm môn học chưa cho thấy rõ một hướng nổi trội</span>"

    match_str = f"Một lựa chọn đáng để tìm hiểu: <b>{e(top_name)}</b> · Mức độ phù hợp tham khảo {top_pct:.1f}%" if top_name else ""
    name_prefix = f"Dành cho {e(student_name)} · " if student_name and student_name != "Sinh viên" else ""
    adjusted_line = (
        "<div class='adjusted-note'>Thứ tự gợi ý đã cân nhắc thêm sở thích và kỹ năng của bạn.</div>"
        if adjusted else ""
    )

    gauge_val = top_pct if top_pct > 0 else conf
    gauge_pct = max(0.0, min(100.0, gauge_val))
    circ = 226.19
    offset = circ * (1.0 - gauge_pct / 100.0)
    gauge_html = (
        f"<div class='res-gauge'>"
        f"  <div class='res-gauge-box'>"
        f"    <svg width='92' height='92' viewBox='0 0 92 92'>"
        f"      <circle class='res-gauge-bg' cx='46' cy='46' r='36'></circle>"
        f"      <circle class='res-gauge-bar' cx='46' cy='46' r='36' "
        f"        stroke-dasharray='{circ:.2f}' stroke-dashoffset='{offset:.2f}'></circle>"
        f"    </svg>"
        f"    <div class='res-gauge-num'>{gauge_pct:.1f}%</div>"
        f"  </div>"
        f"  <div class='res-gauge-lbl'>Mức độ phù hợp</div>"
        f"</div>"
    )

    return (
        f"<div class='res'>"
        f"  <div>"
        f"    <div class='k'>{name_prefix}{'Gợi ý sau khi cân nhắc sở thích' if adjusted else 'Gợi ý từ điểm môn học'}</div>"
        f"    <div class='v'>{e(group)}</div>"
        f"    <div class='s'>{match_str}</div>"
        f"    <div>{chips}</div>"
        f"    <div class='model-note'><b>Gợi ý theo điểm môn học:</b> {e(score_based_group)} "
        f"· <b>Mức dự đoán {conf:.1f}%</b> "
        f"<span>(dựa trên dữ liệu hệ thống đã học; không cho biết mức độ phù hợp hay khả năng thành công ngoài thực tế)</span></div>"
        f"    {adjusted_line}"
        f"  </div>"
        f"  {gauge_html}"
        f"</div>"
    )


def prob_bars(probs: dict) -> str:
    """Thanh thể hiện những nhóm ngành hệ thống gợi ý theo điểm môn học."""
    items = sorted(probs.items(), key=lambda kv: -kv[1])
    out = [
        "<div class='card'>"
        "<div class='card-title-bar'><span class='bar-accent'></span><h4>Các nhóm ngành được gợi ý theo điểm môn học</h4></div>"
    ]
    for i, (g, p) in enumerate(items):
        color = PALETTE[i % len(PALETTE)]
        out.append(
            f"<div class='bar'>"
            f"  <div class='t'><span>{e(g)}</span><span style='color:{color};font-weight:750'>{p:.1f}%</span></div>"
            f"  <div class='tr'><div class='fl' style='width:{max(p, 0.8):.1f}%;background:{color}'></div></div>"
            f"</div>"
        )
    out.append("<div class='note'>Các tỉ lệ cho biết hệ thống nghiêng về nhóm nào dựa trên dữ liệu đã học. Đây không phải mức độ phù hợp hay khả năng thành công ngoài thực tế. Sở thích và kỹ năng được cân nhắc riêng khi sắp xếp gợi ý.</div></div>")
    return "".join(out)


def radar_svg(scores: dict) -> str:
    """Biểu đồ Radar SVG năng lực học tập 12 môn học không cần nạp thư viện ngoài."""
    keys = [k for k in AXIS_LABEL if k in scores]
    n, cx, cy, R = len(keys), 210, 190, 128
    if n == 0:
        return "<div class='card'><div class='card-title-bar'><span class='bar-accent'></span><h4>Hồ sơ năng lực</h4></div><p>Chưa có dữ liệu điểm.</p></div>"

    def pt(i, r):
        a = -math.pi / 2 + 2 * math.pi * i / n
        return cx + r * math.cos(a), cy + r * math.sin(a)

    g = [
        "<defs>",
        "  <linearGradient id='radarAreaGrad' x1='0%' y1='0%' x2='100%' y2='100%'>",
        "    <stop offset='0%' stop-color='#6366F1' stop-opacity='0.42'/>",
        "    <stop offset='100%' stop-color='#0EA5E9' stop-opacity='0.22'/>",
        "  </linearGradient>",
        "  <filter id='radarShadow' x='-20%' y='-20%' width='140%' height='140%'>",
        "    <feDropShadow dx='0' dy='3' stdDeviation='4' flood-color='#4F46E5' flood-opacity='0.28'/>",
        "  </filter>",
        "</defs>",
    ]
    # Các vòng đồng tâm 2.5, 5.0, 7.5, 10.0
    for lv in (2.5, 5, 7.5, 10):
        stroke_color = "#CBD5E1" if lv == 10 else "#E2E8F0"
        dash = "stroke-dasharray='3,3'" if lv < 10 else ""
        g.append("<polygon points='" + " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, R * lv / 10) for i in range(n)))
                 + f"' fill='none' stroke='{stroke_color}' stroke-width='1.2' {dash}/>")
    # Các trục toạ độ
    for i in range(n):
        x, y = pt(i, R)
        g.append(f"<line x1='{cx}' y1='{cy}' x2='{x:.1f}' y2='{y:.1f}' stroke='#E2E8F0' stroke-width='1.2'/>")

    # Đa giác điểm số
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, R * max(0, min(10, float(scores[k]))) / 10) for i, k in enumerate(keys)))
    g.append(f"<polygon points='{poly}' fill='url(#radarAreaGrad)' stroke='#4F46E5' stroke-width='2.6' filter='url(#radarShadow)'/>")

    for i, k in enumerate(keys):
        x, y = pt(i, R * max(0, min(10, float(scores[k]))) / 10)
        g.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='4.5' fill='#4F46E5' stroke='#fff' stroke-width='2'/>")
        lx, ly = pt(i, R + 26)
        anc = "middle" if abs(lx - cx) < 12 else ("start" if lx > cx else "end")
        score_val = float(scores[k])
        g.append(f"<text x='{lx:.1f}' y='{ly:.1f}' text-anchor='{anc}' dominant-baseline='middle' font-size='11.5' font-weight='600' fill='#334155'>"
                 f"{e(AXIS_LABEL[k])} <tspan fill='#4F46E5' font-weight='750'>{score_val:.1f}</tspan></text>")

    return (
        f"<div class='card'>"
        f"  <div class='card-title-bar'><span class='bar-accent'></span><h4>Hồ sơ năng lực 12 học phần</h4></div>"
        f"  <svg viewBox='-40 0 500 380' width='100%' role='img' aria-label='Biểu đồ radar năng lực môn học'>{''.join(g)}</svg>"
        f"</div>"
    )


def explain_card(text: str, note: str, is_ai: bool, disclaimer: str) -> str:
    """Thẻ lời khuyên cá nhân hóa với huy hiệu góc nhìn và biểu tượng đại diện."""
    badge = "Góc nhìn dành riêng cho bạn" if is_ai else "Gợi ý tổng hợp dành riêng cho bạn"
    avatar_svg = (
        "<svg width='22' height='22' viewBox='0 0 24 24' fill='none' stroke='#4F46E5' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
        "<path d='m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z'></path>"
        "</svg>"
    )
    return (
        f"<div class='explain'>"
        f"  <div class='advisor-header'>"
        f"    <div class='advisor-avatar'>{avatar_svg}</div>"
        f"    <div>"
        f"      <span class='b'>{badge}</span>"
        f"      <div style='font-size:0.82rem;color:#4338CA;font-weight:700;margin-top:3px'>Tư vấn cá nhân hóa định hướng sự nghiệp</div>"
        f"    </div>"
        f"  </div>"
        f"  <div class='x'>{e(text)}</div>"
        f"  <div class='n'>{e(note)}</div>"
        f"</div>"
        f"<div class='note'>{e(disclaimer)}</div>"
    )


def _friendly_market_value(value: object, fallback: str, empty: str = "Đang cập nhật") -> str:
    """Hiển thị giá trị thị trường theo phong cách thân thiện, không lộ ngôn ngữ kỹ thuật cứng."""
    text = str(value or "").strip()
    if not text:
        return empty
    lower = text.lower()
    if any(token in lower for token in (
        "chưa có dữ liệu",
        "chưa có nguồn",
        "chưa xác định",
        "chưa có dữ liệu được xác thực",
        "chưa có nguồn kiểm chứng",
        "not available",
        "unknown",
    )):
        return fallback
    return text


def _salary_summary(salary_data: object, fallback: str) -> str:
    if not isinstance(salary_data, dict):
        return fallback

    observations = salary_data.get("observations")
    if not isinstance(observations, list) or not observations:
        note = str(salary_data.get("note") or "").strip()
        return note or "Nguồn hiện chưa công khai số liệu lương."

    def amount(value: object) -> str:
        try:
            millions = float(value) / 1_000_000
        except (TypeError, ValueError):
            return ""
        return f"{millions:.1f}".rstrip("0").rstrip(".")

    lines = []
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        statistic = observation.get("statistic")
        low = amount(observation.get("minimum_vnd_per_month"))
        high = amount(observation.get("maximum_vnd_per_month"))
        value = amount(observation.get("value_vnd_per_month"))
        if statistic == "median" and value:
            experience = str(observation.get("experience") or "")
            experience_labels = {
                "<1 year": "dưới 1 năm",
                "At least 1 year experience": "từ 1 năm kinh nghiệm",
                "1-2 years": "1–2 năm",
                "2-4 years": "2–4 năm",
                "3-4 years": "3–4 năm",
                "2 years": "2 năm",
                "3 years": "3 năm",
                "5-8 years": "5–8 năm",
                "5-8 years; advanced certification required": "5–8 năm; yêu cầu chứng chỉ chuyên sâu",
                ">8 years": "trên 8 năm",
                ">8 years; advanced certification required": "trên 8 năm; yêu cầu chứng chỉ chuyên sâu",
                "Ranges from entry level to senior": "từ ít năm kinh nghiệm đến cấp độ cao",
                "Median experience: 2 years": "kinh nghiệm trung vị 2 năm",
                "Seniority not separated": "không tách cấp bậc",
                "Requires 2 years experience": "yêu cầu 2 năm kinh nghiệm",
                "Requires 4 years experience": "yêu cầu 4 năm kinh nghiệm",
                "SOC Analyst Level 1": "SOC Analyst cấp 1",
            }
            suffix = f" ({experience_labels.get(experience, experience)})" if experience else ""
            lines.append(f"Trung vị{suffix}: {value} triệu VND/tháng")
        elif low and high:
            lines.append(f"Khoảng được ghi nhận: {low}–{high} triệu VND/tháng")
        elif high:
            lines.append(f"Mức trần được ghi nhận: tối đa {high} triệu VND/tháng")
        elif value:
            label = "Mức trung bình" if statistic == "mean" else "Mức tham khảo"
            lines.append(f"{label}: {value} triệu VND/tháng")
        expires_at = str(observation.get("expires_at") or "").strip()
        if expires_at and lines:
            lines[-1] += f" (tin hết hạn {expires_at})"

    if not lines:
        note = str(salary_data.get("note") or "").strip()
        return note or "Nguồn hiện chưa công khai số liệu lương."

    status_labels = {
        "historical_report": "Dữ liệu lịch sử, không phải mức lương hiện hành",
        "expired_listing": "Tin tuyển dụng đã hết hạn",
        "listing_expiry_unknown": "Chưa xác nhận tin tuyển dụng còn hiệu lực",
    }
    status = status_labels.get(str(salary_data.get("status") or ""))
    data_period = str(salary_data.get("data_period") or "").strip()
    period_labels = {
        "2023-2024 chart; exact data period uncertain": "2023–2024 (biểu đồ; kỳ dữ liệu chưa chắc chắn)",
        "2023-2024; page updated in 2024": "Dữ liệu 2023–2024; trang cập nhật năm 2024",
        "2025-2026 report": "Báo cáo 2025–2026",
        "2023 survey; 2023-2024 report": "Khảo sát năm 2023; báo cáo 2023–2024",
        "2024-2025 report": "Báo cáo 2024–2025",
        "2025-2026 report; figures are for Back-end Developer": "Báo cáo 2025–2026; số liệu cho Back-end Developer",
        "2025 article; survey period not specified": "Bài viết năm 2025; không nêu kỳ khảo sát",
        "Indeed result updated 2026-10-12; checked 2026-10-19": "Indeed cập nhật 2026-10-12; rà soát 2026-10-19",
        "Indeed result updated 2026-10-11; checked 2026-10-19": "Indeed cập nhật 2026-10-11; rà soát 2026-10-19",
        "Updated 2026-10-12; checked 2026-10-19": "Cập nhật 2026-10-12; rà soát 2026-10-19",
        "One job listing; expired 2026-07-23": "Một tin tuyển dụng; hết hạn 2026-07-23",
        "One job listing; expired 2026-05-08": "Một tin tuyển dụng; hết hạn 2026-05-08",
        "One job listing; expired 2026-08-09": "Một tin tuyển dụng; hết hạn 2026-08-09",
        "One job listing; expired 2023-04-22": "Một tin tuyển dụng; hết hạn 2023-04-22",
        "One job listing expired 2024-05-09; salary not disclosed": "Một tin tuyển dụng hết hạn 2024-05-09; không công khai lương",
        "Job listing checked 2026-10-15; expiry date not recorded": "Tin tuyển dụng rà soát 2026-10-15; chưa ghi nhận ngày hết hạn",
    }
    data_period = period_labels.get(data_period, data_period)
    location = str(salary_data.get("location") or "").strip()
    location_labels = {
        "Vietnam": "Việt Nam",
        "Hanoi": "Hà Nội",
        "Vietnam (job listing did not specify city)": "Việt Nam (tin tuyển dụng không nêu thành phố)",
        "Vietnam; one listing did not specify city": "Việt Nam; một tin không nêu thành phố",
        "One remote listing; one listing did not specify location": "Một tin làm từ xa; một tin không nêu địa điểm",
    }
    location = location_labels.get(location, location)
    proxy_role = str(salary_data.get("proxy_role") or "").strip()
    proxy_labels = {
        "Back-end Developer": "Lập trình viên Back-end",
        "Data Scientist (excluding Data Analyst)": "Data Scientist (không gồm Data Analyst)",
        "DevOps/DevSecOps; SRE not separated": "DevOps/DevSecOps; không tách riêng SRE",
        "General tester roles; titles and seniority not separated": "Vị trí tester nói chung; không tách chức danh/cấp bậc",
        "IT Support (not specific to IT consulting)": "IT Support (không đại diện riêng cho tư vấn CNTT)",
        "Graphic Designer (not specific to 3D artists)": "Graphic Designer (không riêng họa sĩ 3D)",
    }
    proxy_role = proxy_labels.get(proxy_role, proxy_role)
    sample_size = salary_data.get("sample_size")
    notes = [*lines]
    if status:
        notes.append(status)
    if data_period:
        notes.append(f"Kỳ dữ liệu: {data_period}")
    if location:
        notes.append(f"Khu vực: {location}")
    if isinstance(sample_size, int) and sample_size > 0:
        notes.append(f"Cỡ mẫu: {sample_size}")
    if proxy_role:
        notes.append(f"Tham khảo nghề gần: {proxy_role}; không đại diện riêng chức danh này")
    return "; ".join(notes)


def _career_reason(career: dict) -> str:
    reasons = []
    strengths = career.get("strengths")
    if isinstance(strengths, list) and strengths:
        subjects = [
            str(item.get("subject"))
            for item in strengths[:3]
            if isinstance(item, dict) and item.get("subject")
        ]
        if subjects:
            reasons.append("Môn học phù hợp: " + ", ".join(subjects))

    skills = career.get("soft_skill_matches")
    if isinstance(skills, list) and skills:
        labels = [
            str(item.get("label"))
            for item in skills[:3]
            if isinstance(item, dict) and item.get("label")
        ]
        if labels:
            reasons.append("Kỹ năng bạn chọn phù hợp: " + ", ".join(labels))

    improvements = career.get("improvements")
    if isinstance(improvements, list) and improvements:
        subjects = [
            str(item.get("subject"))
            for item in improvements[:2]
            if isinstance(item, dict) and item.get("subject")
        ]
        if subjects:
            reasons.append("Môn nên củng cố: " + ", ".join(subjects))

    unstudied = career.get("unstudied_core")
    if isinstance(unstudied, list) and unstudied:
        subjects = [
            str(item.get("subject"))
            for item in unstudied[:2]
            if isinstance(item, dict) and item.get("subject")
        ]
        if subjects:
            reasons.append("Môn trọng tâm chưa học: " + ", ".join(subjects))

    if career.get("is_group_fill"):
        reasons.append(
            f"Được bổ sung từ nhóm {career.get('career_group') or 'nghề khác'} "
            "vì nhóm ưu tiên chưa đủ ba gợi ý"
        )
    if not reasons:
        reasons.append("Được xếp hạng theo mức khớp giữa hồ sơ môn học và trọng tâm nghề")
    reasons.append("Điểm khớp tham khảo, không dự đoán khả năng thành công ngoài thực tế")
    return " · ".join(reasons)


def market_source_status(reviewed_at: object, today: date | None = None) -> tuple[str, bool]:
    """Describe the review age without implying that a source claim is still current."""
    value = str(reviewed_at or "").strip()
    if not value:
        return "Chưa có ngày rà soát nguồn", False
    try:
        reviewed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return "Không xác định được ngày rà soát nguồn", False

    today = today or date.today()
    age_days = (today - reviewed).days
    if age_days < 0:
        return "Ngày rà soát nguồn không hợp lệ", False
    if age_days > 365:
        return f"Nguồn có thể đã cũ · rà soát gần nhất {value}", False
    return f"Rà soát {value} · nguồn còn trong thời hạn kiểm tra", True


def _market_source_reference_note(source: dict) -> str:
    """Identify figures sourced from a comparator rather than the exact career."""
    if not source.get("loai_tham_chieu"):
        return ""
    comparator = str(
        source.get("nghe_tham_chieu") or source.get("doi_tuong_tham_chieu") or ""
    ).strip()
    if not comparator:
        return ""
    return f" <span>(tham khảo, không riêng chức danh này: {e(comparator)})</span>"


def career_card(idx: int, c: dict) -> str:
    """Thẻ nghề nghiệp định dạng cao cấp hiển thị đầy đủ thông số tuyển dụng."""
    pct = float(c.get("match_percentage", 0) or 0)
    is_top = (idx == 0)
    badge_cls = "rank gold" if is_top else "rank"
    badge_label = "Gợi ý nổi bật" if is_top else "Một lựa chọn khác"
    region = c.get("region") or c.get("khu_vuc") or "Việt Nam"
    source = c.get("source") or c.get("nguon_du_lieu") or "TopCV & ITviec"
    updated = c.get("updated_at") or c.get("thoi_diem_cap_nhat") or "2025-2026"
    salary_text = _salary_summary(
        c.get("salary_data"),
        _friendly_market_value(
            c.get("salary") or c.get("muc_luong"),
            "Chưa có số liệu lương đủ tin cậy cho chức danh này",
            "Chưa có số liệu lương đủ tin cậy cho chức danh này",
        ),
    )
    trend_text = _friendly_market_value(
        c.get("trend") or c.get("xu_huong_thi_truong"),
        "Chưa có thông tin xu hướng đủ tin cậy cho chức danh này",
        "Chưa có thông tin xu hướng đủ tin cậy cho chức danh này",
    )
    source_labels = {
        "muc_luong": "lương",
        "xu_huong_thi_truong": "xu hướng",
    }
    source_links = []
    sources = c.get("sources") or []
    if isinstance(sources, list):
        for item in sources:
            if not isinstance(item, dict):
                continue
            source_url = str(item.get("url") or "").strip()
            if not source_url.startswith("https://"):
                continue
            scope_items = item.get("pham_vi", [])
            if not isinstance(scope_items, list):
                scope_items = []
            scope = ", ".join(
                source_labels[key]
                for key in scope_items
                if isinstance(key, str)
                if key in source_labels
            )
            source_title = e(item.get("ten") or "Nguồn tham khảo")
            source_links.append(
                f"<a href='{e(source_url)}' target='_blank' rel='noopener noreferrer'>"
                f"{source_title}</a>{f' ({e(scope)})' if scope else ''}"
                f"{_market_source_reference_note(item)}"
            )
    if not source_links:
        source_url = str(c.get("source_url") or c.get("nguon_url") or "").strip()
        if source_url.startswith("https://"):
            source_links.append(
                f"<a href='{e(source_url)}' target='_blank' rel='noopener noreferrer'>"
                f"{e(source)}</a> ({e(updated)})"
            )
    source_note = (
        "Nguồn: " + " · ".join(source_links)
        if source_links else
        "Chưa có nguồn tham khảo phù hợp cho thông tin thị trường của nghề này."
    )
    reviewed_at = c.get("source_reviewed_at") or c.get("ngay_kiem_tra")
    review_status, review_is_recent = market_source_status(reviewed_at)
    review_color = "#047857" if review_is_recent else "#B45309"
    review_note = (
        f"<br><span style='color:{review_color};font-weight:600'>"
        f"{e(review_status)}</span>"
    )

    return (
        f"<div class='career{' first' if is_top else ''}'>"
        f"  <div style='display:flex;justify-content:space-between;align-items:center'>"
        f"    <span class='{badge_cls}'>{badge_label}</span>"
        f"    <span style='font-size:0.8rem;color:#64748B;font-weight:650'>{e(c.get('career_group', ''))}</span>"
        f"  </div>"
        f"  <h3>{e(c.get('career_name'))}</h3>"
        f"  <p>{e(c.get('description', ''))}</p>"
        f"  <div class='meter'>"
        f"    <span style='font-size:0.8rem;color:#64748B'>Mức độ phù hợp tham khảo</span>"
        f"    <div class='tr'><div class='fl' style='width:{max(0, min(100, pct)):.1f}%'></div></div>"
        f"    <b>{pct:.1f}%</b>"
        f"  </div>"
        f"  <div class='kv stack'><span>Vì sao nghề này được gợi ý?</span><span>{e(_career_reason(c))}</span></div>"
        f"  <div class='kv'><span>Mức lương tham khảo</span><span style='color:#059669;font-weight:700'>{e(salary_text)}</span></div>"
        f"  <div class='kv stack'><span>Xu hướng thị trường</span><span>{e(trend_text)}</span></div>"
        f"  <div class='kv'><span>Khu vực</span><span style='font-size:0.78rem;color:#64748B'>{e(region)}</span></div>"
        f"  <div class='kv stack'><span style='font-size:0.76rem;color:#64748B'>{source_note}{review_note}</span></div>"
        f"</div>"
    )


def career_grid(careers: list) -> str:
    """Lưới 3 thẻ nghề nghiệp có chiều cao đồng đều tự động."""
    return "<div class='cgrid'>" + "".join(career_card(i, c) for i, c in enumerate(careers[:3])) + "</div>"


def career_explorer_card(career: dict) -> str:
    """Thẻ khám phá nghề với mô tả và dữ liệu thị trường hiện có."""
    sources = career.get("nguon_tham_khao") or []
    source_links = []
    if isinstance(sources, list):
        for source in sources:
            if not isinstance(source, dict):
                continue
            url = str(source.get("url") or "").strip()
            if url.startswith("https://"):
                source_links.append(
                    f"<a href='{e(url)}' target='_blank' rel='noopener noreferrer'>"
                    f"{e(source.get('ten') or 'Nguồn tham khảo')}</a>"
                    f"<span class='source-scope'>{_market_source_reference_note(source)}</span>"
                )
    source_text = "".join(source_links) or e(
        career.get("nguon_du_lieu") or "Chưa có nguồn tham khảo phù hợp."
    )
    review_status, review_is_recent = market_source_status(career.get("ngay_kiem_tra"))
    review_color = "#047857" if review_is_recent else "#B45309"
    salary = _salary_summary(
        career.get("salary_data"),
        _friendly_market_value(
            career.get("muc_luong"),
            "Chưa có số liệu lương đủ tin cậy cho chức danh này",
            "Chưa có số liệu lương đủ tin cậy cho chức danh này",
        ),
    )
    trend = _friendly_market_value(
        career.get("xu_huong_thi_truong"),
        "Chưa có thông tin xu hướng đủ tin cậy cho chức danh này",
        "Chưa có thông tin xu hướng đủ tin cậy cho chức danh này",
    )
    return (
        "<article class='career-explorer-card'>"
        f"<span class='rank'>{e(career.get('career_group', ''))}</span>"
        f"<h3>{e(career.get('career_name', 'Nghề nghiệp'))}</h3>"
        f"<p>{e(career.get('mo_ta') or 'Chưa có mô tả cho nghề nghiệp này.')}</p>"
        f"<div class='kv stack'><span>Mức lương tham khảo</span><span>{e(salary)}</span></div>"
        f"<div class='kv stack'><span>Xu hướng thị trường</span><span>{e(trend)}</span></div>"
        f"<div class='kv stack'><span>Khu vực</span><span>{e(career.get('khu_vuc') or 'Chưa có thông tin')}</span></div>"
        f"<div class='kv stack'><span>Nguồn tham khảo</span><div class='career-source-links'>{source_text}</div></div>"
        f"<p style='margin:0.75rem 0 0;color:{review_color};font-size:0.78rem;font-weight:600'>"
        f"{e(review_status)}</p>"
        "</article>"
    )


def career_explorer_grid(careers: list) -> str:
    """Lưới hiển thị toàn bộ nghề thuộc nhóm được chọn."""
    cards = "".join(career_explorer_card(career) for career in careers)
    return f"<div class='career-explorer-grid'>{cards}</div>"


def tags(items, kind: str, empty: str, title: str) -> str:
    """Danh sách thế mạnh hoặc kỹ năng cần trau dồi dạng badge với tiêu đề phong cách Góc Khám Phá."""
    prefix = "✓ " if kind == "good" else ""
    body = "".join(f"<span class='tag {kind}'>{prefix}{e(i)}</span>" for i in items) or f"<div class='note'>{e(empty)}</div>"
    return (
        f"<div class='card'>"
        f"  <div class='card-title-bar'><span class='bar-accent'></span><h4>{e(title)}</h4></div>"
        f"  <div style='margin-top:0.4rem'>{body}</div>"
        f"</div>"
    )


def kpi_card(title: str, val: str, sub: str = "", icon_type: str = "bar", *args, **kwargs) -> str:
    """Card thống kê KPI cho bảng điều khiển Admin theo phong cách Góc Khám Phá."""
    icons = {
        "message": "<svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='#4F46E5' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z'></path></svg>",
        "mail": "<svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='#0EA5E9' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><rect width='20' height='16' x='2' y='4' rx='2'></rect><path d='m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7'></path></svg>",
        "smile": "<svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='#10B981' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='10'></circle><path d='M8 14s1.5 2 4 2 4-2 4-2'></path><line x1='9' y1='9' x2='9.01' y2='9'></line><line x1='15' y1='15.01' y2='9'></line></svg>",
        "clock": "<svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='#F59E0B' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='10'></circle><polyline points='12 6 12 12 16 14'></polyline></svg>",
        "bar": "<svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='#6366F1' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><line x1='18' y1='20' x2='18' y2='10'></line><line x1='12' y1='20' x2='12' y2='4'></line><line x1='6' y1='20' x2='6' y2='14'></line></svg>",
    }
    icon_svg = icons.get(icon_type, icons["bar"])
    sub_html = f"<div class='kpi-sub'>{e(sub)}</div>" if sub else ""
    return (
        f"<div class='kpi-card'>"
        f"  <div class='kpi-top'>"
        f"    <div class='kpi-title'>{e(title)}</div>"
        f"    <div class='kpi-icon-badge'>{icon_svg}</div>"
        f"  </div>"
        f"  <div class='kpi-val'>{e(val)}</div>"
        f"  {sub_html}"
        f"</div>"
    )


def admin_group_distribution(group_counts: dict) -> str:
    """Biểu đồ thanh ngang phân bổ nhóm ngành tư vấn theo phong cách Góc Khám Phá."""
    if not group_counts:
        return "<div class='note'>Chưa có dữ liệu lịch sử tư vấn.</div>"
    total = sum(group_counts.values()) or 1
    items = sorted(group_counts.items(), key=lambda kv: -kv[1])
    rows = []
    for g, cnt in items:
        pct = (cnt / total) * 100
        rows.append(
            f"<div class='admin-dist-row'>"
            f"  <div class='admin-dist-label'>{e(g)}</div>"
            f"  <div class='admin-dist-bar-wrap'>"
            f"    <div class='admin-dist-bar-fill' style='width:{max(pct, 2):.1f}%'></div>"
            f"  </div>"
            f"  <div class='admin-dist-count'>{cnt}</div>"
            f"</div>"
        )
    return (
        f"<div class='admin-dist-container'>{''.join(rows)}</div>"
        f"<div class='admin-dist-caption'>Tổng cộng {total} lượt tư vấn được ghi nhận.</div>"
    )
