#!/usr/bin/env python3
"""Test move() with different destinations and test gather."""

import socket, time, re

def connect():
    s = socket.socket()
    s.connect(('localhost', 7777))
    s.settimeout(3)
    time.sleep(0.5); s.recv(65536)
    s.sendall(b'connect wizard\r\n')
    time.sleep(0.8); s.recv(65536)
    return s


def send(s, cmd, wait=0.7):
    s.sendall((cmd + '\r\n').encode())
    time.sleep(wait)
    out = b''
    deadline = time.time() + max(wait + 0.3, 0.35)
    try:
        while time.time() < deadline:
            chunk = s.recv(65536)
            if not chunk: break
            out += chunk
    except: pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))


def ev(s, e, wait=0.7):
    return send(s, '; ' + e, wait)


def main():
    s = connect()
    print('=== Check wizard object type ===')
    out = ev(s, 'player:tell(tostr(parent(player)) + " " + parent(player).name)', wait=0.7)
    print(f'wizard parent: {out.strip()[-80:]}')

    out = ev(s, 'player:tell("is_a generic_player=" + tostr(is_a(player, $player)))', wait=0.7)
    print(f'is $player: {out.strip()[-60:]}')

    # Check if wizard has a 'contents' property
    out = ev(s, 'player:tell("contents" in properties(player) ? "has contents" | "no contents")', wait=0.7)
    print(f'has contents prop: {out.strip()[-60:]}')

    # Check wizard's accept verb
    out = ev(s, 'player:tell("accept" in verbs(player) ? "has accept" | "no accept")', wait=0.7)
    print(f'has accept verb: {out.strip()[-60:]}')

    # Try move to room instead of player
    print('\n=== Move to room test ===')
    out = ev(s, 'r = create($thing); r.name = "room test item"; move(r, player.location); player:tell("loc=" + tostr(r.location))', wait=1.0)
    print(f'move to room: {out.strip()[-80:]}')

    # Check room contents
    out = ev(s, 'for x in (player.location.contents); player:tell("  " + tostr(x) + " " + x.name); endfor', wait=1.0)
    print(f'room contents:\n{out.strip()[-300:]}')

    # Try get
    out = send(s, 'get room test item', wait=1.0)
    print(f'get: {out.strip()[-100:]}')
    out = ev(s, 'player:tell("inv cnt=" + tostr(length(player.contents)))', wait=0.7)
    print(f'inv after get: {out.strip()[-50:]}')

    # Check if $player_start player is different
    print('\n=== Check $player_start (#560) ===')
    out = ev(s, 'ps = $player_start; player:tell(tostr(ps) + " " + ps.name)', wait=0.7)
    print(f'player_start: {out.strip()[-60:]}')

    # Create a test regular player to try move
    print('\n=== Create test player to verify move works ===')
    out = ev(s, 'tp = create($player); tp.name = "Test"; tp.password = "test"; move(tp, #560); player:tell("tp=" + tostr(tp))', wait=1.0)
    print(f'test player: {out.strip()[-60:]}')

    # Parse test player number
    m = re.search(r'tp=#(\d+)', out)
    if m:
        tp_num = m.group(1)
        print(f'  Created test player #{tp_num}')
        # Try to move an item to the test player
        out = ev(s, f'r = create($thing); r.name = "fiber test"; move(r, #{tp_num}); player:tell("r.loc=" + tostr(r.location))', wait=1.0)
        print(f'  move to test player: {out.strip()[-80:]}')

    s.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
