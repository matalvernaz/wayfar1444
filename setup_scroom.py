#!/usr/bin/env python3
"""Create $sc_room prototype with custom look_self (no area() call)."""
import socket, time, re

HOST = 'localhost'; PORT = 7777

def connect():
    s = socket.socket(); s.connect((HOST, PORT)); s.settimeout(3)
    time.sleep(0.5); s.recv(65536)
    s.sendall(b'connect wizard\r\n'); time.sleep(0.8); s.recv(65536)
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

def program_verb(s, obj_num, verbname, code_lines):
    out = send(s, f'@program #{obj_num}:{verbname}', wait=1.0)
    if 'programming' not in out.lower():
        print(f'  ERROR: {repr(out[:150])}'); return False
    old_to = s.gettimeout(); s.settimeout(0.3)
    for i, line in enumerate(code_lines):
        send(s, line, wait=0.06)
        if i % 15 == 14: print(f'    ... {i+1}/{len(code_lines)}')
    s.settimeout(old_to)
    result = send(s, '.', wait=3.0)
    if re.search(r'[1-9]\d* error', result):
        print(f'  CODE ERROR:\n{result[:600]}'); return False
    print(f'  OK: #{obj_num}:{verbname}'); return True


def extract_obj_num(out):
    """Extract object number from output, skipping Heart of God noise lines."""
    skip = ['Heart Of God', 'Division by zero', 'pct = floatstr', '.._beat',
            'skip_beat', 'Invalid indirection', 'RPG Utilities', 'meat_reaper',
            'Wizard (#361)', 'generic player', 'generic room']
    for line in out.strip().split('\n'):
        line = line.strip()
        if any(k in line for k in skip): continue
        m = re.search(r'#(\d+)', line)
        if m:
            return int(m.group(1))
    return None


def create_and_get_num(s, parent_obj='$room', wait=2.0):
    """Create a child object and return its number, filtering noise."""
    # Send two separate evals: create, then tell the number
    out = ev(s, f'wf_new_obj = create({parent_obj})', wait=wait)
    out2 = ev(s, 'player:tell("OBJNUM=" + tostr(wf_new_obj))', wait=1.0)
    # Look in out2 for our tagged output
    m = re.search(r'OBJNUM=#(\d+)', out2)
    if m:
        return int(m.group(1))
    # Fallback: try to find it in out
    return extract_obj_num(out)


def main():
    s = connect()

    # First: reset $sc_room if it's pointing to Heart of God (#150)
    print('=== Check/reset $sc_room ===')
    out = ev(s, 'player:tell(tostr($sc_room))', wait=1.0)
    current_num = extract_obj_num(out)
    print(f'  $sc_room currently = #{current_num}')
    if current_num == 150:
        print('  RESETTING — was pointing to Heart of God!')
        ev(s, '$sc_room = $nothing', wait=0.5)
        current_num = None

    # Check if valid sc_room exists
    scr_num = None
    if current_num is not None:
        ok = ev(s, f'player:tell(valid(#{current_num}) ? "yes" | "no")', wait=0.7)
        if 'yes' in ok:
            parent_check = ev(s, f'player:tell(parent(#{current_num}) == $room ? "yes" | "no")', wait=0.7)
            if 'yes' in parent_check:
                scr_num = current_num
                print(f'  $sc_room already valid as #{scr_num}')

    if scr_num is None:
        # Create new $sc_room as child of $room
        print('\n=== Creating $sc_room ===')
        scr_num = create_and_get_num(s, '$room', wait=2.0)
        if scr_num is None:
            print('ERROR: could not parse create result')
            s.close()
            return
        print(f'  Created #{scr_num}')
        ev(s, f'wf_new_obj.name = "sc_room prototype"', wait=0.5)
        ev(s, f'$sc_room = #{scr_num}', wait=0.5)
        # Verify
        out2 = ev(s, 'player:tell("VERIFY=" + tostr($sc_room))', wait=0.8)
        m2 = re.search(r'VERIFY=#(\d+)', out2)
        if m2:
            print(f'  $sc_room verified = #{m2.group(1)}')
        else:
            print(f'  $sc_room set. Raw verify: {out2.strip()[-60:]}')

    # Add look_self verb to sc_room
    print(f'\n=== Add look_self to $sc_room (#{scr_num}) ===')
    out = send(s, f'@verb #{scr_num}:"look_self" none none none', wait=0.6)
    if 'Verb added' not in out and 'already defined' not in out.lower():
        print(f'  WARN @verb: {repr(out[:80])}')
    program_verb(s, scr_num, 'look_self', [
        '"Show sector center room description (no area() call).";',
        'p = player;',
        'p:tell(this.name);',
        'p:tell("");',
        'p:tell(this.description);',
        'p:tell("");',
        '"Show exits";',
        'exits = {};',
        'if ("east_exit" in properties(this) && valid(this.east_exit))',
        '  exits = listappend(exits, "east");',
        'endif',
        'if ("west_exit" in properties(this) && valid(this.west_exit))',
        '  exits = listappend(exits, "west");',
        'endif',
        'if ("north_exit" in properties(this) && valid(this.north_exit))',
        '  exits = listappend(exits, "north");',
        'endif',
        'if ("south_exit" in properties(this) && valid(this.south_exit))',
        '  exits = listappend(exits, "south");',
        'endif',
        'if ("out_exit" in properties(this) && valid(this.out_exit))',
        '  exits = listappend(exits, "out (return to wilderness)");',
        'endif',
        'if (exits != {})',
        '  exitstr = "";',
        '  for ex in (exits)',
        '    exitstr = exitstr == "" ? ex | exitstr + ", " + ex;',
        '  endfor',
        '  p:tell("Exits: " + exitstr);',
        'endif',
        '"Show other players";',
        'for obj in (this.contents)',
        '  if (is_player(obj) && obj != p)',
        '    p:tell(obj.name + " is here.");',
        '  endif',
        'endfor',
    ])

    # Verify: create a test sc_room and look at it
    print('\n=== Verify: create test room and look ===')
    tr_num = create_and_get_num(s, '$sc_room', wait=2.0)
    if tr_num:
        ev(s, 'wf_new_obj.name = "Test SC Room"', wait=0.5)
        ev(s, 'wf_new_obj.description = "A spartan test room. Everything looks temporary."', wait=0.5)
        print(f'  Test room: #{tr_num}')
        out = send(s, f'@go #{tr_num}', wait=1.0)
        out = send(s, 'look', wait=2.0)
        print(f'  look output:\n{out.strip()}')
        # Return and recycle
        send(s, '@go #591', wait=0.8)
        ev(s, f'recycle(#{tr_num})', wait=0.5)
        print(f'  Test room #{tr_num} recycled.')
    else:
        print('  WARNING: could not create test room')

    # Save
    out = send(s, '@dump-database', wait=3.0)
    print(f'\nSave: {out.strip()[:60]}')
    print(f'\n$sc_room = #{scr_num}')
    s.close()
    print('Done.')


if __name__ == '__main__':
    main()
