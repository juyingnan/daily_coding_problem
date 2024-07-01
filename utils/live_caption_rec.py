from pywinauto.application import Application
import time
import math
import re
from collections import Counter

WORD = re.compile(r"\w+")

# Cosine similarity https://stackoverflow.com/a/15174569/309846

def get_cosine(vec1, vec2):
    """Calculate cosine similarity between two vectors"""
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])

    sum1 = sum([vec1[x] ** 2 for x in list(vec1.keys())])
    sum2 = sum([vec2[x] ** 2 for x in list(vec2.keys())])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0
    else:
        return float(numerator) / denominator

def text_to_vector(text):
    """Convert text to a vector"""
    words = WORD.findall(text)
    return Counter(words)

def is_text_similar_simple(a, b, theta=0.8):
    """Check if two text strings are similar if:
    - a is starting with b or
    - cosine similarity is greater than \theta
    """
    if len(a) == 0 or len(b) == 0:
        return False
    if a.startswith(b):
        return True
    if b.startswith(a):
        return True

    return get_cosine(text_to_vector(a), text_to_vector(b)) > theta

def find_diff_index(s1, s2):
    """Find the index at which two strings start to differ"""
    min_len = min(len(s1), len(s2))
    for i in range(min_len):
        if s1[i] != s2[i]:
            return i
    return min_len

def merge_texts(old, new):
    """Merge new text with old text, handling corrections and overlaps"""
    overlap_index = old.find(new)
    if overlap_index != -1:
        return old[:overlap_index] + new
    else:
        return old + ' ' + new

if __name__ == '__main__':
    app = Application(backend='uia').connect(path='LiveCaptions.exe')

    transcript = ""
    if not app.is_process_running():
        print("Live Captions is not running")
    else:
        try:
            print('Recording live captions. Press Ctrl+C to stop.')

            text_block = app.top_window().child_window(auto_id="CaptionsTextBlock", control_type="Text")
            previous_text = ""
            while True:
                current_text = text_block.window_text()
                if current_text != previous_text:
                    diff_index = find_diff_index(previous_text, current_text)
                    live_accumulation_buffer = current_text[diff_index:]
                    if live_accumulation_buffer.strip():
                        transcript = merge_texts(transcript, live_accumulation_buffer.strip())
                        print(live_accumulation_buffer, end='', flush=True)
                    previous_text = current_text
                time.sleep(2)  # Adjust the sleep interval as necessary
        except KeyboardInterrupt:
            print("\nRecording stopped.")
            # Combine all text and split into sentences
            sentences = re.split(r'(?<=[.!?]) +', transcript)
            with open('transcript.txt', 'w', encoding='utf-8') as f:
                f.write('\n'.join(sentences))
