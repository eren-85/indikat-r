"""
Professional Pattern Detection UI with Lifecycle Management

Features:
- Pattern lifecycle tracking (active/completed)
- Real-time TP/Stop monitoring
- Pattern toggle controls
- Multi-timeframe support
- Complete integration of all algorithms
"""

import json
import io
import numpy as np
import pandas as pd
import streamlit as st
from typing import Dict, List

from head_shoulders import find_hs_patterns
from flags_pennants import find_flags_pennants_trendline
from harmonic_patterns import find_xabcd, ALL_PATTERNS
from directional_change import get_extremes, directional_change
from mp_support_resist import support_resistance_levels
from trendline_automation import fit_trendlines_high_low
from pattern_manager import PatternManager, PatternState, calculate_pattern_max_bars
from data_downloader import download_binance, download_multiple_binance, validate_ohlc


st.set_page_config(
    page_title="Pro Pattern Detection System",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======================= CSS =======================

st.markdown("""
<style>
    .main-title {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(120deg, #2ecc71, #3498db);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .stat-card {
        background: linear-gradient(135deg, #1e1e1e 0%, #2a2a2a 100%);
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid;
        margin: 0.5rem 0;
    }
    .stat-card.active {
        border-color: #2ecc71;
    }
    .stat-card.completed {
        border-color: #3498db;
    }
    .stat-card.winning {
        border-color: #f1c40f;
    }
    .stat-number {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
    }
    .stat-label {
        color: #888;
        font-size: 0.9rem;
        text-transform: uppercase;
    }
    .pattern-toggle {
        background: #2a2a2a;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.3rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ======================= SESSION STATE =======================

if 'pattern_manager' not in st.session_state:
    st.session_state.pattern_manager = None

if 'current_view_index' not in st.session_state:
    st.session_state.current_view_index = -1

# ======================= DATA LOADING =======================

@st.cache_data(show_spinner=False)
def load_ohlc(csv_path=None, file_bytes=None) -> pd.DataFrame:
    """Load OHLC data and ensure datetime index"""
    if file_bytes is not None:
        df = pd.read_csv(io.BytesIO(file_bytes))
    elif csv_path:
        df = pd.read_csv(csv_path)
    else:
        raise ValueError("csv_path veya file_bytes gerekli.")

    # Ensure datetime index
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    elif not isinstance(df.index, pd.DatetimeIndex):
        # If no date column and index is not datetime, try to convert index
        try:
            df.index = pd.to_datetime(df.index)
        except:
            # If conversion fails, create a datetime index
            st.warning("⚠️ CSV'de 'date' kolonu bulunamadı. Otomatik datetime index oluşturuluyor...")
            df['date'] = pd.date_range(start='2023-01-01', periods=len(df), freq='h')
            df = df.set_index('date')

    df.index.name = 'date'
    df = df.sort_index()
    return df


@st.cache_data(show_spinner=False)
def detect_patterns(
    csv_path=None,
    file_bytes=None,
    dataframe=None,
    hs_order: int = 6,
    flag_order: int = 10,
    sigma: float = 0.02,
    err_thresh: float = 0.5,
):
    """Detect all patterns"""

    if dataframe is not None:
        ohlc = dataframe
    else:
        ohlc = load_ohlc(csv_path=csv_path, file_bytes=file_bytes)

    # Log version
    ohlc_log = ohlc.copy()
    for col in ["open", "high", "low", "close"]:
        ohlc_log[col] = np.log(ohlc_log[col])

    log_close = ohlc_log["close"].to_numpy()

    # H&S
    hs_patterns, ihs_patterns = find_hs_patterns(
        log_close, order=hs_order, early_find=False
    )

    # Flags & Pennants
    bull_flags, bear_flags, bull_pennants, bear_pennants = \
        find_flags_pennants_trendline(log_close, flag_order)

    # Harmonics
    data_ext = ohlc.copy()
    data_ext["r"] = np.log(data_ext["close"]).diff().shift(-1)
    extremes = get_extremes(data_ext, sigma)
    harmonic_output = find_xabcd(data_ext, extremes, err_thresh)

    # Support/Resistance
    sr_levels = None
    try:
        if len(ohlc) >= 100:
            sr_lookback = min(365, len(ohlc) // 2)
            sr_levels = support_resistance_levels(
                ohlc, lookback=sr_lookback,
                first_w=0.1, atr_mult=3.0, prom_thresh=0.25
            )
    except:
        pass

    # Directional Change - multiple scales
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
        "dc_levels": dc_levels,
        "extremes": extremes
    }


# ======================= PATTERN MANAGER INTEGRATION =======================

def populate_pattern_manager(result: dict, ohlc: pd.DataFrame) -> PatternManager:
    """
    Populate PatternManager with all detected patterns

    Per YouTube transcripts:
    - Use pattern-specific timeframes for max_bars
    - Calculate proper TP/Stop based on pattern structure
    """

    manager = PatternManager(ohlc)
    index = ohlc.index
    close = ohlc['close'].to_numpy()

    def exp_if_log(x):
        return float(np.exp(x))

    # Add H&S patterns (SHORT)
    for pat in result["hs"]:
        try:
            entry_idx = pat.break_i
            entry_price = exp_if_log(pat.neck_end)
            stop_price = exp_if_log(pat.head_p)
            risk = stop_price - entry_price

            # TP1 = head height (as per transcript)
            tp1_price = entry_price - risk

            # Max bars = head width
            max_bars = pat.head_width if hasattr(pat, 'head_width') else 50

            manager.add_pattern(
                pattern_type="H&S",
                side="short",
                entry_index=entry_idx,
                entry_price=entry_price,
                stop_price=stop_price,
                tp1_price=tp1_price,
                max_bars=int(max_bars),
                pattern_data={
                    'head_height': pat.head_height if hasattr(pat, 'head_height') else None,
                    'pattern_r2': pat.pattern_r2 if hasattr(pat, 'pattern_r2') else None
                }
            )
        except:
            pass

    # Add Inverse H&S (LONG)
    for pat in result["ihs"]:
        try:
            entry_idx = pat.break_i
            entry_price = exp_if_log(pat.neck_end)
            stop_price = exp_if_log(pat.head_p)
            risk = entry_price - stop_price
            tp1_price = entry_price + risk

            max_bars = pat.head_width if hasattr(pat, 'head_width') else 50

            manager.add_pattern(
                pattern_type="Inverse H&S",
                side="long",
                entry_index=entry_idx,
                entry_price=entry_price,
                stop_price=stop_price,
                tp1_price=tp1_price,
                max_bars=int(max_bars),
                pattern_data={
                    'head_height': pat.head_height if hasattr(pat, 'head_height') else None
                }
            )
        except:
            pass

    # Add Flags (use flag width as timeout per transcript)
    def add_flags(patterns, label, side):
        for p in patterns:
            try:
                entry_idx = p.conf_x
                entry_price = exp_if_log(p.conf_y)
                stop_price = exp_if_log(p.base_y)

                if side == "long":
                    risk = entry_price - stop_price
                    tp1_price = entry_price + risk
                else:
                    risk = stop_price - entry_price
                    tp1_price = entry_price - risk

                # Use flag width as timeout
                max_bars = p.flag_width if p.flag_width > 0 else 30

                manager.add_pattern(
                    pattern_type=label,
                    side=side,
                    entry_index=entry_idx,
                    entry_price=entry_price,
                    stop_price=stop_price,
                    tp1_price=tp1_price,
                    max_bars=int(max_bars),
                    pattern_data={
                        'pole_height': p.pole_height,
                        'flag_height': p.flag_height
                    }
                )
            except:
                pass

    add_flags(result["bull_flags"], "Bull Flag", "long")
    add_flags(result["bear_flags"], "Bear Flag", "short")
    add_flags(result["bull_pennants"], "Bull Pennant", "long")
    add_flags(result["bear_pennants"], "Bear Pennant", "short")

    # Add Harmonic Patterns
    for name, info in result["harmonics"].items():
        # Bull patterns
        for p in info["bull_patterns"]:
            try:
                entry_idx = p.D
                entry_price = close[p.D]
                stop_price = close[p.X] if p.X < len(close) else entry_price * 0.98
                risk = entry_price - stop_price
                if risk <= 0:
                    continue
                tp1_price = entry_price + risk

                # Use XA to D distance as timeout
                max_bars = abs(p.D - p.X)

                manager.add_pattern(
                    pattern_type=f"{name}",
                    side="long",
                    entry_index=entry_idx,
                    entry_price=float(entry_price),
                    stop_price=float(stop_price),
                    tp1_price=float(tp1_price),
                    max_bars=max_bars,
                    pattern_data={
                        'error': p.error,
                        'X': p.X, 'A': p.A, 'B': p.B, 'C': p.C, 'D': p.D
                    }
                )
            except:
                pass

        # Bear patterns
        for p in info["bear_patterns"]:
            try:
                entry_idx = p.D
                entry_price = close[p.D]
                stop_price = close[p.X] if p.X < len(close) else entry_price * 1.02
                risk = stop_price - entry_price
                if risk <= 0:
                    continue
                tp1_price = entry_price - risk

                max_bars = abs(p.D - p.X)

                manager.add_pattern(
                    pattern_type=f"{name}",
                    side="short",
                    entry_index=entry_idx,
                    entry_price=float(entry_price),
                    stop_price=float(stop_price),
                    tp1_price=float(tp1_price),
                    max_bars=max_bars,
                    pattern_data={
                        'error': p.error,
                        'X': p.X, 'A': p.A, 'B': p.B, 'C': p.C, 'D': p.D
                    }
                )
            except:
                pass

    return manager


# ======================= UI HELPERS =======================

def ohlc_to_lw_data(ohlc_view: pd.DataFrame):
    """Convert to Lightweight Charts format"""
    data = []
    for t, row in ohlc_view.iterrows():
        # Handle both DatetimeIndex and integer index
        if isinstance(t, pd.Timestamp):
            time_str = t.isoformat()
        elif hasattr(t, 'isoformat'):
            time_str = t.isoformat()
        else:
            # Fallback for integer or other types
            time_str = str(t)

        data.append({
            "time": time_str,
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        })
    return data


def build_active_markers(manager: PatternManager, current_idx: int, enabled_patterns: List[str]):
    """Build markers for active patterns only"""

    active = manager.get_active_patterns(current_idx)

    # Filter by enabled patterns
    active = [p for p in active if p.pattern_type in enabled_patterns]

    markers = []
    for p in active:
        # Entry marker
        markers.append({
            "time": p.entry_time.isoformat(),
            "position": "belowBar" if p.side == "long" else "aboveBar",
            "color": "#2ecc71" if p.side == "long" else "#e74c3c",
            "shape": "arrowUp" if p.side == "long" else "arrowDown",
            "text": f"{p.pattern_type} [{p.bars_active}bars]",
            "size": 1
        })

    return markers


def build_sr_lines(result, current_idx: int, ohlc: pd.DataFrame):
    """Build S/R level lines for current view"""

    if result["sr_levels"] is None or current_idx >= len(result["sr_levels"]):
        return []

    levels = result["sr_levels"][current_idx]
    if not levels:
        return []

    sr_lines = []
    for level in levels:
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
    "Kaynak Seç",
    ["📁 Dosya Yolu", "📤 CSV Yükle", "🌐 Binance İndir"],
    index=0
)

csv_path = None
uploaded_file = None
downloaded_data = None

if data_source == "📁 Dosya Yolu":
    csv_path = st.sidebar.text_input("CSV dosya yolu", "BTCUSDT3600.csv")

elif data_source == "📤 CSV Yükle":
    uploaded_file = st.sidebar.file_uploader("CSV dosyası", type=["csv"])

elif data_source == "🌐 Binance İndir":
    st.sidebar.markdown("### Binance Ayarları")

    symbol = st.sidebar.text_input("Sembol", "BTCUSDT")

    interval = st.sidebar.selectbox(
        "Timeframe",
        ["1m", "5m", "15m", "1h", "4h", "1d"],
        index=3  # 1h default
    )

    num_candles = st.sidebar.number_input(
        "Mum sayısı",
        min_value=100,
        max_value=5000,
        value=1000,
        step=100
    )

    if st.sidebar.button("📥 İndir", key="download_btn"):
        with st.spinner(f"📡 {symbol} verisi indiriliyor..."):
            try:
                if num_candles <= 1000:
                    downloaded_data = download_binance(symbol, interval, num_candles)
                else:
                    downloaded_data = download_multiple_binance(symbol, interval, num_candles)

                st.sidebar.success(f"✅ {len(downloaded_data)} mum indirildi!")
                st.sidebar.info(f"📅 {downloaded_data.index[0]} - {downloaded_data.index[-1]}")

                # Save to session state
                st.session_state['downloaded_data'] = downloaded_data

            except Exception as e:
                st.sidebar.error(f"❌ Hata: {e}")
                downloaded_data = None

    # Check if data exists in session state
    if 'downloaded_data' in st.session_state:
        downloaded_data = st.session_state['downloaded_data']

st.sidebar.markdown("---")
st.sidebar.markdown("## ⚙️ Görünüm")

lookback = st.sidebar.slider(
    "Görüntülenen mum sayısı",
    100, 2000, 500, 50
)

show_sr = st.sidebar.checkbox("Support/Resistance göster", True)
show_dc = st.sidebar.checkbox("Directional Change göster", False)

st.sidebar.markdown("---")
st.sidebar.markdown("## 🎯 Pattern Tespiti")

with st.sidebar.expander("📈 Head & Shoulders"):
    enable_hs = st.checkbox("H&S Aktif", True, key="hs_en")
    hs_order = st.slider("Order", 1, 20, 6, key="hs_ord")

with st.sidebar.expander("🚩 Flags & Pennants"):
    enable_flags = st.checkbox("Flags Aktif", True, key="fl_en")
    flag_order = st.slider("Order", 3, 20, 10, key="fl_ord")

with st.sidebar.expander("🎵 Harmonics"):
    enable_harmonics = st.checkbox("Harmonics Aktif", True, key="harm_en")
    sigma = st.slider("DC Sigma", 0.005, 0.05, 0.02, 0.005, key="sig")
    err_thresh = st.slider("Error Threshold", 0.1, 1.0, 0.5, 0.05, key="err")

    selected_harmonics = st.multiselect(
        "Harmonic Tipler",
        [p.name for p in ALL_PATTERNS],
        ["Gartley", "Bat", "Butterfly"],
        key="harm_sel"
    )

st.sidebar.markdown("---")
st.sidebar.markdown("## 🔍 Pattern Filtreleri")

pattern_side_filter = st.sidebar.multiselect(
    "Pozisyon",
    ["long", "short"],
    ["long", "short"]
)

show_completed = st.sidebar.checkbox("Tamamlanmış pattern'leri göster", False)

# ======================= MAIN UI =======================

st.markdown('<div class="main-title">⚡ Pro Pattern Detection System</div>', unsafe_allow_html=True)

# Load data
if data_source == "📁 Dosya Yolu":
    if not csv_path:
        st.error("❌ CSV dosya yolu giriniz.")
        st.stop()
    file_bytes = None
    use_dataframe = None

elif data_source == "📤 CSV Yükle":
    if uploaded_file is None:
        st.warning("⚠️ CSV dosyası yükleyiniz.")
        st.stop()
    file_bytes = uploaded_file.getvalue()
    csv_path = None
    use_dataframe = None

elif data_source == "🌐 Binance İndir":
    if downloaded_data is None:
        st.warning("⚠️ 'İndir' butonuna basarak veri indirin.")
        st.stop()
    csv_path = None
    file_bytes = None
    use_dataframe = downloaded_data

# Detect patterns
with st.spinner("🔍 Pattern'ler tespit ediliyor..."):
    result = detect_patterns(
        csv_path=csv_path,
        file_bytes=file_bytes,
        dataframe=use_dataframe,
        hs_order=hs_order,
        flag_order=flag_order,
        sigma=sigma,
        err_thresh=err_thresh,
    )

ohlc = result["ohlc"]
n = len(ohlc)

if n == 0:
    st.error("❌ Veri seti boş.")
    st.stop()

# Initialize Pattern Manager
if st.session_state.pattern_manager is None:
    with st.spinner("⚙️ Pattern manager başlatılıyor..."):
        st.session_state.pattern_manager = populate_pattern_manager(result, ohlc)

manager = st.session_state.pattern_manager

# Current view
start_idx = max(0, n - lookback)
current_idx = n - 1
st.session_state.current_view_index = current_idx

# Update patterns to current index
manager.update_patterns(current_idx)

# Build enabled patterns list
enabled_patterns = []
if enable_hs:
    enabled_patterns.extend(["H&S", "Inverse H&S"])
if enable_flags:
    enabled_patterns.extend(["Bull Flag", "Bear Flag", "Bull Pennant", "Bear Pennant"])
if enable_harmonics:
    enabled_patterns.extend(selected_harmonics)

# Get active patterns
active_patterns = manager.get_active_patterns(
    current_idx,
    pattern_types=enabled_patterns if enabled_patterns else None,
    sides=pattern_side_filter if pattern_side_filter else None
)

# Statistics
stats = manager.get_statistics()

# ======================= STATISTICS CARDS =======================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="stat-card active">
        <div class="stat-number" style="color: #2ecc71;">{len(active_patterns)}</div>
        <div class="stat-label">Aktif Pattern</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="stat-card completed">
        <div class="stat-number" style="color: #3498db;">{stats['total']}</div>
        <div class="stat-label">Tamamlanan</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="stat-card winning">
        <div class="stat-number" style="color: #f1c40f;">{stats['win_rate']:.1f}%</div>
        <div class="stat-label">Win Rate</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-number" style="color: #e74c3c;">{stats['avg_r']:.2f}R</div>
        <div class="stat-label">Avg R-Multiple</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ======================= CHART =======================

ohlc_view = ohlc.iloc[start_idx:]
chart_data = ohlc_to_lw_data(ohlc_view)
markers = build_active_markers(manager, current_idx, enabled_patterns)
sr_lines = build_sr_lines(result, current_idx, ohlc) if show_sr else []

lw_data_json = json.dumps(chart_data)
markers_json = json.dumps(markers)
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
        rightPriceScale: {{ borderColor: '#2a2a2a' }},
        timeScale: {{
            borderColor: '#2a2a2a',
            timeVisible: true,
        }},
    }});

    const candleSeries = chart.addCandlestickSeries({{
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
    }});

    candleSeries.setData({lw_data_json});
    candleSeries.setMarkers({markers_json});

    // S/R levels
    const srLevels = {sr_lines_json};
    srLevels.forEach(level => {{
        candleSeries.createPriceLine({{
            price: level.price,
            color: level.color,
            lineWidth: level.width,
            lineStyle: level.style,
            axisLabelVisible: true,
            title: 'S/R',
        }});
    }});

    new ResizeObserver(entries => {{
        if (entries.length && entries[0].target === container) {{
            const newRect = entries[0].contentRect;
            chart.applyOptions({{ width: newRect.width }});
        }}
    }}).observe(container);
</script>
"""

st.components.v1.html(html, height=720)

# ======================= ACTIVE PATTERNS TABLE =======================

st.markdown("## 📊 Aktif Pattern'ler")

if active_patterns:
    active_df = manager.to_dataframe(active_only=True)

    # Filter by enabled
    active_df = active_df[active_df['pattern_type'].isin(enabled_patterns)]

    # Calculate unrealized PnL
    current_price = ohlc['close'].iloc[-1]
    active_df['current_price'] = current_price
    active_df['unrealized_pnl'] = active_df.apply(
        lambda row: (current_price - row['entry_price']) if row['side'] == 'long'
                    else (row['entry_price'] - current_price),
        axis=1
    )
    active_df['unrealized_pnl_pct'] = (active_df['unrealized_pnl'] / active_df['entry_price']) * 100

    # Style
    def color_pnl(val):
        color = '#2ecc71' if val > 0 else '#e74c3c' if val < 0 else '#888'
        return f'color: {color}'

    styled_df = active_df[['pattern_type', 'side', 'entry_time', 'entry_price',
                           'stop_price', 'tp1_price', 'bars_active',
                           'unrealized_pnl_pct']].style.applymap(
        color_pnl, subset=['unrealized_pnl_pct']
    )

    st.dataframe(styled_df, use_container_width=True)

    # Download
    csv = active_df.to_csv(index=False)
    st.download_button(
        "📥 Aktif Pattern'leri İndir",
        csv,
        "active_patterns.csv",
        "text/csv"
    )
else:
    st.info("ℹ️ Aktif pattern bulunamadı.")

# ======================= COMPLETED PATTERNS =======================

if show_completed and stats['total'] > 0:
    st.markdown("---")
    st.markdown("## 📈 Tamamlanan Pattern'ler")

    completed_df = manager.to_dataframe(active_only=False)
    completed_df = completed_df[completed_df['state'] != 'active']

    st.dataframe(completed_df, use_container_width=True)

    # Performance metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Profit Factor", f"{stats['profit_factor']:.2f}")
        st.metric("Total Wins", stats['wins'])
    with col2:
        st.metric("Gross Profit", f"${stats['gross_profit']:.2f}")
        st.metric("Total Losses", stats['losses'])

# ======================= FOOTER =======================

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888;">
    ⚡ Pro Pattern Detection System | Real-time Pattern Lifecycle Management
</div>
""", unsafe_allow_html=True)
