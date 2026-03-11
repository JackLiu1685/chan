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
    initial_sidebar_state="collapsed",
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
    """渲染登录页面，验证通过后设置 session_state"""
    st.markdown("""
    <style>
    /* 登录页全屏居中 */
    [data-testid="stAppViewContainer"] > .main {
        display: flex; align-items: center; justify-content: center;
    }
    .login-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 2.5rem 3rem;
        width: 100%;
        max-width: 420px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.08);
        margin: 8vh auto;
    }
    .login-title {
        font-size: 1.6rem;
        font-weight: 800;
        color: #0f172a;
        text-align: center;
        margin-bottom: 0.3rem;
    }
    .login-sub {
        font-size: 0.85rem;
        color: #64748b;
        text-align: center;
        margin-bottom: 2rem;
    }
    /* 移动端登录页适配 */
    @media (max-width: 768px) {
        .login-card {
            padding: 1.5rem 1.2rem;
            margin: 3vh auto;
            border-radius: 12px;
        }
        .login-title { font-size: 1.3rem; }
        /* 防止 iOS Safari 自动缩放输入框 */
        input[type="password"], input[type="text"] { font-size: 16px !important; }
    }
    </style>
    """, unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([0.5, 3, 0.5])
    with col_c:
        st.markdown('<div class="login-title">📈 缠论AI解盘终端</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">请输入管理员分配给您的访问密钥（非哈希值）</div>', unsafe_allow_html=True)

        key_input = st.text_input(
            "访问密钥",
            type="password",
            placeholder="输入收到的密钥，如 WiikPwpHGrOgkuqx",
            label_visibility="collapsed",
        )

        login_btn = st.button("🔓 验证并进入", type="primary", use_container_width=True)

        if login_btn:
            if not key_input.strip():
                st.error("⚠️ 请输入密钥")
            elif _hash(key_input) in VALID_KEY_HASHES.values():
                st.session_state["authenticated"] = True
                # 记录是哪个用户登录的
                for name, h in VALID_KEY_HASHES.items():
                    if h == _hash(key_input):
                        st.session_state["username"] = name
                        break
                st.rerun()
            else:
                st.error("❌ 密钥错误，请联系管理员获取访问权限")

        st.markdown(
            '<div style="text-align:center;margin-top:1.5rem;font-size:0.75rem;color:#94a3b8;">'
            '密钥由管理员分配 · 请勿泄露给他人'
            '</div>',
            unsafe_allow_html=True,
        )

# ================= 登录拦截 =================
if not check_auth():
    login_page()
    st.stop()

st.markdown("""
<style>
/* 只做最安全的隐藏：visibility 而非 display:none，不触碰 header */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stDeployButton"] { visibility: hidden; }
/* 隐藏右上角"部署"按钮（新版 Streamlit） */
[data-testid="stToolbarActionButton"],
[data-testid="manage-app-button"],
.stDeployButton { visibility: hidden; width: 0; }

/* 侧边栏箭头图标乱码修复 */
[data-testid="stSidebarCollapseButton"] button > span { font-size: 0; color: transparent; }
[data-testid="stSidebarCollapseButton"] button::after { content: "◀"; font-size: 14px; color: #888; }
[data-testid="collapsedControl"] button > span { font-size: 0; color: transparent; }
[data-testid="collapsedControl"] button::after { content: "▶"; font-size: 14px; color: #888; }

/* 布局 - 桌面端 */
.block-container { padding-top: 3.5rem !important; padding-bottom: 1rem !important; padding-left: 2rem !important; padding-right: 2rem !important; }
[data-testid="stSidebar"] { padding-top: 1rem !important; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.2rem !important; }

/* 指标卡片 */
.metric-container { display: flex; gap: 0.8rem; flex-wrap: wrap; margin-bottom: 1rem; }
.metric-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.8rem; flex: 1; min-width: 100px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.metric-value { font-size: 1.25rem; font-weight: 700; color: #1e293b; margin-bottom: 0.1rem; }
.metric-label { font-size: 0.75rem; color: #64748b; font-weight: 500; }
.section-title { font-size: 1.1rem; font-weight: bold; color: #0f172a; border-left: 4px solid #3b82f6; padding-left: 0.5rem; margin: 1rem 0 0.8rem 0; }
.chan-theory-box { background-color: #f8fafc; border-left: 4px solid #f59e0b; padding: 12px; border-radius: 6px; margin-bottom: 10px; font-size: 0.9rem; color: #334155; line-height: 1.5; }
.sym-header { display:flex; align-items:center; gap:0.6rem; padding:0.5rem 0.2rem 0.8rem; border-bottom:1px solid #e2e8f0; margin-bottom:0.8rem; }
.sym-code { font-size:1rem; font-weight:700; color:#64748b; background:#f1f5f9; border-radius:6px; padding:2px 8px; }
.sym-name { font-size:1.15rem; font-weight:800; color:#0f172a; }
.sym-market { font-size:0.75rem; color:#94a3b8; background:#f8fafc; border:1px solid #e2e8f0; border-radius:4px; padding:2px 6px; }
.sym-hint { font-size:0.9rem; color:#94a3b8; padding:0.5rem 0.2rem 0.8rem; border-bottom:1px solid #f1f5f9; margin-bottom:0.8rem; }
/* 快捷区间容器 */
.preset-wrap { border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px; background: #f8fafc; margin-bottom: 4px; }
.preset-label { font-size: 0.75rem; color: #94a3b8; margin-bottom: 6px; letter-spacing: 0.03em; }
/* 快捷区间按钮紧凑样式 */
[data-testid="stSidebar"] button[kind="secondary"] { padding: 0.15rem 0 !important; font-size: 0.8rem !important; min-height: 1.7rem !important; border-radius: 6px !important; }

/* ========== 移动端适配 ========== */
@media (max-width: 768px) {
    /* 收窄主区域 padding，给内容留更多空间 */
    .block-container {
        padding-top: 2.5rem !important;
        padding-left: 0.6rem !important;
        padding-right: 0.6rem !important;
        padding-bottom: 1rem !important;
    }

    /* 侧边栏在移动端减少内边距 */
    [data-testid="stSidebar"] .block-container {
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }

    /* 双列布局强制堆叠为单列 */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }

    /* 指标卡片在手机上 2x2 排列 */
    .metric-card {
        min-width: calc(50% - 0.4rem);
        padding: 0.6rem 0.4rem;
    }
    .metric-value { font-size: 1rem; }
    .metric-label { font-size: 0.7rem; }

    /* 标题字号缩小 */
    .section-title { font-size: 0.95rem; }
    .chan-theory-box { font-size: 0.85rem; padding: 10px; }

    /* 防止 iOS Safari 输入框自动缩放（需 font-size >= 16px）*/
    input, select, textarea { font-size: 16px !important; }

    /* 信号卡片更紧凑 */
    [data-testid="stMarkdownContainer"] div[style*="border-left"] {
        padding: 8px !important;
    }
}

@media (max-width: 480px) {
    /* 超小屏（iPhone SE 等）进一步缩减 */
    .metric-container { gap: 0.5rem; }
    .metric-card { padding: 0.5rem 0.3rem; }
    .metric-value { font-size: 0.9rem; }
    .chan-theory-box { font-size: 0.8rem; }
}
</style>
""", unsafe_allow_html=True)

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

    fig.update_layout(
        height=520, margin=dict(l=10,r=60,t=10,b=10),
        xaxis_rangeslider_visible=False, xaxis2_rangeslider_visible=False,
        legend=dict(
            orientation="h", xanchor="left", x=0.01,
            yanchor="top", y=0.99,
            bgcolor="rgba(255,255,255,0.75)",
            bordercolor="#e2e8f0", borderwidth=1,
            font=dict(size=10), tracegroupgap=2,
        ),
        hovermode="x unified", plot_bgcolor="#fff", paper_bgcolor="#fff",
        xaxis=dict(gridcolor="#f1f5f9"), yaxis=dict(gridcolor="#f1f5f9",side="right"),
        xaxis2=dict(gridcolor="#f1f5f9"), yaxis2=dict(gridcolor="#f1f5f9",side="right"),
        dragmode="pan",
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

_KLT_MAP = {"日K": "101", "60分": "60", "30分": "30", "15分": "15", "5分": "5"}

# ================= 侧边栏 =================
with st.sidebar:
    # 顶部：当前用户 + 退出按钮
    username = st.session_state.get("username", "用户")
    col_u, col_out = st.columns([3, 1])
    with col_u:
        st.markdown(
            f'<div style="font-size:0.8rem;color:#64748b;padding-top:4px;">🔐 {username}</div>',
            unsafe_allow_html=True,
        )
    with col_out:
        if st.button("退出", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state["username"] = ""
            st.rerun()

    st.markdown("### ⚙️ 交易终端参数")

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

    # ── K线周期选择 ───────────────────────────────────────
    st.markdown('<div style="font-size:0.8rem;color:#64748b;margin:6px 0 3px;">📊 K线周期</div>', unsafe_allow_html=True)
    _klt_cols = st.columns(5)
    for _kc, (_kl, _kv) in zip(_klt_cols, _KLT_MAP.items()):
        with _kc:
            _active = st.session_state["klt"] == _kv
            if st.button(_kl, key=f"klt_{_kv}",
                         use_container_width=True,
                         type="primary" if _active else "secondary"):
                st.session_state["klt"] = _kv
                st.rerun()
    klt = st.session_state["klt"]

    # ── 快捷区间（3×2 网格）────────────────────────────────
    st.markdown('<div class="preset-wrap"><div class="preset-label">⚡ 快捷区间</div>', unsafe_allow_html=True)
    _row1 = st.columns(3)
    _row2 = st.columns(3)
    _presets = [
        ("今日",  0,   True),   # (label, days, is_single_day)
        ("昨日",  1,   True),
        ("1月",   30,  False),
        ("1季",   91,  False),
        ("半年",  183, False),
        ("1年",   365, False),
    ]
    for _col, (_ql, _qd, _single) in zip(_row1 + _row2, _presets):
        with _col:
            if st.button(_ql, key=f"preset_{_ql}", use_container_width=True):
                _t = _dt.date.today()
                if _single:
                    _s = _t - _dt.timedelta(days=_qd)
                    st.session_state["start_date"] = _s
                    st.session_state["end_date"]   = _s
                else:
                    st.session_state["start_date"] = _t - _dt.timedelta(days=_qd)
                    st.session_state["end_date"]   = _t
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    start_date = st.date_input("开始日期", key="start_date")
    end_date   = st.date_input("结束日期",  key="end_date")

    st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)
    run_btn = st.button("🚀 执行推演", type="primary", use_container_width=True)

    st.divider()
    st.markdown("##### 💡 缠师寄语")
    st.caption(
        "\"股票不是吃饭，一顿不吃就饿得慌。"
        "理论是让你心里不受贪婪恐惧影响……"
        "任何所谓的预测，都是闲谈，只有当下的走势。\""
    )

# ================= 主界面 =================
# 顶部标题栏（用占位符，分析完成后可即时更新）
_header_ph = st.empty()

def _render_header(code: str, name: str, mkt: str):
    if name:
        _header_ph.markdown(
            f'<div class="sym-header">'
            f'<span class="sym-code">{code}</span>'
            f'<span class="sym-name">{name}</span>'
            f'<span class="sym-market">{mkt}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        _header_ph.markdown(
            '<div class="sym-hint">← 请点击左上角 ≫ 展开参数面板，选择标的后点击「执行推演」</div>',
            unsafe_allow_html=True,
        )

# 用上一次缓存的名称先渲染（首次为提示语）
_render_header(
    st.session_state.get("sym", ""),
    st.session_state.get("sym_name", ""),
    st.session_state.get("mkt", ""),
)

if run_btn:
    # ── 空输入校验 ──────────────────────────────────────────
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

            # 获取中文名称并立即更新顶部标题
            _fetched_name = get_stock_name(symbol, market)
            st.session_state["sym_name"] = _fetched_name
            _render_header(symbol, _fetched_name, market)

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

            st.markdown(f"""
            <div class="metric-container">
              <div class="metric-card"><div class="metric-value">{currency}{cur:.2f}</div><div class="metric-label">最新报价</div></div>
              <div class="metric-card"><div class="metric-value" style="color:{'#ef4444' if pct>=0 else '#10b981'}">{pct:+.2f}%</div><div class="metric-label">区间变动</div></div>
              <div class="metric-card"><div class="metric-value" style="color:{status_color}">{hub_status}</div><div class="metric-label">当下结构定性</div></div>
              <div class="metric-card"><div class="metric-value">{len(hubs)} 个</div><div class="metric-label">已查明中枢战壕</div></div>
            </div>
            """, unsafe_allow_html=True)

            plotly_fig = build_plotly_chart(df, valid_strokes, hubs, buy_signals, sell_signals, symbol, market, klt)
            st.plotly_chart(plotly_fig, use_container_width=True, config={
                "displayModeBar": False,
                "scrollZoom": True,
                "responsive": True,
            })

            col_left, col_right = st.columns([5.5, 4.5], gap="medium")

            with col_left:
                st.markdown('<div class="section-title">📖 缠中说禅：当下走势的哲学解剖</div>', unsafe_allow_html=True)
                if not hubs:
                    st.markdown("""<div class="chan-theory-box">
                    <b>🔍 走势诊断：</b><br>目前尚未凝聚出<b>【走势中枢】</b>。<br><br>
                    <b>💡 缠师原话：</b><i>"任何级别的任何走势类型终要完成。"</i><br>
                    中枢未成，多空双方连明确阵地都没有。此时最佳策略：<b>离场观望，等待中枢成形。</b>
                    </div>""", unsafe_allow_html=True)
                else:
                    lh = hubs[-1]
                    if cur > lh["ZG"]:
                        st.markdown(f"""<div class="chan-theory-box" style="border-color:#ef4444;">
                        <b>🟢 多头进攻态势：</b><br>价格 {cur:.2f} 强势越过中枢上沿 ZG {lh['ZG']:.2f}。<br><br>
                        <b>💡 缠论推演：</b>突破后若出现回调，只要最低点<b>不跌回 {lh['ZG']:.2f} 以内</b>，
                        即构成<b>【第三类买点】</b>——主升浪确立信号！
                        </div>""", unsafe_allow_html=True)
                    elif cur < lh["ZD"]:
                        st.markdown(f"""<div class="chan-theory-box" style="border-color:#10b981;">
                        <b>🔴 空头屠杀警戒：</b><br>价格 {cur:.2f} 已跌穿中枢下沿 ZD {lh['ZD']:.2f}。<br><br>
                        <b>💡 缠论推演：</b>若随后反弹<b>无法触及 {lh['ZD']:.2f}</b>，
                        即形成<b>【第三类卖点】</b>——坚决清仓，君子不立危墙之下！
                        </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f"""<div class="chan-theory-box">
                        <b>🟡 绞肉机模式：</b><br>价格困于中枢 [{lh['ZD']:.2f} ↔ {lh['ZG']:.2f}]。<br><br>
                        <b>💡 缠论推演：</b><i>"在盘整中，绝对不能小看小级别的背驰。"</i><br>
                        大级别操作者：<b>中枢震荡 = 垃圾时间，喝茶观望。</b>
                        </div>""", unsafe_allow_html=True)

            with col_right:
                st.markdown('<div class="section-title">⚡ 异动信号捕获</div>', unsafe_allow_html=True)
                all_signals = sorted(buy_signals + sell_signals, key=lambda x: x['date'], reverse=True)
                if not all_signals:
                    st.info("当前区间内未触发经典买卖点。无聊的走势需要无聊的等待。")
                else:
                    for sig in all_signals[:3]:
                        is_buy = "买" in sig["type"]
                        color  = "#ef4444" if is_buy else "#10b981"
                        icon   = "🔺" if is_buy else "🔻"
                        theory = "多头反击确立。" if is_buy else "空头肆虐确认。"
                        if "一" in sig["type"]:   theory = "MACD 动力衰竭，底背驰信号！买点总在下跌中形成。"
                        if "三买" in sig["type"]: theory = "回抽不破中枢最高点，主升浪正式确立！"
                        if "三卖" in sig["type"]: theory = "反弹不碰中枢最低点，瀑布即将倾泻，立即离场！"
                        st.markdown(f"""
                        <div style="border-left:3px solid {color};padding:10px;background:#fff;border:1px solid #e2e8f0;margin-bottom:10px;border-radius:4px;">
                            <span style="font-size:0.85rem;color:#64748b;">{sig['date'].strftime('%Y-%m-%d')} | 触发价: {currency}{sig['price']:.2f}</span><br>
                            <strong style="color:{color};font-size:1.05rem;">{icon} 发现{sig['type']}</strong><br>
                            <span style="font-size:0.85rem;color:#475569;"><b>底层逻辑：</b>{theory}</span>
                        </div>""", unsafe_allow_html=True)

        except ValueError as e:
            st.warning(f"⚠️ 未查询到数据：{e}")
        except Exception as e:
            st.error(f"⚠️ 查询失败，请检查代码格式或网络连接（{type(e).__name__}）")