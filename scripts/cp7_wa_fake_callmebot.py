"""Fake CallMeBot for the WA tests (owner D17-6): GET /whatsapp.php?phone=&text=&apikey= answers 200 "Message queued"
(the key echoed back, so the tests can prove it is masked before it is stored), or 500 when the text contains FAIL.
Every request is printed as one line "FAKE_REQUEST {json}". Runs only inside the CI stack's docker network; it never
forwards anything."""
import http.server
import json
import urllib.parse


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
        fail = 'FAIL' in q.get('text', '')
        status = 500 if fail else 200
        print('FAKE_REQUEST ' + json.dumps(dict(path=url.path, phone=q.get('phone'), text=q.get('text'), apikey=q.get('apikey'), status=status)), flush=True)
        self.send_response(status)
        self.end_headers()
        self.wfile.write(b'error' if fail else ('Message queued apikey=' + q.get('apikey', '')).encode())

    def log_message(self, *args):
        pass


http.server.ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
