# अमृतकण — audio streaming site

A hobby website that streams the user's personal collection of Marathi spiritual
audio recordings (Dnyaneshwari and Changdev Pashashti discourses), plus two
digital books, so they can be shared with others via a link, without needing
a public IP (the user is behind CGNAT on Telus). Publicly reachable at
**https://amrutkan.org** via a named Cloudflare Tunnel.

## Architecture

**Hybrid: Python backend (data + streaming), React frontend (UI).** `app.py`
is pure Python 3 standard library (`http.server` + `socketserver`), no
external Python runtime dependencies — see "Known constraints" below for why.
Node.js is a *build-time-only* tool for `frontend/`; the running production
process is still just `python3 app.py`, no Node process in production.

**Content model** (`app.py`): episode filenames follow `<book prefix> -
अध्याय <N> ...` or `<book prefix> - ओवी <N> ...`. `build_library()` parses
this at startup with regex, grouping episodes by book → chapter/verse number.
Files that don't match a numbered chapter (intros, summaries, biographies)
get pulled into their own labelled tile by each book's `SPECIAL_CHAPTER_ORDER`
config; anything not in that list falls back to a generic इतर tile. New
episodes just need to follow the naming convention and a server restart to
be picked up — no code changes, unless a new special (non-numbered) file
needs an entry added to `SPECIAL_CHAPTER_ORDER`.

**Backend (`app.py`) routes**:
- `/api/library` — full book/chapter/episode tree as JSON. Also consumed by
  the native `AmrutkanApp` (Expo/React Native) mobile app.
- `/api/home` — static home-page content (about text, podcast links, YouTube
  IDs) as JSON, kept here so content isn't duplicated between Python and
  TypeScript.
- `/audio/<filename>` — HTTP Range-request audio streaming.
- `/download/book/<id>[/<slug>]` — streamed ZIP of a book or chapter, see
  "Bulk ZIP download" below.
- `/`, `/book/<id>`, `/book/<id>/<slug>`, `/pustak/<id>` — not rendered
  server-side. `spa_shell()` generates a minimal HTML shell with per-route
  `<title>`/`og:*` meta tags (pulled from `LIBRARY`/`PUSTAK_DEFS`, so social
  previews work without full SSR) plus the built React bundle. React Router
  takes it from there; a direct/refreshed load of a deep URL still works
  since Python serves the same shell for every route.
- `/assets/<file>` — `frontend/dist/assets/*`, long-lived immutable
  `Cache-Control` (content-hashed filenames). `spa_shell()` extracts the
  actual `<script>`/`<link>` tags from `frontend/dist/index.html` at
  startup, so a new `npm run build` is picked up with zero code changes.

**Frontend (`frontend/src/`)**: Vite + React 19 + TypeScript + Ant Design v6
+ `react-router-dom`. `player/PlayerContext.tsx` holds all player state
(play/pause/seek, playlist-aware prev/next, speed presets, sleep timer,
MediaSession lock-screen controls, resume-on-reload) and is mounted once at
the `App` root so it survives client-side route navigation. Dev: `cd
frontend && npm run dev` (proxies `/api`, `/audio`, `/static`, `/download` to
`python3 app.py` on 8080). **Deploy requires a build first** — `cd frontend
&& npm run build && cd .. && systemctl --user restart audio-site.service`;
restarting alone re-serves the previous `dist/` unchanged.

## Files

- `app.py` — backend, see Architecture above.
- `frontend/` — React/TS/antd UI, Vite build → `frontend/dist/`
  (gitignored). The only place Node.js is required, and only at build time.
- `static/mauli.jpg` / `mauli_original.jpg` — hero image (cropped / source).
- `healthcheck.sh` — see "Health check" below.
- `build_zip_cache.py` — pre-builds `zip-cache/` (gitignored, ~34GB). Re-run
  manually whenever audio content changes.
- `build_pustak_cache.py` — renders the two books' PDFs to per-page JPEGs
  under `pustak-cache/` (gitignored). Source PDFs live outside the repo at
  `~/Desktop/पुस्तके/` (**this repo is public** — a PDF must never be
  committed here). Re-run manually whenever a book is added/replaced.
- Audio content lives outside the repo at `~/Desktop/अमृतकण` (`AUDIO_DIR` in
  `app.py`), arranged on disk to mirror the site's structure/order — none of
  that folder layout matters to `app.py` itself, which only ever looks at
  filenames via regex (`discover_audio_files()`/`FILES_BY_NAME`), so
  reorganizing the folder needs no code change, just a restart.
- Every audio file has Artist/Album (`TPE1`/`TALB` mp3, `©ART`/`©alb` m4a)
  and traceability tags (copyright + `amrutkan.org` URL, deliberately Latin
  script for player/OS compatibility) set via one-off `mutagen` scripts —
  metadata only, `app.py` doesn't read these tags itself; they only matter
  to someone who downloads a file and opens it elsewhere.

## Running it

Both the app and the tunnel run as **systemd user services** (auto-restart on
crash/reconnect, start on boot via `loginctl enable-linger`):
`~/.config/systemd/user/audio-site.service` (`app.py`),
`audio-site-tunnel.service` (`cloudflared`), `audio-site-healthcheck.service`/
`.timer`.

**The app and tunnel units are deliberately not bound together** (no
`BindsTo=`) — restarting `app.py` must never restart the tunnel, since a
tunnel restart used to mean a new random URL under the old quick-tunnel setup
(no longer possible now that it's a named tunnel, but the independence is
still correct — no reason to couple lifecycles that don't need to be).

```bash
systemctl --user status audio-site.service audio-site-tunnel.service audio-site-healthcheck.timer
systemctl --user restart audio-site.service          # picks up app.py edits; tunnel/URL unaffected
journalctl --user -u audio-site.service -f
journalctl --user -u audio-site-tunnel.service -f
tail -f ~/audio-site/access.log
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/
```

Public URL is fixed: `https://amrutkan.org`.

## The cloudflared tunnel

Installed at `~/.local/bin/cloudflared` (user-level, no sudo — see "Known
constraints"). A **named** Cloudflare Tunnel (`cloudflared tunnel create
amrutkan`), config at `~/.cloudflared/config.yml` (ingress rules for
`amrutkan.org`/`www.amrutkan.org` → `http://localhost:8080`, `404` fallback
for any other hostname), DNS routed via `cloudflared tunnel route dns`.
`audio-site-tunnel.service`'s `ExecStart` runs `cloudflared --config
~/.cloudflared/config.yml tunnel run`.

**`www` → root redirect** happens in `app.py`, not Cloudflare: both hostnames
route through the same tunnel to the same process, and `AudioHandler.do_GET`
301-redirects `www.{PRIMARY_DOMAIN}` requests to `{PRIMARY_DOMAIN}` first
thing, reflecting `self.path` verbatim into `Location` so query strings
survive.

Quick tunnels (the old setup) mint a random hostname on every restart and
aren't intended by Cloudflare for sustained media streaming — both problems
are why this moved to a named tunnel.

`app.py` was made HTTP/1.1 with keep-alive (`AudioHandler.protocol_version`)
and the listen backlog raised (`request_queue_size = 128`) after a WiFi-drop
investigation traced perceived "audio quality" issues to connection churn,
not the files or bandwidth themselves — every buffered/seek Range request
was paying a fresh connection setup under the old HTTP/1.0 default.

## Player features (`frontend/src/player/`)

- **Lock-screen / Bluetooth controls**: `navigator.mediaSession` — metadata,
  action handlers, position sync. **Not yet verified on a real device.**
- **Resume where you left off**: `localStorage` key `ak_playback`
  (`{src, label, subtitle, playlist, index, currentTime}`), saved on pause,
  periodically during playback, and on `pagehide`. Restores position on load,
  does not autoplay.
- **Continue Listening homepage widget** (`components/ContinueListening.tsx`,
  `continueListening.ts`) — separate from the above: book-level progress
  (`localStorage` key `ak_progress`) drives one CTA button on `Home.tsx`.
  `resolveContinueListening()` resolves to one of four states: `first` (no
  progress yet), `resume` (mid-episode), `next` (finished an episode —
  crosses from one book's last episode into the next book's first, not a
  dead end), `finished` (last episode of the last book, rendered as a
  disabled button).
- **Playback speed** (`SPEED_PRESETS`, `localStorage` key `ak_speed`) and
  **sleep timer** (episode-end default, or a fixed duration, not persisted
  across visits) — both via antd `Dropdown` menus in `NowPlayingOverlay.tsx`.
- **Download**: plain `<a download>` per episode.
- **Favicon + Open Graph tags**: generated server-side per-route
  (`spa_shell()` in `app.py`) so link previews work without SSR.

**Known gap vs. the pre-React implementation**: a custom loading skeleton and
staggered card-entrance animation weren't carried over (out of scope for the
migration, which prioritized functional parity). antd's default `Spin`/`Card
hoverable` cover the baseline UX; worth adding back only if actually missed.

## Digital book reader — पुस्तके

Two spiritual books by the same author, shown page-by-page,
**deliberately not downloadable as a PDF** — the author's own copyright
notice prohibits reproduction, so the whole design avoids letting a
complete, high-fidelity copy reach the client in one file. This stops the
casual/one-click path (saved PDF, spoofed link, "Save Page As"), not a
screenshot or screen recording, which nothing browser-side can prevent:

- Source PDFs are never in the repo or served directly — `build_pustak_cache.py`
  pre-renders every page to a JPEG (150 DPI / quality 78 — legible on
  screen, well below print/reassembly quality) via poppler's `pdftoppm`.
  `app.py` only ever reads from that rendered cache.
- `/pustak/<book-id>/page/<n>.jpg` (`serve_pustak_page()`) serves exactly one
  page image with no `Content-Disposition` (renders inline, never a download
  prompt); the filename is rebuilt from a validated int + whitelisted book
  id, never from the raw request string, so path traversal isn't reachable.
- **Frontend** (`pages/Pustak.tsx`): draws each page into a `<canvas>`
  (not `<img>`, which has a built-in "Save image as…"/drag-out affordance),
  with `onContextMenu`/`onDragStart` prevented and `user-select`/
  `-webkit-touch-callout` disabled. Prev/Next + ←/→ keyboard nav; next page
  is prefetched. A fullscreen/immersive toggle renders as a CSS state (not
  solely the native Fullscreen API, which is unsupported in a lot of this
  site's real traffic — iOS Safari, in-app browsers) on one persistent
  container, with `requestFullscreen()` attempted best-effort on top.
  Touch-swipe turns pages (suppressed while zoomed, since a horizontal drag
  on a zoomed page is panning, not a page-turn intent); pinch/button zoom
  from 1× (fit-to-screen) to 3×, resetting on page/orientation/fullscreen
  change. Landscape fullscreen and the non-fullscreen landscape reader are
  both height-capped like portrait (an earlier width-filling variant made a
  portrait-shaped page run far taller than a landscape screen — reverted at
  the user's request in favor of seeing the whole page at a glance).
  Last-read page position persists per-book to `localStorage`
  (`pustakProgress.ts`, key `ak_pustak_progress`), read synchronously on
  mount so the very first page fetch is already for the resumed page.

## Bulk ZIP download

Every book/chapter page has a download-all button —
`AudioHandler.serve_zip()` streams a `.zip` built on the fly, safe for a
multi-GB book:
- **Never buffered in memory or on disk**: `zipfile.ZipFile` writes directly
  to a non-seekable wrapper around the response stream, which makes it use
  data descriptors instead of seeking back to patch headers — exactly what a
  live HTTP response needs. `ZIP_STORED` (no compression), since the
  mp3/m4a sources are already compressed.
- **No `Content-Length`** (total size isn't known upfront without a first
  pass): sends `Connection: close` instead, which is standard, spec-compliant
  HTTP/1.1 when neither `Content-Length` nor chunked encoding is used.

**ZIP cache** (`build_zip_cache.py`, gitignored `zip-cache/`, ~34GB —
roughly 2× the source audio, since every file appears in both its book-zip
and chapter-zip): pre-builds every possible ZIP with a real, seekable local
file so the download shows a real `Content-Length`/progress, which the
live-streamed path above can't provide. `do_GET` checks the cache first;
an absent/stale entry falls straight back to the live-build path, so a
missing cache entry never breaks downloads. Not rebuilt automatically on
`app.py` startup — re-run manually whenever audio content changes.

## gzip compression

`AudioHandler.maybe_gzip()` compresses HTML/JSON/frontend JS-CSS-SVG
responses when the client offers `Accept-Encoding: gzip`, skipped below 512
bytes. **Deliberately never applied** to audio, images, ZIPs, or font files —
already-compressed binary formats where it would only cost CPU, and for
Range-requested audio specifically, compressing would actively break
byte-range semantics (a byte offset into the compressed stream has no stable
relationship to a byte offset into the audio) — this must never be touched.

## Access log

`log_message` on `AudioHandler` writes to `~/audio-site/access.log`
(`RotatingFileHandler`, 5MB × 3 backups) — one line per request. Logs the
real visitor IP via Cloudflare's `CF-Connecting-IP` header (falling back to
the raw socket address when hit directly, e.g. local testing without the
tunnel) rather than `127.0.0.1`, which is what every request would otherwise
show since it reaches `app.py` via `cloudflared` on localhost.

## Health check

`~/audio-site/healthcheck.sh`, run every 5 minutes by
`audio-site-healthcheck.timer`. Each run curls both `localhost:8080` (is
`app.py` up) and `https://amrutkan.org` (is the whole path — app + tunnel +
Cloudflare edge — reachable), with one retry after 5s to avoid flagging
sub-5-second blips. State tracked in `~/audio-site/.healthcheck_state`; only
a *transition* triggers a `notify-send` desktop notification (critical on
down, plain on recovery) — depends on the user being logged into the
graphical session, no email/push fallback, degrades to log-only otherwise.

## Known constraints for whoever continues this

- **No pip/venv available** in this environment (`python3-pip`/`python3-venv`
  not installed, no passwordless sudo) — `app.py` deliberately avoids
  Flask/any third-party **Python** package, stdlib only. `python3-mutagen` is
  an apt-installed exception for one-off audio-tag editing, not pip. Does
  **not** apply to `frontend/`, which has its own Node/npm toolchain and
  normal npm dependencies — the "no dependencies" constraint is specifically
  about the Python runtime process, not build tooling.
- **Sandbox quirk with `pkill`**: running `pkill` in the same Bash tool call
  as a follow-up command reliably produces exit code 144 and the rest of
  that command block silently doesn't run, even though the kill itself took
  effect. Shouldn't come up in practice now that both processes are systemd
  services (`systemctl --user restart ...` instead of `pkill`/`nohup`); if a
  stray process ever needs killing directly, treat kill and restart as
  separate tool calls and check `ps aux` in between.
- This machine is the user's real local PC, not a disposable container —
  audio files and everything else here are real user data.

## Possible next steps (not yet done, only do if asked)

- Confirm lock-screen/Bluetooth media controls on a real iPhone/Android —
  still never visually verified on real hardware.
- Consider code-splitting the frontend bundle (`npm run build` warns about a
  single large JS chunk, mostly antd) — not urgent for a low-traffic hobby
  site.
- Optional polish: bring back the pre-React loading skeleton/card-entrance
  animation, only if actually missed (see "Known gap" above).
- Prefer wired ethernet over WiFi on this machine if practical — WiFi
  disconnect/reassociate events have previously been observed to disrupt the
  tunnel mid-stream.
- `app.py` rescans the audio folder only at startup — new episodes need a
  `systemctl --user restart audio-site.service` to be picked up.
