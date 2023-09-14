import pandas as pd
from sklearn.model_selection import train_test_split
import json

# Load your CSV file
df = pd.read_csv('novel_data.csv')

# Ensure that each label appears in both the training and validation sets
train_data, val_data = train_test_split(df, stratify=df['TaskName'], test_size=0.2, random_state=42)

# Save the training and validation data as JSONL files
with open('train_data.jsonl', 'w', encoding='utf-8') as f:
    for _, row in train_data.iterrows():
        json_data = {"completion": row['TaskName'], "prompt": row['ScrubbedMessage']}
        f.write(json.dumps(json_data, ensure_ascii=False) + '\n')

with open('val_data.jsonl', 'w', encoding='utf-8') as f:
    for _, row in val_data.iterrows():
        json_data = {"completion": row['TaskName'], "prompt": row['ScrubbedMessage']}
        f.write(json.dumps(json_data, ensure_ascii=False) + '\n')

