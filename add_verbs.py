#!/usr/bin/env python3
"""
Wayfar 1444 - Add core verbs to existing objects.

Rooms #560-563 and player props (w_hp etc.) already exist.
This script adds all the gameplay verbs.

Run: python3 add_verbs.py
"""

import socket, time, re

HOST = 'localhost'
PORT = 7777

PLAYER   = 6
WROOM    = 452
CAC      = 561    # CAC Exchange
DISPATCH = 563    # Planetary Dispatch Bay
SKILLS_ROOM = 562


def connect():
    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(3)
    time.sleep(0.5)
    s.recv(65536)
    s.sendall(b'connect wizard\r\n')
    time.sleep(0.7)
    s.recv(65536)
    return s


def send(s, cmd, wait=0.65):
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


def ev(s, expr, wait=0.55):
    return send(s, f'; {expr}', wait=wait)


def moo_str(text):
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'


def add_verb(s, obj_num, verbname, args='none none none'):
    """Add verb; verbname may be quoted for aliases e.g. '"st status"'."""
    cmd = f'@verb #{obj_num}:{verbname} {args}'
    out = send(s, cmd, wait=0.6)
    ok = 'Verb added' in out or 'already defined' in out.lower()
    if not ok:
        print(f'  WARN add_verb #{obj_num}:{verbname}: {repr(out[:100])}')
    return out


def program_verb(s, obj_num, verbname, code_lines):
    """Program verb with code. verbname is the base name (no aliases)."""
    out = send(s, f'@program #{obj_num}:{verbname}', wait=0.7)
    if 'programming' not in out.lower():
        print(f'  ERROR @program #{obj_num}:{verbname}: {repr(out[:150])}')
        return out
    old_timeout = s.gettimeout()
    s.settimeout(0.25)
    for line in code_lines:
        send(s, line, wait=0.04)
    s.settimeout(old_timeout)
    result = send(s, '.', wait=2.5)
    if re.search(r'[1-9]\d* error', result):
        print(f'  CODE ERROR #{obj_num}:{verbname}:')
        print(result[:800])
    else:
        print(f'    OK: #{obj_num}:{verbname}')
    return result


# ─────────────────────────────────────────────────────────────────────────────
# ST — dice-pool status display
# ─────────────────────────────────────────────────────────────────────────────

def add_st(s):
    print('\n[ST]')
    add_verb(s, PLAYER, '"st status"', 'none none none')
    program_verb(s, PLAYER, 'st', [
        '"Wayfar dice-pool status.";',
        'esc = chr(27); bold = esc + "[1m"; reset = esc + "[0m";',
        'red = esc + "[31m"; grn = esc + "[32m"; yel = esc + "[33m";',
        'cyn = esc + "[36m"; dim = esc + "[90m";',
        'hp = player.w_hp; hpmax = player.w_hp_max;',
        'stam = player.w_stam; stammax = player.w_stam_max;',
        'clar = player.w_clar; clarmax = player.w_clar_max;',
        'agg = player.w_agg; aggmax = player.w_agg_max;',
        '"HP bar (10 chars)";',
        'pct = (hpmax > 0) ? (hp * 10 / hpmax) | 0;',
        'hpbar = ""; filled = 0;',
        'while (filled < 10)',
        '  hpbar = hpbar + (filled < pct ? "#" | "-");',
        '  filled = filled + 1;',
        'endwhile',
        'hpcol = (pct >= 7) ? grn | (pct >= 4 ? yel | red);',
        '"Dice bars";',
        'stambar = ""; idx = 1;',
        'while (idx <= stammax)',
        '  stambar = stambar + (idx <= stam ? "|" | (dim + "." + reset));',
        '  idx = idx + 1;',
        'endwhile',
        'clarbar = ""; idx = 1;',
        'while (idx <= clarmax)',
        '  clarbar = clarbar + (idx <= clar ? "|" | (dim + "." + reset));',
        '  idx = idx + 1;',
        'endwhile',
        'aggbar = ""; idx = 1;',
        'while (idx <= aggmax)',
        '  aggbar = aggbar + (idx <= agg ? "|" | (dim + "." + reset));',
        '  idx = idx + 1;',
        'endwhile',
        'player:tell(bold + "=== STATUS ===" + reset);',
        'player:tell("  HP     : " + hpcol + "[" + hpbar + "]" + reset + " " + tostr(hp) + "/" + tostr(hpmax));',
        'player:tell("  Stamina: [" + grn + stambar + reset + "] " + tostr(stam) + "/" + tostr(stammax));',
        'player:tell("  Clarity: [" + cyn + clarbar + reset + "] " + tostr(clar) + "/" + tostr(clarmax));',
        'player:tell("  Aggress: [" + yel + aggbar + reset + "] " + tostr(agg) + "/" + tostr(aggmax));',
        'player:tell("  Credits: " + tostr(player.w_credits) + "  |  SP: " + tostr(player.w_sp) + "/" + tostr(player.w_sp_cap));',
        'player:tell("  Class  : " + player.w_background);',
        'if (player.w_nourished > time())',
        '  player:tell("  Status : " + grn + "Nourished" + reset);',
        'endif',
        'tgt = player.w_combat_target;',
        'if (valid(tgt))',
        '  player:tell("  Target : " + tgt.name);',
        'endif',
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Combat: KILL, SWING, FIRE
# ─────────────────────────────────────────────────────────────────────────────

def add_combat(s):
    print('\n[KILL]')
    add_verb(s, PLAYER, 'kill', 'any none none')
    program_verb(s, PLAYER, 'kill', [
        '"Set combat target.";',
        'if (!valid(dobj))',
        '  player:tell("Kill what?");',
        '  return;',
        'endif',
        'if (dobj == player)',
        '  player:tell("You cannot target yourself.");',
        '  return;',
        'endif',
        'if (dobj.location != player.location)',
        '  player:tell(dobj.name + " is not here.");',
        '  return;',
        'endif',
        'player.w_combat_target = dobj;',
        'player:tell("You set your sights on " + dobj.name + ".");',
        'player.location:announce(player.name + " eyes " + dobj.name + " dangerously.", player);',
    ])

    print('\n[SWING]')
    add_verb(s, PLAYER, 'swing', 'none none none')
    program_verb(s, PLAYER, 'swing', [
        '"Melee attack using stamina dice.";',
        'target = player.w_combat_target;',
        'if (!valid(target))',
        '  player:tell("No target. Use: kill <name>");',
        '  return;',
        'endif',
        'if (target.location != player.location)',
        '  player:tell(target.name + " is not here.");',
        '  player.w_combat_target = #-1;',
        '  return;',
        'endif',
        'stam = player.w_stam;',
        'if (stam <= 0)',
        '  player:tell("Exhausted -- wait for stamina dice to recover.");',
        '  return;',
        'endif',
        'player.w_stam = stam - 1;',
        'roll = random(6) + player.w_stam_max;',
        '"Defense: 4 for unknown targets, check w_hp as proxy for being a combatant";',
        'tdef = ("w_hp" in properties(target)) ? 4 | 3;',
        'if (roll >= tdef)',
        '  agg = player.w_agg;',
        '  damage = (agg <= 0) ? 3 | (random(agg * 2) + 2);',
        '  if ("w_hp" in properties(target))',
        '    newhp = target.w_hp - damage;',
        '    target.w_hp = newhp;',
        '    if (newhp <= 0)',
        '      player:tell("You cut down " + target.name + " for " + tostr(damage) + " damage!");',
        '      player.location:announce(player.name + " kills " + target.name + "!", player);',
        '      player.w_sp = min(player.w_sp + 10, player.w_sp_cap);',
        '      player.w_sp_earned = player.w_sp_earned + 10;',
        '      if (is_a(target, $player))',
        '        target:respawn();',
        '      else',
        '        for item in (target.contents)',
        '          move(item, player.location);',
        '        endfor',
        '        recycle(target);',
        '      endif',
        '      player.w_combat_target = #-1;',
        '    else',
        '      player:tell("You hit " + target.name + " for " + tostr(damage) + " damage. [" + tostr(newhp) + " HP]");',
        '      player.location:announce(player.name + " attacks " + target.name + ".", player);',
        '    endif',
        '  else',
        '    player:tell("You hit " + target.name + " but they seem unfazed.");',
        '  endif',
        'else',
        '  player:tell("Miss! [rolled " + tostr(roll) + " vs def " + tostr(tdef) + "]");',
        '  player.location:announce(player.name + " swings and misses.", player);',
        'endif',
    ])

    print('\n[FIRE]')
    add_verb(s, PLAYER, 'fire', 'none none none')
    program_verb(s, PLAYER, 'fire', [
        '"Ranged attack using clarity dice.";',
        'target = player.w_combat_target;',
        'if (!valid(target))',
        '  player:tell("No target. Use: kill <name>");',
        '  return;',
        'endif',
        'if (target.location != player.location)',
        '  player:tell(target.name + " is not here.");',
        '  player.w_combat_target = #-1;',
        '  return;',
        'endif',
        'clar = player.w_clar;',
        'if (clar <= 0)',
        '  player:tell("Too blurred to aim -- wait for clarity dice to recover.");',
        '  return;',
        'endif',
        'player.w_clar = clar - 1;',
        'roll = random(6) + player.w_clar_max;',
        'tdef = ("w_hp" in properties(target)) ? 4 | 3;',
        'if (roll >= tdef)',
        '  agg = player.w_agg;',
        '  damage = (agg <= 0) ? 3 | (random(agg * 2) + 2);',
        '  if ("w_hp" in properties(target))',
        '    newhp = target.w_hp - damage;',
        '    target.w_hp = newhp;',
        '    if (newhp <= 0)',
        '      player:tell("Your shot drops " + target.name + " for " + tostr(damage) + " damage!");',
        '      player.location:announce(player.name + " guns down " + target.name + "!", player);',
        '      player.w_sp = min(player.w_sp + 10, player.w_sp_cap);',
        '      player.w_sp_earned = player.w_sp_earned + 10;',
        '      if (is_a(target, $player))',
        '        target:respawn();',
        '      else',
        '        for item in (target.contents)',
        '          move(item, player.location);',
        '        endfor',
        '        recycle(target);',
        '      endif',
        '      player.w_combat_target = #-1;',
        '    else',
        '      player:tell("Hit " + target.name + " for " + tostr(damage) + " damage. [" + tostr(newhp) + " HP]");',
        '      player.location:announce(player.name + " fires at " + target.name + ".", player);',
        '    endif',
        '  else',
        '    player:tell("Your shot hits " + target.name + " but seems to do nothing.");',
        '  endif',
        'else',
        '  player:tell("Miss! [rolled " + tostr(roll) + " vs def " + tostr(tdef) + "]");',
        '  player.location:announce(player.name + " misses the shot.", player);',
        'endif',
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Skills: SKILLS list, LEARN (override existing), FORGET
# ─────────────────────────────────────────────────────────────────────────────

SKILLS = [
    # (name, sp_cost, prereq, description, bonus_prop, bonus_amt)
    ('heavy_tan',             75,  '',                   'Heavy Tan: +10 max HP',                    'w_hp_max',   10),
    ('situational_awareness', 75,  '',                   'Situational Awareness: +1 stamina max',    'w_stam_max',  1),
    ('i_work_out',           100,  'situational_awareness', 'I Work Out: +1 defense, +1 stam max',  'w_stam_max',  1),
    ('tough_guy',            250,  'i_work_out',         'Tough Guy: +10 HP, +2 stam max',          'w_hp_max',   10),
    ('knows_end',             50,  '',                   'Knows Which End Hurts: +1 agg max',       'w_agg_max',   1),
    ('self_defense',         100,  'knows_end',          'Self Defense Training: +1 stam max',      'w_stam_max',  1),
    ('slashing',             150,  'knows_end',          'Advanced Slashing: +1 agg max',           'w_agg_max',   1),
    ('power_operation',       50,  '',                   'Power Operation: +1 clarity max',         'w_clar_max',  1),
    ('touchpanel',           100,  'power_operation',    'Touchpanel Training: +1 clarity max',     'w_clar_max',  1),
    ('machine_spirit',       200,  'touchpanel',         'Machine Spirit: +5 max HP',               'w_hp_max',    5),
    ('improvisation',         50,  '',                   'Improvisation: grants IMPROVISE',         '',            0),
    ('crude_planning',       100,  '',                   'Crude Planning: faster crafting',         '',            0),
    ('better_materials',     150,  'crude_planning',     'Better Materials: grants PURIFY',         '',            0),
    ('crafter',              200,  'better_materials',   'Crafter: +1 success, grants STAMP',       '',            0),
    ('sightseer',             25,  '',                   'Sightseer: helps explore/discover',       '',            0),
    ('developing_obs',        75,  'sightseer',          'Developing Observation: better explore',  '',            0),
    ('terrain_details',      150,  'developing_obs',     'Terrain Details: grants SURVEY',          '',            0),
    ('cartographer',         250,  'terrain_details',    'Unpaid Cartographer: grants DISCOVER',    '',            0),
    ('first_aid',             50,  '',                   'First Aid: grants BANDAGE',               'w_hp_max',    2),
    ('pharmacy',             100,  'first_aid',          'Pharmacy: +5 max HP',                     'w_hp_max',    5),
    ('neurosurgeon',         150,  'pharmacy',           'Neurosurgeon: medical mastery',           '',            0),
    ('matrix_coder',          75,  '',                   'Matrix Coder: prereq for hacking',        '',            0),
    ('novice_hacker',         75,  'matrix_coder',       'Novice Hacker: +1 clarity max',           'w_clar_max',  1),
    ('lab_operation',        150,  '',                   'Lab Operation: research access',          '',            0),
    ('research_focus',       150,  '',                   'Research Focus: research bonus',          '',            0),
    ('driving',              100,  '',                   'Driving: operate land vehicles',         '',            0),
    ('flying',               100,  '',                   'Flying: operate aircraft',               '',            0),
]

def skill_defs_lines(skills, chunk_size=9):
    """Return MOO lines that build skill_defs in chunks to avoid line-length limits."""
    chunks = [skills[i:i+chunk_size] for i in range(0, len(skills), chunk_size)]
    lines = []
    chunk_vars = []
    for ci, chunk in enumerate(chunks):
        var = f'_sd{ci}'
        chunk_vars.append(var)
        entries = ', '.join(
            f'{{{moo_str(sk[0])}, {sk[1]}, {moo_str(sk[2])}, {moo_str(sk[3])}, {moo_str(sk[4])}, {sk[5]}}}'
            for sk in chunk
        )
        lines.append(f'{var} = {{{entries}}};')
    splice = ', '.join(f'@{v}' for v in chunk_vars)
    lines.append(f'skill_defs = {{{splice}}};')
    return lines


def add_skills(s):
    print('\n[SKILLS]')
    add_verb(s, PLAYER, 'skills', 'none none none')

    # Build listing code
    cats = [
        ('SURVIVAL',    ['heavy_tan','situational_awareness','i_work_out','tough_guy']),
        ('COMBAT',      ['knows_end','self_defense','slashing']),
        ('TECH WEAPONS',['power_operation','touchpanel','machine_spirit']),
        ('CRAFTING',    ['improvisation','crude_planning','better_materials','crafter']),
        ('EXPLORATION', ['sightseer','developing_obs','terrain_details','cartographer']),
        ('MEDICINE',    ['first_aid','pharmacy','neurosurgeon']),
        ('SECURITY',    ['matrix_coder','novice_hacker']),
        ('SCIENCE',     ['lab_operation','research_focus']),
        ('VEHICLES',    ['driving','flying']),
    ]
    skill_map = {sk[0]: sk for sk in SKILLS}

    lines = [
        '"List available skills.";',
        'esc = chr(27); bold = esc + "[1m"; reset = esc + "[0m";',
        'yel = esc + "[33m"; dim = esc + "[90m";',
        'sp = player.w_sp; spcap = player.w_sp_cap;',
        'learned = player.w_learned;',
        'player:tell(bold + "=== SKILLS  [SP: " + tostr(sp) + "/" + tostr(spcap) + "] ===" + reset);',
        'player:tell("  learn <name>   forget <name>  (forget refunds 75%)");',
        'player:tell("");',
    ]
    for cat_name, cat_skills in cats:
        lines.append(f'player:tell("  {cat_name}");')
        for sname in cat_skills:
            if sname not in skill_map:
                continue
            sk = skill_map[sname]
            cost = sk[1]
            desc = sk[3][:42]
            sname_lit = f'"{sname}"'
            cost_str = f'({cost}sp)'
            # MOO: check if skill is learned, show [X] or [ ]
            lines.append(
                f'player:tell(({sname_lit} in learned ? "  [X] " | "  [ ] ") + '
                f'yel + {moo_str(f"{sname:<24s}")} + reset + '
                f'dim + {moo_str(f"{cost_str:<8s}")} + reset + '
                f'" " + {moo_str(desc)});'
            )
        lines.append('player:tell("");')
    program_verb(s, PLAYER, 'skills', lines)

    print('\n[LEARN] (fix ownership + reprogram)')
    # Ensure learn verb is wizard-owned (not parent class #29)
    send(s, f'; set_verb_info(#{PLAYER}, "learn", {{#{PLAYER}.owner, "rxd", "learn"}})', wait=0.6)
    program_verb(s, PLAYER, 'learn', [
        '"Spend SP to learn a skill. Usage: learn <skill_name>";',
        'skill = dobjstr;',
        'if (skill == "")',
        '  player:tell("Learn what? Type SKILLS to see the list.");',
        '  return;',
        'endif',
        *skill_defs_lines(SKILLS),
        'found = 0; cost = 0; prereq = ""; desc = ""; bprop = ""; bamt = 0;',
        'for def in (skill_defs)',
        '  if (def[1] == skill)',
        '    found = 1; cost = def[2]; prereq = def[3];',
        '    desc = def[4]; bprop = def[5]; bamt = def[6];',
        '    break;',
        '  endif',
        'endfor',
        'if (!found)',
        '  player:tell("Unknown skill: " + skill + ". Type SKILLS for the list.");',
        '  return;',
        'endif',
        'learned = player.w_learned;',
        'if (skill in learned)',
        '  player:tell("You already know " + skill + ".");',
        '  return;',
        'endif',
        'if (prereq != "" && !(prereq in learned))',
        '  player:tell("Requires " + prereq + " first.");',
        '  return;',
        'endif',
        'if (player.w_sp < cost)',
        '  player:tell("Not enough SP. Need " + tostr(cost) + ", have " + tostr(player.w_sp) + ".");',
        '  return;',
        'endif',
        'player.w_sp = player.w_sp - cost;',
        'player.w_learned = listappend(learned, skill);',
        'if (bprop == "w_hp_max")',
        '  player.w_hp_max = player.w_hp_max + bamt;',
        '  player.w_hp = player.w_hp + bamt;',
        'elseif (bprop == "w_stam_max")',
        '  player.w_stam_max = player.w_stam_max + bamt;',
        'elseif (bprop == "w_clar_max")',
        '  player.w_clar_max = player.w_clar_max + bamt;',
        'elseif (bprop == "w_agg_max")',
        '  player.w_agg_max = player.w_agg_max + bamt;',
        'endif',
        'player:tell("You learn: " + desc);',
        'player:tell("[SP remaining: " + tostr(player.w_sp) + "]");',
    ])

    print('\n[FORGET]')
    add_verb(s, PLAYER, 'forget', 'any none none')
    program_verb(s, PLAYER, 'forget', [
        '"Forget a skill for 75% SP refund. Usage: forget <skill_name>";',
        'skill = dobjstr;',
        'if (skill == "")',
        '  player:tell("Forget what skill?");',
        '  return;',
        'endif',
        'learned = player.w_learned;',
        'idx = 0; found = 0;',
        'for i in [1..length(learned)]',
        '  if (learned[i] == skill)',
        '    idx = i; found = 1; break;',
        '  endif',
        'endfor',
        'if (!found)',
        '  player:tell("You don\'t know " + skill + ".");',
        '  return;',
        'endif',
        *skill_defs_lines(SKILLS),
        'cost = 0; bprop = ""; bamt = 0;',
        'for def in (skill_defs)',
        '  if (def[1] == skill)',
        '    cost = def[2]; bprop = def[5]; bamt = def[6]; break;',
        '  endif',
        'endfor',
        'refund = (cost * 3) / 4;',
        'player.w_learned = listdelete(learned, idx);',
        'player.w_sp = min(player.w_sp + refund, player.w_sp_cap);',
        'if (bprop == "w_hp_max")',
        '  player.w_hp_max = player.w_hp_max - bamt;',
        '  player.w_hp = min(player.w_hp, player.w_hp_max);',
        'elseif (bprop == "w_stam_max")',
        '  player.w_stam_max = max(1, player.w_stam_max - bamt);',
        '  player.w_stam = min(player.w_stam, player.w_stam_max);',
        'elseif (bprop == "w_clar_max")',
        '  player.w_clar_max = max(1, player.w_clar_max - bamt);',
        '  player.w_clar = min(player.w_clar, player.w_clar_max);',
        'elseif (bprop == "w_agg_max")',
        '  player.w_agg_max = max(1, player.w_agg_max - bamt);',
        '  player.w_agg = min(player.w_agg, player.w_agg_max);',
        'endif',
        'player:tell("You forget " + skill + ". Refunded " + tostr(refund) + " SP. [SP: " + tostr(player.w_sp) + "]");',
    ])


# ─────────────────────────────────────────────────────────────────────────────
# CAC: SELL and PRICES
# ─────────────────────────────────────────────────────────────────────────────

CAC_PRICES = [
    ('inert metal',        2),
    ('ore',                2),
    ('solid-phase metal',  5),
    ('responsive metal',  10),
    ('transuranic metal', 20),
    ('native fiber',       1),
    ('native lumber',      2),
    ('native fungus',      1),
    ('native berries',     1),
    ('native tubers',      1),
    ('solar kretherson',   3),
    ('thermal kretherson', 3),
    ('kretherson',         2),
    ('any energy',         2),
    ('unpurified water',   1),
    ('water',              1),
    ('sand',               1),
    ('ceramic geode',     15),
    ('magneto-mineral',   12),
    ('gems',              20),
]


def add_cac(s):
    print('\n[SELL]')
    add_verb(s, CAC, 'sell', 'any none none')
    prices_moo = '{' + ', '.join(f'{{{moo_str(k)}, {v}}}' for k, v in CAC_PRICES) + '}'
    program_verb(s, CAC, 'sell', [
        '"Sell a resource to the CAC.";',
        'if (!valid(dobj))',
        '  player:tell("Sell what? (e.g. sell ore)");',
        '  return;',
        'endif',
        'if (dobj.location != player)',
        '  player:tell("You don\'t have that.");',
        '  return;',
        'endif',
        f'prices = {prices_moo};',
        'iname = dobj.name;',
        'price = 0;',
        'for entry in (prices)',
        '  if (index(iname, entry[1]))',
        '    price = entry[2]; break;',
        '  endif',
        'endfor',
        'if (price == 0)',
        '  player:tell("The CAC doesn\'t buy that. Type PRICES to see what sells.");',
        '  return;',
        'endif',
        'player.w_credits = player.w_credits + price;',
        'player.w_sp = min(player.w_sp + 1, player.w_sp_cap);',
        'player.w_sp_earned = player.w_sp_earned + 1;',
        'recycle(dobj);',
        'player:tell("CAC buys " + iname + " for " + tostr(price) + " credits. [Balance: " + tostr(player.w_credits) + "cr | SP: " + tostr(player.w_sp) + "]");',
    ])

    print('\n[PRICES]')
    add_verb(s, CAC, 'prices', 'none none none')
    price_lines = [
        '"Show CAC buy prices.";',
        'esc = chr(27); bold = esc + "[1m"; reset = esc + "[0m";',
        'player:tell(bold + "=== CAC RESOURCE PRICES ===" + reset);',
    ]
    for name, price in CAC_PRICES:
        price_lines.append(f'player:tell("  {name:<26s}  {price} cr");')
    price_lines += [
        'player:tell("");',
        'player:tell("Use: sell <item>  (must be in your inventory)");',
    ]
    program_verb(s, CAC, 'prices', price_lines)


# ─────────────────────────────────────────────────────────────────────────────
# Dispatch Bay: DISPATCH
# ─────────────────────────────────────────────────────────────────────────────

def add_dispatch(s):
    print('\n[DISPATCH]')
    add_verb(s, DISPATCH, 'dispatch', 'none none none')
    program_verb(s, DISPATCH, 'dispatch', [
        '"Launch player to Kepler-7 surface.";',
        'landing = $ods:spawn_room($kepler7, 0, 0);',
        'if (!valid(landing))',
        '  player:tell("Dispatch malfunction -- launch aborted.");',
        '  return;',
        'endif',
        'player:tell("Launch confirmed. Strap in.");',
        'player:tell("The pod accelerates -- 3g, 5g, 8g -- Kepler-7 fills the viewport.");',
        'player:tell("Impact. You are on the surface of Kepler-7.");',
        'move(player, landing);',
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Heartbeat: dice regen
# ─────────────────────────────────────────────────────────────────────────────

def add_regen(s):
    print('\n[_wayfar_regen]')
    add_verb(s, PLAYER, '_wayfar_regen', 'this none none')
    program_verb(s, PLAYER, '_wayfar_regen', [
        '"Regen Wayfar dice pools each heartbeat.";',
        'if (player.w_stam < player.w_stam_max)',
        '  player.w_stam = player.w_stam + 1;',
        'endif',
        'if (player.w_clar < player.w_clar_max)',
        '  player.w_clar = player.w_clar + 1;',
        'endif',
        'if (player.w_agg < player.w_agg_max)',
        '  player.w_agg = player.w_agg + 1;',
        'endif',
        'if (player.w_nourished > time())',
        '  if (player.w_stam < player.w_stam_max)',
        '    player.w_stam = player.w_stam + 1;',
        '  endif',
        '  if (player.w_hp < player.w_hp_max)',
        '    player.w_hp = player.w_hp + 2;',
        '  endif',
        'endif',
    ])

    print('\n[heartbeat override]')
    program_verb(s, PLAYER, 'heartbeat', [
        'r = pass(@args);',
        'this:change_temperature();',
        'if (is_connected(this))',
        '  this:_wayfar_regen();',
        '  if (idle_seconds(this) > 300 && this.posture == "standing" && !this.executing)',
        '    this.location:idle_sit(this);',
        '  endif',
        'elseif (time() - this.last_connect_time > 300 || time() < this.last_connect_time)',
        '  $heart:unregister(this);',
        '  if (random(100) < 3 && is_a(area(this), $real_area))',
        '    this:aat(this:dnamec(), " snores softly.");',
        '  endif',
        'endif',
        'return r;',
    ])


# ─────────────────────────────────────────────────────────────────────────────
# EAT override — Nourished effect
# ─────────────────────────────────────────────────────────────────────────────

def add_eat(s):
    print('\n[eat override]')
    program_verb(s, PLAYER, 'eat', [
        '"Eat food. Grants Nourished effect (better dice regen).";',
        'if (!valid(dobj))',
        '  player:tell("Eat what?");',
        '  return;',
        'endif',
        'if (dobj.location != player)',
        '  player:tell("You don\'t have that.");',
        '  return;',
        'endif',
        'fname = dobj.name;',
        'edible = 0;',
        'for kw in ({"berry", "berries", "fungus", "tuber", "soup", "ration", "food", "snack", "fruit", "meat", "pie", "paste", "donut", "slush", "vita"})',
        '  if (index(fname, kw))',
        '    edible = 1; break;',
        '  endif',
        'endfor',
        'if (!edible && "is_food" in properties(dobj))',
        '  edible = dobj.is_food;',
        'endif',
        'if (!edible)',
        '  player:tell("That doesn\'t look edible.");',
        '  return;',
        'endif',
        'player.w_nourished = time() + 600;',
        'heal = 5;',
        'player.w_hp = min(player.w_hp + heal, player.w_hp_max);',
        'recycle(dobj);',
        'player:tell("You eat the " + fname + ". [+" + tostr(heal) + " HP | Nourished for 10 min]");',
        'player.location:announce(player.name + " eats.", player);',
    ])


# ─────────────────────────────────────────────────────────────────────────────
# GATHER update — awards SP
# ─────────────────────────────────────────────────────────────────────────────

def update_gather(s):
    print('\n[gather update]')
    program_verb(s, WROOM, 'gather', [
        '"Gather resources from this wilderness room.";',
        'nodelist = {};',
        'for itm in (player.location.contents)',
        '  if (itm != player && "is_node" in properties(itm) && itm.is_node == 1)',
        '    nodelist = listappend(nodelist, itm);',
        '  endif',
        'endfor',
        'if (dobjstr == "" || dobjstr == "list")',
        '  if (length(nodelist) == 0)',
        '    player:tell("Nothing to gather here.");',
        '    return;',
        '  endif',
        '  player:tell("Resources here:");',
        '  for rn in (nodelist)',
        '    player:tell("  " + rn.name + " (" + tostr(rn.count) + " remaining)");',
        '  endfor',
        '  return;',
        'endif',
        'mined = 0;',
        'for rn in (nodelist)',
        '  if (index(rn.name, dobjstr))',
        '    if (rn.count <= 0)',
        '      player:tell("That deposit is exhausted.");',
        '      mined = 1; break;',
        '    endif',
        '    itm = create($thing);',
        '    itm.name = rn.yield_name;',
        '    itm.description = rn.yield_desc;',
        '    move(itm, player);',
        '    rn.count = rn.count - 1;',
        '    player.w_sp = min(player.w_sp + 2, player.w_sp_cap);',
        '    player.w_sp_earned = player.w_sp_earned + 2;',
        '    player:tell("You gather some " + itm.name + ". [" + tostr(rn.count) + "/" + tostr(rn.max_count) + " left] [+2 SP]");',
        '    player.location:announce(player.name + " gathers resources.", player);',
        '    mined = 1; break;',
        '  endif',
        'endfor',
        'if (!mined)',
        '  player:tell("No " + dobjstr + " here. Type gather (no args) to list.");',
        'endif',
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Diagonal movement
# ─────────────────────────────────────────────────────────────────────────────

def add_diagonals(s):
    print('\n[diagonal movement]')
    for direction, dx, dy in [('ne', 1, 1), ('se', 1, -1), ('sw', -1, -1), ('nw', -1, 1)]:
        add_verb(s, PLAYER, direction, 'none none none')
        program_verb(s, PLAYER, direction, [
            f'"Move {direction}.";',
            'loc = player.location;',
            'if (!("x" in properties(loc)))',
            f'  player:tell("Can\'t go {direction} from here.");',
            '  return;',
            'endif',
            f'nx = loc.x + ({dx}); ny = loc.y + ({dy});',
            'newroom = $ods:spawn_room(loc.planet, nx, ny);',
            'if (!valid(newroom))',
            f'  player:tell("Can\'t go {direction}.");',
            '  return;',
            'endif',
            'move(player, newroom);',
        ])


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print('Connecting...')
    s = connect()
    print('Connected.')

    add_st(s)
    add_combat(s)
    add_skills(s)
    add_cac(s)
    add_dispatch(s)
    add_regen(s)
    add_eat(s)
    update_gather(s)
    add_diagonals(s)

    print('\n[Saving DB]')
    send(s, '@dump-database', wait=3.0)
    print('Saved.')

    print('\n=== Done! ===')
    print('Test in game:  st / skills / kill / swing / fire / dispatch')
    s.close()


if __name__ == '__main__':
    main()
