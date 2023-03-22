from bs4 import BeautifulSoup
import cloudscraper
import base64
import js2py
import re
from urllib.parse import urlsplit
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep
from threading import Lock
from clint.textui import progress
from utils import mp4_to_mp3, Log
from os import remove
import ffmpeg
import pathlib

js2py_lock = Lock()

URL = "https://www.wcofun.com/"
ANIME_URL = URL + "anime/"

def get_episodes(anime, scraper):
    r = scraper.get(ANIME_URL + anime)
    
    if r.status_code != 200:
        raise Exception("Could not get anime url")

    soup = BeautifulSoup(r.text, "html.parser")

    episodes: list[(str, str)] = []
    for episode in soup.select("div.cat-eps > a"):
        episodes.append((episode.text, episode["href"]))

    return episodes


def atob(s):
    return base64.b64decode('{}'.format(s)).decode('utf-8')

REGEX_VIDEO_GET_LINK = re.compile(r'(?<=\$\.getJSON\(")(.*)(?=")')

def get_video_url(episode_url, scraper):
    r = scraper.get(episode_url)
    
    if r.status_code != 200:
        raise Exception("Could not get episode url")

    website_soup = BeautifulSoup(r.text, "html.parser")

    # Get the obfuscated script that contains the iframe url
    iframe_script = website_soup.select_one("div[id*=hide-] + script")

    if iframe_script is None:
        raise Exception("Could not find iframe script")

    script = iframe_script.text.replace("document.write", "")

    ctx = js2py.EvalJs({'atob': atob})
    sleep(1)

    with js2py_lock:
        iframe_soup = BeautifulSoup(ctx.eval(script), "html.parser")

    iframe = iframe_soup.select_one("iframe")
    if iframe is None:
        raise Exception("Could not find iframe")
    
    iframe_url = iframe["src"]

    scraper.headers.update({"Referer": episode_url})

    r = scraper.get(iframe_url)

    if r.status_code != 200:
        raise Exception("Could not get iframe url")

    video_get_url = re.search(REGEX_VIDEO_GET_LINK, r.text)

    if video_get_url is None:
        raise Exception("Could not find video get url")
    
    video_get_url = video_get_url.group()
    
    scraper.headers.update({"x-requested-with": "XMLHttpRequest"})
    scraper.headers.update({"Referer": iframe_url})

    url = urlsplit(iframe_url)
    video_get_url = url.scheme + "://" + url.netloc + video_get_url

    r = scraper.get(video_get_url)

    if r.status_code != 200:
        raise Exception("Could not get video url")
    
    video_json = r.json()
    if not ("server" in video_json and "enc" in video_json): 
        raise Exception("Could not find video url in json")
    
    scraper.headers.pop("x-requested-with")
    scraper.headers.pop("Referer")
    
    return video_json["server"] + "/getvid?evid=" + video_json["enc"]


def download_video(video_url, filename, scraper, chunk_size=4096 * 4096):
    r = scraper.get(video_url, stream=True)

    total_length = int(r.headers.get('content-length'))
    with open(filename, "wb") as f:
        for chunk in progress.bar(r.iter_content(chunk_size=chunk_size), expected_size=(total_length/(chunk_size)) + 1): 
            if chunk:
                f.write(chunk)
                f.flush()


def download_episode(episode_url, directory):
    scraper = cloudscraper.create_scraper()
    while True:
        try:
            video_url = get_video_url(episode_url, scraper)
            break
        except cloudscraper.exceptions.CloudflareChallengeError:
            scraper = cloudscraper.create_scraper()

    filename = directory.joinpath(pathlib.Path(episode_url.split("/")[-1] + ".mp4"))

    try:
        download_video(video_url, filename, scraper)
    except cloudscraper.exceptions.CloudflareChallengeError:
        return download_episode(episode_url, directory)
    
    return filename


def get_episodes_retry(anime):
    scraper = cloudscraper.create_scraper()
    while True:
        try:
            return get_episodes(anime, scraper)
            
        except cloudscraper.exceptions.CloudflareChallengeError:
            scraper = cloudscraper.create_scraper()

def download_episodes_multiple_animes(animes, log: Log):
    for anime in animes:
        log.write_entry(anime)

    with ThreadPoolExecutor(max_workers=5) as executor:
        downloaded = 0
        print("Getting episodes for animes")

        futures = {executor.submit(get_episodes_retry, anime): anime for anime in animes}

        for future in as_completed(futures):
            anime = futures[future]

            downloaded += 1
            
            print(f"Found anime episodes {downloaded}/{len(futures)}")

            if future.exception() is not None:
                log.write_error(anime, future.exception())
                continue

            log.move_to_processed(anime, future.result())




def download_episodes(animes, directory):
    with ThreadPoolExecutor(max_workers=5) as executor: 
        downloaded = 0
        print("Downloading episodes")

        futures = []
        for episode in episodes:
            futures.append(executor.submit(download_episode, episode[1], directory))

        for future in as_completed(futures):
            downloaded += 1
            print(f"Downloaded episode {downloaded}/{len(episodes)}")

            if future.exception() is not None and function_on_error is not None:
                function_on_error(future.exception())

            elif function_on_complete is not None:
                function_on_complete(future.result())




def complete_handler(path, new_directory, log_file):
    print("Converting to mp3")
    new_filename = str(new_directory) + pathlib.Path(path).stem + ".mp3"

    try:
        mp4_to_mp3(path, new_filename)
    except ffmpeg.Error as e:
        file_log_write(log_file, str(path), e)
        return

    file_log_write(log_file, str(path))
    remove(path)


if __name__ == "__main__":
    video_directory = pathlib.Path("anime_videos/")
    audio_directory = pathlib.Path("anime_audios/")
    log = pathlib.Path("download_log.txt")
    
    if not video_directory.exists():
        video_directory.mkdir()
    
    if not audio_directory.exists():
        audio_directory.mkdir()

    with open(log, "w") as download_log:
        download_animes(["sword-art-online"], video_directory, lambda filename: complete_handler(filename, audio_directory, download_log))