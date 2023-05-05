import re
import yaml
from collections import defaultdict
from typing import Optional
import requests
import http.server
import socketserver
from urllib.parse import unquote

PORT = 8000

delay_url = 'http://www.gstatic.com/generate_204'
delay_interval = 100


# 重写组
def handler(lis: list) -> list:
    groups = defaultdict(list)
    lis.sort(key=lambda i: i['name'])
    for i in lis:
        name = i['name']
        if re.search(r'(hongkong|kong kong|香港)', name.lower()):
            groups['香港负载组'].append(name)

        elif re.search(r'(taiwan|tai wan|台湾)', name.lower()):
            groups['台湾负载组'].append(name)

        elif re.search(r'(japan|jp|日本)', name.lower()):
            groups['日本负载组'].append(name)
        else:
            groups['其他'].append(name)

    proxy_groups = [
        {
            'name': '🚀 节点选择',
            'type': 'select',
            'proxies': ['香港负载组', '台湾负载组', '日本负载组', '其他']
         },
        {
            'name': '香港负载组',
            'type': 'load-balance',
            'url': delay_url,
            'interval': delay_interval,
            'proxies': groups['香港负载组']
        },
        {
            'name': '台湾负载组',
            'type': 'load-balance',
            'url': delay_url,
            'interval': delay_interval,
            'proxies': groups['台湾负载组']
        },
        {
            'name': '日本负载组',
            'type': 'load-balance',
            'url': delay_url,
            'interval': delay_interval,
            'proxies': groups['日本负载组']
        },
        {
            'name': '其他',
            'type': 'load-balance',
            'url': delay_url,
            'interval': delay_interval,
            'proxies': groups['其他']
        },
    ]
    return proxy_groups


class Handler(http.server.BaseHTTPRequestHandler):
    def _net(self):
        """添加剩余流量等信息"""
        path = unquote(self.path)
        print(f'parse: {self.path}')
        session = requests.Session()
        session.trust_env = False
        response = session.get(path)

        return response

    def parse_url(self) -> Optional[bytes]:
        if self.path and len(self.path) > 1:
            self.path = self.path[1:]
            return b''
        return b'parse url error'

    def get_clash(self, conf) -> Optional[bytes]:

        try:
            # conf = self._net().text
            print(conf[:100] if len(conf) > 100 else conf)

            conf = yaml.safe_load(conf)
            groups_agent = handler(conf['proxies'])
            groups_agent.extend(conf['proxy-groups'][1:])
            conf['proxy-groups'] = groups_agent

            res = yaml.safe_dump(conf, allow_unicode=True, sort_keys=False).encode()
            self.end_headers()
            return res
        except Exception as e:
            print(e)
            return str(e).encode()

    def end_headers(self):
        ...

    def do_GET(self):
        self.parse_url()
        headers = b'HTTP/1.1 200 OK\r\n'
        response = self._net()
        for k, v in response.headers.items():
            if k.lower() in ('content-encoding', 'content-length', 'transfer-encoding'):
                continue
            headers += f'{k}: {v}\r\n'.encode()
        response = self.get_clash(response.content)
        headers += f'Content-Length: {len(response)}\r\n'.encode()
        headers += b'\r\n'

        # print(headers.decode())
        self.wfile.write(headers + response)

    def handle(self):
        self.handle_one_request()


if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print("serving at port", PORT)
        httpd.serve_forever()
