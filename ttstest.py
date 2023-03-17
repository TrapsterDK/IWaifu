from TTS.api import TTS
import time
import json

# print available models
models = TTS.list_models()


model_times = {}

test = "We have both free and paid subscriptions to our applications to meet different users' needs on different budgets. Our Plus subscription includes exclusive features and the use of Plus Voices, our newest and most advanced voices. Plus Voices enable fluid and natural-sounding text to speech that matches the patterns and intonation of human voices."

for model in models:
    model_name = model.replace('/', '-')
    path = "audio_tests/" + model_name + ".wav"
    tts = TTS(model_name=model, gpu=True)

    language = None 
    if tts.is_multi_lingual:
        if "en" not in tts.languages:
            break
        language = tts.languages[tts.languages.index("en")]

    s = time.time()
    tts.tts_to_file(text=test, 
                    file_path=path, 
                    speaker=None if not tts.is_multi_speaker else tts.speakers[0],
                    language=language)
    e = time.time()

    model_times[model_name] = e-s
    with open("audio_tests/times.json", "w") as f:
        json.dump(model_times, f)

# usefull models
# en-ek1-tacotron2
# en-ljspeech-* (all)
# en vctk-* (all)

# best sounding model tts_models-en-vctk-vits