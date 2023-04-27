# https://github.com/worldveil/dejavu

from time import sleep
import dejavu
import pydub
import constants
from multiprocessing import Queue, Process
from pathlib import Path
import signal
from databases import VoiceAudioDatabase, FingerPrintDatabase
from concurrent.futures import ThreadPoolExecutor


MINUTES_TO_SECONDS = 60
MILISECONDS_TO_SECONDS = 1000
MAX_FINGERPRINT_MINUTE_SIZE = 10


def process_audio_files(
    audio_path: Path,
    audio_filetype: str,
    audio_queue: "Queue[tuple[str, pydub.AudioSegment]]",
):
    try:
        print("Audio process started")

        with VoiceAudioDatabase() as voice_db, FingerPrintDatabase() as fingerprint_db:
            audios = voice_db.get_audios()
            audios_len = len(audios)

            count = 0
            for audio in audios:
                # max 100 minutes in queue
                while audio_queue.qsize() > 10:
                    sleep(1)

                # check if file is already processeds
                audio_id = fingerprint_db.get_audio_id(audio["audio_name"])
                if audio_id and fingerprint_db.audio_is_fingerprinted(audio_id):
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

                # add to queue in chunks
                for i in range(
                    0,
                    len(new_audio),
                    MAX_FINGERPRINT_MINUTE_SIZE
                    * MINUTES_TO_SECONDS
                    * MILISECONDS_TO_SECONDS,
                ):
                    audio_queue.put(
                        (
                            audio["audio_name"],
                            new_audio[
                                i : i
                                + MAX_FINGERPRINT_MINUTE_SIZE
                                * MINUTES_TO_SECONDS
                                * MILISECONDS_TO_SECONDS
                            ].get_array_of_samples(),
                        )
                    )

        audio_queue.put(None)
        print("Audio process finished")

    except KeyboardInterrupt:
        print("Keyboard interrupt, terminating audio process")


def process_fingerprint(
    audio_queue: "Queue[tuple[str, pydub.AudioSegment]]",
    fingerprint_queue: "Queue[tuple[str, list[tuple[bytes, int]]]]",
):
    try:
        print("Fingerprint process started")

        count = 0
        while True:
            count += 1
            data = audio_queue.get()

            if data is None:
                break

            file_name, audio = data

            print(f"Fingerprinting audio {count}")

            # get audio fingerprint
            audio_fingerprint = dejavu.fingerprint(audio)

            # add audio fingerprint to queue
            fingerprint_queue.put((file_name, audio_fingerprint))

        fingerprint_queue.put(None)
        print("Fingerprint process finished")

    except KeyboardInterrupt:
        print("Keyboard interrupt, terminating fingerprint process")


def database_thread(data: tuple[str, list[tuple[bytes, int]]]) -> None:
    file_name, audio_fingerprint = data

    with FingerPrintDatabase() as fingerprint_db:
        # get audio id
        audio_id = fingerprint_db.get_audio_id(file_name)
        if audio_id is None:
            audio_id = fingerprint_db.insert_audio(file_name)

        # insert audio fingerprint into database
        fingerprint_db.insert_fingerprints(audio_id, audio_fingerprint)

        # set audio fingerprinted
        fingerprint_db.audio_set_fingerprinted(audio_id)


def process_database(fingerprint_queue: "Queue[tuple[str, list[tuple[bytes, int]]]]"):
    try:
        print("Database process started")

        with ThreadPoolExecutor(max_workers=5) as executor:
            count = 0
            while True:
                count += 1
                data = fingerprint_queue.get()

                if data is None:
                    break

                print(f"Inserting fingerprint {count}")

                # add to thread pool to insert into database
                executor.submit(database_thread, data)

            print("Database process finished")

    except KeyboardInterrupt:
        print("Keyboard interrupt, terminating database process")


def run(i):
    with FingerPrintDatabase() as fingerprint_db:
        fingerprint_db.find_matches(i)


from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# print("Starting")
# s = time.perf_counter()
#
# try:
#     with ThreadPoolExecutor(max_workers=15) as executor:
#         futures = []
#         for i in range(1, 60):
#             futures.append(executor.submit(run, i))
#
#         for future in as_completed(futures):
#             elapsed = time.perf_counter() - s
#             print(f"Finished in {elapsed:0.2f} seconds")
#
# except KeyboardInterrupt:
#     print("Keyboard interrupt, terminating processes")
#
# print("Finished, in", time.perf_counter() - s, "seconds")

s = time.perf_counter()

with FingerPrintDatabase() as fingerprint_db:
    matches = fingerprint_db.find_matches(1)

    elapsed = time.perf_counter() - s
    print(f"Finished in {elapsed:0.2f} seconds")

    # find streaks where offset is countinuous and the id is the same
    streaks = []
    for i in range(len(matches) - 1):
        if (
            matches[i]["id"] == matches[i + 1]["id"]
            and matches[i]["offset"] + 1 == matches[i + 1]["offset"]
        ):
            streaks.append(matches[i])

    print(streaks)


exit()

if __name__ == "__main__":
    print("Starting")

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    audio_queue, fingerprint_queue = (
        Queue(),
        Queue(),
    )

    processes = [
        Process(
            target=process_audio_files,
            args=(constants.FOLDER_MP3, "mp3", audio_queue),
        ),
        Process(target=process_fingerprint, args=(audio_queue, fingerprint_queue)),
        Process(target=process_database, args=(fingerprint_queue,)),
    ]

    for process in processes:
        process.start()

    try:
        for process in processes:
            process.join()

        with FingerPrintDatabase() as fingerprint_db:
            fingerprint_db.create_indexes()
            fingerprint_db.alter_forgien_key()
            fingerprint_db.alter_unique()

    except KeyboardInterrupt:
        print("Keyboard interrupt, terminating processes")

        for process in processes:
            process.terminate()

    print("Finished")