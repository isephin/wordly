"""Run on each trusted LAN machine: python -m distributed.worker --port 8765."""
import argparse, hmac, json, os, socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from time import perf_counter
from core.advanced_analyzer import count_chunk, options
from distributed.distributed import MAX_BYTES

# Receive JSON requests and reuse the same word-counting engine as the coordinator.
class Handler(BaseHTTPRequestHandler):
    # Encode a bounded JSON response and send HTTP headers.
    def reply(self, status, data):
        body=json.dumps(data,ensure_ascii=False).encode('utf-8')
        if len(body) > MAX_BYTES:
            status, body = (413, b'{"error":"Result too large"}')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    # Compare the supplied token to the configured shared token.
    def authorized(self):
        return hmac.compare_digest(self.headers.get('Authorization','').encode(), ('Bearer '+self.server.token).encode())
    # Health endpoint identifies an available worker.
    def do_GET(self):
        if not self.authorized():
            return self.reply(401, {'error': 'Unauthorized'})
        if self.path != '/health':
            return self.reply(404, {'error': 'Not found'})
        self.reply(200,{'name':socket.gethostname()})
    # Count a received batch and return its partial frequencies and elapsed time.
    def do_POST(self):
        if not self.authorized():
            return self.reply(401, {'error': 'Unauthorized'})
        if self.path != '/count':
            return self.reply(404, {'error': 'Not found'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0 < size <= MAX_BYTES:
                return self.reply(413, {'error': 'Invalid chunk size'})
            self.connection.settimeout(60)
            data = json.loads(self.rfile.read(size))
            lines = data['lines']
            opt = options(data['options'])
            if not isinstance(lines, list) or len(lines) > 1100000 or any((not isinstance(x, str) for x in lines)):
                raise ValueError('Invalid lines')
            start = perf_counter()
            counts = count_chunk((lines, opt))
            elapsed = perf_counter() - start
            self.reply(200,{'counts':dict(counts),'lines':len(lines),'seconds':elapsed,'name':socket.gethostname()})
        except (ValueError,KeyError,TypeError): self.reply(400,{'error':'Invalid request'})

# Start an HTTP worker on the requested address and port.
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--host', default='0.0.0.0')
    args = parser.parse_args()
    token=os.environ.get('WORDLY_TOKEN','')
    if len(token) < 24:
        raise SystemExit('Set WORDLY_TOKEN to a shared secret of at least 24 characters.')
    server = HTTPServer((args.host, args.port), Handler)
    server.token = token
    print('Wordly worker listening on port', args.port, flush=True)
    server.serve_forever()
if __name__ == '__main__':
    main()
