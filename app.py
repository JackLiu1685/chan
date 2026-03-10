import os
import urllib.request
import time, json, re
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

# ================= 页面样式设置 =================
st.set_page_config(
    page_title="缠论AI解盘终端",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={}   # 清空右上角菜单，避免显示部署等选项
)

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

/* 布局 */
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
    sym = symbol.replace(".HK", "").zfill(5)
    sd  = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
    ed  = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
    raw = SESSION.get(f"https://web.ifzq.gtimg.cn/appstock/app/hkfqkline/get?param=hk{sym},day,{sd},{ed},640,qfq", timeout=15).json().get("data", {}).get(f"hk{sym}", {}).get("qfqday", [])
    if not raw: raise ValueError("港股接口返回空数据")
    df = pd.DataFrame([{"date": pd.to_datetime(r[0]), "open": float(r[1]), "close": float(r[2]), "high": float(r[3]), "low": float(r[4])} for r in raw])
    return df[(df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))].reset_index(drop=True)

def fetch_us(symbol, start_date, end_date):
    import yfinance as yf, datetime
    sd  = datetime.datetime.strptime(start_date, "%Y%m%d").strftime("%Y-%m-%d")
    ed  = (datetime.datetime.strptime(end_date,   "%Y%m%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    raw = yf.Ticker(symbol.replace(".", "-").upper()).history(start=sd, end=ed, interval="1d", auto_adjust=True).reset_index()
    if raw.empty: raise ValueError("美股接口返回空数据")
    raw["Date"] = pd.to_datetime(raw["Date"]).dt.tz_localize(None)
    df = pd.DataFrame({"date": raw["Date"], "open": raw["Open"], "high": raw["High"], "low": raw["Low"], "close": raw["Close"]})
    return df[df["close"] > 0].reset_index(drop=True)

def fetch_stock_data(symbol, start_date, end_date, market):
    if market == MARKET_FUTURES: return fetch_futures(symbol, start_date, end_date)
    if market == MARKET_CN:      return fetch_cn(symbol, start_date, end_date)
    elif market == MARKET_HK:    return fetch_hk(symbol, start_date, end_date)
    elif market == MARKET_US:    return fetch_us(symbol, start_date, end_date)

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
def build_plotly_chart(df, valid_strokes, hubs, buy_signals, sell_signals, symbol, market):
    currency = {"A股":"¥","港股":"HK$","美股":"$","国内期货":"点"}.get(market,"")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75,0.25])

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="K线", increasing_line_color="#ef4444", decreasing_line_color="#10b981",
        increasing_fillcolor="#ef4444", decreasing_fillcolor="#10b981",
        hoverinfo="text",
        hovertext=[f"{d.strftime('%Y-%m-%d')}<br>收:{c:.2f}" for d,c in zip(df.index, df.close)]
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
        height=600, margin=dict(l=20,r=80,t=10,b=10),
        xaxis_rangeslider_visible=False, xaxis2_rangeslider_visible=False,
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="left",x=0),
        hovermode="x unified", plot_bgcolor="#fff", paper_bgcolor="#fff",
        xaxis=dict(gridcolor="#f1f5f9"), yaxis=dict(gridcolor="#f1f5f9",side="right"),
        xaxis2=dict(gridcolor="#f1f5f9"), yaxis2=dict(gridcolor="#f1f5f9",side="right"),
    )
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat","mon"])])
    return fig

# ================= session_state 初始化（解决侧边栏双击 bug）=================
_MARKET_LIST = [MARKET_US, MARKET_CN, MARKET_HK, MARKET_FUTURES]
_DEFAULT_SYM  = {MARKET_US:"EDU", MARKET_CN:"000001", MARKET_HK:"00700", MARKET_FUTURES:"RB0"}

if "mkt" not in st.session_state: st.session_state["mkt"] = MARKET_US
if "sym" not in st.session_state: st.session_state["sym"] = _DEFAULT_SYM[MARKET_US]

# ================= 侧边栏 =================
with st.sidebar:
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
        st.rerun()  # 强制刷新，保证 text_input 立刻显示新默认值

    symbol = st.text_input(
        "交易标的",
        value=st.session_state["sym"],
        help=(
            "A股: 000001  港股: 00700  美股: AAPL\n"
            "期货主力(0结尾): RB0(螺纹钢) AU0(黄金) IF0(沪深300) M0(豆粕) CU0(铜)"
        ),
    )
    st.session_state["sym"] = symbol  # 同步输入，防 rerun 丢失

    start_date = st.date_input("开始日期", value=pd.to_datetime("2025-06-01"))
    end_date   = st.date_input("结束日期",  value=pd.to_datetime("today"))

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
if run_btn:
    with st.spinner(f"正在分析 {symbol} 的几何结构与动力学特征..."):
        try:
            df_raw = fetch_stock_data(symbol, start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d"), market)
            df_raw["date"] = pd.to_datetime(df_raw["date"])
            df = calc_macd(df_raw)

            std_klines    = process_inclusion(df.copy())
            all_fractals  = find_fractals(std_klines)
            valid_strokes = draw_strokes(all_fractals)
            hubs          = find_hubs(valid_strokes)
            buy_signals, sell_signals = analyze_signals(valid_strokes, hubs)
            df.set_index("date", inplace=True)

            cur  = df["close"].iloc[-1]
            prev = df["close"].iloc[-2]
            pct  = (cur - prev) / prev * 100
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

            plotly_fig = build_plotly_chart(df, valid_strokes, hubs, buy_signals, sell_signals, symbol, market)
            st.plotly_chart(plotly_fig, use_container_width=True, config={"displayModeBar": False})

            col_left, col_right = st.columns([5.5, 4.5])

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

        except Exception as e:
            st.error(f"分析异常：{e}")
            st.exception(e)