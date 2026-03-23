from flask import Flask, request, jsonify
from ddgs import DDGS
import os
import re

app = Flask(__name__)


def normalize(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def match_score(title, artist, song):
    title_norm = normalize(title)
    artist_norm = normalize(artist)
    song_norm = normalize(song)
    score = 0

    artist_words = artist_norm.split()
    if artist_words:
        artist_matches = sum(1 for w in artist_words if w in title_norm)
        score += (artist_matches / len(artist_words)) * 50

    song_words = song_norm.split()
    if song_words:
        song_matches = sum(1 for w in song_words if w in title_norm)
        score += (song_matches / len(song_words)) * 50

    return score


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})


@app.route('/search', methods=['POST'])
def search_youtube():
    try:
        data = request.json
        artist = data.get('artist', '').strip()
        song = data.get('song', '').strip()
        query = data.get('query', '').strip()
        max_results = data.get('max_results', 3)

        if not query and not (artist and song):
            return jsonify({"error": "query or artist+song required"}), 400

        if not artist and not song and query:
            parts = query.split(' - ', 1)
            artist = parts[0].strip() if len(parts) > 1 else ''
            song = parts[-1].strip()

        # Prova diverse query in ordine di precisione
        search_queries = [
            f'"{artist}" "{song}" youtube',
            f'{artist} - {song}',
            f'{artist} {song}',
        ]

        best_videos = []

        for sq in search_queries:
            try:
                results = DDGS().videos(
                    query=sq,
                    region="wt-wt",
                    safesearch="off",
                    max_results=10
                )
            except Exception:
                continue

            for video in results:
                content_url = video.get("content", "")
                if "youtube.com" not in content_url and "youtu.be" not in content_url:
                    continue

                video_id = ""
                if "watch?v=" in content_url:
                    video_id = content_url.split("watch?v=")[1].split("&")[0]
                elif "youtu.be/" in content_url:
                    video_id = content_url.split("youtu.be/")[1].split("?")[0]

                # Evita duplicati
                if any(v['id'] == video_id for v in best_videos):
                    continue

                title = video.get("title", "")
                score = match_score(title, artist, song)

                best_videos.append({
                    "id": video_id,
                    "title": title,
                    "channel": video.get("uploader", ""),
                    "duration": video.get("duration", ""),
                    "view_count": video.get("statistics", {}).get("viewCount"),
                    "url": content_url,
                    "thumbnail": video.get("images", {}).get("large", ""),
                    "match_score": round(score, 1)
                })

            # Se troviamo un match con score >= 80, non servono altre query
            if any(v['match_score'] >= 80 for v in best_videos):
                break

        best_videos.sort(key=lambda x: x['match_score'], reverse=True)
        best_videos = best_videos[:max_results]

        return jsonify({
            "success": True,
            "artist": artist,
            "song": song,
            "results": best_videos
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
