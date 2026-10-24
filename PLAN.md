# Build plan

Goal: the most complete, fastest-updating list of **US software-engineering internships (all seasons)**,
published as a GitHub-style README, with completeness measured on every run rather than claimed.

## Evidence this plan rests on (measured 2026-10-22)

- 17,224 Simplify listings by ATS: Workday 48.8%, Greenhouse 9.0%, iCIMS 6.4%, Oracle Cloud 5.5%,
  Ashby 4.5%, SmartRecruiters 3.4%, SuccessFactors 3.0%, Lever 2.8%, custom company sites ~6-10%.
- Direct scrape of the 1,030 Greenhouse/Lever/Ashby boards Simplify already links: ~34 genuine US SWE
  internships (~10%) missing from Simplify + vanshb03 combined.
- Simplify lists postings a median 3.7 h after the ATS publishes them (p75 7.3 h).
- Greenhouse and Lever application APIs require the *employer's* secret key, so applying can't go
  through an API; it has to be browser form filling.

## Milestones

1. **Core scraper (this milestone)**
   - Company registry discovered from community lists (Simplify, vanshb03, any README of links).
   - Connectors: Workday, Greenhouse, Lever, Ashby.
   - Classifier: internship + SWE + US, term extraction. Rules only, no paid services.
   - Listing state (first seen / last seen / closed), README rendering, recall scorecard vs Simplify.
   - GitHub Actions schedule (free on public repos).
2. **Coverage**
   - Done: iCIMS (*.icims.com), Oracle Cloud, SmartRecruiters, SuccessFactors (sitemap), JazzHR
     (XML feed), TikTok (search API; needs the `website-path: tiktok` header).
   - Next: iCIMS custom domains (60 of 125 iCIMS misses), ByteDance (SSL chain fails locally),
     Tesla, Waymo, Eightfold, Rippling, Jobvite, Workable; hand-written scrapers for Google, Meta,
     Apple, Microsoft, Amazon; schema.org `JobPosting` fallback (scraper/jsonld.py) for the rest.
3. **Discovery** — measured 2026-10-22, see "Audits" below.
   - Done: Common Crawl sweep (scraper/discovery.py, monthly workflow) promotes boards that have a
     US SWE internship into the registry.
   - Open: Workday boards can't be guessed from a company name (unknown and real tenants return
     identical responses), so name lists (S&P 500, LCA filers) only help for Greenhouse/Lever/Ashby.
4. **Review queue (apply assistant)** — built 2026-10-23 (apply/, APPLY.md); deliberately *not* fully automatic:
   - Profile + answer library (work authorization, sponsorship, start dates, links, EEO choices).
   - Match new postings against the profile; daily digest ranked by fit.
   - For Greenhouse / Lever / Ashby: open the form pre-filled (resume attached, standard answers,
     drafted short answers) and **stop before Submit**; the user reviews and submits.
   - For Workday: pre-fill only after the user signs in themselves. (Not built yet: Workday pages
     go to the user's regular Chrome for Jobright Autofill, `[browser] mode = "hybrid"`.)
   - Pages forbidding tool/AI-completed applications are detected and left entirely untouched.
   - Never: account creation, password handling, CAPTCHA bypass, unattended submission.
     Why: no applicant API exists, Workday needs one account per company (1,000+), forms
     contain signed attestations, and the classifier's false positives would become real applications.

## Audits (2026-10-22)

**Accuracy.** Hand-labelled a stratified sample of 119 live listings across all ten systems:
95 correct, 8 wrong, 16 ambiguous, i.e. precision 93% (clear errors only) to 80% (ambiguous counted
as wrong). Errors were generic titles passing the description check (chip design, systems
engineering, quant, research). Rules fixed; the 103 unambiguous titles are a regression test
(tests/fixtures/labeled_titles.json). The audit also found 429 duplicate Workday listings (same
requisition on case-variant or regional sites); registry keys are now case-insensitive and the README
de-duplicates on tenant + requisition id.

**Independent discovery.** Common Crawl's URL index lists 14,127 ATS boards; 11,814 were not in the
registry (which Common Crawl in turn covers only 49% of; capture-recapture suggests >= ~29,000 boards
exist). A random 2,000 of the new boards yielded 6 clear US SWE internships no list or registry had
(+3 ambiguous) -> ~35 extrapolated (95% CI ~13-77, wider given clustering), about +2% on the list.
Conclusion: the community lists already point at almost all boards that post SWE internships; the
remaining gain comes from ~1% of boards, hence monthly promotion rather than hourly scraping.
Caveat: the Simplify scorecard is seeded from Simplify's own links, so it measures connector and
classifier quality, not discovery.
