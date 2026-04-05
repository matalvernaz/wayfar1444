#!/usr/bin/env python3
"""Quick test script for resource nodes and Phase 3 features."""

import socket, time, re

s = socket.socket()
s.connect(('localhost', 7777))
s.settimeout(0.5)
time.sleep(0.5)
try: s.recv(65536)
except: pass
s.sendall(b'connect wizard\r\n')
time.sleep(0.5)
try: s.recv(65536)
except: pass


def send(cmd, wait=0.4):
    s.sendall((cmd + '\r\n').encode())
    time.sleep(wait)
    out = b''
    try:
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            out += chunk
    except Exception:
        pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))


def ev(expr, wait=0.4):
    return send(f'; {expr}', wait)


# --- 1. Scan for a coord that gets a node (roll >= 7) ---
print('=== Scanning coords for node-spawning rolls ===')
good_coords = []
for x in range(1, 8):
    for y in range(1, 8):
        out = ev(f'player:tell(tostr(perlin_2d({x*7+13}, {y*5+7}, 2.0, 2.0, 10, 1)))')
        m = re.search(r'>> (\d+)', out)
        if m:
            roll = int(m.group(1))
            if roll >= 7:
                good_coords.append((x, y, roll))
                print(f'  ({x},{y}) roll={roll}')

if not good_coords:
    print('  No node-spawning coords found in scan range — lowering threshold')
    good_coords = [(1, 1, 0)]  # fallback

x, y, roll = good_coords[0]
print(f'\n=== Testing at ({x},{y}) roll={roll} ===')

# Spawn the room
out = ev(f'r = $ods:spawn_room(#457, {x}, {y}); player:tell(tostr(r))', wait=0.6)
m = re.search(r'#(\d+)', out)
if not m:
    print('Could not spawn room:', repr(out[:200]))
    exit(1)
rnum = int(m.group(1))
print(f'Room: #{rnum}')

# Check room contents
out2 = ev(f'player:tell(tostr(#{rnum}.contents))')
print(f'Contents: {out2[:200]}')

# Move there
send(f'@go #{rnum}', wait=0.6)
out3 = send('look', wait=0.6)
print('\n--- look ---')
print(out3[:600])

# --- 2. Test gather if a node is present ---
out4 = ev(f'player:tell(tostr(#{rnum}.contents))')
m2 = re.search(r'#(\d+)', out4)
if m2:
    node_num = int(m2.group(1))
    out5 = ev(f'player:tell(#{node_num}.name)')
    print(f'\nNode found: #{node_num} =>', out5[:100])
    # Try gather
    out6 = send('gather', wait=0.6)
    print('gather (no args):', out6[:200])
    out7 = send(f'mine #{node_num}', wait=0.6)
    print('mine #node:', out7[:200])
    # Check inventory
    out8 = send('i', wait=0.5)
    print('\nInventory:', out8[:300])
else:
    print('No node in room (it was a <= roll or already visited)')

# --- 3. Test vitals ---
print('\n=== Testing vitals ===')
out9 = send('vitals', wait=0.5)
print(out9[:300])

# --- 4. Test status ---
print('=== Testing status ===')
out10 = send('status', wait=0.5)
print(out10[:300])

print('\nDone.')
