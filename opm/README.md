# OPM — Operationeel Procesmanagement

Een agentische AI-toepassing voor het beoordelen van studentopdrachten binnen het vak Operationeel Procesmanagement (OPM). Een AI-agent leest de inleveringen van studentgroepen samen met de bijbehorende rubric en genereert gestructureerde feedback per rubriccriterium.

## Workflow

1. Studentgroepen leveren opdrachten in via Brightspace
2. De docent downloadt de inleveringen en plaatst ze in `submissions/sprint2/{groep-id}/`
3. De AI-agent leest de rubric en inleverbestanden en genereert feedback
4. De docent beoordeelt de feedback op de statische Quarto-webpagina
5. De docent kopieert relevante feedback terug naar Brightspace

## Projectstructuur

```
_quarto.yml                        # Quarto site-configuratie
index.qmd                          # Startpagina
sprint2.qmd                        # Sprint 2 docentinstructie (prompts & inleveringen)
styles.css                         # Aangepaste stijlen

sprint-2/                          # Rubrieken per opdracht
  opm-sprint-2-dma/rubric.md
  opm-sprint-2-meetplan-tbv-datacollectie/rubric.md

submissions/sprint2/               # Inleverbestanden per groep
  FC2E-01/ FC2E-03/ FC2F-01/

feedback/sprint2/                  # AI-gegenereerde feedback (apart van de website)
  feedback-FC2E-01.md ...

tests/                             # Property-based tests (pytest)
```

## Vereisten

- [Quarto](https://quarto.org/) >= 1.3
- [uv](https://docs.astral.sh/uv/) (Python pakketbeheer)

## Aan de slag

```bash
# Installeer Python-afhankelijkheden
uv sync

# Bekijk de site lokaal
quarto preview

# Draai de tests
uv run pytest
```

## Licentie

[MIT](LICENSE)
