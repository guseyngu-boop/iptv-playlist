from pathlib import Path
import re

PLAYLIST = Path('MEGA_IPTV_FINAL_2026.m3u')
GROUP = '🎬 Кино/сериалы RU • Бесплатные'

# Бесплатные публичные русскоязычные эфиры, где регулярно идут фильмы/сериалы.
# Это не подмена платных TV1000/Viasat/National Geographic.
CINEMA = [
    ('RussiaK.ru@HD', 'Россия-К / Культура HD', 'https://stream.smotrim.ru/hls2/russia_k/playlist_5.m3u8'),
    ('NTV.ru@HD', 'НТВ HD — сериалы и кино', 'https://cdn-dvr.ntv.ru/ntv0_hd/index.m3u8'),
    ('MoskvaDoveriye.ru@SD', 'Москва Доверие — советское кино', 'https://stream.smotrim.ru/hls2/doverie/playlist_3.m3u8'),
    ('Zvezda.ru@HD', 'Звезда HD — военное и историческое кино', 'https://tvchannelstream1.tvzvezda.ru/cdn/tvzvezda/playlist.m3u8'),
    ('TVCentr.ru@SD', 'ТВ Центр — кино и сериалы', 'https://tvc-hls.cdnvideo.ru/tvc-res/smil:vd9221.smil/playlist.m3u8'),
    ('Mir.ru@HD', 'МИР HD — кино и сериалы', 'http://hls.mirtv.cdnvideo.ru/mirtv-parampublish/mirtv_2500/playlist.m3u8'),
    ('RedLine.ru@SD', 'Красная линия — советское кино', 'http://s55766.cdn.ngenix.net/s55766-media-origin/rline_high/index.m3u8'),
    ('Solnce.ru@SD', 'Солнце — семейное кино', 'https://tv.mediacdn.ru/live/solntse/playlist.m3u8'),
]

text = PLAYLIST.read_text(encoding='utf-8-sig')
lines = text.replace('\r\n', '\n').split('\n')
out = []
i = 0
while i < len(lines):
    if lines[i].startswith('#EXTINF:') and f'group-title="{GROUP}"' in lines[i]:
        i += 1
        while i < len(lines) and not lines[i].startswith('#EXTINF:'):
            i += 1
        continue
    out.append(lines[i])
    i += 1

while out and not out[-1].strip():
    out.pop()
out.append('')
for tvg, name, url in CINEMA:
    out.append(f'#EXTINF:-1 tvg-id="{tvg}" group-title="{GROUP}",{name}')
    out.append(url)
    out.append('')

PLAYLIST.write_text('\n'.join(out), encoding='utf-8-sig')
print(f'Added {len(CINEMA)} Russian free cinema/series aliases')
