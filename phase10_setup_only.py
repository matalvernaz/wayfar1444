#!/usr/bin/env python3
"""Phase 10 setup only — no test run."""
import socket, time, re

HOST = 'localhost'; PORT = 7777
PLAYER = 6; HEARTBEAT = 545

def connect():
    s = socket.socket(); s.connect((HOST, PORT)); s.settimeout(5)
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

def program_verb(s, obj_expr, verbname, code_lines):
    out = send(s, f'@program {obj_expr}:{verbname}', wait=1.5)
    if 'programming' not in out.lower():
        print(f'  ERROR: {repr(out[:150])}'); return False
    old = s.gettimeout(); s.settimeout(0.5)
    for i, line in enumerate(code_lines):
        send(s, line, wait=0.08)
        if i % 15 == 14: print(f'    ... {i+1}/{len(code_lines)}')
    s.settimeout(old)
    result = send(s, '.', wait=5.0)
    if re.search(r'[1-9]\d* error', result):
        print(f'  CODE ERROR:\n{result[:400]}'); return False
    print(f'  OK: {obj_expr}:{verbname}'); return True

def add_verb(s, obj_expr, verbname, args='none none none'):
    out = send(s, f'@verb {obj_expr}:{verbname} {args}', wait=0.6)
    if 'Verb added' not in out and 'already defined' not in out.lower():
        print(f'  WARN @verb: {repr(out[:80])}')

def extract_num(out):
    m = re.search(r'OBJNUM=#(\d+)', out)
    return int(m.group(1)) if m else None

s = connect()

# ── 1. Create $npc_worker prototype via temp verb ─────────────────────────
print('=== Create $npc_worker prototype ===')
out = ev(s, 'player:tell("NW_EXISTS=" + tostr("npc_worker" in properties(#0)))', wait=0.7)
nw_exists = '1' in out.strip()[-10:]
npc_num = None
if nw_exists:
    out2 = ev(s, 'player:tell("OBJNUM=" + tostr(#0.npc_worker))', wait=0.7)
    existing = extract_num(out2)
    if existing and existing > 0:
        npc_num = existing
        print(f'  $npc_worker already exists: #{npc_num}')
if npc_num is None:
    add_verb(s, f'#{PLAYER}', '"_nw_setup"', 'none none none')
    program_verb(s, f'#{PLAYER}', '_nw_setup', [
        '"Create $npc_worker prototype and register on #0.";',
        'if (!("npc_worker" in properties(#0)))',
        '  add_property(#0, "npc_worker", $nothing, {player, "rw"});',
        'endif',
        'if (!valid(#0.npc_worker))',
        '  nw = create($thing);',
        '  nw.name = "npc_worker prototype";',
        '  add_property(nw, "w_job", "ore", {player, "rw"});',
        '  add_property(nw, "w_owner", $nothing, {player, "rw"});',
        '  add_property(nw, "w_last_tick", 0, {player, "rw"});',
        '  #0.npc_worker = nw;',
        'endif',
        'player:tell("OBJNUM=" + tostr(#0.npc_worker));',
    ])
    out3 = send(s, '_nw_setup', wait=3.0)
    npc_num = extract_num(out3)
    if not npc_num:
        print(f'  ERROR: {repr(out3[-120:])}'); s.close(); exit(1)
    print(f'  $npc_worker = #{npc_num}')

# ── 2. $worker_list ────────────────────────────────────────────────────────
print('\n=== $worker_list ===')
out = ev(s, 'player:tell("WL_EXISTS=" + tostr("worker_list" in properties(#0)))', wait=0.7)
if '1' in out.strip()[-10:]:
    print('  already exists')
else:
    ev(s, 'add_property(#0, "worker_list", {}, {wizard, "rw"})', wait=0.8)
    print('  created')

# ── 3-5. Player verbs ──────────────────────────────────────────────────────
from phase10_workers import HIRE_VERB, FIRE_VERB, WORKERS_VERB, TICK_VERB_EXTENDED

print('\n=== hire verb ===')
add_verb(s, f'#{PLAYER}', '"hire"', 'any none none')
program_verb(s, f'#{PLAYER}', 'hire', HIRE_VERB)

print('\n=== fire verb ===')
add_verb(s, f'#{PLAYER}', '"fire"', 'any none none')
program_verb(s, f'#{PLAYER}', 'fire', FIRE_VERB)

print('\n=== workers verb ===')
add_verb(s, f'#{PLAYER}', '"workers"', 'none none none')
program_verb(s, f'#{PLAYER}', 'workers', WORKERS_VERB)

# ── 6. Extend tick ────────────────────────────────────────────────────────
print('\n=== Extend #545:tick ===')
program_verb(s, f'#{HEARTBEAT}', 'tick', TICK_VERB_EXTENDED)

# ── 7. tick_now helper ────────────────────────────────────────────────────
print('\n=== tick_now on #545 ===')
add_verb(s, f'#{HEARTBEAT}', '"tick_now"', 'none none none')
program_verb(s, f'#{HEARTBEAT}', 'tick_now', [
    '"Run worker tick immediately (test/debug).";',
    'set_task_perms(this.owner);',
    'now = time();',
    'clean_list = {};',
    'for w in ($worker_list)',
    '  if (!valid(w))',
    '    "skip";',
    '  else',
    '    clean_list = listappend(clean_list, w);',
    '    if ((now - w.w_last_tick) >= 300)',
    '      w.w_last_tick = now;',
    '      job = w.w_job;',
    '      iname = "ore sample";',
    '      idesc = "A rough chunk of alien mineral ore.";',
    '      if (job == "fiber")',
    '        iname = "fiber bundle";',
    '        idesc = "A bundle of dried alien plant fiber.";',
    '      elseif (job == "water")',
    '        iname = "water sample";',
    '        idesc = "A sealed flask of filtered water.";',
    '      elseif (job == "salvage")',
    '        iname = "salvage scrap";',
    '        idesc = "Twisted metal and polymer pulled from ruins.";',
    '      endif',
    '      item = create($thing);',
    '      item.name = iname;',
    '      item.description = idesc;',
    '      move(item, w.location);',
    '      owner = w.w_owner;',
    '      if (valid(owner) && (owner in connected_players()))',
    '        owner:tell("[COLONY] Your " + job + " gatherer deposited a " + iname + " in the factorium.");',
    '      endif',
    '    endif',
    '  endif',
    'endfor',
    '$worker_list = clean_list;',
    'player:tell("tick_now done. workers processed: " + tostr(length(clean_list)));',
])

out = send(s, '@dump-database', wait=3.0)
print(f'\nSave: {out.strip()[:60]}')
s.close()
print('Setup done.')
