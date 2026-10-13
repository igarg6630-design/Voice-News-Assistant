
from flask import Flask, request, jsonify
from flask_cors import CORS

from news_api import fetch_news, API_KEY

app = Flask(__name__)
CORS(app)


@app.route("/")
def home():
    return jsonify({
        "message": "Voice News Assistant API is running!"
    })


@app.route("/api/news", methods=["GET"])
def get_news():
    category = request.args.get("category", "").strip().lower()
    query = request.args.get("q", "").strip()

    allowed_categories = {
        "sports", "business", "technology",
        "health", "entertainment", "science"
    }

    if not API_KEY or API_KEY == "YOUR_NEWSAPI_KEY":
        return jsonify({
            "error": "NEWSAPI_KEY is missing. Please configure your API key.",
            "articles": []
        }), 500

    # Search by topic, e.g. cricket or Tesla
    if query:
        articles, error = fetch_news(query=query)

    # Fetch category headlines
    elif category:
        if category not in allowed_categories:
            return jsonify({
                "error": "Invalid news category.",
                "articles": []
            }), 400

        articles, error = fetch_news(category=category)

    # Default: top headlines
    else:
        articles, error = fetch_news()

    if error:
        return jsonify({
            "error": error,
            "articles": []
        }), 502

    # Convert NewsAPI response to the format expected by your HTML
    formatted_articles = []

    for article in articles:
        source = article.get("source") or {}

        formatted_articles.append({
            "title": article.get("title") or "No title",
            "description": article.get("description") or "",
            "source": source.get("name", "Unknown source"),
            "url": article.get("url") or "",
            "publishedAt": article.get("publishedAt") or ""
        })

    return jsonify({
        "articles": formatted_articles
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)