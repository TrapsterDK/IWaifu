import dejavu
import pydub
import time

audio = pydub.AudioSegment.from_mp3(r"D:\iwaifudata\mono_mp3\a-certain-magical-index-episode-1-english-dubbed.mp3")


a = dejavu.fingerprint(audio.get_array_of_samples(), Fs=audio.frame_rate)

