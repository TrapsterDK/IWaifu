from utils import Log, ThreadPoolWithLog, FOLDER_DOWNLOAD_MP4, FOLDER_DOWNLOAD_MP3, FOLDER_LOGS, mp4_to_mp3, LOG_ANIMES, LOG_EPISODES, LOG_MP4, LOG_MP3
from wcofun import download_episode, get_episodes_retry, get_all_dubbed_animes
from multiprocessing import Process
from multiprocessing.managers import BaseManager
from functools import partial
import pathlib
import msvcrt

def mp4_to_mp3_and_delete(mp4_file: str, mp3_folder: pathlib.Path):
    mp4_file_path = pathlib.Path(mp4_file)
    mp3_file = mp3_folder / mp4_file_path.with_suffix(".mp3").name
    mp4_to_mp3(mp4_file, mp3_file)
    mp4_file_path.unlink()

    return str(mp3_file)


if __name__ == "__main__":
    pathlib.Path(FOLDER_LOGS).mkdir(exist_ok=True)
    pathlib.Path(FOLDER_DOWNLOAD_MP4).mkdir(exist_ok=True)
    pathlib.Path(FOLDER_DOWNLOAD_MP3).mkdir(exist_ok=True)

    BaseManager.register("Log", Log)

    with BaseManager() as manager:
        log_animes_exists = pathlib.Path(LOG_ANIMES).exists()

        log_animes: Log = manager.Log(LOG_ANIMES)
        log_episodes: Log = manager.Log(LOG_EPISODES)
        log_mp4: Log = manager.Log(LOG_MP4)
        log_mp3: Log = manager.Log(LOG_MP3)

        if not log_animes_exists:
            print("Finding all dubbed animes...")
            log_animes.write_entry("dubbed_animes")
            log_animes.write_processed("dubbed_animes", get_all_dubbed_animes())
            # just to make sure it's saved
            log_animes.save()


        episode_finder = Process(target=ThreadPoolWithLog, args=("EPFINDER", log_episodes, log_animes, get_episodes_retry))            

        episode_downloader = Process(target=ThreadPoolWithLog, args=("EPDOWNLD", log_mp4, log_episodes, partial(download_episode, directory=FOLDER_DOWNLOAD_MP4)))

        mp4_to_mp3_converter = Process(target=ThreadPoolWithLog, args=("MP4TOMP3", log_mp3, log_mp4, partial(mp4_to_mp3_and_delete, mp3_folder=FOLDER_DOWNLOAD_MP3), 20))

        episode_finder.start()
        episode_downloader.start()
        mp4_to_mp3_converter.start()

        while True:
            try:
                if msvcrt.kbhit():
                    if msvcrt.getch() == b'q':
                        break

            except KeyboardInterrupt:
                break

        print("Exiting...")
        log_animes.save()
        log_episodes.save()
        log_mp4.save()
        log_mp3.save()

        episode_finder.terminate()
        episode_downloader.terminate()
        mp4_to_mp3_converter.terminate()
