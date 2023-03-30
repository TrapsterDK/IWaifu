import whisper
import time
import json



filename = "D:/iwaifudata/mp3/a-certain-magical-index-episode-1-english-dubbed.mp3"
#models = ["tiny.en", "base.en", "small.en", "medium.en"]
models = ["small.en"]
# use small model because of speed to result

print("Loading audio...")
audio = whisper.load_audio(filename)

for model in models:
    print(f"Loading {model}...")
    m = whisper.load_model(model, device="cuda")

    print("Transcribing...")
    s = time.time()
    result = m.transcribe(audio)
    print(f"Done {model}")
    print(f"Time: {time.time() - s}")

    with open(f"{model}.json", "w") as f:
        json.dump(result, f)

    del m