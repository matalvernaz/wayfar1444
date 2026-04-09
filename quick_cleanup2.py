#!/usr/bin/env python3
"""Clean stale sector center rooms by scanning object range."""
import socket, time, re

HOST = 'localhost'; PORT = 7777

def connect():
    s = socket.socket(); s.connect((HOST, PORT)); s.settimeout(2)
    time.sleep(0.5)
    try: s.recv(65536)
    except: pass
    s.sendall(b'connect wizard\r\n'); time.sleep(0.5)
    try: s.recv(65536)
    except: pass
    return s

def send(s, cmd, wait=0.5):
    s.sendall((cmd + '\r\n').encode()); time.sleep(wait)
    out = b''
    try:
        while True:
            chunk = s.recv(65536)
            if not chunk: break
            out += chunk
    except: pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))

def ev(s, e, wait=0.5): return send(s, '; ' + e, wait)
def program_verb(s, obj_expr, verbname, code_lines):
    out = send(s, f'@program {obj_expr}:{verbname}', wait=1.0)
    if 'programming' not in out.lower():
        print(f'  ERROR: {repr(out[:80])}'); return False
    old = s.gettimeout(); s.settimeout(0.3)
    for line in code_lines: send(s, line, wait=0.06)
    s.settimeout(old)
    r = send(s, '.', wait=3.0)
    if re.search(r'[1-9]\d* error', r): print(f'  CODE ERROR: {r[:200]}'); return False
    return True

s = connect()

# Add a cleanup verb to player
send(s, '@verb #6:"sc_cleanup" none none none', wait=0.5)
program_verb(s, '#6', 'sc_cleanup', [
    '"Cleanup all stale sector center rooms and portals.";',
    # Remove portals from room
    'for itm in (player.location.contents)',
    '  if (is_a(itm, $building) && "sc_plaza" in properties(itm))',
    '    player:tell("Portal: " + itm.name);',
    '    recycle(itm);',
    '  endif',
    'endfor',
    # Scan for stale Sector Center rooms
    'for i in [790..850]',
    '  obj = toobj(i);',
    '  if (valid(obj) && typeof(obj) == OBJ)',
    '    if (index(obj.name, "Sector Center") != 0)',
    '      player:tell("SC room: " + tostr(obj) + " " + obj.name);',
    '      recycle(obj);',
    '    endif',
    '  endif',
    'endfor',
    'player.w_colony = $nothing;',
    'player:tell("Cleanup complete. w_colony=" + tostr(player.w_colony));',
])

print(send(s, 'sc_cleanup', wait=5.0).strip())
print(send(s, '@dump-database', wait=3.0).strip()[:60])
s.close()
