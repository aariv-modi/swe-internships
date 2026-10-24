# Apply assistant (review queue with pre-filled forms)

A local tool that turns the list into a daily queue ranked by fit with you, opens each application
in a real browser window with everything it can answer already filled in, and then hands over.
**You review and press Submit yourself.** It never submits, never creates accounts or handles
passwords, never solves CAPTCHAs, and never answers certifications, consents or signatures.

Your profile and history live in `~/.swe-internships/`, outside this repo, so nothing personal can
end up in the public list.

## Setup (once)

```bash
pip install -r requirements-apply.txt
python -m apply init          # creates ~/.swe-internships/profile.toml
```

Fill in `profile.toml` (contact details, resume path, school, work authorization, preferences).
Playwright drives your installed Google Chrome, so no extra browser download is needed. Sign-ins
(e.g. Workday) are kept in `~/.swe-internships/browser_state.json` between runs.

Optional: install the Claude Code CLI (`npm install -g @anthropic-ai/claude-code`, then run
`claude` once to sign in with your subscription) to get drafts for long-answer questions.

## Jobright Autofill

Install [Jobright Autofill](https://chromewebstore.google.com/detail/jobright-autofill-%E2%80%93-insta/odcnpipkhjegpefkfplmedhmkmmhmoko)
in your everyday Chrome and sign in to Jobright once. Then choose in `profile.toml`:

```toml
[browser]
mode = "hybrid"        # this tool pre-fills Greenhouse/Lever/Ashby; everything else goes to Jobright
# mode = "jobright"    # every posting goes to Jobright
chrome_profile = ""    # e.g. "Profile 1" if Jobright is installed in a non-default Chrome profile
```

Why not run Jobright inside this tool's window: that window is a clean, automated Chrome with
extensions disabled, and Chrome 137+ no longer lets automation load extensions into branded Chrome.
So postings for Jobright open as a normal tab in your own Chrome; the queue and outcome tracking
work the same. Before handing a Greenhouse/Lever/Ashby posting to Jobright, the tool checks the page
for "no tool or AI-completed applications" clauses and warns you (Workday pages can't be checked;
they're behind a sign-in). Jobright's own AI answers are subject to the same employer rules.

## Daily use

```bash
python -m apply queue         # ranked open postings you haven't handled
python -m apply open 3        # open #3, pre-fill it, review and submit in the browser
python -m apply mark 5 skipped
```

After `open`, the terminal lists what was filled, what was drafted, and what's yours to answer.
When you're done in the browser, answer `a` (applied), `s` (skipped) or Enter (later).

## What gets filled

| System | Share of the list | Pre-fill |
|---|---|---|
| Greenhouse, Lever, Ashby | ~30% (382 of 1,347 Summer 2027 postings) | contact, links, location, school, graduation date, sponsorship/authorization (simple questions only), demographic questions per your profile, resume upload |
| Workday, iCIMS, Oracle, others | ~70% | opens in your regular Chrome, where Jobright Autofill fills it (default `hybrid` mode) |

Measured on live forms (2026-10-23, fake profile, nothing submitted): Greenhouse (Vercel) 13 fields,
Lever (Acron Aviation) 11, Ashby (1Password) 13, each confirmed by reading the page back.

Deliberately left to you, because a wrong answer is worse than none:

- certifications, consents, privacy acknowledgements, signatures (e.g. Lever's disability-form signature);
- compound questions whose meaning flips with wording ("authorized to work *without sponsorship*?",
  "do you live in *and* are you authorized in the listed countries?");
- job-specific questions (commute, pay expectations, graduation windows, export control, referrals);
- long answers (drafted when the Claude CLI is installed; always edit before submitting).

## Employers that forbid tool or AI help

Some applications require certifying the form was not completed by another person or an AI tool
(Advanced Space: "not filled out, in whole or in part, by another person or by an artificial
intelligence (AI) tool on my behalf"). On such pages the assistant fills **nothing** and tells you
to complete it yourself. In a survey of 159 Greenhouse companies on 2026-10-22, 1 had such a clause;
2 more (Samsara, KnowBe4) forbid AI during interviews. Lever's AI wording on every form is the
employer's own notice that *it* may use AI, not a rule for applicants.
