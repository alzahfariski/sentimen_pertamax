# Analisis Sentimen Kebijakan Kenaikan Harga Pertamax RON 92 Menggunakan SVM

Repository ini berisi implementasi lengkap untuk proyek **Analisis Sentimen Masyarakat Terhadap Kebijakan Kenaikan Harga Pertamax RON 92 Berdasarkan Komentar X (Twitter) Menggunakan Metode Support Vector Machine (SVM)**. Proyek ini mengintegrasikan seluruh tahapan mulai dari pengambilan data (*data crawling*), pembersihan data (*preprocessing*), pelabelan data latih berbasis leksikon (*sentiment labeling*), ekstraksi fitur (TF-IDF), pelatihan model (SVM), hingga evaluasi model klasifikasi.

---

## 📂 Struktur Direktori Proyek

```directory
├── data/
│   ├── raw/
│   │   ├── tweets.csv                        # Data mentah hasil crawling Twitter
│   │   ├── positive.tsv                      # Kamus leksikon positif (InSet)
│   │   ├── negative.tsv                      # Kamus leksikon negatif (InSet)
│   │   └── colloquial-indonesian-lexicon.csv # Kamus normalisasi kata alay/slang
│   └── processed/
│       ├── preprocessed_tweets.csv           # Hasil text preprocessing (stemmed)
│       ├── labeled_tweets.csv                # Hasil pelabelan sentimen (3 kelas)
│       ├── classification_report.txt         # Laporan evaluasi performa model SVM
│       ├── sentiment_distribution.png        # Grafik distribusi sentimen dataset
│       ├── confusion_matrix.png              # Heatmap matrix evaluasi SVM
│       ├── positive_wordcloud.png            # Word cloud komentar positif
│       └── negative_wordcloud.png            # Word cloud komentar negatif
├── src/
│   ├── crawling.py                           # Modul crawler Twitter (X)
│   ├── preprocess.py                         # Pipeline pembersihan teks bahasa Indonesia
│   ├── labeling.py                           # Pelabelan sentimen berbasis leksikon & aturan
│   └── train_svm.py                          # Training SVM, GridSearch, & evaluasi model
├── venv/                                     # Python Virtual Environment
├── README.md                                 # Dokumentasi utama proyek
└── requirements.txt                          # File daftar dependensi proyek
```

---

## 🛠️ Persyaratan & Instalasi

Proyek ini dikembangkan menggunakan **Python 3.14+**. Ikuti langkah-langkah di bawah ini untuk menyiapkan lingkungan kerja Anda:

1. **Clone atau Buka Direktori Proyek**:
   Masuk ke direktori kerja proyek Anda.

2. **Siapkan Virtual Environment (Rekomendasi)**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Untuk macOS/Linux
   # venv\Scripts\activate   # Untuk Windows
   ```

3. **Instal Dependensi**:
   ```bash
   pip install -r requirements.txt
   ```
   *Catatan: Jika file `requirements.txt` belum ada, jalankan perintah instalasi berikut:*
   ```bash
   pip install twifork pandas Sastrawi nltk scikit-learn matplotlib seaborn wordcloud imbalanced-learn httpx
   ```

---

## 🚀 Cara Menjalankan Proyek

Langkah-langkah dijalankan secara berurutan sesuai dengan tahapan analisis data:

### Langkah 1: Pengumpulan Data (Data Crawling)
Jalankan crawler untuk mengambil tweet terkait kenaikan harga Pertamax. Script ini menggunakan library `twifork` (pengganti `twikit` yang stabil dari bug parsing X/Twitter saat ini) menggunakan token otentikasi akun X.
```bash
python src/crawling.py
```
*Hasil: File mentah disimpan di `data/raw/tweets.csv`.*

### Langkah 2: Preprocessing Data
Lakukan pembersihan teks mentah (case folding, pembersihan tautan/mention/hashtag/emoji, normalisasi kata slang alay, filtering stopword bahasa Indonesia, dan stemming kata dasar menggunakan Sastrawi).
```bash
python src/preprocess.py
```
*Hasil: Dataset bersih disimpan di `data/processed/preprocessed_tweets.csv`.*

### Langkah 3: Pelabelan Sentimen (Sentiment Labeling)
Lakukan pelabelan otomatis terhadap data latih ke dalam kelas **Positif, Negatif, atau Netral** menggunakan metode leksikon InSet yang ditingkatkan dengan aturan negasi dan penyesuaian kata kunci khusus domain (seperti `naik` dan `mahal` didefinisikan sebagai negatif).
```bash
python src/labeling.py
```
*Hasil: Data berlabel disimpan di `data/processed/labeled_tweets.csv`.*

### Langkah 4: Pemodelan SVM & Evaluasi
Lakukan ekstraksi fitur menggunakan TF-IDF (unigram & bigram) dan latih model klasifikasi SVM. Script ini melakukan pencarian parameter terbaik (GridSearchCV) pada kernel **Linear, Polynomial, dan RBF** serta membandingkan teknik penyeimbang kelas antara **Class Weighting** (Rekomendasi) dan **SMOTE**.
```bash
python src/train_svm.py
```
*Hasil: Laporan evaluasi disimpan di `data/processed/classification_report.txt` dan visualisasi disimpan di `data/processed/`.*

---

## 📊 Metodologi & Hasil Evaluasi Model

### 1. Perbandingan Performa antar-Kernel SVM (GridSearchCV):
Dari pencarian Grid Search CV (5-Fold Cross Validation), kernel **RBF (Radial Basis Function)** terbukti sebagai model paling optimal untuk dataset sentimen ini:
- **RBF**: Mean CV Macro F1 = **0.5781** (Best Parameter: `C=100`, `gamma='auto'`)
- **Linear**: Mean CV Macro F1 = **0.5547**
- **Polynomial**: Mean CV Macro F1 = **0.4867**

### 2. Hasil Klasifikasi pada Data Uji (Metode Class Weighting):
Metode *Class Weighting* (`class_weight='balanced'`) dipilih sebagai default karena terbukti menghasilkan nilai recall (sensitivitas) yang jauh lebih seimbang pada kelas minoritas dibanding SMOTE.

```
              precision    recall  f1-score   support

    Negative       0.89      0.77      0.83        71
     Neutral       0.31      0.31      0.31        13
    Positive       0.28      0.44      0.34        16

    accuracy                           0.66       100
   macro avg       0.49      0.51      0.49       100
weighted avg       0.71      0.66      0.68       100
```

---

## 📝 Ringkasan Analisis Kebijakan

1. **Dominasi Sentimen Negatif (70,9%)**: Disebabkan oleh kesenjangan (*gap*) harga yang terlalu tinggi antara Pertamax (Rp16.250) dan Pertalite bersubsidi (Rp10.000). Hal ini memicu migrasi besar-besaran konsumen Pertamax ke Pertalite yang berujung pada kelangkaan BBM bersubsidi dan antrean panjang di SPBU.
2. **Sentimen Positif (16,5%)**: Mayoritas berupa kritik tidak langsung yang membandingkan kebijakan harga dengan Malaysia (di mana RON 95 disubsidi penuh dan lebih murah dari Pertamax Indonesia) serta harapan/tuntutan agar harga diturunkan demi meringankan beban transportasi harian masyarakat.
