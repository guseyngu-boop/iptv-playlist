from pathlib import Path
import re

PLAYLIST = Path('MEGA_IPTV_FINAL_2026.m3u')
GROUP = '🔞 NUDE 18+'

CHANNELS = [
    ('MiamiTV.us@SD', 'Miami TV Nude 18+', 'https://59ec5453559f0.streamlock.net/miamitv/smil:miamitvWEB/playlist.m3u8'),
    ('MiamiTVJennyLive.us@SD', 'Miami TV Jenny Live Nude 18+', 'https://59ec5453559f0.streamlock.net/JennyLive/JennyLive/playlist.m3u8'),
    ('MiamiTVMexico.us@SD', 'Miami TV Mexico Nude 18+', 'https://59ec5453559f0.streamlock.net/mexicotv/smil:miamitvmexicoROKU/playlist.m3u8'),
    ('MiamiTVLatino.us@HD', 'Miami TV Latino Nude 18+', 'https://5ee7c2b857b7f.streamlock.net/latino/latino/playlist.m3u8'),
    ('MiamiTVLatinoBackup.us@HD', 'Miami TV Latino Nude 18+ [Backup]', 'https://59ec5453559f0.streamlock.net/Latino/smil:WEB/chunklist.m3u8'),
]

text = PLAYLIST.read_text(encoding='utf-8-sig')
lines = text.replace('\r\n', '\n').split('\n')

out = []
i = 0
while i < len(lines):
    line = lines[i]
    if line.startswith('#EXTINF:') and ('group-title="🔞 Эротика"' in line or 'group-title="🔞 NUDE 18+"' in line):
        i += 1
        while i < len(lines) and not lines[i].startswith('#EXTINF:'):
            i += 1
        continue
    out.append(line)
    i += 1

while out and not out[-1].strip():
    out.pop()
out.append('')

for tvg, name, url in CHANNELS:
    out.append(f'#EXTINF:-1 tvg-id="{tvg}" group-title="{GROUP}",{name}')
    out.append(url)
    out.append('')

# Update descriptive header only, leaving #EXTM3U intact.
for idx, line in enumerate(out[:8]):
    if line.startswith('# WORLD ULTRA'):
        out[idx] = '# WORLD ULTRA + расширенные Азербайджан + Турция + NUDE 18+'

PLAYLIST.write_text('\n'.join(out), encoding='utf-8-sig')
print(f'Adult block refreshed: {len(CHANNELS)} channels in {GROUP}')
