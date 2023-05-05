import re
import os
import yaml
from collections import defaultdict


yaml.Dumper.ignore_aliases = lambda *args: True

delay_url = 'http://www.gstatic.com/generate_204'
delay_interval = 180


class BaseModify:
    def __init__(self, data: str):
        print(data[:100] if len(data) > 100 else data)
        self.struct = yaml.safe_load(data)

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


class RouterModify(BaseModify):
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
