# Wayfar 1444 — TODO
# Goal: faithful recreation of the original 2010-2016 game per wiki

## Phase 1 — Core Survival Loop

- [x] **#19b** Fix biomes — 5 major (Mountain/Forest/Desert/Jungle/Underwater) + 2 dangerous overlays (Fungal Zone/Volcanic, ~5% rare 1-tile); wiki-accurate descriptions, colors, map chars, resource mapping
- [ ] **#14** Item quality — resources get quality 0-100+ on harvest; crafting skill affects output; refining converts bulk low-quality → fewer high-quality (wiki: quality is core to endgame)
- [ ] **#12** Expanded crafting tools — wiki lists 8+ tools each with own recipes: structure crafting tool (colony buildings, sector center), equipment crafting tool (weapons, armor, gadgets), defensive crafting tool, micro-bot crafting tool, chemistry tool, food processor, maker block, cooking fire, engineering tool, electronics processor, component crafting tool; `craft <item> on <tool>` syntax; `list <tool>` shows recipes
- [ ] **#41** Sector center recipe fix — wiki: needs structure crafting tool, not basic tool; recipe: 2x simple structure base + 10x inert beam + 8x inert siding + 4x structure power core; complexity 85.0; up to 5 per player
- [ ] **#16** Exploration — `EXPLORE` fills room 0-100%; at 100%: `MEMORIZE` (fast `TRAVEL`), `DISCOVER` (req Unpaid Cartographer skill) finds artifacts/specimens/features; terrain surveyor equipped → `interface terrain surveyor with terminal` for credits
- [ ] **#42** Resource classes — wiki has 4 classes each with own starter harvesting tool: minerals (ion-driven mineral collector), organics (cheap orgo-reaper), energy/kretherson (hand-held energy absorption unit), water (atmo-thrasher condenser); each class has common→rare tiers (e.g. inert metal → solid-phase → responsive → transuranic); sand variants (regular/red/black/pink)
- [ ] **#20** Governor's office verbs — citizens/population, exile, govern (sector allegiance), sectormap, construction (rights, off by default), buildings, resources, colony, events/history, rollcall, collection (NPC harvest config), mods/modules + activate
- [ ] **#43** Building stats — wiki: buildings have crime/civ/econ/rec/ind ratings; ingredient quality affects building quality
- [ ] **#4** CHATNET/CHAT — `say` (local), `chat` (global chatnet), `chatnet history`, `page <person> <message>` (private), `who` (connected players + idle)
- [ ] **#22** Communication nets — critternet, griefnet, mailnet, comedynet all toggleable with history; `corp` chat for corporations

## Phase 2 — Combat & Creatures (wiki: dice pool system)

- [ ] **#9b** Combat polish — dice regen over time (not just on rest); Nourished effect from eating (bonus dice rolls + max health + faster regen); health does NOT regen (must heal manually per wiki); `ST` shows health + dice + active effects; each attack consumes dice
- [ ] **#6** Creatures — wiki: biome-specific wildlife (carnivores/herbivores); named bosses (Mother Muex has territory); catbug (can pet); loot varies by species; `CON` to assess before engaging; creature AI roaming
- [ ] **#31** Medical — `USE BANDAGE` applies Bandaged effect (health ticks up); `BANDAGE` command from First Aid skill; infirmary building with clinic room (auto-heal, diagnose/cure diseases); `ASSIST <ally>` for party healing; e-med tools heal via clarity roll; fibrous bandage craftable on basic tool
- [ ] **#32** Status effects — bleeding (slashing/bullet → health loss over time, fix: bandages/coagulant), burns (thermal/plasma/laser → reduced dice pools AND regen rate, fix: salves/fungal salve), diseases (from biomes, fix: azocillin/antitoxin/omni-vaccine)
- [ ] **#30** Weapon modules — weapons have module capacity (points); modules permanently installed; stat bonuses (e.g. laser aiming module: +10 tohit, 25 capacity; craft: 1x energy + 1x inert wiring + 2x electronics-grade silica + 2x solid-phase metal)
- [ ] **#44** Item degradation — weapons wear with use, armor degrades on damage absorption; `REPAIR <item>` while holding the crafting tool that made it

## Phase 3 — Progression (wiki: SP-based, 19 skill categories)

- [ ] **#8** Full skill tree — 19 categories per wiki with exact SP costs and prereq chains; SP earned from actions (not credits); SP cap starts at 2500 (+100/reroll to 3500 max); `score` or `skills` to view/purchase; skills grant commands (PUNCH/KICK from Self Defense, BANDAGE from First Aid, HACK from Novice Hacker, SURVEY from Terrain Details, DISCOVER from Unpaid Cartographer, etc.)
- [ ] **#15** Reroll/ascension — complete background victory condition → earn reroll points; on reroll: lose skills/SP, keep buildings/vehicles/inventory; respawn at Central Control Station; choose new background + gender; `forget <skill>` refunds 75% SP
- [ ] **#17** Jobs — wiki lists ~30 repeatable achievements (FARMER 0sp/10cr/100x, FACTORIUM LABOR 25sp/25cr/100x, FLORA CATALOG 50sp/100cr/5x, CENTER OF ATTENTION 250sp/0cr/1x, PLANETARY HERO 200sp/250cr/5x, etc.); punishment jobs (CHEATER -100sp/-15000cr); admin jobs (BUG HUNTER 2sp)
- [ ] **#23** Refining — 3 buildings: refinery (minerals), organic processing plant, nuclear enrichment plant; mass-add resources → processor tracks material quality equivalent → process → fewer over-maxed quality units; processor locks to one type until reset
- [ ] **#24** Material processor — tool (3x weak power emitter + 4x solid-phase metal + 4x inert casing); converts raw → crafting materials: fiber cloth, solid-phase alloy, rare earth metal, polymer brick, electronics-grade silica, ceramic plate, nano-silk fabric, etc.
- [ ] **#25** Blueprints — tools have default + discoverable blueprints; `LOAD <chip> onto <tool>` / `DOWNLOAD <tool>` to extract; blank blueprint chips from electronics processor; found at pirate bases, discoveries; `lookup <thing> with datapad` identifies which tool makes an item

## Phase 4 — World & Content

- [ ] **#18** Central Complex — space station in DSO-12 system; commerce main junction, mall lobby (already built as starting area — expand with shops); ship refueling; smartpad shop, medical kit shop; colony dispatch + link-up terminals
- [ ] **#7** Multi-planet — different biome ratios per planet making each unique; shuttle/drop pod travel between planets; 5 solar systems at launch (goal was 20)
- [ ] **#21** Weather — visible in room descriptions, affects gameplay
- [ ] **#34** Farming — seeding tool (given on landing per wiki); farm plots; agricultural pod building; landslide farming harvestor for crops; seeds discovered during exploration
- [ ] **#35** Colony beacon — `place beacon` at colony; other players use link-up terminal to join directly
- [ ] **#37** Fishing — wooden fishing rig (basic tool recipe), salt water fishing gear (equipment tool); alien waters; CAREER ANGLER job (200sp, haul 50 fish)
- [ ] **#38** Artifacts & research — Laboratory building; research q-locked items at terminal; odd trinket → relic, indecipherable q-disk → hacking chip, q-locked medical bay → e-med equipment; DISCOVER command feeds this system
- [ ] **#45** NPC settlements — wiki: NPC settlements establish organically on planets; pirate outposts, faction bases (lootable), droid factories
- [ ] **#46** Points of interest — black markets, moons (raid for blueprints + rare resources)

## Phase 5 — Advanced / Endgame

- [ ] **#26** Hacking — smartpads in gadget slot; `HACK` command (Novice Hacker skill); q-chip programs (y2k breaker, mega infiltrator, etc.); `LOAD <chip> ON <smartpad>`; outlaw status if observed; hackable: ships, control pads, building AI, matrix relays
- [ ] **#27** Automated crafting — engineering tool builds automation machines (automated material/electronics/industrial processor, equipment assembler, starship assembler); input/output hoppers; mature colony runs without player input
- [ ] **#28** Vehicles — q-cycle (no skill needed), land vehicles (Driving skill 100sp), aircraft (Flying skill 100sp); vehicle assembly station (equipment tool); vehicle lock systems (simplex→elite-tek); vehicle christening; `REPAIR`
- [ ] **#29** Starships — starship complex building; starship assembly tool; ships = rooms (bridge, generator, turret positions, engineering); crew mans turrets; warp gates (player-buildable); asteroid mining; life support; self-destruct; ship types: asteroid miner, orbital assembly ship, solar dropship, solar carrier
- [ ] **#33** Implants — augmentations from black markets; hack-pro (hacking bonus), impact dissipators (damage resistance); separate from gadget slot
- [ ] **#36** Robots — micro-bot tool (medical dog), robotic fabrication table (androids); robot control hand-pad; REAL STEEL job (robot arena combat)
- [ ] **#39** Factions — sector allegiance; faction HQ building (advanced structure tool); corp chat; political systems
- [ ] **#40** Black markets — 6 randomized shop types per planet: Implants, Munitions, Superior Equipment, Starships, Medical, Robots

## Bugs / Cosmetic

- [ ] **#10** Silence Heart Of God `#150` division-by-zero noise

## Completed

- [x] Wiki accuracy pass — backgrounds (Ranger/Fabricator/Retiree/Student/Lab Tech/Botanist), resource names (inert metal/native fiber/unpurified water/salvaged components), craft syntax (`craft X on <tool>`), commands (CREWHIRE/CREWFIRE/SURVEY), 8-direction movement, 12hr worker delivery, wiki recipes (machete/javelin/rifle/hide armor/soup/bandage/casing/backpack/shelter)
- [x] New player flow — Shuttle → Commerce Main Junction → Complex-Alpha Mall Lobby → background terminal → DISPATCH → drop pod to Kepler-7; `create <name> <password>` at login; starter items (basic crafting tool + ion-driven mineral collector + native fiber + inert metal)
- [x] Equipment slots — weapon/armor/gadget/special; WIELD/WEAR/EQUIP/REMOVE/GEAR/ACTIONS; $equipment prototype; combat integration (tohit/dmg/defense/dodge)
- [x] Harvesting tools — WIELD → SURVEY/SCAN → CONFIGURE → HARVEST (2x yield); ion-driven mineral collector starter
- [x] NPC workers — CREWHIRE/CREWFIRE (hire/fire aliases); 12hr delivery; 50-item stockpile cap; sell from factorium
- [x] Per-player colonies — sector center (3 rooms: plaza/governor/factorium); colony/enter/out/labor
- [x] CAC economy — sell/balance/prices; credits; quality affects sell price
- [x] Procedural world — Perlin biomes (Mountain/Forest/Desert/Jungle/Volcanic); on-demand rooms; ANSI 7x5 map; coordinate movement (8 directions)
- [x] Survival — hunger/health/stamina decay; heartbeat tick; death/respawn at Impact Site Zero
- [x] Combat basics — dice pools (stamina/clarity/aggression); KILL/SWING/FIRE/TAC/CON; weapon bonuses; armor defense+dodge; creature spawning + loot
- [x] Crafting — basic crafting tool recipes per wiki; item quality on harvest (10-50 random)
- [x] Connection fixes — suppressed HellCore error spam; @quit works
