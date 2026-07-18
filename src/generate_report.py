import os
import pandas as pd

def df_to_markdown_table(df, max_len=60):
    headers = list(df.columns)
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    
    for idx, row in df.iterrows():
        row_vals = []
        for col in headers:
            val = row[col]
            val_str = str(val).replace('\n', ' ').replace('|', '\\|')
            # Truncate long strings for readability in tables
            if col in ['text', 'original_text', 'cleaned_text', 'preprocessed_text'] and len(val_str) > max_len:
                val_str = val_str[:max_len-3] + "..."
            row_vals.append(val_str)
        lines.append("| " + " | ".join(row_vals) + " |")
        
    return "\n".join(lines)

def generate_report():
    raw_csv = "data/raw/tweets.csv"
    labeled_csv = "data/processed/labeled_tweets.csv"
    output_md = "analysis_results.md"
    
    if not os.path.exists(raw_csv) or not os.path.exists(labeled_csv):
        print("Error: Missing datasets. Make sure to run crawling, preprocessing, and labeling first.")
        return
        
    print("Loading datasets...")
    df_raw = pd.read_csv(raw_csv)
    df_labeled = pd.read_csv(labeled_csv)
    
    # 1. Format Raw Tweets Table (first 10 rows, select key columns)
    raw_cols = ['user_name', 'screen_name', 'text', 'favorite_count']
    df_raw_sample = df_raw[raw_cols].head(10)
    raw_table_md = df_to_markdown_table(df_raw_sample)
    
    # 2. Format Labeled Tweets Table (first 10 rows, select key columns)
    labeled_cols = ['user_name', 'screen_name', 'original_text', 'sentiment_score', 'sentiment']
    df_labeled_sample = df_labeled[labeled_cols].head(10)
    labeled_table_md = df_to_markdown_table(df_labeled_sample)
    
    # 3. Compile the markdown report
    report_content = f"""# Laporan Hasil Analisis Sentimen & Dataset Pertamax RON 92

Laporan ini menyajikan analisis sentimen komentar X (Twitter) terkait kebijakan penyesuaian harga Pertamax (RON 92) dari Rp12.300 menjadi Rp16.250 per liter.

---

## 1. Distribusi Sentimen Masyarakat
Berdasarkan data 498 tweet bersih, distribusi kelas sentimen yang diperoleh adalah:
- **Sentimen Negatif**: 353 tweet (70.9%)
- **Sentimen Positif**: 82 tweet (16.5%)
- **Sentimen Netral**: 63 tweet (12.6%)

Hal ini menunjukkan mayoritas masyarakat merespon **Negatif** terhadap kenaikan harga Pertamax karena memicu antrean panjang dan kelangkaan Pertalite (migrasi konsumen).

---

## 2. Performa Model SVM (Grid Search)
Dari pencarian Grid Search CV (5-Fold Cross Validation), kernel **RBF** terpilih sebagai yang terbaik:
- **Akurasi Global**: 66%
- **Macro F1-Score**: 0.49
- **Best Parameter**: `{{'C': 100, 'gamma': 'auto', 'kernel': 'rbf'}}`

---

## 3. Sampel Tabel Data Mentah (data/raw/tweets.csv)
Berikut adalah 10 baris pertama data mentah hasil crawling Twitter:

{raw_table_md}

---

## 4. Sampel Tabel Data Berlabel (data/processed/labeled_tweets.csv)
Berikut adalah 10 baris pertama data hasil preprocessing dan pelabelan sentimen:

{labeled_table_md}

---

*Catatan: Grafik visualisasi distribusi sentimen, confusion matrix, dan word cloud dapat dilihat di folder `data/processed/`.*
"""

    with open(output_md, 'w', encoding='utf-8') as f:
        f.write(report_content)
        
    print(f"Report successfully saved to {output_md}")

if __name__ == '__main__':
    generate_report()
