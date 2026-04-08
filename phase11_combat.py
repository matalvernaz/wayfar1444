#!/usr/bin/env python3
"""
Wayfar 1444 — Phase 11: Dice Pool Combat (Redesign F)

Adds:
  1. Dice pool stats on $player: w_stam/w_stam_max, w_clarity/w_clarity_max,
     w_aggression/w_aggression_max (default 3/3/3 each)
  2. Dice regen in #545:tick (1 per die type per tick, up to max)
  3. Updated ST/status to show dice pools
  4. $creature prototype (#0.creature) — hp, hp_max, cr_stam, cr_aggr, cr_name
  5. Creature spawning: $ods:populate drops 0-1 creature per room
  6. KILL <target> — set w_target on player
  7. SWING — melee: spend 1 stam die, roll to hit (1d6 >= 3), on hit spend aggression dice
  8. FIRE  — ranged: spend 1 clarity die, same hit mechanic
  9. TAC   — list all entities in room with HP
  10. CON <target> — consider: compare stats
  11. Creature retaliation: strikes back immediately when hit (spends its own dice)
  12. Creature death: announces, drops salvage scrap, recycles
  13. Player death from combat: respawn at #459 with partial stats

Run with server live: python3 phase11_combat.py
"""

import socket, time, re, sys

HOST = 'localhost'
PORT = 7777
PLAYER = 6       # $player / generic player
HEARTBEAT = 545
ODS = 458        # $ods (on-demand spawner)
RESPAWN = 459    # Impact Site Zero

def connect():
    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(5)
    time.sleep(0.5); s.recv(65536)
    s.sendall(b'connect wizard\r\n')
    time.sleep(0.8); s.recv(65536)
    return s

def send(s, cmd, wait=0.7):
    s.sendall((cmd + '\r\n').encode())
    time.sleep(wait)
    out = b''
    deadline = time.time() + max(wait + 0.3, 0.4)
    try:
        while time.time() < deadline:
            chunk = s.recv(65536)
            if not chunk: break
            out += chunk
    except: pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))

def ev(s, expr, wait=0.7): return send(s, '; ' + expr, wait)

def program_verb(s, obj, name, lines, wait_compile=4.0):
    out = send(s, f'@program {obj}:{name}', wait=1.5)
    if 'programming' not in out.lower():
        print(f'  ERROR @program {obj}:{name}: {repr(out[:150])}')
        return False
    old = s.gettimeout(); s.settimeout(0.3)
    for i, line in enumerate(lines):
        send(s, line, wait=0.06)
        if i % 20 == 19: print(f'    ...{i+1}/{len(lines)}')
    s.settimeout(old)
    result = send(s, '.', wait=wait_compile)
    if re.search(r'[1-9]\d* error', result):
        print(f'  CODE ERROR {obj}:{name}:\n{result[:400]}')
        return False
    print(f'  OK: {obj}:{name}')
    return True

def add_verb(s, obj, name, args='none none none'):
    out = send(s, f'@verb {obj}:"{name}" {args}', wait=0.6)
    if 'Verb added' not in out and 'already defined' not in out.lower():
        # Try without quotes
        out2 = send(s, f'@verb {obj}:{name} {args}', wait=0.6)
        if 'Verb added' not in out2 and 'already defined' not in out2.lower():
            print(f'  WARN @verb {obj}:{name}: {repr(out[:80])}')


# ─────────────────────────────────────────────────────────────────────────────
# KILL verb — set combat target
# ─────────────────────────────────────────────────────────────────────────────
KILL_VERB = [
    '"Set combat target. Usage: kill <creature>. Sets w_target on player.";',
    'p = player;',
    'target = 0;',
    '"Find target in room by name";',
    'tstr = (typeof(dobjstr) == STR && dobjstr != "") ? dobjstr | "";',
    'if (tstr == "")',
    '  p:tell("Kill what? Usage: kill <target>");',
    '  return;',
    'endif',
    'for obj in (p.location.contents)',
    '  if (obj != p && is_a(obj, $creature) && index(obj.name, tstr) != 0)',
    '    target = obj;',
    '    break;',
    '  endif',
    'endfor',
    'if (target == 0)',
    '  p:tell("You don\'t see any " + tstr + " here.");',
    '  return;',
    'endif',
    'p.w_target = target;',
    'p:tell("You focus on the " + target.name + ". [HP: " + tostr(target.cr_hp) + "/" + tostr(target.cr_hp_max) + "]");',
    'p:tell("Use SWING (melee) or FIRE (ranged) to attack.");',
]

# ─────────────────────────────────────────────────────────────────────────────
# SWING verb — melee attack
# ─────────────────────────────────────────────────────────────────────────────
SWING_VERB = [
    '"Melee attack. Spends 1 stamina die. Rolls d6 >= 3 to hit. Damage = d6 per aggression die spent.";',
    'p = player;',
    '"Validate target";',
    'if (!("w_target" in properties(p)) || !valid(p.w_target))',
    '  p:tell("No target set. Use: kill <creature>");',
    '  return;',
    'endif',
    'target = p.w_target;',
    'if (target.location != p.location)',
    '  p:tell("Your target is no longer here.");',
    '  p.w_target = $nothing;',
    '  return;',
    'endif',
    '"Check stamina dice";',
    'if (p.w_stam < 1)',
    '  p:tell("No stamina dice remaining. Rest or wait for them to recover.");',
    '  return;',
    'endif',
    '"Spend 1 stamina die and roll to hit (1d6, hit on 3+)";',
    'p.w_stam = p.w_stam - 1;',
    'hit_roll = random(6);',
    'if (hit_roll < 3)',
    '  p:tell("[MISS] You swing at the " + target.name + " but miss! (rolled " + tostr(hit_roll) + ")");',
    '  p.location:announce(p.name + " swings at the " + target.name + " and misses.", p);',
    'else',
    '  "Hit — spend aggression dice for damage";',
    '  dmg = 0;',
    '  dice_spent = p.w_aggression;',
    '  for i in [1..dice_spent]',
    '    dmg = dmg + random(6);',
    '  endfor',
    '  p.w_aggression = 0;',
    '  target.cr_hp = target.cr_hp - dmg;',
    '  p:tell("[HIT] You strike the " + target.name + " for " + tostr(dmg) + " damage! (rolled " + tostr(hit_roll) + ")");',
    '  p.location:announce(p.name + " strikes the " + target.name + " for " + tostr(dmg) + " damage!", p);',
    '  "Creature retaliation";',
    '  this:cr_retaliate(target);',
    '  "Check creature death";',
    '  if (target.cr_hp <= 0)',
    '    this:cr_die(target);',
    '  endif',
    'endif',
    '"Show updated status";',
    'p:tell("[ST] HP:" + tostr(p.health) + " STM:" + tostr(p.w_stam) + "/" + tostr(p.w_stam_max) + " AGG:" + tostr(p.w_aggression) + "/" + tostr(p.w_aggression_max));',
]

# ─────────────────────────────────────────────────────────────────────────────
# FIRE verb — ranged attack (clarity dice)
# ─────────────────────────────────────────────────────────────────────────────
FIRE_VERB = [
    '"Ranged attack. Spends 1 clarity die. Rolls d6 >= 3 to hit. Damage = d6 per aggression die.";',
    'p = player;',
    'if (!("w_target" in properties(p)) || !valid(p.w_target))',
    '  p:tell("No target set. Use: kill <creature>");',
    '  return;',
    'endif',
    'target = p.w_target;',
    'if (target.location != p.location)',
    '  p:tell("Your target is no longer here.");',
    '  p.w_target = $nothing;',
    '  return;',
    'endif',
    'if (p.w_clarity < 1)',
    '  p:tell("No clarity dice remaining. Rest or wait for them to recover.");',
    '  return;',
    'endif',
    'p.w_clarity = p.w_clarity - 1;',
    'hit_roll = random(6);',
    'if (hit_roll < 3)',
    '  p:tell("[MISS] You fire at the " + target.name + " but miss! (rolled " + tostr(hit_roll) + ")");',
    '  p.location:announce(p.name + " fires at the " + target.name + " and misses.", p);',
    'else',
    '  dmg = 0;',
    '  dice_spent = p.w_aggression;',
    '  for i in [1..dice_spent]',
    '    dmg = dmg + random(6);',
    '  endfor',
    '  p.w_aggression = 0;',
    '  target.cr_hp = target.cr_hp - dmg;',
    '  p:tell("[HIT] You shoot the " + target.name + " for " + tostr(dmg) + " damage! (rolled " + tostr(hit_roll) + ")");',
    '  p.location:announce(p.name + " shoots the " + target.name + " for " + tostr(dmg) + " damage!", p);',
    '  this:cr_retaliate(target);',
    '  if (target.cr_hp <= 0)',
    '    this:cr_die(target);',
    '  endif',
    'endif',
    'p:tell("[ST] HP:" + tostr(p.health) + " CLR:" + tostr(p.w_clarity) + "/" + tostr(p.w_clarity_max) + " AGG:" + tostr(p.w_aggression) + "/" + tostr(p.w_aggression_max));',
]

# ─────────────────────────────────────────────────────────────────────────────
# cr_retaliate verb — creature strikes back
# ─────────────────────────────────────────────────────────────────────────────
CR_RETALIATE_VERB = [
    '"Creature strikes back at the player who just hit it.";',
    'p = player;',
    'creature = args[1];',
    'if (!valid(creature) || creature.cr_hp <= 0)',
    '  return;',
    'endif',
    '"Creature rolls its own stamina die";',
    'if (creature.cr_stam < 1)',
    '  p:tell("The " + creature.name + " staggers, too exhausted to retaliate.");',
    '  return;',
    'endif',
    'creature.cr_stam = creature.cr_stam - 1;',
    'hit_roll = random(6);',
    'if (hit_roll < 3)',
    '  p:tell("The " + creature.name + " retaliates but misses you! (rolled " + tostr(hit_roll) + ")");',
    'else',
    '  dmg = 0;',
    '  for i in [1..creature.cr_aggr]',
    '    dmg = dmg + random(6);',
    '  endfor',
    '  p.health = p.health - dmg;',
    '  p:tell("The " + creature.name + " strikes you for " + tostr(dmg) + " damage! [HP: " + tostr(p.health) + "]");',
    '  p.location:announce("The " + creature.name + " strikes " + p.name + " for " + tostr(dmg) + " damage!", p);',
    '  "Player death check";',
    '  if (p.health <= 0)',
    '    p.hunger = 20; p.health = 30; p.stamina = 50;',
    '    p.w_stam = p.w_stam_max; p.w_clarity = p.w_clarity_max; p.w_aggression = p.w_aggression_max;',
    '    p:tell(""); p:tell("*** YOU HAVE DIED ***");',
    '    p:tell("The " + creature.name + " finishes you. You wake at the crash site.");',
    '    p:tell("");',
    '    p.w_target = $nothing;',
    '    move(p, #459);',
    '    p.location:announce(p.name + " staggers back from the brink of death.", p);',
    '  endif',
    'endif',
]

# ─────────────────────────────────────────────────────────────────────────────
# cr_die verb — creature death handler
# ─────────────────────────────────────────────────────────────────────────────
CR_DIE_VERB = [
    '"Handle creature death: announce, drop loot, recycle.";',
    'p = player;',
    'creature = args[1];',
    'if (!valid(creature)) return; endif',
    'loc = creature.location;',
    'p:tell("The " + creature.name + " collapses and dies!");',
    'loc:announce("The " + creature.name + " collapses and dies!", p);',
    '"Drop loot: salvage scrap";',
    'loot = create($thing);',
    'loot.name = "salvage scrap";',
    'loot.description = "Twisted remains salvaged from a dead creature.";',
    'move(loot, loc);',
    'p:tell("The " + creature.name + " drops: salvage scrap");',
    '"Clear target if this was the player\'s target";',
    'if ("w_target" in properties(p) && p.w_target == creature)',
    '  p.w_target = $nothing;',
    'endif',
    '"Remove from creature list and recycle";',
    '$creature_list = setremove($creature_list, creature);',
    'recycle(creature);',
    '"Job: SCHOOL OF HARD KNOCKS handled in death; here just HUNT reward";',
    'p.w_credits = p.w_credits + 5;',
    'p:tell("[+5 cr] Combat kill reward.");',
]

# ─────────────────────────────────────────────────────────────────────────────
# TAC verb — tactical display
# ─────────────────────────────────────────────────────────────────────────────
TAC_VERB = [
    '"Tactical display: show HP of all entities in room.";',
    'p = player;',
    'p:tell("=== TACTICAL ===");',
    'p:tell("  [YOU] " + p.name + "  HP: " + tostr(p.health) + "  STM:" + tostr(p.w_stam) + "/" + tostr(p.w_stam_max) + "  CLR:" + tostr(p.w_clarity) + "/" + tostr(p.w_clarity_max) + "  AGG:" + tostr(p.w_aggression) + "/" + tostr(p.w_aggression_max));',
    'for obj in (p.location.contents)',
    '  if (obj != p && is_a(obj, $creature))',
    '    bar = "";',
    '    pct = (obj.cr_hp * 10) / obj.cr_hp_max;',
    '    for i in [1..10]',
    '      if (i <= pct) bar = bar + "#"; else bar = bar + "."; endif',
    '    endfor',
    '    p:tell("  [" + obj.name + "]  HP: " + tostr(obj.cr_hp) + "/" + tostr(obj.cr_hp_max) + "  [" + bar + "]");',
    '  endif',
    'endfor',
]

# ─────────────────────────────────────────────────────────────────────────────
# CON verb — consider target
# ─────────────────────────────────────────────────────────────────────────────
CON_VERB = [
    '"Consider a target: compare your combat stats to theirs.";',
    'p = player;',
    'tstr = (typeof(dobjstr) == STR && dobjstr != "") ? dobjstr | "";',
    'target = 0;',
    'for obj in (p.location.contents)',
    '  if (obj != p && is_a(obj, $creature))',
    '    if (tstr == "" || index(obj.name, tstr) != 0)',
    '      target = obj;',
    '      break;',
    '    endif',
    '  endif',
    'endfor',
    'if (target == 0)',
    '  p:tell("Consider what? No creature found.");',
    '  return;',
    'endif',
    'p:tell("You size up the " + target.name + "...");',
    'my_power = p.w_stam_max + p.w_aggression_max;',
    'cr_power = target.cr_stam_max + target.cr_aggr;',
    'if (my_power > cr_power + 2)',
    '  p:tell("  This looks like easy prey.");',
    'elseif (my_power > cr_power)',
    '  p:tell("  You have the edge, but be careful.");',
    'elseif (my_power == cr_power)',
    '  p:tell("  This is an even fight.");',
    'elseif (cr_power > my_power + 2)',
    '  p:tell("  This creature could kill you. Proceed with caution.");',
    'else',
    '  p:tell("  The creature is stronger — be careful.");',
    'endif',
    'p:tell("  Their HP: " + tostr(target.cr_hp) + "/" + tostr(target.cr_hp_max));',
]

# ─────────────────────────────────────────────────────────────────────────────
# Updated ST verb (replaces status — adds dice pools)
# ─────────────────────────────────────────────────────────────────────────────
ST_VERB = [
    '"Personal status: health, hunger, stamina, dice pools.";',
    'p = player;',
    '"Hunger bar";',
    'hbar = "";',
    'hpct = (p.hunger * 10) / 100;',
    'for i in [1..10]',
    '  if (i <= hpct) hbar = hbar + "#"; else hbar = hbar + "."; endif',
    'endfor',
    '"Health bar";',
    'hpbar = "";',
    'hppct = (p.health * 10) / 100;',
    'for i in [1..10]',
    '  if (i <= hppct) hpbar = hpbar + "#"; else hpbar = hpbar + "."; endif',
    'endfor',
    'p:tell("=== STATUS ===");',
    'p:tell("  Health   [" + hpbar + "] " + tostr(p.health) + "/100");',
    'p:tell("  Hunger   [" + hbar + "] " + tostr(p.hunger) + "/100");',
    'p:tell("  Credits  " + tostr(p.w_credits) + " cr");',
    'p:tell("--- Combat Dice ---");',
    'p:tell("  Stamina  " + tostr(p.w_stam) + "/" + tostr(p.w_stam_max) + "  (melee hit)");',
    'p:tell("  Clarity  " + tostr(p.w_clarity) + "/" + tostr(p.w_clarity_max) + "  (ranged hit)");',
    'p:tell("  Aggrssn  " + tostr(p.w_aggression) + "/" + tostr(p.w_aggression_max) + "  (damage)");',
    'if ("w_target" in properties(p) && valid(p.w_target))',
    '  p:tell("  Target:  " + p.w_target.name + " [HP: " + tostr(p.w_target.cr_hp) + "]");',
    'endif',
    'if ("w_background" in properties(p) && p.w_background != "none")',
    '  p:tell("  Background: " + p.w_background);',
    'endif',
]

# ─────────────────────────────────────────────────────────────────────────────
# Dice regen in tick (appended to end of TICK_VERB)
# We rewrite tick entirely to add dice regen
# ─────────────────────────────────────────────────────────────────────────────
TICK_VERB_WITH_REGEN = [
    '"Decay survival stats; regen dice; process workers; re-schedule.";',
    '"No set_task_perms — inherits wizard perms via kickstart fork.";',
    'for p in (connected_players())',
    '  "--- hunger decay ---";',
    '  nh = p.hunger - 4;',
    '  if (nh < 0) nh = 0; endif',
    '  p.hunger = nh;',
    '  "--- stamina: recover if fed ---";',
    '  if (p.hunger > 30)',
    '    ns = p.stamina + 2;',
    '    if (ns > 100) ns = 100; endif',
    '  else',
    '    ns = p.stamina - 3;',
    '    if (ns < 0) ns = 0; endif',
    '  endif',
    '  p.stamina = ns;',
    '  "--- health falls when starving ---";',
    '  if (p.hunger == 0)',
    '    nhp = p.health - 5;',
    '    if (nhp <= 0) nhp = 0; endif',
    '    p.health = nhp;',
    '    if (nhp > 0)',
    '      p:tell("[SURVIVAL] You are starving. Find food or you will die.");',
    '    endif',
    '  elseif (p.hunger < 20)',
    '    p:tell("[SURVIVAL] Warning: hunger critical (" + tostr(p.hunger) + "/100).");',
    '  endif',
    '  "--- dice pool regen ---";',
    '  if ("w_stam" in properties(p))',
    '    if (p.w_stam < p.w_stam_max)',
    '      p.w_stam = p.w_stam + 1;',
    '    endif',
    '    if (p.w_clarity < p.w_clarity_max)',
    '      p.w_clarity = p.w_clarity + 1;',
    '    endif',
    '    if (p.w_aggression < p.w_aggression_max)',
    '      p.w_aggression = p.w_aggression + 1;',
    '    endif',
    '  endif',
    '  "--- creature stam regen ---";',
    '  for cr in ($creature_list)',
    '    if (valid(cr) && cr.cr_stam < cr.cr_stam_max)',
    '      cr.cr_stam = cr.cr_stam + 1;',
    '    endif',
    '  endfor',
    '  "--- death check ---";',
    '  if (p.health <= 0)',
    '    p.hunger = 20; p.health = 30; p.stamina = 50;',
    '    if ("w_stam" in properties(p))',
    '      p.w_stam = p.w_stam_max;',
    '      p.w_clarity = p.w_clarity_max;',
    '      p.w_aggression = p.w_aggression_max;',
    '    endif',
    '    p:tell(""); p:tell("*** YOU HAVE DIED ***");',
    '    p:tell("Starvation claimed you. You wake at the crash site, barely alive.");',
    '    p:tell("");',
    '    move(p, #459);',
    '    p.location:announce(p.name + " crawls back from the brink of death.", p);',
    '  endif',
    'endfor',
    '"--- NPC idle chatter ---";',
    'this:npc_idle();',
    '"--- Worker tick ---";',
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
    '      iname = "ore sample"; idesc = "A rough chunk of alien mineral ore.";',
    '      if (job == "fiber")',
    '        iname = "fiber bundle"; idesc = "A bundle of dried alien plant fiber.";',
    '      elseif (job == "water")',
    '        iname = "water sample"; idesc = "A sealed flask of filtered water.";',
    '      elseif (job == "salvage")',
    '        iname = "salvage scrap"; idesc = "Twisted metal and polymer pulled from ruins.";',
    '      endif',
    '      item = create($thing);',
    '      item.name = iname; item.description = idesc;',
    '      move(item, w.location);',
    '      owner = w.w_owner;',
    '      if (valid(owner) && (owner in connected_players()))',
    '        owner:tell("[COLONY] Your " + job + " gatherer deposited a " + iname + " in the factorium.");',
    '      endif',
    '    endif',
    '  endif',
    'endfor',
    '$worker_list = clean_list;',
    '"--- re-schedule in 300 seconds ---";',
    'fork (300)',
    '  this:tick();',
    'endfork',
]

# ─────────────────────────────────────────────────────────────────────────────
# $ods:populate extended — spawn creature in some rooms
# ─────────────────────────────────────────────────────────────────────────────
POPULATE_VERB = [
    '"Populate a new wilderness room with resource nodes and maybe a creature.";',
    'room = args[1];',
    'biome = room.biome;',
    '"Spawn 1-2 resource nodes based on biome";',
    'if (biome == 0)',
    '  "Mountain — ore (mineral veins)";',
    '  move(create($ore_node), room);',
    '  if (random(2) == 1) move(create($ore_node), room); endif',
    'elseif (biome == 1)',
    '  "Forest — fiber (alien plants)";',
    '  move(create($fiber_node), room);',
    '  if (random(2) == 1) move(create($water_node), room); endif',
    'elseif (biome == 2)',
    '  "Desert — salvage (buried ruins)";',
    '  move(create($salvage_node), room);',
    '  if (random(2) == 1) move(create($ore_node), room); endif',
    'elseif (biome == 3)',
    '  "Jungle — water + fiber";',
    '  move(create($water_node), room);',
    '  if (random(2) == 1) move(create($fiber_node), room); endif',
    'else',
    '  "Volcanic — ore + energy deposits";',
    '  move(create($ore_node), room);',
    '  move(create($salvage_node), room);',
    'endif',
    '"Spawn creature: 40% chance per room";',
    'if (random(10) <= 4)',
    '  cr = create($creature);',
    '  "Pick creature type based on biome";',
    '  if (biome == 0 || biome == 2)',
    '    cr.name = "rock stalker";',
    '    cr.description = "A squat, armoured predator that hunts in rocky terrain. Its carapace deflects light.";',
    '    cr.cr_hp = 15 + random(10);',
    '    cr.cr_aggr = 2;',
    '    cr.cr_stam = 3; cr.cr_stam_max = 3;',
    '  elseif (biome == 1 || biome == 3)',
    '    cr.name = "scrub runner";',
    '    cr.description = "A fast, lean carnivore with serrated teeth. Common in scrubland and dust plains.";',
    '    cr.cr_hp = 10 + random(8);',
    '    cr.cr_aggr = 1;',
    '    cr.cr_stam = 2; cr.cr_stam_max = 2;',
    '  else',
    '    cr.name = "thermal slug";',
    '    cr.description = "A slow but heavily armoured creature that radiates heat. Dangerous up close.";',
    '    cr.cr_hp = 20 + random(10);',
    '    cr.cr_aggr = 3;',
    '    cr.cr_stam = 2; cr.cr_stam_max = 2;',
    '  endif',
    '  cr.cr_hp_max = cr.cr_hp;',
    '  move(cr, room);',
    '  $creature_list = listappend($creature_list, cr);',
    'endif',
]


def main():
    s = connect()

    # ── 1. Create $creature prototype ────────────────────────────────────────
    print('=== Create $creature prototype ===')
    out = ev(s, 'player:tell("cr_exists=" + tostr("creature" in properties(#0)))')
    cr_num = None
    if '"creature" in properties' or 'cr_exists=0' not in out:
        # Check more carefully
        out2 = ev(s, 'player:tell(tostr("creature" in properties(#0)))')
        if '0' in out2.strip()[-5:]:
            # Create it
            add_verb(s, f'#{PLAYER}', '_cr_setup', 'none none none')
            program_verb(s, f'#{PLAYER}', '_cr_setup', [
                'if (!("creature" in properties(#0)))',
                '  add_property(#0, "creature", $nothing, {player, "rw"});',
                'endif',
                'if (!valid(#0.creature))',
                '  cr = create($thing);',
                '  cr.name = "creature";',
                '  add_property(cr, "cr_hp", 10, {player, "rw"});',
                '  add_property(cr, "cr_hp_max", 10, {player, "rw"});',
                '  add_property(cr, "cr_stam", 3, {player, "rw"});',
                '  add_property(cr, "cr_stam_max", 3, {player, "rw"});',
                '  add_property(cr, "cr_aggr", 1, {player, "rw"});',
                '  #0.creature = cr;',
                'endif',
                'player:tell("OBJNUM=" + tostr(#0.creature));',
            ])
            out3 = send(s, '_cr_setup', wait=3.0)
            m = re.search(r'OBJNUM=#(\d+)', out3)
            if m:
                cr_num = int(m.group(1))
                print(f'  $creature = #{cr_num}')
            else:
                print(f'  ERROR: {repr(out3[-100:])}')
                s.close(); return
        else:
            out3 = ev(s, 'player:tell("OBJNUM=" + tostr(#0.creature))')
            m = re.search(r'OBJNUM=#(\d+)', out3)
            cr_num = int(m.group(1)) if m else None
            print(f'  $creature already exists: #{cr_num}')

    # ── 2. $creature_list on #0 ───────────────────────────────────────────────
    print('\n=== Setup $creature_list ===')
    out = ev(s, 'player:tell(tostr("creature_list" in properties(#0)))')
    if '0' in out.strip()[-5:]:
        send(s, '@property #0.creature_list {}')
        ev(s, 'set_property_info(#0, "creature_list", {#361, "rw"})')
        print('  Created $creature_list')
    else:
        print('  Already exists')

    # ── 3. Dice pool props on $player ─────────────────────────────────────────
    print('\n=== Add dice pool props to $player ===')
    for prop, default in [('w_stam', 3), ('w_stam_max', 3),
                           ('w_clarity', 3), ('w_clarity_max', 3),
                           ('w_aggression', 3), ('w_aggression_max', 3),
                           ('w_target', '$nothing')]:
        out = ev(s, f'player:tell(tostr("{prop}" in properties(#{PLAYER})))')
        if '0' in out.strip()[-5:]:
            if prop == 'w_target':
                ev(s, f'add_property(#{PLAYER}, "{prop}", $nothing, {{#361, "rw"}})')
            else:
                ev(s, f'add_property(#{PLAYER}, "{prop}", {default}, {{#361, "rw"}})')
            # Make world-writable so tick can write it
            ev(s, f'set_property_info(#{PLAYER}, "{prop}", {{#361, "rw"}})')
            print(f'  Added {prop}={default}')
        else:
            ev(s, f'set_property_info(#{PLAYER}, "{prop}", {{#361, "rw"}})')
            print(f'  {prop} already exists (set rw)')

    # ── 4. Init dice on wizard player ─────────────────────────────────────────
    print('\n=== Init dice on wizard (#361) ===')
    ev(s, 'player.w_stam = 3; player.w_stam_max = 3')
    ev(s, 'player.w_clarity = 3; player.w_clarity_max = 3')
    ev(s, 'player.w_aggression = 3; player.w_aggression_max = 3')
    ev(s, 'player.w_target = $nothing')
    print('  Done')

    # ── 5. Combat verbs on $player ────────────────────────────────────────────
    print('\n=== KILL verb ===')
    add_verb(s, f'#{PLAYER}', 'kill', 'any none none')
    program_verb(s, f'#{PLAYER}', 'kill', KILL_VERB)

    print('\n=== SWING verb ===')
    add_verb(s, f'#{PLAYER}', 'swing', 'none none none')
    program_verb(s, f'#{PLAYER}', 'swing', SWING_VERB)

    print('\n=== FIRE verb ===')
    add_verb(s, f'#{PLAYER}', 'fire', 'none none none')
    program_verb(s, f'#{PLAYER}', 'fire', FIRE_VERB)

    print('\n=== cr_retaliate verb ===')
    add_verb(s, f'#{PLAYER}', 'cr_retaliate', 'any none none')
    program_verb(s, f'#{PLAYER}', 'cr_retaliate', CR_RETALIATE_VERB)

    print('\n=== cr_die verb ===')
    add_verb(s, f'#{PLAYER}', 'cr_die', 'any none none')
    program_verb(s, f'#{PLAYER}', 'cr_die', CR_DIE_VERB)

    print('\n=== TAC verb ===')
    add_verb(s, f'#{PLAYER}', 'tac', 'none none none')
    program_verb(s, f'#{PLAYER}', 'tac', TAC_VERB)

    print('\n=== CON verb ===')
    add_verb(s, f'#{PLAYER}', 'con', 'any none none')
    program_verb(s, f'#{PLAYER}', 'con', CON_VERB)

    print('\n=== ST verb (updated) ===')
    program_verb(s, f'#{PLAYER}', 'st', ST_VERB)

    # ── 6. Updated tick with dice regen ───────────────────────────────────────
    print('\n=== Update #545:tick with dice regen ===')
    program_verb(s, f'#{HEARTBEAT}', 'tick', TICK_VERB_WITH_REGEN)

    # ── 7. Updated $ods:populate with creature spawning ───────────────────────
    print('\n=== Update $ods:populate with creature spawning ===')
    program_verb(s, f'#{ODS}', 'populate', POPULATE_VERB)

    # ── 8. Kick heartbeat ─────────────────────────────────────────────────────
    print('\n=== Kick heartbeat ===')
    print(ev(s, '#545:kickstart()').strip())

    # ── 9. Quick combat test ──────────────────────────────────────────────────
    print('\n=== Combat test ===')
    # Spawn a test creature at player location
    test_out = ev(s, '''
cr = create($creature);
cr.name = "test critter";
cr.description = "A test creature.";
cr.cr_hp = 8; cr.cr_hp_max = 8;
cr.cr_stam = 2; cr.cr_stam_max = 2;
cr.cr_aggr = 1;
move(cr, player.location);
$creature_list = listappend($creature_list, cr);
player:tell("Spawned: " + cr.name + " HP=" + tostr(cr.cr_hp));
'''.strip().replace('\n', '; '), wait=1.5)
    print(test_out.strip())

    print(send(s, 'tac', wait=1.0).strip())
    print(send(s, 'con test', wait=1.0).strip())
    print(send(s, 'kill test critter', wait=1.0).strip())
    print(send(s, 'swing', wait=1.0).strip())
    print(send(s, 'swing', wait=1.0).strip())
    print(send(s, 'st', wait=1.0).strip())

    # Save
    print('\n=== Save ===')
    print(send(s, '@dump-database', wait=3.0).strip())
    s.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
