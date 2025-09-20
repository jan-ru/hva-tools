# EduMundo Statistics Automation

Automated extraction of module and class statistics from HVA EduMundo platform.

## Project Structure

- **`edumundo_stats.py`** - Main application for EduMundo statistics extraction
- **`scraping_utils.py`** - Reusable web scraping utilities (required dependency)

## Setup

1. **Install dependencies:**
   ```bash
   uv venv
   uv add requests beautifulsoup4 playwright
   uv run playwright install chromium
   ```

2. **Start Chrome with remote debugging:**
   ```bash
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --remote-allow-origins="*" --user-data-dir=/tmp/chrome-debug
   ```

3. **Login to EduMundo:**
   - Navigate to the statistics page: `https://hva.myedumundo.com/tutor/course/3053/statistics`
   - Ensure you're logged in and can see the dropdowns

## Usage

### Quick Test (2 classes)
```bash
uv run python edumundo_stats.py quicktest
```
Extracts data for FA1E and FA1A with "Toon alle modules".

### Full Automation (13 classes × 17 modules)
```bash
uv run python edumundo_stats.py automate
```
Extracts data for all class/module combinations (221 total).

### Manual Options
```bash
uv run python edumundo_stats.py
```
Interactive menu with options for setup, data extraction, and analysis.

## Output

**CSV Format:** `automated_stats_YYYYMMDD_HHMMSS.csv`

| Field | Description |
|-------|-------------|
| `extraction_date` | Date of extraction (YYYY-MM-DD) |
| `extraction_time` | Time of extraction (HH:MM:SS) |
| `class_name` | Class name (FA1A, FA1B, etc.) |
| `module_name` | Module name or "Toon alle modules" |
| `time_spent_minutes` | Total time spent in minutes |
| `progress_percentage` | Progress percentage (0-100) |
| `assignments_*` | Assignment completion data |
| `quizzes_*` | Quiz completion data |

## Classes & Modules

**Classes (13):** FA1A, FA1B, FA1C, FA1D, FA1E, FA1F, FA1G, FA1H, FA1I, FA1J, FA1K, FA1L, FA1M

**Modules (17):** Professional Skills & Leercoaching, Wat is een ondernemingsplan?, Bedrijfsomgeving, Onderzoekend vermogen, Belastingrecht I, Belastingrecht II, Financi�le overzichten, Bedrijfsadministratie (BA): Inleiding, BA: Balans, BA: Financi�le Feiten & Boekingsdocumenten, BA: Grootboekrekening, BA: Journaal, BA: Kolommenbalans, BA: BTW, BA: Priv�, BA: Retouren & Kortingen, BA: Voorafgaande Journaalposten

## Requirements

- Chrome browser
- HVA EduMundo access
- Python 3.12+
- Network access to EduMundo platform
- **Both `edumundo_stats.py` and `scraping_utils.py` must be in the same directory**

## Reusable Components

The `scraping_utils.py` module contains reusable components for other scraping projects:

- **`BrowserManager`** - Handles CDP connections to existing browser sessions
- **`SelectorFinder`** - Robust element finding with fallback selectors
- **`PatternExtractor`** - Common data extraction patterns (time, percentages, ratios)
- **`ScrapingSession`** - High-level session manager combining all utilities

These utilities can be imported into other Playwright + BeautifulSoup projects.

## Notes

- Assignment/quiz data may be empty for some class/module combinations
- Each extraction includes timestamp for audit trail
- 0.5 second delay between requests to avoid server overload
- The application has been refactored to use modular, reusable scraping utilities