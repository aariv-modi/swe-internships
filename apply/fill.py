"""Pre-fill a Greenhouse, Lever or Ashby application in a visible browser, then hand over.

Rules this module never breaks (agreed scope, see PLAN.md milestone 4):
- it never clicks Submit, never creates accounts, never handles passwords or CAPTCHAs;
- it never answers certifications, consents or "I agree" questions; those are the applicant's;
- on pages that forbid tool- or AI-completed applications it fills nothing at all.
  (2026-10-22 survey: 1 of 159 Greenhouse companies had such a clause; Advanced Space requires
  certifying the form was "not filled out, in whole or in part, by another person or by an
  artificial intelligence (AI) tool".)
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

# Pages whose terms forbid filling the application with a tool or AI.
FORBIDS_TOOLS_RE = re.compile(
    r"(not (been )?(filled out|completed|written)|personally completed)[^.]{0,160}"
    r"(artificial intelligence|\bAI\b|another person|software|automat)|"
    r"do not use any AI tools during any part", re.I)

# Questions the applicant must answer personally, whatever the profile says.
APPLICANT_ONLY_RE = re.compile(
    r"certif|attest|\bi agree\b|\bagree\b|\bi understand\b|acknowledg|consent|by (checking|agreeing|"
    r"submitting|clicking)|privacy (policy|notice|statement)|terms (of|and)|signature|"
    r"are you an? (llm|ai)|export control|itar|former .{0,30}employee|previously (worked|employed)|"
    r"not listed in the previous|^if|if you (responded|selected|answered|chose)|if other|please specify|"
    r"u\.?s\.? person|commut|hourly range|compensation|salary|pay range|how did you hear|"
    r"what brought you|referr|non-?compete|criminal|convicted|background check|drug", re.I)

DECLINE_RE = re.compile(r"decline|prefer not|don.?t wish|do not wish|not to (self[- ])?identify|"
                        r"choose not|rather not|not disclose|i don.?t want|do not want|"
                        r"prefer not to (answer|say)|not to answer", re.I)
AUTH_RE = re.compile(r"authori[sz](ed|ation) to work|work authori[sz]ation|eligible to work|"
                     r"legally (permitted|able|authori[sz]ed)|right to work", re.I)
SPONSOR_RE = re.compile(r"sponsor|visa", re.I)
RESIDENCE_RE = re.compile(r"\b(live|living|reside|located|based) in\b", re.I)

JS_FIELDS = r"""
() => {
  const txt = el => (el ? el.innerText || el.textContent || '' : '').replace(/\s+/g, ' ').trim();
  const labelOf = el => {
    if (el.id) { const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`); if (l && txt(l)) return txt(l); }
    const lb = el.getAttribute('aria-labelledby');
    if (lb) { const t = lb.split(/\s+/).map(i => txt(document.getElementById(i))).join(' ').trim(); if (t) return t; }
    if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
    const entry = el.closest('.ashby-application-form-field-entry');
    if (entry) { const t = entry.querySelector('.ashby-application-form-question-title, label'); if (t) return txt(t); }
    const lever = el.closest('.application-question') || el.closest('.application-field');
    if (lever) { const t = lever.querySelector('.application-label, .text'); if (t && txt(t)) return txt(t); }
    const wrap = el.closest('label'); if (wrap) return txt(wrap);
    const fs = el.closest('fieldset'); if (fs && fs.querySelector('legend')) return txt(fs.querySelector('legend'));
    // Unlabelled widgets (Greenhouse school/degree pickers): the nearest label up the tree.
    let node = el.parentElement;
    for (let k = 0; node && k < 5; k++, node = node.parentElement) {
      const l = node.querySelector('label'); if (l && txt(l)) return txt(l);
    }
    return '';
  };
  const visible = el => !!(el.offsetParent || el.getClientRects().length) || el.type === 'file';
  const out = []; let n = 0; const tag = el => { el.dataset.fillId = String(n); return String(n++); };
  const handled = new Set();

  // Ashby yes/no questions are rendered as a pair of buttons around a hidden checkbox.
  for (const entry of document.querySelectorAll('.ashby-application-form-field-entry')) {
    const btns = [...entry.querySelectorAll('button')].filter(b => /^(yes|no)$/i.test(txt(b)));
    if (btns.length >= 2) {
      entry.querySelectorAll('input').forEach(i => handled.add(i));
      const t = entry.querySelector('.ashby-application-form-question-title, label');
      out.push({id: tag(entry), kind: 'buttons', label: txt(t), options: btns.map(txt), required: !!entry.querySelector('[class*=required]'), empty: true});
    }
  }
  // Radio / checkbox groups, grouped by their question container: Lever shares one name per
  // question, but Ashby gives every checkbox its own name (13 race options = 13 names).
  // closest() with a selector list returns the nearest match of any, which for Lever is each
  // option's own <li>, so question-level containers are tried first.
  const boxOf = e => e.closest('.application-question') || e.closest('.ashby-application-form-field-entry') ||
                     e.closest('fieldset') || e.closest('[class*=question]') || e.closest('li') || e.parentElement;
  const groups = new Map();
  for (const el of document.querySelectorAll('input[type=radio], input[type=checkbox]')) {
    if (handled.has(el)) continue;
    const key = boxOf(el);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(el);
  }
  for (const [box, els] of groups) {
    const e0 = els[0];
    let label = '';
    const legend = box && box.querySelector('legend, .application-label, .ashby-application-form-question-title, label:not(:has(input))');
    if (legend) label = txt(legend);
    const options = els.map(e => { const l = e.closest('label') || (e.id && document.querySelector(`label[for="${CSS.escape(e.id)}"]`)); return txt(l) || e.value; });
    if (!label) label = txt(box).replace(options.join(' '), '').slice(0, 200);
    const gid = 'g' + n++;
    els.forEach((e, k) => { e.dataset.fillId = gid + '-' + k; handled.add(e); });
    out.push({id: gid, kind: els[0].type === 'radio' ? 'radio' : 'checkbox', label, options, name: e0.name || '',
              required: els.some(e => e.required), empty: !els.some(e => e.checked)});
  }
  for (const el of document.querySelectorAll('input, textarea, select')) {
    if (handled.has(el) || el.type === 'hidden' || el.type === 'submit' || el.type === 'button' || !visible(el)) continue;
    if (el.name === 'g-recaptcha-response' || el.closest('.ashby-application-form-autofill-uploader')) continue;
    if (el.type !== 'file' && (el.getAttribute('aria-hidden') === 'true' || getComputedStyle(el).opacity === '0')) continue;
    let kind = el.tagName === 'SELECT' ? 'select' : el.tagName === 'TEXTAREA' ? 'textarea'
             : el.type === 'file' ? 'file' : (el.getAttribute('role') === 'combobox' || el.getAttribute('aria-autocomplete') === 'list') ? 'combobox' : 'text';
    out.push({id: tag(el), kind, label: labelOf(el), type: el.type, name: el.name || el.id || '',
              options: kind === 'select' ? [...el.options].map(o => o.text.trim()).filter(Boolean) : [],
              required: el.required || el.getAttribute('aria-required') === 'true',
              empty: kind === 'select' ? el.selectedIndex <= 0 : !el.value});
  }
  return out;
}
"""


@dataclass
class Report:
    blocked: bool = False
    filled: list = field(default_factory=list)     # (label, value)
    for_you: list = field(default_factory=list)    # labels the applicant must answer
    essays: list = field(default_factory=list)     # labels of required long answers
    drafted: list = field(default_factory=list)    # labels with a drafted answer
    errors: list = field(default_factory=list)     # (label, error) when a widget refused input


def _yes_no(flag):
    return "Yes" if flag else "No"


def answer(label: str, kind: str, profile: dict, type_: str = ""):
    """The profile's answer for a question, or None if the tool shouldn't answer it."""
    c, e, w, q = (profile.get(k, {}) for k in ("contact", "education", "work", "eeo"))
    l = clean_label(label).lower()
    if APPLICANT_ONLY_RE.search(l):
        return None
    # Compound questions flip meaning depending on wording ("authorized to work *without*
    # sponsorship?", "do you live in *and* are authorized in the listed countries?"). A wrong
    # Yes/No here is worse than none, so they are left to the applicant.
    if AUTH_RE.search(l) and (SPONSOR_RE.search(l) or RESIDENCE_RE.search(l)):
        return None
    # Order matters: the first match wins, so yes/no questions and graduation come before the
    # entity rules they mention ("currently enrolled at an educational *institution*?",
    # "when will you complete your *degree*?" were both mis-answered with the order reversed).
    rules = [
        (r"currently (enrolled|in school|a student|attending)|are you a (current )?student", _yes_no(e.get("currently_enrolled"))),
        (r"sponsor|visa", _yes_no(w.get("needs_sponsorship"))),
        (r"authori[sz]ed to work|eligible to work|legally (permitted|able|authorized)|right to work", _yes_no(w.get("authorized_us"))),
        (r"security clearance|active clearance", w.get("security_clearance")),
        (r"relocat", _yes_no(w.get("willing_to_relocate"))),
        (r"month (and|&|/) year", f"{e.get('grad_month', '')} {e.get('grad_year', '')}".strip()),
        (r"(graduation|end date).*month|month.*graduat", e.get("grad_month")),
        (r"(graduation|end date).*year|year.*graduat", e.get("grad_year")),
        (r"\bexpect to graduate (between|before|after|by)", None),   # a Yes/No about a window
        (r"graduation|graduate|grad date|complete your (current )?degree",
         f"{e.get('grad_month', '')} {e.get('grad_year', '')}".strip()),
        (r"\bfirst name|given name", c.get("first_name")),
        (r"\blast name|family name|surname", c.get("last_name")),
        (r"preferred (first )?name", c.get("preferred_name") or c.get("first_name")),
        (r"^(full )?name\b|^your name|legal name", f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()),
        (r"pronoun", c.get("pronouns")),
        (r"e-?mail", c.get("email")),
        (r"phone|mobile", c.get("phone")),
        (r"linkedin", c.get("linkedin")),
        (r"github", c.get("github")),
        (r"twitter|\bx \(formerly", None),
        (r"portfolio|personal (web)?site|^website|other website|\bwebsite\b", c.get("website")),
        (r"^country$|country of residence", "United States"),
        (r"current location|^location|city.*(live|reside)|where are you (located|based)", c.get("location")),
        (r"current (company|employer)", None),
        (r"^(school|university|college|institution)\b|which (school|university|college|institution)|"
         r"school (name|attended)|name of (your )?(school|university|college)", e.get("school")),
        (r"^degree\b|^(highest )?degree( type| level)?$|what degree|degree (are you )?(pursuing|type|level)", e.get("degree")),
        (r"discipline|major|field of study|area of study", e.get("major")),
        (r"\bgpa\b|grade point", e.get("gpa")),
        (r"start date (month|year)", None),
        (r"(available|availability|able) to start|earliest start|start date|when can you start", w.get("earliest_start")),
        (r"\bgender\b|\bsex\b", q.get("gender")),
        (r"hispanic|latin[oax]", q.get("hispanic")),
        (r"\brace\b|ethnic", q.get("race")),
        (r"veteran", q.get("veteran")),
        (r"disabilit", q.get("disability")),
    ]
    for pattern, value in rules:
        if re.search(pattern, l):
            return value or None
    if type_ == "email":
        return c.get("email") or None
    if type_ == "tel":
        return c.get("phone") or None
    return None


def pick_option(value: str, options: list):
    """The option text best matching a profile value, or None."""
    v = value.strip().lower()
    if not v or not options:
        return None
    if DECLINE_RE.search(v) or v == "decline":
        return next((o for o in options if DECLINE_RE.search(o)), None)
    if v in ("yes", "no"):
        return next((o for o in options if o.strip().lower().startswith(v)), None)
    exact = [o for o in options if o.strip().lower() == v]
    if exact:
        return exact[0]
    starts = [o for o in options if o.strip().lower().startswith(v) or v.startswith(o.strip().lower())]
    if starts:
        return starts[0]
    contains = [o for o in options if v in o.lower()]
    if contains:
        return contains[0]
    # Word overlap, for differently phrased names: "The University of Texas at Austin" vs
    # "University of Texas - Austin", "Austin, TX" vs "Austin, Texas, United States".
    want = _tokens(v)
    if not want:
        return None
    scored = sorted(((len(want & _tokens(o)) / len(want), -len(o), o) for o in options), reverse=True)
    best_share, _, best = scored[0]
    return best if best_share >= 0.75 else None


_STOP = {"the", "of", "at", "and", "in", "a", "an", "-", "&"}


def _tokens(text: str) -> set:
    words = re.findall(r"[a-z0-9]+", text.lower())
    out = set()
    for w in words:
        if w in _STOP:
            continue
        out.add(US_STATE_NAMES.get(w, w))   # "tx" -> "texas"
    return out


US_STATE_NAMES = {abbr.lower(): name.lower() for abbr, name in __import__(
    "scraper.classify", fromlist=["US_STATES"]).US_STATES.items() if " " not in name}


def clean_label(label: str) -> str:
    return re.sub(r"[\s*✱]+$", "", re.sub(r"\s+", " ", label)).strip()


def _is_essay(f) -> bool:
    # Only required long answers: optional boxes ("Additional information", accommodations,
    # "if other, specify") are left alone.
    return (f["kind"] == "textarea" and f["empty"] and f["required"] and len(f["label"]) > 20
            and not APPLICANT_ONLY_RE.search(f["label"]))


def fill_page(page, profile: dict, drafter=None, job_context: str = "") -> Report:
    """Fill what the profile can answer. Never submits. Returns what was done and what's left."""
    rep = Report()
    if FORBIDS_TOOLS_RE.search(page.inner_text("body")):
        rep.blocked = True
        return rep
    resume = (profile.get("files") or {}).get("resume", "")
    seen = set()   # fields already handled, by (kind, label, name); ids are reassigned each pass
    # Two passes: answering a question can reveal follow-ups (Ashby shows the institution and
    # graduation-date questions only after "Are you currently enrolled?" is answered Yes).
    for _pass in range(2):
        new = 0
        for f in page.evaluate(JS_FIELDS):
            label, kind, sel = clean_label(f["label"]), f["kind"], f'[data-fill-id="{f["id"]}"]'
            key = (kind, label, f.get("name", ""))
            if not label or key in seen:
                continue
            seen.add(key)
            new += 1
            if kind == "file":
                # Greenhouse labels both uploads "Attach"; the input's id says which is the resume.
                if re.search(r"resume|\bcv\b", f"{label} {f.get('name', '')}", re.I) and resume and Path(resume).is_file():
                    page.set_input_files(sel, resume)
                    rep.filled.append((label, Path(resume).name))
                continue
            if not f["empty"]:
                continue
            if re.search(r"signature|sign here|e-?sign", f"{label} {f.get('name', '')}", re.I):
                rep.for_you.append(f"{label} (signature)")
                continue
            if _is_essay(f):
                rep.essays.append(label)
                continue
            value = answer(label, kind, profile, f.get("type", ""))
            if value is None:
                if f["required"]:
                    rep.for_you.append(label)
                continue
            try:
                done = _apply(page, f, sel, value)
            except Exception as exc:
                done = None
                rep.errors.append((label, f"{type(exc).__name__}: {str(exc).splitlines()[0][:120]}"))
                page.keyboard.press("Escape")  # close any dropdown left open
            if done:
                rep.filled.append((label, done))
            elif f["required"]:
                rep.for_you.append(label)
        if not new:
            break
        page.wait_for_timeout(500)   # let revealed follow-ups render
    if drafter and rep.essays:
        ids = {clean_label(f["label"]): f["id"] for f in page.evaluate(JS_FIELDS) if f["kind"] == "textarea"}
        for label in rep.essays:
            text = drafter(label, job_context, profile) if label in ids else None
            if text:
                page.fill(f'[data-fill-id="{ids[label]}"]', text)
                rep.drafted.append(label)
    return rep


def _apply(page, f, sel, value):
    kind = f["kind"]
    if kind in ("text", "textarea"):
        if DECLINE_RE.search(value) or value.lower() == "decline":
            return None  # "Decline" is an option to pick, never text to type
        page.fill(sel, value)
        return value
    if kind == "select":
        opt = pick_option(value, f["options"])
        if opt:
            page.select_option(sel, label=opt)
        return opt
    if kind in ("radio", "checkbox"):
        opt = pick_option(value, f["options"])
        if opt is None:
            return None
        k = f["options"].index(opt)
        page.check(f'[data-fill-id="{f["id"]}-{k}"]', force=True)
        return opt
    if kind == "buttons":
        opt = pick_option(value, f["options"])
        if opt:
            page.locator(sel).get_by_role("button", name=opt, exact=True).click()
        return opt
    if kind == "combobox":
        box = page.locator(sel)
        box.scroll_into_view_if_needed()
        box.click(force=True)
        # Only visible options: Greenhouse keeps the phone-number country list (role=option,
        # hidden) in the page, which otherwise answers every dropdown with "Afghanistan".
        options = page.locator("[role=option]:visible")
        # Search widgets may find nothing for a long string, so retry with its first words.
        # e.g. "Austin, TX" -> "Austin"; "The University of Texas at Austin" -> "University of Texas"
        words = re.split(r"\s+", re.sub(r"^the\s+", "", value.split(",")[0], flags=re.I))
        for query in dict.fromkeys([value[:40], " ".join(words[:3]), words[0]]):
            box.fill(query)
            texts = []
            for _ in range(16):   # up to ~4 s for search results
                page.wait_for_timeout(250)
                texts = [t.strip() for t in options.all_inner_texts()]
                if texts and not re.search(r"loading|searching", " ".join(texts), re.I):
                    break
            opt = pick_option(value, texts)
            if opt is not None:
                options.nth(texts.index(opt)).click()
                return opt
        box.fill("")
        page.keyboard.press("Escape")
        return None
    return None
