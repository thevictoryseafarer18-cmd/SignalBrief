#!/usr/bin/env python3
"""
Information Overload Eliminator - Local API & Web Server
Provides REST endpoints for news clustering, URL ingestion, and serves the Web UI.
"""

import http.server
import socketserver
import json
import os
import urllib.parse
from briefing_engine import run_pipeline, generate_markdown_briefing

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class BriefingHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/sample":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(os.path.join(BASE_DIR, "sample_data.json"), "r", encoding="utf-8") as f:
                self.wfile.write(f.read().encode("utf-8"))
            return
        elif parsed.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "app": "Information Overload Eliminator"}).encode("utf-8"))
            return
        
        # Default static file handler
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        if parsed.path == "/api/cluster":
            try:
                payload = json.loads(post_data.decode("utf-8"))
                articles = payload.get("articles", [])
                topic = payload.get("topic", "All")
                keywords = payload.get("keywords", [])
                threshold = float(payload.get("threshold", 0.25))

                result = run_pipeline(articles, topic=topic, keywords=keywords, threshold=threshold)
                markdown = generate_markdown_briefing(result["briefings"], result["metrics"])
                result["markdown"] = markdown

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        elif parsed.path == "/api/ingest-url":
            # Quick simulated / extracted metadata from URL
            try:
                payload = json.loads(post_data.decode("utf-8"))
                url = payload.get("url", "").strip()
                title = payload.get("title", "").strip()
                source = payload.get("source", "").strip()
                topic = payload.get("topic", "Artificial Intelligence").strip()
                content = payload.get("content", "").strip()

                if not title:
                    # Infer reasonable title from URL if omitted
                    slug = url.rstrip("/").split("/")[-1].replace("-", " ").title()
                    title = slug if slug else "Extracted Article Coverage"
                if not source:
                    # Infer source from domain
                    domain = urllib.parse.urlparse(url).netloc.replace("www.", "")
                    source = domain.split(".")[0].title() if domain else "Web Source"

                new_article = {
                    "id": f"art-custom-{int(os.times().elapsed * 1000)}",
                    "title": title,
                    "source": source,
                    "url": url if url else "https://example.com/article",
                    "date": "2024-11-12",
                    "topic": topic,
                    "author": "Online Desk",
                    "content": content if content else f"{title}. Full coverage reporting on recent developments and industry reactions.",
                    "key_points": [f"Key update reported by {source} regarding {title}."]
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "article": new_article}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

def main():
    with socketserver.TCPServer(("", PORT), BriefingHandler) as httpd:
        print(f"⚡ Information Overload Eliminator server running at http://localhost:{PORT}")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
