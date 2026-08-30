# Laporan Hasil Analisis Sentimen & Dataset Pertamax RON 92

Laporan ini menyajikan analisis sentimen komentar X (Twitter) terkait kebijakan penyesuaian harga Pertamax (RON 92) dari Rp12.300 menjadi Rp16.250 per liter.

---

## 1. Distribusi Sentimen Masyarakat
Berdasarkan data **2.992 tweet bersih** (dari 3.003 data mentah hasil crawling), distribusi kelas sentimen yang diperoleh adalah:
- **Sentimen Negatif**: 2.082 tweet (69.6%)
- **Sentimen Positif**: 479 tweet (16.0%)
- **Sentimen Netral**: 431 tweet (14.4%)

Hal ini menunjukkan mayoritas masyarakat merespon **Negatif** terhadap isu kenaikan harga Pertamax karena memicu antrean panjang dan kelangkaan Pertalite (migrasi konsumen).

---

## 2. Performa Model SVM (Grid Search)
Dari pencarian Grid Search CV (5-Fold Cross Validation), kernel **RBF** terpilih sebagai yang terbaik:
- **Akurasi Global**: 79% (meningkat signifikan dari 66% pada dataset awal)
- **Macro F1-Score**: 0.68 (meningkat dari 0.49)
- **Weighted F1-Score**: 0.79
- **Best Parameter**: `{'C': 1, 'gamma': 1, 'kernel': 'rbf'}`

### Ringkasan Metrik per Kelas:
- **Negative**: Precision 0.90 | Recall 0.88 | F1-Score 0.89 (Support: 417)
- **Neutral**: Precision 0.55 | Recall 0.64 | F1-Score 0.59 (Support: 86)
- **Positive**: Precision 0.58 | Recall 0.55 | F1-Score 0.57 (Support: 96)

---

## 3. Sampel Tabel Data Mentah (data/raw/tweets.csv)
Berikut adalah 10 baris pertama data mentah hasil crawling Twitter:

| user_name | screen_name | text | favorite_count |
| --- | --- | --- | --- |
| Kotaro Mieyamin | belalangsemprul | @farisrachman_1 Ikut2an komentar ttg BI Gak ngitung dampa... | 1 |
| Bloomberg Technoz | BloombergTZ | Ekonom Fitra Badiul Hadi menilai antrean dan kelangkaan P... | 3 |
| NISANI🍑 | adamnisani07 | @CarolineLukita @tanyarlfes Sebelumnya kan pertalit oplos... | 0 |
| helloliz | dreamy_lofoten | Ga normal sebelum Pertamax turun harga 💀 | 0 |
| chocomochi🐾 | maharanisvt_ | @tanyarlfes Iya nder di sumatera kmrn aku naik bis nyari ... | 0 |
| Daeng Sampara 2 | nasranmaarif963 | @tekarok007 Morowali gas melon 3 kilo masih diangka 120.0... | 0 |
| Kylo Ren(dra) | renkyloren28 | Pertamax naik jadi 16.250 beneran berasa anjirr. Motor be... | 0 |
| Muji Afianto | MujiAfianto | Gue langganan Pertamax Sejak harga Pertamax naik, perasaa... | 0 |
| annie 𓅮 | bebekhermes | @limttel wkwkw dulu pas belom naik pertamax aku sering be... | 0 |
| Lulusan Segar | sipalingbacot | @Jateng_Twit di spbu gua biasa ngisi emg terjadi shifting... | 2 |

---

## 4. Sampel Tabel Data Berlabel (data/processed/labeled_tweets.csv)
Berikut adalah 10 baris pertama data hasil preprocessing dan pelabelan sentimen:

| user_name | screen_name | original_text | sentiment_score | sentiment |
| --- | --- | --- | --- | --- |
| Kotaro Mieyamin | belalangsemprul | @farisrachman_1 Ikut2an komentar ttg BI Gak ngitung dampa... | -12 | Negative |
| Bloomberg Technoz | BloombergTZ | Ekonom Fitra Badiul Hadi menilai antrean dan kelangkaan P... | -8 | Neutral |
| NISANI🍑 | adamnisani07 | @CarolineLukita @tanyarlfes Sebelumnya kan pertalit oplos... | -18 | Negative |
| helloliz | dreamy_lofoten | Ga normal sebelum Pertamax turun harga 💀 | -1 | Negative |
| chocomochi🐾 | maharanisvt_ | @tanyarlfes Iya nder di sumatera kmrn aku naik bis nyari ... | -10 | Negative |
| Daeng Sampara 2 | nasranmaarif963 | @tekarok007 Morowali gas melon 3 kilo masih diangka 120.0... | -15 | Negative |
| Kylo Ren(dra) | renkyloren28 | Pertamax naik jadi 16.250 beneran berasa anjirr. Motor be... | -12 | Negative |
| Muji Afianto | MujiAfianto | Gue langganan Pertamax Sejak harga Pertamax naik, perasaa... | -4 | Negative |
| annie 𓅮 | bebekhermes | @limttel wkwkw dulu pas belom naik pertamax aku sering be... | 7 | Positive |
| Lulusan Segar | sipalingbacot | @Jateng_Twit di spbu gua biasa ngisi emg terjadi shifting... | -17 | Negative |

---

*Catatan: Grafik visualisasi distribusi sentimen, confusion matrix, dan word cloud dapat dilihat di folder `data/processed/`.*
