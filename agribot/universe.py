"""Universo delle materie prime e riconoscimento dei nomi nel testo libero."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Commodity:
    key: str
    name: str
    symbol: str  # ticker Yahoo Finance (future continuo)
    sector: str
    aliases: tuple[str, ...]


UNIVERSE: tuple[Commodity, ...] = (
    Commodity("oro", "Oro", "GC=F", "Metalli preziosi", ("oro", "gold", "xau")),
    Commodity("argento", "Argento", "SI=F", "Metalli preziosi", ("argento", "silver", "xag")),
    Commodity("platino", "Platino", "PL=F", "Metalli preziosi", ("platino", "platinum")),
    Commodity("rame", "Rame", "HG=F", "Metalli industriali", ("rame", "copper")),
    Commodity("wti", "Petrolio WTI", "CL=F", "Energia", ("wti", "petrolio", "crude", "oil", "greggio")),
    Commodity("brent", "Petrolio Brent", "BZ=F", "Energia", ("brent",)),
    Commodity("gas", "Gas naturale", "NG=F", "Energia", ("gas", "gas naturale", "natgas", "natural gas")),
    Commodity("grano", "Grano", "ZW=F", "Agricole", ("grano", "frumento", "wheat")),
    Commodity("mais", "Mais", "ZC=F", "Agricole", ("mais", "granturco", "corn")),
    Commodity("soia", "Soia", "ZS=F", "Agricole", ("soia", "soybean", "soybeans", "soy")),
    Commodity("caffe", "Caffè", "KC=F", "Soft", ("caffe", "caffè", "coffee")),
    Commodity("zucchero", "Zucchero", "SB=F", "Soft", ("zucchero", "sugar")),
    Commodity("cacao", "Cacao", "CC=F", "Soft", ("cacao", "cocoa")),
    Commodity("cotone", "Cotone", "CT=F", "Soft", ("cotone", "cotton")),
    Commodity("bovini", "Bovini vivi", "LE=F", "Zootecnia", ("bovini", "bestiame", "live cattle", "cattle")),
)

_BY_KEY = {c.key: c for c in UNIVERSE}

SECTOR_ALIASES = {
    "metalli": ("Metalli preziosi", "Metalli industriali"),
    "preziosi": ("Metalli preziosi",),
    "energia": ("Energia",),
    "energetiche": ("Energia",),
    "agricole": ("Agricole",),
    "cereali": ("Agricole",),
    "soft": ("Soft",),
}


def get(key: str) -> Commodity | None:
    return _BY_KEY.get(key)


def _normalize(text: str) -> str:
    text = text.lower().replace("è", "e").replace("é", "e")
    return " " + re.sub(r"[^a-z0-9/ ]+", " ", text) + " "


def find_commodities(text: str) -> list[Commodity]:
    """Restituisce le materie prime citate nel testo, nell'ordine dell'universo.

    Gli alias multi-parola vengono cercati prima, così "gas naturale" non
    viene confuso con altro e "petrolio brent" → Brent (non WTI).
    """
    norm = _normalize(text)
    found: list[Commodity] = []
    consumed = norm
    pairs = sorted(
        ((alias, c) for c in UNIVERSE for alias in c.aliases),
        key=lambda p: -len(p[0]),
    )
    for alias, commodity in pairs:
        token = " " + _normalize(alias).strip() + " "
        if token in consumed:
            if commodity not in found:
                found.append(commodity)
            consumed = consumed.replace(token, " ")
    # "petrolio brent": l'alias generico "petrolio" non deve aggiungere anche il WTI
    wti, brent = get("wti"), get("brent")
    if brent in found and wti in found and not any(t in norm for t in (" wti ", " crude ", " greggio ")):
        found.remove(wti)
    order = {c.key: i for i, c in enumerate(UNIVERSE)}
    return sorted(found, key=lambda c: order[c.key])


def find_sectors(text: str) -> list[Commodity]:
    norm = _normalize(text)
    sectors: set[str] = set()
    for alias, names in SECTOR_ALIASES.items():
        if f" {alias} " in norm:
            sectors.update(names)
    return [c for c in UNIVERSE if c.sector in sectors]
