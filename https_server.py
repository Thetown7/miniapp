#!/usr/bin/env python3
import http.server
import ssl
import socketserver
import os

# Generiamo un certificato auto-firmato per test
os.system("openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj '/CN=localhost'")

PORT = 3000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Aggiungi header necessari per Telegram Mini App
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

httpd = socketserver.TCPServer(("", PORT), MyHTTPRequestHandler)

# Configura SSL
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain('cert.pem', 'key.pem')
httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

print(f"🔒 Server HTTPS avviato su https://localhost:{PORT}")
print(f"📱 Per Telegram Mini App usa: https://TUO_IP:{PORT}")
print("⚠️  Certificato auto-firmato - ignora warning del browser")

httpd.serve_forever()
