# coding: utf-8
from __future__ import unicode_literals

import hashlib
import re

from .common import InfoExtractor
from ..compat import compat_parse_qs
from ..utils import (
    int_or_none,
    float_or_none,
    unified_timestamp,
)


class BiliBiliIE(InfoExtractor):
    _VALID_URL = r'https?://www\.bilibili\.(?:tv|com)/video/av(?P<id>\d+)'

    _TESTS = [{
        'url': 'http://www.bilibili.tv/video/av1074402/',
        'md5': '9fa226fe2b8a9a4d5a69b4c6a183417e',
        'info_dict': {
            'id': '1074402',
            'ext': 'mp4',
            'title': '【金坷垃】金泡沫',
            'description': 'md5:ce18c2a2d2193f0df2917d270f2e5923',
            'duration': 308.315,
            'timestamp': 1398012660,
            'upload_date': '20140420',
            'thumbnail': 're:^https?://.+\.jpg',
            'uploader': '菊子桑',
            'uploader_id': '156160',
        },
    }, {
        'url': 'http://www.bilibili.com/video/av1041170/',
        'info_dict': {
            'id': '1041170',
            'ext': 'mp4',
            'title': '【BD1080P】刀语【诸神&异域】',
            'description': '这是个神奇的故事~每个人不留弹幕不给走哦~切利哦！~',
            'duration': 3382.259,
            'timestamp': 1396530060,
            'upload_date': '20140403',
            'thumbnail': 're:^https?://.+\.jpg',
            'uploader': '枫叶逝去',
            'uploader_id': '520116',
        },
    }, {
        'url': 'http://www.bilibili.com/video/av4808130/',
        'info_dict': {
            'id': '4808130',
            'ext': 'mp4',
            'title': '【长篇】哆啦A梦443【钉铛】',
            'description': '(2016.05.27)来组合客人的脸吧&amp;amp;寻母六千里锭 抱歉，又轮到周日上班现在才到家 封面www.pixiv.net/member_illust.php?mode=medium&amp;amp;illust_id=56912929',
            'duration': 1493.995,
            'timestamp': 1464564180,
            'upload_date': '20160529',
            'thumbnail': 're:^https?://.+\.jpg',
            'uploader': '喜欢拉面',
            'uploader_id': '151066',
        },
    }, {
        # Missing upload time
        'url': 'http://www.bilibili.com/video/av1867637/',
        'info_dict': {
            'id': '1867637',
            'ext': 'mp4',
            'title': '【HDTV】【喜剧】岳父岳母真难当 （2014）【法国票房冠军】',
            'description': '一个信奉天主教的法国旧式传统资产阶级家庭中有四个女儿。三个女儿却分别找了阿拉伯、犹太、中国丈夫，老夫老妻唯独期盼剩下未嫁的小女儿能找一个信奉天主教的法国白人，结果没想到小女儿找了一位非裔黑人……【这次应该不会跳帧了】',
            'duration': 5760.0,
            'uploader': '黑夜为猫',
            'uploader_id': '610729',
            'thumbnail': 're:^https?://.+\.jpg',
        },
        'params': {
            # Just to test metadata extraction
            'skip_download': True,
        },
        'expected_warnings': ['upload time'],
    }]

    _APP_KEY = '6f90a59ac58a4123'
    _BILIBILI_KEY = '0bfd84cc3940035173f35e6777508326'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        cid = compat_parse_qs(self._search_regex(
            [r'EmbedPlayer\([^)]+,\s*"([^"]+)"\)',
             r'<iframe[^>]+src="https://secure\.bilibili\.com/secure,([^"]+)"'],
            webpage, 'player parameters'))['cid'][0]

        payload = 'appkey=%s&cid=%s&otype=json&quality=2&type=mp4' % (self._APP_KEY, cid)
        sign = hashlib.md5((payload + self._BILIBILI_KEY).encode('utf-8')).hexdigest()

        video_info = self._download_json(
            'http://interface.bilibili.com/playurl?%s&sign=%s' % (payload, sign),
            video_id, note='Downloading video info page')

        entries = []

        for idx, durl in enumerate(video_info['durl']):
            formats = [{
                'url': durl['url'],
                'filesize': int_or_none(durl['size']),
            }]
            for backup_url in durl['backup_url']:
                formats.append({
                    'url': backup_url,
                    # backup URLs have lower priorities
                    'preference': -2 if 'hd.mp4' in backup_url else -3,
                })

            self._sort_formats(formats)

            entries.append({
                'id': '%s_part%s' % (video_id, idx),
                'duration': float_or_none(durl.get('length'), 1000),
                'formats': formats,
            })

        title = self._html_search_regex('<h1[^>]+title="([^"]+)">', webpage, 'title')
        description = self._html_search_meta('description', webpage)
        timestamp = unified_timestamp(self._html_search_regex(
            r'<time[^>]+datetime="([^"]+)"', webpage, 'upload time', fatal=False))

        # TODO 'view_count' requires deobfuscating Javascript
        info = {
            'id': video_id,
            'title': title,
            'description': description,
            'timestamp': timestamp,
            'thumbnail': self._html_search_meta('thumbnailUrl', webpage),
            'duration': float_or_none(video_info.get('timelength'), scale=1000),
        }

        uploader_mobj = re.search(
            r'<a[^>]+href="https?://space\.bilibili\.com/(?P<id>\d+)"[^>]+title="(?P<name>[^"]+)"',
            webpage)
        if uploader_mobj:
            info.update({
                'uploader': uploader_mobj.group('name'),
                'uploader_id': uploader_mobj.group('id'),
            })

        for entry in entries:
            entry.update(info)

        if len(entries) == 1:
            return entries[0]
        else:
            for idx, entry in enumerate(entries):
                entry['id'] = '%s_part%d' % (video_id, (idx + 1))

            return {
                '_type': 'multi_video',
                'id': video_id,
                'title': title,
                'description': description,
                'entries': entries,
            }
