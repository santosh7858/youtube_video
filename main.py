from flask import Flask, request, jsonify
import subprocess
import json
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ YouTube Search & Related API is Live!"

@app.route('/search')
def search_youtube():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Missing search query'}), 400

    cookie_path = os.path.join(os.path.dirname(__file__), 'youtube_cookies.txt')

    cmd = [
        "yt-dlp",
        f"ytsearch10:{query}",
        "--cookies", cookie_path,
        "--dump-json",
        "--skip-download",
        "--no-warnings"
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        videos = [json.loads(line) for line in result.stdout.strip().split("\n")]
        simplified = [{
            "title": v.get("title"),
            "video_id": v.get("id"),
            "url": v.get("webpage_url"),
            "duration": v.get("duration"),
            "thumbnail": v.get("thumbnail")
        } for v in videos]
        return jsonify({'results': simplified})
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
        related = data.get("related_videos", [])
        simplified = [{
            "title": v.get("title"),
            "video_id": v.get("id"),
            "url": f"https://www.youtube.com/watch?v={v.get('id')}",
            "thumbnails": v.get("thumbnails")
        } for v in related]
        return jsonify({'related_videos': simplified})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': e.stderr.strip()}), 500
    except json.JSONDecodeError:
        return jsonify({'error': 'Failed to parse related videos'}), 500

if __name__ == '__main__':
    app.run(debug=True)
