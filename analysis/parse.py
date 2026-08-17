"""Parsing & feature engineering for spotify_data.json (PROMPT.md Phase 1 & 2)."""
import json
import re
from datetime import datetime

DATA_PATH_DEFAULT = "../research/taste-data/spotify_data.json"

VERSION_QUALIFIER_RE = re.compile(
    r"\s*-\s*(Live|Live From|Live At|Remaster(ed)?|Radio Edit|Remix|Acoustic|Deluxe|A COLORS SHOW|feat\..+)",
    re.IGNORECASE,
)

META_RE = re.compile(
    r'#\s*Track:\s*"(?P<track>[^"]+)"\s*by\s*(?P<artists>.+?)\.\s*'
    r"(?:Composer:\s*(?P<composer>.+?)\.\s*)?"
    r"(?:Producer:\s*(?P<producer>.+?)\.\s*)?"
    r"(?:Conductor:\s*(?P<conductor>.+?)\.\s*)?"
    r"(?:Writer:\s*(?P<writer>.+?)\.\s*)?"
    r"(?:Lyricist:\s*(?P<lyricist>.+?)\.\s*)?"
    r"(?:Arranger:\s*(?P<arranger>.+?)\.\s*)?"
    r"Released on\s*(?P<released>[\d-]+)\.\s*"
    r"Descriptors:\s*(?P<descriptors>.+?)\.?\s*$"
)

ARTIST_RE = re.compile(r'"([^"]+)"\(spotify:artist:([A-Za-z0-9]+)\)|([A-Za-z0-9 .\'&]+)\(spotify:artist:([A-Za-z0-9]+)\)')


def _split_names_field(raw):
    """Parse a comma/'and'-joined list of quoted or bare names into a plain list."""
    if not raw:
        return []
    raw = raw.strip()
    parts = re.split(r",\s*(?:and\s+)?|\s+and\s+", raw)
    out = []
    for p in parts:
        p = p.strip().strip('"').strip()
        if p:
            out.append(p)
    return out


_QUOTED_RE = re.compile(r'"([^"]+)"')
_COMMA_AND_RE = re.compile(r"\s*,?\s+and\s+")


def _split_descriptors(raw):
    """Split a comma/'and'-joined descriptor string into individual tags.

    Quoted phrases are protected before splitting so an "and" *inside* a quoted
    descriptor (e.g. "rock and roll") isn't mistaken for a list separator, and
    a bare ' and ' with no preceding comma (e.g. 'country and "country blues"')
    is still recognized as a separator rather than swallowed into one token.
    """
    if not raw:
        return []

    quoted = []

    def _protect(m):
        quoted.append(m.group(1))
        return f"\x00{len(quoted) - 1}\x00"

    protected = _QUOTED_RE.sub(_protect, raw)
    # Normalize every '<comma>? and' separator to a plain comma so a single
    # split pass handles "X, Y, and Z", "X and Y", and "X, and Y" alike.
    normalized = _COMMA_AND_RE.sub(", ", protected)

    out = []
    for part in normalized.split(","):
        p = part.strip()
        if not p:
            continue
        m = re.fullmatch(r"\x00(\d+)\x00", p)
        if m:
            p = quoted[int(m.group(1))]
        out.append(p.strip().lower())
    return out


def parse_track_metadata(name_field):
    """Parse the packed `name` field: 'spotify:track:<uri>\\t# Track: ...' into a dict."""
    if "\t" not in name_field:
        return None
    _, meta_str = name_field.split("\t", 1)
    m = META_RE.search(meta_str)
    if not m:
        return None
    gd = m.groupdict()

    artist_names = []
    artist_uris = []
    for match in ARTIST_RE.finditer(gd["artists"]):
        quoted_name, quoted_uri, bare_name, bare_uri = match.groups()
        if quoted_name:
            artist_names.append(quoted_name)
            artist_uris.append(quoted_uri)
        elif bare_name:
            # A bare (unquoted) artist at the end of an "X, Y, and Z" list
            # greedily captures the leading "and " joiner — strip it.
            cleaned = re.sub(r"^(?:and)\s+", "", bare_name.strip(), flags=re.IGNORECASE)
            artist_names.append(cleaned)
            artist_uris.append(bare_uri)

    return {
        "track_name": gd["track"],
        "artist_names": artist_names,
        "artist_uris": artist_uris,
        "producers": _split_names_field(gd.get("producer")),
        "composers": _split_names_field(gd.get("composer") or gd.get("writer")),
        "released_on": gd["released"],
        "descriptors": _split_descriptors(gd["descriptors"]),
    }


def canonical_name(track_name):
    return VERSION_QUALIFIER_RE.sub("", track_name).strip()


def version_type(track_name):
    lowered = track_name.lower()
    if "live" in lowered:
        return "live"
    if "remaster" in lowered:
        return "remaster"
    if "remix" in lowered:
        return "remix"
    if "radio edit" in lowered:
        return "radio_edit"
    if "acoustic" in lowered:
        return "acoustic"
    if track_name == canonical_name(track_name):
        return "original"
    return "other"


def load_tracks(data_path=DATA_PATH_DEFAULT):
    """Parse spotify_data.json into a deduplicated list of track dicts."""
    with open(data_path) as f:
        data = json.load(f)

    raw_by_uri = {}

    def ingest(items, is_recent):
        for item in items:
            meta = parse_track_metadata(item["name"])
            if meta is None:
                continue
            uri = item["uri"]
            row = raw_by_uri.setdefault(uri, {"uri": uri, **meta})
            row["played_seconds_raw"] = item.get("played_seconds", 0)
            row["last_played_at"] = item.get("last_played_at")
            row["is_recent"] = row.get("is_recent", False) or is_recent
            if is_recent:
                row["played_seconds_recent"] = item.get("played_seconds", 0)
            else:
                row["played_seconds_top"] = item.get("played_seconds", 0)

    ingest(data.get("top_tracks", {}).get("items", []), is_recent=False)
    ingest(data.get("recent_tracks", {}).get("items", []), is_recent=True)

    # URI normalization: collapse versions sharing (canonical_name, primary_artist)
    groups = {}
    for uri, row in raw_by_uri.items():
        cname = canonical_name(row["track_name"])
        primary_artist = row["artist_uris"][0] if row["artist_uris"] else row["artist_names"][0] if row["artist_names"] else "unknown"
        key = (cname, primary_artist)
        groups.setdefault(key, []).append(row)

    tracks = []
    uri_collisions = []
    for (cname, _), rows in groups.items():
        rows.sort(key=lambda r: len(r["track_name"]))
        canonical_row = rows[0]
        if len(rows) > 1:
            uri_collisions.append({"canonical_name": cname, "uris": [r["uri"] for r in rows]})

        total_played = sum(r.get("played_seconds_top", r.get("played_seconds_raw", 0)) for r in rows)
        last_played = max((r["last_played_at"] for r in rows if r.get("last_played_at")), default=None)

        release_year = None
        try:
            release_year = int(canonical_row["released_on"][:4])
        except (ValueError, TypeError):
            pass

        tracks.append({
            "canonical_uri": canonical_row["uri"],
            "canonical_name": cname,
            "track_name": canonical_row["track_name"],
            "artist_names": canonical_row["artist_names"],
            "artist_uris": canonical_row["artist_uris"],
            "descriptors": canonical_row["descriptors"],
            "producers": canonical_row["producers"],
            "composers": canonical_row["composers"],
            "release_year": release_year,
            "decade": (release_year // 10 * 10) if release_year else None,
            "played_seconds": total_played,
            "last_played_at": last_played,
            "is_recent": any(r.get("is_recent") for r in rows),
            "version_type": version_type(canonical_row["track_name"]),
        })

    return tracks, uri_collisions


MACRO_GENRE_MAP = {
    "country": "country_americana", "country blues": "country_americana", "americana": "country_americana",
    "folk rock": "country_americana", "honky tonk": "country_americana",
    "hip hop": "hip_hop_rap", "rap": "hip_hop_rap", "pop rap": "hip_hop_rap", "trap": "hip_hop_rap", "trap latino": "hip_hop_rap",
    "pop": "pop", "bubblegum pop": "pop", "easy listening": "pop",
    "r&b": "r_and_b_soul", "soul": "r_and_b_soul", "soul funk": "r_and_b_soul", "soulful": "r_and_b_soul",
    "motown": "r_and_b_soul", "jazz blues": "r_and_b_soul",
    "indie folk": "indie_folk", "folk": "indie_folk", "folk pop": "indie_folk", "indie pop": "indie_folk", "indie": "indie_folk",
    "alternative rock": "alternative_rock", "rock": "alternative_rock", "grunge": "alternative_rock",
    "britpop": "alternative_rock", "garage rock": "alternative_rock", "new wave": "alternative_rock",
    "latin": "latin", "reggaeton": "latin", "salsa": "latin", "sierreno": "latin", "merengue": "latin",
    "house": "electronic", "club": "electronic", "electronic": "electronic", "ibiza": "electronic",
    "musicals": "classical_musicals", "classical": "classical_musicals",
}
MOOD_TAGS = {
    "sad", "melancholy", "slow", "romantic", "love", "cozy", "chill", "calm",
    "nostalgia", "moody", "sensual", "classy", "soulful", "nature", "acoustic",
}


def classify(track):
    """Return (macro_genres, moods) for a track — ALL matched macro genres,
    not just the first, since a track can legitimately span more than one
    (e.g. "pop rap" contributes to both hip_hop_rap descriptors here and
    could reasonably also read as pop). Order preserved, de-duplicated."""
    macros = []
    moods = []
    for d in track["descriptors"]:
        if d in MOOD_TAGS:
            moods.append(d)
        if d in MACRO_GENRE_MAP:
            macro = MACRO_GENRE_MAP[d]
            if macro not in macros:
                macros.append(macro)
    if not macros:
        macros = ["unknown"]
    return macros, moods
