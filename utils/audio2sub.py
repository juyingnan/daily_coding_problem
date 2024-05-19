import os
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
from datetime import timedelta

def format_time(seconds):
    """ Convert time in seconds to the SRT time format HH:MM:SS,MS """
    if seconds is None:
        return f"{0:02}:{0:02}:{0:02},{0:03}"
    millisec = int((seconds % 1) * 1000)
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02},{millisec:03}"

def convert_to_srt(transcriptions, file_path):
    """
    Create an SRT file from the transcriptions with timestamps.
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        for i, chunk in enumerate(transcriptions['chunks'], start=1):
            start_time = format_time(chunk['timestamp'][0])
            end_time = format_time(chunk['timestamp'][1])
            f.write(f"{i}\n{start_time} --> {end_time}\n{chunk['text'].strip()}\n\n")    
    f.close()            

def main():
    root = r'C:\Users\yiju\Desktop\subs'  # Directory containing audio files
    device = "cuda:0" if torch.cuda.is_available() else "cpu"  # Use GPU if available
    print(f"Using {device} device")
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    # Initialize the Whisper model and processor
    model_id = r"C:\Users\yiju\Desktop\openai_whisper_large_v2"
    model = AutoModelForSpeechSeq2Seq.from_pretrained(model_id, torch_dtype=torch_dtype)
    processor = AutoProcessor.from_pretrained(model_id)

    pipe = pipeline(
    "automatic-speech-recognition",
    model=model,
    tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    max_new_tokens=128,
    chunk_length_s=30,
    batch_size=16,
    return_timestamps=True,
    torch_dtype=torch_dtype,
    device=device,)

    supported_formats = ('.wav', '.mp3', '.mp4', '.m4a')  # Extendable list of supported audio formats
    target_lang = 'zh'

    for filename in os.listdir(root):
        if filename.endswith(supported_formats):
            file_path = os.path.join(root, filename)
            print(f"Transcribing {filename}...")
            transcriptions = pipe(file_path, generate_kwargs={"language":f"<|{target_lang}|>","task": "transcribe"},)
            # print(transcriptions)
            result_path = os.path.join(root, 'result', filename.replace(filename.split('.')[-1], f'{target_lang}.srt'))
            convert_to_srt(transcriptions, result_path)
            print(f"Saved {result_path} to {root}")

if __name__ == "__main__":
    main()

