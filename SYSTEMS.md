# Driftless Drive: how the systems work

Working notes for whoever picks this up next (including me after a context reset). Read this before touching the game.
Keep it current: when a system changes, update its section here in the same step.
Then copy it to the GitHub clone `/home/user/driftless-drive-repo` (branch `systems-notes`), commit and push.

## The basics

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
- Bank job (`H`, `heistFrame`, `startHeist`, `heistStage`): ring outside Driftless Savings, 10 s lobby, stages 1 guards, 2 gate keypad,
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
