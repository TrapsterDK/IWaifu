from pyannote.audio import Pipeline
import ffmpeg
from pathlib import Path
from multiprocessing import Queue, Process
from time import sleep
import constants
import signal
from databases import VoiceAudioDatabase


def convert_to_wav(file: Path, folder: Path) -> Path:
    if not file.is_file():
        return

    if file.suffix == ".wav":
        return

    new_file = folder / f"{file.stem}.wav"

    stream = ffmpeg.input(str(file))
    stream = ffmpeg.output(stream, str(new_file), ac=1)
    ffmpeg.run(stream, quiet=True, overwrite_output=True)

    return new_file


def process_mp3_folder(folder: Path, queue: "Queue[Path]"):
    try:
        files_len = len(list(folder.iterdir()))
        print(f"Starting mp3 to wav conversion of {folder.name}, {files_len} files")

        with VoiceAudioDatabase() as database:
            for index, file in enumerate(folder.iterdir()):
                # max 10 files in queue
                while queue.qsize() > 10:
                    sleep(5)

                if file.is_dir():
                    process_mp3_folder(file, queue)
                    continue

                # check if file is already processeds
                audio_id = database.get_audio_id(file.stem)
                if audio_id and database.audio_is_processed(audio_id):
                    continue

                print(f"Converting file {files_len - index}/{files_len}")

                queue.put(convert_to_wav(file, constants.FOLDER_TEMP))

        queue.put(None)
        print(f"Finished mp3 to wav conversion of {folder.name}")

    except KeyboardInterrupt:
        print("Keyboard interrupt, mp3 to wav conversion stopped")


def process_voice_detection(
    queue: "Queue[Path]", database_queue: "Queue[tuple[Path, list[tuple[int, int]]]]"
):
    try:
        print("Starting voice detection")

        voice_activity_detection = Pipeline.from_pretrained(
            "pyannote/voice-activity-detection",
            use_auth_token="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",
        )

        while True:
            file = queue.get()

            if file is None:
                break

            print(f"Detecting voice in {file.stem}")

            voice_activity = voice_activity_detection(file)

            database_queue.put((file, voice_activity))

        database_queue.put(None)
        print("Finished voice detection")

    except KeyboardInterrupt:
        print("Keyboard interrupt, voice detection stopped")


def process_database(database_queue: "Queue[tuple[Path, list[tuple[int, int]]]]"):
    try:
        print("Starting database")

        with VoiceAudioDatabase() as database:
            while True:
                data = database_queue.get()

                if data is None:
                    break

                audio_name, voice_activity = data

                print(f"Inserting voice activity of {audio_name.name}")

                # convert to list of tuples with start and end time
                voice_activity = [
                    (round(speech.start), round(speech.end))
                    for speech in voice_activity.get_timeline().support()
                ]

                # delete file
                audio_name.unlink()

                audio_id = database.get_audio_id(audio_name.stem)
                if not audio_id:
                    audio_id = database.insert_audio(audio_name.stem)

                database.delete_voice_activity(audio_id)

                database.insert_voice_activity(audio_id, voice_activity)

                database.set_processed(audio_id)

        print("Finished database")

    except KeyboardInterrupt:
        print("Keyboard interrupt, database stopped")


if __name__ == "__main__":
    # create database
    print("Starting")

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    wav_queue, voice_queue = (
        Queue(),
        Queue(),
    )

    processes = [
        Process(target=process_mp3_folder, args=(constants.FOLDER_MP3, wav_queue)),
        Process(target=process_voice_detection, args=(wav_queue, voice_queue)),
        Process(target=process_database, args=(voice_queue,)),
    ]

    for process in processes:
        process.start()

    try:
        for process in processes:
            process.join()
        db = VoiceAudioDatabase()
        db.process_voice_activity()

    except KeyboardInterrupt:
        print("Keyboard interrupt, terminating processes")
        for process in processes:
            process.terminate()

    print("Finished")
