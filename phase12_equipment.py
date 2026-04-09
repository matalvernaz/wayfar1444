#!/usr/bin/env python3
"""
Wayfar 1444 — Phase 12: Equipment Slot System (#11)

Adds:
  1. $equipment prototype on #0 — eq_slot/eq_type/eq_tohit/eq_defense/eq_dodge/
     eq_dmg_bonus/eq_hp_bonus/eq_stam_bonus/eq_clarity_bonus/eq_aggr_bonus/eq_actions
  2. Equipment slot properties on $player: w_weapon, w_armor, w_gadget, w_special
  3. wield/wear/equip/remove/gear/actions verbs on $player
  4. _apply_stats/_unequip_stats internal helpers
  5. Modified swing/fire — weapon bonuses, unarmed penalty
  6. Modified cr_retaliate — armor defense + dodge
  7. Updated ST — shows equipped gear
  8. Starter craft recipes: colonial machete, colonial rifle, hide armor

Run with server live: python3 phase12_equipment.py
"""

import socket, time, re, sys

HOST = 'localhost'
PORT = 7777
PLAYER = 6
HEARTBEAT = 545
BCT_NUM = 592

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

def extract_num(out):
    m = re.search(r'OBJNUM=#(\d+)', out)
    return int(m.group(1)) if m else None


# ─────────────────────────────────────────────────────────────────────────────
# _apply_stats — add equipment stat bonuses to player
# ─────────────────────────────────────────────────────────────────────────────

APPLY_STATS_VERB = [
    '"Apply equipment stat bonuses. Called as this:_apply_stats(item).";',
    'item = args[1];',
    'if (!valid(item)) return; endif',
    'p = player;',
    'if (item.eq_hp_bonus != 0)',
    '  p.w_hp_max = p.w_hp_max + item.eq_hp_bonus;',
    '  p.health = p.health + item.eq_hp_bonus;',
    'endif',
    'if (item.eq_stam_bonus != 0)',
    '  p.w_stam_max = p.w_stam_max + item.eq_stam_bonus;',
    'endif',
    'if (item.eq_clarity_bonus != 0)',
    '  p.w_clarity_max = p.w_clarity_max + item.eq_clarity_bonus;',
    'endif',
    'if (item.eq_aggr_bonus != 0)',
    '  p.w_aggression_max = p.w_aggression_max + item.eq_aggr_bonus;',
    'endif',
]

# ─────────────────────────────────────────────────────────────────────────────
# _unequip_stats — remove equipment stat bonuses from player
# ─────────────────────────────────────────────────────────────────────────────

UNEQUIP_STATS_VERB = [
    '"Remove equipment stat bonuses. Called as this:_unequip_stats(item).";',
    'item = args[1];',
    'if (!valid(item)) return; endif',
    'p = player;',
    'if (item.eq_hp_bonus != 0)',
    '  p.w_hp_max = p.w_hp_max - item.eq_hp_bonus;',
    '  if (p.w_hp_max < 1) p.w_hp_max = 1; endif',
    '  if (p.health > p.w_hp_max) p.health = p.w_hp_max; endif',
    'endif',
    'if (item.eq_stam_bonus != 0)',
    '  p.w_stam_max = p.w_stam_max - item.eq_stam_bonus;',
    '  if (p.w_stam_max < 1) p.w_stam_max = 1; endif',
    '  if (p.w_stam > p.w_stam_max) p.w_stam = p.w_stam_max; endif',
    'endif',
    'if (item.eq_clarity_bonus != 0)',
    '  p.w_clarity_max = p.w_clarity_max - item.eq_clarity_bonus;',
    '  if (p.w_clarity_max < 1) p.w_clarity_max = 1; endif',
    '  if (p.w_clarity > p.w_clarity_max) p.w_clarity = p.w_clarity_max; endif',
    'endif',
    'if (item.eq_aggr_bonus != 0)',
    '  p.w_aggression_max = p.w_aggression_max - item.eq_aggr_bonus;',
    '  if (p.w_aggression_max < 1) p.w_aggression_max = 1; endif',
    '  if (p.w_aggression > p.w_aggression_max) p.w_aggression = p.w_aggression_max; endif',
    'endif',
]


# ─────────────────────────────────────────────────────────────────────────────
# wield verb — equip weapon or special weapon
# ─────────────────────────────────────────────────────────────────────────────

WIELD_VERB = [
    '"Equip a weapon or special tool. Usage: wield <item name>.";',
    'p = player;',
    'tstr = (typeof(dobjstr) == STR && dobjstr != "") ? dobjstr | "";',
    'if (tstr == "" && args != {})',
    '  for w in (args)',
    '    if (typeof(w) == STR)',
    '      tstr = tstr == "" ? w | tstr + " " + w;',
    '    endif',
    '  endfor',
    'endif',
    'if (tstr == "")',
    '  p:tell("Wield what? Usage: wield <weapon name>");',
    '  return;',
    'endif',
    '"Find matching equipment in inventory";',
    'item = 0;',
    'for itm in (p.contents)',
    '  if (is_a(itm, $equipment) && index(itm.name, tstr))',
    '    item = itm;',
    '    break;',
    '  endif',
    'endfor',
    'if (item == 0)',
    '  p:tell("You\'re not carrying any wieldable item matching \'" + tstr + "\'.");',
    '  return;',
    'endif',
    '"Check slot type";',
    'slot = item.eq_slot;',
    'if (slot == "weapon")',
    '  "Unequip current weapon if any";',
    '  if (valid(p.w_weapon))',
    '    this:_unequip_stats(p.w_weapon);',
    '    p:tell("You put away the " + p.w_weapon.name + ".");',
    '  endif',
    '  p.w_weapon = item;',
    '  this:_apply_stats(item);',
    '  p:tell("You wield the " + item.name + ".");',
    '  if (item.eq_type == "melee")',
    '    p:tell("  Use SWING to attack in melee.");',
    '  elseif (item.eq_type == "ranged")',
    '    p:tell("  Use FIRE to attack at range.");',
    '  endif',
    'elseif (slot == "special")',
    '  if (valid(p.w_special))',
    '    this:_unequip_stats(p.w_special);',
    '    p:tell("You put away the " + p.w_special.name + ".");',
    '  endif',
    '  p.w_special = item;',
    '  this:_apply_stats(item);',
    '  p:tell("You ready the " + item.name + " in your special weapon slot.");',
    'else',
    '  p:tell("You can\'t wield that. Try WEAR for armor or EQUIP for gadgets.");',
    '  return;',
    'endif',
    'p.location:announce(p.name + " readies a " + item.name + ".", p);',
]


# ─────────────────────────────────────────────────────────────────────────────
# wear verb — equip armor
# ─────────────────────────────────────────────────────────────────────────────

WEAR_VERB = [
    '"Equip armor. Usage: wear <armor name>.";',
    'p = player;',
    'tstr = (typeof(dobjstr) == STR && dobjstr != "") ? dobjstr | "";',
    'if (tstr == "" && args != {})',
    '  for w in (args)',
    '    if (typeof(w) == STR)',
    '      tstr = tstr == "" ? w | tstr + " " + w;',
    '    endif',
    '  endfor',
    'endif',
    'if (tstr == "")',
    '  p:tell("Wear what? Usage: wear <armor name>");',
    '  return;',
    'endif',
    'item = 0;',
    'for itm in (p.contents)',
    '  if (is_a(itm, $equipment) && itm.eq_slot == "armor" && index(itm.name, tstr))',
    '    item = itm;',
    '    break;',
    '  endif',
    'endfor',
    'if (item == 0)',
    '  p:tell("You\'re not carrying any armor matching \'" + tstr + "\'.");',
    '  return;',
    'endif',
    'if (valid(p.w_armor))',
    '  this:_unequip_stats(p.w_armor);',
    '  p:tell("You remove the " + p.w_armor.name + ".");',
    'endif',
    'p.w_armor = item;',
    'this:_apply_stats(item);',
    'p:tell("You put on the " + item.name + ". [def:" + tostr(item.eq_defense) + " dodge:" + tostr(item.eq_dodge) + "]");',
    'p.location:announce(p.name + " puts on some " + item.name + ".", p);',
]


# ─────────────────────────────────────────────────────────────────────────────
# equip verb — equip gadget
# ─────────────────────────────────────────────────────────────────────────────

EQUIP_VERB = [
    '"Equip a gadget. Usage: equip <gadget name>.";',
    'p = player;',
    'tstr = (typeof(dobjstr) == STR && dobjstr != "") ? dobjstr | "";',
    'if (tstr == "" && args != {})',
    '  for w in (args)',
    '    if (typeof(w) == STR)',
    '      tstr = tstr == "" ? w | tstr + " " + w;',
    '    endif',
    '  endfor',
    'endif',
    'if (tstr == "")',
    '  p:tell("Equip what? Usage: equip <gadget name>");',
    '  return;',
    'endif',
    'item = 0;',
    'for itm in (p.contents)',
    '  if (is_a(itm, $equipment) && itm.eq_slot == "gadget" && index(itm.name, tstr))',
    '    item = itm;',
    '    break;',
    '  endif',
    'endfor',
    'if (item == 0)',
    '  p:tell("You\'re not carrying any gadget matching \'" + tstr + "\'.");',
    '  return;',
    'endif',
    'if (valid(p.w_gadget))',
    '  this:_unequip_stats(p.w_gadget);',
    '  p:tell("You unequip the " + p.w_gadget.name + ".");',
    'endif',
    'p.w_gadget = item;',
    'this:_apply_stats(item);',
    'p:tell("You equip the " + item.name + " in your gadget slot.");',
    'p.location:announce(p.name + " equips a " + item.name + ".", p);',
]


# ─────────────────────────────────────────────────────────────────────────────
# remove verb — unequip by slot name or item name
# ─────────────────────────────────────────────────────────────────────────────

REMOVE_VERB = [
    '"Unequip an item. Usage: remove <weapon|armor|gadget|special> or remove <item name>.";',
    'p = player;',
    'tstr = (typeof(dobjstr) == STR && dobjstr != "") ? dobjstr | "";',
    'if (tstr == "" && args != {})',
    '  for w in (args)',
    '    if (typeof(w) == STR)',
    '      tstr = tstr == "" ? w | tstr + " " + w;',
    '    endif',
    '  endfor',
    'endif',
    'if (tstr == "")',
    '  p:tell("Remove what? Usage: remove <weapon|armor|gadget|special>");',
    '  return;',
    'endif',
    '"Match by slot name";',
    'item = 0;',
    'slot_name = "";',
    'if (tstr == "weapon" || tstr == "wield")',
    '  item = p.w_weapon; slot_name = "weapon";',
    'elseif (tstr == "armor" || tstr == "wear")',
    '  item = p.w_armor; slot_name = "armor";',
    'elseif (tstr == "gadget" || tstr == "equip")',
    '  item = p.w_gadget; slot_name = "gadget";',
    'elseif (tstr == "special" || tstr == "tool" || tstr == "harvest")',
    '  item = p.w_special; slot_name = "special";',
    'else',
    '  "Try matching against equipped item names";',
    '  if (valid(p.w_weapon) && index(p.w_weapon.name, tstr))',
    '    item = p.w_weapon; slot_name = "weapon";',
    '  elseif (valid(p.w_armor) && index(p.w_armor.name, tstr))',
    '    item = p.w_armor; slot_name = "armor";',
    '  elseif (valid(p.w_gadget) && index(p.w_gadget.name, tstr))',
    '    item = p.w_gadget; slot_name = "gadget";',
    '  elseif (valid(p.w_special) && index(p.w_special.name, tstr))',
    '    item = p.w_special; slot_name = "special";',
    '  endif',
    'endif',
    'if (!valid(item))',
    '  p:tell("Nothing equipped matching \'" + tstr + "\'. Type GEAR to see equipped items.");',
    '  return;',
    'endif',
    'this:_unequip_stats(item);',
    'iname = item.name;',
    'if (slot_name == "weapon")',
    '  p.w_weapon = $nothing;',
    'elseif (slot_name == "armor")',
    '  p.w_armor = $nothing;',
    'elseif (slot_name == "gadget")',
    '  p.w_gadget = $nothing;',
    'elseif (slot_name == "special")',
    '  p.w_special = $nothing;',
    'endif',
    'p:tell("You remove the " + iname + ".");',
    'p.location:announce(p.name + " puts away their " + iname + ".", p);',
]


# ─────────────────────────────────────────────────────────────────────────────
# gear verb — show all equipped items
# ─────────────────────────────────────────────────────────────────────────────

GEAR_VERB = [
    '"Show all equipped items and their stats.";',
    'p = player;',
    'p:tell("=== GEAR ===");',
    'if (valid(p.w_weapon))',
    '  w = p.w_weapon;',
    '  p:tell("  Weapon:  " + w.name + "  [" + w.eq_type + " | tohit:" + tostr(w.eq_tohit) + " dmg:" + tostr(w.eq_dmg_bonus) + "]");',
    'else',
    '  p:tell("  Weapon:  (empty) — wield <weapon>");',
    'endif',
    'if (valid(p.w_armor))',
    '  a = p.w_armor;',
    '  p:tell("  Armor:   " + a.name + "  [def:" + tostr(a.eq_defense) + " dodge:" + tostr(a.eq_dodge) + " hp:" + tostr(a.eq_hp_bonus) + "]");',
    'else',
    '  p:tell("  Armor:   (empty) — wear <armor>");',
    'endif',
    'if (valid(p.w_gadget))',
    '  p:tell("  Gadget:  " + p.w_gadget.name);',
    'else',
    '  p:tell("  Gadget:  (empty) — equip <gadget>");',
    'endif',
    'if (valid(p.w_special))',
    '  p:tell("  Special: " + p.w_special.name);',
    'else',
    '  p:tell("  Special: (empty) — wield <tool>");',
    'endif',
]


# ─────────────────────────────────────────────────────────────────────────────
# actions verb — show equipped weapon commands
# ─────────────────────────────────────────────────────────────────────────────

ACTIONS_VERB = [
    '"Show available combat actions from equipped weapon.";',
    'p = player;',
    'if (!valid(p.w_weapon))',
    '  p:tell("No weapon equipped. Use WIELD <weapon> first.");',
    '  p:tell("Unarmed: SWING (melee, reduced damage)");',
    '  return;',
    'endif',
    'w = p.w_weapon;',
    'p:tell("=== ACTIONS: " + w.name + " ===");',
    'if (w.eq_type == "melee")',
    '  p:tell("  SWING  — melee attack (costs 1 stamina die)");',
    'elseif (w.eq_type == "ranged")',
    '  p:tell("  FIRE   — ranged attack (costs 1 clarity die)");',
    'endif',
    'p:tell("  KILL <target> — set combat target");',
    'p:tell("  TAC    — tactical display (all entities in room)");',
    'p:tell("  CON <target> — consider enemy strength");',
    'p:tell("  GEAR   — show equipped items");',
]


# ─────────────────────────────────────────────────────────────────────────────
# Modified SWING — weapon bonuses, unarmed penalty
# ─────────────────────────────────────────────────────────────────────────────

SWING_VERB_V2 = [
    '"Melee attack. Weapon gives tohit + damage bonus. Unarmed = half aggression dice.";',
    'p = player;',
    '"Validate target";',
    'if (!valid(p.w_target))',
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
    '"Weapon check";',
    'tohit_bonus = 0;',
    'dmg_bonus = 0;',
    'armed = 0;',
    'wname = "bare fists";',
    'if (valid(p.w_weapon) && p.w_weapon.location == p && p.w_weapon.eq_type == "melee")',
    '  tohit_bonus = p.w_weapon.eq_tohit;',
    '  dmg_bonus = p.w_weapon.eq_dmg_bonus;',
    '  armed = 1;',
    '  wname = p.w_weapon.name;',
    'endif',
    '"Spend 1 stamina die and roll to hit";',
    'p.w_stam = p.w_stam - 1;',
    'hit_roll = random(6) + tohit_bonus;',
    'if (hit_roll < 3)',
    '  p:tell("[MISS] You swing at the " + target.name + " but miss! (rolled " + tostr(hit_roll) + ")");',
    '  p.location:announce(p.name + " swings at the " + target.name + " and misses.", p);',
    'else',
    '  "Hit — roll aggression dice for damage";',
    '  dice_to_spend = armed ? p.w_aggression | ((p.w_aggression + 1) / 2);',
    '  if (dice_to_spend < 1) dice_to_spend = 1; endif',
    '  dmg = 0;',
    '  for i in [1..dice_to_spend]',
    '    dmg = dmg + random(6);',
    '  endfor',
    '  if (armed)',
    '    p.w_aggression = 0;',
    '  else',
    '    p.w_aggression = p.w_aggression - dice_to_spend;',
    '    if (p.w_aggression < 0) p.w_aggression = 0; endif',
    '  endif',
    '  dmg = dmg + dmg_bonus;',
    '  target.cr_hp = target.cr_hp - dmg;',
    '  p:tell("[HIT] You strike the " + target.name + " with " + wname + " for " + tostr(dmg) + " damage!");',
    '  p.location:announce(p.name + " strikes the " + target.name + " for " + tostr(dmg) + " damage!", p);',
    '  "Creature retaliation";',
    '  this:cr_retaliate(target);',
    '  "Check creature death";',
    '  if (target.cr_hp <= 0)',
    '    this:cr_die(target);',
    '  endif',
    'endif',
    'p:tell("[ST] HP:" + tostr(p.health) + " STM:" + tostr(p.w_stam) + "/" + tostr(p.w_stam_max) + " AGG:" + tostr(p.w_aggression) + "/" + tostr(p.w_aggression_max));',
]


# ─────────────────────────────────────────────────────────────────────────────
# Modified FIRE — ranged weapon check
# ─────────────────────────────────────────────────────────────────────────────

FIRE_VERB_V2 = [
    '"Ranged attack. Requires ranged weapon for full damage. No weapon = throw a rock.";',
    'p = player;',
    'if (!valid(p.w_target))',
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
    '"Weapon check";',
    'tohit_bonus = 0;',
    'dmg_bonus = 0;',
    'armed = 0;',
    'wname = "a thrown rock";',
    'if (valid(p.w_weapon) && p.w_weapon.location == p && p.w_weapon.eq_type == "ranged")',
    '  tohit_bonus = p.w_weapon.eq_tohit;',
    '  dmg_bonus = p.w_weapon.eq_dmg_bonus;',
    '  armed = 1;',
    '  wname = p.w_weapon.name;',
    'endif',
    'p.w_clarity = p.w_clarity - 1;',
    'hit_roll = random(6) + tohit_bonus;',
    'if (hit_roll < 3)',
    '  p:tell("[MISS] You fire at the " + target.name + " but miss! (rolled " + tostr(hit_roll) + ")");',
    '  p.location:announce(p.name + " fires at the " + target.name + " and misses.", p);',
    'else',
    '  dmg = 0;',
    '  if (armed)',
    '    for i in [1..p.w_aggression]',
    '      dmg = dmg + random(6);',
    '    endfor',
    '    p.w_aggression = 0;',
    '  else',
    '    "No ranged weapon — just 1d6";',
    '    dmg = random(6);',
    '  endif',
    '  dmg = dmg + dmg_bonus;',
    '  target.cr_hp = target.cr_hp - dmg;',
    '  p:tell("[HIT] You hit the " + target.name + " with " + wname + " for " + tostr(dmg) + " damage!");',
    '  p.location:announce(p.name + " shoots the " + target.name + " for " + tostr(dmg) + " damage!", p);',
    '  this:cr_retaliate(target);',
    '  if (target.cr_hp <= 0)',
    '    this:cr_die(target);',
    '  endif',
    'endif',
    'p:tell("[ST] HP:" + tostr(p.health) + " CLR:" + tostr(p.w_clarity) + "/" + tostr(p.w_clarity_max) + " AGG:" + tostr(p.w_aggression) + "/" + tostr(p.w_aggression_max));',
]


# ─────────────────────────────────────────────────────────────────────────────
# Modified cr_retaliate — armor defense + dodge
# ─────────────────────────────────────────────────────────────────────────────

CR_RETALIATE_V2 = [
    '"Creature strikes back. Armor provides defense and dodge.";',
    'p = player;',
    'creature = args[1];',
    'if (!valid(creature) || creature.cr_hp <= 0)',
    '  return;',
    'endif',
    'if (creature.cr_stam < 1)',
    '  p:tell("The " + creature.name + " staggers, too exhausted to retaliate.");',
    '  return;',
    'endif',
    'creature.cr_stam = creature.cr_stam - 1;',
    'hit_roll = random(6);',
    'if (hit_roll < 3)',
    '  p:tell("The " + creature.name + " retaliates but misses you! (rolled " + tostr(hit_roll) + ")");',
    'else',
    '  "Check dodge from armor";',
    '  dodge_bonus = 0;',
    '  def_bonus = 0;',
    '  if (valid(p.w_armor) && p.w_armor.location == p)',
    '    dodge_bonus = p.w_armor.eq_dodge;',
    '    def_bonus = p.w_armor.eq_defense;',
    '  endif',
    '  if (dodge_bonus > 0 && random(6) <= dodge_bonus)',
    '    p:tell("You dodge the " + creature.name + "\'s attack!");',
    '  else',
    '    dmg = 0;',
    '    for i in [1..creature.cr_aggr]',
    '      dmg = dmg + random(6);',
    '    endfor',
    '    dmg = dmg - def_bonus;',
    '    if (dmg < 1) dmg = 1; endif',
    '    p.health = p.health - dmg;',
    '    if (def_bonus > 0)',
    '      p:tell("The " + creature.name + " strikes you for " + tostr(dmg) + " damage (armor absorbs " + tostr(def_bonus) + ")! [HP: " + tostr(p.health) + "]");',
    '    else',
    '      p:tell("The " + creature.name + " strikes you for " + tostr(dmg) + " damage! [HP: " + tostr(p.health) + "]");',
    '    endif',
    '    p.location:announce("The " + creature.name + " strikes " + p.name + " for " + tostr(dmg) + " damage!", p);',
    '    "Player death check";',
    '    if (p.health <= 0)',
    '      p.hunger = 20; p.health = 30; p.stamina = 50;',
    '      p.w_stam = p.w_stam_max; p.w_clarity = p.w_clarity_max; p.w_aggression = p.w_aggression_max;',
    '      p:tell(""); p:tell("*** YOU HAVE DIED ***");',
    '      p:tell("The " + creature.name + " finishes you. You wake at the crash site.");',
    '      p:tell("");',
    '      p.w_target = $nothing;',
    '      move(p, #459);',
    '      p.location:announce(p.name + " staggers back from the brink of death.", p);',
    '    endif',
    '  endif',
    'endif',
]


# ─────────────────────────────────────────────────────────────────────────────
# Equipment craft recipes (appended to existing craft verb)
# ─────────────────────────────────────────────────────────────────────────────

MACHETE_RECIPE = [
    '"=== COLONIAL MACHETE (melee weapon) ===";',
    'if (index(tgt, "machete"))',
    '  found_m = {}; found_f = {};',
    '  for itm in (p.contents)',
    '    n = itm.name;',
    '    if (length(found_m) == 0 && index(n, "inert metal"))',
    '      found_m = listappend(found_m, itm);',
    '    endif',
    '    if (length(found_f) == 0 && (index(n, "fiber") || index(n, "plant")))',
    '      found_f = listappend(found_f, itm);',
    '    endif',
    '  endfor',
    '  if (length(found_m) == 0)',
    '    p:tell("Need 1x inert metal.");',
    '    return;',
    '  endif',
    '  if (length(found_f) == 0)',
    '    p:tell("Need 1x fiber.");',
    '    return;',
    '  endif',
    '  recycle(found_m[1]); recycle(found_f[1]);',
    '  r = create($equipment);',
    '  r.name = "colonial machete";',
    '  r.description = "A crude but effective blade forged from alien ore. Standard colonial sidearm.";',
    '  r.eq_slot = "weapon";',
    '  r.eq_type = "melee";',
    '  r.eq_tohit = 1;',
    '  r.eq_dmg_bonus = 2;',
    '  r.eq_actions = {"swing"};',
    '  move(r, p);',
    '  p:tell("You hammer an inert metal ingot into a brutal colonial machete. [+melee weapon]");',
    '  return;',
    'endif',
]

RIFLE_RECIPE = [
    '"=== COLONIAL RIFLE (ranged weapon) ===";',
    'if (index(tgt, "rifle"))',
    '  found_m = {}; found_w = {};',
    '  for itm in (p.contents)',
    '    n = itm.name;',
    '    if (length(found_m) < 2 && index(n, "inert metal"))',
    '      found_m = listappend(found_m, itm);',
    '    endif',
    '    if (length(found_w) == 0 && index(n, "crude wire"))',
    '      found_w = listappend(found_w, itm);',
    '    endif',
    '  endfor',
    '  if (length(found_m) < 2)',
    '    p:tell("Need 2x inert metal. Have: " + tostr(length(found_m)));',
    '    return;',
    '  endif',
    '  if (length(found_w) == 0)',
    '    p:tell("Need 1x crude wire.");',
    '    return;',
    '  endif',
    '  recycle(found_m[1]); recycle(found_m[2]); recycle(found_w[1]);',
    '  r = create($equipment);',
    '  r.name = "colonial rifle";',
    '  r.description = "A mag-rail rifle cobbled from colony metal and salvaged wire. Fires inert slugs.";',
    '  r.eq_slot = "weapon";',
    '  r.eq_type = "ranged";',
    '  r.eq_tohit = 1;',
    '  r.eq_dmg_bonus = 3;',
    '  r.eq_actions = {"fire"};',
    '  move(r, p);',
    '  p:tell("You assemble a mag-rail colonial rifle from metal and wire. [+ranged weapon]");',
    '  return;',
    'endif',
]

HIDE_ARMOR_RECIPE = [
    '"=== HIDE ARMOR ===";',
    'if (index(tgt, "hide") || index(tgt, "armor"))',
    '  found_f = {};',
    '  for itm in (p.contents)',
    '    if (length(found_f) < 3 && (index(itm.name, "fiber") || index(itm.name, "plant")))',
    '      found_f = listappend(found_f, itm);',
    '    endif',
    '  endfor',
    '  if (length(found_f) < 3)',
    '    p:tell("Need 3x fiber. Have: " + tostr(length(found_f)));',
    '    return;',
    '  endif',
    '  recycle(found_f[1]); recycle(found_f[2]); recycle(found_f[3]);',
    '  r = create($equipment);',
    '  r.name = "hide armor";',
    '  r.description = "Thick alien plant fibers woven and hardened into crude body armor.";',
    '  r.eq_slot = "armor";',
    '  r.eq_type = "armor";',
    '  r.eq_defense = 2;',
    '  r.eq_dodge = 1;',
    '  r.eq_hp_bonus = 5;',
    '  move(r, p);',
    '  p:tell("You weave hardened fibers into crude hide armor. [+armor | def:2 dodge:1 hp:+5]");',
    '  return;',
    'endif',
]


# ─────────────────────────────────────────────────────────────────────────────
# Sector center kit recipe (from phase9_colony.py)
# ─────────────────────────────────────────────────────────────────────────────

SC_RECIPE = [
    '"=== SECTOR CENTER KIT ===";',
    'if (index(tgt, "sector") || index(tgt, "center") || index(tgt, "sc kit"))',
    '  found_m = {}; found_w = {};',
    '  for itm in (p.contents)',
    '    n = itm.name;',
    '    if (length(found_m) < 2 && index(n, "inert metal"))',
    '      found_m = listappend(found_m, itm);',
    '    endif',
    '    if (length(found_w) < 2 && index(n, "crude wire"))',
    '      found_w = listappend(found_w, itm);',
    '    endif',
    '  endfor',
    '  if (length(found_m) < 2)',
    '    p:tell("Need 2x inert metal. Have: " + tostr(length(found_m)));',
    '    return;',
    '  endif',
    '  if (length(found_w) < 2)',
    '    p:tell("Need 2x crude wire. Have: " + tostr(length(found_w)));',
    '    return;',
    '  endif',
    '  recycle(found_m[1]); recycle(found_m[2]);',
    '  recycle(found_w[1]); recycle(found_w[2]);',
    '  r = create($thing); r.name = "sector center kit";',
    '  r.description = "A compressed prefab colony administration complex. Deploy with: place sector center";',
    '  move(r, p);',
    '  p:tell("You assemble the components into a sector center kit. [+sector center kit]");',
    '  return;',
    'endif',
]


def build_craft_verb():
    """Build full craft verb with all recipes including equipment."""
    return [
        '"Craft items using a basic crafting tool from inventory.";',
        'p = player;',
        'tool = 0;',
        'for itm in (player.contents)',
        f'  if (is_a(itm, #{BCT_NUM}))',
        '    tool = itm; break;',
        '  endif',
        'endfor',
        'if (tool == 0)',
        '  player:tell("You need a basic crafting tool. (You don\'t have one.)");',
        '  return;',
        'endif',
        'tgt = "";',
        'for w in (args)',
        '  tgt = (tgt == "") ? w | (tgt + " " + w);',
        'endfor',
        'if (typeof(dobjstr) == STR && dobjstr != "")',
        '  tgt = dobjstr;',
        'endif',
        'if (tgt == "" || tgt == "list" || tgt == "help")',
        '  p:tell("=== BASIC CRAFTING TOOL — RECIPES ===");',
        '  p:tell("  ration bar           — 2x fiber");',
        '  p:tell("  water canteen        — 1x fiber + 1x raw water");',
        '  p:tell("  inert metal          — 2x ore/mineral");',
        '  p:tell("  crude wire           — 1x ore + 1x salvage");',
        '  p:tell("  pre-fab shelter kit  — 1x inert metal + 2x fiber");',
        '  p:tell("  sector center kit    — 2x inert metal + 2x crude wire");',
        '  p:tell("  --- EQUIPMENT ---");',
        '  p:tell("  colonial machete     — 1x inert metal + 1x fiber");',
        '  p:tell("  colonial rifle       — 2x inert metal + 1x crude wire");',
        '  p:tell("  hide armor           — 3x fiber");',
        '  p:tell("Usage: craft <recipe name>");',
        '  return;',
        'endif',
        # RATION BAR
        'if (index(tgt, "ration") || index(tgt, "food") || index(tgt, "bar"))',
        '  found = {};',
        '  for itm in (p.contents)',
        '    if (length(found) < 2 && (index(itm.name, "fiber") || index(itm.name, "plant")))',
        '      found = listappend(found, itm);',
        '    endif',
        '  endfor',
        '  if (length(found) < 2)',
        '    p:tell("Need 2x fiber. Have: " + tostr(length(found)));',
        '    return;',
        '  endif',
        '  recycle(found[1]); recycle(found[2]);',
        '  r = create($thing); r.name = "ration bar";',
        '  r.description = "A compressed brick of processed plant fiber.";',
        '  move(r, p);',
        '  p:tell("You press the fibers into a dense ration bar. [+food item]");',
        '  p.location:announce(p.name + " uses a crafting tool.", p);',
        '  return;',
        'endif',
        # WATER CANTEEN
        'if (index(tgt, "water") || index(tgt, "canteen"))',
        '  found_f = {}; found_w = {};',
        '  for itm in (p.contents)',
        '    n = itm.name;',
        '    if (length(found_f) == 0 && (index(n, "fiber") || index(n, "plant")))',
        '      found_f = listappend(found_f, itm);',
        '    endif',
        '    if (length(found_w) == 0 && (index(n, "water") || index(n, "liquid")))',
        '      found_w = listappend(found_w, itm);',
        '    endif',
        '  endfor',
        '  if (length(found_f) == 0)',
        '    p:tell("Need 1x fiber.");',
        '    return;',
        '  endif',
        '  if (length(found_w) == 0)',
        '    p:tell("Need 1x water sample.");',
        '    return;',
        '  endif',
        '  recycle(found_f[1]); recycle(found_w[1]);',
        '  r = create($thing); r.name = "water canteen";',
        '  r.description = "A rough fiber-bound canteen containing filtered drinking water.";',
        '  move(r, p);',
        '  p:tell("You weave fiber around the water sample into a sealed canteen. [+drink item]");',
        '  return;',
        'endif',
        # INERT METAL
        'if (index(tgt, "inert") || index(tgt, "metal"))',
        '  found = {};',
        '  for itm in (p.contents)',
        '    if (length(found) < 2)',
        '      n = itm.name;',
        '      if (index(n, "ore") || index(n, "mineral") || index(n, "rock") || index(n, "stone"))',
        '        found = listappend(found, itm);',
        '      endif',
        '    endif',
        '  endfor',
        '  if (length(found) < 2)',
        '    p:tell("Need 2x ore/mineral. Have: " + tostr(length(found)));',
        '    return;',
        '  endif',
        '  recycle(found[1]); recycle(found[2]);',
        '  r = create($thing); r.name = "inert metal";',
        '  r.description = "Smelted alien ore, shaped into a rough ingot. Foundation of all construction.";',
        '  move(r, p);',
        '  p:tell("You smelt the ore samples into an inert metal ingot. [+inert metal]");',
        '  return;',
        'endif',
        # CRUDE WIRE
        'if (index(tgt, "wire") || index(tgt, "crude"))',
        '  found_o = {}; found_s = {};',
        '  for itm in (p.contents)',
        '    n = itm.name;',
        '    if (length(found_o) == 0 && (index(n, "ore") || index(n, "mineral")))',
        '      found_o = listappend(found_o, itm);',
        '    endif',
        '    if (length(found_s) == 0 && (index(n, "salvage") || index(n, "scrap") || index(n, "wreckage")))',
        '      found_s = listappend(found_s, itm);',
        '    endif',
        '  endfor',
        '  if (length(found_o) == 0)',
        '    p:tell("Need 1x ore/mineral.");',
        '    return;',
        '  endif',
        '  if (length(found_s) == 0)',
        '    p:tell("Need 1x salvage/scrap.");',
        '    return;',
        '  endif',
        '  recycle(found_o[1]); recycle(found_s[1]);',
        '  r = create($thing); r.name = "crude wire";',
        '  r.description = "Rough conductive wire pulled from salvage and ore.";',
        '  move(r, p);',
        '  p:tell("You draw ore through salvage frames into crude wire. [+crude wire]");',
        '  return;',
        'endif',
        # PRE-FAB SHELTER KIT
        'if (index(tgt, "shelter") || index(tgt, "prefab") || index(tgt, "pre"))',
        '  found_m = {}; found_f = {};',
        '  for itm in (p.contents)',
        '    n = itm.name;',
        '    if (length(found_m) == 0 && index(n, "inert metal"))',
        '      found_m = listappend(found_m, itm);',
        '    endif',
        '    if (length(found_f) < 2 && (index(n, "fiber") || index(n, "plant")))',
        '      found_f = listappend(found_f, itm);',
        '    endif',
        '  endfor',
        '  if (length(found_m) == 0)',
        '    p:tell("Need 1x inert metal.");',
        '    return;',
        '  endif',
        '  if (length(found_f) < 2)',
        '    p:tell("Need 2x fiber. Have: " + tostr(length(found_f)));',
        '    return;',
        '  endif',
        '  recycle(found_m[1]); recycle(found_f[1]); recycle(found_f[2]);',
        '  r = create($thing); r.name = "pre-fab shelter kit";',
        '  r.description = "A collapsed alloy-frame shelter with fiber panels. Type \'place shelter\' to deploy.";',
        '  move(r, p);',
        '  p:tell("You assemble metal frame and fiber panels into a pre-fab shelter kit. [+shelter kit]");',
        '  return;',
        'endif',
    ] + MACHETE_RECIPE + RIFLE_RECIPE + HIDE_ARMOR_RECIPE + SC_RECIPE + [
        'p:tell("Unknown recipe: \'" + tgt + "\'");',
        'p:tell("Type \'craft\' to see available recipes.");',
    ]


def main():
    s = connect()
    print('Connected.', flush=True)

    # ── 1. Create $equipment prototype ────────────────────────────────────────
    print('\n=== Create $equipment prototype ===', flush=True)
    out = ev(s, 'player:tell("EQ_EXISTS=" + tostr("equipment" in properties(#0)))', wait=0.7)
    eq_exists = '1' in out.strip()[-10:]
    eq_num = None
    if eq_exists:
        out2 = ev(s, 'player:tell("OBJNUM=" + tostr(#0.equipment))', wait=0.7)
        existing = extract_num(out2)
        if existing and existing > 0:
            eq_num = existing
            print(f'  $equipment already exists: #{eq_num}', flush=True)
    if eq_num is None:
        add_verb(s, f'#{PLAYER}', '"_eq_setup"', 'none none none')
        program_verb(s, f'#{PLAYER}', '_eq_setup', [
            '"Create $equipment prototype and register on #0.";',
            'if (!("equipment" in properties(#0)))',
            '  add_property(#0, "equipment", $nothing, {player, "rw"});',
            'endif',
            'if (!valid(#0.equipment))',
            '  eq = create($thing);',
            '  eq.name = "equipment prototype";',
            '  add_property(eq, "eq_slot", "", {player, "rw"});',
            '  add_property(eq, "eq_type", "", {player, "rw"});',
            '  add_property(eq, "eq_tohit", 0, {player, "rw"});',
            '  add_property(eq, "eq_defense", 0, {player, "rw"});',
            '  add_property(eq, "eq_dodge", 0, {player, "rw"});',
            '  add_property(eq, "eq_dmg_bonus", 0, {player, "rw"});',
            '  add_property(eq, "eq_hp_bonus", 0, {player, "rw"});',
            '  add_property(eq, "eq_stam_bonus", 0, {player, "rw"});',
            '  add_property(eq, "eq_clarity_bonus", 0, {player, "rw"});',
            '  add_property(eq, "eq_aggr_bonus", 0, {player, "rw"});',
            '  add_property(eq, "eq_actions", {}, {player, "rw"});',
            '  #0.equipment = eq;',
            'endif',
            'player:tell("OBJNUM=" + tostr(#0.equipment));',
        ])
        out3 = send(s, '_eq_setup', wait=3.0)
        eq_num = extract_num(out3)
        if not eq_num:
            print(f'  ERROR creating $equipment: {repr(out3[-120:])}', flush=True)
            s.close(); return
        print(f'  $equipment = #{eq_num}', flush=True)

    # ── 2. Add slot properties to $player ─────────────────────────────────────
    print('\n=== Add slot properties to $player ===', flush=True)
    for prop in ['w_weapon', 'w_armor', 'w_gadget', 'w_special']:
        out = ev(s, f'player:tell("{prop}" in properties($player))', wait=0.7)
        if '1' in out.strip()[-5:]:
            print(f'  {prop} already exists', flush=True)
        else:
            ev(s, f'add_property($player, "{prop}", $nothing, {{player, "rw"}})', wait=0.8)
            print(f'  Created {prop}', flush=True)

    # ── 3. Internal helper verbs ──────────────────────────────────────────────
    print('\n=== _apply_stats / _unequip_stats ===', flush=True)
    add_verb(s, f'#{PLAYER}', '"_apply_stats"', 'any none none')
    program_verb(s, f'#{PLAYER}', '_apply_stats', APPLY_STATS_VERB)
    add_verb(s, f'#{PLAYER}', '"_unequip_stats"', 'any none none')
    program_verb(s, f'#{PLAYER}', '_unequip_stats', UNEQUIP_STATS_VERB)

    # ── 4. Equipment verbs ────────────────────────────────────────────────────
    print('\n=== wield verb ===', flush=True)
    add_verb(s, f'#{PLAYER}', '"wield"', 'any none none')
    program_verb(s, f'#{PLAYER}', 'wield', WIELD_VERB)

    print('\n=== wear verb ===', flush=True)
    add_verb(s, f'#{PLAYER}', '"wear"', 'any none none')
    program_verb(s, f'#{PLAYER}', 'wear', WEAR_VERB)

    print('\n=== equip verb ===', flush=True)
    add_verb(s, f'#{PLAYER}', '"equip"', 'any none none')
    program_verb(s, f'#{PLAYER}', 'equip', EQUIP_VERB)

    print('\n=== remove verb ===', flush=True)
    # Note: 'remove' may already exist on parent — add on #6 specifically
    add_verb(s, f'#{PLAYER}', '"remove"', 'any none none')
    program_verb(s, f'#{PLAYER}', 'remove', REMOVE_VERB)

    print('\n=== gear verb ===', flush=True)
    add_verb(s, f'#{PLAYER}', '"gear"', 'none none none')
    program_verb(s, f'#{PLAYER}', 'gear', GEAR_VERB)

    print('\n=== actions verb ===', flush=True)
    add_verb(s, f'#{PLAYER}', '"actions"', 'none none none')
    program_verb(s, f'#{PLAYER}', 'actions', ACTIONS_VERB)

    # ── 5. Modified combat verbs ──────────────────────────────────────────────
    print('\n=== Modified swing (weapon bonuses) ===', flush=True)
    program_verb(s, f'#{PLAYER}', 'swing', SWING_VERB_V2)

    print('\n=== Modified fire (ranged weapon) ===', flush=True)
    program_verb(s, f'#{PLAYER}', 'fire', FIRE_VERB_V2)

    print('\n=== Modified cr_retaliate (armor defense) ===', flush=True)
    program_verb(s, f'#{PLAYER}', 'cr_retaliate', CR_RETALIATE_V2)

    # ── 6. Updated craft verb ─────────────────────────────────────────────────
    print('\n=== Updated craft verb (equipment recipes) ===', flush=True)
    program_verb(s, f'#{PLAYER}', 'craft', build_craft_verb())

    # ── 7. Save ───────────────────────────────────────────────────────────────
    out = send(s, '@dump-database', wait=3.0)
    print(f'\nSave: {out.strip()[:60]}', flush=True)

    s.close()
    print('\nPhase 12 (Equipment) deployed.', flush=True)


if __name__ == '__main__':
    main()
