# Wayfar 1444 — TODO
# Goal: faithful recreation of the original 2010-2016 game per wiki
# Ordered by dependency chain — each item unblocks the ones below it

## Phase 1 — Foundation (these unblock everything else)

- [x] **#19b** Fix biomes — 5 major (Mountain/Forest/Desert/Jungle/Underwater) + 2 dangerous overlays (Fungal Zone/Volcanic)
- [x] **#8** Skill tree — THE critical dependency. 19 categories per wiki with exact SP costs and prereq chains. SP earned from actions (not credits). SP cap 2500 (+100/reroll to 3500). `score`/`skills` to view/purchase. Skills grant commands: PUNCH/KICK (Self Defense), BANDAGE (First Aid), HACK (Novice Hacker), SURVEY (Terrain Details), DISCOVER (Unpaid Cartographer), PURIFY (Better Materials), IMPROVISE (Improvisation), FOCUS (Situational Awareness), etc. Replaces current 8-skill credit system entirely.
- [x] **#42** Resource classes — 4 types each with own starter tool and material tiers. Minerals: inert metal → solid-phase → responsive → transuranic + sand variants. Organics: native fiber → native lumber → adaptive-phase fiber + berries/fungus/tubers. Energy: solar kretherson → thermal → dense thermal → intrinsic field. Water: unpurified water. Each class has a harvesting tool progression.
- [ ] **#12** Expanded crafting tools — unlocks the entire item tree. Wiki lists 8+ tools: structure crafting tool (buildings, sector center), equipment crafting tool (weapons, armor, gadgets), defensive crafting tool (turrets, shields), micro-bot crafting tool (robots), chemistry tool, food processor, maker block, cooking fire, engineering tool (automation), electronics processor (chips, AI), component crafting tool. Each has own recipe list per wiki. `list <tool>` shows recipes.

## Phase 2 — Core Systems (depend on Phase 1)

- [ ] **#41** Sector center recipe fix — needs structure crafting tool from #12. Wiki recipe: 2x simple structure base + 10x inert beam + 8x inert siding + 4x structure power core. Complexity 85.0. Up to 5 per player.
- [ ] **#14** Item quality — resources get quality 0-100+ on harvest (varies by tool quality and skill). Crafted item quality = avg ingredient quality + skill bonus. Refining converts bulk low-quality → fewer high-quality. Core to endgame loop.
- [ ] **#24** Material processor — tool (3x weak power emitter + 4x solid-phase metal + 4x inert casing). Raw → crafting materials: fiber cloth, solid-phase alloy, rare earth metal, polymer brick, electronics-grade silica, ceramic plate, nano-silk fabric etc. Needed for advanced crafting.
- [ ] **#43** Building stats — buildings have crime/civ/econ/rec/ind ratings. Ingredient quality affects building quality.
- [ ] **#9b** Combat polish — dice regen over time; Nourished effect (eating → bonus dice + max HP + faster regen); health does NOT regen naturally (heal manually per wiki); `ST` shows active effects.
- [ ] **#6** Creatures — biome-specific wildlife (carnivores/herbivores); named bosses (Mother Muex); catbug; loot varies by species; creature AI roaming; `CON` assessment.
- [ ] **#44** Item degradation — weapons wear with use, armor degrades on damage. `REPAIR <item>` with the crafting tool that made it.

## Phase 3 — Progression & Economy (depend on skills + crafting tools)

- [ ] **#15** Reroll/ascension — complete background victory condition → reroll points. On reroll: lose skills/SP, keep buildings/vehicles/inventory. Respawn at Central Control. `forget <skill>` refunds 75% SP.
- [ ] **#17** Jobs — ~30 repeatable achievements per wiki (FARMER, FACTORIUM LABOR, FLORA CATALOG, CENTER OF ATTENTION, PLANETARY HERO, etc.). Each awards SP and/or credits with repeat limits.
- [ ] **#16** Exploration — `EXPLORE` fills room 0-100%. At 100%: `MEMORIZE` (fast TRAVEL), `DISCOVER` (req Unpaid Cartographer). Terrain surveyor income. Feeds Botanist and Lab Tech backgrounds.
- [ ] **#31** Medical — `USE BANDAGE` / `BANDAGE` (First Aid skill); infirmary with clinic (auto-heal, diagnose diseases); `ASSIST <ally>` party healing; e-med tools (clarity roll).
- [ ] **#32** Status effects — bleeding (bandages/coagulant), burns (reduced dice pools, salves/patches), diseases (from biomes, azocillin/antitoxin/omni-vaccine).
- [ ] **#30** Weapon modules — module capacity on weapons; permanently installed; stat bonuses.
- [ ] **#25** Blueprints — tools have default + discoverable blueprints. `LOAD <chip> onto <tool>` / `DOWNLOAD <tool>`. Blank chips from electronics processor. `lookup <thing> with datapad`.
- [ ] **#23** Refining — 3 buildings: refinery (minerals), organic processing plant, nuclear enrichment plant. Mass-add → process → fewer over-maxed quality units.
- [ ] **#20** Governor's office verbs — citizens/population, exile, govern, sectormap, construction, buildings, resources, colony, events/history, rollcall, collection, mods/modules.

## Phase 4 — World & Content

- [ ] **#4** Communications — `say` (local), `chat` (global chatnet), `chatnet history`, `page` (private), `who`; additional nets: critternet/griefnet/mailnet/comedynet (toggleable + history); `corp` chat.
- [ ] **#18** Central Complex expansion — expand starting area into full station. Ship refueling, smartpad shop, medical kits, colony dispatch + link-up terminals.
- [ ] **#7** Multi-planet — different biome ratios per planet. Shuttle/drop pod travel. 5 solar systems (DSO-12 first).
- [ ] **#21** Weather — visible in room descriptions, affects gameplay.
- [ ] **#34** Farming — seeding tool, farm plots, agricultural pod building, landslide farming harvestor.
- [ ] **#35** Colony beacon — other players link-up to your colony via terminal.
- [ ] **#37** Fishing — wooden fishing rig, salt water fishing gear; CAREER ANGLER job.
- [ ] **#38** Artifacts & research — Laboratory building; research q-locked items; odd trinket → relic; feeds Lab Tech/Botanist backgrounds.
- [ ] **#45** NPC settlements — establish organically on planets; pirate outposts, faction bases (lootable), droid factories.
- [ ] **#46** Points of interest — black markets, moons (blueprints + rare resources).

## Phase 5 — Advanced / Endgame

- [ ] **#26** Hacking — smartpads, HACK command, q-chip programs, outlaw status.
- [ ] **#27** Automated crafting — engineering tool machines with input/output hoppers.
- [ ] **#28** Vehicles — q-cycle (no skill), land (Driving), aircraft (Flying); vehicle assembly station.
- [ ] **#29** Starships — starship complex, assembly tool; ships = rooms; warp gates; asteroid mining.
- [ ] **#33** Implants — augmentations from black markets.
- [ ] **#36** Robots — micro-bot tool, robotic fabrication table, robot control hand-pad.
- [ ] **#39** Factions — sector allegiance, faction HQ, corp chat, political systems.
- [ ] **#40** Black markets — 6 randomized shop types per planet.

## Bugs / Cosmetic

- [ ] **#10** Silence Heart Of God `#150` division-by-zero noise

## Completed

- [x] Wiki accuracy pass — backgrounds (Ranger/Fabricator/Retiree/Student/Lab Tech/Botanist), resource names (inert metal/native fiber/unpurified water/salvaged components), craft syntax (`craft X on <tool>`), commands (CREWHIRE/CREWFIRE/SURVEY), 8-direction movement, 12hr worker delivery, wiki recipes
- [x] New player flow — Shuttle → Commerce Main Junction → Complex-Alpha Mall Lobby → background → DISPATCH → drop pod to Kepler-7
- [x] Equipment slots — weapon/armor/gadget/special; WIELD/WEAR/EQUIP/REMOVE/GEAR/ACTIONS; combat integration
- [x] Harvesting tools — WIELD → SURVEY/SCAN → CONFIGURE → HARVEST (2x yield)
- [x] NPC workers — CREWHIRE/CREWFIRE; 12hr delivery; 50-item stockpile cap
- [x] Per-player colonies — sector center (plaza/governor/factorium); colony/enter/out/labor
- [x] CAC economy — sell/balance/prices; quality affects price
- [x] Procedural world — 7 Perlin biomes; on-demand rooms; ANSI map; 8-direction movement
- [x] Survival — hunger/health/stamina decay; heartbeat; death/respawn
- [x] Combat basics — dice pools; KILL/SWING/FIRE/TAC/CON; weapon/armor bonuses; creatures + loot
- [x] Crafting — basic tool wiki recipes; item quality on harvest
- [x] Connection — create command, @quit, error suppression
