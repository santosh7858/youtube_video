from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import json
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for AJAX

def build_thumbnail_url(video_id):
    return f"https://i.ytimg.com/vi/{video_id}/hq720.jpg"

@app.route('/')
def home():
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

    cookie_path = os.path.join(os.path.dirname(__file__), 'youtube_cookies.txt')

    cmd = [
        "yt-dlp",
        f"ytsearch{total_limit}:{query}",
        "--cookies", cookie_path,
        "--dump-json",
        "--skip-download",
        "--no-warnings"
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

        videos = []
        for line in result.stdout.strip().split("\n"):
            try:
                v = json.loads(line)
                videos.append(v)
            except json.JSONDecodeError:
                continue

        videos = videos[offset:offset + limit]

        seen_ids = set()
        unique_videos = []
        for v in videos:
            vid = v.get("id")
            if vid in seen_ids:
                continue
            seen_ids.add(vid)

            unique_videos.append({
                "video_id": vid,
                "title": v.get("title"),
                "description": v.get("description"),
                "duration": v.get("duration"),
                "thumbnail": build_thumbnail_url(vid),
                "author": v.get("uploader"),
                "author_logo": (v.get("channel_thumbnail") or [{}])[-1].get("url")
            })

        return jsonify({'results': unique_videos})

    except subprocess.CalledProcessError as e:
        return jsonify({'error': e.stderr.strip()}), 500


@app.route('/related')
def related_videos():
    video_id = request.args.get('video_id')
    if not video_id:
        return jsonify({'error': 'Missing video ID'}), 400

    cookie_path = os.path.join(os.path.dirname(__file__), 'youtube_cookies.txt')

    cmd = [
        "yt-dlp",
        f"https://www.youtube.com/watch?v={video_id}",
        "--cookies", cookie_path,
        "--dump-single-json",
        "--no-warnings",
        "--extractor-args", "youtube:player_client=web"
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        data = json.loads(result.stdout)
        related = data.get("related_videos", [])[:10]

        seen_ids = set()
        simplified = []

        for v in related:
            vid = v.get("id")
            if not vid or vid in seen_ids:
                continue
            seen_ids.add(vid)

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
        return jsonify({'error': 'Failed to parse related videos'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=True, host='0.0.0.0', port=port)
