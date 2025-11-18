# 🎯 Advanced Pattern Detection System

Profesyonel teknik analiz pattern tespit sistemi. TradingView Lightweight Charts ile görselleştirme.

## 🚀 İki Sistem Seçeneği

### 1. **PRO SYSTEM** (Önerilen) - `pro_pattern_ui.py`
✅ Pattern lifecycle management (ACTIVE/TP_HIT/STOP_HIT/EXPIRED)
✅ Sadece aktif pattern'ler gösterilir
✅ Real-time TP/Stop monitoring
✅ Performance statistics
✅ Pattern toggle controls

### 2. **BASIC SYSTEM** - `advanced_pattern_ui.py`
✅ Tüm pattern'leri göster
✅ Basit kullanım
✅ Hızlı analiz

**Önerilen:** Trading için **PRO SYSTEM** kullanın.

## ✨ Özellikler

### 📊 Pattern Tespiti

- **Harmonic Patterns**: Gartley, Bat, Butterfly, Crab, Deep Crab, Cypher, Shark
- **Head & Shoulders**: Normal ve Inverted versiyonlar
- **Flags & Pennants**: Bull/Bear Flags ve Pennants
- **Support/Resistance**: Market Profile bazlı S/R seviyeleri
- **Trend Lines**: Otomatik destek ve direnç trend çizgileri
- **Directional Change**: Multi-scale zigzag analizi

### 🎨 Görselleştirme

- TradingView Lightweight Charts entegrasyonu
- Pattern overlay çizgileri (XABCD noktaları)
- Support/Resistance seviyeleri
- Entry/Stop/TP1 sinyalleri
- Interaktif kontrol paneli

### ⚙️ Gelişmiş Özellikler

- Parametrik pattern kontrolü
- Multi-timeframe analiz
- Pattern filtering
- CSV export
- Real-time statistics

## 🚀 Kurulum

### 1. Bağımlılıkları Yükle

```bash
pip install -r requirements.txt
```

### 2. Örnek Veri Oluştur (İlk kez)

```bash
python sample_data_generator.py
```

### 3. Sistemi Test Et

```bash
# Pattern detection test
python test_patterns.py

# Pro system test
python test_pro_system.py
```

### 4. Uygulamayı Başlat

**PRO SYSTEM (Önerilen):**
```bash
streamlit run pro_pattern_ui.py
```

**BASIC SYSTEM:**
```bash
streamlit run advanced_pattern_ui.py
```

Tarayıcınızda otomatik olarak `http://localhost:8501` açılacaktır.

## 📖 Kullanım

### Veri Formatı

CSV dosyanız şu kolonları içermelidir:

```csv
date,open,high,low,close,volume
2024-01-01 00:00:00,45000,46000,44500,45500,1000
...
```

### Hızlı Başlangıç

1. **Veri Yükle**: Sol panelden CSV dosyanızı seçin veya yükleyin
2. **Pattern Seç**: Hangi pattern tiplerini tespit etmek istediğinizi seçin
3. **Parametreleri Ayarla**: Order, sigma, error threshold gibi parametreleri ayarlayın
4. **Grafik İncele**: Pattern'leri ve sinyalleri görsel olarak inceleyin
5. **Sinyalleri İndir**: CSV olarak export edin

### Pattern Parametreleri

#### Head & Shoulders
- **Order**: Rolling window boyutu (1-20, varsayılan: 6)
- Daha büyük değerler daha büyük pattern'leri bulur

#### Flags & Pennants
- **Order**: Pattern boyut kontrolü (3-20, varsayılan: 10)

#### Harmonic Patterns
- **Sigma**: Directional change threshold (0.005-0.05, varsayılan: 0.02)
- **Error Threshold**: Pattern eşleşme toleransı (0.1-1.0, varsayılan: 0.5)

#### Support/Resistance
- **Lookback**: Geriye dönük analiz periyodu (50-500, varsayılan: 365)

## 📊 Pattern Açıklamaları

### Harmonic Patterns

XABCD formasyonları. Fibonacci oranlarına dayalı:

- **Gartley**: Klasik harmonik pattern (0.618 retrace)
- **Bat**: Daha derin retracement (0.886)
- **Butterfly**: Genişletilmiş pattern
- **Crab**: Extreme harmonik
- **Deep Crab**: Daha derin Crab
- **Cypher**: Alternatif harmonik
- **Shark**: Farklı bir harmonik yapı

### Head & Shoulders

Trend dönüş patternleri:

- **H&S**: Düşüş sinyali (short)
- **Inverse H&S**: Yükseliş sinyali (long)

### Flags & Pennants

Devam patternleri:

- **Bull Flag**: Yükseliş trendi devam
- **Bear Flag**: Düşüş trendi devam
- **Pennants**: Üçgen devam patternleri

## 🔧 Gelişmiş Kullanım

### Python API

```python
from advanced_pattern_ui import detect_all_patterns

result = detect_all_patterns(
    csv_path="BTCUSDT3600.csv",
    hs_order=6,
    flag_order=10,
    sigma=0.02,
    err_thresh=0.5
)

# Access patterns
hs_patterns = result["hs"]
harmonics = result["harmonics"]
sr_levels = result["sr_levels"]
```

### Özelleştirme

Pattern tespiti fonksiyonları:

- `head_shoulders.py`: H&S pattern recognition
- `flags_pennants.py`: Flag & Pennant detection
- `harmonic_patterns.py`: Harmonic XABCD patterns
- `mp_support_resist.py`: S/R level calculation
- `trendline_automation.py`: Trend line fitting

## 📁 Dosya Yapısı

```
indikat-r/
├── 🚀 UYGULAMALAR
│   ├── pro_pattern_ui.py           # PRO: Lifecycle management
│   ├── advanced_pattern_ui.py      # BASIC: Tüm pattern'ler
│   └── pattern_lw_ui.py            # LEGACY: Eski UI
│
├── 🔧 PATTERN DETECTION
│   ├── head_shoulders.py           # H&S pattern detection
│   ├── flags_pennants.py           # Flag & Pennant detection
│   ├── harmonic_patterns.py        # Harmonic patterns (XABCD)
│   └── pattern_manager.py          # Pattern lifecycle engine
│
├── 📊 ALGORİTMALAR
│   ├── directional_change.py       # Zigzag algorithm
│   ├── rolling_window.py           # Local extrema
│   ├── perceptually_important.py   # PIP algorithm
│   ├── trendline_automation.py     # Trend lines
│   ├── mp_support_resist.py        # S/R levels
│   └── retracement_ratios.py       # Fibonacci analysis
│
├── 🧪 PATTERN MINING (Advanced)
│   ├── pip_pattern_miner.py        # Pattern mining
│   └── wf_pip_miner.py             # Walk-forward mining
│
├── 📝 TESTLER VE VERI
│   ├── test_patterns.py            # Pattern detection tests
│   ├── test_pro_system.py          # Pro system tests
│   └── sample_data_generator.py    # Veri oluşturucu
│
└── 📚 DOKÜMANTASYON
    ├── README.md                    # Ana dokümantasyon
    ├── QUICKSTART.md                # Hızlı başlangıç
    ├── PRO_SYSTEM_GUIDE.md          # Pro sistem rehberi
    └── requirements.txt             # Dependencies
```

## 🎯 Algoritma Kaynakları

Bu projede kullanılan algoritmalar:

- **Directional Change**: Trend dönüş noktalarını tespit eder
- **Rolling Window**: Lokal top ve bottom noktaları bulur
- **Perceptually Important Points (PIP)**: Görsel olarak önemli noktaları seçer
- **Market Profile**: Hacim bazlı S/R seviyeleri

## 📈 Performans İpuçları

1. **Büyük veri setleri** için lookback değerini azaltın
2. **Daha fazla pattern** için error threshold'u artırın
3. **Daha kaliteli pattern** için error threshold'u azaltın
4. **Farklı timeframe'ler** için sigma değerini ayarlayın

## 🤝 Katkıda Bulunma

Pattern detection algoritmalarını geliştirmek için:

1. Yeni pattern tanımları ekleyin
2. Parametreleri optimize edin
3. Görselleştirmeyi iyileştirin

## 📝 Lisans

Bu proje eğitim amaçlıdır. Gerçek trading için kullanmadan önce kapsamlı test edin.

## ⚠️ Uyarı

Bu sistem sadece analiz amaçlıdır. Finansal yatırım tavsiyesi değildir. Kendi sorumluluğunuzda kullanın.

## 🔗 İlgili Projeler

- TradingView Lightweight Charts: https://tradingview.github.io/lightweight-charts/
- YouTube Algoritma Videoları: Pattern Recognition Tutorial Series

---

**Made with ❤️ for algorithmic traders**
