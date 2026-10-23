# Handoff — Rollingwood Report

For **Ronald Hasso**, operator since October 2026. The Rollingwood Report
was created by Jeff Marx and handed off to Ronald Hasso in October 2026.

To get set up, open Claude Code in a Terminal and say:

> set me up using HANDOFF.md

## For Claude Code (read this first)

You are setting this up for Ronald on his Mac. He has used Terminal once
or twice, is new to Claude Code, and has no GitHub account yet. Work
through **One-time setup** in order, one step at a time, and run each
**Check** before moving on. Explain each step in a sentence before you
run it.

- Steps marked **Ronald does this** need him (a browser sign-up, a
  password, typing a key). Stop, tell him exactly what to do, and wait.
- **Never ask Ronald to paste an API key into this chat.** He types keys
  into `.env` himself (step 9).
- **Never put API keys in `~/.zshrc`, `~/.zprofile`, or any shell
  startup file**, and never `export ANTHROPIC_API_KEY` in his shell. If
  `ANTHROPIC_API_KEY` is set in the shell, Claude Code bills that API key
  instead of Ronald's Claude plan. The keys belong only in the repo's
  `.env`, which the scripts load themselves and git ignores.
- Never `git push` unless Ronald explicitly says to, and only after the
  First-day TODOs are done. Also follow `CLAUDE.md` and
  `SESSION_HYGIENE.md` in the repo.

## What this is and what it produces

The pipeline takes a Rollingwood meeting recording from YouTube,
transcribes it (AssemblyAI), and summarizes it (Claude) into a neutral,
newsletter-style report. You get one **PDF per meeting**. Every claim in
it links to the exact moment in the YouTube recording, so a reader can
check it.

Cost per meeting: about **$0.30 in Anthropic API usage** (the 10/19/2026
RCDC run was $0.29), plus **AssemblyAI** transcription, billed by audio
length (the AssemblyAI dashboard shows the exact charge). These are
API accounts, separate from a Claude plan.

## One-time setup

The repo goes in `~/rollingwood-report`. Meeting audio and reports go in
`~/Documents/rollingwood-report-outputs/` — never inside the repo.

**1. Homebrew** (Mac package manager). Skip if `brew --version` works.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Ronald does this:** it asks for his Mac password (nothing shows while
typing — that's normal). At the end it prints "Next steps" with two
commands to add Homebrew to the PATH; run them. On Apple Silicon they
are:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

Check: `brew --version`

**2. Tools**

```bash
brew install python@3.14 ffmpeg pango deno ocrmypdf tesseract
```

What each is for: `python@3.14` runs the scripts; `ffmpeg` handles
audio; `pango` is needed by WeasyPrint to make the PDF; `deno` is the
JavaScript runtime yt-dlp needs for YouTube; `ocrmypdf` + `tesseract`
read agenda PDFs that are scanned images.

Check: `python3.14 --version && ffmpeg -version | head -1 && ocrmypdf --version && deno --version | head -1`

**3. Get the code.** Ronald needs no GitHub account for this.

- If Jeff has pushed the handoff commits to GitHub (this file is on
  <https://github.com/jeffm031/rollingwood-report>):

  ```bash
  git clone https://github.com/jeffm031/rollingwood-report.git ~/rollingwood-report
  ```

- If not yet (the handoff is held locally until Ronald reviews it), Jeff
  sends a file `rollingwood-report.bundle` (made with
  `git bundle create rollingwood-report.bundle main`). Save it to
  Downloads, then:

  ```bash
  git clone ~/Downloads/rollingwood-report.bundle ~/rollingwood-report
  git -C ~/rollingwood-report remote set-url origin https://github.com/jeffm031/rollingwood-report.git
  ```

If macOS offers to install "command line developer tools" for `git`,
accept and re-run.

Check: `ls ~/rollingwood-report/HANDOFF.md`

**4. Python environment and packages**

```bash
cd ~/rollingwood-report
/opt/homebrew/bin/python3.14 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -U "yt-dlp[default]"
```

(On an Intel Mac, use `/usr/local/bin/python3.14`.) The last line
upgrades yt-dlp; YouTube changes often, and an old yt-dlp fails with
"HTTP Error 403: Forbidden".

Check: `.venv/bin/python tests/test_roster.py` prints `ok`, and
`.venv/bin/yt-dlp --version` prints a version.

**5. AssemblyAI account — Ronald does this.** Sign up at
<https://www.assemblyai.com>, add a payment method if asked, and copy
the API key from the dashboard. Keep it in the browser for step 7.

**6. Anthropic API account — Ronald does this.** At
<https://console.anthropic.com>, sign up, add credits under Billing,
and create a key under API Keys (it starts `sk-ant-`). This is separate
from his Claude plan and pays only for the summaries.

**7. `.env` with both keys — Ronald does this.**

```bash
cd ~/rollingwood-report
touch .env
open -e .env
```

TextEdit opens. Ronald types these two lines with his real keys, then
saves and closes:

```
ASSEMBLYAI_API_KEY=paste-assemblyai-key-here
ANTHROPIC_API_KEY=paste-anthropic-key-here
```

Check (shows only names, not the keys): `cut -d= -f1 .env` prints
both names; `git check-ignore .env` prints `.env`.

**8. Outputs folder**

```bash
mkdir -p ~/Documents/rollingwood-report-outputs
```

## Per-meeting runbook

**1. Find the meeting.** Open the meetings archive:
<https://legacyrollingwoodtx.teammunicode.com/meetings> (also embedded
on rollingwoodtx.gov → City Meetings). Each row has an agenda link, a
packet link, and **View Details**. The details page links the YouTube
recording; the video ID is the part after `watch?v=` or `/live/` (for
example `R8jOSrsFzkY`).

**2. Copy the plain agenda link** — the one whose URL contains
`MEET-Agenda-…pdf`. **Never use the packet (`MEET-Packet-…pdf`).**
Packets embed earlier meetings' draft minutes, which put people and
discussion from *other* meetings into the report. They are also huge and
often scanned. The agenda gives the item titles and numbering without
that contamination.

**3. Download audio only**, keeping the video ID in square brackets in
the filename — that is how the report's timestamp links find the video.
Put the body and date in the name too (M-D-YYYY); the PDF title uses it.

```bash
cd ~/Documents/rollingwood-report-outputs
~/rollingwood-report/.venv/bin/yt-dlp -f 'bestaudio[ext=m4a]/bestaudio' \
  -o 'RCDC Meeting 10-19-2026 [%(id)s].%(ext)s' \
  'https://www.youtube.com/watch?v=R8jOSrsFzkY'
```

If it fails with a 403, upgrade yt-dlp:
`~/rollingwood-report/.venv/bin/pip install -U "yt-dlp[default]"`.

**4. Run the report.** Always put the audio path in double quotes — the
square brackets break it otherwise.

```bash
cd ~/rollingwood-report
.venv/bin/python scripts/test_local.py \
  "$HOME/Documents/rollingwood-report-outputs/RCDC Meeting 10-19-2026 [R8jOSrsFzkY].m4a" \
  --packet "https://mccmeetings.blob.core.usgovcloudapi.net/rollwdtx-pubu/MEET-Agenda-f87cbbd2886e4089b767f401e9e14f1f.pdf"
```

It takes a few minutes. Three files land next to the audio:

- `….m4a.transcript.txt` — the transcript. Kept as a cache: re-running
  the same audio does not charge AssemblyAI again (it does charge
  Anthropic again).
- `….m4a.summary.md` — the report text.
- `….m4a.summary.pdf` — **the PDF to share.**

If it ends with "TRUNCATED" (exit code 3), no PDF was made; run it
again.

**5. Fixing a mistake by hand.** Edit the `.summary.md` (for example
`open -e` it), then rebuild the PDF without re-running Claude:

```bash
cd ~/rollingwood-report
.venv/bin/python -c 'import sys; sys.path.insert(0,"scripts"); from pathlib import Path; from pdf_export import derive_meeting_date, export_to_pdf, extract_meeting_type; a=Path(sys.argv[1]); md=Path(str(a)+".summary.md"); s=md.read_text(); export_to_pdf(s, md.with_suffix(".pdf"), extract_meeting_type(s), derive_meeting_date(a.name, fallback="")); print("PDF:", md.with_suffix(".pdf"))' \
  "$HOME/Documents/rollingwood-report-outputs/RCDC Meeting 10-19-2026 [R8jOSrsFzkY].m4a"
```

**6. Share** the `.summary.pdf` on WhatsApp (drag it into the chat) —
after the review checklist.

## Review checklist before posting (5 minutes)

1. **Spot-check 3 timestamp links.** Click three, ideally the votes. The
   video should land on what the sentence says. Links are sometimes
   ~10 seconds early; that's tolerable, a different topic is not.
2. **Scan for dates and years.** The model has written "spring 2026"
   when the speaker meant next spring (2027). Check every year and every
   "next month / next year" against the meeting date.
3. **Scan for resident home addresses.** There should be none. City
   Hall (403 Nixon Drive) in meeting logistics is fine; a resident's
   street number is not — change it to the street name only.
4. **Read "Names to verify"** at the end of the Appendix. Check each
   name against the recording. If it's absent, still glance at names in
   votes and public comments, and at any "not named on the record"
   notes. Confirmed spellings go into
   `prompts/roster/tier4_learned.yml` (see `CLAUDE.md`).

## Ground rules

- **The recording is the source of truth.** The report is a convenience
  summary. If it disagrees with the video, the video wins — fix the
  report.
- **No resident home addresses, ever.** Block or street level only
  ("a residence on Pickwick Lane").
- **Neutral framing.** Describe what was said and decided. No opinions,
  no winners and losers, no predictions.

## Upkeep

- **Officials roster (Tier 1):** monthly, and after any council or
  commission appointment.

  ```bash
  cd ~/rollingwood-report
  .venv/bin/python scripts/scrape_tier1.py            # preview only
  .venv/bin/python scripts/scrape_tier1.py --write    # update the roster
  git diff --stat prompts/roster/
  ```

- **Past speakers (Tier 2):** when new minutes are posted. About 6
  minutes; free.

  ```bash
  .venv/bin/python scripts/scrape_tier2.py --write
  ```

- After either, run `.venv/bin/python tests/test_roster.py`, then commit
  the roster changes (Claude Code can do this for you).

## First-day TODOs for Ronald

1. Confirm your name and email in `README.md` ("Operator & contact") and
   `methodology.md` (top, and "How to contact and submit corrections").
2. Complete your operator disclosures in `config/disclosures.yml` and the
   `STANDING_DISCLOSURE` block of `methodology.md`. Nothing has been
   written on your behalf. Also review the first-person commitments in
   `methodology.md` and adopt or revise them, then remove the TODO
   notes.
3. Then push. That needs a GitHub account and write access: create an
   account at <https://github.com>, ask Jeff to add you as a
   collaborator on `jeffm031/rollingwood-report`, then:

   ```bash
   brew install gh
   gh auth login
   cd ~/rollingwood-report && git push
   ```

   Or ask Jeff to push for you once you've confirmed.

## What you can ignore

- `scripts/run.py` — the automated daily-email version. Not needed to
  make PDFs. (README and methodology describe it running in GitHub
  Actions, but no workflow file exists in this repo today.)
- Gmail / Google OAuth (`bootstrap_google_auth*.py`, `send_preview.py`,
  `GOOGLE_CREDS_JSON`) — only for `run.py` and email sending.
- The subscribers repo.

## Known issues

See "Known issues for Ronald" in
[`sessions/2026-10-23_session.md`](sessions/2026-10-23_session.md).
