# config.py
# -*- coding: utf-8 -*-
"""Konstanter för gbgcup (Alingsås HK · Göteborg Cup). Byt TOURNAMENT_ID nästa år."""

TOURNAMENT_ID = "72459189"
CLUB_ID = 76496464                       # NameClub({id:76496464}) = Alingsås HK
CLUB_NAME = "Alingsås HK"
CUP_NAME = "Göteborg Cup"

# cupmanager-värd för turneringen. Eventspecifik subdomän – byt om arrangören byter.
API_HOST = "goteborgcup.cupmanager.net"
# Publik resultatsida (footer-källänk).
RESULT_URL = "https://goteborgcup.com/2026,sv/result/"

PAGES_HOST = "martinwelen.github.io"
PAGES_PATH = "/gbgcup"
PAGES_BASE = f"https://{PAGES_HOST}{PAGES_PATH}"

UTC_OFFSET_HOURS = 2                      # Göteborg i september = CEST = UTC+2

CLUB_BLUE = "#1f5fbf"                     # klubbens standardfärg (ensamt lag)

# Färgord (slugifierat) → hex. Används när ALLA lag i en klass har färgsuffix.
COLOR_MAP = {
    "bla": "#1f5fbf",
    "vit": "#c9c2b4",
    "svart": "#23303a",
    "orange": "#e8730c",
    "gul": "#f2bd0c",
    "rod": "#d22f27",
    "gron": "#2f9e44",
    "rosa": "#e864a4",
}

# Distinkta färger för fallback (siffer-/blandade suffix).
PALETTE = ["#1f5fbf", "#e8730c", "#2f9e44", "#d22f27", "#9c36b5", "#f2bd0c"]

# Spelplats-förkortningar för slutspelsträdet (arena completeName → kort namn).
# Godkänd av Martin. Okänd hall → faller tillbaka på klartext (trunkeras i kortet).
VENUE_ABBR = {
    "Aktiviteten A": "Akt A",
    "Aktiviteten B": "Akt B",
    "Frölunda Kulturhus": "Frölunda",
    "Heidhallen": "Heid",
    "Härlandatjärnskolan": "Härlanda",
    "Kviberg Park Sporthall A": "Kviberg A",
    "Kviberg Park Sporthall B": "Kviberg B",
    "Kärra Sporthall": "Kärra",
    "Lillekärrshallen": "Lillekärr",
    "Lundbystrand 1": "Lundby 1",
    "Lundbystrand 3": "Lundby 3",
    "Lundbystrand 5": "Lundby 5",
    "Lundenhallen": "Lunden",
    "Prioritet Serneke Arena Serneke Arena A": "Serneke A",
    "Prioritet Serneke Arena Serneke Arena B": "Serneke B",
    "Prioritet Serneke Arena Serneke Gräs 1": "Serneke G1",
    "Prioritet Serneke Arena Serneke Gräs 2": "Serneke G2",
    "Prioritet Serneke Arena Serneke Gräs 3": "Serneke G3",
    "Prioritet Serneke Arena Serneke Gräs 4": "Serneke G4",
    "Prioritet Serneke Arena Serneke Gräs 5": "Serneke G5",
    "Prioritet Serneke Arena Serneke Gräs 6": "Serneke G6",
    "Sandklevsskolan": "Sandklev",
    "Torpahallen": "Torpa",
    "Valhalla Sport A": "Valhalla A",
    "Valhalla Sport B": "Valhalla B",
    "Valhalla Sport C": "Valhalla C",
    "Västerbergsskolan": "Västerberg",
    "ÖHK-Hallen A": "ÖHK A",
    "ÖHK-Hallen ÖHK WH hallen": "ÖHK WH",
    "ÖHK-Hallen ÖHK Gbg Brandservicehallen": "ÖHK Brand",
}
