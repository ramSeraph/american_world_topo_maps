
import json
import re
from pathlib import Path

def get_parallels(txt):
    idx = txt.lower().find('parallels')
    if idx == -1:
        idx = txt.lower().find('paralles')

    if idx == -1:
        return None
    rest = txt[idx:]

    # Parallels } 1^{\text{o}}20' \text{ and } 6^{\text{o}}40'
    match = re.match(r'parallel?s[^\d]*(?P<d1>[0-9]+)[^\d]*(?P<m1>[0-9]+)[^\d]*(?P<d2>[0-9]+)[^\d]*(?P<m2>[0-9]+)', rest, re.IGNORECASE)
    if match is None:
        raise ValueError(f'Could not parse parallels as latex exp from {rest}')
    d1 = match.group('d1')
    m1 = match.group('m1')
    d2 = match.group('d2')
    m2 = match.group('m2')

    #print(f'Parsed parallels: {d1}°{m1}′ and {d2}°{m2}′')
    try:
        d1 = int(d1)
        m1 = int(m1)
        d2 = int(d2)
        m2 = int(m2)
    except ValueError:
        raise ValueError(f'Could not convert parallels to integers: {d1}°{m1}′ and {d2}°{m2}′')

    if d1 < 0 or d2 < 0 or m1 < 0 or m2 < 0:
        raise ValueError(f'Parallels cannot be negative: {d1}°{m1}′ and {d2}°{m2}′')
    if d1 > 90 or d2 > 90 or m1 >= 60 or m2 >= 60:
        raise ValueError(f'Parallels cannot be greater than 90° or minutes greater than 59: {d1}°{m1}′ and {d2}°{m2}′')

    return [
        d1 + m1 / 60,
        d2 + m2 / 60
    ]

def get_convergence(txt):
    idx = txt.lower().find('convergence')
    if idx == -1:
        idx = txt.lower().find('convergency')
    if idx == -1:
        idx = txt.lower().find('vergence')
    if idx == -1:
        idx = txt.lower().find('conv\u00e9rgence')

    if idx == -1:
        return None

    rest = txt[idx:]
    match = re.match(r'(con)?v.rgenc[ey][^\d]*(?P<c>[\.\-0-9]+)', rest, re.IGNORECASE)
    if match is None:
        raise ValueError(f'Could not parse convergence as latex exp from {rest}')
    c = match.group('c')
    if c.startswith('.'):
        c = c[1:]
    elif c.startswith('0.'):
        c = c[2:]
    elif c.startswith('0-'):
        c = c[2:]

    if len(c) != 5:
        raise ValueError(f'Convergence should be 5 digits, got {c}, {rest}')
    try:
        c = float('0.' + c)
    except ValueError:
        raise ValueError(f'Could not convert convergence to float: {c}')

    return c


proj_map = {}
for p in Path('data/text').glob('*.json'):
    print(f'Processing {p}')
    sheet_no = p.stem
    items = json.loads(p.read_text())
    parallels = None
    convergence = None
    for item in items:
        txt = item['text']
        if parallels is None:
            parallels = get_parallels(txt)
        if convergence is None:
            convergence = get_convergence(txt)

    #if parallels is None and convergence is None:
    #    print('No parallels or convergence found, going with polar stereographic')
    #    proj = '+proj=stere +lat_0=90 +lat_ts=81.05 +lon_0=180 +x_0=2000000 +y_0=2000000 +datum=WGS84 +units=m'
    #    proj_map[sheet_no] = proj
    #    continue


    proj_map[sheet_no] = { 'parallels': parallels, 'convergence': convergence }
    if parallels is None:
        print(txt)
    if convergence is None:
        print(txt)
    #print(f'Parallels: {parallels}')
    #print(f'Convergence: {convergence}')

with open('data/proj_map.json', 'w') as f:
    json.dump(proj_map, f, indent=4)


