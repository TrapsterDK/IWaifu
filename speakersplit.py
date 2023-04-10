from time import sleep
import pydub
import constants
from multiprocessing import Queue, Process
from pathlib import Path
import signal
from databases import VoiceAudioDatabase, SpeakerDatabase
from pyannote.audio import Pipeline

MILISECONDS_TO_SECONDS = 1000


def process_audio_files(
    audio_path: Path,
    audio_filetype: str,
    audio_queue: "Queue[str]",
):
    try:
        print("Audio process started")

        with VoiceAudioDatabase() as voice_db, SpeakerDatabase() as speaker_db:
            audios = voice_db.get_audios()
            audios_len = len(audios)

            count = 0
            for audio in audios:
                # max 5 audio files in queue
                while audio_queue.qsize() > 5:
                    sleep(1)

                # check if file is already processeds
                audio_id = speaker_db.get_audio_id(audio["audio_name"])
                if audio_id and speaker_db.audio_is_diarized(audio_id):
                    audios_len -= 1
                    continue

                count += 1

                print(f"Processing audio {count}/{audios_len}")

                # load audio file
                audio_segment = pydub.AudioSegment.from_file(
                    audio_path / f"{audio['audio_name']}.{audio_filetype}",
                    audio_filetype,
                )

                # convert to mono
                audio_segment = audio_segment.set_channels(1)

                # get voice activity
                voice_activity = voice_db.get_voice_activity_processed(
                    audio["audio_id"]
                )

                # create new audio segment
                new_audio = pydub.AudioSegment.empty()

                # add voice activity to new audio segment
                for activity in voice_activity:
                    new_audio += audio_segment[
                        activity["start_time"]
                        * MILISECONDS_TO_SECONDS : activity["end_time"]
                        * MILISECONDS_TO_SECONDS
                    ]

                # save new audio segment
                new_audio.export(
                    constants.FOLDER_TEMP / f"{audio['audio_name']}.wav", format="wav"
                )

                # add new audio segment to queue
                audio_queue.put(audio["audio_name"])

        audio_queue.put(None)
        print("Audio process finished")

    except KeyboardInterrupt:
        print("Keyboard interrupt, terminating audio process")


def process_speaker_diarization(
    audio_queue: "Queue[tuple[str, pydub.AudioSegment]]",
    speaker_queue: "Queue[tuple[str, list[tuple[int, float, float]]]]",
):
    try:
        print("Diarization process started")

        speaker_diarization = Pipeline.from_pretrained(
            "pyannote/speaker-diarization",
            use_auth_token="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",
        )

        count = 0
        while True:
            count += 1
            file_name = audio_queue.get()

            if file_name is None:
                break

            print(f"Diarization of audio {count}")

            # diarize audio
            diarization = speaker_diarization(
                str(constants.FOLDER_TEMP / f"{file_name}.wav")
            )

            # convert to list of tuples with speaker id, start and end time
            data = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                data.append((int(speaker[8:]), turn.start, turn.end))

            # add audio diarization to queue
            speaker_queue.put((file_name, data))

        speaker_queue.put(None)
        print("Diarization process finished")

    except KeyboardInterrupt:
        print("Keyboard interrupt, terminating diarization process")


def process_database(
    speaker_queue: "Queue[tuple[Path, list[tuple[int, float, float]]]]",
):
    try:
        print("Starting database")

        with SpeakerDatabase() as database:
            count = 0
            while True:
                count += 1
                data = speaker_queue.get()

                if data is None:
                    break

                file_name, diarization_data = data

                print(f"Database insert of audio {count}")

                # delete file
                (constants.FOLDER_TEMP / f"{file_name}.wav").unlink()

                audio_id = database.get_audio_id(file_name)
                if not audio_id:
                    audio_id = database.insert_audio(file_name)

                database.delete_diarization(audio_id)

                database.insert_speaker_diarization(audio_id, diarization_data)

                database.audio_set_dialized(audio_id)

        print("Finished database")

    except KeyboardInterrupt:
        print("Keyboard interrupt, terminating database process")


if __name__ == "__main__":
    print("Starting")

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    audio_queue, speaker_queue = (
        Queue(),
        Queue(),
    )

    processes = [
        Process(
            target=process_audio_files,
            args=(constants.FOLDER_MP3, "mp3", audio_queue),
        ),
        Process(target=process_speaker_diarization, args=(audio_queue, speaker_queue)),
        Process(target=process_database, args=(speaker_queue,)),
    ]

    for process in processes:
        process.start()

    try:
        for process in processes:
            process.join()

    except KeyboardInterrupt:
        print("Keyboard interrupt, terminating processes")

        for process in processes:
            process.terminate()

    print("Finished")
