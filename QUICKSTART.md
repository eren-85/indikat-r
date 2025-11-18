# 🚀 Quick Start Guide

## 5 Dakikada Başlangıç

### 1️⃣ Kurulum (İlk Kez)

```bash
# Gerekli paketleri yükle
pip install -r requirements.txt
```

### 2️⃣ Örnek Veri Oluştur

```bash
# Örnek BTC verisi oluştur
python sample_data_generator.py
```

Bu komut şu dosyaları oluşturur:
- `BTCUSDT3600.csv` - Ana test verisi (2000 saatlik mum)
- `harmonic_sample.csv` - Harmonic pattern içeren veri
- `hs_sample.csv` - Head & Shoulders pattern içeren veri
- `flag_sample.csv` - Bull Flag pattern içeren veri

### 3️⃣ Test Et

```bash
# Pattern detection'ın çalıştığını doğrula
python test_patterns.py
```

Başarılı ise şunu görmelisiniz:
```
✅ Pattern detection test completed!
```

### 4️⃣ UI'ı Başlat

```bash
# Web arayüzünü başlat
streamlit run advanced_pattern_ui.py
```

Tarayıcınız otomatik açılacak: `http://localhost:8501`

---

## 📖 UI Kullanımı

### Sol Panel - Ayarlar

1. **Veri Kaynağı**
   - "📁 Dosya Yolu" seçin
   - Varsayılan: `BTCUSDT3600.csv`

2. **Genel Ayarlar**
   - Görüntülenecek mum sayısı: 1000 (önerilen)
   - Pattern başına max sinyal: 10

3. **Pattern Ayarları**
   - **Head & Shoulders**: Order = 6
   - **Flags & Pennants**: Order = 10
   - **Harmonics**:
     - Sigma = 0.02
     - Error threshold = 0.5
     - İstediğiniz pattern tiplerini seçin

### Ana Ekran

- **İstatistikler**: Tespit edilen pattern sayıları
- **Chart**: TradingView grafik + pattern marker'ları
- **Sinyal Tablosu**: Entry/Stop/TP detayları
- **CSV Export**: Sinyalleri indir

---

## 🎯 Kendi Verinizi Kullanma

### CSV Format

Dosyanız şu kolonlara sahip olmalı:

```csv
date,open,high,low,close,volume
2024-01-01 00:00:00,45000,46000,44500,45500,1000
2024-01-01 01:00:00,45500,46200,45200,45800,1200
...
```

### Veriyi Yükle

**Seçenek 1: Dosya Yolu**
- Sol panelde "📁 Dosya Yolu" seç
- CSV dosya yolunu gir (örn: `my_data.csv`)

**Seçenek 2: Upload**
- Sol panelde "📤 CSV Yükle" seç
- CSV dosyanı yükle

---

## ⚙️ Pattern Parametreleri

### Optimal Değerler

| Pattern Type | Parameter | Timeframe | Önerilen |
|--------------|-----------|-----------|----------|
| H&S | Order | 1H | 6-10 |
| H&S | Order | 1D | 3-6 |
| Flags | Order | 1H | 10-15 |
| Flags | Order | 1D | 5-10 |
| Harmonics | Sigma | 1H | 0.02 |
| Harmonics | Sigma | 1D | 0.03 |
| Harmonics | Error | Hepsi | 0.3-0.7 |

### Ayar İpuçları

**Daha az ama kaliteli pattern için:**
- Order değerini artır
- Error threshold'u azalt (0.2-0.3)

**Daha fazla pattern için:**
- Order değerini azalt
- Error threshold'u artır (0.6-0.8)

**Farklı ölçekler için:**
- Küçük patterns → Order: 3-5
- Orta patterns → Order: 8-12
- Büyük patterns → Order: 15-20

---

## 🐛 Sorun Giderme

### "No module named 'X'" Hatası

```bash
pip install -r requirements.txt
```

### "CSV dosyası bulunamadı"

```bash
python sample_data_generator.py
```

### "Pattern bulunamadı"

- Daha fazla veri kullan (min 500 mum)
- Error threshold'u artır
- Order değerini ayarla

### Streamlit Başlamıyor

```bash
# Port zaten kullanımda ise:
streamlit run advanced_pattern_ui.py --server.port 8502
```

---

## 📊 Pattern Örnekleri

### En İyi Sonuç Veren Setuplar

**Scalping (1H chart):**
```
H&S Order: 4-6
Flag Order: 8-10
Harmonics Sigma: 0.015-0.02
Error: 0.4-0.5
```

**Swing Trading (4H-1D):**
```
H&S Order: 6-8
Flag Order: 10-15
Harmonics Sigma: 0.025-0.03
Error: 0.3-0.5
```

---

## 🎨 Görselleştirme Özellikleri

### Chart Üzerinde

- ✅ **Entry Marker**: Yeşil (long) / Kırmızı (short) ok
- ✅ **TP1 Marker**: Sarı nokta
- ✅ **STOP Marker**: Kırmızı ok
- ✅ **S/R Levels**: Mavi kesikli çizgiler
- ✅ **Pattern Lines**: Harmonic XABCD çizgileri

### Kontrol

- ✔️ Pattern çizgilerini göster/gizle
- ✔️ S/R seviyelerini göster/gizle
- ✔️ Aktif pattern tiplerini seç

---

## 💡 İleri Seviye

### Python API Kullanımı

```python
from advanced_pattern_ui import detect_all_patterns

result = detect_all_patterns(
    csv_path="my_data.csv",
    hs_order=6,
    flag_order=10,
    sigma=0.02,
    err_thresh=0.5
)

# Pattern'lere eriş
print(f"H&S: {len(result['hs'])}")
print(f"Harmonics: {result['harmonics']}")
```

### Toplu Test

```bash
# Farklı parametrelerle test
for order in 5 6 7 8; do
    echo "Testing order=$order"
    # Kendi test scriptiniz
done
```

---

## 📈 Veri Kaynakları

### Ücretsiz Veri İndirme

**Binance:**
```python
# binance API ile
import ccxt
exchange = ccxt.binance()
ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=2000)
```

**Yahoo Finance:**
```python
import yfinance as yf
df = yf.download("BTC-USD", period="1y", interval="1h")
```

**CSV Export:**
```python
df.to_csv('my_btc_data.csv')
```

---

## 🎯 Sonraki Adımlar

1. ✅ Kurulumu tamamla
2. ✅ Örnek veri ile test et
3. ✅ Parametreleri optimize et
4. ✅ Kendi verinle dene
5. ✅ Sinyalleri export et
6. ✅ Backtest yap

---

## 🤝 Yardım

Sorun yaşıyorsanız:

1. `test_patterns.py` çalıştır
2. Hata mesajlarını kontrol et
3. README.md'yi oku
4. GitHub Issues'a yaz

---

**Mutlu Trading! 🚀📊**
