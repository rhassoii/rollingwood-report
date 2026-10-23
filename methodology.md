# Methodology

The Rollingwood Report is an automated pipeline that produces
structured email briefings after each meeting of Rollingwood, Texas
municipal bodies.

**Operator:** Ronald Hasso.

The Rollingwood Report was created by Jeff Marx and handed off to Ronald
Hasso in October 2026.

> **TODO (Ronald Hasso):** This document is written in the first person.
> That voice predates the handoff — the commitments below were written
> by the Report's creator. Review them and adopt or revise them in your
> own voice, then remove this note.

This document explains what the Report is, how the pipeline works, what
accountability structures back it, what the operator discloses, and
what known limitations readers should weigh.

## What the Report is

The Rollingwood Report is automated coverage of municipal meetings.
After a meeting is posted to the City of Rollingwood's YouTube channel,
the pipeline transcribes it, summarizes it in a structured format, and
emails the result. Each issue is a structured summary with YouTube-
timestamped citations back to the source recording for every
attributed claim. The specific structure — what sections appear, what
they contain, how they're ordered — is defined by the public prompt
at `prompts/summary_prompt.md` and iterates based on operator tuning
and reader feedback. The prompt is versioned in the repo; any issue's
structure is exactly what that version of the prompt produced.

The Report does not editorialize, endorse, predict political outcomes,
or identify "winners" and "losers." It describes what was said and
decided. This is a deliberate constraint encoded in the summarization
prompt.

## How the pipeline works

The pipeline is run by the operator for each meeting. (An automated
daily GitHub Actions version exists in `scripts/run.py` but is not
currently deployed.) Each stage is automated:

1. **Check for new meetings.** Watch the Rollingwood YouTube channel for
   newly posted videos matching municipal-meeting keywords.
2. **Download audio.** Use `yt-dlp` to pull an MP3 of any new meeting.
3. **Transcribe.** AssemblyAI's `universal-3-pro` model produces a
   speaker-diarized transcript.
4. **Summarize.** Claude Opus 4.7 generates the structured summary using
   a locked prompt at `prompts/summary_prompt.md` and a roster of
   canonical Rollingwood names.
5. **Deliver.** The summary is archived to Google Drive (markdown +
   PDF), and an email is sent to readers.

There is no human editorial review between transcription and delivery.
I operate the pipeline — I decide which meetings count as in-scope,
when to run it manually for a missed meeting, and what gets changed in
the prompt — but no issue is reviewed by a human before it reaches a
reader's inbox.

Pipeline source is at <https://github.com/jeffm031/rollingwood-report>.
The prompt, roster, and configuration are public.

## Accountability model

I use four structures to reduce the error rate and to make errors
catchable after the fact. Two are operational today; two are commitments
for the Report's first beta edition.

### Operational today

**The tuned prompt.** `prompts/summary_prompt.md` encodes the register
(neutral newsletter voice, third person), the required structure (nine
numbered sections plus an Appendix), and specific rules about citation
accuracy, canonical-name rendering, and what belongs in the "Names to
verify" appendix. The prompt is iteratively tuned against known failure
modes. Prompt tuning is ongoing work; open failure modes are tracked
publicly in `NOTES.md` under "Prompt-tuning followup" in this repo.

**The four-tier name roster.** Speech-to-text misrenders names,
especially for speakers who don't appear often. A roster of canonical
names reduces that. The roster has four tiers: current officials
scraped from the City directory (Tier 1, extended to adjacent bodies
like West Lake Hills via TML city directories), historical public
speakers from meeting packets since April 2024 (Tier 2), property
owners in Rollingwood from Travis County appraisal data (Tier 3,
likely residents), and names confirmed through reader corrections and
review of past summaries (Tier 4). The roster is cross-referenced by
the pipeline during summarization; transcript misspellings are resolved to canonical
spellings where a match is found. The roster catches many phonetic
errors but not all — see "Known limitations" below.

**Reader corrections.** Readers send corrections to
<rhassoii@gmail.com> or <jeffm031@gmail.com>. The operator checks each
one against the meeting recording, with Claude Code's help. Confirmed
name fixes are added to the roster (Tier 4) so the same error doesn't
recur. This is a manual process; there is no automated correction
pipeline.

### Committed for the Report's first beta edition

**Quarterly full-recording audit.** Each quarter I will select one
published issue, watch the source meeting recording end to end, and
publish an audit comparing the recording's content to the issue's
coverage. Discrepancies — factual errors, attribution errors, timestamp
errors, editorial drift — will be documented and published with any
follow-up corrections. Sample size is one issue per quarter; this is
not comprehensive coverage. It is a sampled spot-check, and I'll say so
in each audit. **Not yet operational.** It is a commitment for the first
beta edition.

## Operator commitments

A few commitments I'm making and intend to keep:

- **Correction priority.** When I become aware of an error — from a
  reader, from the quarterly audit, or from my own re-reading — I check
  it against the recording promptly. Confirmed name fixes go into the
  roster so they don't recur.
- **Public tooling.** The pipeline source, prompt, roster, and
  configuration stay in a public repository. The mechanics are open
  for review.
- **Constrained scope.** The Report covers Rollingwood municipal
  meetings. It doesn't speculate about political races, campaign
  dynamics, or regional politics beyond what appeared on the agenda.
- **Operator disclosures.** See "Operator and disclosures" below.
- **Resident addresses.** The Report does not publish residents' home
  addresses. Home addresses are never stored in the name roster and
  are never drawn from meeting packets or agendas. Where an agenda
  item concerns a specific property, the Report identifies it at the
  block or street level (e.g., "a residence on Pickwick Lane")
  without the street number. This is enforced by the summarization
  prompt and checked in the quarterly audit.

## Operator and disclosures

The Rollingwood Report was created by Jeff Marx and handed off to Ronald
Hasso in October 2026. Ronald Hasso is the current operator.

**Operator disclosures** — civic applications, appointments, and
affiliations that touch municipal matters — are tracked in
`config/disclosures.yml` in this repo. Rendering that file into each
issue is planned but not yet implemented.

<!-- STANDING_DISCLOSURE_START -->
Ronald Hasso is a former member of the Rollingwood Utility Commission and the Comprehensive Plan Strike Force (inactive).
<!-- STANDING_DISCLOSURE_END -->

<!-- Implementation note for render_disclosures() in scripts/run.py
     (or wherever it lives): extract the paragraph content between
     STANDING_DISCLOSURE_START and STANDING_DISCLOSURE_END. Strip the
     HTML comment markers themselves from the extracted text before
     rendering — otherwise they appear as literal <!-- ... --> strings
     in generated issues. Fail-loud if the anchor pair isn't found;
     see config/disclosures.yml for the broader fail-loud contract. -->

## Known limitations

Some specific things the Report does poorly or not at all. I'd rather
name these than gesture vaguely at "AI can make mistakes":

- **Speech-to-text produces phonetic name errors.** AssemblyAI's model
  misrenders names of speakers who don't appear in the roster
  (first-time public commenters) or whose names have unusual
  spellings. The roster resolves many — but not all — of these at
  summarization time. Ambiguous cases are flagged in each issue's
  "Names to verify" appendix.

- **The timestamp-citation rule has known open failure modes.** The
  Report cites YouTube timestamps for every attributed claim, which is
  load-bearing for readers who want to verify in the recording. The
  citation rule doesn't always bind correctly. Current-state specifics
  and in-progress diagnostic work live in `NOTES.md` under
  "Prompt-tuning followup."

- **No human pre-publication review.** Any error — factual,
  attributional, editorial drift — reaches readers before a reader
  correction catches it. Reader corrections are a post-hoc mechanism,
  not a pre-publication safeguard.

- **The quarterly audit is a sample, not comprehensive coverage.** One
  issue per quarter will be compared end to end against the source
  recording. Most issues won't be audited at that depth. If you notice
  something that looks wrong in any issue, please submit a correction
  — don't wait for the next audit.

- **The meeting recording is the authoritative source.** The Report is
  a derivative product, as are the City's official minutes. If an
  issue's coverage conflicts with what the recording shows, the
  recording is what happened. The Report is a convenience for readers
  who don't have two hours per meeting to watch.

## How to contact and submit corrections

Send corrections and questions to <rhassoii@gmail.com> or
<jeffm031@gmail.com>. The operator checks each correction against the
meeting recording, with Claude Code's help. For corrections that
identify a name, the confirmed spelling is added to the roster (Tier 4,
learned names) so the same error doesn't recur.
