from flask import Flask, request, jsonify
import subprocess
import json
import os

app = Flask(__name__)

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

    cookie_path = os.path.join(os.path.dirname(__file__), 'youtube_cookies.txt')

    total_limit = limit * page

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
        all_videos = [json.loads(line) for line in result.stdout.strip().split("\n")]

        # Get only the page slice
        start_index = (page - 1) * limit
        end_index = start_index + limit
        selected_videos = all_videos[start_index:end_index]

        seen_ids = set()
        unique_videos = []
        for v in selected_videos:
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
                "author_logo": v.get("channel_thumbnail")
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
                "author_logo": v.get("channel_thumbnail", [{}])[-1].get("url")
            })

        return jsonify({'related_videos': simplified})

    except subprocess.CalledProcessError as e:
        return jsonify({'error': e.stderr.strip()}), 500
    except json.JSONDecodeError:
        return jsonify({'error': 'Failed to parse related videos'}), 500

if __name__ == '__main__':
    app.run(debug=True)
