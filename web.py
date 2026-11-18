"""Browser interface for the Leipzig student jobs bot."""

import argparse
from datetime import date
from functools import lru_cache
from html import escape
from time import monotonic
from urllib.error import URLError
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from leipzig_jobs import BOARD, JOB_OFFICE, SNAPSHOT, SNAPSHOT_DATE, WORK_RULES, fetch_jobs


@lru_cache(maxsize=1)
def load_jobs(cache_window):
    try:
        return fetch_jobs(), "Live listings from Studentenwerk Leipzig"
    except (URLError, OSError, ValueError):
        return SNAPSHOT, f"Live board unavailable. Showing saved listings from {SNAPSHOT_DATE}."


def render_job(job):
    return f"""
    <article>
      <h2><a href="{job.url}">{escape(job.title)}</a></h2>
      <p>{escape(job.tags)}</p>
      <dl>
        <dt>Pay</dt><dd>{escape(job.pay) or "See posting"}</dd>
        <dt>Hours</dt><dd>{escape(job.hours) or "See posting"}</dd>
        <dt>Dates</dt><dd>{escape(job.period) or "See posting"}</dd>
      </dl>
    </article>"""


def application(environ, start_response):
    if environ.get("PATH_INFO") != "/":
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"Page not found"]

    params = parse_qs(environ.get("QUERY_STRING", "")[:2048])
    query = params.get("q", [""])[0].strip()[:120]
    english = params.get("english", [""])[0] == "1"
    jobs, source = load_jobs(int(monotonic() // 300))
    today = date.today()
    matches = [job for job in jobs if job.matches(
        query.casefold().split(), "english" if english else "any", today
    )]
    cards = "".join(map(render_job, matches)) or "<p>No matches. Try a broader search or open the job board.</p>"
    hint = "<p>Jobs tagged English may also require German.</p>" if english else ""
    checked = "checked" if english else ""
    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Leipzig Student Jobs</title>
<style>
  * {{ box-sizing: border-box }}
  body {{ margin: 0; background: #f3f6f3; color: #172b20; font: 1rem/1.55 system-ui, sans-serif }}
  main {{ width: min(100% - 2rem, 60rem); margin: 3rem auto }}
  h1 {{ font-size: clamp(2.25rem, 7vw, 4rem); line-height: 1; margin-bottom: .55em }}
  h2 {{ font-size: 1.2rem; margin: 0 }}
  a {{ color: #205538; text-underline-offset: .2em }}
  form {{ background: #dfebdf; padding: 1.25rem; border-radius: .8rem; margin: 1.5rem 0 }}
  label[for="q"] {{ display: block; font-weight: 700 }}
  .search {{ display: flex; flex-wrap: wrap; gap: .5rem; margin: .5rem 0 1rem }}
  input[type="search"] {{ flex: 1 1 15rem; min-width: 0; border: 1px solid #678271; background: white }}
  input, button {{ font: inherit }}
  input[type="search"], button {{ border-radius: .4rem; padding: .6rem .8rem }}
  button {{ border: 0; background: #205538; color: white; cursor: pointer }}
  article {{ padding: 1.15rem; border: 1px solid #d3e0d5; border-radius: .8rem; background: white }}
  .results {{ display: grid; gap: .8rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 25rem), 1fr)) }}
  dl {{ display: grid; grid-template-columns: auto 1fr; gap: .25rem 1rem; margin-bottom: 0 }}
  dt {{ font-weight: 650 }}
  dd {{ margin: 0 }}
  footer {{ margin: 2rem 0 }}
  footer ul {{ padding-left: 1.25rem }}
</style></head>
<body><main>
  <h1>Leipzig Student Jobs</h1>
  <p>Find minijobs, casual shifts, and working-student jobs in Leipzig.</p>
  <form method="get" action="/">
    <label for="q">Search jobs</label>
    <div class="search">
      <input type="search" id="q" name="q" maxlength="120" value="{escape(query)}" placeholder="e.g. events or warehouse">
      <button type="submit">Search</button>
    </div>
    <label><input type="checkbox" name="english" value="1" {checked}> Show jobs tagged English</label>
  </form>
  <p>{len(matches)} found. {escape(source)}</p>
  {hint}
  <section class="results" aria-label="Job listings">{cards}</section>
  <footer><ul>
    <li><a href="{BOARD}">Full Studentenwerk Leipzig job board</a></li>
    <li><a href="{JOB_OFFICE}">Student registration guide</a></li>
    <li><a href="{WORK_RULES}">Work rules for international students</a></li>
  </ul></footer>
</main></body></html>"""
    start_response("200 OK", [
        ("Content-Type", "text/html; charset=utf-8"),
        ("X-Content-Type-Options", "nosniff"),
        ("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"),
    ])
    return [body.encode("utf-8")]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    with make_server(args.host, args.port, application) as server:
        print(f"Leipzig Student Jobs listening on {args.host}:{args.port}", flush=True)
        server.serve_forever()
