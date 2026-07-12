"""E-Mail-Versand des täglichen Analyse-Reports per SMTP (z.B. Gmail)."""
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .scoring import ScoredListing

PROPERTY_TYPE_LABELS = {"wohnung": "Wohnung", "grundstueck": "Grundstück"}


def _fmt_price(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{int(value):,} €".replace(",", ".")


def _fmt_size(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.0f} m²"


def _fmt_price_per_sqm(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.0f} €/m²".replace(",", ".")


def build_html(scored_listings: list[ScoredListing], cities: list[str], max_price: int) -> str:
    today = date.today().strftime("%d.%m.%Y")
    rows = []
    for s in scored_listings:
        listing = s.listing
        rows.append(
            "<tr>"
            f'<td><a href="{listing.url}">{listing.title}</a></td>'
            f"<td>{PROPERTY_TYPE_LABELS.get(listing.property_type, listing.property_type)}</td>"
            f"<td>{listing.location}</td>"
            f"<td>{_fmt_price(listing.price_eur)}</td>"
            f"<td>{_fmt_size(listing.size_sqm)}</td>"
            f"<td>{_fmt_price_per_sqm(s.price_per_sqm)}</td>"
            f"<td>{'Privat' if listing.is_private else 'Gewerblich'}</td>"
            f"<td>{'<br>'.join(s.reasons)}</td>"
            "</tr>"
        )

    if rows:
        body = (
            '<table border="1" cellpadding="6" cellspacing="0" '
            'style="border-collapse:collapse;font-family:sans-serif;font-size:13px;">'
            '<tr style="background:#f0f0f0;">'
            "<th>Titel</th><th>Typ</th><th>Ort</th><th>Preis</th><th>Größe</th>"
            "<th>€/m²</th><th>Anbieter</th><th>Bewertung</th></tr>"
            f"{''.join(rows)}</table>"
        )
    else:
        body = "<p>Heute keine passenden Angebote von Privatanbietern gefunden.</p>"

    return (
        '<html><body style="font-family:sans-serif;">'
        f"<h2>🏡 MelkYab Immobilien-Analyse – {today}</h2>"
        f"<p>Region: {', '.join(cities)} | Max. Preis: {_fmt_price(max_price)} | Nur Privatanbieter (keine Provision)</p>"
        f"{body}"
        '<p style="color:#888;font-size:11px;">Automatisierte Analyse aus Kleinanzeigen.de. '
        "Richtwerte für die Bewertung sind grobe Schätzungen, keine Marktgarantie. "
        "Angebote vor Kontaktaufnahme bitte selbst prüfen.</p>"
        "</body></html>"
    )


def send_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    recipient: str,
    subject: str,
    html_body: str,
) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as server:
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, [recipient], msg.as_string())
