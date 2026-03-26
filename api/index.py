"""Vercel serverless function using BaseHTTPRequestHandler."""
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'''<!DOCTYPE html>
<html>
<head><title>Oracle Agent</title></head>
<body style="font-family:Arial;text-align:center;padding:50px;background:linear-gradient(135deg,#667eea,#764ba2);color:white">
    <h1>\xf0\x9f\x9a\x80 Oracle Agent</h1>
    <h2 style="color:#4CAF50">\xe2\x9c\x85 Working!</h2>
    <p>Vercel deployment successful</p>
</body>
</html>''')
    
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')
