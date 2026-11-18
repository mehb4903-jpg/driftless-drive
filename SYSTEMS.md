# Rampage Road (formerly Driftless Drive): how the systems work

Working notes for whoever picks this up next (including me after a context reset). Read this before touching the game.
Keep it current: when a system changes, update its section here in the same step.
Then copy it to the GitHub clone `/home/user/driftless-drive-repo` (branch `systems-notes`), commit and push.

## The basics

- V66: the game is called Rampage Road (title, menu heading, bank/mall/speedway names). Internal ids, room names and dd-* storage
  keys keep their old names on purpose, so saves and rooms carry over.

- **The game is one file**: `/home/user/driftless-drive/index.html` (~5,000 lines, ~450 KB). It is an HTML *fragment*: no `<html>/<head>/<body>`.
  three.js r128 from cdnjs, then one inline IIFE `<script>` with everything in it.
- **Published as** the artifact `https://claude.ai/artifact/CzE8DajCvedNAxTnHXTf1P`. Publish with the Artifact tool, `url` set to that link and
  `file_path` the index.html. Capabilities are carried forward automatically (room, user, db laps rules); don't pass `capabilities`.
  Small edits: `edits` on the publish call. Big ones: python patch script, then publish.
- **The user wants**: ship after every step, keep things playable on phones (touch buttons) and with a controller, multiplayer kept in sync.

## Two copies of the game

- **Source of truth:** the claude.ai artifact, built from `/home/user/driftless-drive/index.html` in the Claude session that writes
  these notes. Multiplayer there uses the artifact `room` capability (`claude.use('room')`, presence).
- **GitHub copy:** `mehb4903-jpg/driftless-drive` (`index.html` + `README.md`) is a standalone conversion made by a separate Claude
  session ("Export 3D game to HTML"). It swaps the room for PeerJS (WebRTC, `#room=` links) and is a full HTML document. It trails the
  artifact by a version or so, and that session also commits its own fixes there. Treat the two files as related, not identical.
- These notes describe the artifact version; everything except the networking layer applies to both.

## How to edit safely (learned the hard way)

- Pitfalls, short list: boot-time code must not touch a `const`/`let` declared later in the file (TDZ); never end an inserted
  fragment with a `//` comment when code follows on the same line; check a name is free before adding it (BK/BNK, gAt/gravAt, T as
  a local, `ar` in presence); `store()` only returns objects.

- Patch with python scripts in the scratchpad: `rep(old, new)` that asserts the anchor occurs exactly once, collect failures, write only
  if none failed. Anchors with `›`, `“`, `·` etc are real Unicode characters in the file, not `\u` escapes.
- **Never put a `//` comment on a line that continues afterwards.** A comment added at the end of a replacement swallows the rest of that
  line (`});`, a closing brace). This broke the build four or five times.
- **TDZ**: `setCar()` and the POI builders run at boot, before later `const`s are initialised. State that boot-time code touches must be
  declared early. There is a block "looks and kit you have bought" just before `let PARK = null, RIDE = null, walker = null` for this.
  `POSE` is declared there too. Builders that run at POI-build time (bMall, bBank, gasShop, bStation) may only use consts defined
  above them in the file (`GS`, `BNK`, `SHOPDEF`, `MALLI`, `BANKI` are placed accordingly). `makePerson`/`lookOf` are defined later:
  create people lazily at runtime (first frame you are near), never at build time.
- Name clashes: `BK` is the big-map scale. The bank object is `BNK`. `gAt` is the road-height cache; gravity is `gravAt`.
- Check after every patch: `bash /tmp/claude-0/-home-user/d920d492-d96f-500b-b07e-2e345c0fe66f/scratchpad/chk.sh` (extracts the script,
  `node --check`), then `boot.js` (headless load, prints page errors, `drive: true` if `window.__drive` exists).
- Rollback copies: `scratchpad/index.vNN.html` = the file as it was before version NN+1 work.

## Testing

- Playwright + swiftshader. Route `**/three.min.js` to `scratchpad/three.min.js`, abort Google Fonts. Click `#go` to start.
- `window.__drive` exposes almost everything (P, inp, sim(secs) = fixed steps without reading input, tick(dt) = one full frame incl.
  readInput/camera/HUD, setCar, unlock, travelTo(POI), POI, CITY, ACT, NET, GUN, HACK, H, BNK, GS, SHOPS, MONEY, ... grep the line
  `window.__drive = {`). `DTMAX.paused = true` stops the real frame loop while you script.
- Headless frames are slow (~4 fps): real-time things (setTimeout fades, hold-to-prone, pedestrians on the wall clock) need waits.
- Camera: fireGun shoots along the camera ray. After teleporting the player, `tick(0.001)` before aiming or the shot misses.
- Two-player: `scratchpad/mp2.js` has a mock room + virtual clock (`open(b, name)`, `run(A, B, secs)`). Copy its head into new tests.
- Bash commands time out at ~120 s: long tests go in the background or get split.

## World and regions

- Square island, flat city 20x20 blocks: `CITY.E = 1200`, block pitch `CITY.P = 120`, roads on lines `k*120 - 1200`, kerb at 8 m into
  a block, buildings start >= 11 m in. Central avenue at x = 0. `inCity(x, z, margin)`. `CITY.boxes[bi*20+bj]` = building boxes
  `[x0,x1,z0,z1,top]`. `BOXES` = other solid boxes (POIs, mall/bank walls; optional 6th value = bottom). `SOLIDS` = circles `[x,z,r,top]`.
- Reserved blocks: `CITY_RES` (bank [8,12], mall [12,8], police [11,9], city, park, diner [10,5], dealer, barn, observatory, trap, lookout).
- Far-off regions in the same coordinate space: Moon x 12000..36000 (`onMoon`), open space x > 36000 (`inSpace`, SPC), indoor regions
  x < -12000 (`inMall(x)` = any indoors; `inBank(x,z)` = z > 300). `regionOf(o)` returns 'out' | 'mall' | 'bank'.
  `terrainH` returns MALLI.y (60) for x < -12000.
- POIs: `defs` list in the POI IIFE (`['id', 'Name', 'blk'|'road'|'abs'|'fix'|'air', where, findRadius, builder]`). Builders get
  `(p, b, ln, gl)` = POI, body GB, line GB, glow GB; signs via `mallSign(text, w, h, bg, fg)` added to `p.grp`.

## Player, vehicles, on foot

- `P` = player state, `CAR` = current vehicle def from `CARS` (or `FOOTCAR`). `setCar(i)`, `toggleFoot()`/`getOut()`/`getIn()`, `PARK` =
  parked car while on foot. `stepPlayer` -> `stepFoot`/`stepUfo`/`stepHeli`/`stepSpace` or car physics. Fixed step `H_STEP`.
- Health: `HP` (vehicle), `PH` (person), `ARM.v` armour (soaks 70% on foot). `damage(d)`. Down on foot: respawn beside PARK after 10 s.
- Easter egg: names King Rello / Lil Marz (`EGGS`, `eggKey(name)`) make the on-foot model `buildClassic()`: the porch `sitMan` figure
  box for box, stood up and scaled 0.79, with the walker's rig. Passed as `fit.egg` into `makeCar('walker', ...)`.
- Stance `POSE.v` 0/1/2 (stand/crouch/prone): Ctrl tap/hold, touch `tFC`, pad D-pad down. `poseKey(down)`, `poseTick`, `stancePose`.
  Affects speed, camera height, muzzle height, spread, and NPC hit chance (`t.low`). Sent as presence `cr`.
- Camera: `updateCamera`; indoors/city it is pulled in front of walls by `camWalls()`/`camHits()`.

## Weapons

- `GUNS` index: 0 pistol, 1 SMG, 2 shotgun, 3 rifle, 4 fists (melee), 5 revolver, 6 micro SMG, 7 sawed-off, 8 assault rifle, 9 bazooka.
  `GUNSLOT` maps number keys 1..0. `OWN` = owned set (0-4 free). `GM` = box models per gun (index 4 empty). `gunMesh(i, view, att)`.
- `fireGun()`: melee -> `punch()`; rocket -> `launchRocket()`; else hitscan against target list `tg` (npcs, people via `peopleTargets`,
  remote players with head boxes). Headshot x3 rifle / x2 others. Aim assist pulls 10% toward targets inside a 12 degree cone.
- Attachments `ATT[gun] = {dot,long,supp,ext,grip,laser,fin}`, `ATTOWN`, `magOf(i)`, `refreshGuns()`, `laserFrame()`. Others see the
  gun in your hand with its parts: presence `ga` = `gaKey(i)`, rebuilt on their side by `remoteGunAtt(r, s)`. Scope overlay `#scope`
  (rifle or long scope), red dot overlay `#rdot` (first person + dot). `GUN.scoped`, `GUN.rdot`.
- Rockets/explosions: `ROCKETS`, `stepRockets`, `explode(x,y,z,mine)` (damages everyone in 7 m, shared via presence `bx`).

## People (NPCs)

- Pedestrians: pure function of the shared clock, `pedAt(bi,bj,k,t,o)`, 7 per block on the sidewalk loop (inset 9.7). Drawn near you
  (`PEOPLE.vis`). Hidden while an actor with the same src exists or `PEOPLE.hide`.
- Actors (`ACT`): people this client runs, shared to others via presence `ac` (rendered there as `REMA`). `spawnActor(src, x,y,z, yaw, seed,
  opts)`; states st 0 fight, 1 flee, 2 dead, 3 calm. `stepActor`, `hurtActor`, `hitPerson`, `peopleTargets(tg, R)`. Options: gun, hp, dmg,
  acc, slow, cop, wpn ('ar'|'sg'), cdm, heist, guard, police, look, tgt. Other players damage our actors via presence `adm`.
- Traffic: shared deterministic sim (`TR`, `trStep`, rail cars), bodies near you (`npcs`, `makeNpc`). Each car has a driver `n.drv`;
  shooting a car on foot -> `exitDriver(n)` -> driver actor fights. Car modes: 0 rail, 1 chase, 2 return, 4-6 beam/fall/wreck, 7 puppet, 8 abandoned.
- Cops: `copStep(a, t, dt)` = shared logic for any `a.cop` actor (LOS check `canSee`, bursts/shotgun, follow through doors via
  `copDoor(region, from)`, catch-up teleport for mall cops). `copShot`.
  - Mall police: `mallAlarm()` on gunfire in the mall; 4 officers rise from the fountain (120 hp, full strength).
  - Bank job police: `spawnPolice(n, where, tag)`, 70 hp, cdm 0.4 acc 0.55.
  - Bank guards: 40 hp, dmg 7, acc 0.6.

## Police and wanted stars

- `WANTED = { lv 0-3, last {x,z}, seenT, clearT, dispT }`. `wantedAtLeast(n)` (ignored indoors/space/moon/while down), `wantedSeen()`
  (refresh last-seen), `clearWanted(quiet)` (also on going down), `crimeKill(a)`.
- Running people over (`RUNHIT.t` set with MYHIT in the two car-hit paths): `crimeKill` counts kills in `WANTED.runs`; only 3 inside
  15 s give 1 star. Other civilian kills still give 1 star.
- Crimes: gunfire `witnessed(x,z)` (officer LOS within 70 m, any officer within 40 m, or within 110 m of the station) -> 1; killing a
  civilian -> 1; till/safe/ATM -> 1; hitting an officer, a police car, or the cashier -> 2; killing an officer -> lv+1 (min 2).
  "Was it me" detection: `MYHIT = performance.now()` is set by every damage path the player causes (hitPerson, explode, car hits);
  `hurtActor` treats a death within 60 ms as the player's kill.
- Station: `bStation` + `PSTN { x, z, y, offs[6] (idle officers, made lazily, `o.out` when deployed as actor 'so'+k), bays[4], box }`.
  Idle officers are targets (`pp.off`) -> `activateOfficer(o)`.
- Police cars `PCARS` (`newPcar`, `makePoliceCar` = white sedan + 'police' livery + light bar + POLICE text). States: parked, board
  (waiting for officers), drive, stop, wreck, gone. Crew count `c.crew` (officers inside are not actors). `stepPcar`: grid navigation
  `navPoint` (street lines `roadLine`), top speed `PC_MAX` = 85 km/h, unstick by reversing, bump/run over the player, `unloadCar` near you,
  officers re-board (`a.task = 'board'`, `boardStep`) if you drive off. `dmgPoliceCar` (160 hp).
- `dispatch()` runs at once on the first star, then every 2.5 s while live units < stars: station car + idle officers only if the
  station is within 320 m, else a patrol car (`patrol: true`, crew aboard) spawned 150-210 m away out of sight (max stars + 2), so the
  first unit reaches the scene in about 8-12 s (tested 7.8 s).
- Police actors: `policeOpts(lv, k)` (cop + police flags; 90 hp; damage/aim scale with stars). In `copStep`: stand down at 0 stars,
  board task, report sightings, and when they cannot see you they walk to `WANTED.last` instead of tracking you.
- Cop bubbles (V56): every active officer and crewed police car finds you inside `CB[lv]` (60/80/100 m) even without line of sight, and
  sees you with line of sight up to 160 m (`stepPcar` seesMe, `copStep`, a bubble pass in policeFrame). Each sighting calls wantedSeen().
- Losing them: `WANTED.crimeT` (set by every wantedAtLeast) gives a grace of 15 + 5*lv s, then unseen > `LOSE[lv]` (8/12/16 s) clears
  the stars. The old last-seen circle (`WR`) is no longer used for clearing. 20 s after clearing, units
  out of your way reset (station cars teleport home, patrols removed, officers back at their posts).
- Map: `policeBlips(g, k)` (cop dots, car squares, and a red bubble circle around each active unit while wanted). HUD: `#wanted` shows stars, `.srch` while searching.
- Targeting: aim assist weights cops 3x closer; heli/Blick lock-on gets `copTargets()` (wrappers with `copT`, `hitBy`).
- Shared stars: `wantedLink(now)` links you with the player you ride with (`RIDE`, or whoever sends `rw` = your id). The higher level is
  copied over when it rises; when the partner drops to 0 you clear too. Presence `wl` [lv, lastX, lastZ], `rw` ride target id.
- Multiplayer: police actors go out as normal actors (`ac`, flag q[11]); moving police cars in presence `pc`; others render them
  (`REMPC`) and hide their own parked copy with the same id.

## Money and robbery

- `MONEY.v` (localStorage dd-cash), `addCash(n)`, HUD `#cash`. `dropCash(x,y,z,amt,piles)` -> `CASH` piles, shared via presence `cd`/`cg`.
  Deaths drop cash (people; players drop 25%).
- ATMs (`ATMS`, 18 on sidewalks) -> `tryRob()` -> PIN mini-game `HACK` (`hackKey`, `hackSubmit`, `hackFail`; `HACK.kind` = 'atm' | 'gate' |
  'safe'). Empty for 5 min, shared via presence `at`.
- Gas station (Halfway Diner, `gasShop()` + `GS`): hollow building with a back door (`GS.back`), cashier hold-up by aiming a gun (6 s),
  safe in the back room = $420 (`crackSafe`/`safeCracked`). Security camera `GS.cam` over the door: `camLive()`; cover it (`coverCam`, prompt
  `#camP`) or shoot it (`camShot`, target `pp.cam`). A robbery seen by a live camera = 1 star at once (`robbed()`); otherwise the cashier
  starts a 15 s report timer (`GS.report`). One punch knocks him out (`cashierHit`, melee) and cancels it; a bullet kills him (2 stars only
  if the camera is live). Shooting the camera sends him running for the back door (`GS.flee`); if he gets out he reports you (1 star) and is
  gone until restock. Timers (till, safe, camera broken, camera covered) shared via presence `gs` [reg, safe, camBroke, camCover].
- Bank job (`H`, `heistFrame`, `startHeist`, `heistStage`): ring outside Rampage Savings, 10 s lobby, stages 1 guards, 2 gate keypad,
  3 drill (100 s, runs while crew is inside), crew members who go down come back up at the bank doors, 4 pallets, 5 drop-off at (360,-120), 6 done ($15,000 split), 7 failed (12 min).
  Lowest crew id runs it and broadcasts `hs`; lobby via `hl`; non-leader gate hack via `hk`; closed-until via `bk`. Interior at BANKI.

## Mall and shops

- Mall interior at MALLI; doors via `mallGo(inside)`. Shops in `SHOPDEF` (units 0-3 west, 5-6 east), props via `shopProps`, keepers made
  lazily in `shopBuild()`. Menu: `openShop`, `drawShop`, `shopStock(def, cat)` returning rows `{name, right, blurb, dim, buy}`.
  - Iron Works: guns, rockets, armour. Threads/Sole Search: `WEAR` list -> `FIT` outfit -> `rebuildWalker()`.
  - Tactical Bench: `MODS`, `FINS`, on the gun in hand. Wrap City: `DECAL` -> `DEC[carId]` -> `applyLook(model, car, look)`.
  - Torque Shop: `TUNE` -> `UPG[carId]` -> `applyUpg(car)` (accel, vmax, grip, brk, nos). Nitrous: `CAR.nos`, `P.nos`.
  - Shop items apply to `tgtCar()` = parked car or `LASTCAR`.
- Saved in localStorage: dd-cash, dd-guns, dd-rockets, dd-armour, dd-fit, dd-ward, dd-att, dd-attown, dd-upg, dd-dec.

## Homes and furniture (V54)
- `HDEF` (prices, style, w×d), `HSTY` (colours per style), `HOUSES` (runtime records). Built during the POI pass:
  - Hill plots use POI kind `'hill'` (`a = [x, z]`, height = terrain, levelled by PADS like 'road'/'abs'): hN1 Pine Cabin 250k, hN2 Harbour Lookout 310k (north harbour), hS1 Ridge Lodge 520k, hS2 Cliffside Modern 780k (south harbour).
  - City plots are 'blk' entries in `CITY_RES`: hC1 Brick Townhouse 275k [6,6], hC2 Corner Loft 420k [14,11], hC3 Garden Villa 1.15M [12,14] (pool), pent Skyline Penthouse 2.5M [9,6].
- `houseShell(p, b, gl, id, x, y, z, H, noDoor)`: walls in BOXES, doorway on the +z wall with a door mesh and `doorBox` (in BOXES until owned), floor, roof (gable or flat), ceiling lights, storage crate at the back-left (`h.bin`, a SOLIDS circle). Record: `{id, def, x, z, y, door, bin, in:{x0,x1,z0,z1,y}, doorBox, doorM, grp, pieces, built, noDoor}`. NB: never name a local `T` (it shadows three.js); the wall thickness is `TK`.
- `homeRing` puts the green buy ring + price sign at `h.ring` (`h.ringY`). `bPent`: a 60 m glass tower (BOXES, its top is walkable) with the penthouse shell on the roof (`noDoor`: door never opens). Owned: walking into the lobby doors (`h.lobby`) lifts you up to `h.up`; the lift spot inside (`h.elev`) takes you down (`homeGo`, flash fade).
- State `HOME = { own: Set (dd-homes), inv: {furnId: count} (dd-inv), furn: {houseId: [[t, x, y, z, yaw]]} (dd-furn, relative to h.x/h.z/h.in.y) }`, `saveHome()`. Local to the device, not synced in multiplayer (other players see doors closed).
- `homeFrame(dt)` (in runFrame after policeFrame): builds owned homes within 500 m (`buildHome`: removes doorBox, hides door, rebuilds pieces, greys the ring); sets `HOMEACT` = buy / mine / bin / move (aimed piece within 4.5 m of the player) and the `#homeP` prompt; lobby/lift checks.
- `homeKey()` is first in the F chain (and gamepad D-pad up): place / buy / open storage / pick up. `homeStore()` = B key / gamepad Y: store the aimed piece or the one being moved.
- Furniture: `FURN` catalogue (21 pieces, `{id, name, cat, price, w, d, h, build(b), solid}`, GB boxes centred, front -z), `fgeo(id)` caches geometry. Placed pieces: mesh in `h.grp` with `userData.pc`, plus a SOLIDS circle (not rugs). `addPiece` / `dropPiece` / `saveFurn`.
- Furniture shop = `SHOPDEF[7]` Home & Co ('furn'), stock from `furnStock(cat)` (adds to HOME.inv). Showroom pieces drawn in shopBuild. Storage menu: `binShop(h)` opens a fake shop `{bin:true, h, def:{id:'bin'}}`; shopFrame does not auto-close `bin` shops; `binStock` rows start placing.
- Placement (3008-style, yaw only): `PLACE = {on, t, yaw, h, ghost, from, ok, x, y, z}`; `placeFrame` raycasts from the camera along the aim (`aimRay`, far 16) against `h.grp`: a hit face with normal.y > 0.6 stacks on top, else the floor plane. Position clamped inside `h.in` with the rotated half extents; ok only if near the aim point, < 8 m from the player, under the ceiling. Ghost translucent, red when not ok. Rotate: Q/E (Shift fine), wheel / ⟲⟳ buttons / LB RB 15°. Place: click, F, gamepad A, Place button. Cancel: Esc, gamepad B (puts a moved piece back). While placing, firing and Q/E roll are suppressed.
- Test: scratchpad `home.js` (buy, walk in, shop, storage, place, stack, lift, reload) and `home2.js` (stack, B store, screenshots). Seed localStorage dd-homes/dd-inv/dd-furn then reload to skip buying.

## Waterfall bunker, map table, orbital strike (V55-V56)
- Bunker = home id 'bunk' ($2M) in `HDEF`, POI kind 'hill' at (830, 2000), builder `bBunker` (rock face, waterfall planes with a scrolling
  canvas texture `BUNK.wtex`, plunge pool, steel shutter `BUNK.shut`/`shutBox` until owned) + `bunkInside` (own region `BUNKI` x -24000,
  z -700, y 60; `inBunk(x,z)` = x < -12000 && z < -300; excluded from mall map/alarm/label). Its HOUSES record has `onOwn` (opens the
  shutter), `noDoor`, furniture bounds = the hall. `bunkFrame`: walking or driving into the mouth (`BUNK.mouth`) when owned -> `bunkGo(true)`
  (lands in the garage, keeps car speed); x < BUNKI.x - 42 in the garage tunnel -> `bunkGo(false)` (out through the falls).
- Map table: `holoBuild()` (lazy, first visit): terrain grid 96x96 from terrainH, CITY.boxes, road line, POI pins with sprite labels
  (`holoLabel`), a Moon sphere orbiting above; `holoFrame` rotates it and draws remote players and strike zones live.
- Satellite room: `SAT.own` (dd-sat), $3M at the green ring `BUNK.satRing` (HOMEACT 'sat'), `satOpen()` (run from bunkFrame once) opens
  the door. Console `BUNK.con` (HOMEACT 'orb') -> `orbOpen()`: #orb overlay with `orbDraw()` (drawMap with `MAPW = true` forces the world
  map), click/tap aims, WASD/arrows/stick move (900 m/s), Enter/A/Fire button = `orbFire()` ($200k, one pending at a time, max 8 zones).
  Gamepad handled by `orbPad` from the input function; keyboard branch at the top of keydown.
- Strikes: `STRIKES` [{key, x, z, t0, mine, st 0 pending/1 hit, gy, cr, rem, deco, fx, fires, beam}], `addStrike(x,z,t0,mine)`,
  impact 5 s after firing (`OS_DELAY`), radius `OSR` 240 m (4x4 blocks), lasts `OS_LIFE` 20 min. Shared via presence `os` [[x,z,t0]]
  (`netOs`), merged in `strikeFrame`. `strikeHit(s, fresh)`: removes CITY.boxes/BOXES/SOLIDS touching the circle (restored by
  `strikeEnd`), builds the crater mesh + ejecta rubble + fires; when fresh: flash `#nflash`, shake, mushroom fx (ball/stem/cap/ring/beam),
  kills you, npcs, actors, peds and police cars inside.
- Crater: `craterAt(x,z)` (bowl 28 m deep to r 200, a 5 m lip near r 210, blends back to the old ground by r 240). `groundAt` returns it
  first when `CRN` > 0; `inWater` ignores it. The shader patch `nukeMat(m)` (uniform `NZ` vec4[8] = x, z, r, gy) discards every fragment
  inside a zone for propMat, glowMat, fireMat, terrainMat, roadMat, lineMat, the sea, SIGMAT, parked cars and `nzDepth` (shadow depth,
  assigned as customDepthMaterial by a 2 s sweep). Chunk trees inside a zone stop colliding (`nzIn`).
- V57 fixes: sea-level clamps in car physics, on foot, traffic and the bail-out check go through `lowG(g, x, z, floor)`, which skips the
  clamp inside a crater (the floor is about -20 m, below the sea). `nzNear(s)` gives every landmark mesh near a strike (POI groups, and
  static scene meshes whose bounds fall in the zone) a cloned material run through `nukeMat`, so buildings with their own materials (the
  police station) vanish too; `nukeMat` marks materials with `userData.nz` and the shadow sweep covers any marked material. Police cars
  wrecked by a strike drop to the crater floor; desk officers inside a zone are hidden and never dispatched.
- Satellite save: `store()` only returns objects, so it is saved as `dd-sat = {own: 1}`; the old plain `1` is still read.
- Tests: scratchpad `bunk.js` (buy, walk in, holo, sat, console, fire, expiry), `bunk2.js` (views), `crat.js` (crater shape, drive in),
  `mpos.js` (strike reaches player 2 and kills them), `want.js` (run-overs, response time, bubbles).

## Lunar station and ore mining (V58)
- `buildLunar()` (runs at boot) picks the flattest spot near the landing site (5x5 samples of moonH over the footprint), builds a slab
  (BOXES, walkable), a hab module, a dome, solar panels, a mast with a blinking light, the ore exchange (`LSTN.sell`) and the drill rack
  (`LSTN.rack`, both with green rings). 40 ore nodes `ORES` [{i, x, z, y, g, sol, minedT, mine}] are scattered 45-425 m around it (seeded).
- `MINE = {own, carry}` saved as dd-mine (object), plus runtime `tool` (drill equipped) and `game`. The drill is free at the rack;
  `drillToggle()` = Y key, D-pad down (edge 13), or the #drillB button. Picking a gun (`setGun`) puts it away. The drill model is
  `DRILLGEO`, shown in the gun hand by `showDrill(model, on)` (local and remote, presence `tl`); guns are hidden while it is out
  (showGun(model, -1)), and firing is blocked.
- Mining (`mineStart`): exactly 5 s; a needle sweeps the bar, `mineStrike()` (F/Space/Enter/X, click or tap the canvas, the Strike
  button, gamepad A/X/RT) counts a hit inside the green zone (V59, easier: zone 36% wide shrinking 2% per hit, 4% grace either side,
  needle speed 0.55 +0.12 per hit); 3 hits by 5 s = +1 ore (max 10 carried). Esc or B cancels. Input is frozen
  while mining (input function and keydown branches). Mined nodes return after `ORE_BACK` (4 min); shared via presence `om` [[i, t]].
- Selling: `sellOre()` at the exchange ring, $1,000 each. `moonFrame` sets `MOONACT` (sell / drill / mine / hint) and the #moonP prompt;
  `moonKey()` is in the F and D-pad-up chains after homeKey.

## TVs and sitting (V58)
- Furniture with a `screen` {w, h, y, z} plays video: 'tv' (TV and stand) and the new 'bigtv' (Big-screen TV, $3,500).
- One YouTube embed `#tvFrame` (960x540, under the HUD, pointer-events none) plays the uploads playlist of Joe Bart VODs (@joebartvod,
  playlist `UU-lfGGqb5hHLBqVnVnWyrsw`). It is drawn over the nearest screen in the home you are in with a CSS matrix3d from `homog()`
  (four projected corners); hidden when the screen faces away or you leave. It is driven by postMessage commands (`tvCmd`: playVideo,
  pauseVideo, seekTo, setVolume, mute, unMute, nextVideo) after a 'listening' handshake; it answers with initialDelivery / infoDelivery /
  onStateChange (`TVP.cur, dur, state, title`). The iframe needs a referrer (referrerpolicy, origin param) or YouTube shows a configuration
  error; from file:// it always fails. Volume falls off with distance (`TVP.vol` x falloff, sent every 0.3 s). Headless Chromium cannot
  decode the video, so only the handshake is testable here.
- Sitting: seats are `SEATS` (sofa, armchair, beanbag, stool); standing near one gives HOMEACT 'sit' -> `sitDown(h, pc)` (SIT state,
  crouch pose, faces the seat's front, stepPlayer holds you there). `standUp()` on F, Esc, WASD, Space, gamepad B or the button.
- Remote #tvRemote (bottom left, while sitting): restart, -30s, play/pause, +30s, next, a seek slider, go-to-time (h:mm:ss), mute,
  volume. Keys: arrows seek/volume, K or P pause, N next, R restart, M mute. Gamepad (`tvPad`): A pause, X next, Y restart, LB/RB
  -/+30 s, D-pad left/right -/+10 s, up/down volume, B stand. TV and sitting are local to each device.

## El Blick and freeze missiles on people (V64)
- Lock-on (`copTargets`) now offers every hostile actor: `a.cop || a.gun || a.st === 0 || a.guard || a.atk` (was police only). Their
  wrapper `hitBy(oil)` -> `actorHitBy(a, oil)`. Unguided missiles/oil that pass within 1.8 m of an actor also hit it.
- El Blick -> `a.bleed` {t 5 s}: `actorFx` drains 30% of max hp over 5 s (BLEED_T, BLEED_F, the same rule as the player bleed in the
  standalone copy), caps their speed at walking x0.8 (BLEED_SLOW), spurts blood from the hit (`bloodSpurt`, falling droplets) and leaves
  a drip trail (`bloodDrip`, 40 pooled ground decals, `bloodFrame`). Bleeding out counts as your kill (MYHIT -> crimeKill rules).
- Freeze missile -> `a.frozen = FREEZE_T` + 20 damage: `actorFx` returns true so `stepActor` skips moving and shooting; an ice block
  (`a.ice`, removed in dropActor) sits on them. They can still be shot.
- Police cars: freeze missile sets `c.frozen` (stepPcar returns early, no driving, no unloading, ice box on the car); El Blick unchanged.
- Shared (V65): each `ac` entry has a 13th number, fx bits (1 frozen, 2 bleeding); other players' games draw the ice block and the
  blood spurts/drips for that person (`remoteFx(e, dt)`, removed when the entry goes). Each `pc` entry has a 7th number, 1 = frozen
  (`carIce(e, on)` on REMPC). The truck's `ak` may carry an 8th number, how it was stopped (1 freeze, 2 El Blick, 3 damage); receivers
  set ATK.fx so they see the ice or the spin. Older 7-number `ak` arrays are still accepted. Test: scratchpad `fxsync.js`.
- Test: scratchpad `bleed.js` (Hellhound oil on an armed NPC: 100 -> 70 hp over 5 s, ~2 m/s; heli freeze: stands still in ice; frozen police car).

## Armored truck heist (V60)
- Schedule from the shared clock, nothing sent: run id `R = floor((NET.now() - ATK.base) / ATK_P)` (8 min), `ATK.base` is 0 except for
  the test hook `atkStartNow(k)`. The truck drives for `ATK_DRIVE` (4 min) on `atkRoute(R)` (a rectangle of city street lines picked
  from R) at `ATK_V` 11 m/s; `atkPos(t)` gives the right-hand-lane position with rounded corners. It is NOT a TR rail slot: TR cars stop
  at lights and turn at random, the truck must not; it is just as deterministic. Traffic treats it as a blocker (blk in updateNpcs).
- Model `atkModel()`: boxy steel body, gold stripe, barred side windows, two rear door pivots (`ATK.doors`), ice box, 6 bag meshes,
  the drop-off ring + flag (`ATK.dropM`). Collision: two SOLIDS circles (`ATK.sol`) moved every frame (parked far away when hidden).
- Hits: `ATK.tg` wrapper in `copTargets()` (missile and El Blick lock-on, `hitBy(oil)`), gun target `{atk:1}` in fireGun, bazooka
  blasts in `explode` (V61: any blast within BOOMR + 3 m stops it in one shot), ramming (speed > 5 within 4.2 m, uses last frame's speed because the collision slows the car first).
  `atkHit(d, kind)`: 600 hp; a freeze missile or El Blick stops it at once, damage stops it at 0 hp. `atkStopNow` -> `ATK.myStop`, 2 stars.
- Shared state (presence `ak` = [R, flags, bags, stopX, stopZ, stopYaw*100, stopTime], sent only while you have flags or a stop;
  parsed only if 7 numbers). Every client merges: earliest stop wins (ties by id), doors open if anyone has flag 2, bags taken = union of
  bag masks, job done if anyone has flag 16. The stopper's game spawns the 2 guards (`a.atk = true`; actors sync as usual).
- Flags: 1 hit, 2 cracked the doors, 4 killed a guard (`crimeKill` -> also 2 stars), 8 took a bag, 16 delivered.
- Doors: prompt #atkP 'Crack the doors' (F / D-pad up / tap) within 2.6 m of the rear -> `ATK.game` 3-dial pin game on canvas #atkCv
  (3 pins per dial, needle sweeps, press F/Space/Enter/X/click/tap/A/X/RT, Esc/B cancels). V63 forgiving: window +-0.62 rad (drawn
  +-0.5), needle 1.5 rad/s (+3% per pin, +0.12 per dial), next pin at least half a turn away, 5 misses fail, 60 s limit.
  Win -> flag 2, 3 stars. Fail -> `ATK.lock` 15 s, 3 stars, a unit dispatched at once.
- Bags: walk over one (1.5 m) -> `atkGrab(i)`; carried bags show on your back (`bagOn`) and on remote players (from their `ak` mask).
- Delivery: `ATK_DROP` beside the road at z 1750 (south of the city, on the map once the doors are open). Carrying a bag there with
  0 stars -> `atkDeliver()` (flag 16) -> job done for everyone. Job = first bag delivered.
- Payout: each client pays itself $65,000 (`ATK_PAY`) when the job is done and its own flags are non-zero, once per run:
  `ATK.paid` / dd-atk {run}. Uninvolved players get nothing. Run over at 470 s ("The truck's been recovered").
- HUD #atkHud (time left / stopped / bags), map/minimap `atkBlips` (flashing gold square, TRUCK DROP), toast when a run starts.
- Test hooks: `atkStartNow(k)`, `atkHit`, `ATK.tg.hitBy(oil)`, `atkKey`, `atkPress`, `atkWin`, `atkFail`, `atkGrab(i)`, `atkDeliver`,
  `atkPos`, `ATK_DROP`, `hurtActor`. Tests: scratchpad `atk1.js` (solo), `atk3.js` (3 players: 2 involved get 65k, 1 gets 0).
- V62 lock-on fixes: the truck's own SOLIDS circles blocked `canSee`, so missile/El Blick lock-on never held; the lock check now aims
  at `y + 3.9` (over the roof) for `ATK.tg`. Guided hits on the truck trigger within 4.5 m; unguided missiles/oil that pass within
  4.2 m also hit it. On-foot aim assist counts the truck like a cop (`t.atk`), and for the bazooka the assist pull is 100% (the rocket
  flies straight at the assisted target; guns keep the 10% pull). Test: scratchpad `atklock.js` (heli freeze, Hellhound oil, bazooka).
- Pitfalls met here: `ar` was already the armour presence key (so `ak`); a stop is set in `ATK.myStop` immediately but `ATK.stop` only
  next frame, so guards against repeat hits must check both.

## Saucer beam on players and wrecks (V67)
- Beam on a player: the saucer names its target in presence `beam` {targetId, point, strength 2}. The victim's own client does the pulling in `netBeamPull`: a spring of 9 with damping 4.5, clamped at ±130, plus gravity cancel. The hold point is never lower than ground + 1.4, so the car always loses traction.
- Holding a target: the saucer grabs within 6.5 m horizontally when 0.5 m or more above them. It keeps the lock out to 45 m.
- While held (`NET.wasPulled`): all drive, fly and run inputs are zeroed in `runFrame`, and `getOut` is refused. `stepFoot` also calls `netBeamPull`, so people on foot are lifted too, with their walking steer skipped.
- Both players need the new version, because the victim's client does the pulling.
- Wrecked car (`damage` → `wreckOut`): you're forced out with `getOut(true)` at 30 health, prone (POSE 2), and stars are kept. The car stays as `PARK.wreck` and smokes.
- New car: `HP.carT` counts 10 s and the `#wreck.mini` banner shows the countdown. After that, Z (`getIn`) moves the same model to where you stand at full health and enters it with `enterPark`. Indoors and mid-air are refused, and the Garage is blocked during the countdown.
- Still kills outright: damage of 5000 or more (orbital strike), and wrecks in space.
- Dying on foot is unchanged.
- Backup before the graphics overhaul: `backups/rampage-road-v67-before-graphics.html` (artifact Version 67).

## Ultra graphics (V68)
- **Quality flag and switching:** `GFXQ` / `ULTRA` is read once at boot from localStorage `dd-gfx` ('ultra' by default, or 'classic'). The top-bar **Graphics** button (`#bGfx`) flips it and reloads.
- **Classic path:** Classic is exactly the old renderer, materials and models. Every ultra change sits behind `ULTRA`, so later gameplay changes keep working in both modes.
- **Rendering pipeline:**
  - Ultra draws into an offscreen target: `makePost` / `POST`, multisampled on WebGL2, FXAA on WebGL1.
  - The bright pass threshold is `POST.th` (0.9 by day, about 0.66 at night). It feeds a 5-level bloom chain.
  - One composite pass applies the filmic ACES curve, slight saturation and S-curve, vignette and dither.
  - Always draw through `present()`; `__drive.draw` does.
  - `resize()` calls `POST.size()`.
- **Reflections:**
  - `ENVQ` holds a small copy of the sky (sharing `sky.material`) plus a ground disc. It's baked with `PMREMGenerator` into `scene.environment`.
  - `envTick` re-bakes when the sky colours change, checked every 0.5 s.
  - The sky fragment shader ends with `#include <encodings_fragment>`. PMREM renders into RGBE, and without that line everything goes black and white.
- **Materials (`PBR(phong, std)`):**
  - Terrain, props, roads and lines use MeshStandard. Car paint is MeshPhysical with clearcoat.
  - Glass and water are reflective Standard.
  - Walls, ground and roads keep their `envMapIntensity` low, or the scene washes out.
- **Surface detail (`gfxPatch`):**
  - Called from `nukeMat`'s shader hook through `material.userData.gfx`, using the world position `vNW`.
  - 'road': asphalt grain, patches, and wet spots with lower roughness.
  - 'terr': grass mottling, and rock on slopes using derivatives of `vNW`.
  - 'prop': weathering.
  - 'fac': procedural facade on city towers. A window grid of 2.7 m by 3.4 m floors starts above `uYS` + 3.25. It has frames and reflective glass, warm or cool lit windows driven by `GFXU.uNight`, ground-floor shopfront glass, and a darker base.
  - In ultra, `bCity` puts tower bodies in their own `F` builder with `facadeMat`, and skips the old window-band boxes.
- **Smooth cars:**
  - `carParts` sends `SMOOTH` types (sedan, sport, roadster, suv, pickup, muscle) to `smoothCar`. Everything else, and Classic mode, uses `carPartsC` (the old builder).
  - `smoothCar` lofts rounded cross-sections along z: raked windscreen, crowned roof, tumblehome cabin, wheel arches raised into the sills, rounded nose and tail caps. Glass is its own geometry when `sepGlass`, with a dash and seats for the cockpit view.
  - It reuses the classic wheel positions and `halfLen`, so physics, hit boxes and multiplayer are unchanged.
  - The `lo` flag gives a light version for the 300 instanced parked cars.
  - `wheel()` in ultra builds a tread, a sidewall, a dark rim well, a hub and 5 spokes.
- **V69 additions:**
  - **FPS readout:** `#fps`, under the minimap, also showing the quality level.
  - **Auto step-down:** if Ultra still runs under 25 fps for 4 s at the lowest pixel ratio, `POST.lvl` turns glow off, then drops to 1024 shadows, then turns the effects off. Each step shows a toast.
  - **Graphics switch:** refuses with a toast when storage can't save the setting.
  - **Env re-bakes:** at most every 3 s unless the sky jumps.
  - **Model fixes:** the Jet Roadster gets its pods and nozzle back, and the Hellhound gets its red rocker stripe. The parked-car LOD is lighter.
  - **Testing:** headless tests must start with `document.getElementById('go').click()` inside `evaluate`. Playwright's `click()` times out because Ultra frames are slow on swiftshader.
- **Budget:** about 1.4M triangles in the city view (shadow pass included), against about 0.68M classic.
- **Backup of the pre-graphics build:** `backups/rampage-road-v67-before-graphics.html`.

## Map revamp, same in both modes (V70)
- **Graphics setting:** Classic and Ultra now differ only in rendering (materials, reflections, post, grass). The map geometry is identical in both, and no POI or footprint moved.
- **City towers (`bCity`):**
  - Lots within 520 m of the centre, over 36 m tall and over 22 m wide, get a setback. The full footprint goes up to `H1` (55–75 % of the height), with a cornice there. Above that, a tier inset 3 m on each side.
  - Collision pushes the inset box first and the full footprint at `H1` second. `groundAt` takes the first match, so you can stand on the setback ledge.
  - Every tower inside 820 m gets a band over the shopfronts and a ledge every other floor. Columns stop at `H1`.
  - The old window-band boxes are gone. All tower bodies use `facadeMat`: Phong in Classic, Standard in Ultra, both with `userData.gfx = 'fac'` and flatShading (needed for the dFdx calls in WebGL1).
- **Facade styles:** chosen in the shader by wall colour.
  - Blue-grey: glass curtain wall.
  - Warm red: brick with mortar lines (faded out at distance with `fwidth`) and narrower windows.
  - Everything else: stone with punched windows.
  - Lit windows are emissive at night in both modes.
- **Smooth cars and the 5-spoke wheels:** used in both modes too (`SMOOTH`, `wheel()`).
- **Pitched roofs are solid:**
  - `gable()` calls `addRoof`, which stores the slope (eave y, rise, overhang bounds) in `ROOFG`, a 40 m cell grid.
  - `groundAt` asks `roofAt` and lands you on the slope when you're within 1.4 m above it.
  - Covers every gable roof: suburbs, homes, barns, the harbour cottage.
- **Grass (Ultra, not phones):**
  - `GRASS`: crossed-blade tufts instanced on 6 m tiles in a 15×15 ring, with slots reused as you move.
  - Only on open terrain: not in the city, on roads, under anything built, below 0.6 m, or off the mainland.
  - Wind sway in the vertex shader. Normals point up, and each blade is doubled so both faces are front faces.
- **Night glow lowered:** bloom 0.2 + 0.12 × night, threshold 0.9 − 0.1 × night, window emissive 0.45–0.9.

## Energy Weapons Update (V71-V73)
- **Guns and saving:**
  - `GUNS` 10-17 are, in order: Quackzooka, Disco Detonator, Tesla Tickler, Sawmerang, Swapshot, Snowglobe Singularity, Shrinkinator, Yeet Beam. `XG` maps names to indexes.
  - Each has `exp`, `ven` (unlock venue) and `hint`. Models are appended to `GM`. `GUNSLOT` has 18 entries; Shift+1-8 selects 10-17, and the wheel, gamepad and phone Gun button cycle through all of them.
  - Saved keys: `dd-xam` (ducks, coil packs, globes), `dd-xunlock` (venue id -> 1), `dd-xheists` (completed heists, for Frostbank). Owned guns stay in `dd-guns`.
- **Shop:** the Iron Works category is "Experimental". Locked guns show their hint until the venue is won.
- **Firing:** experimental guns never go through `fireGun`. `footFrame` calls `xTrig(trig, dt)`, which handles press, hold and release through `XWEAP[exp]`.
  - Charges: `XC` (disco 2/30 s, swap 3/4 s, yeet 3/12 s, saw 1, shrink 1/6 s).
  - Ammo pools: `XAM`. Snowglobe cooldown: `XCOOL.hole`.
- **Network:**
  - One presence key `xw: {f, s, sc}` via `xwOut()` / `xwIn()`.
  - `f`: up to 4 cosmetic events `[type, seq, t0, ...nums, targetId?]`, replayed by every client through `xPlay` (the same code path for your own shots). Types: 1 yeet, 2 hole, 3 zap, 4 duck, 5 swap, 6 disco, 7 shrink, 8 saw.
  - `s`: up to 3 statuses `[toId, seq, kind, t0, a, b, c]`, applied only by the target's own client (`xStIn`). Checks: kind known, age under 4 s, shooter within `XRANGE`, shooter's `g` equals `XNEEDG`, per-sender cooldown, and `xCan()`.
  - `sc`: shrink scale, which remote clients apply to that player's mesh.
  - The first presence seen from a peer only records its seq (late joiners skip old events).
  - Counters: `XNET.sent`, `applied`, `rejected`, `log`.
- **Statuses on your own player (`XS`):**
  - Kinds: float (15 s, straight up about 2 m/s, then fall), stun, dance (then 18 s immune), stall, slow, shrink (30 %), yeet (impulse plus input lock, landing damage), swap (teleport via `xFreeSpot`).
  - Input locks are in `xInput()`, called after `readInput`.
  - Yeet Beam holding a player reuses the UFO path: `NET.beam = XHOLD.beam`.
- **Traffic cars:** npc mode 9 with `n.xs`, stepped by `xNpcStep` from `updateHeld`. The `nq` list carries positions to other clients.
- **People:** actors use `a.xs`, stepped by `xActorStep` from `actorFx`. Kinds: duck/fall, dance, stun, yeet.
- **Police cars:** `c.xst` (stalled), `c.xl` (lift), `c.xf` (flung), `c.xsh` (shrunk).
- **Armored truck:** every truck effect goes through `atkHit(d, kind)`.
  - Damage: duck 100 after 4 ducks, zap 60, saw 40, hole 30/s.
  - Disco, yeet, swap and shrink are 0-damage involvement hits only. The truck's position is clock-driven and can't be paused.
- **Effects (`XFX`, `xAdd`, `xFxFrame`):** pooled meshes, culled past 160 m, capped at 40, all removed when they end. Nothing stays in the world.
- **Venues (`XVEN`, `VEN`, `VCH`):**
  - `pier`: Quacker Pier Carnival, a `ven` POI over the water east of the South Harbour, with `DECKS`.
  - `club`: Club Mirrorball, which takes lot (0, 0) of block [9,12] in `bCity`.
  - `volt`: Voltridge Substation, a hill POI on the north coast.
  - `sky`: Skyhook crane beside the tallest tower. Its rungs are floors in `SKYG` (checked in `groundAt`, not city boxes, which act as walls). The platform and plank are `DECKS`.
  - `grav`: Gravity Lab, 70 m east of `LSTN`.
  - `frost`: Frostbank, by the bank; `xHeistDone()` is called from the heist payout.
  - `ufo`: UFO site, a hill POI at (-1900, 200).
  - `scrap`: Scrapyard, a hill POI at (-300, 3170).
  - The pedestal prompt is `#venP` (F, D-pad up or tap), handled by `venKey()`. Challenge state is per player and never synced.
- **City ground:** `groundAt` now takes the highest valid city box instead of the first match, so you can stand on the setback ledges.
- **On foot:** no engine, wind or skid sound; footsteps instead (`footStep` in `updateAudio`).
- **Shared lines touched (merge hotspots):** the presence line (`xw: xwOut()`), `netUpdate` (`xwIn`), the `runFrame` list (`xFrame`), `xInput()` after readInput, the KeyF and gamepad interact chains (`venKey`), the keydown top (dance arrows), `fireGun` (`exp` return, shrink damage, `hit.ven`), `footFrame` trigger and reload lines, `reloadGun`, `setGun`, `cycleGun`, the digit keys, the ammo HUD, `actorFx`, `updateHeld`, `stepPcar`, the POI defs and `ven` kind, the `bCity` lot loop, `nukeMat`'s beam else, the heist payout, and `__drive`.

## Multiplayer (room presence)

- `netSend()` builds one presence object ~18 Hz; `netUpdate()` reads peers. Fields: v n col rd w hp dm g c m p q vel bo beam frz oil pre
  ice ts nq ac adm cd cg at ft cv bx ar pu cr hl hs hk bk gs pc wl rw ga. Validate everything received (`num`, `vec`, `hexOK`,
  `cleanFit`, `cleanLook`).
- Damage to another player: cumulative `NET.dm` map; the receiver applies the increase (first hit counts in full).
- Shared clock `NET.now()`; time of day, traffic, lights and pedestrians are all derived from it.

## Other systems (short)

- Moon/space: `MOON`, `SPC`, `spaceHop(to)`, `stepSpace`, vehicles with `space: true`.
- Mall police banner / wanted HUD: `#wanted`, `wantedHud()`.
- Touch: foot buttons tFF fire, tFJ jump, tFS run, tFA aim, tFW next gun, tFC crouch, tFR reload. Heli lock-on ignores targets behind
  buildings (`canSee` on the chosen one).
- Parachute: `buildChute`, `openChute`, `CHUTE`. Controller: `gpPick`, `readInput` (pad mapping), `rumble`.
