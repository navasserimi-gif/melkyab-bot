"""
Firmendaten von MaYa Investment GmbH für den Exposé-Fußbereich.
Werte lassen sich per Umgebungsvariable überschreiben (z.B. auf Railway).
"""

import os

COMPANY = {
    "name": "MaYa Investment GmbH",
    "phone": os.environ.get("COMPANY_PHONE", "+49 (0) 000 000 000"),
    "email": os.environ.get("COMPANY_EMAIL", "info@maya-investment.de"),
    "website": os.environ.get("COMPANY_WEBSITE", "www.maya-investment.de"),
    "address": os.environ.get("COMPANY_ADDRESS", "Musterstraße 1, 00000 Musterstadt"),
}
