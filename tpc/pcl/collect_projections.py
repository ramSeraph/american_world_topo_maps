
import json
import re
from pathlib import Path

def get_parallels(txt):
    idx = txt.lower().find('parallels')
    if idx == -1:
        idx = txt.lower().find('paralles')
    if idx == -1:
        idx = txt.lower().find('parellels')
    if idx == -1:
        idx = txt.lower().find('parelles')
    if idx == -1:
        idx = txt.lower().find('parallells')

    if idx == -1:
        return None
    rest = txt[idx:]

    # Parallels } 1^{\text{o}}20' \text{ and } 6^{\text{o}}40'
    match = re.match(r'par[ea]lle[l]*s[^\d]*(?P<d1>[0-9]+)[^\d]*(?P<m1>[0-9]+)[^\d]*(?P<d2>[0-9]+)[^\d]*(?P<m2>[0-9]+)', rest, re.IGNORECASE)
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
    match = re.match(r'(con)?v.rgenc[ey][^\d]*(?P<c>[\.\-,0-9]+)', rest, re.IGNORECASE)
    if match is None:
        print(txt)
        raise ValueError(f'Could not parse convergence as latex exp from {rest}')
    c = match.group('c')
    if c.startswith('.'):
        c = c[1:]
    elif c.startswith('0.'):
        c = c[2:]
    elif c.startswith('0-'):
        c = c[2:]
    c = c.replace(',', '')

    if len(c) != 5:
        raise ValueError(f'Convergence should be 5 digits, got {c}, {rest}')
    try:
        c = float('0.' + c)
    except ValueError:
        raise ValueError(f'Could not convert convergence to float: {c}')

    return c


proj_map = {}
count = 0
for p in Path('data/text').glob('*.json'):
    count += 1
    print(f'{count} Processing {p}')
    sheet_no = p.stem
    items = json.loads(p.read_text())
    parallels = None
    convergence = None
                
    if sheet_no == 'E04-B':
        convergence = 0.78830
    if sheet_no == 'B04-D':
        parallels = [ 73.3333333333, 78.6666666667 ]
        convergence = 0.97065
    if sheet_no == 'J19-C':
        convergence = 0.3746410
    if sheet_no == 'G03-B':
        convergence = 0.58800
    if sheet_no == 'N05-A':
        convergence = 0.20799
    if sheet_no == 'B03-C':
        convergence = 0.97065
        parallels = [ 73.3333333333, 78.6666666667 ]
    if sheet_no == 'C03-B':
        parallels = [ 65.3333333333, 70.6666666667 ]
        convergence = 0.92752
    if sheet_no == 'C05-D':
        parallels = [ 65.3333333333, 70.6666666667 ]
        convergence = 0.92752
    if sheet_no == 'C01-D':
        convergence = 0.92752
    if sheet_no == 'D07-C':
        convergence = 0.86634
        parallels = [ 57.3333333333, 62.6666666667 ]
    if sheet_no == 'F02-C':
        convergence = 0.69491
        parallels = [ 41.3333333333, 46.6666666667 ]
    if sheet_no == 'B08-B':
        convergence = 0.97065
        parallels = [ 73.3333333333, 78.6666666667 ]
    if sheet_no == 'H25-A':
        convergence = 0.46965
        parallels = [ 25.3333333333, 30.6666666667 ]
    if sheet_no == 'E01-A':
        convergence = 0.78830
        parallels = [ 49.3333333333, 54.6666666667 ]
    if sheet_no == 'L10-D':
        # copied from L10-C
        convergence = 0.06979
        parallels = [ 1.3333333333, 6.6666666667 ]
    if sheet_no == 'C06-D':
        parallels = [ 65.3333333333, 70.6666666667 ]
    if sheet_no == 'M12-D':
        parallels = [ 1.3333333333, 6.6666666667 ]

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

    def truncate_to_7(lst):
        if lst is None:
            return None
        return [ round(x, 7) for x in lst ]

    proj_map[sheet_no] = { 'parallels': truncate_to_7(parallels), 'convergence': convergence }
    if parallels is None:
        print('parallels fail', txt)
    if convergence is None:
        print('convergence fail', txt)
    #print(f'Parallels: {parallels}')
    #print(f'Convergence: {convergence}')

with open('data/proj_map.json', 'w') as f:
    json.dump(proj_map, f, indent=4)


