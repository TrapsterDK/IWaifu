from bs4 import BeautifulSoup
import cloudscraper
import base64
import js2py
import re
from urllib.parse import urlsplit
from time import sleep
from threading import Lock
from clint.textui import progress
import pathlib


js2py_lock = Lock()

URL = "https://www.wcofun.com/"
DUBBED_URL = URL + "dubbed-anime-list/"
ANIME_URL = URL + "anime/"

def get_episodes(anime, scraper):
    r = scraper.get(ANIME_URL + anime)
    
    if r.status_code != 200:
        raise Exception("Could not get anime url")

    soup = BeautifulSoup(r.text, "html.parser")

    #episodes: list[(str, str)] = []
    episodes: list[str] = []
    for episode in soup.select("div.cat-eps > a"):
        #episodes.append((episode.text, episode["href"]))
        episodes.append(episode["href"])

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
        #for chunk in progress.bar(r.iter_content(chunk_size=chunk_size), expected_size=(total_length/(chunk_size)) + 1): 
        for chunk in r.iter_content(chunk_size=chunk_size):
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
    
    return str(filename)


def get_episodes_retry(anime):
    scraper = cloudscraper.create_scraper()
    while True:
        try:
            return get_episodes(anime, scraper)
            
        except cloudscraper.exceptions.CloudflareChallengeError:
            scraper = cloudscraper.create_scraper()

def get_all_dubbed_animes():
    try:
        scraper = cloudscraper.create_scraper()
        r = scraper.get(DUBBED_URL)

        if r.status_code != 200:
            raise Exception("Could not get anime url")

        soup = BeautifulSoup(r.text, "html.parser")

        animes: list[str] = []
        for anime in soup.select("div.ddmcc > ul > li > a"):
            animes.append(anime["href"].split("/")[-1])

        return animes
    except cloudscraper.exceptions.CloudflareChallengeError:
        return get_all_dubbed_animes()
    
if __name__ == "__main__":
    print(get_all_dubbed_animes())