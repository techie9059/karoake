import requests
from flask import Flask, request, jsonify
import subprocess
import os
import tempfile
import re
from ytmusicapi import YTMusic
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)


@app.route("/", methods=["POST"])
def process():
    try:
        data = request.get_json()
        url = data.get("url")
        print("Working on", url)
        if not url:
            return jsonify({"error": "No URL Provided"}), 400

        with tempfile.TemporaryDirectory() as tmpdirname:
            cmd = f"spotdl {url} --output {tmpdirname} --generate-lrc"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            youtube_link_pattern = r"https://music\.youtube\.com/watch\?v=[\w-]+"
            youtube_links = re.findall(youtube_link_pattern, result.stdout)
            ytLink = None
            if youtube_links:
                ytLink = youtube_links[0]
                print(youtube_links[0])

            files = os.listdir(tmpdirname)
            audio_files = [
                file for file in files if file.endswith((".mp3", ".wav", ".ogg"))
            ]
            old_path = os.path.join(tmpdirname, audio_files[0])
            new_path = os.path.join(tmpdirname, "audio.mp3")
            os.rename(old_path, new_path)

            lyrics_text = ""
            hasLyrics = False
            lyric_files = [file for file in files if file.endswith((".lrc"))]

            if len(lyric_files) > 0:
                lyric_path = os.path.join(tmpdirname, lyric_files[0])
                with open(lyric_path, "r", encoding="utf-8") as lyric_file:
                    lyrics_text = lyric_file.read()
                print("Using Synced Lyrics...")
                hasLyrics = True
            else:
                if ytLink is not None:
                    try:
                        yt = YTMusic()
                        parsedUrl = urlparse(ytLink)
                        videoId = parse_qs(parsedUrl.query)["v"][0]
                        id = yt.get_watch_playlist(videoId)["lyrics"]
                        lyrics = yt.get_lyrics(id)["lyrics"]
                        lyrics_text = lyrics
                        hasLyrics = True
                        print("Using YT Music Lyrics...")
                    except:
                        pass

            data = {"api_token": "f3GS8yKdgff1ZZfZh64LJFLHE8tHAU", "sep_type": 25}
            with open(f"{tmpdirname}/audio.mp3", "rb") as file:
                files = {"audiofile": ("audio.mp3", file, "audio/mp3")}
                response = requests.post(
                    "https://mvsep.com/api/separation/create", data=data, files=files
                )
            response = response.json()
            if response["success"]:
                return jsonify(
                    {
                        "link": response["data"]["link"],
                        "done": True,
                        "hasLyrics": hasLyrics,
                        "lyrics": lyrics_text,
                    }
                )
            else:
                return jsonify(
                    {
                        "reason": "Server is busy! Please try after some time.",
                        "done": False,
                    }
                )
    except Exception as e:
        return jsonify(
            {"reason": str(e) + "\nPlease try with another song!", "done": False}
        )


if __name__ == "__main__":
    app.run()
