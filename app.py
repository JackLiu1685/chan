import os
import urllib.request
import time, json, re
import requests
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ================= 环境与网络配置 =================
for var in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"]:
    os.environ.pop(var, None)
os.environ["no_proxy"] = "*"
os.environ["NO_PROXY"] = "*"
urllib.request.getproxies = lambda: {}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ================= 页面样式设置 (UI 优化版) =================
# 默认展开侧边栏，采用宽屏模式
st.set_page_config(page_title="缠论AI解盘终端", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
/* 全局字体优化 */
html, body, [class*="css"], .stMarkdown, p, div, span, label, button {
    font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif !important;
}
/* 顶边距收缩，最大化利用屏幕 */
.block-container { padding-top: 2rem !important; padding-bottom: 1rem !important; }

/* 核心指标卡片样式优化 */
.metric-container { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem; }
.metric-card { 
    background: #ffffff; border: 1px solid #e0e6ed; border-radius: 10px; 
    padding: 1rem; flex: 1; min-width: 120px; text-align: center;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02); transition: transform 0.2s;
}
.metric-card:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.05); }
.metric-value { font-size: 1.4rem; font-weight: 700; color: #1e293b; margin-bottom: 0.2rem; }
.metric-label { font-size: 0.8rem; color: #64748b; font-weight: 500; }

/* 模块标题美化 */
.section-title { font-size: 1.2rem; font-weight: bold; color: #0f172a; border-left: 4px solid #3b82f6; padding-left: 0.5rem; margin: 1.5rem 0 1rem 0; }
.lesson-card { background-color: #f8fafc; padding: 1rem; border-radius: 8px; border-left: 4px solid #10b981; margin-bottom: 0.5rem; font-size: 0.9rem;}
</style>
""", unsafe_allow_html=True)

# ================= 数据获取模块 =================
MARKET_CN, MARKET_HK, MARKET_US = "A股", "港股", "美股"

def detect_market(symbol: str) -> str:
    s = symbol.strip().upper()
    if s.endswith(".HK"): return MARKET_HK
    if re.fullmatch(r"\d{6}", s): return MARKET_CN
    if re.fullmatch(r"\d{1,5}", s): return MARKET_HK
    if re.search(r"[A-Z]", s): return MARKET_US
    return MARKET_CN

def normalize_symbol(symbol: str, market: str) -> str:
    s = symbol.strip().upper()
    if market == MARKET_HK: s = s.replace(".HK", "").zfill(5)
    if market == MARKET_US: s = s.replace(".", "-")
    return s

def _cn_prefix(symbol): return "sh" if (int(symbol) >= 600000 or 500000 <= int(symbol) < 600000) else "sz"

def fetch_cn(symbol, start_date, end_date):
    full = f"{_cn_prefix(symbol)}{symbol}"
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={full},day,{start_date[:4]}-{start_date[4:6]}-{start_date[6:]},{end_date[:4]}-{end_date[4:6]}-{end_date[6:]},640,qfq"
    resp = SESSION.get(url, headers={**HEADERS, "Referer":"https://gu.qq.com/"}, timeout=15)
    raw = resp.json().get("data", {}).get(full, {}).get("qfqday") or resp.json().get("data", {}).get(full, {}).get("day", [])
    if not raw: raise ValueError("腾讯接口返回空数据，请检查代码")
    df = pd.DataFrame([{"date": pd.to_datetime(r[0]), "open": float(r[1]), "close": float(r[2]), "high": float(r[3]), "low": float(r[4])} for r in raw])
    return df[(df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))].reset_index(drop=True)

def fetch_hk(symbol, start_date, end_date):
    full = f"hk{symbol}"
    sd, ed = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}", f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
    url = f"https://web.ifzq.gtimg.cn/appstock/app/hkfqkline/get?param={full},day,{sd},{ed},640,qfq"
    resp = SESSION.get(url, headers={**HEADERS, "Referer":"https://gu.qq.com/"}, timeout=15)
    raw = resp.json().get("data", {}).get(full, {}).get("qfqday") or resp.json().get("data", {}).get(full, {}).get("day", [])
    if not raw:
        raw = SESSION.get(f"https://web.ifzq.gtimg.cn/appstock/app/kline/get?param={full},day,{sd},{ed},640", headers={**HEADERS}).json().get("data", {}).get(full, {}).get("day", [])
    if not raw: raise ValueError("未获取到港股数据")
    df = pd.DataFrame([{"date": pd.to_datetime(r[0]), "open": float(r[1]), "close": float(r[2]), "high": float(r[3]), "low": float(r[4])} for r in raw])
    return df[(df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))].reset_index(drop=True)

def fetch_us(symbol, start_date, end_date):
    try: import yfinance as yf
    except ImportError: raise ImportError("请先安装 yfinance")
    import datetime
    sd = datetime.datetime.strptime(start_date, "%Y%m%d").strftime("%Y-%m-%d")
    ed = (datetime.datetime.strptime(end_date, "%Y%m%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    raw = yf.Ticker(symbol.upper()).history(start=sd, end=ed, interval="1d", auto_adjust=True)
    if raw.empty: raise ValueError("未获取到美股数据")
    raw = raw.reset_index()
    raw["Date"] = pd.to_datetime(raw["Date"]).dt.tz_localize(None)
    df = pd.DataFrame({"date": raw["Date"], "open": raw["Open"].astype(float).round(4), "high": raw["High"].astype(float).round(4), "low": raw["Low"].astype(float).round(4), "close": raw["Close"].astype(float).round(4)})
    return df[df["close"] > 0].reset_index(drop=True)

def fetch_stock_data(symbol, start_date, end_date, market):
    sym = normalize_symbol(symbol, market)
    if market == MARKET_CN: return fetch_cn(sym, start_date, end_date)
    elif market == MARKET_HK: return fetch_hk(sym, start_date, end_date)
    elif market == MARKET_US: return fetch_us(sym, start_date, end_date)

# ================= 缠论核心计算 =================
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
        if c["high"]>p["high"] and c["high"]>n["high"] and c["low"]>p["low"] and c["low"]>n["low"]: out.append({"type":"top","index":i,"kline":c})
        elif c["low"]<p["low"] and c["low"]<n["low"] and c["high"]<p["high"] and c["high"]<n["high"]: out.append({"type":"bottom","index":i,"kline":c})
    return out

def draw_strokes(fractals):
    if not fractals: return []
    strokes, cand = [], fractals[0]
    for i in range(1, len(fractals)):
        cur = fractals[i]
        if cur["type"] == cand["type"]:
            if cur["type"]=="top" and cur["kline"]["high"]>cand["kline"]["high"]: cand=cur
            if cur["type"]=="bottom" and cur["kline"]["low"]<cand["kline"]["low"]: cand=cur
            continue
        if cur["index"]-cand["index"] >= 4:
            cand["end_index"]=cur["index"]; strokes.append(cand); cand=cur
    strokes.append(cand)
    return strokes

def find_hubs(vs):
    for s in vs: s["price"] = s["kline"]["high"] if s["type"]=="top" else s["kline"]["low"]
    hubs, i = [], 0
    while i < len(vs)-3:
        s1,s2,s3,s4 = vs[i],vs[i+1],vs[i+2],vs[i+3]
        ZG, ZD = min(max(s1["price"],s2["price"]),max(s2["price"],s3["price"]),max(s3["price"],s4["price"])), max(min(s1["price"],s2["price"]),min(s2["price"],s3["price"]),min(s3["price"],s4["price"]))
        if ZG > ZD:
            sdt, edt, j = pd.to_datetime(s1["kline"]["date"]), pd.to_datetime(s4["kline"]["date"]), i+3
            while j < len(vs)-1:
                if min(vs[j]["price"],vs[j+1]["price"]) > ZG or max(vs[j]["price"],vs[j+1]["price"]) < ZD: break
                edt=pd.to_datetime(vs[j+1]["kline"]["date"]); j+=1
            hubs.append({"ZG":ZG,"ZD":ZD,"start_dt":sdt,"end_dt":edt,"start_idx":i,"end_idx":j})
            i=j
        else: i+=1
    return hubs

def calc_macd(df):
    df=df.copy()
    df["EMA12"] = df["close"].ewm(span=12,adjust=False).mean()
    df["EMA26"] = df["close"].ewm(span=26,adjust=False).mean()
    df["DIF"] = df["EMA12"]-df["EMA26"]
    df["DEA"] = df["DIF"].ewm(span=9,adjust=False).mean()
    df["MACD"] = (df["DIF"]-df["DEA"])*2
    return df

def analyze_signals(vs, hubs):
    buy_s, sell_s = [], []
    if not hubs or len(vs)<4: return buy_s, sell_s
    lh=hubs[-1]; ZG,ZD=lh["ZG"],lh["ZD"]
    for i in range(lh["end_idx"], len(vs)-1):
        sl,sr = vs[i],vs[i+1]
        dt,rp = pd.to_datetime(sr["kline"]["date"]),sr["price"]
        
        if sl["type"]=="bottom" and sl["price"]>ZG and sr["type"]=="top" and rp>ZG:
            buy_s.append({"date":dt,"price":rp,"type":"第三类买点","desc":"回调不破中枢上沿(ZG)，主升浪确认。"})
        if sl["type"]=="top" and sl["price"]<ZD and sr["type"]=="bottom" and rp<ZD:
            sell_s.append({"date":dt,"price":rp,"type":"第三类卖点","desc":"反弹不碰中枢下沿(ZD)，主跌浪确认。"})
        if sr["type"]=="top" and rp<ZD:
            es=vs[lh["start_idx"]]
            if (sl["price"]-rp)<(es["kline"]["high"]-es["kline"]["low"]):
                buy_s.append({"date":dt,"price":rp*0.98,"type":"第一类买点","desc":"底背驰：创新低但下跌力度明显减弱。"})
    return buy_s, sell_s

# ================= 可视化渲染 (解决重叠与美化) =================
def build_plotly_chart(df, all_fractals, valid_strokes, hubs, buy_signals, sell_signals, symbol, market):
    currency = {"A股": "¥", "港股": "HK$", "美股": "$"}.get(market, "")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])

    # 1. K线图
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="K线", increasing_line_color="#ef4444", decreasing_line_color="#10b981",
        increasing_fillcolor="#ef4444", decreasing_fillcolor="#10b981",
        hoverinfo="text", hovertext=[f"{d.strftime('%Y-%m-%d')}<br>开:{o:.2f} 收:{c:.2f}<br>高:{h:.2f} 低:{l:.2f}" for d,o,c,h,l in zip(df.index, df.open, df.close, df.high, df.low)]
    ), row=1, col=1)

    # 2. 缠论笔
    stroke_x = [pd.to_datetime(s["kline"]["date"]) for s in valid_strokes if pd.to_datetime(s["kline"]["date"]) in df.index]
    stroke_y = [s["price"] for s in valid_strokes if pd.to_datetime(s["kline"]["date"]) in df.index]
    fig.add_trace(go.Scatter(
        x=stroke_x, y=stroke_y, mode="lines+markers", name="缠论笔",
        line=dict(color="#3b82f6", width=2), marker=dict(size=4, color="#3b82f6"),
        hovertemplate="%{x|%Y-%m-%d}<br>转折点: %{y:.2f}<extra></extra>",
    ), row=1, col=1)

    # 3. 缠论中枢 (增加右侧偏移和白底防重叠)
    for hub in hubs:
        x0, x1 = hub["start_dt"], hub["end_dt"]
        zd, zg = hub["ZD"], hub["ZG"]
        fig.add_shape(type="rect", xref="x", yref="y", x0=x0, y0=zd, x1=x1, y1=zg, line=dict(color="#f59e0b", width=1.5), fillcolor="rgba(245,158,11,0.1)", row=1, col=1)
        
        # 文本加入白底，并通过 xshift 偏移，避免和 K 线缠在一起
        fig.add_annotation(
            x=x1, y=zg, text=f"ZG: {zg:.2f}", showarrow=False, 
            xanchor="left", xshift=5, bgcolor="rgba(255,255,255,0.75)",
            font=dict(size=10, color="#d97706"), row=1, col=1
        )
        fig.add_annotation(
            x=x1, y=zd, text=f"ZD: {zd:.2f}", showarrow=False, 
            xanchor="left", xshift=5, bgcolor="rgba(255,255,255,0.75)",
            font=dict(size=10, color="#d97706"), row=1, col=1
        )

    # 4. 买卖点信号 (优化文字位置)
    if buy_signals:
        bx = [b["date"] for b in buy_signals if b["date"] in df.index]
        by = [b["price"] * 0.96 for b in buy_signals if b["date"] in df.index]
        bt = [b["type"] for b in buy_signals if b["date"] in df.index]
        fig.add_trace(go.Scatter(
            x=bx, y=by, mode="markers+text", name="买点", marker=dict(symbol="triangle-up", size=12, color="#ef4444"),
            text=bt, textposition="bottom center", textfont=dict(size=10, color="#ef4444"), hoverinfo="skip"
        ), row=1, col=1)

    if sell_signals:
        sx = [s["date"] for s in sell_signals if s["date"] in df.index]
        sy = [s["price"] * 1.04 for s in sell_signals if s["date"] in df.index]
        st2 = [s["type"] for s in sell_signals if s["date"] in df.index]
        fig.add_trace(go.Scatter(
            x=sx, y=sy, mode="markers+text", name="卖点", marker=dict(symbol="triangle-down", size=12, color="#10b981"),
            text=st2, textposition="top center", textfont=dict(size=10, color="#10b981"), hoverinfo="skip"
        ), row=1, col=1)

    # 5. MACD 副图
    macd_colors = ["#ef4444" if v >= 0 else "#10b981" for v in df["MACD"]]
    fig.add_trace(go.Bar(x=df.index, y=df["MACD"], name="MACD", marker_color=macd_colors, opacity=0.8), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["DIF"], name="DIF", line=dict(color="#f43f5e", width=1)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["DEA"], name="DEA", line=dict(color="#3b82f6", width=1)), row=2, col=1)

    # 整体布局优化 (去除内部大标题以节省空间，交由 Streamlit 显示)
    fig.update_layout(
        height=650, 
        margin=dict(l=40, r=60, t=20, b=10), # 扩大右侧边距给文字留空间，缩小顶部边距
        xaxis_rangeslider_visible=False, xaxis2_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=12)),
        hovermode="x unified", plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        xaxis=dict(gridcolor="#f1f5f9", showgrid=True), yaxis=dict(gridcolor="#f1f5f9", showgrid=True, side="right"),
        xaxis2=dict(gridcolor="#f1f5f9", showgrid=True), yaxis2=dict(gridcolor="#f1f5f9", showgrid=True, side="right"),
    )
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    return fig

# ================= UI 侧边栏结构 =================
with st.sidebar:
    st.markdown("### ⚙️ 控制面板")
    
    market = st.selectbox("选择市场", [MARKET_CN, MARKET_HK, MARKET_US], index=2) # 默认选中美股
    
    # 动态默认代码逻辑
    default_symbol = "000001"
    if market == MARKET_HK: default_symbol = "00700"
    elif market == MARKET_US: default_symbol = "EDU"
    
    symbol = st.text_input("股票代码", value=default_symbol)
    
    # 修改默认开始日期为 2025年6月1日
    start_date = st.date_input("开始日期", value=pd.to_datetime("2025-06-01"))
    end_date = st.date_input("结束日期", value=pd.to_datetime("today"))
    
    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button("🚀 开始推演", type="primary", use_container_width=True)
    
    st.divider()
    st.markdown("#### 📖 缠论操作口诀")
    st.info("• 买点总在下跌中形成\n\n• 卖点总在上涨中形成\n\n• 中枢震荡，多看少动\n\n• 突破回踩不进框，三买确立")

# ================= 主界面数据展台 =================
if run_btn:
    detected = detect_market(symbol)
    if detected != market:
        st.toast(f"提示：您输入的代码似乎是 {detected}，当前在 {market} 下获取。", icon="ℹ️")

    with st.spinner(f"正在从云端拉取 {symbol} 数据进行结构推演..."):
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

            # 1. 顶部核心指标看板
            st.markdown(f'<div class="section-title">📊 {symbol.upper()} 核心数据</div>', unsafe_allow_html=True)
            cur, prev = df["close"].iloc[-1], df["close"].iloc[-2]
            pct = (cur-prev)/prev*100
            currency = {"A股":"¥","港股":"HK$","美股":"$"}.get(market,"")
            
            # 判断当前在中枢的什么位置
            hub_status = "暂无"
            status_color = "#64748b"
            if hubs:
                lh = hubs[-1]
                if cur > lh["ZG"]: hub_status = "强势突破"; status_color = "#ef4444"
                elif cur < lh["ZD"]: hub_status = "弱势破位"; status_color = "#10b981"
                else: hub_status = "中枢震荡"; status_color = "#f59e0b"

            st.markdown(f"""
            <div class="metric-container">
              <div class="metric-card"><div class="metric-value">{currency}{cur:.2f}</div><div class="metric-label">最新收盘价</div></div>
              <div class="metric-card"><div class="metric-value" style="color:{'#ef4444' if pct>=0 else '#10b981'}">{pct:+.2f}%</div><div class="metric-label">最近涨跌幅</div></div>
              <div class="metric-card"><div class="metric-value" style="color:{status_color}">{hub_status}</div><div class="metric-label">当前形态判定</div></div>
              <div class="metric-card"><div class="metric-value">{len(valid_strokes)} 笔</div><div class="metric-label">已走完结构</div></div>
            </div>
            """, unsafe_allow_html=True)

            # 2. 沉浸式图表区
            plotly_fig = build_plotly_chart(df, all_fractals, valid_strokes, hubs, buy_signals, sell_signals, symbol, market)
            st.plotly_chart(plotly_fig, use_container_width=True, config={"displayModeBar": False, "scrollZoom": True})

            # 3. 底部 AI 解盘与复盘分栏布局
            col1, col2 = st.columns([6, 4])
            
            with col1:
                st.markdown('<div class="section-title">👨‍🏫 AI 智能解盘</div>', unsafe_allow_html=True)
                if not hubs:
                    st.info("当前时间段内未能形成重叠的三个走势段，尚未构建出有效的【中枢】结构，请等待走势充分发育。")
                else:
                    lh = hubs[-1]
                    if cur > lh["ZG"]:
                        st.success(f"**多头主导**：价格已冲破核心中枢 [{lh['ZD']:.2f} ↔ {lh['ZG']:.2f}] 上沿。\n\n**🎯 策略**：重点观察回踩动作，只要回调不跌破 **{lh['ZG']:.2f}**，即可确立【第三类买点】，预示着新的主升浪。")
                    elif cur < lh["ZD"]:
                        st.error(f"**空头主导**：价格跌穿中枢 [{lh['ZD']:.2f} ↔ {lh['ZG']:.2f}] 下沿。\n\n**🎯 策略**：必须提高警惕，若反弹无力触碰 **{lh['ZD']:.2f}**，将确立【第三类卖点】，建议减仓或离场避险。")
                    else:
                        st.warning(f"**多空僵持**：价格陷于 [{lh['ZD']:.2f} ↔ {lh['ZG']:.2f}] 之间。\n\n**🎯 策略**：经典的“中枢震荡”行情。适合空仓观望，或依托上下沿进行轻仓的“高抛低吸”操作。")

            with col2:
                st.markdown('<div class="section-title">📡 历史信号雷达</div>', unsafe_allow_html=True)
                all_signals = sorted(buy_signals + sell_signals, key=lambda x: x['date'], reverse=True)
                if not all_signals:
                    st.write("📈 当前视窗内未捕获到经典买卖点。")
                else:
                    # 仅展示最近的3个信号保持版面整洁
                    for sig in all_signals[:3]:
                        color = "#ef4444" if "买" in sig["type"] else "#10b981"
                        icon = "🔴" if "买" in sig["type"] else "🟢"
                        st.markdown(f"""
                        <div style="border-left: 4px solid {color}; padding: 10px; background: #f8fafc; margin-bottom: 8px; border-radius: 4px;">
                            <strong>{icon} {sig['date'].strftime('%Y-%m-%d')}</strong> | {currency}{sig['price']:.2f}<br>
                            <span style="color: {color}; font-weight: bold;">{sig['type']}</span>：{sig['desc']}
                        </div>
                        """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"网络请求或分析过程中发生异常，请稍后重试。")
            st.exception(e)