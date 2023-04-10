import whisper
import time
import json


# filename = "D:/iwaifudata/mp3/a-certain-magical-index-episode-1-english-dubbed.mp3"
# models = ["tiny.en", "base.en", "small.en", "medium.en"]
models = ["small.en"]
# use small model because of speed to result

for model in models:
    print(f"Loading {model}...")
    m = whisper.load_model(model, device="cuda")

    print("Transcribing...")
    for file in [
        # "a-certain-magical-index-episode-1-english-dubbed-0.wav",
        "D:/iwaifudata/mp3/violet-evergarden-movie-english-dubbed.mp3",
    ]:
        audio = whisper.load_audio(file)
        s = time.time()
        result = m.transcribe(audio)
        print(len(result["text"]))
