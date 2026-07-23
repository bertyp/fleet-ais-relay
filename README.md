# Fleet AIS relay (GitHub Actions)

Why: the office firewall blocks aisstream.io, so this tiny repo collects our
6 vessels' AIS positions on GitHub's runners (open egress) every 15 minutes
and publishes positions.json. The office app pulls it from
raw.githubusercontent.com, which the LAN can reach. No scraping anywhere.

## Setup (~10 min, once)
1. Create a GitHub account if needed, then a new PUBLIC repo, e.g. `fleet-ais-relay`
   (public = unlimited free Actions minutes; positions are public AIS data anyway —
   the API key is NOT in the repo).
2. Upload these three files keeping the paths:
   - `collect.py`
   - `.github/workflows/ais-relay.yml`
   - `README.md` (this file)
3. Repo Settings -> Secrets and variables -> Actions -> New repository secret:
   name `AISSTREAM_KEY`, value = the aisstream.io key.
4. Actions tab -> enable workflows -> open "AIS relay" -> "Run workflow" (manual
   first run). Wait ~2 min -> positions.json appears in the repo.
5. Copy the RAW url of positions.json, e.g.
   `https://raw.githubusercontent.com/<user>/fleet-ais-relay/main/positions.json`
6. In the app repo `config/vessels_ais.yaml` add under `settings:`
   `relay_url: "<that raw url>"` — the Timetable strip goes live on the next
   page refresh. (No worker needed on the server while the firewall stands;
   if IT later unblocks aisstream, the local worker takes over automatically —
   freshest source wins.)
