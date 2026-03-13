import os
import urllib.request
import time, json, re
import hashlib
import requests
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ================= 环境与网络直连配置 =================
for var in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"]:
    os.environ.pop(var, None)
os.environ["no_proxy"] = "*"
os.environ["NO_PROXY"] = "*"
urllib.request.getproxies = lambda: {}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ================= 页面基础配置（必须第一个 st 调用）=================
st.set_page_config(
    page_title="缠论AI解盘终端",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={}
)

# ================= 密钥认证系统 =================
# 在此处配置允许访问的密钥（SHA-256 哈希值）
# 生成方法：python3 -c "import hashlib; print(hashlib.sha256('你的密钥'.encode()).hexdigest())"
# 示例密钥列表（每行一个哈希，对应一个用户）：
VALID_KEY_HASHES = {
    # 格式: "用户备注": "sha256哈希值"
    # 用 gen_key.py 生成新密钥，或运行:
    # python3 -c "import hashlib; print(hashlib.sha256('你的密钥'.encode()).hexdigest())"
    "admin":  "6e2321f039a6693bd0d63a08c3d48ad098f949e19994bbd3b1fef344b75a5d59",  # 密钥: YV3q^A49kJ!$CwLDrJ7OV5VQ
    # 继续添加用户：
    # "张三": "哈希值",
    # "李四": "哈希值",
}

def _hash(key: str) -> str:
    return hashlib.sha256(key.strip().encode()).hexdigest()

def check_auth() -> bool:
    """返回 True 表示已通过验证"""
    return st.session_state.get("authenticated", False)

def login_page():
    """登录页 — 卡片样式全部通过CSS作用在列容器上，form 内含装饰HTML"""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    #MainMenu, footer, header { visibility: hidden !important; }

    html, body,
    [data-testid="stApp"],
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > .main,
    .block-container {
        background: #f1f5f9 !important;
        font-family: 'Inter','PingFang SC','Microsoft YaHei',sans-serif !important;
    }
    /* 垂直居中整个页面 */
    .block-container {
        min-height: 100vh !important;
        padding: 0 !important;
        max-width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    /* 登录卡片：作用在 form 的父容器 stVerticalBlockBorderWrapper */
    div[data-testid="column"]:nth-child(2) > div:first-child {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        padding: 0 !important;
        box-shadow: none !important;
    }
    /* form 本身就是卡片 */
    [data-testid="stForm"] {
        background: #fff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 20px !important;
        padding: 2.5rem 2.5rem 2rem !important;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.07), 0 12px 40px -8px rgba(0,0,0,0.12) !important;
        width: 100% !important;
    }
    /* Logo 区 */
    .lc-logo-row { display:flex; align-items:center; gap:12px; margin-bottom:1.75rem; }
    .lc-logo-box {
        width:40px; height:40px; border-radius:10px; background:#dc2626; flex-shrink:0;
        display:flex; align-items:center; justify-content:center;
        font-size:1.05rem; font-weight:800; color:#fff;
        box-shadow: 0 2px 8px rgba(220,38,38,0.35);
    }
    .lc-logo-title { font-size:0.95rem; font-weight:700; color:#1e293b; line-height:1.3; }
    .lc-logo-sub   { font-size:0.67rem; color:#94a3b8; margin-top:2px; letter-spacing:0.04em; }
    /* 标题 */
    .lc-heading { font-size:1.6rem; font-weight:800; color:#0f172a; margin-bottom:0.3rem; letter-spacing:-0.02em; }
    .lc-desc    { font-size:0.83rem; color:#64748b; margin-bottom:1.5rem; line-height:1.65; }
    .lc-lbl     { font-size:0.72rem; font-weight:600; color:#374151; text-transform:uppercase; letter-spacing:0.07em; margin-bottom:6px; }
    .lc-footer  { text-align:center; font-size:0.7rem; color:#94a3b8; padding-top:1.25rem; margin-top:0.5rem; border-top:1px solid #f1f5f9; }
    /* 输入框 */
    [data-testid="stTextInput"] input {
        background:#f8fafc !important; border:1.5px solid #e2e8f0 !important;
        border-radius:10px !important; font-size:0.9rem !important;
        color:#1e293b !important; padding:0.65rem 1rem !important;
        transition:border-color .2s, box-shadow .2s !important;
        font-family:'Inter',sans-serif !important;
    }
    [data-testid="stTextInput"] input:focus {
        border-color:#dc2626 !important;
        box-shadow:0 0 0 3px rgba(220,38,38,0.1) !important;
        background:#fff !important; outline:none !important;
    }
    [data-testid="stTextInput"] input::placeholder { color:#cbd5e1 !important; }
    [data-testid="stTextInput"] label { display:none !important; }
    /* 提交按钮 */
    [data-testid="stFormSubmitButton"] > button {
        background:#dc2626 !important; border:none !important;
        color:#fff !important; font-weight:600 !important;
        border-radius:10px !important; min-height:2.75rem !important;
        font-size:0.9rem !important; width:100% !important;
        box-shadow:0 2px 10px rgba(220,38,38,0.3) !important;
        transition:all .18s ease !important; letter-spacing:0.01em !important;
        font-family:'Inter',sans-serif !important;
    }
    [data-testid="stFormSubmitButton"] > button:hover {
        background:#b91c1c !important;
        box-shadow:0 4px 16px rgba(220,38,38,0.42) !important;
        transform:translateY(-1px) !important;
    }
    [data-testid="stFormSubmitButton"] > button:active { transform:translateY(0) !important; }
    [data-testid="stAlert"] { border-radius:10px !important; margin-top:0.5rem !important; }
    @media (max-width:500px) {
        div[data-testid="column"]:nth-child(2) > div:first-child { padding:1.75rem 1.25rem 1.5rem !important; border-radius:16px !important; }
        input[type="password"] { font-size:16px !important; }
    }
    </style>
    """, unsafe_allow_html=True)

    # 三列居中：卡片在中间列
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        # 所有内容放在同一个 form 里，卡片样式通过 CSS 作用在列容器上
        with st.form("login_form", clear_on_submit=False, border=False):
            # 装饰性 HTML（Logo / 标题）放在 form 内
            st.markdown("""
            <div class="lc-logo-row">
              <div class="lc-logo-box">缠</div>
              <div>
                <div class="lc-logo-title">缠论 AI 解盘终端</div>
                <div class="lc-logo-sub">陈氏理论 · 量子终端</div>
              </div>
            </div>
            <div class="lc-heading">欢迎回来</div>
            <div class="lc-desc">输入您的专属访问密钥即可继续使用</div>
            <div class="lc-lbl">访问密钥</div>
            """, unsafe_allow_html=True)

            key_input = st.text_input(
                "密钥",
                type="password",
                placeholder="输入收到的密钥",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("进入终端 →", use_container_width=True)
            st.markdown('<div class="lc-footer">由管理员分配 · 请勿转发</div>', unsafe_allow_html=True)

        if submitted:
            if not key_input.strip():
                st.error("请输入密钥")
            elif _hash(key_input) in VALID_KEY_HASHES.values():
                st.session_state["authenticated"] = True
                for name, h in VALID_KEY_HASHES.items():
                    if h == _hash(key_input):
                        st.session_state["username"] = name
                        break
                st.rerun()
            else:
                st.error("密钥无效，请联系管理员")


# ================= 登录拦截 =================
if not check_auth():
    login_page()
    st.stop()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ══ LIGHT THEME VARIABLES (default) ══ */
:root {
    --bg:       #ffffff;
    --bg2:      #f8fafc;
    --bg3:      #f1f5f9;
    --border:   #e2e8f0;
    --border2:  #cbd5e1;
    --text:     #1e293b;
    --text2:    #475569;
    --text3:    #94a3b8;
    --blue:     #dc2626;
    --blue-dim: #b91c1c;
    --red:      #ef4444;
    --green:    #10b981;
    --amber:    #f59e0b;
    --header-bg: rgba(255,255,255,0.94);
    --header-border: #e2e8f0;
    --metric-bg: #f8fafc;
    --ins-row-bg: #f8fafc;
    --sig-card-bg: #f8fafc;
    --theory-bg: rgba(245,158,11,0.07);
    --sb-bg:    #ffffff;
    --sb-input: #f8fafc;
    --sans: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    --mono: 'Courier New', monospace;
}

/* ══ DARK THEME — toggled by data-theme attr on <html> ══ */
html[data-theme="dark"] {
    --bg:       #060b14;
    --bg2:      #0a1020;
    --bg3:      #0f172a;
    --border:   #1a2540;
    --border2:  #243050;
    --text:     #e2e8f0;
    --text2:    #94a3b8;
    --text3:    #475569;
    --blue:     #ef4444;
    --blue-dim: #1d4ed8;
    --red:      #f43f5e;
    --green:    #10b981;
    --amber:    #f59e0b;
    --header-bg: rgba(6,11,20,0.92);
    --header-border: #1a2540;
    --metric-bg: #0a1020;
    --ins-row-bg: #0f172a;
    --sig-card-bg: #0f172a;
    --theory-bg: rgba(245,158,11,0.05);
    --sb-bg:    #0a1020;
    --sb-input: #0f172a;
}

/* ══ SYSTEM DARK (only when user hasn't set a manual preference) ══ */
@media (prefers-color-scheme: dark) {
    html:not([data-theme="light"]):not([data-theme="dark"]) {
        --bg:       #060b14;
        --bg2:      #0a1020;
        --bg3:      #0f172a;
        --border:   #1a2540;
        --border2:  #243050;
        --text:     #e2e8f0;
        --text2:    #94a3b8;
        --text3:    #475569;
        --header-bg: rgba(6,11,20,0.92);
        --header-border: #1a2540;
        --metric-bg: #0a1020;
        --ins-row-bg: #0f172a;
        --sig-card-bg: #0f172a;
        --theory-bg: rgba(245,158,11,0.05);
        --sb-bg:    #0a1020;
        --sb-input: #0f172a;
    }
}

/* ══ GLOBAL ══ */
html, body, [class*="css"] { font-family: var(--sans) !important; }
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
.block-container {
    background: var(--bg) !important;
    color: var(--text) !important;
}
/* 彻底隐藏 Streamlit 原生顶栏（display:none 不占空间，visibility:hidden 仍占空间） */
#MainMenu, footer { display: none !important; }
header,
[data-testid="stHeader"],
header[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarHeader"] {
    display: none !important;
}
/* 主界面顶部切换按钮 */
.chan-toggle-btn {
    width:40px;height:40px;border-radius:8px;
    border:1px solid var(--border,#e2e8f0);
    background:var(--bg2,#f8fafc);color:var(--text2,#475569);
    font-size:1.1rem;cursor:pointer;
    display:inline-flex;align-items:center;justify-content:center;
    transition:background .15s,color .15s;margin-bottom:4px;
    -webkit-tap-highlight-color:transparent;
}
.chan-toggle-btn:hover {
    background:var(--bg3,#f1f5f9);color:var(--text,#1e293b);
}
/* 侧边栏边缘切换按钮（桌面端） */
#chan-edge-btn {
    position: fixed;
    top: 50%;
    transform: translateY(-50%);
    z-index: 10001;
    width: 16px; height: 48px;
    border-radius: 0 6px 6px 0;
    background: var(--bg3, #f1f5f9);
    border: 1px solid var(--border, #e2e8f0);
    border-left: none;
    color: var(--text3, #94a3b8);
    font-size: 0.6rem; line-height: 1;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background .15s, left .28s ease, color .15s;
    padding: 0;
    box-shadow: 2px 0 6px rgba(0,0,0,0.06);
}
#chan-edge-btn:hover {
    background: var(--border, #e2e8f0);
    color: var(--text, #1e293b);
}

/* 移动端 FAB 侧边栏切换按钮 */
#chan-mob-fab {
    display: none;
    position: fixed;
    bottom: 24px;
    right: 20px;
    z-index: 10002;
    width: 52px; height: 52px;
    border-radius: 50%;
    background: #dc2626;
    border: none;
    color: #fff;
    font-size: 1.3rem;
    cursor: pointer;
    box-shadow: 0 4px 16px rgba(220,38,38,0.45);
    align-items: center;
    justify-content: center;
    transition: background .2s, transform .15s, box-shadow .2s;
    -webkit-tap-highlight-color: transparent;
}
#chan-mob-fab:active {
    transform: scale(0.92);
    box-shadow: 0 2px 8px rgba(220,38,38,0.35);
}
#chan-mob-fab.sb-open {
    background: #475569;
    box-shadow: 0 4px 16px rgba(71,85,105,0.4);
}
@media (max-width: 768px) {
    #chan-edge-btn { display: none !important; }
    #chan-mob-fab  { display: flex !important; }
}


/* ══ SCROLLBARS ══ */
* { scrollbar-width: thin; scrollbar-color: var(--border2) transparent; }
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 4px; }

/* ══ HEADER ══ */
.app-header {
    position: fixed; top: 0; left: 0; right: 0; height: 56px; z-index: 9999;
    background: var(--header-bg);
    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--header-border);
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 1.5rem 0 1rem;
}
/* 侧边栏切换按钮 */
.sidebar-toggle-btn {
    width: 34px; height: 34px; border-radius: 7px; cursor: pointer;
    background: transparent; border: none; outline: none;
    display: inline-flex; align-items: center; justify-content: center;
    margin-right: 10px; flex-shrink: 0;
    transition: background .15s;
    color: var(--text2);
}
.sidebar-toggle-btn:hover { background: var(--bg3); }
.sidebar-toggle-icon { font-size: 1.1rem; line-height: 1; pointer-events: none; }
.header-left  { display: flex; align-items: center; }
.header-logo  {
    width: 30px; height: 30px; border-radius: 7px; background: #dc2626;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.9rem; font-weight: 800; color: #fff;
    flex-shrink: 0; margin-right: 10px;
}
.header-appname  { font-size: 0.9rem; font-weight: 700; color: var(--text); margin-right: 20px; }
.header-divider  { width: 1px; height: 18px; background: var(--header-border); margin-right: 16px; }
.header-sym-name { font-size: 1rem; font-weight: 600; color: var(--text); margin-right: 8px; }
.header-sym-full { font-size: 0.82rem; color: var(--text2); margin-right: 8px; }
.header-sym-tag  {
    font-size: 0.58rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--blue); background: rgba(220,38,38,0.08); border: 1px solid rgba(220,38,38,0.18);
    border-radius: 4px; padding: 2px 7px;
}
.header-right { display: flex; align-items: center; gap: 12px; }
.header-sync  { font-size: 0.7rem; color: var(--text3); display: flex; align-items: center; gap: 6px; }
.sync-dot     { width: 6px; height: 6px; border-radius: 50%; background: var(--green); animation: pulse-dot 2s infinite; }
@keyframes pulse-dot { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.4;transform:scale(0.7)} }

/* 主题切换按钮 */
#theme-toggle {
    width: 30px; height: 30px; border-radius: 6px; cursor: pointer;
    background: var(--bg3); border: 1px solid var(--border);
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 0.85rem; transition: background .2s, border-color .2s;
    color: var(--text2); user-select: none;
}
#theme-toggle:hover { background: var(--border); border-color: var(--border2); }

/* ══ MAIN CONTENT AREA ══ */
.block-container {
    padding-top: 72px !important; padding-bottom: 2rem !important;
    padding-left: 1.5rem !important; padding-right: 1.5rem !important;
    max-width: 100% !important;
}

/* ══ SIDEBAR ══ */
[data-testid="stSidebar"] {
    background: var(--sb-bg) !important;
    border-right: 1px solid var(--border) !important;
    box-shadow: none !important;
    transition: transform .28s ease, margin-left .28s ease !important;
}
/* 折叠状态 */
body[data-sb-collapsed] [data-testid="stSidebar"] {
    transform: translateX(-100%) !important;
    margin-left: -21rem !important;
    min-width: 0 !important;
}
body[data-sb-collapsed] [data-testid="stMain"] {
    margin-left: 0 !important;
}
/* 消除侧边栏顶部空白 */
section[data-testid="stSidebar"] > div:first-child { padding-top: 0 !important; margin-top: 0 !important; }
[data-testid="stSidebarContent"] { padding-top: 0 !important; margin-top: 0 !important; }
[data-testid="stSidebarUserContent"] {
    padding-top: 12px !important;
    padding-left: 1rem !important; padding-right: 1rem !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.35rem !important; }

/* Sidebar labels */
[data-testid="stSidebar"] label {
    font-size: 0.62rem !important; font-weight: 600 !important;
    color: var(--text2) !important; text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}

/* Sidebar inputs */
[data-testid="stSidebar"] [data-testid="stTextInput"] input,
[data-testid="stSidebar"] [data-testid="stDateInput"] input,
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {
    font-size: 0.82rem !important; border-radius: 6px !important;
    border: 1px solid var(--border) !important;
    background: var(--sb-input) !important; color: var(--text) !important;
}
[data-testid="stSidebar"] [data-testid="stTextInput"] input:focus,
[data-testid="stSidebar"] [data-testid="stDateInput"] input:focus {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 2px rgba(220,38,38,0.1) !important;
}

/* ② K线周期 radio — 选中项红底白字 */
[data-testid="stSidebar"] [data-testid="stRadio"] > div {
    background: var(--bg3) !important; border-radius: 8px !important;
    border: 1px solid var(--border) !important;
    padding: 3px !important; gap: 2px !important;
    display: flex !important; flex-direction: row !important;
    flex-wrap: nowrap !important; width: 100% !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] > div > label {
    flex: 1 !important; min-width: 0 !important; border-radius: 5px !important;
    padding: 6px 2px !important; font-size: 0.7rem !important; font-weight: 500 !important;
    color: var(--text2) !important; cursor: pointer; transition: all .15s;
    text-align: center !important; white-space: nowrap !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
    letter-spacing: 0 !important; text-transform: none !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] > div > label > div:first-child { display: none !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] > div > label:has(input:checked) {
    background: #dc2626 !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    box-shadow: 0 1px 4px rgba(220,38,38,0.35) !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] > div > label:has(input:checked) p,
[data-testid="stSidebar"] [data-testid="stRadio"] > div > label:has(input:checked) span,
[data-testid="stSidebar"] [data-testid="stRadio"] > div > label:has(input:checked) div {
    color: #ffffff !important;
}

/* Sidebar buttons */
[data-testid="stSidebar"] button {
    font-size: 0.72rem !important; border-radius: 6px !important;
    min-height: 1.9rem !important; transition: all .15s !important;
}
[data-testid="stSidebar"] button[kind="secondary"] {
    background: var(--bg3) !important; border: 1px solid var(--border) !important;
    color: var(--text2) !important; font-weight: 500 !important; box-shadow: none !important;
}
[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background: var(--border) !important; color: var(--text) !important;
}
[data-testid="stSidebar"] button[kind="primary"] {
    background: var(--blue) !important; border: none !important;
    color: #fff !important; font-weight: 600 !important;
    min-height: 2.6rem !important; font-size: 0.85rem !important;
    box-shadow: 0 2px 10px rgba(220,38,38,0.22) !important; border-radius: 8px !important;
}
[data-testid="stSidebar"] button[kind="primary"]:hover {
    background: var(--blue-dim) !important;
    box-shadow: 0 4px 16px rgba(220,38,38,0.35) !important;
    transform: translateY(-1px) !important;
}

/* ── 用户信息行等高修复 ── */
[data-testid="stHorizontalBlock"]:has(.user-card) {
    align-items: stretch !important;
}
[data-testid="stHorizontalBlock"]:has(.user-card) [data-testid="stColumn"],
[data-testid="stHorizontalBlock"]:has(.user-card) [data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"]:has(.user-card) [data-testid="stVerticalBlockBorderWrapper"] {
    display: flex !important;
    flex-direction: column !important;
    flex: 1 !important;
    min-height: 0 !important;
    gap: 0 !important;
}

/* 退出 */
.sb-logout {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
    min-height: 0 !important;
}
.sb-logout button {
    background: transparent !important; border: 1px solid var(--border) !important;
    color: var(--text3) !important; font-size: 1.1rem !important;
    flex: 1 !important; min-height: 0 !important; border-radius: 8px !important;
    width: 100% !important;
}
.sb-logout button:hover { border-color: var(--red) !important; color: var(--red) !important; }

/* User card */
.user-card {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 12px; margin-bottom: 4px;
    background: var(--bg3); border-radius: 8px; border: 1px solid var(--border); min-width: 0;
}
.user-avatar {
    width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0;
    background: rgba(220,38,38,0.08); border: 1px solid rgba(220,38,38,0.18);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.7rem; font-weight: 700; color: var(--blue); text-transform: uppercase;
}
.user-name { font-size: 0.82rem; font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.user-role { font-size: 0.62rem; color: var(--text3); margin-top: 1px; }
.sb-divider { border: none; border-top: 1px solid var(--border); margin: 6px 0; }

/* ══ METRIC GRID ══ */
.metric-grid {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 1px; margin-bottom: 1rem;
    background: var(--border); border: 1px solid var(--border); border-radius: 12px; overflow: hidden;
}
.metric-card { background: var(--metric-bg); padding: 1rem 1.1rem; text-align: left; transition: background .2s; }
.metric-card:hover { background: var(--bg3); }
.metric-sup  { font-size: 0.62rem; font-weight: 600; color: var(--text3); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px; }
.metric-val  { font-size: 1.45rem; font-weight: 700; color: var(--text) !important; margin-bottom: 4px; line-height: 1.2; }
.metric-lbl  { font-size: 0.68rem; font-weight: 500; color: var(--text2); letter-spacing: 0.01em; }

/* ══ CHART WRAP ══ */
.chart-wrap { background: var(--bg); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; margin-bottom: 1rem; }
.chart-topbar { display: flex; align-items: center; padding: 10px 16px; border-bottom: 1px solid var(--border); }
.chart-legend { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.lg-item { display: flex; align-items: center; gap: 5px; }
.lg-sq   { width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }
.lg-ln   { width: 18px; height: 2px; flex-shrink: 0; }
.lg-dot  { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.lg-txt  { font-size: 0.68rem; color: var(--text3); }
.lg-sep  { width: 1px; height: 14px; background: var(--border); }
.chart-inner { padding: 8px 4px 0; }

/* ══ TABS ══ */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: var(--bg3) !important; border-radius: 8px !important;
    padding: 3px !important; border: 1px solid var(--border) !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important; border-radius: 6px !important;
    font-size: 0.75rem !important; color: var(--text3) !important;
    padding: 6px 14px !important; border: none !important; transition: all .15s !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: var(--bg) !important; color: var(--text) !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08) !important;
}
[data-testid="stTabs"] [data-baseweb="tab-border"] { display: none !important; }
[data-testid="stTabPanel"] { padding: 0 !important; }

/* ══ INSIGHT ROWS ══ */
.ins-row { display: flex; align-items: center; justify-content: space-between; padding: 8px 10px; background: var(--ins-row-bg); border-radius: 6px; margin-bottom: 6px; }
.ins-lbl { font-size: 0.74rem; font-weight: 500; color: var(--text2); }
.ins-val { font-size: 0.8rem; font-weight: 600; color: var(--text); }

/* ══ SIGNAL CARDS ══ */
.sig-card { border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; background: var(--sig-card-bg); border: 1px solid var(--border); border-left-width: 3px !important; }
.sig-meta  { font-size: 0.68rem; color: var(--text3); margin-bottom: 4px; }
.sig-title { font-size: 0.9rem; font-weight: 600; margin-bottom: 4px; }
.sig-desc  { font-size: 0.8rem; color: var(--text2); line-height: 1.6; }

/* ══ THEORY BOX ══ */
.theory-box { background: var(--theory-bg); border-left: 3px solid var(--amber); padding: 10px 12px; border-radius: 0 8px 8px 0; font-size: 0.82rem; color: var(--text2); line-height: 1.65; margin-top: 8px; }

/* ══ QUOTE BOX ══ */
.quote-box { background: rgba(245,158,11,0.07); border: 1px solid rgba(245,158,11,0.22); border-radius: 8px; padding: 10px 12px; margin-top: 8px; }
.quote-title { font-size: 0.62rem; color: var(--amber); letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 5px; }
.quote-text  { font-size: 0.75rem; color: #92400e; line-height: 1.7; font-style: italic; }

/* ══ SYM HINT ══ */
.sym-hint {
    display: flex; align-items: center; gap: 10px;
    font-size: 0.85rem; font-weight: 500; color: var(--text2);
    background: var(--bg2, #f8fafc);
    border: 1.5px dashed var(--border2, #cbd5e1);
    border-radius: 10px;
    padding: 12px 18px;
    margin: 2px 0 8px;
}
.sym-hint::before { content: "👈"; font-size: 1.1rem; }

/* ══ EMPTY STATE ══ */
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 4rem 2rem; text-align: center; background: var(--bg2); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 1rem; }
.empty-icon  { font-size: 2.5rem; margin-bottom: 1rem; opacity: 0.4; }
.empty-title { font-size: 1rem; font-weight: 700; color: var(--text2); margin-bottom: 0.4rem; }
.empty-desc  { font-size: 0.72rem; color: var(--text3); line-height: 1.7; }

/* ══ RESPONSIVE — ③ 移动端全面适配 ══ */
@media (max-width: 768px) {
    /* 侧边栏改为 overlay 抽屉 */
    [data-testid="stSidebar"] {
        position: fixed !important;
        top: 0 !important; left: 0 !important;
        height: 100vh !important;
        width: 88vw !important; max-width: 320px !important;
        z-index: 2000 !important;
        overflow-y: auto !important;
        box-shadow: 4px 0 24px rgba(0,0,0,0.18) !important;
        transition: transform .28s ease !important;
    }
    /* 移动端主内容始终全宽 */
    [data-testid="stMain"] {
        margin-left: 0 !important;
        width: 100% !important;
    }
    /* 移动端折叠：侧边栏滑出屏幕 */
    body[data-sb-collapsed] [data-testid="stSidebar"] {
        transform: translateX(-100%) !important;
        margin-left: 0 !important;
    }
    /* 遮罩层 */
    #chan-mob-overlay {
        display: none;
        position: fixed; inset: 0;
        background: rgba(0,0,0,0.45);
        z-index: 1999;
    }
    body:not([data-sb-collapsed]) #chan-mob-overlay { display: block; }
    /* 内容区 */
    .block-container {
        padding-top: 64px !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    /* Header */
    .app-header { padding: 0 0.75rem !important; }
    .header-sym-full { display: none; }
    .header-appname { display: none; }
    /* 指标卡 2列 */
    .metric-grid { grid-template-columns: repeat(2, 1fr); }
    .metric-val  { font-size: 1.15rem; }
    .metric-card { padding: 0.75rem 0.75rem; }
    /* 输入框防缩放 */
    input, select, textarea { font-size: 16px !important; }
    /* 图表自适应 */
    .chart-wrap { border-radius: 8px; }
    /* Sidebar 内控件字号加大方便手指点击 */
    [data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div { font-size: 0.95rem !important; min-height: 2.5rem !important; }
    [data-testid="stSidebar"] [data-testid="stTextInput"] input { font-size: 16px !important; min-height: 2.5rem !important; }
    [data-testid="stSidebar"] [data-testid="stDateInput"] input { font-size: 16px !important; min-height: 2.5rem !important; }
    /* Radio 按钮触摸友好 */
    [data-testid="stSidebar"] [data-testid="stRadio"] > div > label { padding: 8px 2px !important; font-size: 0.75rem !important; }
    /* 执行按钮更大 */
    [data-testid="stSidebar"] button[kind="primary"] { min-height: 3rem !important; font-size: 1rem !important; }
    /* 间距区间按钮 */
    [data-testid="stSidebar"] .stButton button { min-height: 2.4rem !important; }
}
@media (max-width: 480px) {
    .metric-val  { font-size: 1rem; }
    .metric-card { padding: 0.65rem 0.5rem; }
    .metric-sup  { font-size: 0.58rem; }
    .header-logo { width: 26px; height: 26px; font-size: 0.8rem; }
    /* 图例换行 */
    .chart-legend { gap: 8px; }
    .lg-txt { font-size: 0.62rem; }
}
</style>

<script>
(function(){
    // ── 清除浏览器缓存的侧边栏折叠状态，让 initial_sidebar_state="expanded" 生效 ──
    [localStorage, sessionStorage].forEach(function(store) {
        var keys = [];
        try { for (var i = 0; i < store.length; i++) keys.push(store.key(i)); } catch(e){}
        keys.forEach(function(k) {
            if (k && k.toLowerCase().indexOf('sidebar') >= 0) {
                try { store.removeItem(k); } catch(e){}
            }
        });
    });

    // ── 主题切换 ──
    var saved = localStorage.getItem('chanlun-theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);

    // ── 移动端：默认折叠侧边栏，创建遮罩层 ──
    if (window.innerWidth <= 768) {
        document.body.setAttribute('data-sb-collapsed', '1');
        if (!document.getElementById('chan-mob-overlay')) {
            var overlay = document.createElement('div');
            overlay.id = 'chan-mob-overlay';
            overlay.onclick = function() {
                document.body.setAttribute('data-sb-collapsed', '1');
                setTimeout(syncHeader, 320);
            };
            document.body.appendChild(overlay);
        }
    }

    // ── 通用侧边栏切换函数（直接 CSS 操控，不依赖 Streamlit 内部按钮）──
    window.chanToggleSidebar = function toggleSidebar() {
        if (document.body.hasAttribute('data-sb-collapsed')) {
            document.body.removeAttribute('data-sb-collapsed');
        } else {
            document.body.setAttribute('data-sb-collapsed', '1');
        }
        setTimeout(syncHeader, 320);
    }

    // ── 桌面端边缘按钮 ──
    if (!document.getElementById('chan-edge-btn')) {
        var edgeBtn = document.createElement('button');
        edgeBtn.id = 'chan-edge-btn';
        edgeBtn.innerHTML = '&#9664;';
        edgeBtn.onclick = window.chanToggleSidebar;
        document.body.appendChild(edgeBtn);
    }

    // ── 移动端 FAB 按钮 ──
    if (!document.getElementById('chan-mob-fab')) {
        var mobFab = document.createElement('button');
        mobFab.id = 'chan-mob-fab';
        mobFab.title = '展开/收起侧边栏';
        mobFab.innerHTML = '&#9776;';
        mobFab.onclick = window.chanToggleSidebar;
        document.body.appendChild(mobFab);
    }

    // ── 同步 header left 偏移 + 两个按钮状态 ──
    function syncHeader() {
        var sidebar = document.querySelector('[data-testid="stSidebar"]');
        var header  = document.querySelector('.app-header');
        var edgeBtn = document.getElementById('chan-edge-btn');
        var mobFab  = document.getElementById('chan-mob-fab');
        if (!sidebar) return;
        var isMobile = window.innerWidth <= 768;
        var sbRect   = sidebar.getBoundingClientRect();
        var isOpen   = !document.body.hasAttribute('data-sb-collapsed') && sbRect.width > 50;
        if (header) header.style.left = (!isMobile && isOpen) ? sbRect.right + 'px' : '0px';
        if (edgeBtn) {
            edgeBtn.style.left = sbRect.right + 'px';
            edgeBtn.innerHTML  = isOpen ? '&#9664;' : '&#9654;';
        }
        if (mobFab) {
            mobFab.innerHTML = isOpen ? '&#10005;' : '&#9776;';
            if (isOpen) { mobFab.classList.add('sb-open'); }
            else        { mobFab.classList.remove('sb-open'); }
        }
    }

    // ── ResizeObserver 监听侧边栏，防重复注册 ──
    if (!window._chanRoStarted) {
        window._chanRoStarted = true;
        var roInterval = setInterval(function() {
            var sidebar = document.querySelector('[data-testid="stSidebar"]');
            if (sidebar) {
                syncHeader();
                new ResizeObserver(syncHeader).observe(sidebar);
                window.addEventListener('resize', syncHeader);
                clearInterval(roInterval);
            }
        }, 200);
    } else {
        syncHeader();
    }

    // ── 注入主题切换按钮 ──
    var tries = 0;
    var injectTheme = setInterval(function(){
        tries++;
        var appHeader = document.querySelector('.app-header .header-right');
        if(appHeader && !document.getElementById('theme-toggle')){
            var btn = document.createElement('div');
            btn.id = 'theme-toggle';
            var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            btn.title = isDark ? '切换亮色' : '切换暗色';
            btn.innerHTML = isDark ? '☀' : '🌙';
            btn.onclick = function(){
                var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
                document.documentElement.setAttribute('data-theme', next);
                localStorage.setItem('chanlun-theme', next);
                btn.innerHTML = next === 'dark' ? '☀' : '🌙';
            };
            appHeader.insertBefore(btn, appHeader.firstChild);
            clearInterval(injectTheme);
        }
        if(tries > 40) clearInterval(injectTheme);
    }, 150);
})();
</script>
""", unsafe_allow_html=True)

# ================= 顶部固定标题栏 =================
_sym_display  = st.session_state.get("sym", "")
_name_display = st.session_state.get("sym_name", "")
_mkt_display  = st.session_state.get("mkt", "")

_sym_block = ""
if _sym_display:
    _sym_block = (
        f'<div class="header-divider"></div>'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'  <span class="header-sym-name">{_sym_display}</span>'
        + (f'  <span class="header-sym-full">{_name_display}</span>' if _name_display else '')
        + (f'  <span class="header-sym-tag">{_mkt_display}</span>'   if _mkt_display else '')
        + '</div>'
    )

st.markdown(
    f'<div class="app-header">'
    f'  <div class="header-left">'
    f'    <div class="header-logo">缠</div>'
    f'    <span class="header-appname">AI解盘终端</span>'
    f'    {_sym_block}'
    f'  </div>'
    f'  <div class="header-right">'
    f'    <span class="header-sync"><span class="sync-dot"></span>LIVE</span>'
    f'  </div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ================= 市场常量 =================
MARKET_CN, MARKET_HK, MARKET_US, MARKET_FUTURES = "A股", "港股", "美股", "国内期货"

# ================= 期货品种交易所映射 =================
_FUTURES_EXCHANGE = {
    **{k: "113" for k in ["RB","CU","AL","ZN","AU","AG","NI","SN","PB","HC","SS","SC","LU","BC","FU","BU","RU","SP","WR","BR"]},
    **{k: "114" for k in ["M","A","B","C","CS","J","JM","I","L","V","PP","EG","EB","PG","RR","LH","P","Y","FB","BB"]},
    **{k: "115" for k in ["SR","CF","ZC","FG","TA","MA","RM","OI","CY","AP","CJ","UR","SA","PK","PF","SM","SF"]},
    **{k: "8"   for k in ["IF","IC","IH","IM","TF","T","TS"]},
}

# ================= 期货数据获取（修复 KeyError 0 + 双数据源）=================
def fetch_futures(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    主力: 东方财富 push2his (日K, fields: 日期,开,收,高,低)
    备用: 新浪财经 JSONP  (兼容 list / dict 两种返回格式)
    symbol 示例: RB0  AU0  IF0  M0  CU0
    """
    sym    = symbol.strip().upper()
    prefix = re.sub(r'\d+$', '', sym)
    ex_id  = _FUTURES_EXCHANGE.get(prefix, "113")

    # ── 东方财富 ────────────────────────────────────────────────
    try:
        url = (
            f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
            f"?secid={ex_id}.{sym}"
            f"&fields1=f1,f2,f3,f4,f5,f6"
            f"&fields2=f51,f52,f53,f54,f55"
            f"&lmt=1000&klt=101&fqt=0"
            f"&beg={start_date}&end={end_date}"
        )
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        klines = r.json().get("data", {}).get("klines") or []
        if klines:
            rows = []
            for k in klines:
                p = k.split(",")
                rows.append({
                    "date":  pd.to_datetime(p[0]),
                    "open":  float(p[1]),
                    "close": float(p[2]),
                    "high":  float(p[3]),
                    "low":   float(p[4]),
                })
            df = pd.DataFrame(rows)
            s, e = pd.to_datetime(start_date), pd.to_datetime(end_date)
            df = df[(df["date"] >= s) & (df["date"] <= e)].reset_index(drop=True)
            if not df.empty:
                return df
    except Exception:
        pass  # 静默失败，尝试备用

    # ── 新浪财经备用 ─────────────────────────────────────────────
    try:
        sym_low = sym.lower()
        url2 = (
            f"https://stock2.finance.sina.com.cn/futures/api/jsonp.php"
            f"/var%20_=/InnerFuturesNewService.getDailyKLine?symbol={sym_low}"
        )
        r2   = SESSION.get(url2, timeout=15)
        hit  = re.search(r'\[.*?\]', r2.text, re.DOTALL)
        if hit:
            raw  = json.loads(hit.group())
            rows = []
            for item in raw:
                try:
                    if isinstance(item, dict):
                        # {"d":"2025-01-02","o":"3800","h":"3850","l":"3780","c":"3820"}
                        rows.append({
                            "date":  pd.to_datetime(item.get("d") or item.get("date")),
                            "open":  float(item.get("o") or item.get("open",  0)),
                            "high":  float(item.get("h") or item.get("high",  0)),
                            "low":   float(item.get("l") or item.get("low",   0)),
                            "close": float(item.get("c") or item.get("close", 0)),
                        })
                    elif isinstance(item, (list, tuple)) and len(item) >= 5:
                        # ["2025-01-02","3800","3850","3780","3820","12345"]
                        rows.append({
                            "date":  pd.to_datetime(item[0]),
                            "open":  float(item[1]),
                            "high":  float(item[2]),
                            "low":   float(item[3]),
                            "close": float(item[4]),
                        })
                except Exception:
                    continue
            if rows:
                df = pd.DataFrame(rows)
                s, e = pd.to_datetime(start_date), pd.to_datetime(end_date)
                df = df[(df["date"] >= s) & (df["date"] <= e)].reset_index(drop=True)
                if not df.empty:
                    return df
    except Exception:
        pass

    raise ValueError(
        f"期货 [{symbol}] 所有数据源均未返回数据。\n"
        f"请检查：\n"
        f"• 代码格式（主力合约用 0 结尾：RB0、AU0、IF0、M0、CU0）\n"
        f"• 日期范围是否合理（期货合约有到期日）\n"
        f"• 网络连接是否正常"
    )

# ================= 其他市场数据 =================
def fetch_cn(symbol, start_date, end_date):
    pfx = "sh" if (int(symbol) >= 600000 or 500000 <= int(symbol) < 600000) else "sz"
    url = (f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={pfx}{symbol},day,"
           f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]},"
           f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]},640,qfq")
    raw = SESSION.get(url, timeout=15).json().get("data", {}).get(f"{pfx}{symbol}", {}).get("qfqday", [])
    if not raw: raise ValueError("A股接口返回空数据")
    df = pd.DataFrame([{"date": pd.to_datetime(r[0]), "open": float(r[1]), "close": float(r[2]), "high": float(r[3]), "low": float(r[4])} for r in raw])
    return df[(df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))].reset_index(drop=True)

def fetch_hk(symbol, start_date, end_date):
    """
    港股日K，三数据源自动切换：
    1. 腾讯前复权 (qfqday)
    2. 腾讯普通日K (day)
    3. 东方财富 (secid 116.XXXXX)
    """
    sym = symbol.replace(".HK", "").zfill(5)
    sd  = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
    ed  = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"

    def _parse(raw):
        rows = []
        for r in raw:
            try:
                rows.append({"date": pd.to_datetime(r[0]), "open": float(r[1]),
                              "close": float(r[2]), "high": float(r[3]), "low": float(r[4])})
            except Exception:
                continue
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        s, e = pd.to_datetime(start_date), pd.to_datetime(end_date)
        return df[(df["date"] >= s) & (df["date"] <= e)].reset_index(drop=True)

    # ── 1. 腾讯前复权 ────────────────────────────────────────
    try:
        data = SESSION.get(
            f"https://web.ifzq.gtimg.cn/appstock/app/hkfqkline/get"
            f"?param=hk{sym},day,{sd},{ed},640,qfq", timeout=12
        ).json().get("data", {}).get(f"hk{sym}", {})
        raw = data.get("qfqday") or data.get("day") or []
        if raw:
            df = _parse(raw)
            if not df.empty:
                return df
    except Exception:
        pass

    # ── 2. 腾讯普通日K ───────────────────────────────────────
    try:
        data = SESSION.get(
            f"https://web.ifzq.gtimg.cn/appstock/app/kline/get"
            f"?param=hk{sym},day,{sd},{ed},640", timeout=12
        ).json().get("data", {}).get(f"hk{sym}", {})
        raw = data.get("day") or []
        if raw:
            df = _parse(raw)
            if not df.empty:
                return df
    except Exception:
        pass

    # ── 3. 东方财富港股接口 ──────────────────────────────────
    try:
        # 港股 secid 前缀为 116，代码去掉前导零
        code_em = str(int(sym))
        url_em = (
            f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
            f"?secid=116.{code_em}"
            f"&fields1=f1,f2,f3,f4,f5,f6"
            f"&fields2=f51,f52,f53,f54,f55"
            f"&lmt=1000&klt=101&fqt=1"
            f"&beg={start_date}&end={end_date}"
        )
        r = SESSION.get(url_em, timeout=12)
        r.raise_for_status()
        klines = r.json().get("data", {}).get("klines") or []
        if klines:
            rows = []
            for k in klines:
                p = k.split(",")
                rows.append({"date": pd.to_datetime(p[0]), "open": float(p[1]),
                              "close": float(p[2]), "high": float(p[3]), "low": float(p[4])})
            df = pd.DataFrame(rows)
            s, e = pd.to_datetime(start_date), pd.to_datetime(end_date)
            df = df[(df["date"] >= s) & (df["date"] <= e)].reset_index(drop=True)
            if not df.empty:
                return df
    except Exception:
        pass

    raise ValueError(
        f"港股 [{symbol}] 三个数据源均未返回数据。\n"
        f"请确认：\n"
        f"• 代码格式正确（如美团=03690，腾讯=00700，阿里=09988）\n"
        f"• 所选日期范围内有交易数据\n"
        f"• 网络连接正常"
    )

def fetch_us(symbol, start_date, end_date):
    import yfinance as yf, datetime
    sd  = datetime.datetime.strptime(start_date, "%Y%m%d").strftime("%Y-%m-%d")
    ed  = (datetime.datetime.strptime(end_date,   "%Y%m%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    raw = yf.Ticker(symbol.replace(".", "-").upper()).history(start=sd, end=ed, interval="1d", auto_adjust=True).reset_index()
    if raw.empty: raise ValueError("美股接口返回空数据")
    raw["Date"] = pd.to_datetime(raw["Date"]).dt.tz_localize(None)
    df = pd.DataFrame({"date": raw["Date"], "open": raw["Open"], "high": raw["High"], "low": raw["Low"], "close": raw["Close"]})
    return df[df["close"] > 0].reset_index(drop=True)

def fetch_stock_data(symbol, start_date, end_date, market, klt="101"):
    if klt != "101":
        return _fetch_intraday(symbol, start_date, end_date, market, klt)
    if market == MARKET_FUTURES: return fetch_futures(symbol, start_date, end_date)
    if market == MARKET_CN:      return fetch_cn(symbol, start_date, end_date)
    elif market == MARKET_HK:    return fetch_hk(symbol, start_date, end_date)
    elif market == MARKET_US:    return fetch_us(symbol, start_date, end_date)

# ================= 分时数据获取 =================
def _fetch_intraday_em(secid: str, start_date: str, end_date: str, klt: str) -> pd.DataFrame:
    """东方财富分钟K线（A股/港股/期货通用）"""
    url = (
        f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
        f"?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55"
        f"&lmt=2000&klt={klt}&fqt=0&beg={start_date}&end={end_date}"
    )
    r = SESSION.get(url, timeout=15)
    r.raise_for_status()
    klines = r.json().get("data", {}).get("klines") or []
    rows = []
    for k in klines:
        p = k.split(",")
        try:
            rows.append({"date": pd.to_datetime(p[0]), "open": float(p[1]),
                         "close": float(p[2]), "high": float(p[3]), "low": float(p[4])})
        except Exception:
            continue
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def _fetch_intraday(symbol, start_date, end_date, market, klt):
    if market == MARKET_CN:
        pfx_id = "1" if (int(symbol) >= 600000 or 500000 <= int(symbol) < 600000) else "0"
        df = _fetch_intraday_em(f"{pfx_id}.{symbol}", start_date, end_date, klt)
        if df.empty: raise ValueError(f"A股 [{symbol}] 分时数据为空，请确认交易日期")
        return df
    elif market == MARKET_HK:
        sym = symbol.replace(".HK", "").zfill(5)
        df = _fetch_intraday_em(f"116.{str(int(sym))}", start_date, end_date, klt)
        if df.empty: raise ValueError(f"港股 [{symbol}] 分时数据为空，请确认交易日期")
        return df
    elif market == MARKET_FUTURES:
        sym = symbol.strip().upper()
        ex_id = _FUTURES_EXCHANGE.get(re.sub(r'\d+$', '', sym), "113")
        df = _fetch_intraday_em(f"{ex_id}.{sym}", start_date, end_date, klt)
        if df.empty: raise ValueError(f"期货 [{symbol}] 分时数据为空，请确认交易日期")
        return df
    elif market == MARKET_US:
        import yfinance as yf, datetime
        klt_map = {"1": "1m", "5": "5m", "15": "15m", "30": "30m", "60": "60m"}
        interval = klt_map.get(klt, "5m")
        sd = datetime.datetime.strptime(start_date, "%Y%m%d").strftime("%Y-%m-%d")
        ed = (datetime.datetime.strptime(end_date, "%Y%m%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        raw = yf.Ticker(symbol.replace(".", "-").upper()).history(start=sd, end=ed, interval=interval, auto_adjust=True).reset_index()
        if raw.empty: raise ValueError(f"美股 [{symbol}] 分时数据为空，请确认交易日期")
        dt_col = "Datetime" if "Datetime" in raw.columns else "Date"
        raw[dt_col] = pd.to_datetime(raw[dt_col])
        if raw[dt_col].dt.tz is not None:
            raw[dt_col] = raw[dt_col].dt.tz_localize(None)
        df = pd.DataFrame({"date": raw[dt_col], "open": raw["Open"],
                           "high": raw["High"], "low": raw["Low"], "close": raw["Close"]})
        return df[df["close"] > 0].reset_index(drop=True)

# ================= 缠论核心推演算法 =================
def process_inclusion(df):
    klines = df.to_dict("records")
    if len(klines) < 2: return klines
    std = [klines[0]]
    for i in range(1, len(klines)):
        cur, prev = klines[i], std[-1]
        if (cur["high"] <= prev["high"] and cur["low"] >= prev["low"]) or (cur["high"] >= prev["high"] and cur["low"] <= prev["low"]):
            up = len(std) < 2 or prev["high"] >= std[-2]["high"]
            prev["high"], prev["low"] = (max(prev["high"], cur["high"]), max(prev["low"], cur["low"])) if up else (min(prev["high"], cur["high"]), min(prev["low"], cur["low"]))
            prev["date"] = cur["date"]
        else: std.append(cur)
    return std

def find_fractals(std):
    out = []
    for i in range(1, len(std)-1):
        p, c, n = std[i-1], std[i], std[i+1]
        if   c["high"]>p["high"] and c["high"]>n["high"] and c["low"]>p["low"] and c["low"]>n["low"]: out.append({"type":"top",    "index":i,"kline":c})
        elif c["low"]<p["low"]   and c["low"]<n["low"]   and c["high"]<p["high"] and c["high"]<n["high"]: out.append({"type":"bottom","index":i,"kline":c})
    return out

def draw_strokes(fractals):
    if not fractals: return []
    strokes, cand = [], fractals[0]
    for i in range(1, len(fractals)):
        cur = fractals[i]
        if cur["type"] == cand["type"]:
            if cur["type"]=="top"    and cur["kline"]["high"] > cand["kline"]["high"]: cand = cur
            if cur["type"]=="bottom" and cur["kline"]["low"]  < cand["kline"]["low"]:  cand = cur
            continue
        if cur["index"] - cand["index"] >= 4:
            cand["end_index"] = cur["index"]; strokes.append(cand); cand = cur
    strokes.append(cand)
    return strokes

def find_hubs(vs):
    for s in vs: s["price"] = s["kline"]["high"] if s["type"]=="top" else s["kline"]["low"]
    hubs, i = [], 0
    while i < len(vs)-3:
        s1,s2,s3,s4 = vs[i],vs[i+1],vs[i+2],vs[i+3]
        ZG = min(max(s1["price"],s2["price"]),max(s2["price"],s3["price"]),max(s3["price"],s4["price"]))
        ZD = max(min(s1["price"],s2["price"]),min(s2["price"],s3["price"]),min(s3["price"],s4["price"]))
        if ZG > ZD:
            sdt,edt,j = pd.to_datetime(s1["kline"]["date"]),pd.to_datetime(s4["kline"]["date"]),i+3
            while j < len(vs)-1:
                if min(vs[j]["price"],vs[j+1]["price"]) > ZG or max(vs[j]["price"],vs[j+1]["price"]) < ZD: break
                edt = pd.to_datetime(vs[j+1]["kline"]["date"]); j+=1
            hubs.append({"ZG":ZG,"ZD":ZD,"start_dt":sdt,"end_dt":edt,"start_idx":i,"end_idx":j})
            i = j
        else: i += 1
    return hubs

def calc_macd(df):
    df = df.copy()
    df["EMA12"] = df["close"].ewm(span=12,adjust=False).mean()
    df["EMA26"] = df["close"].ewm(span=26,adjust=False).mean()
    df["DIF"]   = df["EMA12"] - df["EMA26"]
    df["DEA"]   = df["DIF"].ewm(span=9,adjust=False).mean()
    df["MACD"]  = (df["DIF"] - df["DEA"]) * 2
    return df

def analyze_signals(vs, hubs):
    buy_s, sell_s = [], []
    if not hubs or len(vs)<4: return buy_s, sell_s
    lh = hubs[-1]; ZG,ZD = lh["ZG"],lh["ZD"]
    for i in range(lh["end_idx"], len(vs)-1):
        sl,sr = vs[i],vs[i+1]
        dt,rp = pd.to_datetime(sr["kline"]["date"]), sr["price"]
        if sl["type"]=="bottom" and sl["price"]>ZG and sr["type"]=="top" and rp>ZG:
            buy_s.append({"date":dt,"price":rp,"type":"第三类买点"})
        if sl["type"]=="top" and sl["price"]<ZD and sr["type"]=="bottom" and rp<ZD:
            sell_s.append({"date":dt,"price":rp,"type":"第三类卖点"})
        if sr["type"]=="top" and rp<ZD:
            es = vs[lh["start_idx"]]
            if (sl["price"]-rp) < (es["kline"]["high"]-es["kline"]["low"]):
                buy_s.append({"date":dt,"price":rp*0.98,"type":"第一类买点"})
    return buy_s, sell_s

# ================= 动态 Plotly 图表 =================
def build_plotly_chart(df, valid_strokes, hubs, buy_signals, sell_signals, symbol, market, klt="101"):
    currency = {"A股":"¥","港股":"HK$","美股":"$","国内期货":"点"}.get(market,"")
    is_intraday = klt != "101"
    tfmt = "%Y-%m-%d %H:%M" if is_intraday else "%Y-%m-%d"
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75,0.25])

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="K线", increasing_line_color="#ef4444", decreasing_line_color="#10b981",
        increasing_fillcolor="#ef4444", decreasing_fillcolor="#10b981",
        hoverinfo="text",
        hovertext=[f"{d.strftime(tfmt)}<br>收:{c:.2f}" for d,c in zip(df.index, df.close)]
    ), row=1, col=1)

    stroke_x = [pd.to_datetime(s["kline"]["date"]) for s in valid_strokes if pd.to_datetime(s["kline"]["date"]) in df.index]
    stroke_y = [s["price"] for s in valid_strokes if pd.to_datetime(s["kline"]["date"]) in df.index]
    fig.add_trace(go.Scatter(x=stroke_x, y=stroke_y, mode="lines+markers", name="缠论笔",
        line=dict(color="#3b82f6", width=2), marker=dict(size=4)), row=1, col=1)

    for hub in hubs:
        x0,x1,zd,zg = hub["start_dt"],hub["end_dt"],hub["ZD"],hub["ZG"]
        fig.add_shape(type="rect", xref="x", yref="y", x0=x0, y0=zd, x1=x1, y1=zg,
                      line=dict(color="#f59e0b",width=1.5), fillcolor="rgba(245,158,11,0.1)", row=1,col=1)
        fig.add_annotation(x=x1, y=zg, text=f"ZG: {zg:.2f}", showarrow=False,
            xanchor="left", xshift=8, bgcolor="rgba(255,255,255,0.85)", bordercolor="#f59e0b", borderwidth=1,
            font=dict(size=10,color="#b45309"), row=1, col=1)
        fig.add_annotation(x=x1, y=zd, text=f"ZD: {zd:.2f}", showarrow=False,
            xanchor="left", xshift=8, bgcolor="rgba(255,255,255,0.85)", bordercolor="#f59e0b", borderwidth=1,
            font=dict(size=10,color="#b45309"), row=1, col=1)

    if buy_signals:
        bx = [b["date"] for b in buy_signals if b["date"] in df.index]
        by = [b["price"]*0.94 for b in buy_signals if b["date"] in df.index]
        bt = [b["type"] for b in buy_signals if b["date"] in df.index]
        fig.add_trace(go.Scatter(x=bx, y=by, mode="markers+text", name="买点",
            marker=dict(symbol="triangle-up",size=10,color="#ef4444"),
            text=bt, textposition="bottom center", textfont=dict(size=10,color="#ef4444"), hoverinfo="skip"), row=1,col=1)

    if sell_signals:
        sx  = [s["date"] for s in sell_signals if s["date"] in df.index]
        sy  = [s["price"]*1.06 for s in sell_signals if s["date"] in df.index]
        st2 = [s["type"] for s in sell_signals if s["date"] in df.index]
        fig.add_trace(go.Scatter(x=sx, y=sy, mode="markers+text", name="卖点",
            marker=dict(symbol="triangle-down",size=10,color="#10b981"),
            text=st2, textposition="top center", textfont=dict(size=10,color="#10b981"), hoverinfo="skip"), row=1,col=1)

    macd_colors = ["#ef4444" if v>=0 else "#10b981" for v in df["MACD"]]
    fig.add_trace(go.Bar(x=df.index, y=df["MACD"], name="MACD", marker_color=macd_colors), row=2,col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["DIF"], name="DIF", line=dict(color="#f43f5e",width=1)), row=2,col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["DEA"], name="DEA", line=dict(color="#3b82f6",width=1)), row=2,col=1)

    # ── 生成中文 x 轴刻度 ──────────────────────────────────────
    _dates = df.index.tolist()
    _n = len(_dates)
    _step = max(1, _n // 8)
    _tick_idx = list(range(0, _n, _step))
    _tickvals = [_dates[i] for i in _tick_idx]
    if is_intraday:
        _ticktext = [
            f"{d.month}月{d.day}日 {d.strftime('%H:%M')}" for d in _tickvals
        ]
    else:
        _ticktext = [f"{d.month}月{d.day}日" for d in _tickvals]

    fig.update_layout(
        height=560, margin=dict(l=0, r=52, t=8, b=8),
        xaxis_rangeslider_visible=False, xaxis2_rangeslider_visible=False,
        legend=dict(visible=False),
        hovermode="x unified",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        xaxis=dict(
            gridcolor="#f1f5f9", tickfont=dict(size=10, color="#94a3b8"),
            tickvals=_tickvals, ticktext=_ticktext,
            linecolor="#e2e8f0", zeroline=False,
        ),
        yaxis=dict(
            gridcolor="#f1f5f9", side="right",
            tickfont=dict(size=10, color="#94a3b8"), linecolor="#e2e8f0", zeroline=False,
        ),
        xaxis2=dict(
            gridcolor="#f1f5f9", tickfont=dict(size=9, color="#94a3b8"),
            linecolor="#e2e8f0", zeroline=False,
        ),
        yaxis2=dict(
            gridcolor="#f1f5f9", side="right",
            tickfont=dict(size=9, color="#94a3b8"), linecolor="#e2e8f0", zeroline=False,
        ),
        dragmode="pan",
        font=dict(family="Inter, 'PingFang SC', sans-serif", color="#475569"),
        hoverlabel=dict(
            bgcolor="#ffffff", bordercolor="#e2e8f0",
            font=dict(color="#1e293b", size=11),
        ),
    )
    # 日线去掉周末空档；分时图不加 rangebreaks（自然留空即可）
    if not is_intraday:
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat","mon"])])
    return fig

# ================= 期货品种搜索 =================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_futures_list() -> pd.DataFrame:
    """
    从东方财富获取国内期货全品种列表（含具体月份合约，如 JM2605）。
    返回 DataFrame，列: code, name, exchange
    """
    ex_map = {"113": "上期所", "114": "大商所", "115": "郑商所", "8": "中金所"}
    all_rows = []

    # 每个交易所单独请求，确保获取全部合约
    for ex_id, ex_name in ex_map.items():
        try:
            url = (
                f"https://push2.eastmoney.com/api/qt/clist/get"
                f"?pn=1&pz=1000&po=1&np=1"
                f"&ut=bd1d9ddb04089700cf9c27f6f7426281"
                f"&fltt=2&invt=2&fid=f3"
                f"&fs=m:{ex_id}"
                f"&fields=f12,f14,f13"
            )
            r = SESSION.get(url, timeout=10)
            r.raise_for_status()
            items = r.json().get("data", {}).get("diff", []) or []
            for item in items:
                code = str(item.get("f12", "")).strip()
                name = str(item.get("f14", "")).strip()
                if code and name:
                    all_rows.append({
                        "code":     code,
                        "name":     name,
                        "exchange": ex_name,
                        "label":    f"{code}  {name}（{ex_name}）",
                    })
        except Exception:
            continue

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows).drop_duplicates(subset="code")
    # 排序：主力合约（0结尾）排在前面，具体月份合约按代码排
    df["is_main"] = df["code"].str.match(r'^[A-Z]+0$')
    df = df.sort_values(["is_main", "code"], ascending=[False, True]).drop(columns="is_main")
    return df.reset_index(drop=True)

# ================= 标的中文名称查询 =================
@st.cache_data(ttl=600, show_spinner=False)
def get_stock_name(symbol: str, market: str) -> str:
    """返回标的的中文名称，失败时返回原代码"""
    try:
        if market == MARKET_FUTURES:
            fdf = fetch_futures_list()
            if not fdf.empty:
                match = fdf[fdf["code"] == symbol.strip().upper()]
                if not match.empty:
                    return match.iloc[0]["name"]
        elif market == MARKET_CN:
            pfx = "sh" if (int(symbol) >= 600000 or 500000 <= int(symbol) < 600000) else "sz"
            r = SESSION.get(f"https://qt.gtimg.cn/q={pfx}{symbol}", timeout=5)
            parts = r.text.split("~")
            if len(parts) > 1 and parts[1].strip():
                return parts[1].strip()
        elif market == MARKET_HK:
            sym = symbol.replace(".HK", "").zfill(5)
            r = SESSION.get(f"https://qt.gtimg.cn/q=hk{sym}", timeout=5)
            parts = r.text.split("~")
            if len(parts) > 1 and parts[1].strip():
                return parts[1].strip()
        elif market == MARKET_US:
            import yfinance as yf
            info = yf.Ticker(symbol.replace(".", "-").upper()).info
            return info.get("longName") or info.get("shortName") or symbol
    except Exception:
        pass
    return symbol

# ================= session_state 初始化（解决侧边栏双击 bug）=================
_MARKET_LIST = [MARKET_US, MARKET_CN, MARKET_HK, MARKET_FUTURES]
_DEFAULT_SYM  = {MARKET_US:"NVDA", MARKET_CN:"300308", MARKET_HK:"01810", MARKET_FUTURES:"AU0"}

import datetime as _dt
_today = _dt.date.today()

if "mkt"        not in st.session_state: st.session_state["mkt"]        = MARKET_US
if "sym"        not in st.session_state: st.session_state["sym"]        = _DEFAULT_SYM[MARKET_US]
if "sym_name"   not in st.session_state: st.session_state["sym_name"]   = ""
if "start_date" not in st.session_state: st.session_state["start_date"] = _today - _dt.timedelta(days=183)
if "end_date"   not in st.session_state: st.session_state["end_date"]   = _today
if "klt"        not in st.session_state: st.session_state["klt"]        = "101"
if "futures_df" not in st.session_state: st.session_state["futures_df"] = None
if "preset"     not in st.session_state: st.session_state["preset"]     = "半年"

_PRESET_OPTS = ["1年", "半年", "1季", "1月", "昨日", "今日"]
_PRESET_DAYS = {"1年": 365, "半年": 183, "1季": 91, "1月": 30, "昨日": 1, "今日": 0}


# ================= 侧边栏 =================
with st.sidebar:
    # ── 用户信息 + 退出 ─────────────────────────────────────
    username = st.session_state.get("username", "用户")
    _uid = str(abs(hash(username)) % 900 + 100)
    _display_name = f"用户{_uid}"
    _ucol, _lcol = st.columns([3, 1])
    with _ucol:
        st.markdown(
            f'<div class="user-card">'
            f'  <div class="user-avatar">禅</div>'
            f'  <div class="user-info">'
            f'    <div class="user-name">{_display_name}</div>'
            f'    <div class="user-role">PRO · QUANT</div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with _lcol:
        st.markdown('<div class="sb-logout">', unsafe_allow_html=True)
        if st.button("⏻", key="logout_btn", use_container_width=True, help="退出登录"):
            st.session_state["authenticated"] = False
            st.session_state["username"]      = ""
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        # user-card margin-bottom 对齐
        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
    st.markdown('<hr class="sb-divider">', unsafe_allow_html=True)

    market = st.selectbox(
        "市场选择",
        _MARKET_LIST,
        index=_MARKET_LIST.index(st.session_state["mkt"]),
    )
    # 切换市场 → 自动更新默认代码，避免旧代码残留导致 KeyError
    if market != st.session_state["mkt"]:
        st.session_state["mkt"] = market
        st.session_state["sym"] = _DEFAULT_SYM[market]
        st.rerun()

    # ── 期货：快捷搜索下拉 ──────────────────────────────────
    if market == MARKET_FUTURES:
        with st.spinner("加载期货品种列表..."):
            fdf = fetch_futures_list()

        if fdf.empty:
            # API 失败时退化为手动输入
            st.warning("⚠️ 期货列表加载失败，请手动输入代码")
            symbol = st.text_input(
                "合约代码",
                value=st.session_state["sym"],
                placeholder="如 RB0、AU0、IF0",
                help="主力合约以 0 结尾：RB0(螺纹钢) AU0(黄金) IF0(沪深300) M0(豆粕)",
            )
        else:
            # 搜索框过滤
            search_kw = st.text_input(
                "🔍 搜索品种",
                value="",
                placeholder="输入代码或名称，如 螺纹 / RB / 黄金",
            )
            if search_kw.strip():
                kw = search_kw.strip().upper()
                mask = (
                    fdf["code"].str.upper().str.contains(kw, na=False) |
                    fdf["name"].str.contains(search_kw.strip(), na=False) |
                    fdf["exchange"].str.contains(search_kw.strip(), na=False)
                )
                filtered = fdf[mask]
            else:
                filtered = fdf

            if filtered.empty:
                st.warning(f"未找到「{search_kw}」，请换个关键词或直接输入代码")
                symbol = st.text_input("手动输入代码", value=st.session_state["sym"])
            else:
                labels  = filtered["label"].tolist()
                codes   = filtered["code"].tolist()

                # 默认选中 session_state 里已有的品种
                default_idx = 0
                if st.session_state["sym"] in codes:
                    default_idx = codes.index(st.session_state["sym"])

                chosen = st.selectbox(
                    f"选择合约（共 {len(filtered)} 个）",
                    labels,
                    index=default_idx,
                )
                symbol = codes[labels.index(chosen)]
                # 保存中文名称到 session_state
                _row = filtered[filtered["code"] == symbol]
                if not _row.empty:
                    st.session_state["sym_name"] = _row.iloc[0]["name"]
                # 显示当前选中信息
                st.caption(f"📌 当前合约：**{symbol}**")

        if not symbol or not symbol.strip():
            st.error("⚠️ 请先选择或输入期货合约代码")
            symbol = st.session_state["sym"]

    # ── 非期货：普通文本输入 ────────────────────────────────
    else:
        symbol = st.text_input(
            "交易标的",
            value=st.session_state["sym"],
            help=(
                "A股: 000001  港股: 00700  美股: AAPL\n"
                "期货主力(0结尾): RB0(螺纹钢) AU0(黄金) IF0(沪深300) M0(豆粕)"
            ),
        )

    st.session_state["sym"] = symbol  # 同步，防 rerun 丢失

    klt = st.session_state["klt"]

    # ── 回测区间快捷按钮 ────────────────────────────────────
    _prev_preset = st.session_state["preset"]
    preset_label = st.radio(
        "回测区间",
        options=_PRESET_OPTS,
        index=_PRESET_OPTS.index(_prev_preset),
        horizontal=True,
    )
    if preset_label != _prev_preset:
        st.session_state["preset"] = preset_label
        _t = _dt.date.today()
        if preset_label in ("今日", "昨日"):
            _d = _t - _dt.timedelta(days=_PRESET_DAYS[preset_label])
            st.session_state["start_date"] = _d
            st.session_state["end_date"]   = _d
            st.session_state["klt"]        = "5"
        else:
            st.session_state["start_date"] = _t - _dt.timedelta(days=_PRESET_DAYS[preset_label])
            st.session_state["end_date"]   = _t
            st.session_state["klt"]        = "101"
        st.rerun()

    # ── 自定义日期 ──────────────────────────────────────────
    start_date = st.date_input("开始日期", key="start_date")
    end_date   = st.date_input("结束日期",  key="end_date")

    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
    run_btn = st.button("▶  执行推演", type="primary", use_container_width=True)

    st.markdown(
        '<div class="quote-box" style="margin-top:12px;">'
        '<div class="quote-title">// 缠师寄语</div>'
        '<div class="quote-text">'
        '"股票不是吃饭，一顿不吃就饿得慌。理论是让你心里不受贪婪恐惧影响……'
        '任何所谓的预测，都是闲谈，只有当下的走势。"'
        '</div></div>',
        unsafe_allow_html=True,
    )

# ================= 主界面 =================
_header_ph = st.empty()

def _render_header(code: str, name: str, mkt: str):
    if code:
        st.session_state["_hdr_code"] = code
        st.session_state["_hdr_name"] = name
        st.session_state["_hdr_mkt"]  = mkt

# 用上一次缓存先渲染
if st.session_state.get("sym_name"):
    _header_ph.markdown(
        f'<div style="padding:0.5rem 0 1rem;display:flex;align-items:center;gap:10px;">'
        f'<span style="font-family:\'DM Mono\',monospace;font-size:1.35rem;font-weight:500;color:#fff;letter-spacing:0.02em;">'
        f'{st.session_state.get("sym","")}</span>'
        f'<span style="font-size:0.9rem;color:#94a3b8;font-weight:400;">'
        f'{st.session_state.get("sym_name","")}</span>'
        f'<span style="font-family:\'DM Mono\',monospace;font-size:0.58rem;background:rgba(59,130,246,0.12);'
        f'color:#3b82f6;border:1px solid rgba(59,130,246,0.25);border-radius:4px;padding:2px 7px;letter-spacing:0.1em;text-transform:uppercase;">'
        f'{st.session_state.get("mkt","")}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
else:
    _header_ph.markdown(
        '<div class="sym-hint">在左侧面板输入交易标的，点击「执行推演」开始分析</div>',
        unsafe_allow_html=True,
    )

# ── 缠论理论知识面板（无分析数据时展示）──────────────────────
if not run_btn and not st.session_state.get("sym_name"):

    # 页眉
    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;padding-top:4px;">'
        '<div style="width:36px;height:36px;border-radius:9px;background:#dc2626;display:flex;'
        'align-items:center;justify-content:center;font-size:1rem;font-weight:800;color:#fff;'
        'flex-shrink:0;box-shadow:0 2px 8px rgba(220,38,38,0.3);">缠</div>'
        '<div><div style="font-size:1.05rem;font-weight:800;color:var(--text,#1e293b);">'
        '缠中说禅 · 理论体系</div>'
        '<div style="font-size:0.72rem;color:var(--text3,#94a3b8);margin-top:2px;">'
        '陈氏缠论 — 以数学严格性刻画市场分形结构，构建完全自洽的交易体系'
        '</div></div></div>',
        unsafe_allow_html=True,
    )

    # ── 核心公理 ──
    st.markdown("**📌 核心公理**")
    st.markdown(
        '<div class="theory-box"><b>公理一：</b>市场走势完全由K线组成。任何分析必须基于K线，而非主观预测。</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="theory-box"><b>公理二：</b>相邻K线之间处理包含关系后，不存在包含。有包含关系的K线须合并，形成"标准K线"。</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="theory-box"><b>公理三：走势终必完美。</b>任何级别的走势类型，必须由三段次级别走势完成。</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    # ── 结构推演层次 ──
    st.markdown("**🔗 结构推演层次**")
    steps = ["📊 原始K线", "🔧 包含处理", "🔺 顶底分型", "✏️ 笔", "📏 线段", "🔲 中枢", "📈 走势"]
    cols = st.columns(len(steps) * 2 - 1)
    for i, step in enumerate(steps):
        with cols[i * 2]:
            st.markdown(
                f'<div style="background:var(--bg3,#f1f5f9);border:1px solid var(--border,#e2e8f0);'
                f'border-radius:6px;padding:6px 4px;font-size:0.7rem;font-weight:600;'
                f'color:var(--text,#1e293b);text-align:center;">{step}</div>',
                unsafe_allow_html=True,
            )
        if i < len(steps) - 1:
            with cols[i * 2 + 1]:
                st.markdown(
                    '<div style="text-align:center;color:var(--text3,#94a3b8);'
                    'font-size:1rem;padding-top:4px;">→</div>',
                    unsafe_allow_html=True,
                )

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    # ── 六大核心概念 ──
    st.markdown("**📚 六大核心概念**")

    _CARD_STYLE = (
        "border-radius:10px;padding:14px 16px;height:100%;"
        "background:var(--bg2,#f8fafc);border:1px solid var(--border,#e2e8f0);"
        "border-top:3px solid {color};"
    )
    _TITLE_STYLE = "font-size:0.85rem;font-weight:700;color:var(--text,#1e293b);margin-bottom:8px;"
    _BODY_STYLE  = "font-size:0.78rem;color:var(--text2,#475569);line-height:1.8;"

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            f'<div style="{_CARD_STYLE.format(color="#3b82f6")}">'
            f'<div style="{_TITLE_STYLE}">🔧 包含关系处理</div>'
            f'<div style="{_BODY_STYLE}">'
            f'相邻两K线若存在<b>高低点完全包含</b>关系，须合并为一根"标准K线"。<br><br>'
            f'• 上升中：取两高点的<b>高值</b>、两低点的<b>高值</b><br>'
            f'• 下降中：取两高点的<b>低值</b>、两低点的<b>低值</b><br><br>'
            f'目的：消除噪声，还原真实走势结构。'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f'<div style="{_CARD_STYLE.format(color="#8b5cf6")}">'
            f'<div style="{_TITLE_STYLE}">🔺 顶底分型</div>'
            f'<div style="{_BODY_STYLE}">'
            f'由<b>三根相邻标准K线</b>构成的转折信号：<br><br>'
            f'<b>顶分型</b>：中间K线高点高于左右两侧<br>'
            f'<b>底分型</b>：中间K线低点低于左右两侧<br><br>'
            f'分型是笔的<b>起止点</b>，是判断趋势转折的最小单元，相邻分型间至少间隔1根K线。'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f'<div style="{_CARD_STYLE.format(color="#dc2626")}">'
            f'<div style="{_TITLE_STYLE}">✏️ 笔</div>'
            f'<div style="{_BODY_STYLE}">'
            f'连接一个<b>顶分型与底分型</b>（或反向）的价格运动：<br><br>'
            f'• 顶底之间至少有 <b>1 根独立K线</b><br>'
            f'• <b>上笔</b>：从底分型到顶分型（低→高）<br>'
            f'• <b>下笔</b>：从顶分型到底分型（高→低）<br><br>'
            f'笔是缠论最基础的<b>趋势单元</b>，构成更高级别结构的原料。'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
    c4, c5, c6 = st.columns(3)

    with c4:
        st.markdown(
            f'<div style="{_CARD_STYLE.format(color="#f59e0b")}">'
            f'<div style="{_TITLE_STYLE}">🔲 中枢</div>'
            f'<div style="{_BODY_STYLE}">'
            f'三段<b>连续次级别走势</b>的共同重叠区间：<br><br>'
            f'<b>ZG（中枢顶）</b>= 三段共同区间的最高点<br>'
            f'<b>ZD（中枢底）</b>= 三段共同区间的最低点<br><br>'
            f'• 价格在中枢内 → 震荡盘整<br>'
            f'• 价格站上 ZG → 多头离开中枢<br>'
            f'• 价格跌破 ZD → 空头离开中枢<br><br>'
            f'中枢是判断<b>趋势方向与强弱</b>的核心参照物。'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    with c5:
        st.markdown(
            f'<div style="{_CARD_STYLE.format(color="#10b981")}">'
            f'<div style="{_TITLE_STYLE}">📈 走势类型</div>'
            f'<div style="{_BODY_STYLE}">'
            f'任何走势都只有三种类型：<br><br>'
            f'<b>上涨</b>：多中枢，后中枢整体高于前中枢<br>'
            f'<b>下跌</b>：多中枢，后中枢整体低于前中枢<br>'
            f'<b>盘整</b>：所有中枢在同一价格区间内<br><br>'
            f'走势具有<b>分形自相似性</b>，同样的结构在日线、小时线、分钟线上均适用，可递归分析。'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    with c6:
        st.markdown(
            f'<div style="{_CARD_STYLE.format(color="#f43f5e")}">'
            f'<div style="{_TITLE_STYLE}">🎯 买卖点体系</div>'
            f'<div style="{_BODY_STYLE}">'
            f'<span style="background:rgba(16,185,129,0.12);color:#10b981;border:1px solid rgba(16,185,129,0.3);'
            f'border-radius:4px;padding:1px 6px;font-size:0.65rem;font-weight:700;">买1</span> '
            f'趋势下跌终结，最后中枢下方<b>底背驰</b>低点<br>'
            f'<span style="background:rgba(16,185,129,0.12);color:#10b981;border:1px solid rgba(16,185,129,0.3);'
            f'border-radius:4px;padding:1px 6px;font-size:0.65rem;font-weight:700;">买2</span> '
            f'回抽确认，下跌后回调不破前低<br>'
            f'<span style="background:rgba(16,185,129,0.12);color:#10b981;border:1px solid rgba(16,185,129,0.3);'
            f'border-radius:4px;padding:1px 6px;font-size:0.65rem;font-weight:700;">买3</span> '
            f'中枢震荡后<b>向上突破</b>时入场<br><br>'
            f'<span style="background:rgba(239,68,68,0.1);color:#ef4444;border:1px solid rgba(239,68,68,0.25);'
            f'border-radius:4px;padding:1px 6px;font-size:0.65rem;font-weight:700;">卖1</span> '
            f'趋势上涨终结，最后中枢上方<b>顶背驰</b>高点<br>'
            f'<span style="background:rgba(239,68,68,0.1);color:#ef4444;border:1px solid rgba(239,68,68,0.25);'
            f'border-radius:4px;padding:1px 6px;font-size:0.65rem;font-weight:700;">卖2</span> '
            f'回抽确认，上涨后回调不破前高<br>'
            f'<span style="background:rgba(239,68,68,0.1);color:#ef4444;border:1px solid rgba(239,68,68,0.25);'
            f'border-radius:4px;padding:1px 6px;font-size:0.65rem;font-weight:700;">卖3</span> '
            f'中枢震荡后<b>向下突破</b>时出场'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    # ── 背驰理论 ──
    st.markdown("**⚡ 背驰理论**")
    st.markdown(
        '<div class="theory-box">'
        '<b>背驰</b>是指价格创新高（低），但<b>对应的MACD柱子面积</b>却小于前一段走势的现象。'
        '背驰意味着走势动能衰竭，是趋势<b>即将反转</b>的重要信号。<br><br>'
        '· <b>盘整背驰</b>：发生在同一中枢内部，力度减弱但仍在震荡<br>'
        '· <b>趋势背驰</b>：发生在多中枢之间，预示更大级别的趋势反转<br><br>'
        '本系统自动识别MACD柱面积的相对收缩，辅助判断背驰信号。'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    # ── 缠师名言 ──
    st.markdown("**💬 缠师原文**")
    q1, q2 = st.columns(2)
    with q1:
        st.markdown(
            '<div class="quote-box"><div class="quote-title">// 论趋势</div>'
            '<div class="quote-text">"任何级别的趋势，都必然由三段以上的次级别走势构成，这是市场的铁律。"</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="quote-box"><div class="quote-title">// 论中枢</div>'
            '<div class="quote-text">"中枢是市场博弈的平衡区，所有的趋势都从中枢出发，也终将回归中枢。"</div></div>',
            unsafe_allow_html=True,
        )
    with q2:
        st.markdown(
            '<div class="quote-box"><div class="quote-title">// 论操作</div>'
            '<div class="quote-text">"操作永远只有一个原则：一切以当下走势为准，绝不预测，只做反应。"</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="quote-box"><div class="quote-title">// 论心态</div>'
            '<div class="quote-text">"理论是让你心里不受贪婪恐惧影响，能客观如实地面对当下走势。"</div></div>',
            unsafe_allow_html=True,
        )

if run_btn:
    if not symbol or not symbol.strip():
        st.warning("⚠️ 请先输入交易标的代码，再执行推演")
        st.stop()

    with st.spinner(f"正在分析 {symbol} 的几何结构与动力学特征..."):
        try:
            df_raw = fetch_stock_data(symbol, start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d"), market, klt)
            if df_raw is None or df_raw.empty:
                st.warning(f"⚠️ 未查询到「{symbol}」的行情数据，请检查代码格式或调整日期范围")
                st.stop()

            df_raw["date"] = pd.to_datetime(df_raw["date"])
            df = calc_macd(df_raw)

            _fetched_name = get_stock_name(symbol, market)
            st.session_state["sym_name"] = _fetched_name
            _render_header(symbol, _fetched_name, market)

            # 更新 header 占位符为设计稿风格
            _header_ph.markdown(
                f'<div style="padding:0.4rem 0 1rem;">'
                f'<span style="font-size:1.5rem;font-weight:800;color:#1e293b;">{symbol}</span> '
                f'<span style="font-size:1rem;color:#64748b;font-weight:500;">{_fetched_name}</span> '
                f'<span style="font-size:0.65rem;background:#f1f5f9;color:#94a3b8;'
                f'border-radius:4px;padding:2px 7px;font-weight:700;letter-spacing:0.05em;">'
                f'{market}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            std_klines    = process_inclusion(df.copy())
            all_fractals  = find_fractals(std_klines)
            valid_strokes = draw_strokes(all_fractals)
            hubs          = find_hubs(valid_strokes)
            buy_signals, sell_signals = analyze_signals(valid_strokes, hubs)
            df.set_index("date", inplace=True)

            cur  = df["close"].iloc[-1]
            prev = df["close"].iloc[-2] if len(df) >= 2 else cur
            pct  = (cur - prev) / prev * 100 if prev != 0 else 0.0
            currency = {"A股":"¥","港股":"HK$","美股":"$","国内期货":"点"}.get(market,"")

            hub_status, status_color = "震荡发育中", "#64748b"
            if hubs:
                lh = hubs[-1]
                if   cur > lh["ZG"]: hub_status, status_color = "多头脱离中枢", "#ef4444"
                elif cur < lh["ZD"]: hub_status, status_color = "空头脱离中枢", "#10b981"
                else:                hub_status, status_color = "深陷中枢泥潭", "#f59e0b"

            _pct_color  = "#dc2626" if pct >= 0 else "#10b981"
            _pct_bg     = "rgba(220,38,38,0.06)"  if pct >= 0 else "rgba(16,185,129,0.06)"
            _pct_border = "rgba(220,38,38,0.15)"  if pct >= 0 else "rgba(16,185,129,0.15)"
            _pct_arrow  = "▲" if pct >= 0 else "▼"

            # ── 指标看板（4卡片，修复颜色继承）────────────────────
            st.markdown(f"""
            <div class="metric-grid">
              <div class="metric-card">
                <div class="metric-sup">最新报价</div>
                <div class="metric-val" style="color:var(--text);">{currency}{cur:.2f}</div>
                <div class="metric-lbl">{_pct_arrow} {abs(pct):.2f}% 今日</div>
              </div>
              <div class="metric-card" style="background:{_pct_bg};">
                <div class="metric-sup">区间涨跌</div>
                <div class="metric-val" style="color:{_pct_color};">{pct:+.2f}%</div>
                <div class="metric-lbl">相对前收盘</div>
              </div>
              <div class="metric-card">
                <div class="metric-sup">结构定性</div>
                <div class="metric-val" style="color:{status_color};font-size:1.1rem;">{hub_status}</div>
                <div class="metric-lbl">当前走势状态</div>
              </div>
              <div class="metric-card">
                <div class="metric-sup">已识别中枢</div>
                <div class="metric-val" style="color:var(--text);">{len(hubs)}</div>
                <div class="metric-lbl">个走势中枢</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # ── 图表区（深色卡片）──────────────────────────────
            st.markdown(
                '<div class="chart-wrap">'
                '<div class="chart-topbar">'
                '<div class="chart-legend">'
                '  <div class="lg-item"><span class="lg-sq" style="background:#f43f5e;"></span><span class="lg-txt">K线</span></div>'
                '  <div class="lg-item"><span class="lg-ln" style="background:#3b82f6;"></span><span class="lg-txt">缠论笔</span></div>'
                '  <div class="lg-sep"></div>'
                '  <div class="lg-item"><span class="lg-dot" style="background:#f43f5e;"></span><span class="lg-txt">MACD</span></div>'
                '  <div class="lg-item"><span class="lg-dot" style="background:#3b82f6;"></span><span class="lg-txt">DIF</span></div>'
                '  <div class="lg-item"><span class="lg-dot" style="background:#475569;"></span><span class="lg-txt">DEA</span></div>'
                '</div>'
                '</div>'
                '<div class="chart-inner">',
                unsafe_allow_html=True,
            )
            plotly_fig = build_plotly_chart(df, valid_strokes, hubs, buy_signals, sell_signals, symbol, market, klt)
            st.plotly_chart(plotly_fig, use_container_width=True, config={
                "displayModeBar": False,
                "scrollZoom": True,
                "responsive": True,
            })
            st.markdown('</div></div>', unsafe_allow_html=True)

            # ── 底部分析区：Tab 切换 ────────────────────────────
            all_signals = sorted(buy_signals + sell_signals, key=lambda x: x['date'], reverse=True)
            _sig_count = len(all_signals)
            _tab_signal_label = f"买卖信号 ({_sig_count})" if _sig_count > 0 else "买卖信号"

            tab_stroke, tab_signals, tab_risk = st.tabs([
                "笔 · 中枢分析",
                _tab_signal_label,
                "风控止损",
            ])

            with tab_stroke:
                if not hubs:
                    latest_stroke  = "尚未形成笔" if not valid_strokes else ("↑ 向上笔" if valid_strokes[-1]["type"] == "bottom" else "↓ 向下笔")
                    st.markdown(f"""
                    <div class="ins-row"><span class="ins-lbl">最新笔状态</span><span class="ins-val" style="color:var(--text3);">{latest_stroke}</span></div>
                    <div class="ins-row"><span class="ins-lbl">买卖点预判</span><span class="ins-val" style="color:var(--amber);">等待中枢凝聚</span></div>
                    <div class="theory-box" style="margin-top:10px;">
                    <b>走势诊断：</b>目前尚未凝聚出【走势中枢】。<br>
                    中枢未成，多空双方连明确阵地都没有。<b>离场观望，等待中枢成形。</b>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    lh = hubs[-1]
                    latest_stroke = "↑ 向上笔延伸中" if valid_strokes and valid_strokes[-1]["type"] == "bottom" else "↓ 向下笔延伸中"
                    _stroke_color = "#f43f5e" if "↑" in latest_stroke else "#10b981"
                    if cur > lh["ZG"]:
                        signal_preview, sig_color = "寻找三类买点", "#f43f5e"
                        theory_html = f"""<div class="theory-box" style="border-color:var(--red);">
                        <b>多头进攻态势：</b>价格 {currency}{cur:.2f} 越过中枢上沿 ZG {lh['ZG']:.2f}。<br>
                        回调不跌回 <b>{lh['ZG']:.2f}</b> → <b>【三类买点】</b>确立，主升浪信号！
                        </div>"""
                    elif cur < lh["ZD"]:
                        signal_preview, sig_color = "警惕三类卖点", "#10b981"
                        theory_html = f"""<div class="theory-box" style="border-color:var(--green);">
                        <b>空头屠杀警戒：</b>价格 {currency}{cur:.2f} 跌穿中枢下沿 ZD {lh['ZD']:.2f}。<br>
                        反弹无法触及 <b>{lh['ZD']:.2f}</b> → <b>【三类卖点】</b>，坚决清仓！
                        </div>"""
                    else:
                        signal_preview, sig_color = "中枢震荡观望", "#f59e0b"
                        theory_html = f"""<div class="theory-box">
                        <b>绞肉机模式：</b>价格困于 [{lh['ZD']:.2f} ↔ {lh['ZG']:.2f}]。<br>
                        大级别操作者：<b>中枢震荡 = 垃圾时间，喝茶观望。</b>
                        </div>"""
                    st.markdown(f"""
                    <div class="ins-row"><span class="ins-lbl">最新笔状态</span><span class="ins-val" style="color:{_stroke_color};">{latest_stroke}</span></div>
                    <div class="ins-row"><span class="ins-lbl">中枢区间</span><span class="ins-val" style="color:var(--amber);font-family:var(--mono);">{lh['ZD']:.2f} — {lh['ZG']:.2f}</span></div>
                    <div class="ins-row"><span class="ins-lbl">买卖点预判</span><span class="ins-val" style="color:{sig_color};">{signal_preview}</span></div>
                    {theory_html}
                    """, unsafe_allow_html=True)

            with tab_signals:
                if not all_signals:
                    st.markdown(
                        '<div class="empty-state">'
                        '<div class="empty-icon">◎</div>'
                        '<div class="empty-title">当前区间无触发信号</div>'
                        '<div class="empty-desc">缠论买卖点尚未在此区间形成<br>可尝试拉长回测区间或切换周期</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    for sig in all_signals[:5]:
                        is_buy = "买" in sig["type"]
                        color  = "#f43f5e" if is_buy else "#10b981"
                        arrow  = "▲" if is_buy else "▼"
                        theory = "多头反击确立。" if is_buy else "空头主导确认。"
                        if "一" in sig["type"]:   theory = "MACD 动力衰竭，底背驰信号。买点总在下跌中形成。"
                        if "三买" in sig["type"]: theory = "回抽不破中枢最高点，主升浪确立！"
                        if "三卖" in sig["type"]: theory = "反弹不碰中枢最低点，大跌在即，立即离场！"
                        st.markdown(f"""
                        <div class="sig-card" style="border-left-color:{color};">
                          <div class="sig-meta">{sig['date'].strftime('%Y-%m-%d')} · 触发 {currency}{sig['price']:.2f}</div>
                          <div class="sig-title" style="color:{color};">{arrow} {sig['type']}</div>
                          <div class="sig-desc">{theory}</div>
                        </div>""", unsafe_allow_html=True)

            with tab_risk:
                stop_loss_5  = cur * 0.95
                stop_loss_3  = cur * 0.97
                risk_color   = "#f43f5e" if pct >= 0 else "#10b981"
                if hubs:
                    lh = hubs[-1]
                    key_support  = lh["ZD"]
                    key_resist   = lh["ZG"]
                    hub_advice = f"当前价格{'高于' if cur > lh['ZG'] else '低于' if cur < lh['ZD'] else '处于'}中枢区间"
                else:
                    key_support = cur * 0.93
                    key_resist  = cur * 1.07
                    hub_advice  = "中枢尚未成型，以技术位估算"
                st.markdown(f"""
                <div class="ins-row"><span class="ins-lbl">当前价格</span><span class="ins-val" style="color:#fff;font-family:var(--mono);">{currency}{cur:.2f}</span></div>
                <div class="ins-row"><span class="ins-lbl">止损参考 (−3%)</span><span class="ins-val" style="color:var(--red);font-family:var(--mono);">{currency}{stop_loss_3:.2f}</span></div>
                <div class="ins-row"><span class="ins-lbl">止损参考 (−5%)</span><span class="ins-val" style="color:var(--red);font-family:var(--mono);">{currency}{stop_loss_5:.2f}</span></div>
                <div class="ins-row"><span class="ins-lbl">关键支撑位</span><span class="ins-val" style="color:var(--green);font-family:var(--mono);">{currency}{key_support:.2f}</span></div>
                <div class="ins-row"><span class="ins-lbl">关键阻力位</span><span class="ins-val" style="color:var(--amber);font-family:var(--mono);">{currency}{key_resist:.2f}</span></div>
                <div class="theory-box" style="margin-top:10px;">
                <b>风控提示：</b>{hub_advice}。<br>
                当前波动率 {abs(pct):.2f}%，严禁在中枢未成型时重仓操作。
                仓位建议：趋势明确时不超过 50%，震荡阶段不超过 30%。
                </div>
                """, unsafe_allow_html=True)

        except ValueError as e:
            st.warning(f"⚠️ 未查询到数据：{e}")
        except Exception as e:
            st.error(f"⚠️ 查询失败，请检查代码格式或网络连接（{type(e).__name__}）")