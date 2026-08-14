from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin
from urllib.error import HTTPError, URLError
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import re

PLAYLIST = Path('MEGA_IPTV_FINAL_2026.m3u')
REPORT = Path('AZ_TR_HEALTH_REPORT.md')
AZ_SOURCE = 'https://raw.githubusercontent.com/iptv-org/iptv/master/streams/az.m3u'
TR_SOURCE = 'https://raw.githubusercontent.com/iptv-org/iptv/master/streams/tr.m3u'
TIMEOUT = 8
WORKERS = 28
UA = 'Mozilla/5.0 (Linux; Android 11; TV) AppleWebKit/537.36 Chrome/124 Safari/537.36'

# Do not import obvious subscription/pay-TV restreams even if a public URL appears somewhere.
BLOCKED_TR_WORDS = (
    'national geographic', 'disney jr', 'moviesmart', 's sport', 'bein',
    'tivibu spor', 'smart spor', 'eurosport', 'exxen'
)

# Extra public/free-to-air alternatives. They are still health-checked before inclusion.
SUPPLEMENTAL_AZ = [
    ('ATV.az@SD', 'ATV Azərbaycan', 'https://stream.atv.az/WebRTCAppEE/streams/780339739845112514894920_adaptive.m3u8'),
    ('ARB.az@SD', 'ARB', 'https://raw.githubusercontent.com/UzunMuhalefet/streams/main/myvideo-az/arb.m3u8'),
    ('ARB24.az@SD', 'ARB 24', 'https://raw.githubusercontent.com/UzunMuhalefet/streams/main/myvideo-az/arb-24.m3u8'),
    ('ARBGunes.az@SD', 'ARB Günəş', 'https://raw.githubusercontent.com/UzunMuhalefet/streams/main/myvideo-az/arb-gunes.m3u8'),
    ('AzerbaijanNews.az@SD', 'Azerbaijan News', 'https://edge1.socialsmart.tv/aznews/smil/playlist.m3u8'),
    ('AzTV.az@SD', 'AzTV [Alt]', 'https://aztv.live/stream/index.m3u8'),
    ('BakuTV.az@SD', 'Baku TV [Alt]', 'https://rtmp.baku.tv/live/bakutv_720p.m3u8'),
    ('BakuTV.az@SD', 'Baku TV [GitHub Alt]', 'https://raw.githubusercontent.com/UzunMuhalefet/streams/main/myvideo-az/baku-tv.m3u8'),
    ('CBCTV.az@SD', 'CBC Azərbaycan', 'https://stream.cbctv.az:5443/LiveApp/streams/cbctv.m3u8'),
    ('DunyaTV.az@SD', 'Dünya TV', 'https://stream.ftv.az/live/dunyatv.m3u8'),
    ('DunyaTV.az@SD', 'Dünya TV [Alt]', 'https://raw.githubusercontent.com/UzunMuhalefet/streams/main/myvideo-az/dunya-tv.m3u8'),
    ('IctimaiTV.az@SD', 'İctimai TV [Alt]', 'http://109.205.166.68/server124/ictimai_tv/index.m3u8'),
    ('IdmanTV.az@SD', 'İdman Azərbaycan', 'https://idman.aztv.live/stream/index.m3u8'),
    ('KanalS.az@SD', 'Kanal S [Alt]', 'https://raw.githubusercontent.com/UzunMuhalefet/streams/main/myvideo-az/kanal-s.m3u8'),
    ('MedeniyyetTV.az@SD', 'Mədəniyyət TV [Alt]', 'https://str.yodacdn.net/medeniyyet/index.m3u8'),
    ('MTVAzerbaijan.az@SD', 'MTV Azərbaycan', 'https://raw.githubusercontent.com/UzunMuhalefet/streams/main/myvideo-az/mtv-azerbaycan.m3u8'),
    ('MuganTV.az@SD', 'Muğan TV', 'https://cdn10-mugantv.yayin.com.tr/mugantv/mugantv/playlist.m3u8'),
    ('NaxcivanTV.az@SD', 'Naxçıvan TV [Alt]', 'http://streams.livetv.az/azerbaijan/nax/playlist.m3u8'),
    ('QafqazTV.az@SD', 'Qafqaz TV', 'https://str1.yodacdn.net/qafkaz/playlist.m3u8'),
    ('QebeleTV.az@SD', 'Qəbələ TV', 'https://qebele.tv/live/stream/index.m3u8'),
    ('RealTV.az@SD', 'REAL TV', 'https://str.yodacdn.net/real/playlist.m3u8'),
    ('RihatTV.az@SD', 'Rihat TV Azərbaycan', 'http://cdn-rihattvazerbaijan.yayin.com.tr/rihattvazerbaijan/rihattvazerbaijan/playlist.m3u8'),
    ('SpaceTV.az@SD', 'Space TV', 'https://raw.githubusercontent.com/UzunMuhalefet/streams/main/myvideo-az/space-tv.m3u8'),
    ('SpaceTV.az@SD', 'Space TV [Alt]', 'http://109.205.166.68/server124/space_tv/index.m3u8'),
    ('TMBAzerbaijan.az@SD', 'TMB Azərbaycan', 'https://raw.githubusercontent.com/UzunMuhalefet/streams/main/myvideo-az/tmb-azerbaycan.m3u8'),
    ('UmidTV.az@SD', 'Ümid TV', 'https://cdn-umudtv.yayin.com.tr/umudtv/ngrp:umudtv/playlist.m3u8'),
    ('VIPTV.az@SD', 'VIP TV', 'https://raw.githubusercontent.com/UzunMuhalefet/streams/main/myvideo-az/vip.m3u8'),
    ('XezerTV.az@SD', 'Xəzər TV [Alt]', 'https://raw.githubusercontent.com/UzunMuhalefet/streams/main/myvideo-az/xezer-tv.m3u8'),
]

SUPPLEMENTAL_TR = [
    ('ShowTV.tr@HD', 'Show TV HD', 'https://ciner-live.daioncdn.net/showtv/showtv_1080p.m3u8'),
    ('CNNTurk.tr@HD', 'CNN Türk HD', 'https://live.duhnet.tv/S2/HLS_LIVE/cnn_turknp/playlist.m3u8'),
    ('Teve2.tr@HD', 'teve2 HD', 'https://demiroren-live.daioncdn.net/teve2/teve2.m3u8'),
    ('Teve2.tr@HD', 'teve2 HD [Alt]', 'https://live.duhnet.tv/S2/HLS_LIVE/teve2np/playlist.m3u8'),
    ('ASpor.tr@HD', 'A Spor HD [Alt]', 'https://trkvz-live.daioncdn.net/aspor/aspor.m3u8'),
    ('BeyazTV.tr@HD', 'Beyaz TV HD [Alt]', 'https://beyaztv-live.daioncdn.net/beyaztv/beyaztv.m3u8'),
    ('Kanal7.tr@HD', 'Kanal 7 HD [Alt]', 'https://live.kanal7.com/live/kanal7LiveDesktop/index.m3u8'),
    ('Kanal7.tr@HD', 'Kanal 7 FHD [Alt 2]', 'https://kanal7-live.daioncdn.net/kanal7/kanal7_1080p.m3u8'),
    ('NOWTV.tr@HD', 'NOW TV [HTTP Alt]', 'http://uycyyuuzyh.turknet.ercdn.net/nphindgytw/nowtv/nowtv.m3u8'),
    ('TRTSpor.tr@HD', 'TRT Spor', 'https://tv-trtspor.live.trt.com.tr/master.m3u8'),
    ('TRTBelgesel.tr@HD', 'TRT Belgesel [Alt]', 'https://tv-trtbelgesel.live.trt.com.tr/master.m3u8'),
    ('UlkeTV.tr@HD', 'Ülke TV [Alt]', 'https://mn-nl.mncdn.com/blutv_ulketv2/live.m3u8'),
    ('Number1Turk.tr@HD', 'Number 1 Türk', 'https://mn-nl.mncdn.com/blutv_nr1turk2/live.m3u8'),
    ('SportsTV.tr@HD', 'Sports TV', 'https://live.sportstv.com.tr/hls/low/sportstv_fhd/index.m3u8'),
    ('TarimTV.tr@HD', 'Tarım TV HD', 'https://content.tvkur.com/l/c7e1da7mm25p552d9u9g/index-720p.m3u8'),
    ('TGRTEU.tr@SD', 'TGRT EU', 'https://tv.ensonhaber.com/tv/tr/tgrteu/index.m3u8'),
    ('TGRTBelgesel.tr@SD', 'TGRT Belgesel [Alt]', 'https://tv.ensonhaber.com/tv/tr/tgrtbelgesel/index.m3u8'),
]


def get_text(url):
    req = Request(url, headers={'User-Agent': UA, 'Accept': '*/*'})
    with urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8-sig', errors='replace')


def parse(text):
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    out, i = [], 0
    while i < len(lines):
        if not lines[i].startswith('#EXTINF:'):
            i += 1
            continue
        block = [lines[i]]
        i += 1
        while i < len(lines) and not lines[i].startswith('#EXTINF:'):
            if lines[i].strip():
                block.append(lines[i].strip())
            if lines[i].strip().startswith(('http://', 'https://')):
                i += 1
                break
            i += 1
        out.append(block)
    return out


def url_of(block):
    return next((x for x in block if x.startswith(('http://', 'https://'))), None)


def extinf(block):
    return block[0]


def tvg_id(block):
    m = re.search(r'tvg-id="([^"]*)"', extinf(block))
    return m.group(1) if m else ''


def name_of(block):
    return extinf(block).split(',', 1)[1].strip() if ',' in extinf(block) else tvg_id(block)


def group_of(block):
    m = re.search(r'group-title="([^"]*)"', extinf(block))
    return m.group(1) if m else ''


def key_of(block):
    return tvg_id(block) or re.sub(r'\W+', '', name_of(block).lower())


def score(block):
    e = extinf(block).lower()
    u = (url_of(block) or '').lower()
    s = 0
    if u.startswith('https://'): s += 8
    if '[geo-blocked]' not in e: s += 6
    if '[not 24/7]' not in e: s += 4
    if '2160p' in e: s += 5
    elif '1440p' in e: s += 4
    elif '1080p' in e or '@hd' in e: s += 3
    elif '720p' in e: s += 2
    elif '576p' in e: s += 1
    return s


def headers_for(block, range_header=None):
    h = {'User-Agent': UA, 'Accept': '*/*'}
    for x in block:
        if x.lower().startswith('#extvlcopt:http-user-agent='):
            h['User-Agent'] = x.split('=', 1)[1].strip()
        elif x.lower().startswith('#extvlcopt:http-referrer='):
            h['Referer'] = x.split('=', 1)[1].strip()
    if range_header:
        h['Range'] = range_header
    return h


def fetch_probe(url, block, range_header=None, limit=131072):
    req = Request(url, headers=headers_for(block, range_header))
    with urlopen(req, timeout=TIMEOUT) as r:
        data = r.read(limit)
        status = getattr(r, 'status', 200)
        ctype = (r.headers.get('Content-Type') or '').lower()
        return status, data, ctype, r.geturl()


def first_uri(text):
    for line in text.replace('\r', '').split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            return line
    return None


def probe_manifest(url, block, depth=0):
    status, data, ctype, final_url = fetch_probe(url, block)
    if status < 200 or status >= 400 or not data:
        return False, f'HTTP {status}'
    low = data[:2048].lower()
    is_m3u = b'#extm3u' in low or 'mpegurl' in ctype or '.m3u8' in final_url.lower()
    if not is_m3u:
        return True, f'HTTP {status} {ctype or "data"}'
    text = data.decode('utf-8', errors='replace')
    if '#EXTM3U' not in text.upper():
        return False, 'not a valid HLS manifest'
    uri = first_uri(text)
    if not uri:
        return False, 'empty HLS manifest'
    child = urljoin(final_url, uri)
    if depth < 2 and ('#EXT-X-STREAM-INF' in text.upper() or '.m3u8' in uri.lower()):
        return probe_manifest(child, block, depth + 1)
    try:
        st, seg, ct, _ = fetch_probe(child, block, 'bytes=0-2047', 4096)
        if 200 <= st < 400 and seg:
            return True, f'HLS media OK ({st})'
        return False, f'media HTTP {st}'
    except HTTPError as e:
        if e.code in (400, 403, 416):
            try:
                st, seg, ct, _ = fetch_probe(child, block, None, 4096)
                return (200 <= st < 400 and bool(seg), f'HLS media OK ({st})' if 200 <= st < 400 and seg else f'media HTTP {st}')
            except Exception as e2:
                return False, f'media {type(e2).__name__}'
        return False, f'media HTTP {e.code}'


def check(block):
    u = url_of(block)
    if not u:
        return False, 'no URL'
    try:
        return probe_manifest(u, block)
    except HTTPError as e:
        return False, f'HTTP {e.code}'
    except URLError as e:
        return False, f'URL error: {getattr(e, "reason", "")}'
    except TimeoutError:
        return False, 'timeout'
    except Exception as e:
        return False, type(e).__name__


def regroup(block, group):
    b = list(block)
    e = re.sub(r'\s+group-title="[^"]*"', '', b[0])
    left, name = e.split(',', 1) if ',' in e else (e, name_of(block))
    b[0] = f'{left} group-title="{group}",{name}'
    return b


def allowed_tr(block):
    hay = (tvg_id(block) + ' ' + name_of(block)).lower()
    return not any(word in hay for word in BLOCKED_TR_WORDS)


def choose_working(blocks, country):
    by_key = {}
    for b in blocks:
        if country == 'TR' and not allowed_tr(b):
            continue
        by_key.setdefault(key_of(b), []).append(b)
    all_candidates = [b for vals in by_key.values() for b in vals]
    results = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(check, b): b for b in all_candidates}
        for fut in as_completed(futs):
            b = futs[fut]
            try:
                results[id(b)] = fut.result()
            except Exception as e:
                results[id(b)] = (False, type(e).__name__)
    chosen, failed = [], []
    for key, vals in by_key.items():
        vals = sorted(vals, key=score, reverse=True)
        alive = [b for b in vals if results.get(id(b), (False, ''))[0]]
        if alive:
            chosen.append(alive[0])
        else:
            failed.append((name_of(vals[0]), '; '.join(sorted({results.get(id(b), (False, 'unknown'))[1] for b in vals}))))
    chosen.sort(key=lambda b: name_of(b).lower())
    return chosen, failed, len(all_candidates)


original = PLAYLIST.read_text(encoding='utf-8-sig')
base = []
for b in parse(original):
    t = tvg_id(b)
    g = group_of(b)
    if '.az@' in t.lower() or '.tr@' in t.lower() or g in {'🇦🇿 Азербайджан', '🇹🇷 Турция'}:
        continue
    base.append(b)

az_source = parse(get_text(AZ_SOURCE))
for tvg, name, url in SUPPLEMENTAL_AZ:
    az_source.append([f'#EXTINF:-1 tvg-id="{tvg}",{name}', url])
tr_source = parse(get_text(TR_SOURCE))
for tvg, name, url in SUPPLEMENTAL_TR:
    tr_source.append([f'#EXTINF:-1 tvg-id="{tvg}",{name}', url])

az_ok, az_failed, az_tested = choose_working(az_source, 'AZ')
tr_ok, tr_failed, tr_tested = choose_working(tr_source, 'TR')
az_entries = [regroup(b, '🇦🇿 Азербайджан') for b in az_ok]
tr_entries = [regroup(b, '🇹🇷 Турция') for b in tr_ok]

seen = set()
final = []
for b in base + az_entries + tr_entries:
    u = url_of(b)
    if not u or u in seen:
        continue
    seen.add(u)
    final.append(b)

header = [
    '#EXTM3U',
    '# MEGA IPTV FINAL 2026',
    '# WORLD ULTRA + проверенные Азербайджан + Турция + дополнительные группы',
    '# Обновлено: ' + datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
    '# AZ/TR потоки проверяются автоматически перед добавлением.',
    '# Geo-блокировка и ограничения провайдера всё равно могут отличаться на вашем IP.',
    ''
]
lines = header[:]
for b in final:
    lines.extend(b)
    lines.append('')
PLAYLIST.write_text('\n'.join(lines), encoding='utf-8-sig')

report = [
    '# Azerbaijan & Turkey IPTV health report',
    '',
    f'Checked: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}',
    '',
    f'- Azerbaijan candidates tested: **{az_tested}**',
    f'- Azerbaijan working channels selected: **{len(az_entries)}**',
    f'- Turkey candidates tested: **{tr_tested}**',
    f'- Turkey working channels selected: **{len(tr_entries)}**',
    '',
    '## Azerbaijan channels selected',
] + [f'- {name_of(b)}' for b in az_ok] + [
    '', '## Turkey channels selected',
] + [f'- {name_of(b)}' for b in tr_ok] + [
    '', '## Failed Azerbaijan channels at check time',
] + ([f'- {n}: {r}' for n, r in az_failed] or ['- None']) + [
    '', '## Failed Turkey channels at check time',
] + ([f'- {n}: {r}' for n, r in tr_failed] or ['- None']) + [
    '', '> A stream can pass this server-side check and still be geo-blocked or ISP-blocked for a specific viewer. Conversely, a geo-limited stream can fail from the GitHub runner but work locally.',
]
REPORT.write_text('\n'.join(report) + '\n', encoding='utf-8')
print(f'AZ: {len(az_entries)} working from {az_tested} candidates; TR: {len(tr_entries)} working from {tr_tested} candidates')
