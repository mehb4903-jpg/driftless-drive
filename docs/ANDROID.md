# Driftless Drive for Android (experimental)

This is an **experimental** Android app. It is the same game as the website (`index.html`), wrapped with
[Capacitor](https://capacitorjs.com/) 6, with AdMob interstitial ads. It is **not on Google Play**. GitHub Actions builds it
and publishes it as a GitHub **pre-release**.

## Install it

1. On your Android phone, open the repository's **Releases** page
   (https://github.com/mehb4903-jpg/driftless-drive/releases) and pick the newest release marked *Pre-release*,
   for example **Experimental v0.1.0-exp**.
2. Under *Assets*, tap `driftless-drive-<version>.apk` to download it.
3. Open the downloaded file. Android asks you to allow **Install unknown apps** for your browser or file manager.
   Tap **Settings**, turn on **Allow from this source**, go back, and tap **Install**.
   (You can also find this setting under *Settings → Apps → Special app access → Install unknown apps*.)
4. Google Play Protect may warn that the app is from an unknown developer. That is expected for an app that is not on Play.

**Updating:** if the build was signed with a throwaway key (see *Signing* below), Android refuses to install a newer APK
over the old one ("App not installed"). Uninstall the old app first. **Uninstalling deletes the save on the phone**, so
first use **Import save → Copy my save** in the menu and keep the text somewhere safe. Then import it again in the new app.

## What is experimental

- Ads are shown: one after you tap **Start driving**, then on every 2nd death, never more than one per 120 seconds. No ad is
  shown while the TV (YouTube) is on screen, during a heist or the armored truck job, while drilling, the orbital strike,
  placing furniture, or while the Import save, Servers or Fast travel windows are open.
- **Google sign in does not work in the app.** Android WebViews block the Google sign-in popup. The button explains this.
  Sign in on the website instead, then move your save into the app with **Import save** (*Copy my save* on the website,
  paste in the app).
- The YouTube TV inside the game may refuse some videos in the app (YouTube treats an app WebView differently from a browser).
- Multiplayer (PeerJS / WebRTC) works as on the website. The app does not ask for the microphone or camera.
- Saves live inside the app, separate from the browser's saves.
- The app keeps the screen on, runs landscape only, and hides the status and navigation bars (swipe from the edge to show them).

## Ads: AdMob ids, test ads and real ads

All ad settings are in **one object** in `index.html`, `window.DD_ADS_CONFIG` (search for it):

| Setting | Value | Meaning |
| --- | --- | --- |
| `appId` | `ca-app-pub-2728172646252789~8538967894` | the real AdMob **app** id. The build copies it into the Android manifest (`scripts/patch-android.js`). |
| `interstitialId` | `ca-app-pub-2728172646252789/3419870135` | the real (production) interstitial **ad unit**. |
| `testInterstitialId` | `ca-app-pub-3940256099942544/1033173712` | Google's public **test** interstitial unit. |
| `USE_TEST_ADS` | `true` | `true`: the app requests Google's test ad (marked "Test Ad"). `false`: real, paid ads from `interstitialId`. |
| `TEST_DEVICE_IDS` | `[]` | your phone's AdMob test device id(s). With real ads on, ads on these phones are served as test ads, so you can check real ads without invalid clicks. Find the id in `adb logcat` (look for `Use RequestConfiguration.Builder().setTestDeviceIds(Arrays.asList("…"))`). |
| `minGapSec` / `everyNthDeath` / `startupAd` | `120` / `2` / `true` | how often ads appear. |
| `childDirected`, `underAgeOfConsent`, `maxAdContentRating` | `true`, `true`, `'General'` | see *Ad content settings*. |

A real app id together with the test unit id is a valid setup: AdMob serves test ads and nothing is paid or counted as a click.

**To switch to real ads:** set `USE_TEST_ADS: false` in `index.html`, commit, and push a new tag (for example
`git tag v0.1.1-exp && git push origin v0.1.1-exp`). The workflow builds and publishes a new APK.
Before you do:

- **Never tap your own live ads**, and do not ask friends to. AdMob detects invalid clicks and can disable the account.
  Keep testing with `USE_TEST_ADS: true`, or register your phone as a test device in the AdMob console.
- The app must be set up in AdMob (app + ad unit, both already created) and AdMob may need the app to be **linked to a
  store listing** before it serves real ads at full rate. Apps that are not on a supported store often get limited or no ad
  fill. Check the AdMob console for the app's status and any policy notices.
- AdMob needs an `app-ads.txt` file on your developer website for full demand; without a store listing there is no place
  to declare one.

### Ad content settings

The app sets `tagForChildDirectedTreatment: true`, `tagForUnderAgeOfConsent: true` and `maxAdContentRating: 'General'` (G)
when it starts AdMob. That keeps ads to family-safe content and turns off personalised ads, because the audience of the game
is not known. Ads earn less with these settings. If you change them, the allowed ratings are `General`, `ParentalGuidance`
and `Teen` (keep it at Teen or lower). If the game is meant for children under 13, it also needs a privacy policy and must
follow Google's Families policies.

## Remove ads (redeem codes)

There is no paid "Remove ads" purchase. Selling it the normal way needs Google Play Billing, which only works for apps
installed from Google Play, and publishing on Play needs a **Google Play Console developer account ($25, one time)**, a
privacy policy, and Google's review. A $2.99 in-app purchase can be added after the app is on Play.

Instead, the menu of the app (never the website) has a **Remove ads code** field. A valid code switches ads off on that
phone for good (stored in `localStorage` as `dd-noads`; it is not synced to the Google account or included in Import save,
so each phone needs its own code redemption).

- The repository only holds the **SHA-256 hashes** of the codes (`redeemHashes` in `DD_ADS_CONFIG`), never the codes.
  Codes are compared after making them upper case and removing spaces and dashes, so `dd-abcd-efgh-ijkl` and
  `DDABCDEFGHIJKL` are the same code.
- Five codes were generated and given to the owner privately. A code can be used on any number of phones, so hand them out
  to people you trust (for example as a thank-you).
- To make a new code, pick a random string (for example `DD-` and 12 random letters/digits), compute the hash and add it
  to `redeemHashes`:
  ```sh
  node -e "console.log(require('crypto').createHash('sha256').update(process.argv[1].toUpperCase().replace(/[^A-Z0-9]/g,'')).digest('hex'))" "DD-XXXX-XXXX-XXXX"
  ```
  To retire a code, delete its hash.
- This is a simple honour system. Someone who edits the app (or the saved data on a rooted phone) can turn ads off without a
  code.

## Signing

Android only installs signed APKs. The workflow signs the release APK like this:

- If the repository has these **Actions secrets**, it uses your keystore, so each new APK installs over the old one and the
  save is kept: `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`.
  Make one once and keep a backup (if you lose it you can never update the app with the same identity):
  ```sh
  keytool -genkeypair -keystore driftless.jks -alias driftless -keyalg RSA -keysize 2048 -validity 10000
  base64 -w0 driftless.jks   # paste the output into ANDROID_KEYSTORE_BASE64
  ```
  Add them under **Settings → Secrets and variables → Actions → New repository secret**.
- Otherwise it generates a **throwaway keystore** inside that build and deletes it afterwards. The APK installs fine, but every
  build has a different signature, so updates need an uninstall first (see *Install it*). The release notes say which key
  was used.

## How the build works

- `package.json` / `package-lock.json` pin Capacitor 6.2.1 and `@capacitor-community/admob` 6.2.0 (works with JDK 17,
  Android SDK 34).
- `capacitor.config.json`: app id `com.driftless.drive`, name *Driftless Drive*, `webDir: www`, the CDN, Firebase, PeerJS and
  YouTube hosts allowed for navigation, and `DriftlessDriveApp` added to the user agent.
- `scripts/build-www.js` copies `index.html`, `manifest.webmanifest`, `sw.js` and `icons/` into `www/`. The repository root is
  still the GitHub Pages site; `www/`, `android/` and `node_modules/` are not committed.
- In CI, `npx cap add android` generates the Android project, `npx cap sync android` copies the web files and the AdMob
  plugin in, and `scripts/patch-android.js` adds the AdMob app id, landscape, fullscreen, keep-screen-on, autoplay,
  third-party cookies (YouTube embed), the launcher icon and the version number. Then `./gradlew assembleRelease`.
- `.github/workflows/android.yml` runs on every pushed tag that starts with `v` (for example `v0.1.0-exp`) and on
  *Run workflow* in the Actions tab, then attaches the APK and its SHA-256 to a GitHub pre-release named
  *Experimental &lt;tag&gt;*.

Build it on your own computer (needs Node 20, JDK 17 and the Android SDK):

```sh
npm ci
node scripts/build-www.js
npx cap add android      # once
npx cap sync android
node scripts/patch-android.js
cd android && ./gradlew assembleDebug   # app/build/outputs/apk/debug/app-debug.apk
```

## Policy and legal notes

- **Ads must never cover the YouTube player.** The game blocks ads while the TV is on screen. Keep it that way if you change
  the ad code; AdMob and YouTube both forbid ads placed over or next to embedded video in a way that could be confused with it.
- **The TV is a risk for a monetised app.** The in-game remote (seek, skip-ad button), drawing the video onto a 3D TV with
  objects covering it, and hiding or skipping YouTube's own ads may break the
  [YouTube API Services Terms and Developer Policies](https://developers.google.com/youtube/terms/developer-policies)
  (for example: do not modify, obscure or interfere with the player or its ads, and extra rules for apps that earn money).
  Before you earn real money with this app, consider removing or simplifying the TV in the app build, or get advice.
- **AdMob policy:** real ads need the app registered in AdMob (done), honest ad placement (no accidental clicks; interstitials
  only at natural breaks such as start and death, which is how this build uses them), and a privacy policy that mentions
  AdMob. Google may also require a consent message (UMP) for users in the EEA/UK before showing ads; this experimental build
  does not include one.
- Apps from outside Google Play are not reviewed by Google. Only share the APK from this repository's Releases page.
