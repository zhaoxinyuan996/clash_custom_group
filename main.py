import socket
import requests
import http.server
import socketserver
from typing import Optional
from urllib.parse import unquote
from modify_yaml import RouterModify


host = socket.gethostbyname(socket.gethostname())
port = 8000

delay_url = 'http://www.gstatic.com/generate_204'
delay_interval = 100


class Handler(http.server.BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.msg: bytes = b'HTTP/1.1 200 OK\r\n'
        super().__init__(*args, **kwargs)

    def _net(self):
        """获取原生订阅信息"""
        path = unquote(self.path)
        print(f'parse: {path}')
        session = requests.Session()
        session.trust_env = False
        response = session.get(path, verify=False)

        return response

    def parse_url(self) -> Optional[bytes]:
        """路由就是原生订阅链接"""
        if self.path and len(self.path) > 1:
            self.path = self.path[1:]
            return b''
        return b'parse url error'

    def end_headers(self):
        """继承占位，空调用"""
        ...

    def build_headers(self, headers):
        data = b''
        for k, v in headers.items():
            if k.lower() in ('content-encoding', 'content-length', 'transfer-encoding'):
                continue
            data += f'{k}: {v}\r\n'.encode()

        self.msg += data

    def build_body(self, body):
        self.msg += body

    def do_GET(self):
        self.parse_url()
        response = self._net()

        self.build_headers(response.headers)

        body = RouterModify(response.text).build()
        self.msg += f'Content-Length: {len(body)}\r\n\r\n'.encode()
        self.build_body(body)

        RouterModify.record(self.msg)
        self.wfile.write(self.msg)

    def handle(self):
        """重写接收请求"""
        self.handle_one_request()


if __name__ == '__main__':
    with socketserver.TCPServer((host, port), Handler) as httpd:
        print(f"serving at {host}:{port}")
        httpd.serve_forever()
