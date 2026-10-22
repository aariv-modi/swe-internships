"""Rule-based filters: is a posting a US software-engineering internship, and for which term?

Scope decisions (kept explicit so they can be argued with):
- SWE means roles whose main job is writing software: software/SWE/SDE/developer/programmer,
  full/front/back-end, mobile, web, DevOps/SRE, platform/infrastructure/cloud engineering,
  embedded software/firmware, ML/AI/data *engineering*, SDET. Scientists, analysts, researchers
  (other than research engineers), PM, design, IT support, hardware and quant trading are out.
- US means at least one location is in the US. A bare "Remote" counts as US.
"""
import re

INTERN_RE = re.compile(r"\b(intern|interns|internship|internships|co-?op|coop)\b", re.I)
INTERN_EXCLUDE_RE = re.compile(r"\b(high[- ]school|mba|post-?doc|externship|apprentice(ship)?)\b", re.I)

STRONG_SWE_RE = re.compile(
    r"\b(software|swe|sde|sdet|programmer|programming|developer|"
    r"full[- ]?stack|front[- ]?end|back[- ]?end|devops|site reliability|sre|ios|android|compiler)\b",
    re.I)
ROLE_SWE_RE = re.compile(
    r"\b(platform|infrastructure|cloud|mobile|web|machine learning|ml|ai|data|security|"
    r"embedded|firmware|systems software|site reliability|backend|frontend|distributed systems|"
    r"devsecops|mlops|applied ai)\s+(engineer|engineering|developer|development)\b",
    re.I)
NOT_DEVELOPER_RE = re.compile(
    r"\b(business|sales|market|talent|people|leadership|land|real estate)\s+develop\w*|"
    r"\bdeveloper\s+(community|relations|advocate|advocacy|marketing|experience|evangelist)", re.I)
NOT_SWE_RE = re.compile(
    r"\b(sales|marketing|recruit\w*|account(ing|ant)?|finance|financial|legal|counsel|"
    r"product manag\w*|program manag\w*|project manag\w*|designer|graphic|ux research|"
    r"analyst|scientist|research(er)? (assistant|associate)|researcher|trader|trading|"
    r"mechanical|electrical|hardware|civil|chemical|structural|environmental|water|"
    r"manufacturing|process|industrial|technician|field|solutions engineer|sales engineer|"
    r"applications? engineer|help ?desk|it support|desktop support|customer support|"
    r"operations|supply chain|construction|nursing|clinical|pharmac\w*)\b",
    re.I)

US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
    "PR": "Puerto Rico",
}
US_EXPLICIT_RE = re.compile(r"\b(united states( of america)?|usa|u\.s\.a?\.?|us)\b", re.I)
US_STATE_NAME_RE = re.compile(r"\b(" + "|".join(sorted(US_STATES.values(), key=len, reverse=True)) + r")\b", re.I)
# "Austin, TX", "US-CA-San Jose", "Santa Clara CA 95054"; case-sensitive so "in"/"or"/"me" don't match.
US_STATE_ABBR_RE = re.compile(r"(?:^|[,\-/(]\s*|\s)(" + "|".join(US_STATES) + r")(?=\s*(?:$|[,\-/)]|\s\d{5}))")
US_CITY_RE = re.compile(
    r"\b(new york( city)?|nyc|san francisco|sf bay area|bay area|seattle|austin|boston|chicago|"
    r"los angeles|palo alto|mountain view|menlo park|sunnyvale|san jose|santa clara|cupertino|"
    r"redmond|bellevue|denver|boulder|atlanta|dallas|houston|san diego|irvine|pittsburgh|"
    r"philadelphia|miami|raleigh|durham|salt lake city|portland|phoenix|nashville|minneapolis|"
    r"detroit|ann arbor|madison|columbus|arlington|reston|mclean|huntsville|el segundo)\b",
    re.I)
FOREIGN_COUNTRY_RE = re.compile(
    r"\b(canada|mexico|brazil|argentina|colombia|chile|peru|united kingdom|uk|england|scotland|"
    r"ireland|france|germany|deutschland|netherlands|belgium|switzerland|austria|spain|portugal|"
    r"italy|poland|czech( republic)?|romania|hungary|sweden|norway|denmark|finland|estonia|"
    r"lithuania|ukraine|serbia|greece|turkey|israel|egypt|uae|united arab emirates|saudi arabia|"
    r"india|pakistan|bangladesh|sri lanka|china|hong kong|taiwan|japan|korea|singapore|malaysia|"
    r"indonesia|philippines|vietnam|thailand|australia|new zealand|south africa|nigeria|kenya|"
    r"ontario|quebec|british columbia|alberta|emea|apac|latam)\b",
    re.I)
FOREIGN_CITY_RE = re.compile(
    r"\b(toronto|vancouver|montreal|waterloo|ottawa|calgary|markham|london|dublin|paris|berlin|"
    r"munich|frankfurt|hamburg|cologne|stuttgart|amsterdam|rotterdam|eindhoven|zurich|geneva|"
    r"lausanne|vienna|brussels|milan|rome|athens|istanbul|dubai|cairo|edinburgh|manchester|"
    r"cambridge, uk|oxford|belfast|cork|galway|budapest|sofia|belgrade|kyiv|vilnius|tallinn|riga|"
    r"helsinki|oslo|gothenburg|malmo|madrid|barcelona|lisbon|warsaw|krakow|prague|bucharest|stockholm|"
    r"copenhagen|tel aviv|bangalore|bengaluru|hyderabad|pune|mumbai|chennai|gurgaon|noida|delhi|"
    r"shanghai|beijing|shenzhen|hangzhou|taipei|tokyo|seoul|sydney|melbourne|"
    r"mexico city|guadalajara|sao paulo|são paulo|buenos aires|bogota|bogotá|manila)\b",
    re.I)
REMOTE_RE = re.compile(r"\b(remote|anywhere|virtual|work from home|work remotely)\b", re.I)


def is_internship(title: str, typed_intern: bool = False) -> bool:
    """typed_intern: the ATS itself labels the job an internship (Workday intern facet, Lever
    commitment, Ashby employmentType). Titles alone miss e.g. GE Appliances' "Software Engineer"
    filed under Workday's "Co-op" type."""
    if INTERN_EXCLUDE_RE.search(title):
        return False
    return typed_intern or bool(INTERN_RE.search(title))


SWE_EXACT_RE = re.compile(
    r"\b(software (engineer|engineering|developer|development)|swe|sde|sdet|"
    r"forward[- ]deployed (software )?engineer|application development|app development)\b", re.I)
HARD_NO_RE = re.compile(
    r"\b(sales|marketing|recruit\w*|analyst|scientist|researcher|trader|product manag\w*|"
    r"program manag\w*|designer|solutions engineer|sales engineer|applications? engineer|"
    r"technician|support|technical artist|consult\w*|solutions? engineer|"
    r"administrator|sysadmin|society of women engineers|conference|attending)\b", re.I)
# Generic titles that may or may not be software work: decided from the description.
MAYBE_RE = re.compile(
    r"\b(engineer|engineering|technology|technical|tech|member of technical staff|mts|"
    r"information technology|it|digital|computer science|computer engineering|ai|"
    r"artificial intelligence|automation|systems|r&d|research (and|&) development|robotics|"
    r"agent|agentic|llm|quantum computing|performance|tools|tooling|middleware|infrastructure)\b",
    re.I)
HARDWARE_DOMAIN_RE = re.compile(
    r"\b(mechanical|electrical|hardware|civil|chemical|structural|environmental|water|wind|"
    r"manufacturing|process|industrial|construction|nursing|clinical|pharmac\w*|aerospace|"
    r"silicon|asic|rf|analog|power systems|hvac|mining|petroleum|materials|biomedical|"
    r"field|project engineer|quality|process integration|module development|epi|cmos|beol|"
    r"wafer|yield|lithography|reliability engineer\w*)\b", re.I)


def swe_verdict(title: str) -> str:
    """'yes', 'no', or 'maybe' (generic title: needs the description)."""
    t = NOT_DEVELOPER_RE.sub(" ", title)
    if HARD_NO_RE.search(t) and not re.search(r"\bsoftware (engineer|developer)", t, re.I):
        return "no"
    if SWE_EXACT_RE.search(t) and not re.search(r"\b(sales|recruit\w*|technical artist)\b", t, re.I):
        return "yes"
    strong = STRONG_SWE_RE.search(t)
    role = ROLE_SWE_RE.search(t)
    if strong or role:
        if NOT_SWE_RE.search(t):
            # "Software" or "developer" wins over domain words ("Mechanical Software Engineer
            # Intern" is still software); job-function words (sales, analyst, scientist) exclude.
            return "yes" if strong and not HARD_NO_RE.search(t) else "no"
        return "yes"
    if HARD_NO_RE.search(t) or NOT_SWE_RE.search(t) or HARDWARE_DOMAIN_RE.search(t):
        return "no"
    return "maybe" if MAYBE_RE.search(t) else "no"


def is_swe(title: str) -> bool:
    return swe_verdict(title) == "yes"


SW_TERMS_RE = re.compile(
    r"\b(python|java|javascript|typescript|c\+\+|c#|golang|rust|kotlin|swift|scala|ruby|react|"
    r"angular|vue|node\.?js|django|flask|spring|sql|graphql|rest(ful)? apis?|apis?|backend|"
    r"back-end|frontend|front-end|full[- ]stack|git|linux|kubernetes|docker|aws|gcp|azure|"
    r"microservices|distributed systems|data structures|algorithms|object[- ]oriented|"
    r"ci/cd|unit tests?|codebase|pytorch|tensorflow|llms?)\b", re.I)
CODING_RE = re.compile(r"\b(software|coding|code|programming|develop(ing|ment)? (software|applications|features|tools|services))\b", re.I)
NON_SW_TERMS_RE = re.compile(
    r"\b(solidworks|autocad|cad|catia|creo|ansys|gd&t|pcb|schematics?|circuits?|soldering|"
    r"oscilloscope|machining|fabrication|welding|hvac|thermal|fluid|mechanical design|"
    r"help desk|service desk|ticketing|troubleshoot\w*|active directory|imaging|"
    r"desktop support|end[- ]user support|cabling|hardware installation)\b", re.I)


def description_is_swe(text: str) -> bool:
    """For 'maybe' titles: does the description describe building software?"""
    if not text:
        return False
    sw = {m[0].lower() for m in SW_TERMS_RE.finditer(text)}
    non = {m[0].lower() for m in NON_SW_TERMS_RE.finditer(text)}
    return len(sw) >= 3 and bool(CODING_RE.search(text)) and len(sw) >= 2 * len(non)


def location_is_us(loc: str):
    """True (US), False (not US) or None (can't tell, e.g. '3 Locations')."""
    s = loc.strip()
    if not s:
        return None
    if US_EXPLICIT_RE.search(s):
        return True
    if US_STATE_NAME_RE.search(s):
        # strip state names first so "New Mexico" doesn't read as Mexico
        return not FOREIGN_COUNTRY_RE.search(US_STATE_NAME_RE.sub(" ", s))
    if US_STATE_ABBR_RE.search(s):
        # "Toronto, CA" and "Frankfurt, DE" use country codes that collide with state codes
        return not (FOREIGN_COUNTRY_RE.search(s) or FOREIGN_CITY_RE.search(s))
    if FOREIGN_COUNTRY_RE.search(s):
        return False
    if US_CITY_RE.search(s):
        return True
    if FOREIGN_CITY_RE.search(s):
        return False
    if REMOTE_RE.search(s):
        return True
    return None


def us_status(locations):
    """True if any location is US, False if all are known non-US, None if undetermined."""
    results = [location_is_us(l) for l in locations]
    if any(r is True for r in results):
        return True
    if results and all(r is False for r in results):
        return False
    return None


SEASON_RE = re.compile(
    r"\b(summer|fall|autumn|winter|spring)\b[\s,'/-]*(?:of\s+)?(?:20)?(\d{2})?\b|"
    r"\b20(\d{2})\b[\s,/-]*(summer|fall|autumn|winter|spring)\b",
    re.I)
MONTH = (r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
         r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b\.?")
MONTH_RANGE_RE = re.compile(MONTH + r"\s*(?:20\d{2})?\s*(?:-|–|to|through)\s*" + MONTH + r"\s*(20\d{2})?", re.I)
YEAR_RE = re.compile(r"\b(20[2-3]\d)\b")
MONTH_SEASON = {"jan": "Winter", "feb": "Winter", "mar": "Spring", "apr": "Spring",
                "may": "Summer", "jun": "Summer", "jul": "Summer", "aug": "Fall", "sep": "Fall",
                "oct": "Fall", "nov": "Fall", "dec": "Winter"}


def terms(title: str) -> list[str]:
    found = []
    year_any = YEAR_RE.search(title)
    for m in SEASON_RE.finditer(title):
        season = (m[1] or m[4]).title().replace("Autumn", "Fall")
        yy = m[2] or m[3]
        year = f"20{yy}" if yy else (year_any[1] if year_any else "")
        found.append(f"{season} {year}".strip())
    if not found and (m := MONTH_RANGE_RE.search(title)):
        year = m[3] or (year_any[1] if year_any else "")
        found.append(f"{MONTH_SEASON[m[1].lower()[:3]]} {year}".strip())
    if not found and re.search(r"\bco-?op\b", title, re.I):
        found.append(f"Co-op {year_any[1]}".strip() if year_any else "Co-op")
    if not found and year_any:
        found.append(year_any[1])
    return list(dict.fromkeys(found))
