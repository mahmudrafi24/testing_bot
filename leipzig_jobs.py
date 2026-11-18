"""Find casual student jobs on the public Studentenwerk Leipzig job board."""

import argparse
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
import re
from urllib.error import URLError
from urllib.request import Request, urlopen

BOARD = "https://jobvermittlung.studentenwerk-leipzig.de/"
JOB_OFFICE = "https://www.studentenwerk-leipzig.de/en/bafoeg-financing/student-job-office/"
WORK_RULES = "https://www.make-it-in-germany.com/en/study-vocational-training/studying-in-germany/work"
CONTRACTS = ("Minijob", "Kurzfristige Beschäftigung", "Tagesjob", "Werkstudierendenvertrag")
DISTRICTS = r"zentrum|paunsdorf|plagwitz|connewitz|mockau|lößnig|gohlis|lindenau|reudnitz"
TITLE = re.compile(r"(.+?)\s*\(#(\d+)\)")
DETAIL = re.compile(r"(?:^|/)job/view/(\d+)(?:[/?#]|$)")
DATE = re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b")
KEYWORDS = {
    "events": "event messe trade stagehand seminar gastronomie catering",
    "warehouse": "lager logistik versand paket verpackung",
    "cleaning": "reinigung putz housekeeping",
    "kitchen": "küche spül gastro koch",
    "delivery": "liefer kurier zustell",
    "retail": "verkauf handel kasse",
    "tutoring": "nachhilfe unterricht",
    "weekend": "weekend wochenende samstag sonntag",
}


@dataclass(frozen=True)
class Job:
    number: str
    title: str
    tags: str
    period: str
    hours: str
    pay: str

    @property
    def url(self):
        return f"{BOARD}job/view/{self.number}?fp=1"

    def matches(self, terms, language, today):
        tags = self.tags.casefold()
        if not re.search(rf"\b(?:leipzig|{DISTRICTS})\b", tags):
            return False
        if not any(contract.casefold() in tags for contract in CONTRACTS):
            return False
        if language == "english" and not re.search(r"\benglisch\b", tags):
            return False
        dates = DATE.findall(self.period)
        if dates and not re.search(r"\bab\b", self.period, re.I):
            try:
                if datetime.strptime(dates[-1], "%d.%m.%Y").date() < today:
                    return False
            except ValueError:
                pass
        searchable = f"{self.title} {self.tags} {self.hours} {self.pay}".casefold()
        return all(
            any(alias in searchable for alias in KEYWORDS.get(term, term).split())
            for term in terms
        )


class BoardParser(HTMLParser):
    """Collect text between the numbered title and the corresponding detail link."""

    headings = {"h2", "h3", "h4", "h5"}
    blocks = {"div", "br", "p", "li", "dt", "dd", "td", "h2", "h3", "h4", "h5", "article"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self.jobs = {}
        self.link = None
        self.heading = None
        self.title = None

    def handle_starttag(self, tag, attrs):
        if tag in self.headings:
            self.heading = []
        if self.title and tag in self.blocks:
            self.parts.append(" ")
        if tag == "a":
            href = dict(attrs).get("href") or ""
            self.link = DETAIL.search(href)

    def handle_data(self, data):
        if self.heading is not None:
            self.heading.append(data)
        if self.title:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag in self.headings and self.heading is not None:
            heading = " ".join("".join(self.heading).split())
            self.heading = None
            match = TITLE.fullmatch(heading)
            if match:
                self.title = match.groups()
                self.parts.clear()
            return
        if self.title and tag in self.blocks:
            self.parts.append(" ")
        if tag != "a":
            return
        link, self.link = self.link, None
        if not link or not self.title or link.group(1) != self.title[1]:
            return
        fields = " ".join("".join(self.parts).split())
        details = re.fullmatch(
            r"(.*?)\s*Zeitraum\s*:?(.*?)\s*Arbeitszeit\s*:?(.*?)\s*Bezahlung\s*:?(.*?)\s*Job ansehen",
            fields,
            re.I,
        )
        if details:
            title, number = self.title
            self.jobs[number] = Job(number, title, *(field.strip() for field in details.groups()))
            self.title = None
            self.parts.clear()

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


def fetch_jobs():
    request = Request(BOARD, headers={"User-Agent": "LeipzigStudentJobs/1.0"})
    with urlopen(request, timeout=12) as response:
        page = response.read(2_000_000).decode(response.headers.get_content_charset() or "utf-8")
    parser = BoardParser()
    parser.feed(page)
    parser.close()
    if not parser.jobs:
        raise ValueError("No listings could be read from the job board.")
    return list(parser.jobs.values())


SNAPSHOT_DATE = "2026-11-18"
SNAPSHOT = [
    Job("42730", "Event and hospitality service", "Leipzig · Gastro · Kurzfristige Beschäftigung · Deutsch",
        "ab 30.11.2026", "Flexible Monday through Sunday", "€15–€15.33"),
    Job("42729", "Event logistics and stagehand", "Leipzig · Stagehand · Kurzfristige Beschäftigung · Deutsch",
        "ab 30.11.2026", "Flexible Monday through Sunday", "€15–€15.33 plus shift premiums"),
    Job("42726", "Trade fair assistant", "Leipzig · Messe · Kurzfristige Beschäftigung · Deutsch",
        "06.02.2027–14.02.2027", "10:00–17:00", "€18"),
    Job("42715", "Packing assistant", "Leipzig Alt-West · Verpackung · Minijob · Deutsch",
        "ab 11.11.2026", "Monday and Friday, up to 10 hours/week", "€14"),
    Job("42701", "Student IT assistant", "Leipzig · IT · Minijob · Deutsch · Englisch",
        "01.12.2026–31.12.2027", "43 hours/month", "€14"),
    Job("42700", "Passenger survey for Deutsche Bahn", "Leipzig · Kurzfristige Beschäftigung · Deutsch",
        "15.11.2026–31.12.2027", "Flexible by arrangement", "From €17.48 (€19.23 weekends/holidays)"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("keywords", nargs="*", help="Examples: events, warehouse, cleaning, or weekend")
    parser.add_argument("--language", choices=("any", "english"), default="any",
                        help="Show jobs marked Englisch. Check whether German is also required.")
    parser.add_argument("--offline", action="store_true", help="Use the dated sample of public listings.")
    args = parser.parse_args()
    jobs = SNAPSHOT
    offline = args.offline
    if not offline:
        try:
            jobs = fetch_jobs()
        except (URLError, OSError, ValueError) as error:
            print(f"Live board unavailable ({error}).")
            offline = True

    if offline:
        print(f"Saved listings from {SNAPSHOT_DATE}. Verify availability on the job board.")
    else:
        print("Public listings from the first page of Studentenwerk Leipzig.")

    terms = [word for phrase in args.keywords for word in phrase.casefold().split()]
    today = date.today()
    matches = [job for job in jobs if job.matches(terms, args.language, today)]
    for job in matches:
        print(f"\n{job.title}\n  {job.tags}\n  Dates: {job.period}\n"
              f"  Hours: {job.hours}\n  Pay: {job.pay}\n  {job.url}")
    if not matches:
        print("No matches in the listings checked. Try fewer keywords or open the board below.")
    if args.language == "english":
        print("\nThe English tag may appear alongside German. Check the posting for requirements.")
    print(f"\nFull job board: {BOARD}\nStudent registration guide: {JOB_OFFICE}\n"
          f"Work rules for international students: {WORK_RULES}")


if __name__ == "__main__":
    main()
