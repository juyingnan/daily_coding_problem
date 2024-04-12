import os
import torch
import torchaudio
from transformers import WhisperForConditionalGeneration, WhisperProcessor

def transcribe_audio(audio_file, model, processor, device):
    """Transcribe an audio file using the Whisper model."""
    audio, sample_rate = torchaudio.load(audio_file)

    # Convert to mono if stereo
    if audio.shape[0] > 1:
        audio = audio.mean(dim=0, keepdim=True)

    # Resample to 16 kHz if necessary
    if sample_rate != 16000:
        resampler = torchaudio.transforms.Resample(sample_rate, 16000)
        audio = resampler(audio)

    # Add batch dimension
    audio = audio.unsqueeze(0)

    # Move audio to the appropriate device
    audio = audio.to(device)

    # Transcribe audio
    input_features = processor(audio.cpu(), return_tensors="pt", sampling_rate=16000).input_features.to(device)
    transcription = model.generate_transcriptions(input_features, max_length=512)

    return transcription

def create_srt(transcription, chunk_length_sec=30, output_file=None):
    """Convert transcription to SRT format."""
    srt_lines = []
    start_time = 0
    index = 1

    for segment in transcription:
        text = segment['text'].strip()
        if not text:
            continue

        end_time = start_time + chunk_length_sec
        start_timecode = f"{int(start_time // 3600):02}:{int((start_time % 3600) // 60):02}:{int(start_time % 60):02},000"
        end_timecode = f"{int(end_time // 3600):02}:{int((end_time % 3600) // 60):02}:{int(end_time % 60):02},000"

        srt_lines.append(f"{index}")
        srt_lines.append(f"{start_timecode} --> {end_timecode}")
        srt_lines.append(f"{text}")
        srt_lines.append("")

        start_time = end_time
        index += 1

    srt_content = "\n".join(srt_lines)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(srt_content)
    else:
        return srt_content
    
def main():
    root = r'C:\Users\yiju\Desktop\subs'  # Directory containing .wav files
    device = "cuda" if torch.cuda.is_available() else "cpu"  # Use GPU if available
    print(f"Using {device} device")

    # Initialize the Whisper model and processor
    model = WhisperForConditionalGeneration.from_pretrained(r"C:\Users\yiju\Desktop\openai_whisper_large_v2").to(device)
    processor = WhisperProcessor.from_pretrained(r"C:\Users\yiju\Desktop\openai_whisper_large_v2")

    for filename in os.listdir(root):
        if filename.endswith('.wav'):
            file_path = os.path.join(root, filename)
            print(f"Transcribing {filename}...")
            transcriptions = transcribe_audio(file_path, model, processor, device)
            create_srt(transcriptions, file_path, chunk_length_sec=30)
            print(f"Saved {filename.replace('.wav', '.srt')} to {root}")

if __name__ == "__main__":
    main()
