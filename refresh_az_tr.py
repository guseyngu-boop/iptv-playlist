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

SUPPLEMENTAL_AZ = [
    ('SpaceTV.az@SD', 'Space TV', 'https://raw.githubusercontent.com/UzunMuhalefet/streams/main/myvideo-az/space-tv.m3u8'),
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
    elif '1080p' in e: s += 3
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
        # Some CDNs reject Range while the stream itself is fine. Retry a tiny normal GET.
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
            best = alive[0]
            chosen.append(best)
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
