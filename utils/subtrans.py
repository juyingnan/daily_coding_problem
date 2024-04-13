import os
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
import re
from tqdm import tqdm
import torch

def translate_srt(file_path, src_lang, tgt_lang, model, tokenizer):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer.src_lang = src_lang
    translated_lines = []
    buffer = []
    is_text = False

    for line in tqdm(lines):
        # Check if the line is a number (index of subtitle)
        if re.match(r'^\d+$', line.strip()):
            if buffer:
                # Join all buffered lines (subtitle text lines) and translate
                text_to_translate = ' '.join(buffer)
                encoded_text = tokenizer(text_to_translate, return_tensors="pt").to(device)
                generated_tokens = model.generate(**encoded_text, forced_bos_token_id=tokenizer.get_lang_id(tgt_lang))
                translated_text = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
                # Append the translated text
                translated_lines.append(translated_text + '\n')
                buffer = []
                is_text = False
            translated_lines.append(line)  # Append the index line unchanged
        elif re.match(r'^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$', line.strip()):
            translated_lines.append(line)  # Append the timestamp line unchanged
            is_text = True  # Next lines will be text until a new index or timestamp
        elif is_text:
            buffer.append(line.strip())  # Append subtitle text lines to buffer

    # Handle the last buffered text if any
    if buffer:
        text_to_translate = ' '.join(buffer)
        encoded_text = tokenizer(text_to_translate, return_tensors="pt").to(device)
        generated_tokens = model.generate(**encoded_text, forced_bos_token_id=tokenizer.get_lang_id(tgt_lang))
        translated_text = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
        translated_lines.append(translated_text + '\n')

    return translated_lines

def main():   

    if torch.cuda.is_available():
        print("CUDA is available. GPU device:", torch.cuda.get_device_name(0))
    else:
        print("CUDA is not available. Using CPU.")

    device = "cuda" if torch.cuda.is_available() else "cpu"

    src_lang = "ja"  
    tgt_lang = "zh"  
    model_name = r"C:\Users\yiju\Desktop\m2m100_1.2B"
    
    model = M2M100ForConditionalGeneration.from_pretrained(model_name).to(device)
    tokenizer = M2M100Tokenizer.from_pretrained(model_name)

    os.makedirs('result', exist_ok=True)

    root = r'C:\Users\yiju\Desktop\subs'

    for filename in os.listdir(root):
        if filename.endswith('.srt'):
            print(f"Translating {filename}...")
            file_path = os.path.join(root, filename)
            translated_lines = translate_srt(file_path, src_lang, tgt_lang, model, tokenizer)
            # Write translated lines to a new file in the result folder
            new_file_name = filename.replace('.srt', f'.{tgt_lang}.srt')
            with open(os.path.join(root, 'result', new_file_name), 'w', encoding='utf-8') as f:
                f.writelines(translated_lines)
            print(f"Saved translated {new_file_name} to result folder.")

if __name__ == "__main__":
    main()
