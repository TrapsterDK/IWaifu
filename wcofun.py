from bs4 import BeautifulSoup
import cloudscraper
import base64
import js2py
import re
from urllib.parse import urlsplit
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_pcomleted
from time import sleep
from copy import copy
from threading import Lock
from clint.textui import progress

js2py_lock = Lock()

URL = "https://www.wcofun.com/"
ANIME_URL = URL + "anime/"

def get_episodes(anime, scraper):
    r = scraper.get(ANIME_URL + anime)
    
    if r.status_code != 200:
        return None

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
        return None

    website_soup = BeautifulSoup(r.text, "html.parser")

    # Get the obfuscated script that contains the iframe url
    iframe_script = website_soup.select_one("div[id*=hide-] + script")

    if iframe_script is None:
        raise Exception("Could not find iframe script")

    script = iframe_script.text.replace("document.write", "")

    ctx = js2py.EvalJs({'atob': atob})
    sleep(1)

    with js2py_lock:
        iframe_soup = BeautifulSoup(ctx.eval(copy(str(script))), "html.parser")

    iframe = iframe_soup.select_one("iframe")
    if iframe is None:
        raise Exception("Could not find iframe")
    
    iframe_url = iframe["src"]

    scraper.headers.update({"Referer": episode_url})

    r = scraper.get(iframe_url)

    if r.status_code != 200:
        return None

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
        return None
    
    video_json = r.json()
    if not ("server" in video_json and "enc" in video_json): 
        raise Exception("Could not find video url in json")
    
    return video_json["server"] + "/getvid?evid=" + video_json["enc"]


def scraper_retry(function, *args, max_retries=15, **kwargs):
    scraper = cloudscraper.create_scraper()
    tries = 0
    while True:
        try:
            tries += 1
            if tries > max_retries:
                return None

            return function(*args, **kwargs, scraper=scraper)
        except cloudscraper.exceptions.CloudflareChallengeError:
            scraper = cloudscraper.create_scraper()


def get_all_videos(anime):
    with ThreadPoolExecutor() as executor:
        episodes = scraper_retry(get_episodes, anime)
        print(f"Found {len(episodes)} episodes, getting video urls")
        results = list(tqdm(executor.map(scraper_retry, [get_video_url] * len(episodes), [episode[1] for episode in episodes]), total=len(episodes)))
 
        return results


def download_video(video_url, filename, scraper):
    r = scraper.get(video_url, stream=True)

    total_length = int(r.headers.get('content-length'))
    with open(filename, "wb") as handle:
        for data in r.iter_content(chunk_size=4096):


video = None
while True:
    scraper = cloudscraper.create_scraper()
    try:
        video = get_video_url("https://www.wcofun.com/beyblade-burst-season-2-episode-27-english-subbed", scraper)
        break
    except Exception as e:
        scraper = cloudscraper.create_scraper()
    
while True:
    try:
        download_video(video, "test.mp4", scraper)
        break
    except Exception as e:
        break


'''
scraper = cloudscraper.create_scraper() 
while True:
    try:
        #link = get_video_url("https://www.wcofun.com/sword-art-online-episode-12-english-dubbed-2", scraper) 
        #link2 = get_video_url("https://www.wcofun.com/sword-art-online-episode-13-english-dubbed-2", scraper) 
        #print(link)
        #print(link2)

        """r = scraper.get(link, stream=True)
        with open("test.mp4", "wb") as handle:
            for data in tqdm(r.iter_content()):
                handle.write(data)
        """

        break

    except Exception as e:
        scraper = cloudscraper.create_scraper()
        print(e)
'''