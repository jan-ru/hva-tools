# OPM — Operations

Een AI-toepassing voor het beoordelen van studentopdrachten binnen het vak Operations (OPM). Een AI-agent leest de inleveringen van studentgroepen samen met de bijbehorende rubric en genereert gestructureerde feedback per rubriccriterium.

## Workflow

1. Studentgroepen leveren opdrachten in via Brightspace
2. De docent downloadt de inleveringen en plaatst ze in `submissions/sprint2/{groep-id}/`
3. De AI-agent leest de context, rubric en inleverbestanden en genereert feedback
4. De docent beoordeelt de feedback
5. De docent kopieert relevante feedback terug naar Brightspace

## Projectstructuur

```
_quarto.yml                        # Quarto site-configuratie
index.qmd                          # Beoordelingsprompts met sprint-tabs
werkwijze.qmd                      # Werkwijze (aparte pagina)
styles.css                         # Aangepaste stijlen

sprint-2/                          # Rubrieken per opdracht
  opm-sprint-2-dma/rubric.md
  opm-sprint-2-meetplan-tbv-datacollectie/rubric.md

docs/                              # HTML-output
  huisstijl.html                   # HvA template
  beoordeling.html                 # Gegenereerde Brightspace-pagina (prompts)
  werkwijze.html                   # Gegenereerde Brightspace-pagina (werkwijze)
  instructie.html                  # Standalone instructiepagina

scripts/
  build_brightspace.py             # Combineert Quarto-output + HvA template

submissions/sprint2/               # Inleverbestanden per groep
  FC2E-01/ FC2E-03/ FC2F-01/

feedback/sprint2/                  # AI-gegenereerde feedback (apart van de website)

tests/                             # Property-based tests (pytest)
```

## Drie outputs

1. **Quarto website** (`_site/`) — sprint-tabs met crosstab prompttabel + werkwijze
2. **Brightspace HTML** (`docs/beoordeling.html`, `docs/werkwijze.html`) — HvA huisstijl, CSS-only tabs
3. **Feedback documenten** (`feedback/sprint2/`) — per studentgroep

## Aan de slag

```bash
# Installeer Python-afhankelijkheden
uv sync

# Bekijk de site lokaal
quarto preview

# Genereer Brightspace HTML
quarto render
uv run python scripts/build_brightspace.py

# Draai de tests
uv run pytest
```

## Licentie

[MIT](LICENSE)


## Todo

- [ ] Script om rubrics van Brightspace om te zetten naar Markdown-bestanden zodat de AI-agent ze kan lezen
- [ ] Yellow Belt cursussamenvattingen als context aanbieden aan de AI-agent (bijv. via MCP)
