#!/usr/bin/env python3
"""
Wayfar 1444 — Phase 13: New Player Creation Flow

Fixes:
  1. Proper base stat initialization on first connect
  2. Starting items (basic crafting tool + resources)
  3. SP cap set to 2500
  4. Arrival narrative text
  5. Background verb applies bonuses on top of correct base stats

Run with server live: python3 phase13_newplayer.py
"""

import socket, time, re

HOST = 'localhost'
PORT = 7777
PLAYER = 6
BCT_NUM = 592  # $basic_craft_tool

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

def add_verb(s, obj_expr, verbname, args='none none none'):
    out = send(s, f'@verb {obj_expr}:{verbname} {args}', wait=0.6)
    if 'Verb added' not in out and 'already defined' not in out.lower():
        print(f'  WARN @verb {obj_expr}:{verbname}: {repr(out[:80])}', flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# _init_newplayer — initialize all stats + give starter items
# Called once from connect verb when w_background == "none"
# ─────────────────────────────────────────────────────────────────────────────

INIT_NEWPLAYER_VERB = [
    '"Initialize a new player with base stats and starter items. Called once.";',
    'p = player;',
    '"Check if already initialized (has crafting tool = not new)";',
    'has_tool = 0;',
    'for itm in (p.contents)',
    f'  if (is_a(itm, #{BCT_NUM}))',
    '    has_tool = 1; break;',
    '  endif',
    'endfor',
    'if (has_tool)',
    '  return;',
    'endif',
    '"--- Base survival stats ---";',
    'p.hunger = 80;',
    'p.health = 100;',
    'p.stamina = 100;',
    '"--- Base combat stats (before background bonuses) ---";',
    'p.w_hp = 50;',
    'p.w_hp_max = 50;',
    'p.w_stam = 3;',
    'p.w_stam_max = 3;',
    'p.w_clarity = 3;',
    'p.w_clarity_max = 3;',
    'p.w_aggression = 3;',
    'p.w_aggression_max = 3;',
    '"--- Economy / progression ---";',
    'p.w_credits = 0;',
    'p.w_sp = 0;',
    'p.w_sp_cap = 2500;',
    'p.w_sp_earned = 0;',
    'p.w_learned = {};',
    'p.w_background = "none";',
    'p.w_colony = $nothing;',
    '"--- Equipment slots ---";',
    'p.w_weapon = $nothing;',
    'p.w_armor = $nothing;',
    'p.w_gadget = $nothing;',
    'p.w_special = $nothing;',
    'p.w_target = $nothing;',
    '"--- Give starter items ---";',
    f'tool = create(#{BCT_NUM});',
    'tool.name = "basic crafting tool";',
    'tool.description = "A battered multi-tool issued to all colonists. Craft items with: craft <recipe name>";',
    'move(tool, p);',
    '"Give some starting resources";',
    'for i in [1..4]',
    '  f = create($thing);',
    '  f.name = "alien plant fiber";',
    '  f.description = "A tough, fibrous stalk from an alien shrub.";',
    '  move(f, p);',
    'endfor',
    'for i in [1..2]',
    '  o = create($thing);',
    '  o.name = "ore sample";',
    '  o.description = "A rough chunk of alien mineral ore.";',
    '  move(o, p);',
    'endfor',
    '"--- Move to Impact Site Zero ---";',
    'if (p.location != #459)',
    '  move(p, #459);',
    'endif',
]


# ─────────────────────────────────────────────────────────────────────────────
# connect verb — fires on login; init new players, show background chooser
# ─────────────────────────────────────────────────────────────────────────────

CONNECT_VERB = [
    '"Called when player connects.";',
    'p = player;',
    'if (p.w_background == "none" || p.w_background == "")',
    '  "First time — initialize stats and give starter items";',
    '  this:_init_newplayer();',
    '  p:tell("");',
    '  p:tell("══════════════════════════════════════════════════");',
    '  p:tell("           W A Y F A R   1 4 4 4");',
    '  p:tell("══════════════════════════════════════════════════");',
    '  p:tell("");',
    '  p:tell("  The escape pod shudders and screams through");',
    '  p:tell("  alien atmosphere. Metal tears. Systems fail.");',
    '  p:tell("  You hit hard.");',
    '  p:tell("");',
    '  p:tell("  You crawl from the wreckage. The beacon is");',
    '  p:tell("  transmitting. The Central Administrative");',
    '  p:tell("  Complex will buy any resources you can find.");',
    '  p:tell("  Survive. Build. Sell. That is the loop.");',
    '  p:tell("");',
    '  p:tell("  You have a basic crafting tool, some fiber,");',
    '  p:tell("  and ore from the crash. Type CRAFT to see");',
    '  p:tell("  what you can make. Type STATUS for your");',
    '  p:tell("  vitals. LOOK to see around you.");',
    '  p:tell("");',
    '  p:tell("  First: choose who you were before the crash.");',
    '  p:tell("");',
    '  this:bg_menu();',
    'else',
    '  "Returning player";',
    '  p:tell("Welcome back, " + p.name + ".");',
    '  p:tell("[" + p.w_background + " | HP:" + tostr(p.w_hp) + "/" + tostr(p.w_hp_max) + " | Credits:" + tostr(p.w_credits) + "]");',
    'endif',
]


# ─────────────────────────────────────────────────────────────────────────────
# background verb — choose background, apply bonuses on correct base
# ─────────────────────────────────────────────────────────────────────────────

BACKGROUND_VERB = [
    '"Show or set player background. Usage: background [name or number]";',
    'p = player;',
    '"Build arg string";',
    'arg = (typeof(dobjstr) == STR) ? dobjstr | "";',
    'if (arg == "" && args != {})',
    '  for w in (args)',
    '    if (typeof(w) == STR)',
    '      arg = arg == "" ? w | arg + " " + w;',
    '    endif',
    '  endfor',
    'endif',
    '"No arg — show current background and menu if unchosen";',
    'if (arg == "")',
    '  if (p.w_background == "none" || p.w_background == "")',
    '    p:tell("You have not chosen a background yet.");',
    '    this:bg_menu();',
    '  else',
    '    p:tell("Background: " + p.w_background);',
    '    if (p.w_background == "colonist")',
    '      p:tell("  Balanced survivor. Victory: establish a thriving sector center.");',
    '    elseif (p.w_background == "hunter")',
    '      p:tell("  Endurance specialist. Victory: kill 100 wildlife on a planet surface.");',
    '    elseif (p.w_background == "engineer")',
    '      p:tell("  Craftsman. Victory: craft 25 products of quality 70+.");',
    '    elseif (p.w_background == "medic")',
    '      p:tell("  Field surgeon. Victory: research 25 artifacts at a laboratory.");',
    '    elseif (p.w_background == "scavenger")',
    '      p:tell("  Opportunist. Victory: accumulate 10,000 credits.");',
    '    endif',
    '  endif',
    '  return;',
    'endif',
    '"Already chosen";',
    'if (p.w_background != "none" && p.w_background != "")',
    '  p:tell("You are already a " + p.w_background + ". Backgrounds cannot be changed (yet).");',
    '  return;',
    'endif',
    '"Map arg to background name";',
    'bg = "";',
    'if (arg == "1" || index(arg, "colonist"))',
    '  bg = "colonist";',
    'elseif (arg == "2" || index(arg, "hunter"))',
    '  bg = "hunter";',
    'elseif (arg == "3" || index(arg, "engineer"))',
    '  bg = "engineer";',
    'elseif (arg == "4" || index(arg, "medic"))',
    '  bg = "medic";',
    'elseif (arg == "5" || index(arg, "scavenger"))',
    '  bg = "scavenger";',
    'endif',
    'if (bg == "")',
    '  p:tell("Unknown background: \'" + arg + "\'");',
    '  this:bg_menu();',
    '  return;',
    'endif',
    '"Apply background bonuses (base HP is 50, base dice are 3)";',
    'if (bg == "colonist")',
    '  p.w_hp_max = p.w_hp_max + 20;',
    '  p.w_stam_max = p.w_stam_max + 1;',
    'elseif (bg == "hunter")',
    '  p.w_hp_max = p.w_hp_max + 10;',
    '  p.w_stam_max = p.w_stam_max + 2;',
    'elseif (bg == "engineer")',
    '  p.w_hp_max = p.w_hp_max + 10;',
    '  p.w_clarity_max = p.w_clarity_max + 2;',
    'elseif (bg == "medic")',
    '  p.w_hp_max = p.w_hp_max + 30;',
    '  p.w_clarity_max = p.w_clarity_max + 1;',
    'elseif (bg == "scavenger")',
    '  p.w_hp_max = p.w_hp_max + 10;',
    '  p.w_aggression_max = p.w_aggression_max + 1;',
    'endif',
    '"Set current to max";',
    'p.w_hp = p.w_hp_max;',
    'p.w_stam = p.w_stam_max;',
    'p.w_clarity = p.w_clarity_max;',
    'p.w_aggression = p.w_aggression_max;',
    'p.w_background = bg;',
    'p:tell("");',
    'p:tell("══════════════════════════════════════════════════");',
    'p:tell("  BACKGROUND: " + bg);',
    'p:tell("  HP: " + tostr(p.w_hp_max) + "  STM:" + tostr(p.w_stam_max) + "  CLR:" + tostr(p.w_clarity_max) + "  AGG:" + tostr(p.w_aggression_max));',
    'p:tell("══════════════════════════════════════════════════");',
    'p:tell("");',
    'p:tell("  Your past clicks into focus. You remember now.");',
    'p:tell("  The crash didn\'t take everything.");',
    'p:tell("");',
    'p:tell("  NEXT STEPS:");',
    'p:tell("  - LOOK       — see your surroundings + map");',
    'p:tell("  - GATHER     — harvest resources from this area");',
    'p:tell("  - CRAFT      — see craftable recipes");',
    'p:tell("  - STATUS     — check your vitals + credits");',
    'p:tell("  - n/s/e/w    — move across the planet");',
    'p:tell("  - SELL ALL   — sell resources for credits");',
    'p:tell("  - SKILLS     — spend credits on skills");',
    'p:tell("");',
]


# ─────────────────────────────────────────────────────────────────────────────
# bg_menu — unchanged from phase7 but included for completeness
# ─────────────────────────────────────────────────────────────────────────────

BG_MENU_VERB = [
    '"Display background selection menu.";',
    'p = player;',
    'p:tell("╔══════════════════════════════════════════════════╗");',
    'p:tell("║            CHOOSE YOUR BACKGROUND               ║");',
    'p:tell("╠══════════════════════════════════════════════════╣");',
    'p:tell("║  1. Colonist  +20 HP  +1 STM die               ║");',
    'p:tell("║     Balanced survivor. Jack of all trades.      ║");',
    'p:tell("║                                                 ║");',
    'p:tell("║  2. Hunter    +10 HP  +2 STM dice               ║");',
    'p:tell("║     Endurance specialist. Born to fight.        ║");',
    'p:tell("║                                                 ║");',
    'p:tell("║  3. Engineer  +10 HP  +2 CLR dice               ║");',
    'p:tell("║     Craftsman. Precision and technology.        ║");',
    'p:tell("║                                                 ║");',
    'p:tell("║  4. Medic     +30 HP  +1 CLR die                ║");',
    'p:tell("║     Field surgeon. Hard to kill.                ║");',
    'p:tell("║                                                 ║");',
    'p:tell("║  5. Scavenger +10 HP  +1 AGG die  +50% salvage ║");',
    'p:tell("║     Opportunist. Turns wreckage into wealth.    ║");',
    'p:tell("╚══════════════════════════════════════════════════╝");',
    'p:tell("Type: background <number>  to choose.");',
    'p:tell("      background colonist  (or type the name)");',
]


def main():
    s = connect()
    print('Connected.', flush=True)

    # ── 1. Ensure w_sp_cap and w_sp_earned exist on $player ──────────────────
    print('\n=== Ensure progression properties exist ===', flush=True)
    for prop, default in [('w_sp_cap', '2500'), ('w_sp_earned', '0'), ('w_sp', '0')]:
        out = ev(s, f'player:tell("{prop}" in properties($player))', wait=0.7)
        if '1' in out.strip()[-5:]:
            print(f'  {prop} already exists', flush=True)
        else:
            ev(s, f'add_property($player, "{prop}", {default}, {{player, "rwc"}})', wait=0.8)
            print(f'  Created {prop} = {default}', flush=True)

    # ── 2. Set proper defaults on $player prototype ──────────────────────────
    print('\n=== Set base stat defaults on $player ===', flush=True)
    defaults = {
        'w_hp': '50', 'w_hp_max': '50',
        'w_stam': '3', 'w_stam_max': '3',
        'w_clarity': '3', 'w_clarity_max': '3',
        'w_aggression': '3', 'w_aggression_max': '3',
        'hunger': '80', 'health': '100', 'stamina': '100',
        'w_credits': '0', 'w_background': '"none"',
        'w_sp': '0', 'w_sp_cap': '2500', 'w_sp_earned': '0',
    }
    for prop, val in defaults.items():
        ev(s, f'$player.{prop} = {val}', wait=0.3)
    print(f'  Set {len(defaults)} defaults', flush=True)

    # ── 3. _init_newplayer verb ──────────────────────────────────────────────
    print('\n=== _init_newplayer verb ===', flush=True)
    add_verb(s, f'#{PLAYER}', '"_init_newplayer"', 'none none none')
    program_verb(s, f'#{PLAYER}', '_init_newplayer', INIT_NEWPLAYER_VERB)

    # ── 4. connect verb ──────────────────────────────────────────────────────
    print('\n=== connect verb ===', flush=True)
    program_verb(s, f'#{PLAYER}', 'connect', CONNECT_VERB)

    # ── 5. bg_menu verb ──────────────────────────────────────────────────────
    print('\n=== bg_menu verb ===', flush=True)
    program_verb(s, f'#{PLAYER}', 'bg_menu', BG_MENU_VERB)

    # ── 6. background verb ───────────────────────────────────────────────────
    print('\n=== background verb ===', flush=True)
    program_verb(s, f'#{PLAYER}', 'background', BACKGROUND_VERB)

    # ── 7. Save ──────────────────────────────────────────────────────────────
    out = send(s, '@dump-database', wait=3.0)
    print(f'\nSave: {out.strip()[:60]}', flush=True)

    s.close()
    print('\nPhase 13 (New Player) deployed.', flush=True)


if __name__ == '__main__':
    main()
