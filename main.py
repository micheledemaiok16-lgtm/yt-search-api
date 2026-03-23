from flask import Flask, request, jsonify
from ddgs import DDGS
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
        results = DDGS().videos(
            query=query,
            region="wt-wt",
            safesearch="off",
            max_results=max_results
        )
        videos = []
        for video in results:
            content_url = video.get("content", "")
            if "youtube.com" in content_url or "youtu.be" in content_url:
                video_id = ""
                if "watch?v=" in content_url:
                    video_id = content_url.split("watch?v=")[1].split("&")[0]
                elif "youtu.be/" in content_url:
                    video_id = content_url.split("youtu.be/")[1].split("?")[0]
                videos.append({
                    "id": video_id,
                    "title": video.get("title", ""),
                    "channel": video.get("uploader", ""),
                    "duration": video.get("duration", ""),
                    "view_count": video.get("statistics", {}).get("viewCount"),
                    "url": content_url,
                    "thumbnail": video.get("images", {}).get("large", "")
                })
        return jsonify({
            "success": True,
            "query": query,
            "results": videos
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/video-info', methods=['POST'])
def video_info():
    try:
        data = request.json
        query = data.get('query') or data.get('url')
        if not query:
            return jsonify({"error": "query or url required"}), 400
        results = DDGS().videos(
            query=query,
            region="wt-wt",
            safesearch="off",
            max_results=1
        )
        if not results:
            return jsonify({"error": "No results found"}), 404
        video = results[0]
        return jsonify({
            "success": True,
            "video": {
                "id": video.get("content", "").split("watch?v=")[-1].split("&")[0] if "watch?v=" in video.get("content", "") else "",
                "title": video.get("title", ""),
                "channel": video.get("uploader", ""),
                "duration": video.get("duration", ""),
                "view_count": video.get("statistics", {}).get("viewCount"),
                "published": video.get("published", ""),
                "description": video.get("description", "")[:500]
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
