import json
import io
import numpy as np
import pandas as pd
import streamlit as st
from typing import Dict, List, Tuple

from head_shoulders import find_hs_patterns
from flags_pennants import find_flags_pennants_trendline
from harmonic_patterns import find_xabcd, ALL_PATTERNS
from directional_change import get_extremes, directional_change
from mp_support_resist import support_resistance_levels
from trendline_automation import fit_trendlines_high_low
from perceptually_important import find_pips


st.set_page_config(
    page_title="Advanced Pattern Detection System",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======================= CSS STYLING =======================

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2ecc71;
        text-align: center;
        margin-bottom: 1rem;
    }
    .stat-box {
        background-color: #1e1e1e;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2ecc71;
    }
    .pattern-count {
        font-size: 2rem;
        font-weight: bold;
        color: #2ecc71;
    }
    .pattern-label {
        color: #888;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


# ======================= DATA LOADER =======================

@st.cache_data(show_spinner=False)
def load_ohlc(csv_path=None, file_bytes=None) -> pd.DataFrame:
    """Load OHLC data from CSV file or uploaded bytes"""
    if file_bytes is not None:
        df = pd.read_csv(io.BytesIO(file_bytes))
    elif csv_path:
        df = pd.read_csv(csv_path)
    else:
        raise ValueError("csv_path veya file_bytes gerekli.")

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    df = df.sort_index()
    return df


@st.cache_data(show_spinner=False)
def detect_all_patterns(
    csv_path=None,
    file_bytes=None,
    hs_order: int = 6,
    flag_order: int = 10,
    sigma: float = 0.02,
    err_thresh: float = 0.5,
    sr_lookback: int = 365,
    trend_lookback: int = 30
):
    """Detect all patterns and features"""

    ohlc = load_ohlc(csv_path=csv_path, file_bytes=file_bytes)

    # Log version for patterns
    ohlc_log = ohlc.copy()
    for col in ["open", "high", "low", "close"]:
        ohlc_log[col] = np.log(ohlc_log[col])

    log_close = ohlc_log["close"].to_numpy()

    # --- Head & Shoulders ---
    hs_patterns, ihs_patterns = find_hs_patterns(
        log_close,
        order=hs_order,
        early_find=False
    )

    # --- Flags & Pennants ---
    bull_flags, bear_flags, bull_pennants, bear_pennants = \
        find_flags_pennants_trendline(log_close, flag_order)

    # --- Harmonic Patterns ---
    data_ext = ohlc.copy()
    data_ext["r"] = np.log(data_ext["close"]).diff().shift(-1)
    extremes = get_extremes(data_ext, sigma)
    harmonic_output = find_xabcd(data_ext, extremes, err_thresh)

    # --- Support & Resistance Levels ---
    sr_levels = None
    if len(ohlc) >= sr_lookback:
        sr_levels = support_resistance_levels(
            ohlc,
            lookback=sr_lookback,
            first_w=0.1,
            atr_mult=3.0,
            prom_thresh=0.25
        )

    # --- Trend Lines ---
    trend_lines = []
    if len(ohlc) >= trend_lookback:
        for i in range(trend_lookback - 1, len(ohlc)):
            candles = ohlc_log.iloc[i - trend_lookback + 1: i + 1]
            try:
                support_coefs, resist_coefs = fit_trendlines_high_low(
                    candles['high'].to_numpy(),
                    candles['low'].to_numpy(),
                    candles['close'].to_numpy()
                )
                trend_lines.append({
                    'index': i,
                    'support_slope': support_coefs[0],
                    'support_intercept': support_coefs[1],
                    'resist_slope': resist_coefs[0],
                    'resist_intercept': resist_coefs[1]
                })
            except:
                pass

    # --- Directional Change (multiple sigma levels) ---
    dc_levels = {}
    for sig in [0.01, 0.02, 0.03]:
        tops, bottoms = directional_change(
            ohlc['close'].to_numpy(),
            ohlc['high'].to_numpy(),
            ohlc['low'].to_numpy(),
            sig
        )
        dc_levels[sig] = {'tops': tops, 'bottoms': bottoms}

    return {
        "ohlc": ohlc,
        "ohlc_log": ohlc_log,
        "hs": hs_patterns,
        "ihs": ihs_patterns,
        "bull_flags": bull_flags,
        "bear_flags": bear_flags,
        "bull_pennants": bull_pennants,
        "bear_pennants": bear_pennants,
        "harmonics": harmonic_output,
        "sr_levels": sr_levels,
        "trend_lines": trend_lines,
        "dc_levels": dc_levels,
        "extremes": extremes
    }


# ======================= HELPERS =======================

def filter_patterns(patterns, start_attr: str, min_start: int, max_count: int):
    """Filter patterns by start index and limit count"""
    if not patterns:
        return []
    filtered = [p for p in patterns if getattr(p, start_attr) >= min_start]
    filtered.sort(key=lambda p: getattr(p, start_attr))
    if max_count > 0 and len(filtered) > max_count:
        filtered = filtered[-max_count:]
    return filtered


def exp_if_log(x):
    """Convert log price back to linear"""
    return float(np.exp(x))


def build_pattern_overlays(result, start_idx: int, ohlc: pd.DataFrame, show_lines: bool = True):
    """Build pattern overlay lines for TradingView chart"""

    index = ohlc.index
    overlays = []

    if not show_lines:
        return overlays

    # ========== HARMONIC PATTERNS XABCD Lines ==========
    h_out = result["harmonics"]
    for pattern_name, info in h_out.items():
        # Bull patterns (green)
        for p in info["bull_patterns"]:
            if p.X < start_idx:
                continue
            try:
                close = ohlc["close"].to_numpy()
                overlays.append({
                    "type": "line",
                    "color": "#2ecc71",
                    "width": 2,
                    "points": [
                        {"time": int(index[p.X].timestamp()), "price": float(close[p.X])},
                        {"time": int(index[p.A].timestamp()), "price": float(close[p.A])},
                    ],
                    "label": pattern_name
                })
                overlays.append({
                    "type": "line",
                    "color": "#2ecc71",
                    "width": 2,
                    "points": [
                        {"time": int(index[p.A].timestamp()), "price": float(close[p.A])},
                        {"time": int(index[p.B].timestamp()), "price": float(close[p.B])},
                    ]
                })
                overlays.append({
                    "type": "line",
                    "color": "#2ecc71",
                    "width": 2,
                    "points": [
                        {"time": int(index[p.B].timestamp()), "price": float(close[p.B])},
                        {"time": int(index[p.C].timestamp()), "price": float(close[p.C])},
                    ]
                })
                overlays.append({
                    "type": "line",
                    "color": "#2ecc71",
                    "width": 2,
                    "points": [
                        {"time": int(index[p.C].timestamp()), "price": float(close[p.C])},
                        {"time": int(index[p.D].timestamp()), "price": float(close[p.D])},
                    ]
                })
            except:
                pass

        # Bear patterns (red)
        for p in info["bear_patterns"]:
            if p.X < start_idx:
                continue
            try:
                close = ohlc["close"].to_numpy()
                overlays.append({
                    "type": "line",
                    "color": "#e74c3c",
                    "width": 2,
                    "points": [
                        {"time": int(index[p.X].timestamp()), "price": float(close[p.X])},
                        {"time": int(index[p.A].timestamp()), "price": float(close[p.A])},
                    ],
                    "label": pattern_name
                })
                overlays.append({
                    "type": "line",
                    "color": "#e74c3c",
                    "width": 2,
                    "points": [
                        {"time": int(index[p.A].timestamp()), "price": float(close[p.A])},
                        {"time": int(index[p.B].timestamp()), "price": float(close[p.B])},
                    ]
                })
                overlays.append({
                    "type": "line",
                    "color": "#e74c3c",
                    "width": 2,
                    "points": [
                        {"time": int(index[p.B].timestamp()), "price": float(close[p.B])},
                        {"time": int(index[p.C].timestamp()), "price": float(close[p.C])},
                    ]
                })
                overlays.append({
                    "type": "line",
                    "color": "#e74c3c",
                    "width": 2,
                    "points": [
                        {"time": int(index[p.C].timestamp()), "price": float(close[p.C])},
                        {"time": int(index[p.D].timestamp()), "price": float(close[p.D])},
                    ]
                })
            except:
                pass

    return overlays


def build_signals_from_patterns(
    result,
    start_idx: int,
    max_per_type: int,
    ohlc: pd.DataFrame
):
    """Build entry/stop/tp signals for all patterns"""

    index = ohlc.index
    close = ohlc["close"].to_numpy()
    signals = []

    # ========== Head & Shoulders (Short) ==========
    for pat in filter_patterns(result["hs"], "start_i", start_idx, max_per_type):
        try:
            t_break = index[pat.break_i]
            entry_price = exp_if_log(pat.neck_end)
            stop_price = exp_if_log(pat.head_p)
            risk = stop_price - entry_price
            tp1_price = entry_price - risk

            signals.append({
                "time": int(t_break.timestamp()),
                "side": "short",
                "pattern": "H&S",
                "entry": entry_price,
                "stop": stop_price,
                "tp1": tp1_price,
            })
        except:
            pass

    # ========== Inverse Head & Shoulders (Long) ==========
    for pat in filter_patterns(result["ihs"], "start_i", start_idx, max_per_type):
        try:
            t_break = index[pat.break_i]
            entry_price = exp_if_log(pat.neck_end)
            stop_price = exp_if_log(pat.head_p)
            risk = entry_price - stop_price
            tp1_price = entry_price + risk

            signals.append({
                "time": int(t_break.timestamp()),
                "side": "long",
                "pattern": "Inverse H&S",
                "entry": entry_price,
                "stop": stop_price,
                "tp1": tp1_price,
            })
        except:
            pass

    # ========== Flags & Pennants ==========
    def add_flag_signals(pats, label, side):
        for p in filter_patterns(pats, "base_x", start_idx, max_per_type):
            try:
                t_conf = index[p.conf_x]
                entry_price = exp_if_log(p.conf_y)
                stop_price = exp_if_log(p.base_y)

                if side == "long":
                    risk = entry_price - stop_price
                    tp1_price = entry_price + risk
                else:
                    risk = stop_price - entry_price
                    tp1_price = entry_price - risk

                signals.append({
                    "time": int(t_conf.timestamp()),
                    "side": side,
                    "pattern": label,
                    "entry": entry_price,
                    "stop": stop_price,
                    "tp1": tp1_price,
                })
            except:
                pass

    add_flag_signals(result["bull_flags"], "Bull Flag", "long")
    add_flag_signals(result["bear_flags"], "Bear Flag", "short")
    add_flag_signals(result["bull_pennants"], "Bull Pennant", "long")
    add_flag_signals(result["bear_pennants"], "Bear Pennant", "short")

    # ========== Harmonic Patterns ==========
    h_out = result["harmonics"]
    for name, info in h_out.items():
        # Bull patterns
        for p in info["bull_patterns"]:
            if p.D < start_idx:
                continue
            try:
                t_D = index[p.D]
                entry_price = close[p.D]
                stop_price = close[p.X] if p.X < len(close) else entry_price * 0.98
                risk = entry_price - stop_price
                if risk <= 0:
                    continue
                tp1_price = entry_price + risk

                signals.append({
                    "time": int(t_D.timestamp()),
                    "side": "long",
                    "pattern": f"{name} (Bull)",
                    "entry": float(entry_price),
                    "stop": float(stop_price),
                    "tp1": float(tp1_price),
                })
            except:
                pass

        # Bear patterns
        for p in info["bear_patterns"]:
            if p.D < start_idx:
                continue
            try:
                t_D = index[p.D]
                entry_price = close[p.D]
                stop_price = close[p.X] if p.X < len(close) else entry_price * 1.02
                risk = stop_price - entry_price
                if risk <= 0:
                    continue
                tp1_price = entry_price - risk

                signals.append({
                    "time": t_D.isoformat(),
                    "side": "short",
                    "pattern": f"{name} (Bear)",
                    "entry": float(entry_price),
                    "stop": float(stop_price),
                    "tp1": float(tp1_price),
                })
            except:
                pass

    return signals


def ohlc_to_lw_data(ohlc_view: pd.DataFrame):
    """Convert OHLC dataframe to Lightweight Charts format"""
    data = []
    for t, row in ohlc_view.iterrows():
        # Use Unix timestamp for TradingView compatibility
        if isinstance(t, pd.Timestamp):
            time_value = int(t.timestamp())
        elif hasattr(t, 'timestamp'):
            time_value = int(t.timestamp())
        else:
            time_value = int(pd.Timestamp('2023-01-01').timestamp()) + (len(data) * 3600)

        data.append({
            "time": time_value,
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        })
    return data


def build_sr_levels(result, start_idx: int, ohlc: pd.DataFrame):
    """Build support/resistance level lines"""
    sr_lines = []

    if result["sr_levels"] is None:
        return sr_lines

    index = ohlc.index

    # Get SR levels for the last visible candle
    if len(result["sr_levels"]) > start_idx:
        last_levels = result["sr_levels"][-1]
        if last_levels:
            for level in last_levels:
                sr_lines.append({
                    "price": float(level),
                    "color": "#3498db",
                    "width": 1,
                    "style": 2  # dashed
                })

    return sr_lines


# ======================= SIDEBAR =======================

st.sidebar.markdown("## 📊 Veri Kaynağı")

data_source = st.sidebar.radio(
    "Kaynak seç",
    ["📁 Dosya Yolu", "📤 CSV Yükle"],
    index=0
)

csv_path = None
uploaded_file = None

if data_source == "📁 Dosya Yolu":
    csv_path = st.sidebar.text_input("CSV dosya yolu", "BTCUSDT3600.csv")
else:
    uploaded_file = st.sidebar.file_uploader("CSV dosyası seç", type=["csv"])

st.sidebar.markdown("---")
st.sidebar.markdown("## ⚙️ Genel Ayarlar")

lookback = st.sidebar.slider(
    "Görüntülenecek mum sayısı",
    min_value=200,
    max_value=5000,
    value=1000,
    step=100
)

max_per_type = st.sidebar.slider(
    "Pattern başına max sinyal",
    min_value=1,
    max_value=50,
    value=10
)

show_pattern_lines = st.sidebar.checkbox("Pattern çizgilerini göster", True)
show_sr_levels = st.sidebar.checkbox("Support/Resistance göster", True)

st.sidebar.markdown("---")
st.sidebar.markdown("## 🎯 Pattern Ayarları")

with st.sidebar.expander("📈 Head & Shoulders", expanded=True):
    enable_hs = st.checkbox("Aktif et", True, key="hs_enable")
    hs_order = st.slider("Order", 1, 20, 6, key="hs_order")

with st.sidebar.expander("🚩 Flags & Pennants", expanded=True):
    enable_flags = st.checkbox("Aktif et", True, key="flags_enable")
    flag_order = st.slider("Order", 3, 20, 10, key="flag_order")

with st.sidebar.expander("🎵 Harmonic Patterns", expanded=False):
    enable_harmonics = st.checkbox("Aktif et", True, key="harm_enable")
    sigma = st.slider("DC Sigma", 0.005, 0.05, 0.02, step=0.005, key="sigma")
    err_thresh = st.slider("Hata eşiği", 0.1, 1.0, 0.5, step=0.05, key="err")

    selected_harmonics = st.multiselect(
        "Harmonic tipler",
        options=[p.name for p in ALL_PATTERNS],
        default=["Gartley", "Bat", "Butterfly"],
    )

with st.sidebar.expander("📊 Support/Resistance", expanded=False):
    sr_lookback = st.slider("Lookback period", 50, 500, 365, key="sr_lb")

with st.sidebar.expander("📉 Trend Lines", expanded=False):
    trend_lookback = st.slider("Lookback period", 10, 100, 30, key="trend_lb")

# ======================= MAIN UI =======================

st.markdown('<div class="main-header">🎯 Advanced Pattern Detection System</div>', unsafe_allow_html=True)

# --- Load & Detect ---

if data_source == "📁 Dosya Yolu":
    if not csv_path:
        st.error("❌ CSV dosya yolu giriniz.")
        st.stop()
    file_bytes = None
else:
    if uploaded_file is None:
        st.warning("⚠️ CSV dosyası yükleyiniz.")
        st.stop()
    file_bytes = uploaded_file.getvalue()
    csv_path = None

with st.spinner("🔍 Pattern'ler tespit ediliyor..."):
    try:
        result = detect_all_patterns(
            csv_path=csv_path,
            file_bytes=file_bytes,
            hs_order=hs_order,
            flag_order=flag_order,
            sigma=sigma,
            err_thresh=err_thresh,
            sr_lookback=sr_lookback,
            trend_lookback=trend_lookback,
        )
    except Exception as e:
        st.error(f"❌ Hata: {e}")
        st.stop()

ohlc = result["ohlc"]
n = len(ohlc)

if n == 0:
    st.error("❌ Veri seti boş.")
    st.stop()

start_idx = max(0, n - lookback)
ohlc_view = ohlc.iloc[start_idx:]

# --- Apply filters ---

if not enable_hs:
    result["hs"] = []
    result["ihs"] = []

if not enable_flags:
    result["bull_flags"] = []
    result["bear_flags"] = []
    result["bull_pennants"] = []
    result["bear_pennants"] = []

if not enable_harmonics:
    for name in list(result["harmonics"].keys()):
        result["harmonics"][name]["bull_patterns"] = []
        result["harmonics"][name]["bear_patterns"] = []
else:
    for name in list(result["harmonics"].keys()):
        if name not in selected_harmonics:
            result["harmonics"][name]["bull_patterns"] = []
            result["harmonics"][name]["bear_patterns"] = []

# --- Build signals ---

signals = build_signals_from_patterns(result, start_idx, max_per_type, ohlc)
chart_data = ohlc_to_lw_data(ohlc_view)
overlays = build_pattern_overlays(result, start_idx, ohlc, show_pattern_lines)
sr_lines = build_sr_levels(result, start_idx, ohlc) if show_sr_levels else []

# --- Statistics ---

col1, col2, col3, col4 = st.columns(4)

total_hs = len(result["hs"]) + len(result["ihs"])
total_flags = len(result["bull_flags"]) + len(result["bear_flags"]) + \
              len(result["bull_pennants"]) + len(result["bear_pennants"])
total_harmonics = sum(
    len(info["bull_patterns"]) + len(info["bear_patterns"])
    for info in result["harmonics"].values()
)

with col1:
    st.markdown(f"""
    <div class="stat-box">
        <div class="pattern-count">{total_hs}</div>
        <div class="pattern-label">Head & Shoulders</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="stat-box">
        <div class="pattern-count">{total_flags}</div>
        <div class="pattern-label">Flags & Pennants</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="stat-box">
        <div class="pattern-count">{total_harmonics}</div>
        <div class="pattern-label">Harmonic Patterns</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="stat-box">
        <div class="pattern-count">{len(signals)}</div>
        <div class="pattern-label">Toplam Sinyal</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ======================= CHART =======================

lw_data_json = json.dumps(chart_data)
signals_json = json.dumps(signals)
overlays_json = json.dumps(overlays)
sr_lines_json = json.dumps(sr_lines)

html = f"""
<div id="tvchart" style="width: 100%; height: 700px;"></div>
<script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
<script>
    const container = document.getElementById('tvchart');
    const chart = LightweightCharts.createChart(container, {{
        width: container.clientWidth,
        height: 700,
        layout: {{
            background: {{ type: 'solid', color: '#0e0e0e' }},
            textColor: '#d1d4dc',
        }},
        grid: {{
            vertLines: {{ color: '#1a1a1a' }},
            horzLines: {{ color: '#1a1a1a' }},
        }},
        rightPriceScale: {{
            borderColor: '#2a2a2a',
        }},
        timeScale: {{
            borderColor: '#2a2a2a',
            timeVisible: true,
            secondsVisible: false,
        }},
        crosshair: {{
            mode: LightweightCharts.CrosshairMode.Normal,
        }},
    }});

    const candleSeries = chart.addCandlestickSeries({{
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
    }});

    const data = {lw_data_json};
    candleSeries.setData(data);

    const signals = {signals_json};
    const markers = [];

    signals.forEach(sig => {{
        markers.push({{
            time: sig.time,
            position: sig.side === 'long' ? 'belowBar' : 'aboveBar',
            color: sig.side === 'long' ? '#2ecc71' : '#e74c3c',
            shape: sig.side === 'long' ? 'arrowUp' : 'arrowDown',
            text: sig.pattern,
        }});
    }});

    candleSeries.setMarkers(markers);

    // Support/Resistance levels
    const srLevels = {sr_lines_json};
    srLevels.forEach(level => {{
        const priceLine = candleSeries.createPriceLine({{
            price: level.price,
            color: level.color,
            lineWidth: level.width,
            lineStyle: level.style,
            axisLabelVisible: true,
            title: 'S/R',
        }});
    }});

    // Responsive
    new ResizeObserver(entries => {{
        if (entries.length === 0 || entries[0].target !== container) {{
            return;
        }}
        const newRect = entries[0].contentRect;
        chart.applyOptions({{ width: newRect.width, height: newRect.height }});
    }}).observe(container);
</script>
"""

st.components.v1.html(html, height=720)

# ======================= SIGNALS TABLE =======================

st.markdown("---")
st.markdown("## 📋 Tespit Edilen Sinyaller")

if signals:
    sig_df = pd.DataFrame(signals)
    sig_df['risk'] = abs(sig_df['entry'] - sig_df['stop'])
    sig_df['reward'] = abs(sig_df['tp1'] - sig_df['entry'])
    sig_df['R:R'] = (sig_df['reward'] / sig_df['risk']).round(2)

    # Color code by side
    def highlight_side(row):
        if row['side'] == 'long':
            return ['background-color: #1a4d2e'] * len(row)
        else:
            return ['background-color: #4d1a1a'] * len(row)

    st.dataframe(
        sig_df.style.apply(highlight_side, axis=1),
        use_container_width=True
    )

    # Download button
    csv = sig_df.to_csv(index=False)
    st.download_button(
        label="📥 Sinyalleri CSV olarak indir",
        data=csv,
        file_name="pattern_signals.csv",
        mime="text/csv",
    )
else:
    st.info("ℹ️ Seçili aralıkta sinyal bulunamadı.")

# ======================= PATTERN DETAILS =======================

with st.expander("📊 Pattern Detayları", expanded=False):
    tab1, tab2, tab3 = st.tabs(["Head & Shoulders", "Flags & Pennants", "Harmonics"])

    with tab1:
        st.write(f"**H&S Patterns:** {len(result['hs'])}")
        st.write(f"**Inverse H&S Patterns:** {len(result['ihs'])}")

    with tab2:
        st.write(f"**Bull Flags:** {len(result['bull_flags'])}")
        st.write(f"**Bear Flags:** {len(result['bear_flags'])}")
        st.write(f"**Bull Pennants:** {len(result['bull_pennants'])}")
        st.write(f"**Bear Pennants:** {len(result['bear_pennants'])}")

    with tab3:
        for name, info in result["harmonics"].items():
            bull_count = len(info["bull_patterns"])
            bear_count = len(info["bear_patterns"])
            if bull_count > 0 or bear_count > 0:
                st.write(f"**{name}:** {bull_count} bull, {bear_count} bear")

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; padding: 2rem;">
    <p>🎯 Advanced Pattern Detection System | Powered by TradingView Lightweight Charts</p>
</div>
""", unsafe_allow_html=True)
