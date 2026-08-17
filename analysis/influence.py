"""Build the influence-edge layer: curated (ground truth) + LLM-generated (labeled).

Your 30 hand-curated edges from music_graph.json import first and always win.
Everything else is generated from general music knowledge for artists in your
library that the curated graph doesn't cover — each such edge carries
source="llm" and a confidence level so it renders visually distinct and stays
correctable. Artists I don't have reliable specific knowledge about are
skipped rather than guessed at (listed at the end, not silently dropped).
"""
import json
import os

MUSIC_GRAPH_PATH = "../exploration/music-knowledge-graph/music_graph.json"
OUTPUT_PATH = "data/influence_edges.json"

# Artists I don't have confident, specific knowledge about — skipped rather
# than fabricated. Revisit manually if you know more about them.
SKIPPED_INSUFFICIENT_KNOWLEDGE = [
    "SIENNA SPIRO", "The Something Specials", "DON WEST",
    "Marlon Funaki", "Neu Blume", "LF SYSTEM",
]

# Each entry: (from_name, to_name, type, confidence, note)
# type follows the same vocabulary as music_graph.json: influenced, sounds_like,
# collaborated_with, bridges_to, part_of, discovery_path, family_connection.
LLM_EDGES = [
    ("Sam Cooke", "Amy Winehouse", "influenced", "medium",
     "Amy Winehouse's soul revivalism draws on the classic 60s soul lineage Cooke helped define."),
    ("Amy Winehouse", "Adele", "influenced", "high",
     "Widely credited as the artist who reopened the door for British soul-pop singers like Adele."),
    ("Fleetwood Mac", "Wild Rivers", "sounds_like", "medium",
     "Shared harmony-driven, warm soft-rock/folk-pop sensibility."),
    ("Drugdealer", "Fleetwood Mac", "influenced", "high",
     "Michael Collins' Drugdealer project is an explicit soft-rock/yacht-rock revival act."),
    ("The Smiths", "Radiohead", "influenced", "high",
     "Well-documented lineage from 80s British indie/alternative into Radiohead's early sound."),
    ("The White Stripes", "The Sways", "sounds_like", "medium",
     "Garage-rock revival lineage."),
    ("The White Stripes", "Foxy Shazam", "sounds_like", "medium",
     "Shared glam/garage-rock theatricality."),
    ("Radiohead", "Sam Fender", "sounds_like", "medium",
     "British alt-rock atmospherics; Fender's sound sits in this lineage alongside more direct Springsteen influence."),
    ("Van Morrison", "Paolo Nutini", "influenced", "high",
     "Nutini has cited Van Morrison directly; shared Scottish/Celtic soul-rock phrasing."),
    ("Paolo Nutini", "Sam Fender", "sounds_like", "medium",
     "Both British Isles soulful rock singer-songwriters."),
    ("Nick Drake", "Noah Kahan", "influenced", "medium",
     "Kahan's intimate folk-revival songwriting sits in the lineage Drake helped define, filtered through 2010s indie folk."),
    ("Wild Rivers", "Noah Kahan", "sounds_like", "high",
     "Contemporary folk-pop peers, frequently compared."),
    ("Zach Bryan", "Tyler Childers", "influenced", "high",
     "Bryan has directly cited Childers as part of the New Americana movement he emerged from."),
    ("Chris Stapleton", "Zach Bryan", "sounds_like", "high",
     "Both anchor the modern outlaw-country/Americana revival."),
    ("Chris Stapleton", "The Red Clay Strays", "influenced", "high",
     "Frequently compared for Southern rock/soul-inflected country revival."),
    ("Jon Pardi", "Cody Johnson", "sounds_like", "high",
     "Both neotraditional country mainstays."),
    ("Brooks & Dunn", "Jason Aldean", "influenced", "high",
     "Aldean has cited Brooks & Dunn as a formative influence on his country-rock sound."),
    ("Jason Aldean", "Cody Johnson", "sounds_like", "medium",
     "Shared mainstream country-rock lane."),
    ("Tanya Tucker", "Megan Moroney", "influenced", "medium",
     "Legacy female-country lineage into the current generation."),
    ("Megan Moroney", "Ella Langley", "sounds_like", "medium",
     "Contemporaries in the current wave of female country artists."),
    ("Ms. Lauryn Hill", "Drake", "influenced", "high",
     "Drake's 'Nice For What' samples Hill's 'Ex-Factor' directly."),
    ("Lil Wayne", "Drake", "influenced", "high",
     "Drake was signed to and mentored by Wayne's Young Money label early in his career."),
    ("Lil Wayne", "Lil Uzi Vert", "influenced", "high",
     "Widely cited lineage in melodic/mixtape-era hip-hop."),
    ("PARTYNEXTDOOR", "Drake", "influenced", "high",
     "PARTYNEXTDOOR co-shaped Drake's moody OVO R&B sound as an early labelmate and collaborator."),
    ("Gunna", "Lil Uzi Vert", "sounds_like", "high",
     "Melodic trap peers from the same Atlanta/mixtape-era lineage."),
    ("2 Chainz", "Gunna", "influenced", "medium",
     "Earlier Atlanta trap generation feeding into the melodic-trap style Gunna represents."),
    ("Big Sean", "J. Cole", "sounds_like", "medium",
     "Contemporaries in mainstream conscious-adjacent hip-hop."),
    ("Kanye West", "J. Cole", "influenced", "high",
     "Cole has directly cited Kanye's 'The College Dropout' as pivotal to his own artistic direction."),
    ("Drake", "Sampha", "collaborated_with", "high",
     "Sampha featured on Drake's 'Too Much' (Nothing Was the Same)."),
    ("Drake", "Yebba", "collaborated_with", "high",
     "Yebba features directly on 'DIE TRYING' alongside Drake and PARTYNEXTDOOR."),
    ("Sabrina Carpenter", "Chappell Roan", "sounds_like", "high",
     "Constantly compared as the two breakout pop stars of the same 2024 moment."),
    ("Sabrina Carpenter", "Demi Lovato", "sounds_like", "medium",
     "Shared Disney-to-pop-star career arc."),
    ("ROSALÍA", "Bad Bunny", "collaborated_with", "high",
     "Collaborated on 'La Noche de Anoche'; a direct bridge between flamenco-pop and reggaeton."),
    ("Bad Bunny", "KAROL G", "sounds_like", "high",
     "Both define contemporary global Latin urbano."),
    ("Rodrigo y Gabriela", "Fuerza Regida", "sounds_like", "high",
     "The connection you already drew yourself — Fuerza Regida's mariachi-guitar 'Marlboro Rojo' echoes the flamenco-metal energy of 'Diablo Rojo.'"),
    ("Al Green", "Aaron Frazer", "influenced", "high",
     "Frazer's falsetto soul-revival style draws directly on classic 70s soul singers like Green."),
    ("Al Green", "Durand Jones & The Indications", "influenced", "high",
     "A modern retro-soul revival band explicitly rooted in this classic soul lineage."),
    ("Leon Bridges", "St. Paul & The Broken Bones", "sounds_like", "high",
     "Both lead the modern Southern soul-revival wave."),
    ("Kate Bollinger", "Wild Rivers", "sounds_like", "medium",
     "Shared dreamy, understated indie-folk-pop sensibility."),
    ("Ben Platt", "Original Broadway Cast of Dear Evan Hansen", "part_of", "high",
     "Platt originated the lead role and is the cast recording's central voice."),
]


def load_curated_edges():
    with open(MUSIC_GRAPH_PATH) as f:
        graph = json.load(f)
    id_to_name = {a["id"]: a["name"] for a in graph["nodes"]["artists"]}
    # also include genre/concept ids so edges pointing at those still resolve to a label
    for g in graph["nodes"]["genres"]:
        id_to_name[g["id"]] = g["name"]
    for c in graph["nodes"]["concepts"]:
        id_to_name[c["id"]] = c["name"]

    edges = []
    for e in graph["edges"]:
        if e["from"] not in id_to_name or e["to"] not in id_to_name:
            continue
        edges.append({
            "from": id_to_name[e["from"]],
            "to": id_to_name[e["to"]],
            "type": e["type"],
            "source": "curated",
            "confidence": "confirmed",
            "note": e.get("note", ""),
        })
    return edges


def build_llm_edges(curated_edges):
    covered_pairs = {frozenset((e["from"], e["to"])) for e in curated_edges}
    edges = []
    for frm, to, etype, confidence, note in LLM_EDGES:
        pair = frozenset((frm, to))
        if pair in covered_pairs:
            continue  # curated already covers this relationship — don't duplicate
        edges.append({
            "from": frm, "to": to, "type": etype,
            "source": "llm", "confidence": confidence, "note": note,
        })
    return edges


def main():
    curated = load_curated_edges()
    llm = build_llm_edges(curated)
    all_edges = curated + llm

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(all_edges, f, indent=1)

    print(f"Curated edges (ground truth): {len(curated)}")
    print(f"LLM-generated edges (labeled, source='llm'): {len(llm)}")
    print(f"Total influence-layer edges: {len(all_edges)}")
    print(f"\nSkipped (insufficient reliable knowledge, {len(SKIPPED_INSUFFICIENT_KNOWLEDGE)}): "
          f"{', '.join(SKIPPED_INSUFFICIENT_KNOWLEDGE)}")
    print(f"\nWrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
