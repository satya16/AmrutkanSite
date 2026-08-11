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

## Files

- `app.py` — the entire application. Single file, **no external dependencies**
  (see "No pip/venv" below for why).
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

## Architecture

Pure Python 3 standard library (`http.server` + `socketserver`), threaded so
multiple people can stream concurrently. No Flask/Django — see below for why.

**Content model**: episode filenames follow the pattern
`<book prefix> - अध्याय <N> ...` or `<book prefix> - ओवी <N> ...`. `build_library()`
in `app.py` parses this at startup with regex, grouping episodes by book →
chapter/verse number (Devanagari numerals handled via `to_int`/`to_devanagari`).
Files that don't match a numbered chapter (intros, summaries, biographies) land
in an `"other"` bucket per book initially — but per-book `SPECIAL_CHAPTER_ORDER`
(2026-08-10) pulls specific ones out of that bucket by exact label match and
gives them their own individually-labelled tile at a fixed position relative
to the numbered chapters, instead of a generic "इतर" tile:
- **ज्ञानेश्वरी**: परिचय leads (before अध्याय १), सिंहावलोकन trails (after
  अध्याय १८).
- **चांगदेव पासष्टी**: तीन items all lead (before ओवी १), in this order —
  चांगदेवांचे चरित्र, ज्ञानेश्वरांचे चरित्र, सारांश.
- If a book has "other" files with labels *not* in its `SPECIAL_CHAPTER_ORDER`
  config, those still fall back to a generic `"other"`/इतर tile — the config
  only special-cases the specific labels listed, so this degrades gracefully
  if a new unrecognized extra file shows up later (restart still needed to
  pick it up, per usual, but it won't silently vanish — it'll surface as an
  इतर tile same as before, prompting whoever's maintaining this to add it to
  the config or leave it there).
- Within each chapter, `सारांश`-prefixed episodes always sort first (before
  श्लोक/ओवी/नमन/etc.) — see the sort key in `build_library()`.
- Book tiles get a small icon (`ICON_TRACK` vs `ICON_FOLDER` in `app.py`,
  keyed off episode count == 1) as a subtle visual hint for whether tapping
  goes to a single track or a multi-episode list. The "N भाग" count badge is
  suppressed for single-file tiles (`render_book()`) — with the track icon
  already showing it's one file, "१ भाग" was redundant.

This means **new episodes just need to follow the same filename convention
and the server restarted** — no code changes needed to pick them up, *unless*
the new file is a special one-off (like a new intro/summary/biography) that
should get special positioning, in which case it needs an entry added to
`SPECIAL_CHAPTER_ORDER`.

**Site structure**: 3-level drill-down — home (2 book cards) → book page (grid
of chapter/verse tiles) → chapter page (episode list). Feels like a file browser,
per the user's request.

**Frontend**: Server-rendered HTML, but navigation is intercepted client-side
(`GLOBAL_SCRIPT` in `app.py`) — clicking a link does a `fetch()` with an
`X-Partial: 1` header instead of a full page load; the server responds with just
the inner content fragment (see `serve_page`/`do_GET`), which replaces `#content`
via `innerHTML`, plus `history.pushState`. This is what makes the **audio player
survive navigation** — the `<audio>` element lives in the persistent outer shell
(`page_shell()`), not inside the part of the page that gets swapped.

**Player UI**: fixed bar at the bottom of the screen (mini bar: track name +
play/pause + thin progress line), tap to expand and reveal native `<audio
controls>` for seeking/volume. Audio streaming supports HTTP Range requests
(`serve_audio`) so seeking works.

**Dark mode**: toggle button top-right of the header, preference stored in
`localStorage`, CSS variables swapped via `[data-theme="dark"]`.

**Mobile**: responsive grid layouts, `env(safe-area-inset-bottom)` padding on
the player bar for iOS gesture bar clearance, media query at 600px.

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

## Listener-experience features (added 2026-08-10)

All implemented in `app.py`'s `GLOBAL_SCRIPT` (client JS) and `page_shell()`/
`render_chapter()` (server-rendered markup), no new dependencies:

- **Lock-screen / Bluetooth controls**: `navigator.mediaSession` — metadata
  (title/artist/artwork) set in `APP.play()`/`updateMediaSessionMetadata()`,
  action handlers (play/pause/prev/next/seek) wired in `initMediaSession()`,
  position synced via `setPositionState` in `updateProgress()`. Untested on a
  real device from this session — worth confirming lock-screen controls
  actually show up on both iOS and Android.
- **Resume where you left off**: `APP.savePlayback()`/`restorePlayback()`
  persist `{src, label, subtitle, playlist, index, currentTime}` to
  `localStorage` (key `ak_playback`) — on pause, every ~5s during playback,
  and on `pagehide`. On load, the player restores to the saved track/position
  but does **not** autoplay (browser autoplay policies + less surprising UX).
  The `<audio>` tag has `preload="metadata"` specifically so restoring a
  saved track on page load doesn't eagerly start downloading the full file
  before the user actually presses play.
- **Playback speed ("गती")** and **timer ("टायमर")**: originally cycle-on-tap
  pills, changed 2026-08-10 to open a bottom-sheet popup instead (per user
  feedback — a plain "sleep" label with cycling wasn't discoverable/legible in
  Marathi). `np-speed`/`np-sleep` buttons call `openPopup('speed'|'sleep')`;
  `#speed-popup`/`#sleep-popup`/`#popup-backdrop` are rendered as **siblings
  of** (not nested inside) `#now-playing-overlay` specifically to avoid a CSS
  gotcha — the overlay has a `transform`, which makes it a containing block
  for `position: fixed` descendants, so a popup nested inside it wouldn't be
  truly viewport-fixed. Selecting an item calls `setSpeed()`/
  `setSleepOption()`, which apply the change and call `closePopup()`.
  - Speed: `SPEED_PRESETS = [0.75, 1, 1.25, 1.5, 1.75, 2]` (ascending order,
    matches popup list order), persisted in `localStorage` (`ak_speed`),
    applied via `audio.playbackRate`.
  - Timer: **defaults to "भाग संपल्यावर"** (`sleepMode: 'episode'` in `APP`'s
    initial state, not `null`/off) — i.e. out of the box, playback stops when
    the current episode ends rather than auto-advancing to the next one;
    listening to more than one episode in a sitting requires explicitly
    picking "बंद" in the popup. Handled in the `ended` listener via
    `onEnded()`, which skips `playNext()` and clears the mode instead of
    auto-advancing when in episode mode. Other options: 15/30/45/60 minutes
    (wall-clock deadline `Date.now() + N*60000`, checked inside the existing
    `updateProgress()` tick — no separate `setInterval`), then "बंद" (off).
    This default (like the rest of the timer state) is intentionally
    **not** persisted to `localStorage`: a timer set today shouldn't silently
    reactivate on a later visit.
- **Download**: every episode row gets a `.dl-btn` (plain `<a download
  href="/audio/...">`, filename = exact on-disk filename via `html.escape`),
  plus one in the now-playing overlay (`np-download`) that JS points at
  whatever's currently loaded. Two things had to be fixed for this to work
  since the site does SPA-style client-side navigation: (1) the document-level
  click interceptor that turns internal `<a>` clicks into `fetch()`-based
  partial navigation now explicitly skips any link with a `download`
  attribute, otherwise it would `fetch()` the audio file as if it were an
  HTML fragment; (2) the episode row's own click-to-play handler checks
  `e.target.closest('.dl-btn')` and bails, so tapping the download icon
  doesn't also start playback (same pattern already used for the mini-bar's
  play button).
- **Favicon + Open Graph tags**: reuses `static/mauli.jpg` directly as both
  `<link rel="icon">` and `apple-touch-icon` (modern browsers accept JPEG
  favicons fine, no image conversion tooling needed/available). OG
  title/description/image are rendered in `page_shell()`; the image and
  `og:url`-equivalent base URL are derived per-request from the incoming
  `Host` header (`serve_page` in `AudioHandler`) rather than hardcoded, so it
  stays correct even though the quick-tunnel hostname changes.

## Bulk ZIP download (added 2026-08-11)

Every book page (`/book/<id>`) and chapter page (`/book/<id>/<slug>`) now has
a `.download-all-btn` pill (`page-actions` div, right under the title) that
downloads the whole book or the whole chapter/verse as a single `.zip` —
`/download/book/<id>` and `/download/book/<id>/<slug>` in `do_GET`. Like the
per-episode `.dl-btn`, the link carries a `download` attribute so the
SPA's document-level click interceptor treats it as a real navigation
instead of `fetch()`-ing it as an HTML partial.

Implementation lives in `AudioHandler.serve_zip()` plus
`build_book_zip_items()`/`build_chapter_zip_items()` (resolve book/chapter
into a `(display_name, [(arcname, filepath), ...])` list, mirroring the
key/label resolution already done in `render_book`/`render_chapter`). Two
things make this safe for a book that can be several GB (443 files / ~17GB
total across both books):
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

## Now-playing icon bug fix (2026-08-11)

`onEnded()` (the `<audio>` `ended` listener) previously relied entirely on
the browser also firing a `pause` event before `ended` (per spec it should,
and usually does) to flip the mini-bar/overlay icon back to play and reset
`navigator.mediaSession.playbackState`. Reported symptom: after minimizing
the now-playing overlay and navigating elsewhere in the SPA while the
current track played out to the end, the pause icon stayed showing instead
of reverting to play. `onEnded()` now explicitly calls
`this.updatePlayIcon(false)` and resets `this.audio.currentTime = 0` itself
at the top, rather than depending on that implicit `pause` event — belt and
suspenders, and it also means tapping play again after natural end-of-track
restarts the same episode from the beginning instead of doing nothing
(currentTime was previously left sitting at `duration`). When `onEnded()`
does go on to call `playNext()`, the explicit reset is harmless/moot since
`play()` immediately assigns a new `src` for the next track anyway.

## Card-based home page (added 2026-08-11)

The home page (`/`) is now three stacked full-panel "card" sections instead
of one continuous page, built by `render_home()` calling three helpers —
`render_home_main()` (unchanged hero + book grid + podcast footer, now just
additionally wrapped in a `.section-card` panel for visual consistency with
the two new sections below it), `render_home_youtube()`, and
`render_home_about()` — each wrapped in `<section class="home-section">`,
all inside one `<div class="home-scroll">`. CSS (`scroll-snap-type: y
proximity` on `.home-scroll`, `scroll-snap-align: start` on `.home-section`)
gives a gentle snap-to-section feel while scrolling without trapping the
user the way `mandatory` snapping can on variable-height content (chosen
deliberately over `mandatory` for that reason); disabled entirely under
`prefers-reduced-motion: reduce`, consistent with the rest of the site's
motion-reduction handling.

- **YouTube section**: channel link (`YOUTUBE_CHANNEL_URL`/
  `YOUTUBE_CHANNEL_HANDLE` constants — handle is `@अमृतकण`) plus two embedded
  videos (`YOUTUBE_VIDEO_IDS`) via `youtube-nocookie.com/embed/<id>` iframes
  (privacy-enhanced mode, no tracking cookies until playback starts),
  `loading="lazy"` so they don't eagerly load until scrolled near. Icon path
  + brand red (`#FF0000`) sourced from simple-icons, same convention as
  `PODCAST_LINKS`.
- **About section**: `ABOUT_TEXT_MR` is a placeholder Marathi translation of
  copy the user gave in English — content is explicitly not final (user said
  it's "still being decided"), so expect this to be replaced wholesale
  later; don't build anything else on top of this text being stable.
  - **"माझ्याबद्दल" subsection** (added 2026-08-11): sits at the bottom of
    this same card, below a divider (`.about-me`) — a photo of Dr Suresh
    Kumar Chaudhari (`static/sk_chaudhari.jpg`, downloaded from an ITU
    profile page the user linked, not hotlinked) on the left and an
    intentionally **empty** `.about-me-text` div on the right
    (`.about-me-row`, flex; stacks to photo-above-text on mobile via the
    existing `@media (max-width: 600px)` block). The user explicitly asked
    for the text to stay blank for now — don't fill it with placeholder
    copy, that's content to be written later.
- Both new sections reuse the `.section-card`/`.section-title`/
  `.section-lead` classes, generic enough to be reused for further home
  sections if more get added later.
- Not visually verified in a real browser this session (no browser
  automation tool connected) — checked by inspecting the rendered HTML
  structure (balanced tags, correct section/card nesting, right video IDs
  and Marathi text present) and confirming both `localhost:8080` and
  `https://amrutkan.org` return it. Worth an actual look in a browser to
  confirm the snap-scroll feel and iframe sizing look right, especially on
  mobile.

## Motion polish + loading skeleton (added 2026-08-10)

- **Sheet transitions**: the now-playing overlay, mini-bar, and the three
  bottom-sheet popups (गती/टायमर/मदत) all share one easing token,
  `--ease-sheet: cubic-bezier(0.32, 0.72, 0, 1)` (iOS-style decelerate), set
  once in `:root`.
- **Loading skeleton on SPA navigation**: `navigateTo()` now shows a
  placeholder while the `fetch()` for the next page is in flight, instead of
  leaving the old page visible with no feedback until data arrives —
  folded-hands **ASCII art** (not emoji — deliberately, since this is a
  religious site) inside a rotating ring (`.skeleton-ring::before`, a halo-like
  CSS spinner), plus "हरी ॐ" and "थोडा वेळ थांबा…" beneath it. The first
  version of the hands (just a tapering diamond, no finger strokes) read as a
  heart rather than praying hands per user feedback (2026-08-10) — fixed by
  prepending a `||  ||` "fingers" row above the taper (`SKELETON_HANDS_RAW`),
  since shape alone was too ambiguous at ASCII-art resolution without some
  cue that specifically reads as fingers rather than a generic curve. The
  ASCII art is authored once as a raw Python string, then run through
  `json.dumps()` and spliced into `GLOBAL_SCRIPT` via a
  `__SKELETON_HANDS_JSON__` placeholder + `.replace()` — deliberately
  avoiding hand-escaping backslashes through two string layers (Python source
  → JS source), which is exactly the kind of thing that's easy to get subtly
  wrong. `navigateTo()` also gained a `try/catch` around the `fetch()` (falls
  back to a full `location.href` navigation) — without it, a network failure
  mid-navigation would leave the skeleton stuck on screen forever with no
  recovery, which defeats the point of adding it on a site whose whole
  context is flaky connections.
- **Staggered entrance** for `.book-card`/`.tile`/`li.track` grids: these
  start at `opacity: 0` in CSS, and only become visible when JS
  (`applyStagger()`, called at the end of `bindContent()`) sets a per-item
  `animation-delay` (capped at index 10 so long episode lists don't take
  forever to finish revealing) and adds a `.stagger-in` class that triggers
  the actual keyframe animation. This ordering is deliberate, not
  cosmetic — if the CSS `animation` were applied directly on the base
  selector instead, it would start playing (with a uniform zero delay, i.e.
  no stagger at all) as soon as the browser parses the elements, which for
  the very first page load happens before `bindContent()`'s JS has a chance
  to run and set the per-item delays. `bindContent()` runs on both the first
  page load (via `APP.init()` on `DOMContentLoaded`) and every SPA
  navigation, so the stagger works consistently in both cases.
- `prefers-reduced-motion: reduce` disables all of the above (including
  forcing the grid items back to `opacity: 1` so reduced-motion users don't
  end up with permanently invisible content).

## Access log

`log_message` on `AudioHandler` used to be a no-op. It now writes to
`~/audio-site/access.log` via a `logging.handlers.RotatingFileHandler`
(5MB × 3 backups, stdlib only) — one line per HTTP request/error, format
`<ip> [<date>] "<request line>" <status> -`. Added specifically because the
2026-08-10 audio-quality investigation had to lean entirely on `cloudflared`'s
tunnel-level logs; this gives an app-level record too. `tail -f
~/audio-site/access.log` to watch live traffic.

## Health check

`~/audio-site/healthcheck.sh`, run every 5 minutes by
`audio-site-healthcheck.timer` (systemd user timer, `OnBootSec=2min
OnUnitActiveSec=5min Persistent=true`). Each run: curls `localhost:8080`
(is `app.py` up), reads the current tunnel URL out of
`journalctl --user -u audio-site-tunnel.service` and curls *that* (is the
whole path — app + tunnel + Cloudflare edge — actually reachable), with one
retry after 5s to avoid flagging sub-5-second blips. State (`healthy`/
`unhealthy`) is tracked in `~/audio-site/.healthcheck_state`; a **transition**
(not every check) triggers a `notify-send` desktop notification — critical
urgency + reason when it goes down, a plain notification with the current URL
when it recovers. First-ever run never notifies (nothing to "recover" from).
Notification delivery depends on the user being logged into the graphical
Wayland session on this machine (confirmed present and working when this was
set up) — there's no email/push fallback, so if the laptop is logged out this
degrades to log-only (`~/audio-site/healthcheck.log`). Tested end-to-end by
stopping `audio-site.service` and confirming both the down and back-up
notifications fired correctly.

## Known constraints for whoever continues this

- **No pip/venv available** in this environment: `python3-pip` and `python3-venv`
  aren't installed, and `sudo` requires interactive auth that isn't available in
  this session (no passwordless sudo). This is why `app.py` deliberately avoids
  Flask/any third-party package — stick to stdlib unless the user installs pip
  themselves (`sudo apt install python3-pip python3-venv`, which they'd need to
  run themselves via `!` in a Claude Code session, or the environment changes).
  `python3-mutagen` is an exception — the user installed it via `sudo
  apt` (2026-08-11, interactively, see below) for one-off audio-tag editing,
  so it's actually importable now. That's still an apt package, not pip —
  general third-party dependencies for `app.py` itself remain off the table
  under this constraint.
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
  real iPhone/Android — implemented 2026-08-10 but never visually verified
  (no browser tooling available in that session).

- ~~Systemd user services for `app.py` and `cloudflared` so both survive reboots.~~
  Done 2026-08-10, see "Running it" above.
- ~~Switch to a named Cloudflare Tunnel + purchased domain.~~ Done 2026-08-11
  — site is now on `https://amrutkan.org` via a named tunnel, see "The
  cloudflared tunnel" above.
- Prefer wired ethernet (`enp1s0f0`) over WiFi for this machine if practical —
  WiFi disconnect/reassociate events have been observed to kill the tunnel
  mid-stream (see 2026-08-10 investigation above).
- `python3 app.py` currently rescans the folder only at startup — if the user
  adds new episodes, the process needs restarting to pick them up
  (`systemctl --user restart audio-site.service`).
