from bs4 import BeautifulSoup
import cloudscraper
import base64
import js2py
import re
from urllib.parse import urlsplit
from tqdm import tqdm

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

    iframe_soup = BeautifulSoup(ctx.eval(script), "html.parser")

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
    scraper.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"})

    url = urlsplit(iframe_url)
    video_get_url = url.scheme + "://" + url.netloc + video_get_url

    r = scraper.get(video_get_url)

    if r.status_code != 200:
        return None
    
    video_json = r.json()
    if not ("server" in video_json and "enc" in video_json): 
        raise Exception("Could not find video url in json")
    
    scraper.headers.pop("x-requested-with")

    return video_json["server"] + "/getvid?evid=" + video_json["enc"]

episodes = None

scraper = cloudscraper.create_scraper()

"""
while True:
    try:
        episodes = get_episodes("sword-art-online", cloudscraper.create_scraper())
        break
    except Exception as e:
        scraper = cloudscraper.create_scraper()
        print("except")

print(episodes)

for episode in episodes:
    try:
        print(get_video_url(episode[1], cloudscraper.create_scraper()))
    except Exception as e:        
        scraper = cloudscraper.create_scraper()
        print("except")
"""

while True:
    try:
        link = get_video_url("https://www.wcofun.com/sword-art-online-episode-12-english-dubbed-2", scraper) 
        print(link)

        r = scraper.get(link, stream=True)
        with open("test.mp4", "wb") as handle:
            for data in tqdm(r.iter_content()):
                handle.write(data)

        break

    except Exception as e:
        scraper = cloudscraper.create_scraper()
        print(e)
