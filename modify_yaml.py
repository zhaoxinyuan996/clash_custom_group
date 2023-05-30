import re
import os
from typing import List
import json
from urllib.parse import urlparse, unquote, parse_qs
import yaml
import base64
from copy import deepcopy
from collections import defaultdict


yaml.Dumper.ignore_aliases = lambda *args: True

delay_url = 'http://www.gstatic.com/generate_204'
delay_interval = 300


class BaseModify:
    def __init__(self, data: str):
        print(data[:100] if len(data) > 100 else data)
        print('>>>>>')
        self.struct = yaml.safe_load(data)

    @staticmethod
    def factory(url: str):
        if 'dt666' in url:
            return DengTaModify
        elif 'pptiok2020' in url:
            return CatModify
        return RouterModify

    @staticmethod
    def write_file(data: bytes):
        with open('tmp.txt', 'wb') as f:
            f.write(data)

    @staticmethod
    def _group(lis: list):
        """主要生成自定义组"""
        return []

    def build_group(self):
        """自定义组覆盖已有组"""
        self.struct['proxy-groups'].extend(self._group(self.struct['proxies']))

    @staticmethod
    def record(data: bytes):
        """每次都缓存一份到临时文件中，方便排查问题"""
        with open(os.path.join(os.path.dirname(__file__), 'tmp.txt'), 'wb') as f:
            f.write(data)

    def build(self) -> bytes:
        """生成yaml序列化字节"""
        self.build_group()
        data = yaml.safe_dump(self.struct, allow_unicode=True, sort_keys=False, encoding='utf-8')
        return data


class CatModify(BaseModify):
    def build_group(self):
        gs = []
        for g in self.struct['proxy-groups']:
            if '负载' in g['name']:
                g = deepcopy(g)
                g['name'] = re.sub(r'负载组', '测速', g['name'])
                g['type'] = 'url-test'
                gs.append(g)
        self.struct['proxy-groups'].extend(gs)
        self.struct['proxy-groups'][0]['proxies'].extend([i['name'] for i in gs])


class RouterModify(BaseModify):
    """负载组"""
    @staticmethod
    def _group(lis: list) -> list:
        groups = defaultdict(list)
        lis.sort(key=lambda j: j['name'])
        for i in lis:
            name = i['name']
            if re.search(r'(hongkong|hong kong|香港)', name.lower()):
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

    def build_group(self):
        groups_agent = self._group(self.struct['proxies'])
        agent_set = {i['name'] for i in groups_agent}
        for i in self.struct['proxy-groups']:
            if i['name'] in agent_set:
                continue
            groups_agent.append(i)
        self.struct['proxy-groups'] = groups_agent


class DengTaModify(BaseModify):
    shadow = '''port: 7890
socks-port: 7891
allow-lan: true
mode: Rule
log-level: info
external-controller: :9090
proxies:
%s
proxy-groups:
%s
'''
    def __init__(self, data: str):
        print(data[:100] if len(data) > 100 else data)
        print('>>>>>')
        s: List[str] = base64.b64decode(data).decode().split()
        self.proxies = []
        self.proxy_proxies = []
        self.proxy_groups = []
        for i in s:
            if i.startswith('trojan'):
                res = self.parse_trojan(i)
                i = ' - {%s}' % (','.join([f'{k}: {v}' for k, v in res.items()]), )
                name = res['name']
            elif i.startswith('vmess'):
                res = self.parse_vmess(i)
                i = ' - {%s}' % (','.join([f'{k}: {v}' for k, v in res.items()]),)
                name = res['name']
            else:
                continue
            if 'IEPL' not in i:
                continue
            self.proxy_proxies.append(name)
            self.proxies.append(i)
    @staticmethod
    def parse_vmess(s):
        s = s[8:]
        d = json.loads(base64.b64decode(s).decode())
        new_d = {
            "name": d["ps"],
            "type": "vmess",
            "server": d["add"],
            "port": d["port"],
            "uuid": d["id"],
            "alterId": 0,
            "cipher": "auto",
            "tls": True,

            # win
            # 'network': 'ws',
            # 'udp': True,
            # 'ws-opts': ' {path: %s, headers: { Host: %s }} ' % (d['path'], d['host']),
            # 'ws-path': d['path'],
            # 'ws-headers': '{ Host: %s }' % d['host']
            # 路由器
            'skip-cert-verify': False,
            'network': 'ws',
            'ws-opts': ' {path: %s, headers: { Host: %s }} ' % (d['path'], d['host']),
        }
        return new_d

    @staticmethod
    def parse_trojan(s):
        parsed_url = urlparse(s)
        _netloc = parsed_url.netloc.split("@")

        name = unquote(parsed_url.fragment)
        hostname = _netloc[1].split(":")[0]
        port = int(_netloc[1].split(":")[1])
        uid = _netloc[0]

        netquery = dict(
            (k, v if len(v) > 1 else v[0])
            for k, v in parse_qs(parsed_url.query).items()
        )
        res = {
            'name': name,
            'server': hostname,
            'port': port,
            'type': 'trojan',
            'password': uid,
            'sni': netquery.get('sni'),
            'skip-cert-verify': bool(netquery.get('allowInsecure'))

        }
        return res

    def build_group(self):
        self.proxy_groups.append(f''' - name: 节点选择
   type: select
   proxies: [自动测速, 负载均衡, 故障转移]''')
        self.proxy_groups.append(f''' - name: 自动测速
   type: url-test
   url: {delay_url}
   interval: {delay_interval}
   proxies: {self.proxy_proxies}''')
        self.proxy_groups.append(f''' - name: 负载均衡
   type: load-balance
   url: {delay_url}
   interval: {delay_interval}
   proxies: {self.proxy_proxies}''')
        self.proxy_groups.append(f''' - name: 故障转移
   type: fallback
   url: {delay_url}
   interval: {delay_interval}
   proxies: {self.proxy_proxies}''')
        self.struct = self.shadow % ('\n'.join(self.proxies), '\n'.join(self.proxy_groups))

    def build(self) -> bytes:
        """生成yaml序列化字节"""
        self.build_group()
        return self.struct.encode()
