import re
import subprocess
from pathlib import Path
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import ID3NoHeaderError


def is_mp3(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() == ".mp3"


def clean_title_name(raw_title: str, band_name: str) -> str:
    title = raw_title.strip()

    # remove "Band - " prefix (case-insensitive)
    prefix_pattern = re.compile(rf"^{re.escape(band_name)}\s*-\s*", re.IGNORECASE)
    title = prefix_pattern.sub("", title)

    # remove anything inside parentheses ()
    title = re.sub(r"\(.*?\)", "", title)

    # remove anything inside brackets []
    title = re.sub(r"\[.*?\]", "", title)

    # remove anything after pipe (common in YouTube titles)
    title = re.sub(r"\|.*$", "", title)

    # normalize whitespace
    title = re.sub(r"\s+", " ", title).strip()

    return title


def load_easyid3(path: Path) -> EasyID3:
    try:
        return EasyID3(path)
    except ID3NoHeaderError:
        audio = MP3(path)
        audio.add_tags()
        return EasyID3(path)


def update_metadata(path: Path, title: str, band: str, album: str) -> None:
    audio = load_easyid3(path)
    audio["title"] = [str(title)]
    audio["artist"] = [str(band)]
    audio["album"] = [str(album)]
    audio.save()


def rename_file(path: Path, new_title: str) -> Path:
    new_path = path.with_name(f"{new_title}.mp3")

    # avoid renaming if same name
    if path.name != new_path.name:
        path.rename(new_path)

    return new_path


def process_song(song_path: Path, band: str, album: str) -> None:
    original_title = song_path.stem
    clean_title = clean_title_name(original_title, band)

    update_metadata(song_path, clean_title, band, album)
    new_path = rename_file(song_path, clean_title)

    print(f"Updated: {new_path.name}")


def get_playlists() -> list[str]:
    playlists = []

    while (True):
        playlist = input("Enter playlist (or enter to end): ").strip()

        if not playlist: break
        else: playlists.append(playlist)

    return playlists


def scrape_music(music_root: Path, playlists: list[str]) -> None:
    output_template = str(music_root / "%(uploader)s/%(playlist)s/%(title)s.%(ext)s")

    # makes sure yt-dlp is up to date
    print("Checking for yt-dlp updates")
    subprocess.run(["yt-dlp", "-U"]) 

    for playlist in playlists:
        try:
            subprocess.run(
                [
                    "yt-dlp",
                    "--ignore-errors",
                    "--format", "bestaudio",
                    "--extract-audio",
                    "--audio-format", "mp3",
                    "--audio-quality", "320k",
                    "--yes-playlist",
                    "--embed-thumbnail",
                    "--add-metadata",
                    "-o", output_template,
                    playlist,
                ],
                check=True,
            )

            print(f"Finished: {playlist}")
        except subprocess.CalledProcessError as e:
            print(f"Failed: {playlist}")


def organise(root: Path) -> None:
    for band_dir in root.iterdir():
        if not band_dir.is_dir():
            continue

        band_name = band_dir.name

        for album_dir in band_dir.iterdir():
            if not album_dir.is_dir():
                continue

            album_name = album_dir.name

            for song in album_dir.iterdir():
                if is_mp3(song):
                    try:
                        process_song(song, band_name, album_name)
                    except Exception as e:
                        print(f"Error processing {song.name}: {e}")


def main() -> None:
    root_input = input("Music root directory (press enter to use default - \"~/Music\"): ").strip()
    root = Path(root_input).expanduser() if root_input else Path("~/Music").expanduser()

    while True:
        option = input("""
1. Scrape music and organise
2. Organise existing music
Choose: """)

        if option == "1":
            playlists = get_playlists()
            if playlists:
                scrape_music(root, playlists)
                organise(root)
            break

        elif option == "2":
            organise(root)
            break         


if __name__ == "__main__":
    main()
