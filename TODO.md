# Wayfar 1444 — TODO

## Phase 1 — Survival (make the core loop match wiki design)

- [x] **#19** Correct biome names — Mountain/Forest/Desert/Jungle/Volcanic with wiki-accurate descriptions, colors, map chars, resource mapping
- [x] **#11** Equipment slots — weapon/armor/gadget/special slots; WIELD/WEAR/EQUIP/REMOVE/GEAR/ACTIONS verbs; $equipment prototype; combat integration (tohit/dmg/defense/dodge); starter recipes (machete/rifle/hide armor)
- [x] **#13** Harvesting tools — WIELD tool → SCAN (show nodes) → CONFIGURE (target type) → HARVEST (2x yield vs hand-gather); starter ion-driven mineral collector; h_resource property on $equipment
- [ ] **#14** Item quality — resources/items have quality 0–100+; crafting skill affects output quality
- [ ] **#12** Expanded crafting tools — structure tool, equipment tool, food processor, maker block, cooking fire; each with own recipe list per wiki
- [ ] **#16** Exploration — EXPLORE fills room 0–100%; MEMORIZE (fast TRAVEL); DISCOVER (Unpaid Cartographer skill); terrain surveyor income
- [ ] **#20** Governor's office verbs — citizens, exile, govern, sectormap, construction rights, buildings, resources, colony, events/history, rollcall, collection, mods
- [ ] **#4** Test/fix CHATNET/CHAT comms (verbs exist on $player but untested)
- [ ] **#22** Communication nets — chatnet history, critternet, griefnet, mailnet, comedynet, corp chat; toggle on/off

## Phase 2 — Combat

- [ ] **#9** Dice pool combat — stamina dice (SWING), clarity dice (FIRE), aggression dice (damage); KILL/ST/TAC/CON/ACTIONS; dice regen; Nourished bonus
- [ ] **#6** NPCs/creatures — hostile fauna (carnivores/herbivores/bosses like Mother Muex), wildlife roaming, loot drops
- [ ] **#31** Medical system — bandages (First Aid skill), health injectors, infirmary building with clinic; ASSIST for party healing; e-med tools
- [ ] **#32** Status effects — bleeding (bandages/coagulant), burns (salves/patches → reduced dice pools), diseases (azocillin/antitoxin/omni-vaccine)
- [ ] **#30** Weapon modules — module capacity on weapons; permanently installed; stat bonuses

## Phase 3 — Progression & Economy

- [ ] **#8** Full skill tree — 19 categories per wiki, SP from actions, prereq chains, SP cap 2500 (+100/reroll to 3500); replace current 8-skill system
- [ ] **#15** Reroll/ascension — background victory conditions earn reroll points; lose skills/SP, keep buildings/vehicles/inventory; new background
- [ ] **#17** Jobs system — ~30 repeatable achievements awarding SP/credits (FARMER, FACTORIUM LABOR, FLORA CATALOG, CENTER OF ATTENTION, etc.)
- [ ] **#23** Refining — refinery (minerals), organic processing plant, nuclear enrichment plant; low-quality bulk → high-quality refined
- [ ] **#24** Material processor — raw resources → crafting materials (fiber cloth, solid-phase alloy, rare earth, polymer, silica, etc.)
- [ ] **#25** Blueprint system — LOAD chip onto tool / DOWNLOAD; blank chips from electronics processor; found at pirate bases

## Phase 4 — World & Content

- [ ] **#7** Second planet — different biome ratios, unique resources; drop pod travel
- [ ] **#18** Central Complex — space station starting hub (DSO-12); mall, terminals, shops, dispatch
- [ ] **#21** Weather system — affects room descriptions and gameplay
- [ ] **#34** Farming — seeding tool, farm plots, agricultural pod building; discovered seeds
- [ ] **#35** Colony beacon — let other players link-up to your colony
- [ ] **#37** Fishing — fishing gear, alien waters, CAREER ANGLER job
- [ ] **#38** Artifacts & research — Laboratory building; research q-locked items → relics, chips, equipment

## Phase 5 — Advanced / Endgame

- [ ] **#26** Hacking — smartpads, HACK command, q-chip programs, outlaw status
- [ ] **#27** Automated crafting — machines with input/output hoppers; engineering tool recipes
- [ ] **#28** Vehicles — q-cycle, land vehicles (Driving), aircraft (Flying); vehicle assembly station
- [ ] **#29** Starships — starship complex, assembly tool; ships = rooms (bridge/generator/turrets/engineering); warp gates
- [ ] **#33** Implants — augmentations from black markets (damage resistance, hacking bonuses, drug release)
- [ ] **#36** Robots — micro-bot tool (medical dog), robotic fabrication table (androids); robot control
- [ ] **#39** Faction system — sector allegiance, faction HQ, corp chat, political systems
- [ ] **#40** Black markets — 6 randomized shop types per planet

## Bugs / Cosmetic

- [ ] **#10** Silence Heart Of God `#150` division-by-zero noise

## Completed

- [x] **Redesign E** NPC workers — `hire <ore|fiber|water|salvage>` (100 cr, max 3); `fire <job>`; `workers` shows workforce + stockpile/50; auto-gather on 5-min tick; stockpile cap 50; `sell all` from factorium
- [x] **Redesign D** Per-player colonies — `place sector center` → 3-room complex; `colony`/`enter`/`out`/`labor` verbs; `$sc_room` #821
- [x] **Redesign C** Skill system — 8 skills, 2 tiers; survival_1 (+3 HP on eat), commerce_1/2 (sell bonuses), combat_1 (+5 HP max)
- [x] **Redesign B** Backgrounds — 5 backgrounds at connect; stat bonuses; scavenger +50% salvage
- [x] **Redesign A** CAC economy — sell/balance/prices/status; credits on $player
- [x] Building system — pre-fab shelter kit; `place`/`buildings`; $building #117
- [x] Food/water consumables — craft ration bar + water canteen; eat/drink restore HP+Nourished
- [x] Resource nodes — `$ods:populate` + `gather [type]` in wilderness
- [x] Player survival stats — hunger/health/stamina; vitals/eat/drink/rest/build/treat/status
- [x] Heartbeat decay + death/respawn — #545; 5-min tick; starvation kills; respawn #459
- [x] Perlin noise C extension (`perlin_2d`)
- [x] `chr()` / `ord()` C extensions
- [x] On-demand room spawning via `$ods` (#458)
- [x] Coordinate movement (n/s/e/w on $player #6)
- [x] ANSI 7x5 overhead map (`look_self` on $wroom #452)
- [x] 5-biome terrain on Kepler-7 (#457)
- [x] Impact Site Zero at (0,0)
- [x] Resource node prototypes ($ore_node, $fiber_node, $water_node, $salvage_node)
- [x] Fix duplicate movement render
- [x] Fix planet name `[]` in room headers
