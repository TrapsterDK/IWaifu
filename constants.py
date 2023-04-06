from pathlib import Path
import platform

if platform.system() == "Windows":
    FOLDER_BASE = Path("D:/iwaifudata")
else:
    FOLDER_BASE = Path("/mnt/d/iwaifudata")

FOLDER_TEMP = FOLDER_BASE / "temp"
FOLDER_BACKUP = FOLDER_BASE / "backup"
FOLDER_MP3 = FOLDER_BASE / "mp3"
FOLDER_MONO_MP3 = FOLDER_BASE / "mono_mp3"

FOLDERS = [FOLDER_TEMP, FOLDER_BACKUP, FOLDER_MP3, FOLDER_MONO_MP3]

for folder in FOLDERS:
    folder.mkdir(parents=True, exist_ok=True)
