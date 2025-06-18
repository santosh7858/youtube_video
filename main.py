from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import json
import os

app = Flask(__name__)
CORS(app)  # Allow AJAX requests from browser

def build_thumbnail_url(video_id):
    return f"https://i.ytimg.com/vi/{video_id}/hq720.jpg"

@app.route('/')
def index():
    return "✅ YouTube Metadata API is Live!"

@app.route('/search')
def search_youtube():
    query = request.args.get('q')
    limit = int(request.args.get('limit', 10))
    page = int(request.args.get('page', 1))

    if not query:
        return jsonify({'error': 'Missing search query'}), 400

    offset = (page - 1) * limit
    total_limit = offset + limit

    cookie_file = os.path.join(os.path.dirname(__file__), 'youtube_cookies.txt')

    cmd = [
        "yt-dlp",
        f"ytsearch{total_limit}:{query}",
        "--cookies", cookie_file,
        "--dump-json",
        "--skip-download",
        "--no-warnings"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split("\n")
        videos = [json.loads(line) for line in lines[offset:offset + limit]]

        seen = set()
        clean_videos = []

        for v in videos:
            vid = v.get("id")
            if vid in seen:
                continue
            seen.add(vid)

            clean_videos.append({
                "video_id": vid,
                "title": v.get("title"),
                "description": v.get("description"),
                "duration": v.get("duration"),
                "thumbnail": build_thumbnail_url(vid),
                "author": v.get("uploader"),
                "author_logo": (v.get("channel_thumbnail") or [{}])[-1].get("url")
            })

        return jsonify({'results': clean_videos})

    except subprocess.CalledProcessError as e:
        return jsonify({'error': e.stderr.strip()}), 500
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid YouTube response'}), 500

@app.route('/related')
def related_videos():
    video_id = request.args.get('video_id')
    if not video_id:
        return jsonify({'error': 'Missing video ID'}), 400

    cookie_file = os.path.join(os.path.dirname(__file__), 'youtube_cookies.txt')

    cmd = [
        "yt-dlp",
        f"https://www.youtube.com/watch?v={video_id}",
        "--cookies", cookie_file,
        "--dump-single-json",
        "--no-warnings",
        "--extractor-args", "youtube:player_client=web"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        related = data.get("related_videos", [])[:10]

        seen = set()
        simplified = []

        for v in related:
            vid = v.get("id")
            if not vid or vid in seen:
                continue
            seen.add(vid)

            simplified.append({
                "video_id": vid,
                "title": v.get("title"),
                "description": v.get("short_description"),
                "duration": v.get("length_seconds"),
                "thumbnail": build_thumbnail_url(vid),
                "author": v.get("author"),
                "author_logo": (v.get("channel_thumbnail") or [{}])[-1].get("url")
            })

        return jsonify({'related_videos': simplified})

    except subprocess.CalledProcessError as e:
        return jsonify({'error': e.stderr.strip()}), 500
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid related video data'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=False, host='0.0.0.0', port=port)
