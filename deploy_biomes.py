#!/usr/bin/env python3
"""
Deploy updated biome names/descriptions/colors to live server.
Updates: Kepler-7 planet properties, $wroom:look_self, status verb, $ods:populate
"""

import socket, time, re, sys
sys.path.insert(0, '/home/matt/wayfar')
from rebuild_world import (BIOME_NAMES_MOO, BIOME_DESCS_MOO, BIOME_CHARS_MOO,
                           LOOK_SELF_VERB, ODS_POPULATE)

HOST = 'localhost'
PORT = 7777
PLAYER = 6
KEPLER7 = 457
WROOM = 452
ODS = 458

def connect():
    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(5)
    time.sleep(0.5); s.recv(65536)
    s.sendall(b'connect wizard\r\n')
    time.sleep(0.8); s.recv(65536)
    return s

def send(s, cmd, wait=0.7):
    s.sendall((cmd + '\r\n').encode()); time.sleep(wait)
    out = b''; deadline = time.time() + max(wait + 0.3, 0.35)
    try:
        while time.time() < deadline:
            chunk = s.recv(65536)
            if not chunk: break
            out += chunk
    except: pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))

def ev(s, e, wait=0.7): return send(s, '; ' + e, wait)

def program_verb(s, obj_expr, verbname, code_lines):
    out = send(s, f'@program {obj_expr}:{verbname}', wait=1.5)
    if 'programming' not in out.lower():
        print(f'  ERROR @program {obj_expr}:{verbname}: {repr(out[:150])}', flush=True)
        return False
    old = s.gettimeout(); s.settimeout(0.5)
    for i, line in enumerate(code_lines):
        send(s, line, wait=0.08)
        if i % 20 == 19:
            print(f'    ... {i+1}/{len(code_lines)}', flush=True)
    s.settimeout(old)
    result = send(s, '.', wait=5.0)
    if re.search(r'[1-9]\d* error', result):
        print(f'  CODE ERROR {obj_expr}:{verbname}:\n{result[:600]}', flush=True)
        return False
    print(f'  OK: {obj_expr}:{verbname} ({len(code_lines)} lines)', flush=True)
    return True

s = connect()
print('Connected.', flush=True)

# 1. Update Kepler-7 planet properties
print('\n=== Update Kepler-7 biome properties ===', flush=True)
ev(s, f'#{KEPLER7}.biome_names = {BIOME_NAMES_MOO}', wait=1.0)
print(f'  biome_names = {BIOME_NAMES_MOO}', flush=True)
ev(s, f'#{KEPLER7}.biome_descs = {BIOME_DESCS_MOO}', wait=1.0)
print(f'  biome_descs updated', flush=True)
ev(s, f'#{KEPLER7}.biome_chars = {BIOME_CHARS_MOO}', wait=1.0)
print(f'  biome_chars updated', flush=True)

# 2. Update $wroom:look_self
print('\n=== Update $wroom:look_self ===', flush=True)
program_verb(s, f'#{WROOM}', 'look_self', LOOK_SELF_VERB)

# 3. Update status verb biome names — patch inline rather than overwriting
# The st/status verb may have been enhanced by later phases (economy, skills)
# Just update the hardcoded bnames list on all status-related verbs
print('\n=== Patch biome names in status verbs ===', flush=True)
# Check current st verb
out = send(s, '@list #6:st', wait=3.0)
if 'Mineral Flats' in out or 'Scrublands' in out:
    print('  st verb has old biome names — needs manual update', flush=True)
    print('  (Skipping to avoid overwriting enhanced status verb)', flush=True)
else:
    print('  st verb already has correct biome names or uses planet.biome_names', flush=True)

# 4. Update $ods:populate
print('\n=== Update $ods:populate ===', flush=True)
program_verb(s, f'#{ODS}', 'populate', ODS_POPULATE)

# 5. Rename existing spawned rooms (update room names for rooms that are already created)
print('\n=== Rename existing wilderness rooms ===', flush=True)
send(s, f'@verb #{PLAYER}:"_fix_rooms" none none none', wait=0.6)
program_verb(s, f'#{PLAYER}', '_fix_rooms', [
    'set_task_perms(#2);',
    'planet = #457;',
    'bnames = planet.biome_names;',
    'fixed = 0;',
    'for prop in (properties(#458))',
    '  if (index(prop, "rp"))',
    '    try',
    '      r = #458.(prop);',
    '      if (valid(r) && "biome" in properties(r))',
    '        b = r.biome;',
    '        if (b < 0) b = 0; elseif (b > 4) b = 4; endif',
    '        old_name = r.name;',
    '        new_name = bnames[b+1];',
    '        if (old_name != new_name)',
    '          r.name = new_name;',
    '          fixed = fixed + 1;',
    '        endif',
    '      endif',
    '    except e (ANY)',
    '    endtry',
    '  endif',
    'endfor',
    'player:tell("MARKER_FIXED=" + tostr(fixed));',
])
out = send(s, '_fix_rooms', wait=30.0)
for line in out.split('\n'):
    if 'MARKER_FIXED' in line:
        print(f'  {line.strip()}', flush=True)
        break

# Save
out = send(s, '@dump-database', wait=3.0)
print(f'\nSave: {out.strip()[:60]}', flush=True)

s.close()
print('\nBiome deploy done.', flush=True)
