# -*- coding: utf-8 -*-
"""
web/ui_kit.py — Bộ thành phần giao diện hiện đại & cao cấp cho web/app.py (CSS + hàm dựng HTML/SVG).
Không phụ thuộc thêm thư viện ngoài: biểu đồ radar, vòng tin cậy, thanh xác suất đều là HTML/SVG thuần.
Mọi chuỗi động đều đi qua html.escape() trước khi chèn vào HTML để phòng chống XSS.
"""
import html
import math
from datetime import date, datetime

PALETTE = ["#4F46E5", "#0EA5E9", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6", "#64748B"]
AXIS_LABEL = {
    "sec": "ATBM", "se": "CNPM", "linux": "Linux", "db": "CSDL", "graphics": "Đồ họa", "network": "Mạng",
    "analysis": "PTTK", "image": "Xử lý ảnh", "java": "Java", "csharp": "C#/.NET", "web": "Web", "ai": "AI",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

:root {
    --ink: #0F172A;
    --ink-light: #334155;
    --muted: #64748B;
    --line: #E2E8F0;
    --line-light: #F1F5F9;
    --card: #FFFFFF;
    --bg: #F8FAFC;
    --brand: #4F46E5;
    --brand-dark: #3730A3;
    --brand-light: #EEF2FF;
    --brand2: #0EA5E9;
    --brand2-light: #E0F2FE;
    --ok: #059669;
    --ok-bg: #ECFDF5;
    --warn: #D97706;
    --warn-bg: #FFFBEB;
    --danger: #DC2626;
    --danger-bg: #FEF2F2;
    --radius-sm: 10px;
    --radius-md: 16px;
    --radius-lg: 22px;
}

html, body, [class*="css"], .stApp, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', "Segoe UI", Roboto, sans-serif !important;
    color: var(--ink);
}

.stApp {
    background: radial-gradient(1300px 600px at 85% -10%, #E0E7FF 0%, transparent 60%),
                radial-gradient(1000px 500px at 15% 10%, #E0F2FE 0%, transparent 50%),
                var(--bg);
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
    top: 0.4rem !important;
    left: 0.5rem !important;
    width: 2.5rem !important;
    min-width: 2.5rem !important;
    height: 2.5rem !important;
    padding: 0 !important;
    border: 1px solid var(--line) !important;
    border-radius: 0.6rem !important;
    background: #fff !important;
    color: var(--ink-light) !important;
    box-shadow: none !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 1003 !important;
    pointer-events: auto !important;
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
    width: 2.25rem !important;
    min-width: 2.25rem !important;
    height: 2.25rem !important;
    padding: 0 !important;
    border: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
    color: var(--ink-light) !important;
    font-size: 0 !important;
}

[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"] {
    display: none !important;
}

[data-testid="stSidebarCollapseButton"] button::after {
    content: "☰";
    position: absolute;
    top: 50%;
    left: 50%;
    font-size: 1.2rem;
    line-height: 1;
    transform: translate(-50%, -50%);
}

.block-container {
    padding-top: 3rem;
    padding-bottom: 3.5rem;
    max-width: 1200px;
}

h1, h2, h3, h4 {
    letter-spacing: -0.02em;
    color: var(--ink);
    font-weight: 700;
}

[data-testid="stHeaderLink"],
a[aria-label="Link to heading"],
.stMarkdownContainer h1 a,
.stMarkdownContainer h2 a,
.stMarkdownContainer h3 a,
.stMarkdownContainer h4 a {
    display: none !important;
}

/* ================== Hero Banner ================== */
.hero {
    position: relative;
    overflow: hidden;
    border-radius: var(--radius-lg);
    padding: 2.5rem 2.7rem;
    color: #fff;
    background: linear-gradient(118deg, #111827 0%, #24205D 42%, #4338CA 76%, #0E7490 120%);
    box-shadow: 0 24px 50px -24px rgba(30, 27, 75, 0.72);
    margin-bottom: 1.8rem;
}
.hero::after {
    content: "";
    position: absolute;
    right: -50px;
    top: -70px;
    width: 280px;
    height: 280px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.18) 0%, rgba(255, 255, 255, 0) 70%);
}
.hero h1 {
    margin: 0 0 0.5rem;
    font-size: 2.15rem;
    font-weight: 800;
    color: #fff;
    line-height: 1.22;
}
.hero p {
    margin: 0;
    color: rgba(255, 255, 255, 0.84);
    font-size: 1.02rem;
    max-width: 800px;
    line-height: 1.6;
}
.pills {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    margin-top: 1.25rem;
}
.pill {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    padding: 0.42rem 0.95rem;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 600;
    backdrop-filter: blur(6px);
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
}

/* ================== Section & Cards ================== */
.sec-title {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-weight: 700;
    font-size: 1.18rem;
    margin: 0.2rem 0 0.65rem;
    color: var(--ink);
}
.step {
    display: inline-grid;
    place-items: center;
    width: 32px;
    height: 32px;
    border-radius: 10px;
    background: linear-gradient(135deg, #4F46E5, #6366F1);
    color: #fff;
    font-size: 0.9rem;
    font-weight: 800;
    box-shadow: 0 4px 10px -2px rgba(79, 70, 229, 0.4);
    flex-shrink: 0;
}
.sec-desc {
    color: var(--muted);
    font-size: 0.88rem;
    margin-top: -0.3rem;
    margin-bottom: 0.9rem;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid rgba(203, 213, 225, 0.82) !important;
    border-radius: 20px !important;
    box-shadow: 0 16px 38px -28px rgba(30, 41, 59, 0.42) !important;
    padding: 0.65rem;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: rgba(129, 140, 248, 0.55) !important;
    box-shadow: 0 18px 42px -28px rgba(79, 70, 229, 0.32) !important;
}

.card {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    padding: 1.3rem 1.4rem;
    box-shadow: 0 8px 24px -16px rgba(15, 23, 42, 0.12);
    height: 100%;
}
.card h4 {
    margin: 0 0 0.85rem;
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--ink);
}

/* ================== Subject Group Badges ================== */
.subj-group-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.35rem 0 0.65rem;
    border-bottom: 1px solid #E2E8F0;
    font-size: 0.9rem;
    font-weight: 750;
    margin: 0.3rem 0 0.75rem;
}
.subj-group-header.sys { color: #4338CA; border-bottom-color: #C7D2FE; }
.subj-group-header.data { color: #15803D; border-bottom-color: #BBF7D0; }
.subj-group-header.dev { color: #0369A1; border-bottom-color: #BAE6FD; }
.subj-group-header.ai { color: #7E22CE; border-bottom-color: #E9D5FF; }

/* ================== Buttons & Inputs ================== */
[data-testid="stTextInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label,
[data-testid="stNumberInput"] label {
    color: #334155 !important;
    font-size: 0.88rem !important;
    font-weight: 650 !important;
    letter-spacing: -0.01em;
}
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    min-height: 46px;
    border: 1px solid #E2E8F0 !important;
    border-radius: 13px !important;
    background: linear-gradient(180deg, #FFFFFF 0%, #FBFCFF 100%) !important;
    box-shadow: 0 3px 10px -8px rgba(15, 23, 42, 0.28);
    transition: border-color 0.18s ease, box-shadow 0.18s ease;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: #818CF8 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.13) !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
    min-height: 46px;
    border: 1px solid #E2E8F0 !important;
    border-radius: 13px !important;
    background: linear-gradient(180deg, #FFFFFF 0%, #FBFCFF 100%) !important;
    box-shadow: 0 3px 10px -8px rgba(15, 23, 42, 0.28);
}
[data-testid="stSelectbox"] [data-baseweb="select"]:focus-within > div,
[data-testid="stMultiSelect"] [data-baseweb="select"]:focus-within > div {
    border-color: #818CF8 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.13) !important;
}
.st-key-feedback-panel [data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #DCE3F0 !important;
    border-radius: 22px !important;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(247, 249, 255, 0.96)) !important;
    box-shadow: 0 18px 42px -32px rgba(30, 41, 59, 0.38);
}
.feedback-heading {
    margin: 0 0 1.25rem;
}
.feedback-eyebrow {
    margin: 0 0 0.45rem;
    color: #6366F1;
    font-size: 0.69rem;
    font-weight: 750;
    letter-spacing: 0.12em;
}
.feedback-heading h3 {
    margin: 0;
    color: #172033;
    font-size: 1.24rem;
    font-weight: 700;
    letter-spacing: -0.035em;
}
.feedback-heading > p:last-child {
    margin: 0.42rem 0 0;
    color: #64748B;
    font-size: 0.87rem;
    line-height: 1.55;
}
.st-key-feedback-panel .stButton > button {
    min-height: 46px;
    border: 1px solid #DCE3F0 !important;
    border-radius: 13px !important;
    background: rgba(255, 255, 255, 0.88) !important;
    color: #334155 !important;
    font-size: 0.88rem !important;
    font-weight: 650 !important;
    transition: border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease !important;
}
.st-key-feedback-panel .stButton > button:hover {
    border-color: #A5B4FC !important;
    background: #F5F6FF !important;
    box-shadow: 0 8px 18px -14px rgba(79, 70, 229, 0.55) !important;
    transform: translateY(-1px);
}
.st-key-feedback-panel [data-testid="stMarkdownContainer"] p,
.st-key-feedback-panel [data-testid="stTextInput"] label {
    color: #334155 !important;
    font-size: 0.82rem !important;
    font-weight: 650 !important;
}
div[class*="st-key-fb_rating_star_"] button {
    all: unset !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: auto !important;
    min-width: 42px !important;
    min-height: 48px !important;
    padding: 0 0.1rem !important;
    border: 0 !important;
    outline: 0 !important;
    border-radius: 0 !important;
    background: transparent !important;
    color: #BFC7D5 !important;
    font-size: 2.35rem !important;
    font-weight: 700 !important;
    font-family: inherit !important;
    line-height: 1 !important;
    cursor: pointer !important;
    box-shadow: none !important;
}
div[class*="st-key-fb_rating_star_"] button[kind="primary"] {
    color: #D97706 !important;
    -webkit-text-fill-color: #D97706 !important;
}
div[class*="st-key-fb_rating_star_"] button[kind="primary"] *,
div[class*="st-key-fb_rating_star_"] button[kind="primary"] p {
    color: #D97706 !important;
    -webkit-text-fill-color: #D97706 !important;
}
div[class*="st-key-fb_rating_star_"] button[kind="secondary"] {
    color: #BFC7D5 !important;
    -webkit-text-fill-color: #BFC7D5 !important;
}
div[class*="st-key-fb_rating_star_"] button[kind="secondary"] *,
div[class*="st-key-fb_rating_star_"] button[kind="secondary"] p {
    color: #BFC7D5 !important;
    -webkit-text-fill-color: #BFC7D5 !important;
}
div[class*="st-key-fb_rating_star_"] button:hover {
    all: unset !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: auto !important;
    min-width: 42px !important;
    min-height: 48px !important;
    padding: 0 0.1rem !important;
    border: none !important;
    background: transparent !important;
    color: #D97706 !important;
    -webkit-text-fill-color: #D97706 !important;
    box-shadow: none !important;
    font-size: 2.35rem !important;
    font-weight: 700 !important;
    font-family: inherit !important;
    line-height: 1 !important;
    cursor: pointer !important;
    transform: scale(1.08);
}
div[class*="st-key-fb_rating_star_"] button:focus:not(:focus-visible) {
    box-shadow: none !important;
}
.profile-editor-aside {
    position: relative;
    isolation: isolate;
    display: flex;
    min-height: 284px;
    height: 100%;
    flex-direction: column;
    overflow: hidden;
    padding: 1.55rem 1.6rem;
    border-radius: 22px;
    color: #fff;
    background:
        radial-gradient(ellipse at 100% 0%, rgba(34, 211, 238, 0.32), transparent 42%),
        radial-gradient(ellipse at 0% 100%, rgba(129, 140, 248, 0.34), transparent 48%),
        linear-gradient(145deg, #10172D 0%, #20245A 55%, #3730A3 100%);
    box-shadow: 0 24px 44px -28px rgba(30, 27, 75, 0.76);
}
.profile-editor-aside::after {
    position: absolute;
    z-index: -1;
    right: -58px;
    bottom: -86px;
    width: 210px;
    height: 210px;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 50%;
    box-shadow: 0 0 0 22px rgba(255, 255, 255, 0.035), 0 0 0 48px rgba(255, 255, 255, 0.025);
    content: "";
}
.profile-editor-kicker,
.profile-form-heading > span {
    color: #A5B4FC;
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.16em;
}
.profile-editor-mark {
    display: grid;
    width: 42px;
    height: 42px;
    margin-top: 1.35rem;
    place-items: center;
    border: 1px solid rgba(255, 255, 255, 0.24);
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
    font-size: 0.88rem;
    font-weight: 800;
    backdrop-filter: blur(8px);
}
.profile-editor-aside h2 {
    margin: 0.8rem 0 0.55rem;
    color: #fff;
    font-size: clamp(1.25rem, 2vw, 1.72rem);
    font-weight: 750;
    line-height: 1.22;
    letter-spacing: -0.045em;
}
.profile-editor-aside p {
    max-width: 300px;
    margin: 0;
    color: rgba(235, 239, 255, 0.76);
    font-size: 0.84rem;
    line-height: 1.65;
}
.profile-editor-foot {
    display: flex;
    align-items: center;
    gap: 0.48rem;
    margin-top: auto;
    padding-top: 1.2rem;
    color: rgba(224, 231, 255, 0.72);
    font-size: 0.62rem;
    font-weight: 750;
    letter-spacing: 0.1em;
}
.profile-editor-foot span {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #34D399;
    box-shadow: 0 0 0 4px rgba(52, 211, 153, 0.13);
}
.profile-form-heading {
    margin: 0.1rem 0 1.2rem;
}
.profile-form-heading p {
    margin: 0.3rem 0 0;
    color: #64748B;
    font-size: 0.84rem;
}
.profile-form-heading > span {
    color: #6366F1;
}
.profile-hint {
    display: flex;
    align-items: flex-start;
    gap: 0.55rem;
    margin-top: 0.9rem;
    padding: 0.7rem 0.8rem;
    border-left: 3px solid #818CF8;
    border-radius: 0 11px 11px 0;
    background: #F3F4FF;
    color: #475569;
    font-size: 0.78rem;
    line-height: 1.5;
}
.profile-hint span {
    color: #6366F1;
    font-weight: 800;
}
[data-testid="stRadio"] [role="radiogroup"] {
    gap: 0.5rem;
}
[data-testid="stRadio"] [role="radiogroup"] label {
    min-height: 40px;
    justify-content: center;
    padding: 0.45rem 0.75rem;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    background: #fff;
    color: #475569;
    transition: border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}
[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {
    border-color: #818CF8;
    background: #EEF2FF;
    box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.12);
    color: #3730A3;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(125deg, #4F46E5 0%, #0EA5E9 100%) !important;
    border: 0 !important;
    border-radius: 14px !important;
    padding: 0.85rem 1.25rem !important;
    font-weight: 700 !important;
    font-size: 1.08rem !important;
    color: #fff !important;
    box-shadow: 0 12px 28px -10px rgba(79, 70, 229, 0.6) !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 16px 32px -8px rgba(79, 70, 229, 0.75) !important;
}
.stButton > button[kind="secondary"] {
    border-radius: 12px !important;
    border: 1px solid var(--line) !important;
    font-weight: 600 !important;
    background: #fff !important;
    transition: all 0.15s ease !important;
}
.stButton > button[kind="secondary"]:hover {
    background: #F8FAFC !important;
    border-color: #CBD5E1 !important;
}

[data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-right: 1px solid var(--line) !important;
}

[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 0.5rem;
    border-bottom: 2px solid #E2E8F0;
    padding: 0 0.2rem;
}
[data-testid="stTabs"] button[data-baseweb="tab"] {
    height: 46px;
    padding: 0 1.2rem;
    border-radius: 12px 12px 0 0;
    color: #64748B;
    font-weight: 600;
    font-size: 0.94rem;
}
[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
    color: #4338CA;
    background: #EEF2FF;
    border-bottom: 2px solid #4F46E5;
}

[data-testid="stFileUploader"] section {
    border: 1.8px dashed #C7D2FE !important;
    border-radius: 16px !important;
    background: linear-gradient(135deg, #F8FAFF 0%, #F5F7FF 100%) !important;
    padding: 1.25rem !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFileUploader"] section:hover {
    border-color: #818CF8 !important;
    background: #EEF2FF !important;
}

[data-testid="stNumberInput"] input {
    border-radius: 10px !important;
    font-weight: 600 !important;
}

/* ================== Result Hero ================== */
.res {
    display: flex;
    gap: 1.6rem;
    align-items: center;
    justify-content: space-between;
    border-radius: var(--radius-lg);
    padding: 1.8rem 2.2rem;
    color: #fff;
    background: linear-gradient(130deg, #0F172A 0%, #1E1B4B 50%, #4338CA 100%);
    box-shadow: 0 24px 48px -20px rgba(30, 27, 75, 0.7);
    margin: 1.2rem 0;
}
.res .k {
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    opacity: 0.75;
    font-weight: 700;
}
.res .v {
    font-size: 2.25rem;
    font-weight: 800;
    line-height: 1.18;
    margin: 0.3rem 0 0.55rem;
    color: #FFFFFF;
}
.res .s {
    opacity: 0.94;
    font-size: 1.05rem;
    line-height: 1.5;
}
.res .model-note,
.res .adjusted-note {
    margin-top: 0.65rem;
    font-size: 0.9rem;
    line-height: 1.5;
}
.res .model-note span,
.res .adjusted-note span {
    color: rgba(255, 255, 255, 0.72);
    font-size: 0.8rem;
}
.chip {
    display: inline-block;
    margin: 0.6rem 0.4rem 0 0;
    padding: 0.3rem 0.8rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
    background: rgba(255, 255, 255, 0.16);
    border: 1px solid rgba(255, 255, 255, 0.26);
}
.chip.warn {
    background: #FEF3C7;
    color: #92400E;
    border-color: #FCD34D;
}
.ring {
    --p: 0;
    flex: 0 0 auto;
    width: 136px;
    height: 136px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    background: conic-gradient(#10B981 calc(var(--p) * 1%), rgba(255, 255, 255, 0.16) 0);
    box-shadow: 0 8px 24px -6px rgba(16, 185, 129, 0.4);
}
.ring > div {
    width: 108px;
    height: 108px;
    border-radius: 50%;
    background: #0F172A;
    display: grid;
    place-items: center;
    text-align: center;
}
.ring b {
    font-size: 1.45rem;
    font-weight: 800;
    display: block;
    line-height: 1;
    color: #FFFFFF;
}
.ring small {
    font-size: 0.66rem;
    opacity: 0.75;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #94A3B8;
}

/* ================== Probability Bars ================== */
.bar {
    margin: 0.65rem 0;
}
.bar .t {
    display: flex;
    justify-content: space-between;
    font-size: 0.9rem;
    font-weight: 600;
    margin-bottom: 0.3rem;
}
.bar .tr {
    height: 11px;
    border-radius: 999px;
    background: #EEF2F7;
    overflow: hidden;
}
.bar .fl {
    height: 100%;
    border-radius: 999px;
    transition: width 0.4s ease;
}

/* ================== Career Cards ================== */
.cgrid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 1.15rem;
    align-items: stretch;
}
.career {
    position: relative;
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    padding: 1.3rem;
    box-shadow: 0 8px 24px -16px rgba(15, 23, 42, 0.12);
    transition: transform 0.2s, box-shadow 0.2s;
    display: flex;
    flex-direction: column;
}
.career:hover {
    transform: translateY(-3px);
    box-shadow: 0 18px 36px -18px rgba(79, 70, 229, 0.4);
}
.career.first {
    border: 1.8px solid #818CF8;
    background: linear-gradient(180deg, #FFFFFF 0%, #F5F3FF 100%);
}
@media(min-width: 900px) {
    .cgrid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
        grid-template-rows: repeat(8, auto);
        column-gap: 1.15rem;
        row-gap: 0;
    }
    .career {
        grid-row: span 8;
        display: grid;
        grid-template-rows: subgrid;
    }
}
.rank {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.8rem;
    font-weight: 700;
    color: #4338CA;
    background: #EEF2FF;
    padding: 0.28rem 0.75rem;
    border-radius: 999px;
    width: fit-content;
}
.rank.gold {
    background: #FEF3C7;
    color: #92400E;
    border: 1px solid #FDE68A;
}
.career h3 {
    font-size: 1.12rem;
    font-weight: 700;
    margin: 0.75rem 0 0.45rem;
    line-height: 1.32;
    color: var(--ink);
}
.career p {
    font-size: 0.88rem;
    color: #475569;
    line-height: 1.52;
    min-height: 64px;
    margin: 0 0 0.85rem;
    flex-grow: 1;
}
.meter {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    margin-bottom: 0.85rem;
}
.meter .tr {
    flex: 1;
    height: 9px;
    background: #EEF2F7;
    border-radius: 999px;
    overflow: hidden;
}
.meter .fl {
    height: 100%;
    background: linear-gradient(90deg, #4F46E5 0%, #0EA5E9 100%);
    border-radius: 999px;
}
.meter b {
    font-size: 0.92rem;
    color: #4338CA;
    font-weight: 700;
}
.kv {
    display: flex;
    justify-content: space-between;
    gap: 0.6rem;
    font-size: 0.84rem;
    padding: 0.42rem 0;
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
    gap: 0.2rem;
}
.kv.stack span:first-child {
    white-space: normal;
    overflow-wrap: anywhere;
}
.kv.stack span:last-child {
    text-align: left;
    font-weight: 500;
    color: #334155;
    line-height: 1.45;
    overflow-wrap: anywhere;
}
.kv.stack a {
    overflow-wrap: anywhere;
}

/* ================== AI Advisor Explanation ================== */
.explain {
    border-radius: var(--radius-md);
    padding: 1.5rem 1.65rem;
    background: linear-gradient(135deg, #EEF2FF 0%, #F0F9FF 100%);
    border: 1px solid #C7D2FE;
    position: relative;
    box-shadow: 0 8px 24px -16px rgba(79, 70, 229, 0.15);
}
.explain .advisor-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.85rem;
}
.explain .advisor-avatar {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: linear-gradient(135deg, #4F46E5, #0EA5E9);
    display: grid;
    place-items: center;
    color: #fff;
    font-size: 1.1rem;
}
.explain .b {
    display: inline-block;
    font-size: 0.8rem;
    font-weight: 700;
    color: #3730A3;
    background: #fff;
    border: 1px solid #C7D2FE;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
}
.explain .x {
    font-size: 1.04rem;
    line-height: 1.72;
    color: #1E293B;
}
.explain .n {
    margin-top: 0.75rem;
    font-size: 0.82rem;
    color: var(--muted);
}
.tag {
    display: inline-block;
    margin: 0.25rem 0.35rem 0.25rem 0;
    padding: 0.38rem 0.85rem;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 600;
}
.tag.good { background: #D1FAE5; color: #065F46; }
.tag.todo { background: #FEF3C7; color: #92400E; }
.note { font-size: 0.82rem; color: var(--muted); margin: 0.65rem 0 0; }

/* ================== Admin Dashboard Specific ================== */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 1rem;
    margin-bottom: 1.5rem;
}
.kpi-card {
    background: #fff;
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    padding: 1.25rem 1.4rem;
    box-shadow: 0 4px 14px -6px rgba(15, 23, 42, 0.08);
}
.kpi-title {
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted);
    font-weight: 600;
    margin-bottom: 0.4rem;
}
.kpi-val {
    font-size: 1.85rem;
    font-weight: 800;
    color: var(--ink);
    line-height: 1.2;
}
.kpi-sub {
    font-size: 0.8rem;
    color: var(--muted);
    margin-top: 0.3rem;
}
.st-key-admin-login-card {
    box-sizing: border-box;
    width: min(560px, 100%);
    margin: 2rem auto;
    padding: 2rem;
    border: 1px solid var(--line) !important;
    border-radius: var(--radius-lg) !important;
    background: rgba(255, 255, 255, 0.92) !important;
    box-shadow: 0 20px 45px -18px rgba(15, 23, 42, 0.18);
}
.st-key-admin-login-card h2 {
    margin: 0 0 0.35rem;
    color: var(--ink);
    text-align: center;
}
.st-key-admin-login-card > div > [data-testid="stMarkdownContainer"] p {
    text-align: center;
    color: var(--muted);
}
.st-key-admin-login-card [data-testid="stForm"] {
    padding: 0;
    border: 0;
    background: transparent;
}
.st-key-admin-login-card button[aria-label="Show password"],
.st-key-admin-login-card button[aria-label="Hide password"] {
    display: none !important;
}
.career-explorer-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1rem;
    align-items: stretch;
    margin-top: 1.25rem;
}
.career-explorer-card {
    min-width: 0;
    padding: 1.25rem;
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    background: #fff;
    box-shadow: 0 8px 20px -16px rgba(15, 23, 42, 0.25);
}
.career-explorer-card h3 {
    margin: 0.75rem 0 0.45rem;
    font-size: 1.08rem;
}
.career-explorer-card p {
    color: #475569;
    font-size: 0.88rem;
    line-height: 1.6;
}
@media(max-width: 768px) {
    .res { flex-direction: column; align-items: flex-start; }
    .hero h1 { font-size: 1.6rem; }
    .profile-editor-aside { min-height: 235px; }
    .st-key-admin-login-card { padding: 1.25rem; }
    [data-testid="stRadio"] [role="radiogroup"] { flex-wrap: wrap; }
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
    """Tiêu đề nhóm môn tối giản, không dùng biểu tượng trang trí."""
    return (
        f"<div class='subj-group-header {kind}'>"
        f"  <span>{e(name)}</span>"
        f"  <span style='font-size:0.73rem;font-weight:500;color:#64748B;text-align:right'>{e(desc)}</span>"
        f"</div>"
    )


def status_card(ok: bool, version: str, api_url: str) -> str:
    """Thẻ trạng thái hệ thống dành cho quản trị viên."""
    txt = "Hệ thống đang hoạt động" if ok else "Không kết nối được hệ thống"
    return (
        f"<div style='font-weight:700;margin-bottom:.6rem'>"
        f"  {txt}"
        f"</div>"
        f"<div class='kv'><span>Phiên bản hệ thống</span><span>v{e(version)}</span></div>"
        f"<div class='kv'><span>Địa chỉ dịch vụ</span><span style='font-size:.74rem;color:#64748B'>{e(api_url)}</span></div>"
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
    """Tách gợi ý theo điểm môn học khỏi gợi ý đã cân nhắc sở thích."""
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
        f"</div>"
    )


def prob_bars(probs: dict) -> str:
    """Thanh thể hiện những nhóm ngành hệ thống gợi ý theo điểm môn học."""
    items = sorted(probs.items(), key=lambda kv: -kv[1])
    out = ["<div class='card'><h4>Các nhóm ngành được gợi ý theo điểm môn học</h4>"]
    for i, (g, p) in enumerate(items):
        color = PALETTE[i % len(PALETTE)]
        out.append(
            f"<div class='bar'>"
            f"  <div class='t'><span>{e(g)}</span><span style='color:{color};font-weight:700'>{p:.1f}%</span></div>"
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
        return "<div class='card'><h4>Hồ sơ năng lực</h4><p>Chưa có dữ liệu điểm.</p></div>"

    def pt(i, r):
        a = -math.pi / 2 + 2 * math.pi * i / n
        return cx + r * math.cos(a), cy + r * math.sin(a)

    g = []
    # Các vòng đồng tâm 2.5, 5.0, 7.5, 10.0
    for lv in (2.5, 5, 7.5, 10):
        g.append("<polygon points='" + " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, R * lv / 10) for i in range(n)))
                 + "' fill='none' stroke='#E2E8F0' stroke-width='1.2'/>")
    # Các trục toạ độ
    for i in range(n):
        x, y = pt(i, R)
        g.append(f"<line x1='{cx}' y1='{cy}' x2='{x:.1f}' y2='{y:.1f}' stroke='#E2E8F0' stroke-width='1.2'/>")
    
    # Đa giác điểm số
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, R * max(0, min(10, float(scores[k]))) / 10) for i, k in enumerate(keys)))
    g.append(f"<polygon points='{poly}' fill='rgba(79, 70, 229, 0.22)' stroke='#4F46E5' stroke-width='2.6'/>")

    for i, k in enumerate(keys):
        x, y = pt(i, R * max(0, min(10, float(scores[k]))) / 10)
        g.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='4.5' fill='#4F46E5' stroke='#fff' stroke-width='1.5'/>")
        lx, ly = pt(i, R + 26)
        anc = "middle" if abs(lx - cx) < 12 else ("start" if lx > cx else "end")
        score_val = float(scores[k])
        g.append(f"<text x='{lx:.1f}' y='{ly:.1f}' text-anchor='{anc}' dominant-baseline='middle' font-size='11.5' font-weight='600' fill='#334155'>"
                 f"{e(AXIS_LABEL[k])} <tspan fill='#4F46E5' font-weight='700'>{score_val:.1f}</tspan></text>")

    return (
        f"<div class='card'>"
        f"  <h4>Hồ sơ năng lực 12 học phần</h4>"
        f"  <svg viewBox='-40 0 500 380' width='100%' role='img' aria-label='Biểu đồ radar năng lực môn học'>{''.join(g)}</svg>"
        f"</div>"
    )


def explain_card(text: str, note: str, is_ai: bool, disclaimer: str) -> str:
    """Thẻ lời khuyên cá nhân hóa, không phô bày công nghệ phía sau."""
    badge = "Góc nhìn dành riêng cho bạn" if is_ai else "Gợi ý tổng hợp dành riêng cho bạn"
    avatar = ""
    return (
        f"<div class='explain'>"
        f"  <div class='advisor-header'>"
        f"    <div class='advisor-avatar'>{avatar}</div>"
        f"    <div>"
        f"      <span class='b'>{badge}</span>"
        f"      <div style='font-size:0.8rem;color:#4338CA;font-weight:600;margin-top:2px'>Tư vấn cá nhân hóa định hướng sự nghiệp</div>"
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
    salary_text = _friendly_market_value(
        c.get("salary") or c.get("muc_luong"),
        "Chưa có số liệu lương đủ tin cậy cho chức danh này",
        "Chưa có số liệu lương đủ tin cậy cho chức danh này",
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
        f"    <span style='font-size:0.8rem;color:#64748B;font-weight:600'>{e(c.get('career_group', ''))}</span>"
        f"  </div>"
        f"  <h3>{e(c.get('career_name'))}</h3>"
        f"  <p>{e(c.get('description', ''))}</p>"
        f"  <div class='meter'>"
        f"    <span style='font-size:0.78rem;color:#64748B'>Mức độ phù hợp tham khảo</span>"
        f"    <div class='tr'><div class='fl' style='width:{max(0, min(100, pct)):.1f}%'></div></div>"
        f"    <b>{pct:.1f}%</b>"
        f"  </div>"
        f"  <div class='kv'><span>Mức lương tham khảo</span><span style='color:#059669;font-weight:700'>{e(salary_text)}</span></div>"
        f"  <div class='kv stack'><span>Xu hướng thị trường</span><span>{e(trend_text)}</span></div>"
        f"  <div class='kv'><span>Khu vực</span><span style='font-size:0.75rem;color:#64748B'>{e(region)}</span></div>"
        f"  <div class='kv stack'><span style='font-size:0.75rem;color:#64748B'>{source_note}{review_note}</span></div>"
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
                    f"{_market_source_reference_note(source)}"
                )
    source_text = " · ".join(source_links) or e(
        career.get("nguon_du_lieu") or "Chưa có nguồn tham khảo phù hợp."
    )
    review_status, review_is_recent = market_source_status(career.get("ngay_kiem_tra"))
    review_color = "#047857" if review_is_recent else "#B45309"
    salary = _friendly_market_value(
        career.get("muc_luong"),
        "Chưa có số liệu lương đủ tin cậy cho chức danh này",
        "Chưa có số liệu lương đủ tin cậy cho chức danh này",
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
        f"<div class='kv stack'><span>Nguồn tham khảo</span><span>{source_text}</span></div>"
        f"<p style='margin:0.65rem 0 0;color:{review_color};font-size:0.76rem;font-weight:600'>"
        f"{e(review_status)}</p>"
        "</article>"
    )


def career_explorer_grid(careers: list) -> str:
    """Lưới hiển thị toàn bộ nghề thuộc nhóm được chọn."""
    cards = "".join(career_explorer_card(career) for career in careers)
    return f"<div class='career-explorer-grid'>{cards}</div>"


def tags(items, kind: str, empty: str, title: str) -> str:
    """Danh sách thế mạnh hoặc kỹ năng cần trau dồi dạng badge."""
    body = "".join(f"<span class='tag {kind}'>{e(i)}</span>" for i in items) or f"<div class='note'>{e(empty)}</div>"
    return f"<div class='card'><h4>{e(title)}</h4>{body}</div>"


def kpi_card(title: str, val: str, sub: str = "") -> str:
    """Card thống kê KPI cho bảng điều khiển Admin."""
    return (
        f"<div class='kpi-card'>"
        f"  <div class='kpi-title'>{e(title)}</div>"
        f"  <div class='kpi-val'>{e(val)}</div>"
        f"  <div class='kpi-sub'>{e(sub)}</div>"
        f"</div>"
    )
