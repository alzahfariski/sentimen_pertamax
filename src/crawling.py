import asyncio
import json
import os
import random
import httpx
import pandas as pd
from twikit import Client

from dotenv import load_dotenv

# Load .env file
load_dotenv()

async def main():
    auth_token = os.getenv('TWITTER_AUTH_TOKEN')
    if not auth_token:
        print("Error: TWITTER_AUTH_TOKEN is missing in .env file or environment.")
        return
        
    limit = 500
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
    
    # Let's search using the query
    query = 'pertamax naik OR harga pertamax OR pertamax 16250 since:2026-06-01 until:2026-07-18'
    print(f"Starting crawl for query: '{query}'")
    
    all_tweets = []
    seen_ids = set()
    
    try:
        # Initial search
        tweets = await client.search_tweet(query, product='Latest')
        if not tweets:
            print("No tweets found in initial search.")
            return
            
        for t in tweets:
            if t.id not in seen_ids:
                seen_ids.add(t.id)
                all_tweets.append({
                    'tweet_id': t.id,
                    'created_at': t.created_at,
                    'user_name': t.user.name,
                    'screen_name': t.user.screen_name,
                    'text': t.text,
                    'favorite_count': t.favorite_count,
                    'retweet_count': t.retweet_count
                })
        
        print(f"Fetched {len(all_tweets)} tweets from initial page.")
        
        # Paginate
        page = 1
        while len(all_tweets) < limit:
            print(f"Fetching page {page + 1}... Current total: {len(all_tweets)}")
            
            # Wait a bit to avoid rate limits
            delay = random.uniform(2.0, 5.0)
            await asyncio.sleep(delay)
            
            next_tweets = await tweets.next()
            if not next_tweets:
                print("No more tweets available.")
                break
                
            new_tweets_count = 0
            for t in next_tweets:
                if t.id not in seen_ids:
                    seen_ids.add(t.id)
                    all_tweets.append({
                        'tweet_id': t.id,
                        'created_at': t.created_at,
                        'user_name': t.user.name,
                        'screen_name': t.user.screen_name,
                        'text': t.text,
                        'favorite_count': t.favorite_count,
                        'retweet_count': t.retweet_count
                    })
                    new_tweets_count += 1
            
            print(f"Added {new_tweets_count} new tweets.")
            if new_tweets_count == 0:
                print("No new tweets found on this page, stopping.")
                break
                
            tweets = next_tweets
            page += 1
            
    except Exception as e:
        print(f"Error during crawling: {e}")
        
    print(f"Crawling finished. Total tweets scraped: {len(all_tweets)}")
    
    if all_tweets:
        df = pd.DataFrame(all_tweets)
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Saved {len(df)} tweets to {output_file}")
    else:
        print("No tweets collected to save.")

if __name__ == '__main__':
    asyncio.run(main())
