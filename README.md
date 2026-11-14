# Driftless Drive (online)

A standalone copy of the Driftless Drive browser game. It is one file, `index.html`, so any static web host works.
Multiplayer runs peer to peer over WebRTC through [PeerJS](https://peerjs.com/) 1.5.4. PeerJS's free public server only
introduces players to each other. The game data goes directly between browsers.

## Put it on GitHub Pages

1. Create a new public repository on GitHub, for example `driftless-drive`.
2. Upload `index.html` to the root of the repository. You can drag it onto "Add file → Upload files" and commit.
3. Open **Settings → Pages**. Under "Build and deployment", set **Source** to *Deploy from a branch*. Pick the `main`
   branch and the `/ (root)` folder, then save.
4. After about a minute the game is live at `https://<your-user>.github.io/driftless-drive/`.

To try it on your own computer, run `python3 -m http.server` in this folder and open `http://localhost:8000/`.
Opening the file directly with `file://` also works.

## Play with friends

- When you open the page, it adds a room code to the address, for example `…/driftless-drive/#room=k3m9tq`.
- Click **Copy invite link** in the Players online panel, which is under the minimap once you start driving, and send
  the link to your friends. Anyone who opens the same `#room=` link joins your island. Copying the address bar works too.
- You can pick your own room name by editing the address, for example `#room=fridaynight`. Use letters and digits only.
- A room holds up to 8 players. The top bar shows `Online N`, `Reconnecting`, or `Offline`.
- If PeerJS or its server can't be reached, the game still runs as a single-player game and shows `Offline`. Hover over
  the word to see the reason.

## On foot and best laps

- Press **Z** to get out of your vehicle and **Z** again near it to get back in (or near another player's vehicle to ride with them).
  On foot: W S walk, A D turn, Q E strafe, Shift run, Space jump, **X** shoot, **1-4** pick a gun. There is a **Fullscreen** button on the top bar.
- Your best laps on the speedway are saved in this browser (localStorage). In a room, each player's best lap is shared with the others
  and shown on the Best laps board.

## Good to know

- The connection uses public STUN servers from Google and Cloudflare, plus PeerJS's free public TURN relay. These are
  shared demo services with no guarantees. Some strict corporate or mobile networks can still block a direct connection.
  When that happens, the affected players stay solo or can't see each other.
- If you'd rather not depend on the public signaling server, run your own with the `peer` npm package
  (`npx peerjs --port 9000`). Then add this line to `index.html` before the other scripts:
  `<script>window.DD_PEER_OPTIONS = { host: 'your.host', port: 443, path: '/', secure: true };</script>`
- Room codes aren't secret. Anyone who knows or guesses a code can join that room.

## Install on iPhone / iPad (fullscreen)

Open the site in **Safari**, tap **Share**, then **Add to Home Screen**. Launch it from the new Driftless icon and it runs as a full-screen app with no browser bars (iPhones have no browser fullscreen button, so this is the way). On Android, Chrome's menu has **Install app** with the same effect.
