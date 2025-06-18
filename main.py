from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import json

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COOKIES_FILE = "youtube_cookies.txt"

def run_yt_dlp(command_args):
    try:
        result = subprocess.run(
            command_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        return {"error": e.stderr.strip()}


@app.get("/related")
def get_related_videos(video_id: str = Query(..., description="YouTube video ID")):
    cmd = [
        "yt-dlp",
        f"https://www.youtube.com/watch?v={video_id}",
        "--cookies", COOKIES_FILE,
        "--flat-playlist",
        "--dump-json",
        "--skip-download",
        "--extractor-args", "youtube:player_client=web",
        "--no-warnings",
        "--print", "%(related_videos_json)s"
    ]

    result = run_yt_dlp(cmd)

    if "error" in result:
        return {"status": "error", "message": result["error"]}
    
    try:
        # related_videos_json is a stringified JSON list
        related = json.loads(result)
        return {"status": "success", "related_videos": related}
    except:
        return {"status": "error", "message": "No related videos found or parsing failed."}


@app.get("/search")
def search_youtube(q: str = Query(..., description="Search query")):
    cmd = [
        "yt-dlp",
        f"ytsearch10:{q}",
        "--cookies", COOKIES_FILE,
        "--dump-json",
        "--skip-download",
        "--extractor-args", "youtube:player_client=web",
        "--no-warnings"
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        videos = [json.loads(line) for line in result.stdout.strip().split("\n")]
        return {"status": "success", "results": videos}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": e.stderr.strip()}
