"""
Voice News Assistant - English only (NewsAPI + Windows SAPI voice)
Install: pip install requests pywin32 SpeechRecognition pyaudio
 
API key: PowerShell me ek baar chalao, phir terminal restart karo:
    setx NEWSAPI_KEY "your_key_here"
 
Commands (voice se bolo):
    "news"                              -> top headlines (India)
    "sports" / "technology" / "health"  -> category news
    "cricket" / "tell me about Tesla"   -> topic search
    "stop" / "exit"                     -> band
News ke beech rokne ke liye: koi bhi key dabao, ya headlines ke beech "stop" bolo.
"""
 
import os
import json
import time
import msvcrt                     
import requests
import win32com.client
import speech_recognition as sr
from flask import Flask, jsonify, request
from flask_cors import CORS
import sys

app = Flask(__name__)
CORS(app)
 
API_KEY = os.environ.get("NEWSAPI_KEY", "5f8d74a562c3462ab40c22ea78e21617")
TOP_URL = "https://newsapi.org/v2/top-headlines"
EVERYTHING_URL = "https://newsapi.org/v2/everything"
MAX_RETRIES = 2
PAGE_SIZE = 5
VOICE_STOP = True                  # headlines ke beech "stop" sunna
STOP_WORDS = ("stop", "enough", "cancel", "quiet", "exit")
SVS_ASYNC, SVS_PURGE = 1, 2        # SAPI flags
 
 
class StopNews(Exception):
    """News beech me rokne ke liye."""
 
 
CATEGORIES = {
    "sports": "sports", "business": "business", "technology": "technology",
    "tech": "technology", "health": "health", "entertainment": "entertainment",
    "science": "science",
}
FILLER = ("my topic is", "tell me about", "news about", "news on",
          "i want to know about", "search for", "about", "latest",
          "news", "please")
HTTP_MESSAGES = {
    400: "The request was invalid.",
    401: "Your API key is invalid. Please check the key.",
    426: "Your plan does not allow this request.",
    429: "Too many requests. Please wait and try again.",
}
 
speaker = win32com.client.Dispatch("SAPI.SpVoice")
recognizer = sr.Recognizer()
 
 
# ---------------- TEXT TO SPEECH ----------------
def set_english_voice():
    try:
        voices = speaker.GetVoices()
        for i in range(voices.Count):
            voice = voices.Item(i)
            if any(k in voice.GetDescription().lower()
                   for k in ("english", "zira", "david", "heera", "ravi")):
                speaker.Voice = voice
                return
    except Exception as e:
        print("Voice setup error:", e)
 
 
def flush_keys():
    while msvcrt.kbhit():
        msvcrt.getch()
 
 
def key_pressed():
    if msvcrt.kbhit():
        flush_keys()
        return True
    return False
 
 
def say(text, interruptible=False):
    print("🔊", text)
    try:
        speaker.Speak(text, SVS_ASYNC)                 
        while not speaker.WaitUntilDone(100):          
            if interruptible and key_pressed():
                speaker.Speak("", SVS_PURGE)           
                raise StopNews
        time.sleep(0.8)                               
    except StopNews:
        raise
    except Exception as e:
        print("Speech error:", e)
 
 
# ---------------- SPEECH TO TEXT ----------------
def listen():
    try:
        with sr.Microphone() as mic:
            recognizer.adjust_for_ambient_noise(mic, duration=0.5)
            print("🎤 Listening...")
            audio = recognizer.listen(mic, timeout=6, phrase_time_limit=6)
        return recognizer.recognize_google(audio, language="en-IN").lower()
    except (sr.WaitTimeoutError, sr.UnknownValueError):
        return ""
    except sr.RequestError:
        say("Speech service is not reachable. Please check your internet.")
    except (OSError, AttributeError):
        say("Microphone not found. Please connect a microphone.")
        time.sleep(3)
    return ""
 
 
def voice_stop_requested():
   
    try:
        with sr.Microphone() as mic:
            audio = recognizer.listen(mic, timeout=2, phrase_time_limit=2)
        text = recognizer.recognize_google(audio, language="en-IN").lower()
        print("Heard:", text)
        return any(w in text for w in STOP_WORDS)
    except Exception:
        return False
 
 
# ---------------- NEWS API ----------------
def call_api(url, params):
    
    headers = {"X-Api-Key": API_KEY}                   
    last_error = "Unknown error."
    for attempt in range(1, MAX_RETRIES + 2):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            data = json.loads(resp.text)
            if data.get("status") != "ok":
                return [], data.get("message", "The news service returned an error.")
            return data.get("articles", []), None
        except requests.exceptions.HTTPError:
            code = resp.status_code
            if code >= 500:
                last_error = "The news server is having problems."
            else:
                return [], HTTP_MESSAGES.get(code, f"News service returned error {code}.")
        except requests.exceptions.Timeout:
            last_error = "The news server took too long to respond."
        except requests.exceptions.ConnectionError:
            last_error = "No internet connection."
        except (json.JSONDecodeError, ValueError):
            last_error = "Received an invalid response from the news server."
        except requests.exceptions.RequestException as e:
            last_error = f"Network error: {type(e).__name__}."
        print(f"Attempt {attempt} failed: {last_error}")
        if attempt <= MAX_RETRIES:
            time.sleep(2)
    return [], last_error
 
 
def fetch_news(category=None, query=None):
    if query:                                          # topic search
        return call_api(EVERYTHING_URL, {"q": query, "language": "en",
                                         "sortBy": "publishedAt", "pageSize": PAGE_SIZE})
    params = {"country": "in", "pageSize": PAGE_SIZE}
    if category:
        params["category"] = category
    articles, error = call_api(TOP_URL, params)
    if not error and not articles:                     # khali ho to fallback
        return call_api(EVERYTHING_URL, {"q": category or "India", "language": "en",
                                         "sortBy": "publishedAt", "pageSize": PAGE_SIZE})
    return articles, error
 
 
def read_news(category=None, query=None):
    say("Fetching the latest news. Press any key to stop.")
    articles, error = fetch_news(category, query)
    if error:
        say(f"Sorry. {error}")
        return
    if not articles:
        say("Sorry, I could not find any news on that topic.")
        return
    flush_keys()                                       
    try:
        for i, art in enumerate(articles, 1):
            title = art.get("title") or "No title"
            desc = art.get("description") or ""
            say(f"News {i}.", interruptible=True)
            say(f"{title}. {desc}", interruptible=True)
            if VOICE_STOP and i < len(articles) and voice_stop_requested():
                raise StopNews
        say("That was the latest news.")
    except StopNews:
        say("News stopped.")
 
 
# ---------------- COMMAND HANDLER ----------------
def clean_query(cmd):
    for f in FILLER:
        cmd = cmd.replace(f, " ")
    return " ".join(cmd.split())
 
 
def handle(cmd):
    if any(w in cmd for w in ("exit", "quit", "stop", "goodbye")):
        say("Goodbye! Drive safe.")
        return False
    for word, cat in CATEGORIES.items():
        if word in cmd:
            read_news(category=cat)
            return True
    query = clean_query(cmd)
    read_news(query=query) if query else read_news()
    return True
 
 
def main():
    if API_KEY == "YOUR_NEWSAPI_KEY":
        print("Please set your NewsAPI key (setx NEWSAPI_KEY \"your_key\") first.")
        return
    set_english_voice()
    say("Hello! Say news to hear the headlines, or name a topic.")
    running = True
    try:
        while running:
            try:
                cmd = listen()
                if cmd:
                    print("You said:", cmd)
                    running = handle(cmd)
            except Exception as e:
                print("Unexpected error:", type(e).__name__, e)
                say("Something went wrong. Please try again.")
    except KeyboardInterrupt:
        say("Assistant stopped.")
 
 
# ---------------- FLASK WEB API ----------------

@app.route("/api/news", methods=["GET"])
def api_news():
    category = request.args.get("category", "general").lower()
    query = request.args.get("q", "").strip()

    allowed_categories = {
        "general", "sports", "business", "technology",
        "health", "entertainment", "science"
    }

    if category not in allowed_categories:
        category = "general"

    if not API_KEY:
        return jsonify({
            "error": "NewsAPI key missing. Set NEWSAPI_KEY first."
        }), 500

    # Reuse your existing NewsAPI function
    articles, error = fetch_news(
        category=None if query else category,
        query=query if query else None
    )

    if error:
        return jsonify({"error": error}), 502

    results = []

    for article in articles:
        source = article.get("source") or {}

        results.append({
            "title": article.get("title") or "No title",
            "description": article.get("description") or "",
            "source": source.get("name") or "Unknown",
            "url": article.get("url") or "",
            "image": article.get("urlToImage") or "",
            "publishedAt": article.get("publishedAt") or ""
        })

    return jsonify({"articles": results})


@app.route("/")
def home():
    return jsonify({
        "message": "News Voice Assistant API is running",
        "news_endpoint": "/api/news"
    })

    

if __name__ == "__main__":
    if "--voice" in sys.argv:
        main()
    else:
        if not API_KEY:
            print("Warning: NEWSAPI_KEY environment variable is missing.")

        print("News API running at http://127.0.0.1:5000")
        app.run(
            host="127.0.0.1",
            port=5000,
            debug=False,
            use_reloader=False
        )