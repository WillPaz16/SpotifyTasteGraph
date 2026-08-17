---
type: analysis
tags: [taste-analysis, influence]
---

# Influence Lineage

Curated edges are ground truth from your hand-built knowledge graph. LLM-generated edges are my own music knowledge, clearly marked — correct or delete any that are wrong; re-runs never overwrite entries you've edited in `analysis/data/influence_edges.json`.

## Curated (ground truth)

- **Sam Cooke** influenced **Al Green** — Al Green's entire vocal approach draws from Cooke
- **Al Green** influenced **Ms. Lauryn Hill**
- **Roberta Flack** influenced **Ms. Lauryn Hill** — Fugees covered Killing Me Softly; direct lineage
- **Ms. Lauryn Hill** influenced **SZA**
- **Ms. Lauryn Hill** collaborated_with **D'Angelo** — Nothing Even Matters
- **D'Angelo** influenced **Bruno Mars** — Via producer D'Mile
- **Bert Jansch** influenced **Nick Drake**
- **Bert Jansch** influenced **John Martyn**
- **Nick Drake** sounds_like **Mazzy Star** — Same hazy intimate frequency
- **John Martyn** collaborated_with **Nick Drake** — Solid Air written for Drake
- **Van Morrison** influenced **John Martyn**
- **Tim Buckley** influenced **Jeff Buckley** — Father and son — barely knew each other
- **Tim Buckley** family_connection **Jeff Buckley**
- **Van Morrison** influenced **Jeff Buckley**
- **Paco de Lucía** collaborated_with **Camarón de la Isla** — Most important collaboration in flamenco history
- **Paco de Lucía** influenced **Rodrigo y Gabriela**
- **Paco de Lucía** part_of **Nuevo Flamenco** — Invented the genre
- **Carlos Santana** collaborated_with **Ms. Lauryn Hill** — To Zion — nylon-string guitar
- **Carlos Santana** bridges_to **Nylon-String Guitar Warmth** — His tone on To Zion is the seed concept
- **José Feliciano** part_of **Nylon-String Guitar Warmth**
- **Ms. Lauryn Hill** discovery_path **British Folk** — To Zion guitar warmth → José Feliciano → Nick Drake → British folk
- **Ms. Lauryn Hill** discovery_path **Flamenco** — To Zion guitar warmth → Santana → nylon-string → Paco de Lucía
- **Rodrigo y Gabriela** bridges_to **Flamenco**
- **ROSALÍA** part_of **Flamenco**
- **Amália Rodrigues** part_of **Fado**
- **João Gilberto** part_of **Bossa Nova**
- **Caetano Veloso** influenced **João Gilberto**
- **Mazzy Star** sounds_like **Nick Drake**
- **Van Morrison** part_of **Celtic Soul / Irish Folk-Soul**
- **John Martyn** part_of **Celtic Soul / Irish Folk-Soul**

## LLM-generated (labeled, correctable)

- **Sam Cooke** influenced **Amy Winehouse** *(confidence: medium)* — Amy Winehouse's soul revivalism draws on the classic 60s soul lineage Cooke helped define.
- **Amy Winehouse** influenced **Adele** *(confidence: high)* — Widely credited as the artist who reopened the door for British soul-pop singers like Adele.
- **Fleetwood Mac** sounds_like **Wild Rivers** *(confidence: medium)* — Shared harmony-driven, warm soft-rock/folk-pop sensibility.
- **Drugdealer** influenced **Fleetwood Mac** *(confidence: high)* — Michael Collins' Drugdealer project is an explicit soft-rock/yacht-rock revival act.
- **The Smiths** influenced **Radiohead** *(confidence: high)* — Well-documented lineage from 80s British indie/alternative into Radiohead's early sound.
- **The White Stripes** sounds_like **The Sways** *(confidence: medium)* — Garage-rock revival lineage.
- **The White Stripes** sounds_like **Foxy Shazam** *(confidence: medium)* — Shared glam/garage-rock theatricality.
- **Radiohead** sounds_like **Sam Fender** *(confidence: medium)* — British alt-rock atmospherics; Fender's sound sits in this lineage alongside more direct Springsteen influence.
- **Van Morrison** influenced **Paolo Nutini** *(confidence: high)* — Nutini has cited Van Morrison directly; shared Scottish/Celtic soul-rock phrasing.
- **Paolo Nutini** sounds_like **Sam Fender** *(confidence: medium)* — Both British Isles soulful rock singer-songwriters.
- **Nick Drake** influenced **Noah Kahan** *(confidence: medium)* — Kahan's intimate folk-revival songwriting sits in the lineage Drake helped define, filtered through 2010s indie folk.
- **Wild Rivers** sounds_like **Noah Kahan** *(confidence: high)* — Contemporary folk-pop peers, frequently compared.
- **Zach Bryan** influenced **Tyler Childers** *(confidence: high)* — Bryan has directly cited Childers as part of the New Americana movement he emerged from.
- **Chris Stapleton** sounds_like **Zach Bryan** *(confidence: high)* — Both anchor the modern outlaw-country/Americana revival.
- **Chris Stapleton** influenced **The Red Clay Strays** *(confidence: high)* — Frequently compared for Southern rock/soul-inflected country revival.
- **Jon Pardi** sounds_like **Cody Johnson** *(confidence: high)* — Both neotraditional country mainstays.
- **Brooks & Dunn** influenced **Jason Aldean** *(confidence: high)* — Aldean has cited Brooks & Dunn as a formative influence on his country-rock sound.
- **Jason Aldean** sounds_like **Cody Johnson** *(confidence: medium)* — Shared mainstream country-rock lane.
- **Tanya Tucker** influenced **Megan Moroney** *(confidence: medium)* — Legacy female-country lineage into the current generation.
- **Megan Moroney** sounds_like **Ella Langley** *(confidence: medium)* — Contemporaries in the current wave of female country artists.
- **Ms. Lauryn Hill** influenced **Drake** *(confidence: high)* — Drake's 'Nice For What' samples Hill's 'Ex-Factor' directly.
- **Lil Wayne** influenced **Drake** *(confidence: high)* — Drake was signed to and mentored by Wayne's Young Money label early in his career.
- **Lil Wayne** influenced **Lil Uzi Vert** *(confidence: high)* — Widely cited lineage in melodic/mixtape-era hip-hop.
- **PARTYNEXTDOOR** influenced **Drake** *(confidence: high)* — PARTYNEXTDOOR co-shaped Drake's moody OVO R&B sound as an early labelmate and collaborator.
- **Gunna** sounds_like **Lil Uzi Vert** *(confidence: high)* — Melodic trap peers from the same Atlanta/mixtape-era lineage.
- **2 Chainz** influenced **Gunna** *(confidence: medium)* — Earlier Atlanta trap generation feeding into the melodic-trap style Gunna represents.
- **Big Sean** sounds_like **J. Cole** *(confidence: medium)* — Contemporaries in mainstream conscious-adjacent hip-hop.
- **Kanye West** influenced **J. Cole** *(confidence: high)* — Cole has directly cited Kanye's 'The College Dropout' as pivotal to his own artistic direction.
- **Drake** collaborated_with **Sampha** *(confidence: high)* — Sampha featured on Drake's 'Too Much' (Nothing Was the Same).
- **Drake** collaborated_with **Yebba** *(confidence: high)* — Yebba features directly on 'DIE TRYING' alongside Drake and PARTYNEXTDOOR.
- **Sabrina Carpenter** sounds_like **Chappell Roan** *(confidence: high)* — Constantly compared as the two breakout pop stars of the same 2024 moment.
- **Sabrina Carpenter** sounds_like **Demi Lovato** *(confidence: medium)* — Shared Disney-to-pop-star career arc.
- **ROSALÍA** collaborated_with **Bad Bunny** *(confidence: high)* — Collaborated on 'La Noche de Anoche'; a direct bridge between flamenco-pop and reggaeton.
- **Bad Bunny** sounds_like **KAROL G** *(confidence: high)* — Both define contemporary global Latin urbano.
- **Rodrigo y Gabriela** sounds_like **Fuerza Regida** *(confidence: high)* — The connection you already drew yourself — Fuerza Regida's mariachi-guitar 'Marlboro Rojo' echoes the flamenco-metal energy of 'Diablo Rojo.'
- **Al Green** influenced **Aaron Frazer** *(confidence: high)* — Frazer's falsetto soul-revival style draws directly on classic 70s soul singers like Green.
- **Al Green** influenced **Durand Jones & The Indications** *(confidence: high)* — A modern retro-soul revival band explicitly rooted in this classic soul lineage.
- **Leon Bridges** sounds_like **St. Paul & The Broken Bones** *(confidence: high)* — Both lead the modern Southern soul-revival wave.
- **Kate Bollinger** sounds_like **Wild Rivers** *(confidence: medium)* — Shared dreamy, understated indie-folk-pop sensibility.
- **Ben Platt** part_of **Original Broadway Cast of Dear Evan Hansen** *(confidence: high)* — Platt originated the lead role and is the cast recording's central voice.
- **Lee Fields & The Expressions** influenced **Durand Jones & The Indications** *(confidence: high)* — Veteran deep-soul singer since the 60s/70s scene, frequently cited as a mentor influence on the younger soul-revival generation Durand Jones & The Indications belongs to.
- **Durand Jones** part_of **Durand Jones & The Indications** *(confidence: high)* — Durand Jones is the band's lead singer, who also records under his own name as a solo act.
- **Black Pumas** sounds_like **Leon Bridges** *(confidence: high)* — Both lead the modern Grammy-nominated soul-revival wave, frequently compared.
- **Curtis Harding** sounds_like **St. Paul & The Broken Bones** *(confidence: medium)* — Contemporary retro-soul singer-songwriters of the same revival era.
- **Anderson East** sounds_like **St. Paul & The Broken Bones** *(confidence: medium)* — Both modern Southern soul-revival artists working in a similar retro-soul lane.
- **Ne-Yo** influenced **Mario** *(confidence: high)* — Ne-Yo wrote and produced Mario's 2004 hit 'Let Me Love You.'
- **Mario** sounds_like **Chris Brown** *(confidence: medium)* — Both broke through as young R&B stars in the mid-2000s and are frequently grouped together from that era.
- **Olivia Rodrigo** sounds_like **Chappell Roan** *(confidence: medium)* — Both part of the 2023-2024 breakout pop-star cohort frequently discussed together, though musically distinct.
- **Alicia Keys** sounds_like **Adele** *(confidence: medium)* — Both piano-driven soul-pop vocalists frequently compared for vocal power and songwriting.
- **Riley Green** collaborated_with **Ella Langley** *(confidence: high)* — Their 2024 duet 'You Look Like You Love Me' was a major country radio hit.
- **Luke Grimes** sounds_like **Chris Stapleton** *(confidence: medium)* — Grimes' debut album drew critical comparisons to Stapleton-style outlaw country/Americana.
- **Dierks Bentley** sounds_like **Jon Pardi** *(confidence: medium)* — Both established modern neotraditional country mainstays.
- **Granger Smith** sounds_like **Jason Aldean** *(confidence: medium)* — Both mainstream country-rock radio staples appealing to a similar audience.
- **Tory Lanez** sounds_like **PARTYNEXTDOOR** *(confidence: medium)* — Contemporaries in the same moody Toronto R&B scene and era, though on different labels.
- **Weyes Blood** collaborated_with **Drugdealer** *(confidence: high)* — Weyes Blood (Natalie Mering) has appeared on Drugdealer recordings; both are part of the same LA soft-rock-revival circle.
- **Gary Lucas** collaborated_with **Jeff Buckley** *(confidence: high)* — Co-wrote 'Grace' and 'Mojo Pin' with Buckley; the two were bandmates in Gods and Monsters before Buckley's solo career.
