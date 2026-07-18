import os
import re
import pandas as pd

def download_inset_lexicon():
    pos_path = "data/raw/positive.tsv"
    neg_path = "data/raw/negative.tsv"
    return pos_path, neg_path

def load_lexicons(pos_path, neg_path):
    df_pos = pd.read_csv(pos_path, sep='\t')
    df_neg = pd.read_csv(neg_path, sep='\t')
    
    df_pos = df_pos.dropna(subset=['word'])
    df_neg = df_neg.dropna(subset=['word'])
    
    df_pos['word'] = df_pos['word'].str.lower()
    df_neg['word'] = df_neg['word'].str.lower()
    
    pos_dict = dict(zip(df_pos['word'], df_pos['weight']))
    neg_dict = dict(zip(df_neg['word'], df_neg['weight']))
    
    return pos_dict, neg_dict

def get_domain_lexicons(pos_path, neg_path):
    pos_dict, neg_dict = load_lexicons(pos_path, neg_path)
    
    # 1. Clean 'mahal' and 'naik' from positive and move/force them to negative
    if 'mahal' in pos_dict:
        del pos_dict['mahal']
    neg_dict['mahal'] = -4
    
    if 'naik' in pos_dict:
        del pos_dict['naik']
    neg_dict['naik'] = -3  # Price hike is negative
    
    if 'turun' in pos_dict:
        del pos_dict['turun']
    pos_dict['turun'] = 3   # Price drop is positive
    
    # 2. Add domain-specific words
    neg_dict.update({
        'antri': -4, 'antre': -4, 'antrean': -4, 'antrian': -4,
        'langka': -4, 'kelangkaan': -4,
        'susah': -4, 'kesulitan': -4, 'ngeluh': -3, 'mengeluh': -4,
        'boros': -4, 'meroket': -4, 'mencekik': -4, 'kacau': -4,
        'berat': -3, 'keberatan': -4, 'menolak': -4, 'tolak': -4,
        'sengsara': -4, 'menyengsarakan': -4, 'pusing': -3,
        'kecewa': -4, 'kesal': -3, 'marah': -4, 'rugi': -4,
        'benci': -4, 'gagal': -3, 'oplosan': -3, 'antrian panjang': -4,
        'mahalnya': -4, 'kenaikan': -3
    })
    
    pos_dict.update({
        'untung': 3, 'bagus': 4, 'baik': 4, 'mantap': 4,
        'setuju': 4, 'murah': 4, 'membantu': 3, 'senang': 4,
        'puas': 4, 'lancar': 3, 'aman': 3, 'hemat': 4,
        'terjangkau': 4
    })
    
    return pos_dict, neg_dict

def is_news_source(screen_name, user_name):
    news_keywords = {
        'kompas', 'detik', 'tempo', 'tribun', 'liputan6', 'cnn', 'cnbc', 
        'antara', 'tvone', 'bloomberg', 'tirto', 'republika', 'kumparan', 
        'jawapos', 'sindo', 'okezone', 'viva', 'merdeka'
    }
    screen_name = str(screen_name).lower()
    user_name = str(user_name).lower()
    for kw in news_keywords:
        if kw in screen_name or kw in user_name:
            return True
    return False

def calculate_sentiment_score(normalized_text, original_text, pos_dict, neg_dict):
    if not isinstance(normalized_text, str):
        return 0
        
    negation_words = {'tidak', 'enggak', 'bukan', 'belum', 'kurang', 'tanpa'}
    words = normalized_text.split()
    score = 0
    
    # 1. Word-level lexicon scoring with negation handling
    for i, word in enumerate(words):
        word_score = 0
        if word in pos_dict:
            word_score += pos_dict[word]
        if word in neg_dict:
            word_score += neg_dict[word]
            
        # If preceded by negation, invert the score
        if i > 0 and words[i-1] in negation_words:
            word_score = -word_score
            
        score += word_score
        
    # 2. Emoji scoring from original text
    neg_emojis = ['😡', '🤬', '😭', '🤮', '💀', '👎', '💩']
    pos_emojis = ['👍', '😊', '❤️', '🤩', '👏']
    
    if isinstance(original_text, str):
        for emo in neg_emojis:
            if emo in original_text:
                score -= 3
        for emo in pos_emojis:
            if emo in original_text:
                score += 3
                
    return score

def label_data():
    preprocessed_path = "data/processed/preprocessed_tweets.csv"
    labeled_path = "data/processed/labeled_tweets.csv"
    
    if not os.path.exists(preprocessed_path):
        print(f"Error: {preprocessed_path} not found. Please preprocess data first.")
        return
        
    pos_path, neg_path = download_inset_lexicon()
    pos_dict, neg_dict = get_domain_lexicons(pos_path, neg_path)
    
    print("Loading preprocessed tweets...")
    df = pd.read_csv(preprocessed_path)
    print(f"Loaded {len(df)} tweets.")
    
    # Calculate score using normalized_text for negation check
    df['sentiment_score'] = df.apply(
        lambda r: calculate_sentiment_score(r['normalized_text'], r['original_text'], pos_dict, neg_dict), 
        axis=1
    )
    
    # Assign labels based on score and source
    sentiments = []
    for idx, row in df.iterrows():
        # Rule 1: News sources are generally Factual/Neutral unless heavily opinionated
        if is_news_source(row['screen_name'], row['user_name']):
            sentiments.append('Neutral')
            continue
            
        score = row['sentiment_score']
        if score > 1:  # Higher threshold to ensure true positivity
            sentiments.append('Positive')
        elif score < 0:
            sentiments.append('Negative')
        else:
            # Rule 2: If score is 0 or 1, check if there are any strong negative words
            # to prevent false positives/neutrality.
            words = str(row['normalized_text']).split()
            has_strong_neg = any(w in ['mahal', 'naik', 'antre', 'antri', 'langka', 'susah', 'boros'] for w in words)
            if has_strong_neg:
                sentiments.append('Negative')
            else:
                sentiments.append('Neutral')
                
    df['sentiment'] = sentiments
    
    print("\nSentiment Distribution:")
    print(df['sentiment'].value_counts())
    
    # Save labeled data
    df.to_csv(labeled_path, index=False, encoding='utf-8')
    print(f"\nSaved labeled dataset to {labeled_path}")
    
    # Print sample of each class
    print("\n--- Sentiment Labeling Samples ---")
    for sentiment in ['Positive', 'Negative', 'Neutral']:
        sample = df[df['sentiment'] == sentiment]
        if not sample.empty:
            print(f"\n{sentiment} Sample:")
            print(f"Original: {sample.iloc[0]['original_text']}")
            print(f"Score:    {sample.iloc[0]['sentiment_score']}")
            print(f"Final:    {sample.iloc[0]['preprocessed_text']}")

if __name__ == '__main__':
    label_data()
