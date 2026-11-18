# Leipzig Student Jobs

Search Studentenwerk Leipzig for casual shifts, minijobs, and working-student positions. English-tagged listings may also require German.

## Run the bot

Requires Python 3.9 or later. No API key or Python dependencies are needed for local use.

```sh
python3 leipzig_jobs.py warehouse
python3 leipzig_jobs.py --language english
python3 web.py
```

Open http://127.0.0.1:8080 on the machine running the bot. The web app caches job board results for up to five minutes and labels saved listings if fetching fails.

## Host on a server

Use a production WSGI server such as Gunicorn on the server.

```sh
gunicorn --bind 127.0.0.1:8080 web:application
```

Run it under your server's service manager and route your HTTPS reverse proxy to port 8080. The server needs outbound HTTPS access to the Studentenwerk Leipzig job board for live listings.

## GitHub Pages layout

The homepage lists projects. Leipzig Student Jobs lives at `/leipzig-jobs/` in the published site. To add another project, give it its own folder with an `index.html` and add a relative link to it on the homepage. The homepage and project folders are mirrored under `docs/` so either Pages publishing folder on `main` works.
