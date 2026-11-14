#!/usr/bin/env node
/* Fills www/ (Capacitor's webDir) with the deployed web game: index.html, manifest.webmanifest, sw.js and icons/.
   The repo root stays the GitHub Pages site; www/ is a throwaway build folder (git-ignored). */
'use strict';
const fs = require('fs'), path = require('path');
const root = path.resolve(__dirname, '..'), out = path.join(root, 'www');
fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out, { recursive: true });
for (const f of ['index.html', 'manifest.webmanifest', 'sw.js']) fs.copyFileSync(path.join(root, f), path.join(out, f));
fs.cpSync(path.join(root, 'icons'), path.join(out, 'icons'), { recursive: true });
console.log('www/ ready:', fs.readdirSync(out).join(', '));
