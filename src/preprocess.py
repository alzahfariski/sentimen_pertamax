import os
import re
import urllib.request
import pandas as pd
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

def download_slang_dictionary():
    url = "https://raw.githubusercontent.com/nasalsabila/kamus-alay/master/colloquial-indonesian-lexicon.csv"
    filepath = "data/raw/colloquial-indonesian-lexicon.csv"
    if not os.path.exists(filepath):
        print(f"Downloading slang dictionary from {url}...")
        urllib.request.urlretrieve(url, filepath)
        print("Slang dictionary downloaded successfully.")
    else:
        print("Slang dictionary already exists locally.")
    return filepath

def load_slang_dict(filepath):
    # The colloquial-indonesian-lexicon.csv has columns: slang, formal, in-dictionary, context
    df_slang = pd.read_csv(filepath)
    # We map slang column to formal column
    slang_dict = dict(zip(df_slang['slang'], df_slang['formal']))
    return slang_dict

def clean_text(text):
    if not isinstance(text, str):
        return ""
    # 1. Case folding
    text = text.lower()
    # 2. Remove URLs
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    # 3. Remove mentions (@username)
    text = re.sub(r'@\w+', '', text)
    # 4. Remove hashtags (#topic)
    text = re.sub(r'#\w+', '', text)
    # 5. Remove numbers
    text = re.sub(r'\d+', '', text)
    # 6. Remove punctuation and non-alphabetic characters (which also removes emojis)
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    # 7. Remove extra whitespaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def preprocess_dataframe():
    # File paths
    raw_tweets_path = "data/raw/tweets.csv"
    processed_tweets_path = "data/processed/preprocessed_tweets.csv"
    
    if not os.path.exists(raw_tweets_path):
        print(f"Error: {raw_tweets_path} does not exist. Please crawl data first.")
        return
        
    # Download and load slang dict
    slang_path = download_slang_dictionary()
    slang_dict = load_slang_dict(slang_path)
    
    # Load raw tweets
    print("Loading raw tweets...")
    df = pd.read_csv(raw_tweets_path)
    print(f"Loaded {len(df)} tweets.")
    
    # Initialize Sastrawi stemmer and stopwords
    print("Initializing Sastrawi components...")
    stemmer_factory = StemmerFactory()
    stemmer = stemmer_factory.create_stemmer()
    
    stopword_factory = StopWordRemoverFactory()
    # Get standard Sastrawi stopwords and convert to set for fast lookup
    stopwords_list = stopword_factory.get_stop_words()
    stop_words = set(stopwords_list)
    
    # Add custom Indonesian stopwords commonly found in tweets if needed
    custom_stopwords = {'yg', 'dg', 'rt', 'dr', 'sih', 'deh', 'loh', 'kok', 'dgn', 'kalo', 'amp', 'x', 'twitter'}
    stop_words.update(custom_stopwords)
    
    preprocessed_data = []
    
    print("Preprocessing tweets (this may take a couple of minutes due to stemming)...")
    for idx, row in df.iterrows():
        original_text = row['text']
        
        # 1 & 2. Cleaning and Case folding
        cleaned = clean_text(original_text)
        
        # 3 & 4. Tokenizing and Slang Normalization
        words = cleaned.split()
        normalized_words = [slang_dict.get(word, word) for word in words]
        
        # 5. Stopword Removal
        filtered_words = [word for word in normalized_words if word not in stop_words]
        
        # 6. Stemming (run on sentence level for efficiency in Sastrawi)
        filtered_sentence = " ".join(filtered_words)
        if filtered_sentence:
            stemmed = stemmer.stem(filtered_sentence)
        else:
            stemmed = ""
            
        preprocessed_data.append({
            'tweet_id': row['tweet_id'],
            'created_at': row['created_at'],
            'user_name': row['user_name'],
            'screen_name': row['screen_name'],
            'original_text': original_text,
            'cleaned_text': cleaned,
            'normalized_text': " ".join(normalized_words),
            'preprocessed_text': stemmed
        })
        
        if (idx + 1) % 50 == 0 or (idx + 1) == len(df):
            print(f"Processed {idx + 1}/{len(df)} tweets...")
            
    df_processed = pd.DataFrame(preprocessed_data)
    
    # Remove empty processed tweets
    initial_len = len(df_processed)
    df_processed = df_processed[df_processed['preprocessed_text'].str.strip() != ""]
    print(f"Removed {initial_len - len(df_processed)} empty preprocessed tweets.")
    
    # Save to CSV
    os.makedirs(os.path.dirname(processed_tweets_path), exist_ok=True)
    df_processed.to_csv(processed_tweets_path, index=False, encoding='utf-8')
    print(f"Saved preprocessed data to {processed_tweets_path}")
    
    # Show samples
    print("\n--- Preprocessing Samples ---")
    for i in range(min(5, len(df_processed))):
        print(f"\nSample {i+1}:")
        print(f"Original: {df_processed.iloc[i]['original_text']}")
        print(f"Cleaned:  {df_processed.iloc[i]['cleaned_text']}")
        print(f"Normal:   {df_processed.iloc[i]['normalized_text']}")
        print(f"Final:    {df_processed.iloc[i]['preprocessed_text']}")

if __name__ == '__main__':
    preprocess_dataframe()
