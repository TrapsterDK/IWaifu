from utils import (
    Log,
    ThreadPoolRunOnLog,
    FOLDER_DOWNLOAD_MP4,
    FOLDER_DOWNLOAD_MP3,
    FOLDER_LOGS,
    mp4_to_mp3,
    LOG_ANIMES,
    LOG_EPISODES,
    LOG_MP4,
    LOG_MP3,
    BASE_PATH,
    FOLDER_MONO_MP3,
    mp3_to_mp3_mono,
    LOG_MONO_MP3
)
from wcofun import download_episode, get_episodes_retry, get_all_dubbed_animes
from multiprocessing import Process, Value, Pool
from multiprocessing.managers import BaseManager
from functools import partial
import pathlib
import sys
import time


def mp4_to_mp3_and_delete(mp4_file: str, mp3_folder: pathlib.Path):
    mp4_file_path = BASE_PATH / mp4_file
    mp3_file_path = mp3_folder / mp4_file_path.relative_to(
        FOLDER_DOWNLOAD_MP4
    ).with_suffix(".mp3")
    mp4_to_mp3(mp4_file_path, mp3_file_path)

    mp4_file_path.unlink()

    return mp3_file_path

def mp3_to_mp3_mono_folder(mp3_file: str, mp3_folder: pathlib.Path):
    mp3_file_path = BASE_PATH / mp3_file
    mp3_file_mono_path = mp3_folder / mp3_file_path.relative_to(
        FOLDER_DOWNLOAD_MP3
    ).with_suffix(".mp3")

    mp3_to_mp3_mono(mp3_file_path, mp3_file_mono_path)

    return mp3_file_mono_path


if __name__ == "__main__":
    pathlib.Path(FOLDER_LOGS).mkdir(exist_ok=True)
    pathlib.Path(FOLDER_DOWNLOAD_MP4).mkdir(exist_ok=True)
    pathlib.Path(FOLDER_DOWNLOAD_MP3).mkdir(exist_ok=True)
    pathlib.Path(FOLDER_MONO_MP3).mkdir(exist_ok=True)

    BaseManager.register("Log", Log)

    with BaseManager() as manager:
        log_animes_exists = pathlib.Path(LOG_ANIMES).exists()

        log_animes: Log = manager.Log(LOG_ANIMES)
        log_episodes: Log = manager.Log(LOG_EPISODES)
        log_mp4: Log = manager.Log(LOG_MP4)
        log_mp3: Log = manager.Log(LOG_MP3)
        log_mono_mp3: Log = manager.Log(LOG_MONO_MP3)

        done = Value("b", False)

        if not log_animes_exists:
            print("Finding all dubbed animes...")
            log_animes.write_tasks(["dubbed_animes"])
            log_animes.write_task_done("dubbed_animes", get_all_dubbed_animes())
            # just to make sure it's saved
            log_animes.save()

        '''[
            Process(
                target=ThreadPoolRunOnLog,
                args=(log_animes, log_episodes, get_episodes_retry, done),
                name="EPS",
            ),
            Process(
                target=ThreadPoolRunOnLog,
                args=(
                    log_episodes,
                    log_mp4,
                    partial(download_episode, directory=FOLDER_DOWNLOAD_MP4),
                    done,
                ),
                name="MP4",
            ),
            Process(
                target=ThreadPoolRunOnLog,
                args=(
                    log_mp4,
                    log_mp3,
                    partial(mp4_to_mp3_and_delete, mp3_folder=FOLDER_DOWNLOAD_MP3),
                    done,
                ),
                name="MP3",
            ),
            '''

        processess = [
            Process(
                target=ThreadPoolRunOnLog,
                args=(
                    log_mp3,
                    log_mono_mp3,
                    partial(mp3_to_mp3_mono_folder, mp3_folder=FOLDER_MONO_MP3),
                    done,
                ),
                name="MONO",
            ),
        ]

        for process in processess:
            process.start()

        try:
            while True:
                time.sleep(0.5)
                sys.stdout.flush()

        except KeyboardInterrupt:
            print("KeyboardInterrupt, exiting...")

        done.value = True

        # wait for all processes to return
        for process in processess:
            process.join()

        print("Exited successfully")
