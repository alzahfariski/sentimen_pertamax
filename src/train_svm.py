import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.metrics import classification_report, confusion_matrix
from wordcloud import WordCloud
from imblearn.over_sampling import SMOTE

def train_and_evaluate():
    labeled_path = "data/processed/labeled_tweets.csv"
    artifact_dir = "/Users/alzahfariski/.gemini/antigravity/brain/a08df006-7f51-41d8-841b-10917e4e54c8"
    processed_dir = "data/processed"
    
    if not os.path.exists(labeled_path):
        print(f"Error: {labeled_path} not found. Please label data first.")
        return
        
    print("Loading labeled dataset...")
    df = pd.read_csv(labeled_path)
    
    # Clean any empty text rows
    df = df.dropna(subset=['preprocessed_text'])
    df = df[df['preprocessed_text'].str.strip() != ""]
    
    print(f"Loaded {len(df)} non-empty labeled tweets.")
    
    # 1. Feature Extraction: TF-IDF Vectorizer
    print("Extracting TF-IDF features...")
    vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
    X = vectorizer.fit_transform(df['preprocessed_text'])
    y = df['sentiment']
    
    # 2. Train-Test Split (Stratified to handle class imbalance)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"Training set size: {X_train.shape[0]}")
    print(f"Test set size:     {X_test.shape[0]}")
    
    # Toggle for Class Imbalance Method:
    # Set USE_SMOTE = True to use SMOTE (oversampling)
    # Set USE_SMOTE = False to use Class Weighting (recommended for better minority recall)
    USE_SMOTE = False
    
    if USE_SMOTE:
        # Apply SMOTE to handle class imbalance (only on training set!)
        print("\nApplying SMOTE to resample minority classes in the training set...")
        smote = SMOTE(random_state=42)
        X_train_fit, y_train_fit = smote.fit_resample(X_train, y_train)
        print(f"Resampled training set size: {X_train_fit.shape[0]}")
        print("Resampled class distribution:")
        print(pd.Series(y_train_fit).value_counts())
        
        # Grid Search with Standard SVM
        print("\nRunning Grid Search for SVM hyperparameters on SMOTE-resampled training data...")
        param_grid = [
            {
                'kernel': ['linear'],
                'C': [0.1, 1, 10, 100]
            },
            {
                'kernel': ['rbf'],
                'C': [0.1, 1, 10, 100],
                'gamma': ['scale', 'auto', 0.01, 0.1, 1]
            },
            {
                'kernel': ['poly'],
                'C': [0.1, 1, 10, 100],
                'degree': [2, 3],
                'gamma': ['scale', 'auto', 0.01, 0.1, 1]
            }
        ]
        grid = GridSearchCV(SVC(random_state=42), param_grid, cv=5, scoring='f1_macro', n_jobs=-1)
    else:
        # No SMOTE, fit on original stratified training set
        X_train_fit, y_train_fit = X_train, y_train
        
        # Grid Search with Balanced Class Weight SVM (recommended)
        print("\nRunning Grid Search for SVM with Class Weighting...")
        param_grid = [
            {
                'kernel': ['linear'],
                'C': [0.1, 1, 10, 100]
            },
            {
                'kernel': ['rbf'],
                'C': [0.1, 1, 10, 100],
                'gamma': ['scale', 'auto', 0.01, 0.1, 1]
            },
            {
                'kernel': ['poly'],
                'C': [0.1, 1, 10, 100],
                'degree': [2, 3],
                'gamma': ['scale', 'auto', 0.01, 0.1, 1]
            }
        ]
        grid = GridSearchCV(SVC(random_state=42, class_weight='balanced'), param_grid, cv=5, scoring='f1_macro', n_jobs=-1)
        
    grid.fit(X_train_fit, y_train_fit)
    # Extract results for each kernel
    cv_results = pd.DataFrame(grid.cv_results_)
    comparison_data = []
    for kernel in ['linear', 'rbf', 'poly']:
        kernel_results = cv_results[cv_results['param_kernel'] == kernel]
        if not kernel_results.empty:
            best_idx = kernel_results['mean_test_score'].idxmax()
            best_row = kernel_results.loc[best_idx]
            comparison_data.append({
                'Kernel': kernel,
                'Best Params': str(best_row['params']),
                'Mean CV Macro F1': best_row['mean_test_score']
            })
    df_comparison = pd.DataFrame(comparison_data)
    print("\n--- Kernel Performance Comparison (Grid Search CV Results) ---")
    print(df_comparison.to_string(index=False))
    
    # 4. Model Evaluation
    best_model = grid.best_estimator_
    y_pred = best_model.predict(X_test)
    
    print("\n--- Classification Report ---")
    report = classification_report(y_test, y_pred)
    print(report)
    
    # Generate Confusion Matrix
    labels = sorted(y.unique())
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    
    # Save Classification Report and Comparison as text file in workspace
    with open(os.path.join(processed_dir, "classification_report.txt"), "w") as f:
        f.write("=== CLASSIFICATION REPORT ===\n")
        f.write(report)
        f.write(f"\nBest parameters: {grid.best_params_}\n")
        f.write("\n=== KERNEL PERFORMANCE COMPARISON ===\n")
        f.write(df_comparison.to_string(index=False))
        f.write("\n")
    
    # 5. Visualizations
    
    # Plot 1: Sentiment Distribution
    plt.figure(figsize=(6, 4))
    sns.countplot(x='sentiment', data=df, order=['Negative', 'Positive', 'Neutral'], palette='viridis')
    plt.title('Sentiment Distribution of X (Twitter) Comments')
    plt.xlabel('Sentiment')
    plt.ylabel('Count')
    plt.tight_layout()
    plt.savefig(os.path.join(processed_dir, "sentiment_distribution.png"), dpi=150)
    plt.savefig(os.path.join(artifact_dir, "sentiment_distribution.png"), dpi=150)
    plt.close()
    
    # Plot 2: Confusion Matrix Heatmap
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', xticklabels=labels, yticklabels=labels, cmap='Blues')
    plt.title('Confusion Matrix - SVM Classifier')
    plt.ylabel('Actual Sentiment')
    plt.xlabel('Predicted Sentiment')
    plt.tight_layout()
    plt.savefig(os.path.join(processed_dir, "confusion_matrix.png"), dpi=150)
    plt.savefig(os.path.join(artifact_dir, "confusion_matrix.png"), dpi=150)
    plt.close()
    
    # Plot 3 & 4: Word Clouds for Positive and Negative sentiments
    print("\nGenerating Word Clouds...")
    # Positive Word Cloud
    pos_text = " ".join(df[df['sentiment'] == 'Positive']['preprocessed_text'].tolist())
    if pos_text:
        wc_pos = WordCloud(width=800, height=400, background_color='white', colormap='Greens').generate(pos_text)
        plt.figure(figsize=(10, 5))
        plt.imshow(wc_pos, interpolation='bilinear')
        plt.axis('off')
        plt.title('Word Cloud - Positive Sentiments')
        plt.tight_layout()
        plt.savefig(os.path.join(processed_dir, "positive_wordcloud.png"), dpi=150)
        plt.savefig(os.path.join(artifact_dir, "positive_wordcloud.png"), dpi=150)
        plt.close()
        
    # Negative Word Cloud
    neg_text = " ".join(df[df['sentiment'] == 'Negative']['preprocessed_text'].tolist())
    if neg_text:
        wc_neg = WordCloud(width=800, height=400, background_color='white', colormap='Reds').generate(neg_text)
        plt.figure(figsize=(10, 5))
        plt.imshow(wc_neg, interpolation='bilinear')
        plt.axis('off')
        plt.title('Word Cloud - Negative Sentiments')
        plt.tight_layout()
        plt.savefig(os.path.join(processed_dir, "negative_wordcloud.png"), dpi=150)
        plt.savefig(os.path.join(artifact_dir, "negative_wordcloud.png"), dpi=150)
        plt.close()
        
    print("\nAll plots generated and saved successfully to data/processed/ and the artifact folder.")

if __name__ == '__main__':
    train_and_evaluate()
