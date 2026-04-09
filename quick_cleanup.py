#!/usr/bin/env python3
"""Clean up stale sector center rooms/portals and return wizard to grassland."""
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

s = connect()

print('Current location:', ev(s, 'player:tell(player.location.name)').strip()[-60:])

# Return wizard to room #591 (Grassland)
print(send(s, '@go #591', wait=1.0).strip()[-60:])
print('Now at:', ev(s, 'player:tell(player.location.name)').strip()[-60:])

# Remove ALL sc portal buildings from current room
out = ev(s, '''
for itm in (player.location.contents)
  if (is_a(itm, $building) && "sc_plaza" in properties(itm))
    player:tell("Recycling portal: " + itm.name)
    recycle(itm)
  endif
endfor
player:tell("portal cleanup done")
''', wait=2.0)
print(out.strip()[-120:])

# Recycle any Sector Center rooms with parent $room (old ones)
# We'll check objects 790-830 range for sc_room children
out = ev(s, '''
cleaned = 0
for i in [795..840]
  obj = toobj(i)
  if (valid(obj) && typeof(obj) == OBJ)
    if (index(obj.name, "Sector Center") != 0)
      player:tell("Found: " + tostr(obj) + " " + obj.name + " parent=" + tostr(parent(obj)))
      cleaned = cleaned + 1
    endif
  endif
endfor
player:tell("found " + tostr(cleaned))
''', wait=3.0)
print(out.strip()[-300:])

# Reset w_colony
ev(s, 'player.w_colony = $nothing', wait=0.5)
print('w_colony reset:', ev(s, 'player:tell("w_colony=" + tostr(player.w_colony))').strip()[-40:])

out = send(s, '@dump-database', wait=3.0)
print('Save:', out.strip()[:40])
s.close()
