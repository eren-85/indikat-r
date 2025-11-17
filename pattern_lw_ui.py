import json
import io
import numpy as np
import pandas as pd
import streamlit as st

from head_shoulders import find_hs_patterns
from flags_pennants import find_flags_pennants_trendline
from harmonic_patterns import find_xabcd, ALL_PATTERNS
from directional_change import get_extremes


st.set_page_config(page_title="TradingView Lightweight Pattern UI",
                   layout="wide")


# ======================= DATA LOADER =======================

@st.cache_data(show_spinner=False)
def load_ohlc(csv_path=None, file_bytes=None) -> pd.DataFrame:
    if file_bytes is not None:
        df = pd.read_csv(io.BytesIO(file_bytes))
    elif csv_path:
        df = pd.read_csv(csv_path)
    else:
        raise ValueError("csv_path veya file_bytes vermelisin.")

    # Beklenen kolon isimleri: date, open, high, low, close, volume
    # Gerekirse auto-detect edebilirsin ama şimdilik düz kabul ediyorum.
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    df = df.sort_index()
    return df


@st.cache_data(show_spinner=False)
def detect_patterns(csv_path=None,
                    file_bytes=None,
                    hs_order: int = 6,
                    flag_order: int = 10,
                    sigma: float = 0.02,
                    err_thresh: float = 0.5):
    ohlc = load_ohlc(csv_path=csv_path, file_bytes=file_bytes)

    # Log versiyon (H&S + Flags/Pennants için)
    ohlc_log = ohlc.copy()
    for col in ["open", "high", "low", "close"]:
        ohlc_log[col] = np.log(ohlc_log[col])

    log_close = ohlc_log["close"].to_numpy()

    # --- H&S ---
    hs_patterns, ihs_patterns = find_hs_patterns(
        log_close,
        order=hs_order,
        early_find=False
    )

    # --- Flags & Pennants ---
    bull_flags, bear_flags, bull_pennants, bear_pennants = \
        find_flags_pennants_trendline(log_close, flag_order)

    # --- Harmonikler ---
    data_ext = ohlc.copy()
    data_ext["r"] = np.log(data_ext["close"]).diff().shift(-1)
    extremes = get_extremes(data_ext, sigma)
    harmonic_output = find_xabcd(data_ext, extremes, err_thresh)

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
    }


# ======================= HELPERS =======================

def filter_patterns(patterns, start_attr: str, min_start: int, max_count: int):
    if not patterns:
        return []
    filtered = [p for p in patterns if getattr(p, start_attr) >= min_start]
    filtered.sort(key=lambda p: getattr(p, start_attr))
    if max_count > 0 and len(filtered) > max_count:
        filtered = filtered[-max_count:]
    return filtered


def exp_if_log(x):
    return float(np.exp(x))


def build_signals_from_patterns(result,
                                start_idx: int,
                                max_per_type: int,
                                ohlc: pd.DataFrame):
    """
    TradingView Lightweight Charts için:
      - candlestick datası
      - entry/stop/tp1 marker ve ekstra info
    üretir.
    """

    index = ohlc.index
    close = ohlc["close"].to_numpy()
    signals = []

    # ========== H&S ==========

    # SHORT için H&S (tepe)
    for pat in filter_patterns(result["hs"], "start_i", start_idx, max_per_type):
        t_break = index[pat.break_i]
        # log price -> linear
        entry_price = exp_if_log(pat.neck_end)
        stop_price = exp_if_log(pat.head_p)
        risk = stop_price - entry_price
        tp1_price = entry_price - risk  # 1R hedef

        signals.append({
            "time": t_break.isoformat(),
            "side": "short",
            "pattern": "HS",
            "entry": entry_price,
            "stop": stop_price,
            "tp1": tp1_price,
        })

    # LONG için inverse H&S (dip)
    for pat in filter_patterns(result["ihs"], "start_i", start_idx, max_per_type):
        t_break = index[pat.break_i]
        entry_price = exp_if_log(pat.neck_end)
        stop_price = exp_if_log(pat.head_p)  # inverse H&S’de head dip, stop oradan biraz aşağı vs.
        risk = entry_price - stop_price
        tp1_price = entry_price + risk

        signals.append({
            "time": t_break.isoformat(),
            "side": "long",
            "pattern": "InverseHS",
            "entry": entry_price,
            "stop": stop_price,
            "tp1": tp1_price,
        })

    # ========== FLAGS/PENNANTS ==========

    # Basit kural: conf_x mumunda giriş, stop = base_y, tp1 = entry +/− (entry - stop)
    def add_flag_signals(pats, label, side):
        for p in filter_patterns(pats, "base_x", start_idx, max_per_type):
            t_conf = index[p.conf_x]
            # p.conf_y log
            entry_price = exp_if_log(p.conf_y)
            stop_price = exp_if_log(p.base_y)
            if side == "long":
                risk = entry_price - stop_price
                tp1_price = entry_price + risk
            else:
                risk = stop_price - entry_price
                tp1_price = entry_price - risk

            signals.append({
                "time": t_conf.isoformat(),
                "side": side,
                "pattern": label,
                "entry": entry_price,
                "stop": stop_price,
                "tp1": tp1_price,
            })

    add_flag_signals(result["bull_flags"], "BullFlag", "long")
    add_flag_signals(result["bear_flags"], "BearFlag", "short")
    add_flag_signals(result["bull_pennants"], "BullPennant", "long")
    add_flag_signals(result["bear_pennants"], "BearPennant", "short")

    # ========== HARMONICS ==========

    # Basit: D noktasında giriş, stop = X veya biraz ötesi, tp1 = 1R
    h_out = result["harmonics"]
    for name, info in h_out.items():
        for p in info["bull_patterns"]:
            if p.D < start_idx:
                continue
            t_D = index[p.D]
            entry_price = close[p.D]
            stop_price = close[p.X] if p.X < len(close) else entry_price * 0.98
            risk = entry_price - stop_price
            if risk <= 0:
                continue
            tp1_price = entry_price + risk
            signals.append({
                "time": t_D.isoformat(),
                "side": "long",
                "pattern": name,
                "entry": float(entry_price),
                "stop": float(stop_price),
                "tp1": float(tp1_price),
            })

        for p in info["bear_patterns"]:
            if p.D < start_idx:
                continue
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
                "pattern": name,
                "entry": float(entry_price),
                "stop": float(stop_price),
                "tp1": float(tp1_price),
            })

    return signals


def ohlc_to_lw_data(ohlc_view: pd.DataFrame):
    # Lightweight Charts formatı:
    # { time: '2024-01-01T00:00:00', open:.., high:.., low:.., close:.. }
    data = []
    for t, row in ohlc_view.iterrows():
        data.append({
            "time": t.isoformat(),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        })
    return data


# ======================= UI =======================

st.sidebar.header("Veri")

data_source = st.sidebar.radio(
    "Veri kaynağı",
    ["Dosya yolu", "CSV yükle"],
    index=0
)

csv_path = None
uploaded_file = None

if data_source == "Dosya yolu":
    csv_path = st.sidebar.text_input("CSV dosyası", "BTCUSDT3600.csv")
else:
    uploaded_file = st.sidebar.file_uploader("CSV seç", type=["csv"])

st.sidebar.header("Genel")
lookback = st.sidebar.slider("Grafikte gösterilecek mum sayısı",
                             min_value=200, max_value=5000, value=1000, step=100)
max_per_type = st.sidebar.slider("Her pattern tipi için max sinyal sayısı",
                                 min_value=1, max_value=50, value=10)

st.sidebar.header("Head & Shoulders")
hs_order = st.sidebar.slider("H&S order", 1, 20, 6)
enable_hs = st.sidebar.checkbox("H&S ve Inverse H&S kullan", True)

st.sidebar.header("Flags / Pennants")
flag_order = st.sidebar.slider("Flag/Pennant order", 3, 20, 10)
enable_flags = st.sidebar.checkbox("Flag & Pennant kullan", True)

st.sidebar.header("Harmonikler")
enable_harmonics = st.sidebar.checkbox("Harmonic Patterns kullan", False)
sigma = st.sidebar.slider("Directional Change sigma", 0.005, 0.05, 0.02, step=0.005)
err_thresh = st.sidebar.slider("Pattern hata eşiği", 0.1, 1.0, 0.5, step=0.05)

selected_harmonics = st.sidebar.multiselect(
    "Aktif harmonik tipleri",
    options=[p.name for p in ALL_PATTERNS],
    default=[p.name for p in ALL_PATTERNS],
)

st.title("TradingView Lightweight Charts Pattern UI")

# --- Veri kontrolü ---

if data_source == "Dosya yolu":
    if not csv_path:
        st.error("CSV dosya yolunu gir.")
        st.stop()
    file_bytes = None
else:
    if uploaded_file is None:
        st.warning("CSV dosyası seç.")
        st.stop()
    file_bytes = uploaded_file.getvalue()
    csv_path = None

try:
    result = detect_patterns(
        csv_path=csv_path,
        file_bytes=file_bytes,
        hs_order=hs_order,
        flag_order=flag_order,
        sigma=sigma,
        err_thresh=err_thresh,
    )
except Exception as e:
    st.error(f"Veri/pattern okurken hata: {e}")
    st.stop()

ohlc = result["ohlc"]
n = len(ohlc)
if n == 0:
    st.error("Veri seti boş.")
    st.stop()

start_idx = max(0, n - lookback)
ohlc_view = ohlc.iloc[start_idx:]

# --- Sinyal üretimi (entry/stop/tp1) ---

# İstenmeyen pattern gruplarını devre dışı bırak
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
    # yalnızca seçili harmonikleri bırak
    for name in list(result["harmonics"].keys()):
        if name not in selected_harmonics:
            result["harmonics"][name]["bull_patterns"] = []
            result["harmonics"][name]["bear_patterns"] = []

signals = build_signals_from_patterns(result, start_idx, max_per_type, ohlc)

chart_data = ohlc_to_lw_data(ohlc_view)

# ======================= JS + Lightweight Charts =======================

lw_data_json = json.dumps(chart_data)
signals_json = json.dumps(signals)

html = f"""
<div id="tvchart" style="width: 100%; height: 700px;"></div>
<script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
<script>
    const container = document.getElementById('tvchart');
    const chart = LightweightCharts.createChart(container, {{
        width: container.clientWidth,
        height: 700,
        layout: {{
            background: {{ type: 'solid', color: '#000000' }},
            textColor: '#d1d4dc',
        }},
        grid: {{
            vertLines: {{ visible: false }},
            horzLines: {{ visible: false }},
        }},
        rightPriceScale: {{
            borderColor: '#555',
        }},
        timeScale: {{
            borderColor: '#555',
        }},
        crosshair: {{
            mode: LightweightCharts.CrosshairMode.Normal,
        }},
    }});

    const candleSeries = chart.addCandlestickSeries();
    const data = {lw_data_json};
    candleSeries.setData(data);

    const signals = {signals_json};

    // Entry/Stop/TP1 marker'ları
    const markers = [];

    signals.forEach(sig => {{
        // ENTRY
        markers.push({{
            time: sig.time,
            position: sig.side === 'long' ? 'belowBar' : 'aboveBar',
            color: sig.side === 'long' ? '#2ecc71' : '#e74c3c',
            shape: 'arrowUp',
            text: sig.pattern + ' ENTRY',
        }});

        // TP1
        markers.push({{
            time: sig.time,
            position: sig.side === 'long' ? 'aboveBar' : 'belowBar',
            color: '#f1c40f',
            shape: 'circle',
            text: 'TP1',
        }});

        // STOP
        markers.push({{
            time: sig.time,
            position: sig.side === 'long' ? 'belowBar' : 'aboveBar',
            color: '#e74c3c',
            shape: 'arrowDown',
            text: 'STOP',
        }});
    }});

    candleSeries.setMarkers(markers);

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

# ======================= ALTTA ÖZET TABLO =======================

st.subheader("Entry / Stop / TP1 Sinyal Özeti")

if signals:
    sig_df = pd.DataFrame(signals)
    st.dataframe(sig_df)
else:
    st.write("Seçili aralıkta sinyal yok.")
