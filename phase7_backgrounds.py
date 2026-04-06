#!/usr/bin/env python3
"""
Wayfar 1444 — Phase 7: Backgrounds / Character Classes (Redesign B)

Adds:
  1. connect verb on $player (#6) — on login, if no background chosen,
     show chooser and instruct player to type: background <number>
  2. background verb — shows current background, or 'background <1-5>' to pick
  3. Five backgrounds (stored as w_background string):
       colonist  — balanced, +20 HP +10 Stam, colony builder
       hunter    — endurance, +10 HP +30 Stam, wilderness tracker
       engineer  — craftsman, +10 HP +20 Stam, automation path
       medic     — resilient, +30 HP +10 Stam, colony health officer
       scavenger — opportunist, +10 HP +10 Stam, salvage sells for 50% more

Run with server live: python3 phase7_backgrounds.py
"""

import socket, time, re, sys
sys.path.insert(0, '/home/matt/wayfar')

HOST = 'localhost'
PORT = 7777
PLAYER = 6


def connect():
    s = socket.socket()
    s.connect((HOST, PORT))
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


def program_verb(s, obj_expr, verbname, code_lines):
    out = send(s, f'@program {obj_expr}:{verbname}', wait=1.0)
    if 'programming' not in out.lower():
        print(f'  ERROR @program {obj_expr}:{verbname}: {repr(out[:150])}')
        return False
    old_to = s.gettimeout()
    s.settimeout(0.3)
    for i, line in enumerate(code_lines):
        send(s, line, wait=0.06)
        if i % 15 == 14:
            print(f'    ... {i+1}/{len(code_lines)}')
    s.settimeout(old_to)
    result = send(s, '.', wait=3.0)
    if re.search(r'[1-9]\d* error', result):
        print(f'  CODE ERROR {obj_expr}:{verbname}:')
        print(result[:600])
        return False
    print(f'  OK: {obj_expr}:{verbname}')
    return True


def add_verb(s, obj_expr, verbname, args='none none none'):
    out = send(s, f'@verb {obj_expr}:{verbname} {args}', wait=0.6)
    if 'Verb added' not in out and 'already defined' not in out.lower():
        print(f'  WARN @verb {obj_expr}:{verbname}: {repr(out[:80])}')


# ─────────────────────────────────────────────────────────────────────────────
# Background display helper (called from connect and background verbs)
# ─────────────────────────────────────────────────────────────────────────────

BG_MENU_VERB = [
    '"Show the background selection menu.";',
    'p = player;',
    'p:tell("╔══════════════════════════════════════════════════╗");',
    'p:tell("║     WAYFAR 1444 — CHOOSE YOUR BACKGROUND        ║");',
    'p:tell("╠══════════════════════════════════════════════════╣");',
    'p:tell("║  1. Colonist   +20 HP  +10 Stam                 ║");',
    'p:tell("║     Balanced survivor. Built to establish roots. ║");',
    'p:tell("║  2. Hunter     +10 HP  +30 Stam                 ║");',
    'p:tell("║     Endurance specialist. Thrives in the wild.   ║");',
    'p:tell("║  3. Engineer   +10 HP  +20 Stam                 ║");',
    'p:tell("║     Craftsman. Masters tools and automation.     ║");',
    'p:tell("║  4. Medic      +30 HP  +10 Stam                 ║");',
    'p:tell("║     Field surgeon. Keeps the colony alive.       ║");',
    'p:tell("║  5. Scavenger  +10 HP  +10 Stam  +50% salvage   ║");',
    'p:tell("║     Opportunist. Turns wreckage into wealth.     ║");',
    'p:tell("╚══════════════════════════════════════════════════╝");',
    'p:tell("Type: background <number>  to choose.");',
    'p:tell("      background colonist  (or type the name)");',
]


# ─────────────────────────────────────────────────────────────────────────────
# connect verb — fires on login, shows chooser if background not set
# ─────────────────────────────────────────────────────────────────────────────

CONNECT_VERB = [
    '"Called when player connects. Show background chooser if not yet chosen.";',
    'p = player;',
    'if (p.w_background == "none" || p.w_background == "")',
    '  p:tell("");',
    '  p:tell("Welcome to Wayfar 1444.");',
    '  p:tell("You have not yet chosen a background.");',
    '  p:tell("");',
    '  this:bg_menu();',
    'endif',
]


# ─────────────────────────────────────────────────────────────────────────────
# background verb — show status OR pick a background
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
    '      p:tell("  Endurance specialist. Victory: harvest 100 wildlife specimens.");',
    '    elseif (p.w_background == "engineer")',
    '      p:tell("  Craftsman. Victory: automate all resource production.");',
    '    elseif (p.w_background == "medic")',
    '      p:tell("  Field surgeon. Victory: sustain colony health across 30 sessions.");',
    '    elseif (p.w_background == "scavenger")',
    '      p:tell("  Opportunist. Victory: accumulate 10,000 credits.");',
    '    endif',
    '  endif',
    '  return;',
    'endif',
    '"Already chosen";',
    'if (p.w_background != "none" && p.w_background != "")',
    '  p:tell("You are already a " + p.w_background + ". Backgrounds cannot be changed.");',
    '  p:tell("(Contact an admin if this is wrong.)");',
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
    '"Apply background bonuses";',
    'if (bg == "colonist")',
    '  p.w_hp_max = p.w_hp_max + 20; p.w_hp = p.w_hp_max;',
    '  p.w_stam_max = p.w_stam_max + 10; p.w_stam = p.w_stam_max;',
    'elseif (bg == "hunter")',
    '  p.w_hp_max = p.w_hp_max + 10; p.w_hp = p.w_hp_max;',
    '  p.w_stam_max = p.w_stam_max + 30; p.w_stam = p.w_stam_max;',
    'elseif (bg == "engineer")',
    '  p.w_hp_max = p.w_hp_max + 10; p.w_hp = p.w_hp_max;',
    '  p.w_stam_max = p.w_stam_max + 20; p.w_stam = p.w_stam_max;',
    'elseif (bg == "medic")',
    '  p.w_hp_max = p.w_hp_max + 30; p.w_hp = p.w_hp_max;',
    '  p.w_stam_max = p.w_stam_max + 10; p.w_stam = p.w_stam_max;',
    'elseif (bg == "scavenger")',
    '  p.w_hp_max = p.w_hp_max + 10; p.w_hp = p.w_hp_max;',
    '  p.w_stam_max = p.w_stam_max + 10; p.w_stam = p.w_stam_max;',
    'endif',
    'p.w_background = bg;',
    'p:tell("Background set: " + bg);',
    'p:tell("HP: " + tostr(p.w_hp_max) + "  Stamina: " + tostr(p.w_stam_max));',
    'p:tell("Type \'status\' to see your full stats.");',
]


def main():
    s = connect()

    # ── 1. bg_menu helper verb ────────────────────────────────────────────────
    print('=== bg_menu verb on $player ===')
    add_verb(s, f'#{PLAYER}', '"bg_menu"', 'none none none')
    program_verb(s, f'#{PLAYER}', 'bg_menu', BG_MENU_VERB)

    # ── 2. connect verb ───────────────────────────────────────────────────────
    print('\n=== connect verb on $player ===')
    add_verb(s, f'#{PLAYER}', '"connect"', 'none none none')
    program_verb(s, f'#{PLAYER}', 'connect', CONNECT_VERB)

    # ── 3. background verb ────────────────────────────────────────────────────
    print('\n=== background verb on $player ===')
    add_verb(s, f'#{PLAYER}', '"background"', 'any none none')
    program_verb(s, f'#{PLAYER}', 'background', BACKGROUND_VERB)

    # ── 4. Update sell verb to apply scavenger bonus ──────────────────────────
    # The scavenger gets +50% on salvage. We need to update the sell verb.
    print('\n=== Update sell verb with scavenger bonus ===')
    SELL_VERB_V2 = [
        '"Sell items to the Central Administrative Complex for credits.";',
        '"Usage: sell <item name> | sell all";',
        'p = player;',
        'query = (typeof(dobjstr) == STR) ? dobjstr | "";',
        'if (query == "" && args != {})',
        '  for w in (args)',
        '    if (typeof(w) == STR)',
        '      query = query == "" ? w | query + " " + w;',
        '    endif',
        '  endfor',
        'endif',
        'if (query == "")',
        '  p:tell("Sell what? (sell <item> or sell all)");',
        '  p:tell("Type \'prices\' to see CAC buy rates.");',
        '  return;',
        'endif',
        'sell_list = {};',
        'if (query == "all" || query == "resources")',
        '  for itm in (p.contents)',
        '    sell_list = listappend(sell_list, itm);',
        '  endfor',
        'else',
        '  for itm in (p.contents)',
        '    nm = "";',
        '    try',
        '      nm = tostr(itm.name);',
        '    except e (ANY)',
        '      nm = "";',
        '    endtry',
        '    if (index(nm, query))',
        '      sell_list = listappend(sell_list, itm);',
        '    endif',
        '  endfor',
        'endif',
        'if (sell_list == {})',
        '  p:tell("You\'re not carrying \'" + query + "\'.");',
        '  return;',
        'endif',
        'is_scav = (p.w_background == "scavenger");',
        'total = 0;',
        'sold = 0;',
        'for itm in (sell_list)',
        '  nm = "";',
        '  try nm = tostr(itm.name); except e (ANY) nm = ""; endtry',
        '  price = 0;',
        '  if (index(nm, "ore") || index(nm, "mineral"))',
        '    price = 5;',
        '  elseif (index(nm, "fiber") || index(nm, "plant"))',
        '    price = 3;',
        '  elseif (index(nm, "water sample") || index(nm, "raw water"))',
        '    price = 2;',
        '  elseif (index(nm, "salvage") || index(nm, "scrap") || index(nm, "wreckage"))',
        '    price = is_scav ? 6 | 4;',
        '  elseif (index(nm, "inert metal"))',
        '    price = 15;',
        '  elseif (index(nm, "crude wire"))',
        '    price = 12;',
        '  elseif (index(nm, "ration bar") || index(nm, "ration"))',
        '    price = 8;',
        '  elseif (index(nm, "canteen"))',
        '    price = 6;',
        '  endif',
        '  if (price > 0)',
        '    total = total + price;',
        '    sold = sold + 1;',
        '    recycle(itm);',
        '  endif',
        'endfor',
        'if (sold == 0)',
        '  p:tell("The CAC doesn\'t buy that. (Type \'prices\' to see what they buy.)");',
        '  return;',
        'endif',
        'p.w_credits = p.w_credits + total;',
        'p:tell("[CAC] Purchased " + tostr(sold) + " item(s) for " + tostr(total) + " cr.  Balance: " + tostr(p.w_credits) + " cr");',
    ]
    program_verb(s, f'#{PLAYER}', 'sell', SELL_VERB_V2)

    # ── 5. Test ───────────────────────────────────────────────────────────────
    print('\n=== Test backgrounds ===')
    add_verb(s, f'#{PLAYER}', '"bg_test"', 'none none none')
    program_verb(s, f'#{PLAYER}', 'bg_test', [
        '"Test background chooser.";',
        'player:tell("=== BG_TEST BEGIN ===");',
        '"Show menu";',
        'this:bg_menu();',
        'player:tell("---");',
        '"Check w_background current value";',
        'player:tell("Current background: " + player.w_background);',
        '"Test choosing scavenger";',
        'old_bg = player.w_background;',
        'old_hp_max = player.w_hp_max;',
        'old_stam_max = player.w_stam_max;',
        'player.w_background = "none";',
        'player.w_hp_max = 100; player.w_hp = 100;',
        'player.w_stam_max = 100; player.w_stam = 100;',
        'this:background("scavenger");',
        'player:tell("  bg=" + player.w_background + " hp_max=" + tostr(player.w_hp_max) + " stam_max=" + tostr(player.w_stam_max));',
        'player:tell("  Expected: scavenger hp_max=110 stam_max=110");',
        '"Restore";',
        'player.w_background = old_bg;',
        'player.w_hp_max = old_hp_max; player.w_hp = old_hp_max;',
        'player.w_stam_max = old_stam_max; player.w_stam = old_stam_max;',
        '"Test scavenger sell bonus";',
        'player.w_background = "scavenger";',
        'player.w_credits = 0;',
        'sc1 = create($thing); sc1.name = "salvage fragment"; move(sc1, player);',
        'this:sell("salvage");',
        'player:tell("  Scav salvage price: " + tostr(player.w_credits) + " cr (expect 6)");',
        '"Test non-scavenger";',
        'player.w_background = "colonist";',
        'player.w_credits = 0;',
        'sc2 = create($thing); sc2.name = "salvage fragment"; move(sc2, player);',
        'this:sell("salvage");',
        'player:tell("  Normal salvage price: " + tostr(player.w_credits) + " cr (expect 4)");',
        '"Restore";',
        'player.w_background = old_bg;',
        'player.w_credits = 0;',
        'player:tell("=== BG_TEST END ===");',
    ])
    out = send(s, 'bg_test', wait=8.0)
    print(out.strip())

    # ── 6. Save ───────────────────────────────────────────────────────────────
    out = send(s, '@dump-database', wait=3.0)
    print(f'Save: {out.strip()[:60]}')
    s.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
