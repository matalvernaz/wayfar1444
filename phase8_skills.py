#!/usr/bin/env python3
"""
Wayfar 1444 — Phase 8: Skill System (Redesign C)

Adds:
  1. Skill shop: 'skills' verb shows known + purchasable skills
  2. 'buy skill <name>' verb — deducts credits, adds to w_learned list
  3. Tier 1 skills (50 cr each):
       gathering_1  — Expert Forager: gather verb bonus (placeholder)
       crafting_1   — Field Fabricator: additional craft recipes (WIP)
       survival_1   — Field Medicine: eat/drink heals +3 HP more
       commerce_1   — Trade Contacts: sell prices +1 cr per item
       combat_1     — Combat Training: +5 HP max (applied immediately)
  4. Tier 2 skills (200 cr, requires Tier 1):
       gathering_2  — Resource Expert: guaranteed bonus gather (requires gathering_1)
       survival_2   — Combat Medic: treat heals full HP (requires survival_1)
       commerce_2   — CAC Partnership: ore/salvage prices x2 (requires commerce_1)
  5. Wire survival_1 effect into eat verb (+3 HP if known)
  6. Wire commerce_1/commerce_2 effects into sell verb (+1 cr / ore+salvage x2)

Run with server live: python3 phase8_skills.py
"""

import socket, time, re, sys
sys.path.insert(0, '/home/matt/wayfar')

HOST = 'localhost'
PORT = 7777
PLAYER = 6
BCT_NUM = 592


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
# skills verb — show known skills and what's available to buy
# ─────────────────────────────────────────────────────────────────────────────

SKILLS_VERB = [
    '"Show known skills and purchasable skills.";',
    'p = player;',
    'known = p.w_learned;',
    'p:tell("=== SKILLS === (" + tostr(p.w_credits) + " cr available)");',
    '"Tier 1 — 50 cr each";',
    'p:tell("Tier 1 (50 cr):");',
    'for sk in ({"gathering_1", "crafting_1", "survival_1", "commerce_1", "combat_1"})',
    '  tag = (sk in known) ? "[known]" | "[buy]";',
    '  if (sk == "gathering_1")',
    '    p:tell("  " + tag + " gathering_1   Expert Forager: gather yields bonus items");',
    '  elseif (sk == "crafting_1")',
    '    p:tell("  " + tag + " crafting_1    Field Fabricator: additional craft recipes");',
    '  elseif (sk == "survival_1")',
    '    p:tell("  " + tag + " survival_1    Field Medicine: eat/drink heals +3 HP");',
    '  elseif (sk == "commerce_1")',
    '    p:tell("  " + tag + " commerce_1    Trade Contacts: sell prices +1 cr each");',
    '  elseif (sk == "combat_1")',
    '    p:tell("  " + tag + " combat_1      Combat Training: +5 HP max");',
    '  endif',
    'endfor',
    '"Tier 2 — 200 cr, requires Tier 1";',
    'p:tell("Tier 2 (200 cr, requires Tier 1):");',
    'for sk in ({"gathering_2", "survival_2", "commerce_2"})',
    '  tag = (sk in known) ? "[known]" | "[buy]";',
    '  if (sk == "gathering_2")',
    '    req = ("gathering_1" in known) ? "" | " [requires gathering_1]";',
    '    p:tell("  " + tag + " gathering_2   Resource Expert: guaranteed bonus gather" + req);',
    '  elseif (sk == "survival_2")',
    '    req = ("survival_1" in known) ? "" | " [requires survival_1]";',
    '    p:tell("  " + tag + " survival_2    Combat Medic: treat verb heals full HP" + req);',
    '  elseif (sk == "commerce_2")',
    '    req = ("commerce_1" in known) ? "" | " [requires commerce_1]";',
    '    p:tell("  " + tag + " commerce_2    CAC Partnership: ore/salvage prices x2" + req);',
    '  endif',
    'endfor',
    'p:tell("Usage: buy skill <name>  (e.g. buy skill survival_1)");',
]


# ─────────────────────────────────────────────────────────────────────────────
# buy skill verb
# ─────────────────────────────────────────────────────────────────────────────

BUY_SKILL_VERB = [
    '"Purchase a skill with credits. Usage: buy skill <name>";',
    'p = player;',
    '"Build skill name from args";',
    'sk = (typeof(dobjstr) == STR) ? dobjstr | "";',
    'if (sk == "" && args != {})',
    '  for w in (args)',
    '    if (typeof(w) == STR)',
    '      sk = sk == "" ? w | sk + "_" + w;',
    '    endif',
    '  endfor',
    'endif',
    '"Strip leading \'skill \' prefix if typed";',
    'if (index(sk, "skill ") == 1)',
    '  sk = strsub(sk, "skill ", "");',
    'endif',
    'if (sk == "")',
    '  p:tell("Buy what skill? (Type \'skills\' to see options)");',
    '  return;',
    'endif',
    '"Normalize: replace spaces with underscores";',
    'sk = strsub(sk, " ", "_");',
    '"Validate skill name and get cost";',
    'tier1 = {"gathering_1", "crafting_1", "survival_1", "commerce_1", "combat_1"};',
    'tier2 = {"gathering_2", "survival_2", "commerce_2"};',
    'cost = 0;',
    'req = "";',
    'if (sk in tier1)',
    '  cost = 50;',
    'elseif (sk in tier2)',
    '  cost = 200;',
    '  if (sk == "gathering_2") req = "gathering_1";',
    '  elseif (sk == "survival_2") req = "survival_1";',
    '  elseif (sk == "commerce_2") req = "commerce_1";',
    '  endif',
    'else',
    '  p:tell("Unknown skill: \'" + sk + "\'. Type \'skills\' to see options.");',
    '  return;',
    'endif',
    '"Check already known";',
    'if (sk in p.w_learned)',
    '  p:tell("You already know " + sk + ".");',
    '  return;',
    'endif',
    '"Check prerequisite";',
    'if (req != "" && !(req in p.w_learned))',
    '  p:tell("Requires " + req + " first.");',
    '  return;',
    'endif',
    '"Check credits";',
    'if (p.w_credits < cost)',
    '  p:tell("Not enough credits. Need " + tostr(cost) + " cr, have " + tostr(p.w_credits) + " cr.");',
    '  return;',
    'endif',
    '"Purchase";',
    'p.w_credits = p.w_credits - cost;',
    'p.w_learned = listappend(p.w_learned, sk);',
    '"Apply immediate effects";',
    'if (sk == "combat_1")',
    '  p.w_hp_max = p.w_hp_max + 5;',
    '  p.w_hp = min(p.w_hp + 5, p.w_hp_max);',
    '  p:tell("Skill learned: " + sk + ". [HP max +5]  Balance: " + tostr(p.w_credits) + " cr");',
    'else',
    '  p:tell("Skill learned: " + sk + ".  Balance: " + tostr(p.w_credits) + " cr");',
    'endif',
]


# ─────────────────────────────────────────────────────────────────────────────
# Updated eat verb — survival_1 grants +3 HP bonus
# ─────────────────────────────────────────────────────────────────────────────

EAT_VERB_V2 = [
    '"Eat food. Grants Nourished effect (+HP, better dice regen).";',
    '"Works via command (eat <item>) or programmatic call (this:eat(args)).";',
    'found = 0;',
    'if (valid(dobj) && dobj.location == player)',
    '  found = dobj;',
    'else',
    '  query = (typeof(dobjstr) == STR) ? dobjstr | "";',
    '  if (query == "" && args != {})',
    '    for w in (args)',
    '      if (typeof(w) == STR)',
    '        query = query == "" ? w | query + " " + w;',
    '      endif',
    '    endfor',
    '  endif',
    '  if (query == "")',
    '    player:tell("Eat what? (Type i to see inventory)");',
    '    return;',
    '  endif',
    '  for itm in (player.contents)',
    '    nm = "";',
    '    try',
    '      nm = tostr(itm.name);',
    '    except e (ANY)',
    '      nm = "";',
    '    endtry',
    '    if (index(nm, query))',
    '      found = itm;',
    '      break;',
    '    endif',
    '  endfor',
    'endif',
    'if (found == 0)',
    '  player:tell("You are not carrying that.");',
    '  return;',
    'endif',
    'fname = "";',
    'try fname = tostr(found.name); except e (ANY) fname = ""; endtry',
    'edible = 0;',
    'for kw in ({"berry", "berries", "fungus", "tuber", "soup", "ration", "food", "snack", "fruit", "meat", "pie", "paste", "donut", "slush", "vita", "canteen", "water"})',
    '  if (index(fname, kw))',
    '    edible = 1;',
    '    break;',
    '  endif',
    'endfor',
    'if (!edible && "is_food" in properties(found))',
    '  edible = found.is_food;',
    'endif',
    'if (!edible)',
    '  player:tell("That doesn\'t look edible.");',
    '  return;',
    'endif',
    'player.w_nourished = time() + 600;',
    'heal = 5;',
    'if (index(fname, "canteen") || index(fname, "water"))',
    '  heal = 3;',
    'endif',
    '"survival_1 bonus: +3 HP on eat/drink";',
    'if ("survival_1" in player.w_learned)',
    '  heal = heal + 3;',
    'endif',
    'player.w_hp = min(player.w_hp + heal, player.w_hp_max);',
    'recycle(found);',
    'player:tell("You consume the " + fname + ". [+" + tostr(heal) + " HP | Nourished for 10 min]");',
    'player.location:announce(player.name + " eats.", player);',
]


# ─────────────────────────────────────────────────────────────────────────────
# Updated sell verb — commerce_1 (+1 cr/item), commerce_2 (ore/salvage x2)
# Also scavenger bonus retained
# ─────────────────────────────────────────────────────────────────────────────

SELL_VERB_V3 = [
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
    '    try nm = tostr(itm.name); except e (ANY) nm = ""; endtry',
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
    'has_com1 = ("commerce_1" in p.w_learned);',
    'has_com2 = ("commerce_2" in p.w_learned);',
    'total = 0; sold = 0;',
    'for itm in (sell_list)',
    '  nm = "";',
    '  try nm = tostr(itm.name); except e (ANY) nm = ""; endtry',
    '  price = 0;',
    '  if (index(nm, "ore") || index(nm, "mineral"))',
    '    price = has_com2 ? 10 | 5;',
    '  elseif (index(nm, "fiber") || index(nm, "plant"))',
    '    price = 3;',
    '  elseif (index(nm, "water sample") || index(nm, "raw water"))',
    '    price = 2;',
    '  elseif (index(nm, "salvage") || index(nm, "scrap") || index(nm, "wreckage"))',
    '    base = is_scav ? 6 | 4;',
    '    price = has_com2 ? (base * 2) | base;',
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
    '    if (has_com1) price = price + 1; endif',
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


def main():
    s = connect()

    # ── 1. Add w_skills_xp property (placeholder for future SP earn) ──────────
    print('=== Ensure w_learned is proper list ===')
    out = ev(s, 'player:tell(typeof(player.w_learned))', wait=0.7)
    print(f'  typeof w_learned: {out.strip()[-20:]}')
    # 4 = LIST in MOO type system
    out = ev(s, 'player:tell(player.w_learned == {} ? "empty" | "has items")', wait=0.7)
    print(f'  w_learned content: {out.strip()[-30:]}')

    # ── 2. skills verb ────────────────────────────────────────────────────────
    print('\n=== skills verb on $player ===')
    add_verb(s, f'#{PLAYER}', '"skills"', 'none none none')
    program_verb(s, f'#{PLAYER}', 'skills', SKILLS_VERB)

    # ── 3. buy skill verb ─────────────────────────────────────────────────────
    print('\n=== buy skill verb on $player ===')
    # 'buy' needs to handle 'buy skill <name>' or just 'buy <name>'
    # Use "buy" as the verb name with any args
    add_verb(s, f'#{PLAYER}', '"buy"', 'any none none')
    program_verb(s, f'#{PLAYER}', 'buy', BUY_SKILL_VERB)

    # ── 4. Updated eat verb ───────────────────────────────────────────────────
    print('\n=== Update eat verb (survival_1 bonus) ===')
    program_verb(s, f'#{PLAYER}', 'eat', EAT_VERB_V2)

    # ── 5. Updated sell verb ──────────────────────────────────────────────────
    print('\n=== Update sell verb (commerce_1/2 bonuses) ===')
    program_verb(s, f'#{PLAYER}', 'sell', SELL_VERB_V3)

    # ── 6. Test ───────────────────────────────────────────────────────────────
    print('\n=== Test skill system ===')
    add_verb(s, f'#{PLAYER}', '"skill_test"', 'none none none')
    program_verb(s, f'#{PLAYER}', 'skill_test', [
        '"Test skill purchase and effects.";',
        'player:tell("=== SKILL_TEST BEGIN ===");',
        '"Reset state";',
        'player.w_learned = {};',
        'player.w_credits = 200;',
        'player.w_hp = 80; player.w_hp_max = 100;',
        'player.w_background = "colonist";',
        '"Show skills menu";',
        'this:skills();',
        'player:tell("---");',
        '"Buy survival_1 (50 cr)";',
        'this:buy("survival_1");',
        'player:tell("  After buy: credits=" + tostr(player.w_credits) + " learned=" + tostr(player.w_learned));',
        '"Try to buy same skill again";',
        'this:buy("survival_1");',
        '"Try tier2 without prereq";',
        'this:buy("commerce_2");',
        '"Buy commerce_1 (50 cr)";',
        'this:buy("commerce_1");',
        '"Buy combat_1 (50 cr) — immediate hp bonus";',
        'player:tell("  hp_max before combat_1: " + tostr(player.w_hp_max));',
        'this:buy("combat_1");',
        'player:tell("  hp_max after combat_1: " + tostr(player.w_hp_max) + " (expect +5)");',
        '"Test eat with survival_1";',
        'rb = create($thing); rb.name = "ration bar"; move(rb, player);',
        'old_hp = player.w_hp;',
        'this:eat("ration bar");',
        'player:tell("  eat with survival_1: +" + tostr(player.w_hp - old_hp) + " HP (expect 8)");',
        '"Test sell with commerce_1 (+1 bonus)";',
        'o1 = create($thing); o1.name = "ore chunk"; move(o1, player);',
        'player.w_credits = 0;',
        'this:sell("ore");',
        'player:tell("  ore with commerce_1: " + tostr(player.w_credits) + " cr (expect 6)");',
        '"Cleanup";',
        'player.w_learned = {};',
        'player.w_credits = 0;',
        'player:tell("=== SKILL_TEST END ===");',
    ])
    out = send(s, 'skill_test', wait=12.0)
    print(out.strip())

    # ── 7. Save ───────────────────────────────────────────────────────────────
    out = send(s, '@dump-database', wait=3.0)
    print(f'Save: {out.strip()[:60]}')
    s.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
