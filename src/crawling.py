import asyncio
import json
import os
import random
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

# Load .env file
load_dotenv()

# Pastikan semua output print langsung tampil tanpa buffering
import builtins
_orig_print = builtins.print
def print(*args, **kwargs):
    kwargs.setdefault('flush', True)
    return _orig_print(*args, **kwargs)

def save_data(tweets_list, filepath):
    """Menyimpan list tweet ke file CSV."""
    if tweets_list:
        df = pd.DataFrame(tweets_list)
        df.to_csv(filepath, index=False, encoding='utf-8', lineterminator='\n')

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
    auth_token = os.getenv('TWITTER_AUTH_TOKEN')
    if not auth_token:
        print("Error: TWITTER_AUTH_TOKEN is missing in .env file or environment.")
        return
        
    limit = 3000
    output_dir = 'data/raw'
    output_file = os.path.join(output_dir, 'tweets.csv')
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Request X.com with the auth_token to get the ct0 cookie
    headers = {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    cookies = {
        'auth_token': auth_token
    }
    
    print("Retrieving session cookies from x.com...")
    async with httpx.AsyncClient(headers=headers, cookies=cookies, follow_redirects=True) as client_httpx:
        response = await client_httpx.get('https://x.com/')
        print(f"Response status: {response.status_code}")
        for name, value in client_httpx.cookies.items():
            cookies[name] = value
            
    if 'ct0' not in cookies:
        print("Warning: ct0 (CSRF token) not found in cookies. Setting a dummy ct0...")
        cookies['ct0'] = '1234567890abcdef1234567890abcdef'
    
    print(f"Loaded cookies: {list(cookies.keys())}")
    
    # 2. Initialize Twikit Client
    client = Client('en-US')
    client.set_cookies(cookies)
    
    # Query pencarian
    query = 'pertamax naik OR harga pertamax OR pertamax 16250 since:2026-06-01 until:2026-07-18'
    print(f"Starting crawl for query: '{query}' (Target: {limit} tweets)")
    
    all_tweets = []
    seen_ids = set()
    
    # Muat data yang sudah pernah terkumpul agar tidak hilang dan bisa melanjutkan
    if os.path.exists(output_file):
        try:
            existing_df = pd.read_csv(output_file, dtype={'tweet_id': str}, encoding='utf-8')
            for _, row in existing_df.iterrows():
                t_id = str(row['tweet_id'])
                if t_id not in seen_ids:
                    seen_ids.add(t_id)
                    all_tweets.append(row.to_dict())
            print(f"[INFO] Ditemukan {len(all_tweets)} tweet yang sudah tersimpan sebelumnya di {output_file}.")
            if len(all_tweets) >= limit:
                print(f"[INFO] Target {limit} tweet sudah tercapai! Tidak perlu crawling lagi.")
                return
            print(f"[INFO] Melanjutkan pengumpulan sisa {limit - len(all_tweets)} tweet...")
        except Exception as e:
            print(f"[WARNING] Gagal memuat data lama dari {output_file}: {e}")
    
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
            t_id = str(t.id)
            if t_id not in seen_ids:
                seen_ids.add(t_id)
                all_tweets.append({
                    'tweet_id': t_id,
                    'created_at': t.created_at,
                    'user_name': t.user.name,
                    'screen_name': t.user.screen_name,
                    'text': t.text,
                    'favorite_count': t.favorite_count,
                    'retweet_count': t.retweet_count
                })
                initial_new += 1
        
        print(f"Initial page: {len(tweets)} tweets ({initial_new} baru). Total sekarang: {len(all_tweets)}/{limit}")
        if initial_new > 0:
            save_data(all_tweets, output_file)
        
        # Paginate
        page = 1
        consecutive_empty_batches = 0
        
        while len(all_tweets) < limit:
            # Delay antara 4.0 - 7.0 detik untuk stabilitas
            delay = random.uniform(4.0, 7.0)
            await asyncio.sleep(delay)
            
            print(f"Fetching page {page + 1}... (Terkumpul: {len(all_tweets)}/{limit})")
            
            next_tweets = await fetch_with_rate_limit_retry(
                lambda: tweets.next(),
                action_name=f"mengambil halaman {page + 1}"
            )
            
            if not next_tweets or len(next_tweets) == 0:
                consecutive_empty_batches += 1
                if consecutive_empty_batches >= 3:
                    print("[INFO] Twitter tidak mengembalikan tweet lagi (mencapai akhir timeline pencarian).")
                    break
                print("[INFO] Halaman kosong dari Twitter, mencoba halaman berikutnya...")
                tweets = next_tweets
                page += 1
                continue
            else:
                consecutive_empty_batches = 0
                
            new_tweets_count = 0
            for t in next_tweets:
                t_id = str(t.id)
                if t_id not in seen_ids:
                    seen_ids.add(t_id)
                    all_tweets.append({
                        'tweet_id': t_id,
                        'created_at': t.created_at,
                        'user_name': t.user.name,
                        'screen_name': t.user.screen_name,
                        'text': t.text,
                        'favorite_count': t.favorite_count,
                        'retweet_count': t.retweet_count
                    })
                    new_tweets_count += 1
            
            print(f"  -> Halaman {page + 1}: {len(next_tweets)} tweet diterima ({new_tweets_count} baru). Total: {len(all_tweets)}/{limit}")
            
            # Autosave setiap kali ada tweet baru
            if new_tweets_count > 0:
                save_data(all_tweets, output_file)
                    
            tweets = next_tweets
            page += 1
            
    except Exception as e:
        print(f"\n[ERROR] Terjadi error tak terduga: {e}")
        
    save_data(all_tweets, output_file)
    print(f"\n==========================================")
    print(f"Crawling selesai! Total tweet tersimpan: {len(all_tweets)} ke {output_file}")
    print(f"==========================================")

if __name__ == '__main__':
    asyncio.run(main())
