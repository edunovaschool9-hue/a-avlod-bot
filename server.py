import http.server
import socketserver
import os

# Railway beradigan portni o'qiymiz (bo'lmasa 8080)
PORT = int(os.environ.get("PORT", 8080))

Handler = http.server.SimpleHTTPRequestHandler

# Barcha manzillardan (0.0.0.0) tinglaymiz — Railway shu talab qiladi
with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
    print(f"Serving static site on port {PORT}")
    httpd.serve_forever()
