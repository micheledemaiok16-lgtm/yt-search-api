from flask import Flask, request, jsonify
from ddgs import DDGS
import os
import re

app = Flask(__name__)


def normalize(text):
    """Rimuove accenti, punteggiatura e lowercase per confronto."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def match_score(title, artist, song):
    """Calcola quanto un titolo corrisponde ad artista e canzone."""
    title_norm = normalize(title)
    artist_norm = normalize(artist)
    song_norm = normalize(song)

    score = 0

    # Controlla se l'artista è nel titolo
    artist_words = artist_norm.split()
    artist_matches = sum(1 for w in artist_words if w in title_norm)
    score += (artist_matches / len(artist_words)) * 50 if artist_words else 0

    # Controlla se il nome della canzone è nel titolo
    song_words = song_norm.split()
    song_matches = sum(1 for w in song_words if w in title_norm)
    score += (song_matches / len(song_words)) * 50 if song_words else 0

    return score


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})


@app.route('/search', methods=['POST'])
def search_youtube():
    try:
        data = request.json
        query = data.get('query')
        artist = data.get('artist', '')
        song = data.get('song', '')
        max_results = data.get('max_results', 5)

        if not query and not (artist and song):
            return jsonify({"error": "query or artist+song required"}), 400

        if not query:
            query = f'{artist} {song}'

        search_query = f'{query} youtube music video'

        results = DDGS().videos(
            query=search_query,
            region="wt-wt",
            safesearch="off",
            max_results=max_results * 3
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

                title = video.get("title", "")
                score = match_score(title, artist or query.split(' - ')[0], song or query.split(' - ')[-1])

                videos.append({
                    "id": video_id,
                    "title": title,
                    "channel": video.get("uploader", ""),
                    "duration": video.get("duration", ""),
                    "view_count": video.get("statistics", {}).get("viewCount"),
                    "url": content_url,
                    "thumbnail": video.get("images", {}).get("large", ""),
                    "match_score": round(score, 1)
                })

        # Ordina per match_score decrescente
        videos.sort(key=lambda x: x['match_score'], reverse=True)

        # Restituisci solo i migliori risultati
        videos = videos[:max_results]

        return jsonify({
            "success": True,
            "query": search_query,
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
