from flask import Flask, request, jsonify
import subprocess
import json
import os

app = Flask(__name__)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})


@app.route('/search', methods=['POST'])
def search_youtube():
    try:
        data = request.json
        query = data.get('query')
        max_results = data.get('max_results', 1)

        if not query:
            return jsonify({"error": "query required"}), 400

        cmd = [
            'yt-dlp',
            f'ytsearch{max_results}:{query}',
            '--dump-json',
            '--no-download',
            '--no-warnings',
            '--ignore-errors'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0 and not result.stdout:
            return jsonify({"error": "Search failed", "details": result.stderr}), 500

        videos = []
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    video = json.loads(line)
                    videos.append({
                        "id": video.get("id"),
                        "title": video.get("title"),
                        "channel": video.get("channel"),
                        "duration": video.get("duration"),
                        "view_count": video.get("view_count"),
                        "url": f"https://www.youtube.com/watch?v={video.get('id')}",
                        "thumbnail": video.get("thumbnail")
                    })
                except json.JSONDecodeError:
                    continue

        return jsonify({
            "success": True,
            "query": query,
            "results": videos
        })

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Search timeout"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/video-info', methods=['POST'])
def video_info():
    try:
        data = request.json
        url = data.get('url')

        if not url:
            return jsonify({"error": "url required"}), 400

        cmd = [
            'yt-dlp',
            url,
            '--dump-json',
            '--no-download',
            '--no-warnings'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return jsonify({"error": "Failed to get video info"}), 500

        video = json.loads(result.stdout)

        return jsonify({
            "success": True,
            "video": {
                "id": video.get("id"),
                "title": video.get("title"),
                "channel": video.get("channel"),
                "duration": video.get("duration"),
                "view_count": video.get("view_count"),
                "upload_date": video.get("upload_date"),
                "description": video.get("description", "")[:500]
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
