import os
import random
import pandas as pd

folder = r'C:\Users\bunny\Desktop\texts'
novels = [f.split('.')[0] for f in os.listdir(folder) if f.startswith('novel_')]

data = []
for novel in novels:
    with open(os.path.join(folder, novel + '.txt')) as f:
        text = f.read()[3000:]

        for i in range(random.randint(200, 400)):
            start = random.randint(0, len(text) - 1000)
            passage = text[start:start + random.randint(50, 200)]

            # Remove newlines
            passage = passage.replace('\n', ' ')

            # Remove commas
            passage = passage.replace(',', '')

            data.append((novel, passage))

random.shuffle(data)

df = pd.DataFrame(data, columns=['TaskName', 'ScrubbedMessage'])
df.to_csv('novel_data.csv', index=False)