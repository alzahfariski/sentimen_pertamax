import argparse
import asyncio
import csv
import json
import os
import random
import re
import sys
import time
from datetime import datetime
import httpx
import pandas as pd
from twikit import Client
from twikit.errors import TooManyRequests, TwitterException
from dotenv import load_dotenv

# Konfigurasi encoding untuk Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Pastikan load .env dari direktori project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path)

# Pastikan semua output print langsung tampil tanpa buffering
import builtins
_orig_print = builtins.print
def print(*args, **kwargs):
    kwargs.setdefault('flush', True)
    return _orig_print(*args, **kwargs)

def clean_text_for_csv(text):
    """
    Membersihkan newline, carriage return, tabs, dan spasi berlebih 
    agar format teks rapi dan tidak merusak baris pada file CSV.
    """
    if not text:
        return ""
    # Ganti enter/carriage return/tab menjadi spasi
    cleaned = re.sub(r'[\r\n\t]+', ' ', str(text))
    # Normalisasi spasi ganda menjadi spasi tunggal
    cleaned = re.sub(r' +', ' ', cleaned).strip()
    return cleaned

def is_relevant_tweet(text):
    """
    Memvalidasi apakah teks tweet benar-benar mengandung topik PPN / kenaikan pajak,
    bukan sekadar akun pengguna yang bernama 'PPN 12%' tetapi tweet-nya membahas hal lain.
    """
    if not text:
        return False
    t = text.lower()
    # 1. Mengandung kata 'ppn'
    if 'ppn' in t:
        return True
    # 2. Mengandung kata 'pajak' dan konteks kenaikan / 12% / kebijakan
    if 'pajak' in t:
        keywords = [
            'naik', 'kenaikan', '12%', '12 %', '12 persen', 'dua belas persen',
            'tarif', 'beban', 'uu', 'dpr', 'menteri', 'sri mulyani', 'pemerintah', 
            'rakyat', 'daya beli', 'ekonomi', 'inflasi', 'potong'
        ]
        if any(k in t for k in keywords):
            return True
    return False

def extract_tweet_info(t):
    """Mengekstrak atribut tweet menjadi dictionary dengan format rapi."""
    t_id = str(t.id)
    screen_name = str(getattr(t.user, 'screen_name', '')) if hasattr(t, 'user') else ''
    user_name = clean_text_for_csv(getattr(t.user, 'name', '')) if hasattr(t, 'user') else ''
    raw_text = getattr(t, 'text', '')
    cleaned_text = clean_text_for_csv(raw_text)
    
    fav_count = getattr(t, 'favorite_count', 0) or 0
    rt_count = getattr(t, 'retweet_count', 0) or 0
    reply_count = getattr(t, 'reply_count', 0) or 0
    created_at = str(getattr(t, 'created_at', ''))
    tweet_url = f"https://x.com/{screen_name}/status/{t_id}" if screen_name and t_id else ""
    
    return {
        'tweet_id': t_id,
        'created_at': created_at,
        'user_name': user_name,
        'screen_name': screen_name,
        'text': cleaned_text,
        'favorite_count': fav_count,
        'retweet_count': rt_count,
        'reply_count': reply_count,
        'tweet_url': tweet_url
    }

def save_data(tweets_list, filepath):
    """Menyimpan list tweet ke file CSV dengan encoding utf-8-sig dan deduplikasi."""
    if not tweets_list:
        return
    df = pd.DataFrame(tweets_list)
    # Pastikan tweet_id berupa string agar digit panjang tidak terpotong di Excel
    df['tweet_id'] = df['tweet_id'].astype(str)
    # Hapus duplikasi berdasarkan tweet_id
    df = df.drop_duplicates(subset=['tweet_id'], keep='first')
    
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    df.to_csv(
        filepath,
        index=False,
        encoding='utf-8-sig',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator='\n'
    )

async def fetch_with_rate_limit_retry(fetch_fn, action_name="fetching tweets", max_retries=30):
    """
    Menjalankan request twikit dengan penanganan otomatis jika terkena error 429 (Rate Limit).
    Jika terkena 429, fungsi akan menghitung mundur waktu tunggu hingga reset window selesai,
    lalu mencoba request kembali secara otomatis tanpa membatalkan proses crawling.
    """
    retries = 0
    while retries < max_retries:
        try:
            return await fetch_fn()
        except TooManyRequests as e:
            retries += 1
            now = time.time()
            if hasattr(e, 'rate_limit_reset') and e.rate_limit_reset and e.rate_limit_reset > now:
                wait_seconds = int(e.rate_limit_reset - now) + 10
                reset_time_str = datetime.fromtimestamp(e.rate_limit_reset).strftime('%H:%M:%S')
                print(f"\n[429 RATE LIMIT] Batas request Twitter tercapai saat {action_name}.")
                print(f"Jendela batas request akan di-reset pada pukul {reset_time_str}.")
                print(f"Otomatis menunggu selama {wait_seconds} detik (~{wait_seconds // 60} menit)...")
            else:
                wait_seconds = 910  # 15 menit default + 10 detik buffer
                print(f"\n[429 RATE LIMIT] Batas request Twitter tercapai saat {action_name}.")
                print(f"Otomatis menunggu 15 menit ({wait_seconds} detik) hingga rate limit di-reset...")
            
            # Hitung mundur periodik
            step = 30
            while wait_seconds > 0:
                sleep_time = min(step, wait_seconds)
                await asyncio.sleep(sleep_time)
                wait_seconds -= sleep_time
                if wait_seconds > 0:
                    print(f"   [COOLDOWN] Sisa waktu tunggu: {wait_seconds} detik (~{wait_seconds // 60} menit)...")
            
            print(f"[COOLDOWN SELESAI] Melanjutkan crawling kembali...\n")
        except Exception as e:
            retries += 1
            print(f"\n[WARNING] Terjadi kendala saat {action_name}: {e}")
            if retries >= max_retries:
                raise e
            wait_seconds = 15
            print(f"Mencoba kembali dalam {wait_seconds} detik (percobaan {retries}/{max_retries})...")
            await asyncio.sleep(wait_seconds)
            
    return None

async def main():
    parser = argparse.ArgumentParser(description="Twitter / X Crawling Script untuk Sentimen PPN 12%")
    parser.add_argument('--limit', type=int, default=None, help='Target total absolut jumlah tweet (opsional)')
    parser.add_argument('--add-limit', type=int, default=3000, help='Target jumlah tweet baru yang ingin ditambahkan (default: 3000)')
    parser.add_argument('--output', type=str, default='data/raw/tweets1.csv', help='Path output file CSV (default: data/raw/tweets1.csv)')
    parser.add_argument('--since', type=str, default='2024-10-01', help='Tanggal awal periode (default: 2024-10-01)')
    parser.add_argument('--until', type=str, default='2024-12-31', help='Tanggal akhir periode (default: 2024-12-31)')
    parser.add_argument('--query', type=str, default=None, help='Query kustom penuh (opsional)')
    parser.add_argument('--no-filter', action='store_true', help='Nonaktifkan filter relevansi teks tweet')
    args = parser.parse_args()

    auth_token = os.getenv('TWITTER_AUTH_TOKEN', '').strip()
    if not auth_token:
        print("Error: TWITTER_AUTH_TOKEN is missing in .env file or environment.")
        return
        
    output_file = os.path.abspath(args.output)
    filter_relevance = not args.no_filter
    
    # Susun query pencarian
    base_keywords = '("ppn 12%" OR "ppn naik" OR "kenaikan ppn" OR "kenaikan pajak" OR "ppn 12 persen" OR "pajak 12%")'
    if args.query:
        query = args.query
    elif args.since and args.until:
        query = f"{base_keywords} since:{args.since} until:{args.until}"
    elif args.since:
        query = f"{base_keywords} since:{args.since}"
    else:
        query = base_keywords
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # 1. Request X.com with the auth_token to get the session cookies & ct0
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    cookies = {
        'auth_token': auth_token
    }
    
    print("Retrieving session cookies from x.com...")
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client_httpx:
        client_httpx.cookies.set('auth_token', auth_token, domain='.x.com')
        response = await client_httpx.get('https://x.com/')
        print(f"Response status: {response.status_code}")
        for cookie in client_httpx.cookies.jar:
            cookies[cookie.name] = cookie.value
            
    if 'ct0' not in cookies:
        print("Warning: ct0 (CSRF token) not found in cookies. Setting a dummy ct0...")
        cookies['ct0'] = '1234567890abcdef1234567890abcdef'
    
    print(f"Loaded cookies: {list(cookies.keys())}")
    
    # 2. Initialize Twikit Client
    client = Client('en-US')
    client.set_cookies(cookies)
    
    all_tweets = []
    seen_ids = set()
    
    # Muat data yang sudah pernah terkumpul sebelumnya jika ada
    if os.path.exists(output_file):
        try:
            existing_df = pd.read_csv(output_file, dtype={'tweet_id': str}, encoding='utf-8-sig')
            for _, row in existing_df.iterrows():
                t_id = str(row['tweet_id'])
                if t_id not in seen_ids:
                    seen_ids.add(t_id)
                    all_tweets.append(row.to_dict())
            print(f"[INFO] Ditemukan {len(all_tweets)} tweet yang sudah tersimpan sebelumnya di {output_file}.")
        except Exception as e:
            print(f"[WARNING] Gagal memuat data lama dari {output_file}: {e}")
            
    initial_count = len(all_tweets)
    if args.limit is not None:
        target_limit = args.limit
    else:
        target_limit = initial_count + args.add_limit
        
    print(f"\n==========================================")
    print(f"Target Query      : {query}")
    print(f"Periode Crawling  : {args.since or '-'} s/d {args.until or '-'}")
    print(f"Data Sebelumnya   : {initial_count} tweets")
    print(f"Target Penambahan : {target_limit - initial_count} tweets baru")
    print(f"Target Total Kuota: {target_limit} tweets")
    print(f"File Output       : {output_file}")
    print(f"Filter Relevansi  : {'Aktif (hanya tweet dengan teks terkait)' if filter_relevance else 'Nonaktif'}")
    print(f"==========================================\n")
    
    if initial_count >= target_limit:
        print(f"[INFO] Target {target_limit} tweet sudah terpenuhi (sudah ada {initial_count} tweet). Tidak perlu crawling lagi.")
        return
    
    try:
        # Initial search dengan penanganan rate limit
        tweets = await fetch_with_rate_limit_retry(
            lambda: client.search_tweet(query, product='Latest'),
            action_name="pencarian awal (initial search)"
        )
        
        if not tweets:
            print("No tweets found in initial search.")
            return
            
        initial_new = 0
        for t in tweets:
            info = extract_tweet_info(t)
            if filter_relevance and not is_relevant_tweet(info['text']):
                continue
            if info['tweet_id'] not in seen_ids:
                seen_ids.add(info['tweet_id'])
                all_tweets.append(info)
                initial_new += 1
        
        print(f"Initial page: {len(tweets)} tweets ({initial_new} lolos & baru). Total sekarang: {len(all_tweets)}/{target_limit}")
        if initial_new > 0:
            save_data(all_tweets, output_file)
        
        # Paginate
        page = 1
        consecutive_empty_batches = 0
        
        while len(all_tweets) < target_limit:
            # Delay antara 4.0 - 7.0 detik untuk menjaga kestabilan request
            delay = random.uniform(4.0, 7.0)
            await asyncio.sleep(delay)
            
            print(f"Fetching page {page + 1}... (Terkumpul: {len(all_tweets)}/{target_limit})")
            
            next_tweets = await fetch_with_rate_limit_retry(
                lambda: tweets.next(),
                action_name=f"mengambil halaman {page + 1}"
            )
            
            if not next_tweets or len(next_tweets) == 0:
                consecutive_empty_batches += 1
                if consecutive_empty_batches >= 3:
                    print("[INFO] Twitter tidak mengembalikan tweet lagi (mencapai batas akhir timeline pencarian periode ini).")
                    break
                print("[INFO] Halaman kosong dari Twitter, mencoba halaman berikutnya...")
                tweets = next_tweets
                page += 1
                continue
            else:
                consecutive_empty_batches = 0
                
            new_tweets_count = 0
            for t in next_tweets:
                info = extract_tweet_info(t)
                if filter_relevance and not is_relevant_tweet(info['text']):
                    continue
                if info['tweet_id'] not in seen_ids:
                    seen_ids.add(info['tweet_id'])
                    all_tweets.append(info)
                    new_tweets_count += 1
            
            print(f"  -> Halaman {page + 1}: {len(next_tweets)} tweet diterima ({new_tweets_count} lolos & baru). Total: {len(all_tweets)}/{target_limit}")
            
            # Autosave setiap kali ada tweet baru
            if new_tweets_count > 0:
                save_data(all_tweets, output_file)
                    
            tweets = next_tweets
            page += 1
            
    except Exception as e:
        print(f"\n[ERROR] Terjadi error tak terduga: {e}")
        
    save_data(all_tweets, output_file)
    print(f"\n==========================================")
    print(f"Crawling selesai! Total akhir tweet tersimpan: {len(all_tweets)} ke {output_file}")
    print(f"==========================================")

if __name__ == '__main__':
    asyncio.run(main())
