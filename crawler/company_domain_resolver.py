"""Deterministic company-domain and career-page resolution.

This resolver intentionally does not depend on search-engine HTML. It first uses
known official domains for common employers, then generates conservative domain
candidates from the company name and probes a small set of career paths.
"""
from urllib.parse import urljoin, urlparse
import re
import requests
from bs4 import BeautifulSoup

CAREER_PATHS = (
    "/careers", "/career", "/jobs", "/job-search", "/careers/jobs",
    "/join-us", "/work-with-us", "/careers/search", "/en/careers",
)

# Common Indian employers whose official domains are not safely derivable from
# their display names (TCS, LTIMindtree, L&T, etc.).
KNOWN_DOMAINS = {
    "infosys": "https://www.infosys.com",
    "tech mahindra": "https://www.techmahindra.com",
    "tata consultancy services (tcs)": "https://www.tcs.com",
    "tata consultancy services": "https://www.tcs.com",
    "mphasis": "https://www.mphasis.com",
    "wipro": "https://www.wipro.com",
    "ltimindtree": "https://www.ltimindtree.com",
    "hcl technologies": "https://www.hcltech.com",
    "hexaware technologies": "https://hexaware.com",
    "persistent systems": "https://www.persistent.com",
    "cyient": "https://www.cyient.com",
    "birlasoft": "https://www.birlasoft.com",
    "kpit technologies": "https://www.kpit.com",
    "l&t technology services": "https://www.ltts.com",
    "sonata software": "https://www.sonata-software.com",
    "zensar technologies": "https://www.zensar.com",
    "coforge": "https://www.coforge.com",
    "eclerx services": "https://www.eclerx.com",
    "firstsource solutions": "https://www.firstsource.com",
    "expleo solutions": "https://www.expleo.com",
    "happiest minds technologies": "https://www.happiestminds.com",
    "genpact": "https://www.genpact.com",
    "exl service": "https://www.exlservice.com",
    "wns global services": "https://www.wns.com",
    "startek (formerly aegis)": "https://www.startek.com",
    "aurionpro solutions": "https://www.aurionpro.com",
    "datamatics global services": "https://www.datamatics.com",
    "r systems international": "https://www.rsystems.com",
    "newgen software technologies": "https://newgensoft.com",
    "ramco systems": "https://www.ramco.com",
    "tata elxsi": "https://www.tataelxsi.com",
    "nucleus software exports": "https://www.nucleussoftware.com",
    "3i infotech": "https://www.3i-infotech.com",
    "intellect design arena": "https://www.intellectdesign.com",
    "quick heal technologies": "https://www.quickheal.co.in",
    "subex": "https://www.subex.com",
    "xoriant": "https://www.xoriant.com",
    "sasken technologies": "https://www.sasken.com",
    "onmobile global": "https://www.onmobile.com",
    "mastek": "https://www.mastek.com",
    "tanla platforms": "https://www.tanla.com",
    "encora": "https://www.encora.com",
    "altimetrik": "https://www.altimetrik.com",
    "globallogic (a hitachi group company)": "https://www.globallogic.com",
    "brillio": "https://www.brillio.com",
    "citiustech": "https://www.citiustech.com",
    "apexon": "https://www.apexon.com",
    "thoughtworks india": "https://www.thoughtworks.com",
    "epam systems india": "https://www.epam.com",
    "incedo inc.": "https://www.incedo.com",
    "nagarro": "https://www.nagarro.com",
    "endava india": "https://www.endava.com",
    "virtusa india": "https://www.virtusa.com",
    "cybage software": "https://www.cybage.com",
    "cigniti technologies": "https://www.cigniti.com",
    "qualitykiosk technologies": "https://www.qualitykiosk.com",
    "quest global": "https://www.questglobal.com",
    "neilsoft": "https://www.neilsoft.com",
    "kellton tech solutions": "https://www.kellton.com",
    "sg analytics": "https://www.sganalytics.com",
    "latentview analytics": "https://www.latentview.com",
    "fractal analytics": "https://fractal.ai",
    "mu sigma": "https://www.mu-sigma.com",
    "tredence": "https://www.tredence.com",
    "tiger analytics": "https://www.tigeranalytics.com",
    "accenture india": "https://www.accenture.com",
    "capgemini india": "https://www.capgemini.com",
    "cognizant technology solutions india": "https://www.cognizant.com",
    "dxc technology india": "https://dxc.com",
    "ntt data india": "https://www.nttdata.com",
    "ibm india": "https://www.ibm.com",
}


def _norm(value: str) -> str:
    value = re.sub(r"\s+", " ", str(value or "").strip().lower())
    return value.replace("&", "and")


def domain_candidates(company: str) -> list[str]:
    key = _norm(company)
    out = []
    if key in KNOWN_DOMAINS:
        out.append(KNOWN_DOMAINS[key])
    cleaned = re.sub(r"\b(india|formerly|aegis|a company|group company)\b", " ", key)
    cleaned = re.sub(r"\([^)]*\)", " ", cleaned)
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned).strip()
    words = [w for w in cleaned.split() if w not in {"limited", "ltd", "inc", "incorporated", "technologies", "technology", "solutions", "services", "global"}]
    slugs = ["".join(words), "-".join(words)]
    for slug in slugs:
        if slug:
            for tld in (".com", ".co.in", ".in"):
                out.append(f"https://www.{slug}{tld}")
    # Preserve order and remove duplicates.
    return list(dict.fromkeys(out))


def _looks_career(url: str, text: str = "") -> bool:
    hay = f"{url} {text}".lower()
    return any(term in hay for term in ("career", "careers", "jobs", "job-search", "join-us", "work-with-us", "opportunities", "vacancies"))


def resolve(company: str, timeout: tuple[int, int] = (3, 7)) -> dict:
    """Return official website + career URL when they can be determined directly."""
    session = requests.Session()
    session.headers.update({"User-Agent": "JobHunterAI/1.0"})
    for domain in domain_candidates(company):
        try:
            response = session.get(domain, timeout=timeout, allow_redirects=True)
            if response.status_code >= 400:
                continue
            final = response.url.rstrip("/")
            official = f"{urlparse(final).scheme}://{urlparse(final).netloc}"
            soup = BeautifulSoup(response.text, "html.parser")
            links = []
            for a in soup.find_all("a", href=True):
                href = urljoin(final + "/", str(a["href"]).strip())
                text = " ".join(a.stripped_strings)
                if urlparse(href).netloc == urlparse(final).netloc and _looks_career(href, text):
                    links.append(href.rstrip("/"))
            for link in links:
                return {"website": official, "career_url": link, "status": "Found"}
            for path in CAREER_PATHS:
                candidate = urljoin(official + "/", path.lstrip("/"))
                try:
                    probe = session.head(candidate, timeout=timeout, allow_redirects=True)
                    if probe.status_code < 400 and _looks_career(probe.url, ""):
                        return {"website": official, "career_url": probe.url.rstrip("/"), "status": "Found"}
                except requests.RequestException:
                    continue
            # A live official domain is still valuable; the career page can be
            # discovered by CareerFinder on the next stage.
            return {"website": official, "career_url": None, "status": "Website found"}
        except requests.RequestException:
            continue
    return {"website": None, "career_url": None, "status": "Not found"}
