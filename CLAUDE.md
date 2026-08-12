# अमृतकण — audio streaming site

A hobby website that streams the user's personal collection of Marathi spiritual
audio recordings (Dnyaneshwari and Changdev Pashashti discourses) so they can be
shared with others via a link, without needing a public IP (the user is behind
CGNAT on Telus).

## Current status

Working and publicly reachable at **https://amrutkan.org** (as of 2026-08-11).
The user bought the domain through Cloudflare Registrar and it's now served
via a **named** Cloudflare Tunnel with a stable hostname — see "The
cloudflared tunnel" below. Before this it ran on a temporary, random-hostname
Cloudflare **quick tunnel**; that phase is over, but earlier notes below
still mention it for history/context.

**Frontend rewritten as React + antd (2026-08-11)**: the site was originally
one dependency-free Python file that both served data *and* hand-generated
all HTML/CSS/JS. At the user's request it now has a proper React frontend
(TypeScript + Ant Design) instead of hand-rolled markup — see "Architecture"
below for how that's split from the still-dependency-free Python backend.

## Files

- `app.py` — the backend. Still pure Python 3 standard library (`http.server`
  + `socketserver`), still **no external Python dependencies** at runtime
  (see "No pip/venv" below for why that constraint exists) — but it no longer
  renders any page markup itself. It serves data (`/api/library`,
  `/api/home`), audio (Range-request streaming), ZIP downloads, and the
  built React app's static assets.
- `frontend/` — the React + TypeScript + Ant Design (antd) web UI. Built with
  Vite. **This is the one place Node.js is required**, and only at build
  time (`npm run build` → `frontend/dist/`) — see "Architecture" below.
  `frontend/node_modules/` and `frontend/dist/` are gitignored (regenerated,
  never hand-edited).
- `static/mauli.jpg` — hero/header image (Dnyaneshwar Mauli), pre-cropped to a
  square, top-anchored, with the original picture-frame border removed.
- `static/mauli_original.jpg` — the untouched source image, kept in case a
  different crop is ever wanted.
- `static/sk_chaudhari.jpg` — photo of Dr Suresh Kumar Chaudhari for the
  home page's "माझ्याबद्दल" subsection, downloaded 2026-08-11 from an ITU
  profile page the user linked and saved locally (not hotlinked).
- `healthcheck.sh` — see "Health check" below. `access.log`, `healthcheck.log`,
  `.healthcheck_state` are runtime-generated (not checked into anything, just
  local state/logs).
- `build_zip_cache.py` — one-off script, pre-builds `zip-cache/` (gitignored,
  ~34GB, not checked in) — see "ZIP cache" under "Bulk ZIP download" below.
  Re-run manually whenever audio content changes.
- `build_pustak_cache.py` — one-off script, renders the two digital books'
  PDFs into per-page JPEGs under `pustak-cache/` (gitignored, ~44MB) — see
  "Digital book reader" below. Source PDFs themselves live outside the repo
  at `~/Desktop/पुस्तके/` (this repo is public, so a PDF must never be
  committed here). Re-run manually whenever a book is added/replaced.
- Audio content itself is **not** in this folder — it's read directly from
  `~/Desktop/अमृतकण` (see `AUDIO_DIR` in `app.py`). 443 files (401 `.mp3` +
  42 `.m4a`), ~17GB total. **Physically arranged on disk to mirror both the
  site's structure *and* its display order** — every book has a flat list of
  subfolders, one per unit (chapter, verse, or one of the special
  intro/summary/biography items), no `इतर` catch-all folder for either book
  (removed 2026-08-10). The special items are folders too (not loose files —
  uniform with अध्याय/ओवी), each holding exactly one file, with the *folder*
  name (never the audio filename inside — that stays exactly as authored,
  since it's what gets served for downloads) prefixed with an ASCII digit
  where needed purely to force correct alphabetical sort order in a file
  manager: ASCII digits sort below the entire Devanagari Unicode block, so a
  digit prefix reliably sorts a folder before any अध्याय/ओवी-named sibling;
  no digit is needed where a folder already sorts correctly on its own
  (सिंहावलोकन naturally sorts after अध्याय-named folders since स > अ in
  Devanagari order, so it's unprefixed) — e.g. ज्ञानेश्वरी:
  `0 परिचय`, `अध्याय १` … `अध्याय १८`, `सिंहावलोकन`; चांगदेव पासष्टी:
  `1 श्री चांगदेवांचे संक्षिप्त चरित्र`, `2 श्री ज्ञानेश्वरांचे संक्षिप्त
  चरित्र`, `3 सारांश`, `ओवी १` … `ओवी ६५`. None of this — folder names,
  nesting depth, or the digit prefixes — matters to `app.py` at all; it's
  purely for whoever browses the raw files directly. `build_library()` only
  ever looks at the actual audio filenames (via regex), never folder paths,
  and `discover_audio_files()` in `app.py` walks this recursively at startup
  and builds a filename → full-path map (`FILES_BY_NAME`), so it works regardless of
  whether files are flat or nested — if the user (or a future you) reorganizes
  the folder again or adds new episodes anywhere under `AUDIO_DIR`, just restart
  the server to pick up the new layout, no code changes needed.
- **ID3/MP4 tags** (2026-08-11): every file under `AUDIO_DIR` had its
  Artist/Album Artist tag set to "Dr S K Chaudhari" (`TPE1`/`TPE2` for mp3,
  `©ART`/`aART` for m4a) and, in a separate follow-up pass the same day, its
  Album tag set to "Amrutkan" (`TALB` for mp3, `©alb` for m4a) — same album
  name for every file regardless of book (not per-book), using
  `python3-mutagen` (see "Known constraints" below). Both were one-off
  scripts, not part of `app.py`, run directly against the files on disk.
  Metadata-only edits; each was verified beforehand on a backed-up sample
  pair (one mp3, one m4a) that duration/audio payload was untouched, then
  confirmed after the full run with a random 12-file spot check across both
  books/formats. `app.py` itself doesn't read or serve these tags (it gets
  episode labels from filenames, not ID3/MP4 metadata) — this only matters
  to whoever opens a downloaded file in their own music player.
- **Traceability tags** (2026-08-11): user was concerned downloaded files
  wouldn't be traceable back to the site once shared out of context. Added,
  same one-off `mutagen` script pattern as above:
  - mp3 (via `EasyID3`): `copyright` = "© 2026 Amrutkan (amrutkan.org)"
    (`TCOP` frame), `website` = "https://amrutkan.org" (`WOAR` frame — the
    ID3 frame specifically meant for "official webpage for this audio").
  - m4a (via `mutagen.mp4.MP4`): `©cmt` (comment) = "© 2026 Amrutkan —
    https://amrutkan.org", and `cprt` = "© 2026 Amrutkan" — both plain
    atoms, no `MP4FreeForm` wrapping needed, confirmed working on both the
    sample test and the full run.
  - Deliberately **Latin script**, not Devanagari, for these two fields
    specifically (unlike the rest of the site/tags) — many car
    stereos/players/OS metadata viewers have weak Devanagari font support,
    and the whole point of this pass is the text being legibly readable
    wherever the file ends up, which matters more here than it does for
    Artist/Album (which most players handle fine either way).
  - Same verification rigor as the Artist/Album pass: sample pair tested
    first (duration unchanged, **file size delta was exactly 0 bytes on
    both samples** — existing ID3/MP4 tag padding absorbed the new fields
    without needing to resize/shift anything), then the full run (401 mp3 +
    42 m4a = 443, matching the known total exactly, zero errors), then a
    12-file random spot check confirming both new fields and the
    pre-existing Artist/Album tags together.

## Architecture

**Hybrid: Python backend (data + streaming), React frontend (UI).** Node.js
is a *build-time-only* tool — the running production process is still just
`python3 app.py`, no Node process in production.

**Content model** (`app.py`, unchanged by the React migration): episode
filenames follow the pattern `<book prefix> - अध्याय <N> ...` or
`<book prefix> - ओवी <N> ...`. `build_library()` parses this at startup with
regex, grouping episodes by book → chapter/verse number (Devanagari numerals
handled via `to_int`/`to_devanagari`). Files that don't match a numbered
chapter (intros, summaries, biographies) land in an `"other"` bucket per book
initially — but per-book `SPECIAL_CHAPTER_ORDER` (2026-08-10) pulls specific
ones out of that bucket by exact label match and gives them their own
individually-labelled tile at a fixed position relative to the numbered
chapters, instead of a generic "इतर" tile:
- **ज्ञानेश्वरी**: परिचय leads (before अध्याय १), सिंहावलोकन trails (after
  अध्याय १८).
- **चांगदेव पासष्टी**: तीन items all lead (before ओवी १), in this order —
  चांगदेवांचे चरित्र, ज्ञानेश्वरांचे चरित्र, सारांश.
- If a book has "other" files with labels *not* in its `SPECIAL_CHAPTER_ORDER`
  config, those still fall back to a generic `"other"`/इतर tile.
- Within each chapter, `सारांश`-prefixed episodes always sort first (before
  श्लोक/ओवी/नमन/etc.) — see the sort key in `build_library()`.

This means **new episodes just need to follow the same filename convention
and the server restarted** — no code changes needed to pick them up, *unless*
the new file is a special one-off (like a new intro/summary/biography) that
should get special positioning, in which case it needs an entry added to
`SPECIAL_CHAPTER_ORDER`.

**Backend (`app.py`)**:
- `/api/library` — full book/chapter/episode tree as JSON. Originally built
  for the native `AmrutkanApp` (Expo/React Native) mobile app; the web
  frontend now consumes the exact same endpoint.
- `/api/home` — static home-page content (about text, podcast links, YouTube
  IDs) as JSON, added 2026-08-11 specifically for the React frontend so that
  content isn't duplicated between Python and TypeScript.
- `/audio/<filename>` — HTTP Range-request audio streaming (`serve_audio`).
- `/download/book/<id>[/<slug>]` — streamed ZIP of a whole book or one
  chapter (`serve_zip`, `build_book_zip_items`/`build_chapter_zip_items`) —
  see "Bulk ZIP download" below.
- `/`, `/book/<id>`, `/book/<id>/<slug>` — **not** rendered server-side
  anymore. `spa_shell()` generates a minimal HTML shell with per-route
  `<title>`/`og:*` meta tags (so social link previews keep working — pulled
  from `LIBRARY` data, no need to fully resolve a page just for its title)
  plus `<div id="root">` and the built React `<script>` tag. React Router
  (client-side) takes it from there once the bundle loads. A direct/refreshed
  load of a deep URL like `/book/dnyaneshwari/1` still works correctly since
  Python serves the same shell for every one of these routes and React reads
  the current URL on mount.
- `/assets/<file>` — serves `frontend/dist/assets/*` (the Vite build's
  content-hashed JS bundle), long-lived immutable `Cache-Control` since the
  filename changes whenever the content does. `spa_shell()` doesn't hardcode
  the hashed filename — it extracts the actual `<script>`/`<link>` tags out
  of `frontend/dist/index.html` at startup (`_load_frontend_asset_tags()`),
  so a new `npm run build` output is picked up automatically on the next
  `app.py` restart with zero code changes.
- `GA_SNIPPET` — Google Analytics 4 (`G-KLHSC2QRRW`), added 2026-08-11,
  embedded in every `spa_shell()` response.

**Frontend (`frontend/src/`)**:
- Vite + React 19 + TypeScript + Ant Design (antd v6) + `react-router-dom`.
- `App.tsx` — `ConfigProvider` (theme, incl. dark mode via
  `theme.darkAlgorithm`/`defaultAlgorithm`), top bar, `Routes` for `/`,
  `/book/:bookId`, `/book/:bookId/:slug`.
- `pages/Home.tsx`, `Book.tsx`, `Chapter.tsx` — fetch `/api/library` +
  `/api/home`, render with antd `Card`/`Row`/`Col`/`List`/`Breadcrumb`.
  Devanagari-numeral episode counts and the folder-vs-track tile icon
  (single-episode tiles like परिचय/सिंहावलोकन suppress the redundant "१ भाग"
  badge) match the original design's behavior. Podcast links skip
  `target="_blank"` on mobile UA (`navigator.userAgent` regex, client-side
  now — was server-side `MOBILE_UA_RE` in the old Python implementation) so
  iOS/Android can hand off to native podcast apps.
- `player/PlayerContext.tsx` — all player state/logic (play/pause/seek,
  playlist-aware prev/next, speed presets, sleep timer, MediaSession
  lock-screen controls, resume-on-reload via `localStorage`). Mounted once at
  the `App` root (`PlayerProvider` wraps `Routes`, not the other way around)
  so it survives client-side route navigation — the React equivalent of the
  old implementation's trick of keeping `<audio>` outside the DOM region that
  got swapped on navigation. `localStorage` keys (`ak_speed`, `ak_playback`)
  are unchanged from the old implementation, same shape.
- `player/MiniBar.tsx` / `NowPlayingOverlay.tsx` — persistent bottom bar +
  expandable full player UI (seek `Slider`, speed/sleep `Dropdown` menus,
  download link, help `Popover`).
- Dev workflow: `cd frontend && npm run dev` (Vite dev server, proxies
  `/api`, `/audio`, `/static`, `/download` to `python3 app.py` on 8080 — see
  `vite.config.ts`). Deploy workflow: `cd frontend && npm run build`, then
  `systemctl --user restart audio-site.service` — **the build step is
  required**, `app.py` restart alone does not pick up frontend source
  changes, only a freshly-built `frontend/dist/`.

**Known gap vs. the old implementation**: the pre-React version had some
purely decorative touches — a custom ASCII-art loading skeleton between SPA
navigations, and a staggered fade-in animation for card/tile grids — that
were not carried over in the rewrite (out of scope for the approved
migration plan, which prioritized functional parity: player, dark mode,
downloads, content). antd's default `Spin` loading state and `Card hoverable`
interactions cover the baseline UX. Worth adding back only if the user
actually misses them.

## Running it

As of 2026-08-10, both the app and the tunnel run as **systemd user services**
(not manual `nohup`) so they auto-restart on crash *and* on WiFi
drops/reconnects, and start automatically on boot (`loginctl enable-linger` is
on for this user, so they come up even without an interactive login).

Unit files: `~/.config/systemd/user/audio-site.service` (runs `app.py`),
`~/.config/systemd/user/audio-site-tunnel.service` (runs `cloudflared`), and
`audio-site-healthcheck.service`/`.timer` (see "Health check" below).

**Important: the app and tunnel units are deliberately *not* bound together**
(no `BindsTo=`). They were bound together initially, but that meant every
`systemctl restart audio-site.service` (e.g. for a code change) also bounced
the tunnel and handed out a **new random URL**, breaking links people already
had — see the 2026-08-10 incident below. Now restarting `app.py` never
changes the public URL; the tunnel only restarts (and thus changes URL) if it
itself crashes, or on a full reboot.

```bash
systemctl --user status audio-site.service audio-site-tunnel.service audio-site-healthcheck.timer
systemctl --user restart audio-site.service          # picks up app.py edits; tunnel is NOT affected, URL stays the same
journalctl --user -u audio-site.service -f            # app stdout/stderr (was app.log before)
journalctl --user -u audio-site-tunnel.service -f     # tunnel logs, incl. the public URL on startup
tail -f ~/audio-site/access.log                       # HTTP request log (see "Access log" below)
```

**To restart after editing `app.py`**: `systemctl --user restart audio-site.service`
is enough — no more manual pkill/nohup dance, no more "two separate tool calls"
sandbox quirk (that only applied to the old manual-process workflow). This is
now safe to do freely — it does **not** change the public URL (see above).

**To deploy after editing anything in `frontend/src/`**: build *first*, then
restart — `cd frontend && npm run build && cd .. && systemctl --user restart
audio-site.service`. Restarting without rebuilding just re-serves the
previous `frontend/dist/` unchanged; the Python process never reads
`frontend/src/` directly.

**To check it's alive**: `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/`

**The public URL is now fixed**: `https://amrutkan.org` — no more digging
through `journalctl` for a random hostname (that was only ever needed for
quick tunnels, see "The cloudflared tunnel" below).

## The cloudflared tunnel

Installed at `~/.local/bin/cloudflared` (added to PATH via `~/.bashrc`, since
`sudo apt install` wasn't available — see "Known constraints" below; this is
also why the 2026-08-11 domain switch deliberately stayed on this same
user-level, no-sudo `cloudflared` binary rather than following Cloudflare
dashboard's suggested `sudo apt-get install cloudflared` +
`cloudflared service install <token>` flow, which would've installed a
second, root-owned `cloudflared` as a system-level systemd service — more
moving parts and root-owned processes for a low-traffic hobby site with no
real upside).

### Named tunnel setup (2026-08-11)

Switched from the quick tunnel (see below) to a **named** Cloudflare Tunnel
now that the user owns `amrutkan.org` (bought via Cloudflare Registrar, so
the zone/nameservers were already on Cloudflare — no separate DNS migration
needed). Set up entirely from the CLI, no dashboard/token flow:

- `cloudflared tunnel login` — one-time OAuth against the Cloudflare account
  that owns the zone; writes `~/.cloudflared/cert.pem`. Had to be run
  interactively by the user (needs a real browser + their Cloudflare login);
  hit a snag where the account's email needed verifying first, which briefly
  stalled the `argotunnel` authorize page — resolved by re-visiting that same
  authorize URL after verifying the email, rather than re-running the login
  command from scratch.
- `cloudflared tunnel create amrutkan` — created tunnel id
  `e1f7a75e-9ebb-4695-a2eb-481f89d0c021`, credentials written to
  `~/.cloudflared/e1f7a75e-9ebb-4695-a2eb-481f89d0c021.json`.
- `~/.cloudflared/config.yml` — ingress rules mapping both `amrutkan.org`
  and `www.amrutkan.org` → `http://localhost:8080` (the same port `app.py`
  always listened on), falling back to `http_status:404` for any other
  hostname.
- `cloudflared tunnel route dns amrutkan amrutkan.org` and
  `cloudflared tunnel route dns amrutkan www.amrutkan.org` — added CNAMEs
  for both hostnames in the `amrutkan.org` zone, both pointing at
  `<tunnel-id>.cfargotunnel.com`.
- **`www` → root redirect**: rather than a Cloudflare-side Redirect Rule
  (would need dashboard/API access this session doesn't have), `www` is
  routed through the tunnel to the same `app.py` like any other hostname,
  and `AudioHandler.do_GET` checks the incoming `Host` header first thing —
  if it's `www.{PRIMARY_DOMAIN}` (constant near the top of `app.py`), it
  replies `301` with `Location: https://{PRIMARY_DOMAIN}{self.path}` and
  returns immediately, before any routing. `self.path` already carries the
  full path + query string as sent, so it's reflected into the `Location`
  header verbatim — no separate parsing/reassembly needed to preserve query
  params.
- `audio-site-tunnel.service`'s `ExecStart` changed from
  `cloudflared tunnel --url http://localhost:8080` (quick tunnel) to
  `cloudflared --config ~/.cloudflared/config.yml tunnel run` (named tunnel,
  reads the ingress rule above). Everything else about the unit (independent
  from `audio-site.service`, no `BindsTo=`, `Restart=always`) is unchanged —
  that independence matters even more now: an `app.py` restart still never
  touches the tunnel, and now the tunnel itself has no reason to ever change
  hostname either way, quick-tunnel-style random URLs are no longer a
  concern at all.
- `healthcheck.sh` used to discover the current public URL by grepping
  `journalctl` for a `*.trycloudflare.com` hostname (necessary only because
  quick tunnel hostnames were random and changed on every tunnel restart).
  With a fixed domain that's gone — it now just hits `https://amrutkan.org`
  directly, a hardcoded constant in the script.

**Important — for whoever continues this**: quick tunnel URLs are random and
change every time `cloudflared` restarts; that's what made the domain switch
worth doing (a named tunnel keeps `amrutkan.org` stable across every restart,
WiFi blip, and reboot). Quick tunnels were also explicitly not intended by
Cloudflare for sustained/production media streaming (no uptime guarantee) —
that limitation no longer applies now that this runs on a named tunnel.

### 2026-08-10 investigation: "audio quality" complaints

Users reported poor audio quality. Root-caused via `journalctl` cross-referenced
with `cloudflared`'s logs: it wasn't the files (sampled MP3s are legit 256kbps
CBR/44.1kHz) or bandwidth (tested ~143Mbps upload, WiFi at 99% signal). It was
dropouts: the laptop's WiFi disconnected/reassociated twice on 2026-08-09
(`journalctl -k` / NetworkManager logs), and both times matched, to the second,
`cloudflared` logging QUIC failures and forced reconnects — which kills the
tunnel's single connection and cuts off every listener at once. Contributing
factors fixed the same day: `app.py` was HTTP/1.0-only with no keep-alive
(every buffered/seek Range request paid a fresh TCP+QUIC-stream setup — now
`protocol_version = "HTTP/1.1"` on `AudioHandler`), and the listen backlog was
the stdlib default of 5 (now `request_queue_size = 128` on
`ThreadingHTTPServer`). The systemd services (above) address the "whole tunnel
dies and doesn't come back" part; the underlying single-WiFi-link,
single-quick-tunnel fragility is structural and only really goes away with a
named tunnel (and ideally a wired ethernet connection instead of WiFi —
`enp1s0f0` exists on this machine but was unplugged/`NO-CARRIER` at the time of
this investigation).

### 2026-08-10 incident: `BindsTo=` caused an unwanted URL change

Shortly after the systemd setup above, the tunnel unit had
`BindsTo=audio-site.service` so it would stop if the app went down. Restarting
`app.py` for an unrelated change (an icon fix) also stopped-and-restarted the
tunnel via that binding, which — because quick tunnels always mint a new
random hostname on restart — silently broke the URL the user had already
shared, producing a Cloudflare 1033 error for anyone using the old link.
Fixed by removing `BindsTo=` so the two units are independent; see "Running
it" above. Lesson: don't couple a quick-tunnel process's lifecycle to
anything that restarts more often than the tunnel itself needs to.

## Player features (React implementation, `frontend/src/player/`)

Ported 2026-08-11 from the original hand-rolled JS (`GLOBAL_SCRIPT`, now
deleted from `app.py` — see git history before the React migration commit if
the old implementation details are ever needed) into `PlayerContext.tsx`.
Behavior is unchanged from the original design:

- **Lock-screen / Bluetooth controls**: `navigator.mediaSession` — metadata,
  action handlers (play/pause/prev/next/seek), position sync. Registered
  once in a `useEffect`, reading live state via refs to avoid stale
  closures. **Still not verified on a real device** — worth confirming on
  the user's actual iPhone/Android.
- **Resume where you left off**: `localStorage` key `ak_playback`
  (`{src, label, subtitle, playlist, index, currentTime}`), saved on pause,
  every ~5s during playback, and on `pagehide`. Restores track/position on
  load but does **not** autoplay.
- **Playback speed** (`SPEED_PRESETS = [0.75, 1, 1.25, 1.5, 1.75, 2]`,
  `localStorage` key `ak_speed`) and **sleep timer** (episode-end default,
  or 15/30/45/60 min, or off — timer state intentionally *not* persisted
  across visits) — both via antd `Dropdown` menus in `NowPlayingOverlay.tsx`,
  replacing the old bottom-sheet popups.
- **Download**: plain `<a download href="/audio/...">` per episode and in
  the overlay — no special click-interception needed anymore (that was only
  required by the old implementation's manual SPA navigation hijacking;
  React Router doesn't touch `download`-attribute links).
- **Favicon + Open Graph tags**: still `static/mauli.jpg` as favicon
  (`spa_shell()` in `app.py`, not the frontend); OG tags generated
  server-side per-route so link previews work without needing SSR of the
  actual React content.

## Digital book reader — पुस्तके (added 2026-08-12)

A second, unrelated content type from the audio library: two spiritual
books by the same author (सुरेश चौधरी / डॉ. सुरेश चौधरी) — **सोपी गीता**
(107 pages) and **चैतन्य सागर** (160 pages, subtitle "ज्ञानेश्वरी ग्रंथ का
हिन्दी सारांश") — shown page-by-page on the site, deliberately **not**
downloadable as a PDF. The author's own copyright notice inside चैतन्य
सागर explicitly prohibits reproduction without written permission, so
this isn't just a nice-to-have: the whole design is built around never
letting a complete, high-fidelity copy of either book reach the client
in one file.

**How "can't download the PDF" actually works** — realistically, nothing
running in a browser can stop a screenshot or screen recording. What this
*does* stop is the casual/one-click path (a saved PDF, a spoofed download
link, a browser "Save Page As"):
- The source PDFs are **never in the repo and never served**. They live
  outside the repo entirely, at `PUSTAK_SOURCE_DIR`
  (`~/Desktop/पुस्तके/<title>.pdf`) — same convention as `AUDIO_DIR`, and
  necessary because **this repo is public** (see "AmrutkanSite repo
  renamed+public" — anything committed here is world-readable in git
  history forever).
- `build_pustak_cache.py` (repo root, one-off script, same pattern as
  `build_zip_cache.py`) pre-renders every page of every book to a JPEG via
  poppler's `pdftoppm` CLI — **no pip dependency**, `poppler-utils` is
  already an installed system package (see "No pip/venv" below).
  150 DPI / JPEG quality 78 is a deliberate middle ground: fully legible
  Devanagari text on screen, well below print quality, so reassembling a
  page-by-page save doesn't get you a high-fidelity copy either. Output
  goes to `pustak-cache/<book-id>/page-0001.jpg` etc (gitignored, ~44MB
  total for both books) — `app.py` only ever reads from this cache, never
  touches the source PDF at request time. Re-run manually whenever a book
  is added or replaced under `PUSTAK_SOURCE_DIR`; safe to re-run any time,
  each book renders into a temp dir and is atomically swapped in.
- `PUSTAK_DEFS`/`PUSTAK_BY_ID` in `app.py` hold the book metadata (title,
  subtitle, author, source filename) — titles/author were read directly
  off each book's actual cover/title-page render (the PDFs' embedded text
  layer is a garbled legacy Hindi font encoding, not extractable with
  `pdftotext`; the cover images render fine, that's what was read).
- **Backend (`app.py`)**: `/api/pustake` — book list + live page count
  (counted from files actually present in `pustak-cache/<id>/`, no
  restart needed if the cache is rebuilt) + `thumbnailUrl` (just page 1).
  `/pustak/<book-id>` — SPA shell (client-side reader route, same pattern
  as `/book/<id>`). `/pustak/<book-id>/page/<n>.jpg` —
  `serve_pustak_page()` serves exactly one page image, 404 for an unknown
  book id, non-numeric/out-of-range `n`, or a page not yet rendered; no
  `Content-Disposition` is set (so it renders inline like any `<img>`,
  never a download prompt); path traversal isn't reachable at all since
  the filename is rebuilt from a validated `int` and a dict-whitelisted
  book id, never from the raw request string.
- **Frontend**: `pages/Home.tsx` — new "पुस्तके" section between यूट्यूब
  and आमच्याबद्दल (आमच्याबद्दल's tint flipped from `colorBgContainer` to
  `colorFillAlter` so the two sections still read as visually distinct);
  renders only once `/api/pustake` resolves with at least one book, so a
  not-yet-built cache just hides the section rather than showing broken
  thumbnails. `pages/Pustak.tsx` — the reader itself: draws each page into
  a `<canvas>` (`new Image()` → `drawImage`) rather than an `<img>`, since
  a canvas has no built-in "Save image as…"/drag-out affordance;
  `onContextMenu`/`onDragStart` prevented on top of that, plus
  `user-select: none` and `-webkit-touch-callout: none` (blocks iOS
  long-press-to-save). Prev/Next buttons + ←/→ keyboard nav; next page is
  prefetched (`new Image().src = ...`) so paging forward feels instant.
  Page counter uses the existing `toDevanagari()` helper ("पृष्ठ १ / १०७").
  Registered as `/pustak/:bookId` in `App.tsx`.
- Verified end-to-end with Playwright against the live systemd service
  (2026-08-12): both books' cover thumbnails render correctly in the
  पुस्तके section, the reader loads page 1, and clicking next advances to
  page 2 with the counter updating — no console errors.

**Fullscreen/immersive reading mode (added 2026-08-12)**: a button next to
the page counter toggles a bigger, distraction-free view. Implemented as a
CSS state (`immersive`, on the same always-mounted `readerRef` container —
`position: fixed; inset: 0`, black background, breadcrumb/title hidden,
canvas scaled up to fill the viewport) rather than relying solely on the
native Fullscreen API, because that API is unsupported/blocked in a lot of
this site's actual traffic (iOS Safari on non-video elements, in-app
browsers like WhatsApp/Instagram). `readerRef.requestFullscreen()` is
still attempted best-effort on top when available (also hides the browser
chrome/address bar), wrapped in try/catch so a failure is silent and the
CSS state is what actually matters. **Important gotcha hit during
implementation**: an early version rendered the immersive layout as a
*separate* JSX subtree (two early-returns) — toggling immersive on
unmounted the div that native `requestFullscreen()` had just been called
on, which the browser treats as "fullscreen was exited" and immediately
fired `fullscreenchange`, snapping back to normal before the user ever saw
it. Fixed by keeping one persistent container across both states, only
restyled (not remounted) by the `immersive` flag. `Escape` and the
browser's own fullscreen-exit gestures (F11, Android swipe-down) are also
handled — a `fullscreenchange` listener syncs `immersive` back to `false`
if the browser exits fullscreen by some path other than the toggle button.
Page position/navigation state carries over across entering/exiting.
Verified with Playwright: entering shows the black immersive layout with
working prev/next controls, exiting restores the normal page layout with
the current page number preserved.

**Swipe-to-turn-page (added 2026-08-12)**: requested specifically for
mobile fullscreen reading. `onTouchStart`/`onTouchEnd` on the page-canvas
wrapper (works in both immersive and normal layout, same handlers) compare
start/end touch X/Y: a horizontal move past a 50px threshold that's more
horizontal than vertical (so an ordinary vertical scroll/tap isn't
misread) triggers a page turn — right-to-left → next page, left-to-right →
previous, matching the direction convention of every mainstream mobile
reader/gallery app. `touchAction: 'pan-y'` on that same element tells the
browser vertical panning is still native while horizontal drags are ours
to interpret, which also avoids fighting Safari's edge-swipe
back/forward-navigation gesture. Verified with Playwright's iPhone 13
emulation profile (synthetic `TouchEvent`s dispatched directly, since
Playwright has no built-in swipe helper): right-to-left advanced 1→2,
left-to-right returned 2→1, and a sub-threshold jitter correctly left the
page unchanged.

**Landscape fullscreen fills screen width (added 2026-08-12)**: previously
fullscreen always height-capped the canvas (`maxHeight: calc(100vh -
72px)`), which on a landscape phone (short viewport, portrait-shaped page)
left the page narrow with black bars on the sides — the opposite of what
fullscreen is for. Now tracked via `isLandscape`
(`window.matchMedia('(orientation: landscape)')`, re-checked on a
`change` listener so a physical rotation updates it live): in landscape
immersive mode the canvas switches to `width: 100%` with no height cap, so
it fills the screen's width and the page runs taller than the viewport
instead. The immersive container's `justifyContent` switches from
`center` to `flex-start` with `overflowY: auto` in that case specifically
— centering a flex item that overflows its container can leave the start
of the content unreachable by scroll in some browsers, top-aligning
avoids that class of bug entirely. Portrait fullscreen is unchanged
(still height-capped and centered, since the whole page already fits).
Same change moved the prev/next/page-counter/fullscreen-toggle controls
from the normal document flow to a `position: fixed` translucent bar
pinned to the bottom of the viewport whenever immersive — needed once the
page can scroll past the fold in landscape, otherwise the controls would
scroll out of reach along with it; extra bottom padding on the scrollable
area keeps the last part of a scrolled page from hiding behind that bar.
Swipe navigation (previous entry) works unchanged in both orientations,
same handlers. Verified with Playwright's `'iPhone 13 landscape'` device
profile: canvas width matched the viewport width exactly (749.98px vs
750px), scrolling revealed the rest of the page with the control bar
staying fixed on top, and a swipe still advanced the page correctly.

**Zoom in fullscreen (added 2026-08-12)**: `ZoomInOutlined`/`ZoomOutOutlined`
buttons in the fullscreen control bar, `zoom` state from `ZOOM_MIN=1`
(fit-to-screen) to `ZOOM_MAX=3` in `ZOOM_STEP=0.25` increments, disabled
at each bound like the prev/next buttons. The canvas's fit-to-screen width
is now computed in real pixels rather than CSS percentages specifically so
zoom can just multiply it: landscape's fit width is `window.innerWidth`,
portrait's is derived from the loaded image's own aspect ratio
(`naturalSize`, captured in the page-load `useEffect` alongside the
existing `drawImage` call) against the height cap — `zoom` is then just
`fitWidthPx * zoom`. `flexShrink: 0` on the canvas prevents the wrapper's
default flex-shrink from squeezing an oversized zoomed canvas back down
(a real flexbox pitfall with replaced elements, not hypothetical — worth
keeping if this component is touched again). The immersive
container's scroll/alignment logic (previously keyed only on `isLandscape`,
see the "Landscape fullscreen" entry above) now keys on a broader
`scrollable = isLandscape || zoom > 1`, since zooming in can push a
portrait page past the viewport in both dimensions, not just landscape's
width-fill — same top/left-align-instead-of-center reasoning applies to
both axes now, not just the vertical one. `touchAction` on the page
wrapper switches from `'pan-y'` to `'auto'` while zoomed, handing both-
axis panning to native browser scrolling.

**Swipe-to-turn-page is suppressed while zoomed** (`zoom !== 1` checked in
`onTouchEnd`, added by explicit request) — the reasoning being that a
horizontal drag on a zoomed-in page is someone panning across it to read
different areas, not asking to turn the page. Zoom resets to 1 on page
change, on an orientation change, and on exiting fullscreen — the fit
calculation is per-layout, so it can't be preserved sensibly across any of
those; the reset is what stops it, not any of the size math changing
underneath the user unexpectedly. **Loading state** was changed the same
session from an antd `Skeleton.Image` placeholder to a `Spin` (the
rotating-dots loader) — requested because the skeleton read as "this looks
like a broken image," `Spin` unambiguously reads as "loading," centered
inside the same 2:3 aspect-ratio placeholder box so there's no layout jump
once the real page image arrives. Verified with Playwright (mobile
viewport, `hasTouch: true`, route interception adding a 1.5s delay to page
image responses so the spinner state is actually observable instead of
flashing by on localhost): `Spin` visible during the delayed load; two
zoom-in clicks scaled canvas width from 476px to 714px (exactly 1.5×, i.e.
zoom 1.0 → 1.5 in 0.25 steps); a swipe while zoomed left the page
unchanged; zooming back to 1.0 restored the exact original 476px width;
a swipe at that point correctly advanced the page; and the zoom-out button
was correctly disabled once back at the minimum.

**Bugfix: zooming out after panning left a weird off-center view (fixed
2026-08-12)**: reported by the user on mobile — zoom in, touch-pan to some
other part of the page, zoom back out, and the view landed somewhere
off-center/wrong instead of back on the fit-to-screen page. Root cause:
panning sets the immersive container's `scrollTop`/`scrollLeft` to
whatever arbitrary position the user dragged to, and that raw scroll
offset was never reset — so when zoom changed and the canvas resized
underneath it, the *same* leftover pixel offset now pointed at a
completely different part of the (now differently-sized) content. Fixed
with a `useEffect` keyed on `[page, isLandscape, zoom]` that snaps
`readerRef`'s `scrollTop`/`scrollLeft` back to `0, 0` on every one of
those transitions — each new page/orientation/zoom now always starts from
a known top-left position instead of inheriting a stale offset computed
for a different size. Verified with Playwright: zoomed in 3 steps,
confirmed scroll was `(0, 0)` right after (the reset already firing on
zoom-in too), manually set it to `(300, 150)` to simulate a pan, zoomed
back out 3 steps, and confirmed scroll was `(0, 0)` again with the page
correctly centered and fully in frame in the screenshot.

## Bulk ZIP download (added 2026-08-11)

Every book page (`/book/<id>`) and chapter page (`/book/<id>/<slug>`) has a
download-all button that downloads the whole book or the whole chapter/verse
as a single `.zip` — `/download/book/<id>` and `/download/book/<id>/<slug>`
in `do_GET`, unchanged by the React migration (backend-only feature).

Implementation lives in `AudioHandler.serve_zip()` plus
`build_book_zip_items()`/`build_chapter_zip_items()` (resolve book/chapter
into a `(display_name, [(arcname, filepath), ...])` list). Two things make
this safe for a book that can be several GB (443 files / ~17GB total across
both books):
- **Never buffered in memory or on disk.** `zipfile.ZipFile` is handed a
  `_NonSeekableWriter` wrapping `self.wfile` directly — a minimal file-like
  object exposing only `write()`/`flush()`, no `tell()`/`seek()`. `ZipFile`
  detects that as non-seekable (`fp.tell()` raising `AttributeError`) and
  automatically switches to writing data descriptors (size/CRC *after* each
  entry) instead of seeking back to patch local file headers, which is
  exactly what a live HTTP response stream needs. `ZipFile.write()` itself
  already streams each source file in 8KB chunks (`shutil.copyfileobj`)
  rather than reading it whole, and `ZIP_STORED` (no compression) is used
  since the mp3/m4a sources are already compressed — compressing again
  would only cost CPU for no size win.
- **No `Content-Length`.** The total size isn't known upfront without a
  first pass over every file, so the response instead sends
  `Connection: close` — `BaseHTTPRequestHandler.send_header` auto-sets
  `self.close_connection = True` when it sees that, and the client treats
  the socket closing as end-of-body, which is standard, spec-compliant
  HTTP/1.1 behavior when neither `Content-Length` nor chunked encoding is
  used.

`Content-Disposition` sends both an ASCII fallback filename (built from the
already-ASCII `book_id`/`slug`, e.g. `changdev-1.zip`) and an
RFC 5987 `filename*=UTF-8''...` with the real Devanagari name, same
two-name pattern as the OG tags elsewhere in this file. Verified manually:
downloaded a full book (changdev, 135 files / ~4.3GB) and a single chapter
against a throwaway instance on a scratch port, `zipfile.testzip()` came
back clean on both, entries land in per-chapter subfolders for the
book-level zip (flat for a single-chapter zip, since it's already one
unit).

### ZIP cache — real file sizes shown during download (added 2026-08-11)

Users couldn't see download size/progress for ZIPs (unlike individual
episode downloads, which already sent a real `Content-Length` — see
`serve_audio`) because `serve_zip()` above deliberately never knows the
total size upfront. Fix: `build_zip_cache.py` (repo root, one-off script,
same pattern as the ID3-tagging scripts) pre-builds *every* book and
chapter ZIP — 2 book-level + ~88 chapter-level, 90 files total — into
`zip-cache/` (gitignored) using a normal seekable local file, not the
streaming `_NonSeekableWriter` trick (only needed for a live HTTP
response). `do_GET`'s two download routes now check
`zip-cache/book/<id>.zip` / `zip-cache/book/<id>/<slug>.zip` first; if
present, `AudioHandler.serve_cached_zip()` serves it as a plain static
file with a real `Content-Length` (browser shows exact size/progress).
If **absent**, falls straight back to the existing `serve_zip()` live-build
— so a missing/stale cache entry never breaks downloads, it just means
that one won't show a size until the cache is (re)built.

**Storage cost**: ~34GB (every file appears once in its book-zip and once
in its chapter-zip, so ~2× the ~17GB source audio total) — checked against
free disk space before doing this (373GB free at the time, 339GB after).
**Not** rebuilt automatically on `app.py` startup (would add real time to
every restart, which happens often during development) — re-run
`python3 build_zip_cache.py` manually whenever audio content changes,
same "restart needed to pick up new episodes" pattern as the library scan.

Verified: small-scale cache-hit/cache-miss test first (manually placed one
test zip, confirmed cache-hit path returns the exact byte-for-byte file
with correct `Content-Length`, confirmed an uncached chapter still falls
back to the old streaming behavior correctly), *then* ran the full build
(90/90 files, ~34GB, well under a minute — NVMe + `ZIP_STORED` means it's
essentially a fast copy), spot-checked 4 real cached zips with
`zipfile.testzip()` (all clean, entry counts correct — 308 + 135 = 443,
matching the known total exactly), then confirmed on live production that
both a chapter zip and the ~4GB changdev whole-book zip return the correct
real `Content-Length` matching the build script's own reported sizes.

## gzip compression (added 2026-08-11)

`AudioHandler.maybe_gzip()`/`send_compressible()` gzip-compress the
response body when the client sends `Accept-Encoding: gzip` (essentially
universal) — applied to HTML (`serve_html`), JSON (`serve_json`), and the
frontend's built `.js`/`.css`/`.svg` (`serve_frontend_asset`). Skipped
below 512 bytes (not worth the overhead) and **deliberately never applied**
to audio, images, ZIPs, or `.woff`/`.woff2` fonts — all already-compressed
binary formats where gzip would only cost CPU for no size win, and for
Range-requested audio specifically, compressing would actively break
byte-range semantics (a "byte 1000000 of the compressed stream" has no
stable relationship to "byte 1000000 of the audio" — this must never be
touched).

Verified real-world impact before deploying: `/api/library` (large,
repetitive, mostly-Devanagari JSON) went from 264,047 bytes to 12,007 —
a 95% reduction. The frontend JS bundle went from ~940KB to ~296KB,
matching Vite's own reported gzip size from its build output. Confirmed
separately that audio/image responses never get a `Content-Encoding`
header even when the client offers gzip, and that Range requests on audio
still return the correct partial content — gzip must never come anywhere
near that code path.

## Access log

`log_message` on `AudioHandler` used to be a no-op. It now writes to
`~/audio-site/access.log` via a `logging.handlers.RotatingFileHandler`
(5MB × 3 backups, stdlib only) — one line per HTTP request/error, format
`<ip> [<date>] "<request line>" <status> -`. Added specifically because the
2026-08-10 audio-quality investigation had to lean entirely on `cloudflared`'s
tunnel-level logs; this gives an app-level record too. `tail -f
~/audio-site/access.log` to watch live traffic.

**`<ip>` is the real visitor IP** (2026-08-11 fix) — every request reaches
`app.py` via `cloudflared` on localhost, so `self.client_address[0]` is
always `127.0.0.1` and was being logged as such before this fix. `Cloudflare`
adds a `CF-Connecting-IP` header with the true visitor IP on every proxied
request; `log_message` now reads that (falling back to
`client_address[0]` if it's absent, e.g. hitting `app.py` directly during
local testing without going through the tunnel).

## Health check

`~/audio-site/healthcheck.sh`, run every 5 minutes by
`audio-site-healthcheck.timer` (systemd user timer, `OnBootSec=2min
OnUnitActiveSec=5min Persistent=true`). Each run: curls `localhost:8080`
(is `app.py` up) and `https://amrutkan.org` (is the whole path — app +
tunnel + Cloudflare edge — actually reachable), with one retry after 5s to
avoid flagging sub-5-second blips. State (`healthy`/`unhealthy`) is tracked
in `~/audio-site/.healthcheck_state`; a **transition** (not every check)
triggers a `notify-send` desktop notification — critical urgency + reason
when it goes down, a plain notification with the current URL when it
recovers. First-ever run never notifies (nothing to "recover" from).
Notification delivery depends on the user being logged into the graphical
Wayland session on this machine — there's no email/push fallback, so if the
laptop is logged out this degrades to log-only (`~/audio-site/healthcheck.log`).

## Known constraints for whoever continues this

- **No pip/venv available** in this environment: `python3-pip` and `python3-venv`
  aren't installed, and `sudo` requires interactive auth that isn't available in
  this session (no passwordless sudo). This is why `app.py` deliberately avoids
  Flask/any third-party **Python** package — stick to stdlib unless the user
  installs pip themselves (`sudo apt install python3-pip python3-venv`, which
  they'd need to run themselves via `!` in a Claude Code session, or the
  environment changes). `python3-mutagen` is an exception — the user installed
  it via `sudo apt` (2026-08-11, interactively) for one-off audio-tag editing.
  That's still an apt package, not pip — general third-party Python
  dependencies for `app.py` itself remain off the table under this constraint.
  This does **not** apply to the frontend — `frontend/` has its own Node/npm
  toolchain (already installed via nvm) and normal npm dependencies (React,
  antd, etc.) are expected and fine there; the "no dependencies" constraint
  was always specifically about keeping the *Python runtime process* simple,
  not about the build tooling.
- **Sandbox quirk with `pkill`**: running `pkill` in the same Bash tool call as
  a follow-up command (e.g. `pkill ...; nohup ...`) reliably produces a strange
  exit code (144) and the rest of that command block silently doesn't run, even
  though the kill itself did take effect at the OS level. This mattered for the
  old manual `nohup` workflow; now that both processes are systemd user
  services, use `systemctl --user restart audio-site.service` instead of
  `pkill`/`nohup` and this quirk shouldn't come up. If you do ever need to kill
  a stray process directly, still treat kill and restart as **separate** tool
  calls, checking `ps aux` in between.
- This machine is the user's real local PC (Ubuntu, home directory
  `/home/satyasheel`), not a disposable container — audio files and everything
  else here are real user data.

## Possible next steps (not yet done, only do if asked)

- Confirm lock-screen/Bluetooth media controls actually work on the user's
  real iPhone/Android — implemented 2026-08-10, ported to React 2026-08-11,
  still never visually verified on a real device.
- Consider code-splitting the frontend bundle — `npm run build` currently
  warns about a single ~770KB JS chunk (mostly antd). Not urgent for a
  low-traffic hobby site, but worth revisiting if load time ever matters.
- Optional polish: the pre-React implementation had a custom loading
  skeleton and staggered card-entrance animation that weren't carried over
  in the rewrite (see "Known gap" in Architecture above) — only worth doing
  if the user actually wants that motion polish back.
- Prefer wired ethernet (`enp1s0f0`) over WiFi for this machine if practical —
  WiFi disconnect/reassociate events have been observed to kill the tunnel
  mid-stream (see 2026-08-10 investigation above).
- `python3 app.py` currently rescans the folder only at startup — if the user
  adds new episodes, the process needs restarting to pick them up
  (`systemctl --user restart audio-site.service`).
