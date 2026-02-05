# Transfermarkt Scraper - Development Guide

## Project Overview

A Scrapy-based web scraper for collecting football data from Transfermarkt. The scraper follows a hierarchical structure:

```
Confederations → Competitions → Clubs → Players → Appearances
```

## Environment Setup

```bash
# Python version required
python3.9

# Install dependencies
poetry install

# Run any command with poetry
poetry run <command>
```

## Project Structure

```
tfmkt/
├── spiders/
│   ├── common.py              # BaseSpider class with shared utilities
│   ├── common_comp_club.py    # Enhanced base with URL seasonization
│   ├── players.py             # Player details + national career scraping
│   ├── players_from_file.py   # Alternative player spider with file input
│   ├── appearances.py         # Player appearance stats
│   ├── games.py               # Match/game data
│   └── ...
├── settings.py                # Scrapy settings
└── ...
samples/
└── html/                      # Sample HTML files for testing XPath selectors
```

## Spider Synchronization

**IMPORTANT:** The `players.py` and `players_from_file.py` spiders should be kept synchronized with the following understanding:

- **players.py** - Scrapes players from club pages (requires club entrypoint)
  - Has `parse()` method to collect player URLs from club roster
  - Has `parse_details()` method to extract player data

- **players_from_file.py** - Scrapes players directly from URLs (file/stdin input)
  - Has only `parse()` method which is equivalent to `parse_details()` in players.py

**Synchronization Rule:**
- All data extraction logic (XPath selectors, helper methods, parsing logic) should be **identical** between:
  - `players.py::parse_details()` and subsequent methods
  - `players_from_file.py::parse()` and subsequent methods
- When adding features to one spider, port them to the other unless explicitly noted otherwise
- Both spiders should produce the same output structure for the same player URL

**Current synchronized features:**
- Player profile data extraction
- National team career scraping (totals, competitions, matches)
- Market value parsing
- Status detection (active/retired/deceased)
- Error handling with graceful degradation

## Spider Input/Output

Spiders expect input via **stdin** or a **parents file** (JSON lines format):

```bash
# Via stdin
echo '{"type": "club", "href": "/fc-barcelona/startseite/verein/131"}' | poetry run scrapy crawl players -o output.json

# Via parents file
poetry run scrapy crawl players -a parents=clubs.jsonl -o players.json

# Compressed parents file
poetry run scrapy crawl players -a parents=clubs.jsonl.gz -o players.json
```

## Key Code Patterns

### BaseSpider (common.py)
- `__init__(base_url, parents)` - Loads parent entities from stdin or file
- `start_requests()` - Generates initial requests from entrypoints
- `seasonize_entrypoin_href()` - Adds season parameters to URLs
- `safe_strip(word)` - Null-safe string stripping

### Request Chaining
```python
# Chain to next parse method with context
yield response.follow(
    url,
    self.parse_next,
    cb_kwargs={'base': base, 'attributes': attributes},
    errback=self.errback_handler
)
```

### XPath Tips for Transfermarkt
- `colspan` in `<td>` doesn't affect XPath element indexing - `td[N]` counts actual elements
- Tables often have hidden columns: `<td class="hide">`
- Injury/unavailable rows have class `bg_rot_20`
- Result links have class `ergebnis-link` with `greentext`/`redtext` spans

## Testing

### Test XPath Selectors with Sample HTML
```python
from scrapy.http import HtmlResponse, Request

def create_mock_response(html_file, url):
    with open(html_file, 'r', encoding='utf-8') as f:
        body = f.read().encode('utf-8')
    request = Request(url=url)
    return HtmlResponse(url=url, body=body, request=request)

# Use in tests
response = create_mock_response('samples/html/yamal_national.html', 'https://...')
result = response.xpath("//table[@class='items']//tfoot/tr/td[3]/text()").get()
```

### Run Spider Tests
```bash
# Scrapy's built-in contract tests
poetry run scrapy check players

# Test with local HTML (create test script)
poetry run python test_script.py
```

### Sample HTML Files
- `samples/html/yamal.html` - Player profile page
- `samples/html/yamal_national.html` - National career page (extensive)
- `samples/html/casado.html` - Player profile page
- `samples/html/casado_national.html` - National career page (minimal)

## National Career Feature (players.py)

### URL Transformation
```
Profile:         /{player-slug}/profil/spieler/{player_id}
National Career: /{player-slug}/nationalmannschaft/spieler/{player_id}
Specific Team:   /{player-slug}/nationalmannschaft/spieler/{player_id}/verein_id/{team_id}
```

### Request Flow
```
parse_details()
  └── parse_national_career() [gets dropdown + default team stats]
        └── parse_national_team_stats() [for each additional team]
              └── yield final player item
```

### Data Structure
```python
{
  # ... existing player fields ...
  "national_career": [
    {
      "national_team": {
        "id": "3375",
        "name": "Spain",
        "href": "/spain/startseite/verein/3375"
      },
      "totals": {
        "appearances": 23,
        "goals": 6,
        "assists": 12,
        "yellow_cards": 3,
        "second_yellow_cards": 0,
        "red_cards": 0,
        "minutes_played": 1651
      },
      "competitions": [
        {
          "name": "UEFA Nations League",
          "href": "/...",
          "icon_url": "https://...",
          "appearances": 7,
          "goals": 3,
          ...
        }
      ],
      "matches": [
        {
          "competition": "European Qualifiers",
          "competition_href": "/...",
          "matchday": "Group A",
          "date": "08/09/23",
          "venue": "A",
          "team": "Spain",
          "team_href": "/...",
          "opponent": "Georgia",
          "opponent_href": "/...",
          "result": "1:7",
          "result_type": "win",
          "game_id": 3941392,
          "game_href": "/spielbericht/index/spielbericht/3941392",
          "position": "RW",
          "position_full": "Right Winger",
          "goals": 1,
          "assists": 0,
          "yellow_cards": 0,
          "second_yellow_cards": 0,
          "red_cards": 0,
          "minutes_played": 46,
          "unavailable": null  // or "muscular problems" for injuries
        }
      ]
    },
    // ... more teams (U19, U21, etc.)
  ]
}
```

### Key XPath Selectors (National Career Page)

**National Teams Dropdown:**
```xpath
//select[@name='verein_id']/option  → @value=team_id, text()=team_name
//select[@name='verein_id']/option[@selected]  → currently selected
```

**Compact Stats Table:**
```xpath
//table[@class='items']  → main table
.//tfoot/tr/td[3]  → appearances (td[1] has colspan=2)
.//tfoot/tr/td[4]  → goals
.//tbody/tr  → competition rows
```

**Detailed Stats Table:**
```xpath
(//div[@class='responsive-table'])[2]//table/tbody  → matches table
./tr[td[@colspan='20']]  → competition header rows
./tr[@class='bg_rot_20']  → unavailable/injury rows
./td[7]//a/@title  → opponent name
./td[9]/a/text()  → position
./td[15]/text()  → minutes played
```

## Common Issues

### 403 Errors
Transfermarkt blocks requests without proper headers. Solutions:
1. Configure User-Agent in `settings.py`
2. Use proxy rotation
3. Add cookies from browser session

### Poetry Environment Issues
If poetry's venv is corrupted:
```bash
# Remove and reinstall poetry
rm -rf ~/.local/share/pypoetry/venv
curl -sSL https://install.python-poetry.org | python3.9 - --force

# Reinstall project dependencies
poetry install
```

## Debugging

```python
# In any spider method, uncomment to open interactive shell:
from scrapy.shell import inspect_response
inspect_response(response, self)
exit(1)
```
