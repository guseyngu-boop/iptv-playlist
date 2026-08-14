from pathlib import Path
from urllib.request import Request, urlopen
import re

PLAYLIST = Path('MEGA_IPTV_FINAL_2026.m3u')
AZ_SOURCE = 'https://raw.githubusercontent.com/iptv-org/iptv/master/streams/az.m3u'
TR_SOURCE = 'https://raw.githubusercontent.com/iptv-org/iptv/master/streams/tr.m3u'

TR_IDS = {
    '4UTV.tr@SD','360.tr@SD','A2TV.tr@SD','AHaber.tr@SD','ASpor.tr@SD',
    'AfroturkTV.tr@SD','AksuTV.tr@SD','AlanyaPostaTV.tr@SD','AltasTV.tr@SD',
    'AnadoluNetTV.tr@SD','ATV.tr@SD','ATVAlanya.tr@SD','BenguturkTV.tr@SD',
    'BeyazTV.tr@SD','BirTV.tr@SD','BloombergHT.tr@SD','ASTV.tr@SD','CayTV.tr@SD',
    'CekmekoyTV.tr@SD','CNBCe.tr@SD','DHA.tr@SD','DiyanetTV.tr@SD','DiyarTV.tr@SD',
    'DostTV.tr@SD','DreamTurk.tr@SD','EdessaTV.tr@SD','ESTV.tr@SD','ETVKayseri.tr@SD',
    'EuroD.tr@SD','FBTV.tr@SD','FinansTurkTV.tr@SD','FlashHaberTV.tr@SD','GZT.tr@SD',
    'Haber61TV.tr@SD','HaberGlobal.tr@SD','HaberturkTV.tr@SD','HalkTV.tr@SD',
    'HTSporTV.tr@SD','IlkeTV.tr@HD','Kanal3.tr@SD','Kanal7.tr@SD','Kanal7Avrupa.tr@SD',
    'Kanal12.tr@SD','Kanal23.tr@SD','KanalD.tr@SD','KocaeliTV.tr@SD','KonyaOlayTV.tr@SD',
    'KralPopTV.tr@SD','LalegulTV.tr@SD','MinikaCocuk.tr@SD','MinikaGo.tr@SD','NOWTV.tr@SD',
    'NTV.tr@SD','Number1Ask.tr@SD','Number1Damar.tr@SD','Number1Dance.tr@SD','Number1TV.tr@SD',
    'PowerDance.tr@SD','PowerLove.tr@SD','PowerTurkTV.tr@SD','PowerTurkAkustik.tr@SD',
    'PowerTurkSlow.tr@SD','PowerTurkTaptaze.tr@SD','PowerTV.tr@SD','QafTV.tr@SD',
    'Sat7Turk.cy@SD','SemerkandTV.tr@SD','StarTV.tr@SD','TBMMTV.tr@SD','Tele1.tr@SD',
    'TGRTBelgesel.tr@SD','TGRTHaber.tr@SD','Tivi6.tr@SD','TJKTV.tr@SD','TRT1.tr@SD',
    'TRT2.tr@SD','TRT3.tr@SD','TRTArabi.tr@SD','TRTAvaz.tr@SD','TRTBelgesel.tr@SD',
    'TRTCocuk.tr@SD','TRTDiyanetCocuk.tr@SD','TRTHaber.tr@SD','TRTKurdi.tr@SD','TRTMuzik.tr@SD',
    'TRTSporYildiz.tr@SD','TRTTurk.tr@SD','TRTWorld.tr@SD','TV1.tr@SD','TV4.tr@SD',
    'TV8.tr@SD','24TV.tr@SD','TVNET.tr@SD','VavTV.tr@SD','ZarokTV.tr@SD'
}

EROTIC = [
    ('FashionTVSecrets.fr@HD','FashionTV Secrets HD','https://ssai.aniview.com/api/v1/hls/stream.m3u8?AV_CONTENT_LANGUAGE=en&AV_CONTENT_GENRE=fashion%20and%20lifestyle&AV_CONTENT_RATING=R&AV_CLIENT_SECTION=ftv_secrets&content_channel_name=ftv%20-fashiontv%20Secrets&content_livestream=1&AV_CONTENT_PROVIDER=FTV'),
    ('FashionTVMidnightSecrets.fr','FashionTV Midnight Secrets','https://fash1043.cloudycdn.services/slive/ftv_ftv_midnite_k1y_27049_midnite_secr_108_hls.smil/playlist.m3u8'),
    ('FashionTVParisLOriginal.fr@SD',"FashionTV Paris L'Original HD",'https://edge-fast3.evrideo.tv/bfdbb576-83f7-11f0-9f89-0200170e3e04_1000028043_HLS/manifest.m3u8'),
    ('FashionTVEurope.fr@HD','FashionTV Europe HD','https://68f1accef2154d2195cae87dec183843.mediatailor.us-east-1.amazonaws.com/v1/master/44f73ba4d03e9607dcd9bebdcb8494d86964f1d8/RakutenTV-eu_FashionTV/playlist.m3u8'),
    ('MiamiTV.us','Miami TV','https://59ec5453559f0.streamlock.net/miamitv/smil:miamitv/playlist.m3u8'),
    ('MiamiTVLatino.us','Miami TV Latino','https://59ec5453559f0.streamlock.net/Latino/smil:WEB/chunklist.m3u8'),
]

OLD_EROTIC_GROUPS = {
    '18+ Light','Sensual / Fashion','Backup','Late Night / Lifestyle',
    'Lifestyle / Fashion','Sensual / Lifestyle','🔞 Эротика / Sensual'
}


def fetch(url):
    req = Request(url, headers={'User-Agent':'Mozilla/5.0'})
    with urlopen(req, timeout=40) as r:
        return r.read().decode('utf-8-sig', errors='replace')


def parse(text):
    lines = text.replace('\r\n','\n').split('\n')
    entries, i = [], 0
    while i < len(lines):
        if not lines[i].startswith('#EXTINF:'):
            i += 1
            continue
        block = [lines[i]]
        i += 1
        while i < len(lines) and not lines[i].startswith('#EXTINF:'):
            if lines[i].strip():
                block.append(lines[i])
            if lines[i].strip().startswith(('http://','https://','rtmp://','udp://')):
                i += 1
                break
            i += 1
        entries.append(block)
    return entries


def url_of(block):
    return next((x.strip() for x in block if x.strip().startswith(('http://','https://','rtmp://','udp://'))), None)


def meta(block):
    ext = block[0]
    tvg = re.search(r'tvg-id="([^"]*)"', ext)
    grp = re.search(r'group-title="([^"]*)"', ext)
    return (tvg.group(1) if tvg else '', grp.group(1) if grp else '')


def score(block):
    ext = block[0]
    url = url_of(block) or ''
    s = 0
    if url.startswith('https://'): s += 8
    if '[Not 24/7]' not in ext: s += 4
    if '[Geo-blocked]' not in ext: s += 2
    if '1080p' in ext or '1440p' in ext: s += 2
    if '720p' in ext: s += 1
    return s


def regroup(block, group):
    b = list(block)
    ext = re.sub(r'\s+group-title="[^"]*"', '', b[0])
    if ',' in ext:
        left, name = ext.split(',',1)
        b[0] = f'{left} group-title="{group}",{name}'
    else:
        b[0] = ext + f' group-title="{group}"'
    return b


original = PLAYLIST.read_text(encoding='utf-8-sig')
base_entries = []
for b in parse(original):
    tvg, grp = meta(b)
    if '.az@' in tvg or '.tr@' in tvg or grp in OLD_EROTIC_GROUPS:
        continue
    base_entries.append(b)

# Azerbaijan: all current public direct stream IDs, best stream per channel.
az_candidates = parse(fetch(AZ_SOURCE))
best_az = {}
for b in az_candidates:
    tvg, _ = meta(b)
    if not tvg:
        continue
    if tvg not in best_az or score(b) > score(best_az[tvg]):
        best_az[tvg] = b
az_entries = [regroup(best_az[k], '🇦🇿 Азербайджан') for k in sorted(best_az)]
# Space TV has an active public feed but is not currently in streams/az.m3u.
az_entries.append([
    '#EXTINF:-1 tvg-id="SpaceTV.az@SD" group-title="🇦🇿 Азербайджан",Space TV',
    'https://raw.githubusercontent.com/UzunMuhalefet/streams/main/myvideo-az/space-tv.m3u8'
])

# Turkey: curated selection of current public/free-to-air entries, best stream per channel.
tr_candidates = parse(fetch(TR_SOURCE))
best_tr = {}
for b in tr_candidates:
    tvg, _ = meta(b)
    if tvg not in TR_IDS:
        continue
    if tvg not in best_tr or score(b) > score(best_tr[tvg]):
        best_tr[tvg] = b
tr_entries = [regroup(best_tr[k], '🇹🇷 Турция') for k in sorted(best_tr)]

# Legal sensual / erotic, no pirated explicit XXX channels.
er_entries = [[f'#EXTINF:-1 tvg-id="{tvg}" group-title="🔞 Эротика / Sensual",{name}', url] for tvg,name,url in EROTIC]

seen = set()
final = []
for b in base_entries + az_entries + tr_entries + er_entries:
    u = url_of(b)
    if not u or u in seen:
        continue
    seen.add(u)
    final.append(b)

header = [
    '#EXTM3U',
    '# MEGA IPTV FINAL 2026',
    '# WORLD ULTRA + расширенные Азербайджан + Турция + Эротика / Sensual',
    '# Обновлено: 2026-08-14',
    '# Точные дубли потоков удалены по URL.',
    '# Некоторые каналы могут иметь Geo-ограничения или временно менять адрес.',
    ''
]
lines = header[:]
for b in final:
    lines.extend(b)
    lines.append('')
PLAYLIST.write_text('\n'.join(lines), encoding='utf-8-sig')
print(f'Updated {PLAYLIST}: total={len(final)}, AZ={len(az_entries)}, TR={len(tr_entries)}, erotic={len(er_entries)}')
