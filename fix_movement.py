#!/usr/bin/env python3
"""Re-program just the movement verbs with the parent() check fix."""

import socket, time, re

HOST, PORT = 'localhost', 7777
PLAYER_CLASS = 6

def connect():
    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(3)
    time.sleep(0.5); s.recv(65536)
    s.sendall(b'connect wizard\r\n')
    time.sleep(0.7); s.recv(65536)
    return s

def send(s, cmd, wait=0.65):
    s.sendall((cmd + '\r\n').encode())
    time.sleep(wait)
    out = b''
    try:
        while True:
            chunk = s.recv(65536)
            if not chunk: break
            out += chunk
    except: pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))

def add_verb(s, obj, name, args='none none none'):
    return send(s, f'@verb #{obj}:{name} {args}', wait=0.5)

def program_verb(s, obj, name, lines):
    out = send(s, f'@program #{obj}:{name}', wait=0.7)
    if 'programming' not in out.lower():
        print(f'  WARN @program #{obj}:{name}: {repr(out[:80])}')
    s.settimeout(0.25)
    for line in lines:
        send(s, line, wait=0.04)
    s.settimeout(3)
    out = send(s, '.', wait=2.0)
    if re.search(r'[1-9]\d* error', out):
        print(f'  ERROR #{obj}:{name}: {repr(out[:300])}')
    return out

def make_move_verb(direction, dx, dy, from_dir):
    return [
        f'"Move {direction} by adjusting coordinates.";',
        'if (parent(player.location) != $wroom)',
        '  player:tell("You cannot go that way.");',
        '  return;',
        'endif',
        f'nx = player.location.x + ({dx});',
        f'ny = player.location.y + ({dy});',
        'planet = player.location.planet;',
        'dest = $ods:spawn_room(planet, nx, ny);',
        'if (!valid(dest))',
        '  player:tell("The way is blocked.");',
        '  return;',
        'endif',
        f'player.location:announce(player.name + " heads {direction}.", player);',
        'move(player, dest);',
        f'player.location:announce(player.name + " arrives from the {from_dir}.", player);',
    ]

if __name__ == '__main__':
    s = connect()
    dirs = [
        ('north', 0,  1, 'south'),
        ('south', 0, -1, 'north'),
        ('east',  1,  0, 'west'),
        ('west', -1,  0, 'east'),
    ]
    for direction, dx, dy, from_dir in dirs:
        program_verb(s, PLAYER_CLASS, direction, make_move_verb(direction, dx, dy, from_dir))
        abbrev = direction[0]
        program_verb(s, PLAYER_CLASS, abbrev, [f'this:{direction}();'])
        print(f'  Fixed: {direction} / {abbrev}')

    print('Saving...')
    send(s, '@dump-database', wait=2.0)
    s.sendall(b'QUIT\r\n')
    s.close()
    print('Done.')
