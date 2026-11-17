# Delivery Route System

🇧🇷 [Leia em português](README.md)

A **Python + Streamlit** web dashboard that builds the day's delivery route: it reads the orders ready for shipping, fetches their data from the **GestãoClick** ERP, calculates the path with the **Google Routes API**, and produces an ordered route with a PDF and a Google Maps link.
The project came from a need at the company where I worked, which planned its delivery routes by hand. Once finished, it was used internally by the team. This version is public for portfolio purposes only: the company name, logo and all real data have been removed.

**Development time:** 4 months.

## How it was built

This was my first professional project, built while I'm still learning.

- **By me:** the original Python automation (reading the orders, integrating with the GestãoClick and Google APIs, and calculating the route), the business rules, the security decisions, all design and user experience decisions (layout, colors, screen organization and what each screen shows), and the review of all the code.
- **With AI assistance (Claude Code):** the Streamlit web interface and parts of the system's later development, always based on the rules and design I defined. All generated code was reviewed and tested by me before going into the system.

## Features

- **Prioritized order list**, checked against the ERP (only confirmed orders), with invoice number, package count, and delivery to the customer or to a carrier.
- **Route generation** with 1 to 10 stops, a 50 km maximum radius, and departure and return times.
- **Grouping by carrier**: everything going to the same carrier becomes a single stop.
- **Extra stops** (pickups, samples, exchanges) looked up by Brazilian tax ID (CPF/CNPJ).
- **Route PDF** for the driver and a link with the stops for Google Maps.
- **Delivery confirmation** item by item and a 60-day **history**.
- **Google free-tier quota control**, to avoid charges.

## Security

- Login with **bcrypt**-hashed passwords, lockout after 5 failed attempts, and a mandatory change of the temporary password.
- Secrets (tokens, keys, address) only in `st.secrets`, **never in the code**.
- SQL always uses **parameters** (`?`) against SQL injection.
- All external text is **escaped** against XSS.
- **Data minimization**: tax IDs and phone numbers are removed from names before saving; history is deleted after 60 days.
- **Writes protected against concurrent access** (`BEGIN IMMEDIATE`): whoever saves last does not erase someone else's work.
- Access over the internal network only through **HTTPS** (Caddy as a reverse proxy).
- Code checked with **Bandit**, **pip-audit** and **Gitleaks**.

## Tech stack

Python 3.14 · Streamlit · SQLite · bcrypt · requests · fpdf2 · Google Routes API · GestãoClick API · Caddy

## Running it

1. Clone the repository and create the virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Copy `secrets.example.toml` to `.streamlit/secrets.toml` and fill in your own values. The admin password hash is generated with `python gerar_hash.py`.
3. Start it: `streamlit run app.py`
4. (Optional) For network access over HTTPS, download Caddy from [caddyserver.com](https://caddyserver.com/download), place `caddy.exe` in the `servidor` folder, and start the system with `servidor\iniciar_sistema.bat`.

## Tests

The tests use a temporary database and mocked APIs (no real calls):

```bash
python -m unittest testes_rodada1 testes_rodada2 testes_rodada3 testes_marca
```

## Rights

Code published for portfolio and viewing purposes only. All rights reserved.

*Note: the code, file names and interface are in Portuguese.*