# Transfermarkt Scraper - Complete Documentation

![checks status](https://github.com/dcaribou/transfermarkt-scraper/workflows/Scrapy%20Contracts%20Checks/badge.svg)
![docker build status](https://github.com/dcaribou/transfermarkt-scraper/workflows/Dockerhub%20Image/badge.svg)

A comprehensive web scraper for collecting football/soccer data from [Transfermarkt](https://www.transfermarkt.co.uk/). This Scrapy-based project recursively navigates the Transfermarkt hierarchy to extract structured data about confederations, competitions, clubs, players, games, and individual match appearances.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Spider Reference](#spider-reference)
- [Usage Examples](#usage-examples)
- [Output Data Formats](#output-data-formats)
- [Configuration](#configuration)
- [Docker Usage](#docker-usage)
- [Contributing](#contributing)
- [Additional Documentation](#additional-documentation)

## Overview

The scraper follows Transfermarkt's hierarchical data structure, allowing you to scrape data at any level of granularity:

```
Confederations → Competitions → Clubs → Players → Appearances
                              ↓
                            Games → Game Lineups
```

Key features:
- Modular spider architecture - scrape only what you need
- Streaming JSON Lines output format
- Supports piping between spiders for efficient workflows
- HTTP caching for development
- Season-aware scraping with automatic detection
- Parent-child relationship tracking for data lineage

## Architecture

### Data Flow Hierarchy

The scraper implements a hierarchical approach with two main data flows:

#### 1. Player Statistics Flow
```
confederations → competitions → clubs → players → appearances
```

#### 2. Match Data Flow
```
confederations → competitions → games → game_lineups
```

### Spider Types

1. **Root Spiders** (no input required)
   - `confederations`: Entry point, generates confederation URLs

2. **Hierarchy Spiders** (require parent input)
   - `competitions`: Scrapes league/competition data
   - `clubs`: Scrapes club metadata and squad rosters
   - `players`: Scrapes detailed player profiles
   - `games`: Scrapes match details and events
   - `game_lineups`: Scrapes lineups and formations
   - `appearances`: Scrapes player match statistics

3. **Standalone Spiders** (optional parent input)
   - `clubs_by_url`: Direct club scraping via competition codes
   - `players_from_file`: Direct player scraping via href list

## Installation

This project uses [Poetry](https://python-poetry.org/) for dependency management.

### Prerequisites
- Python 3.8 or higher
- Poetry (install from https://python-poetry.org/docs/)

### Install Dependencies

```bash
cd transfermarkt-scraper
poetry install
poetry shell
```

### User Agent Configuration

**Important:** This scraper requires a user agent string. Configure it in one of two ways:

1. **Via settings file** (recommended):
   Add to `tfmkt/settings.py`:
   ```python
   ROBOTSTXT_USER_AGENT = 'Mozilla/5.0 (Your User Agent)'
   ```

2. **Via command line**:
   ```bash
   scrapy crawl <spider-name> -s USER_AGENT='Mozilla/5.0 (Your User Agent)'
   ```

## Quick Start

### Basic Workflow

```bash
# 1. Generate confederations (root data)
scrapy crawl confederations > confederations.json

# 2. Generate competitions from confederations
scrapy crawl competitions -a parents=confederations.json > competitions.json

# 3. Generate clubs from competitions
scrapy crawl clubs -a parents=competitions.json > clubs.json

# 4. Generate players from clubs
scrapy crawl players -a parents=clubs.json > players.json

# 5. Generate appearances from players (requires season parameter)
scrapy crawl appearances -a parents=players.json -a season=2020 > appearances.json
```

### Piped Workflow (Recommended)

Process data streams without intermediate files:

```bash
# Scrape 2 competitions and their players' appearances for 2020 season
cat competitions.json | head -2 \
  | scrapy crawl clubs \
  | scrapy crawl players \
  | scrapy crawl appearances -a season=2020 > appearances_2020.json
```

### Games Workflow

```bash
# 1. Generate games from competitions
scrapy crawl games -a parents=competitions.json > games.json

# 2. Generate lineups from games
scrapy crawl game_lineups -a parents=games.json > lineups.json
```

### Direct Club Scraping

Scrape specific competitions without full hierarchy:

```bash
# Scrape Champions League and Europa League clubs
scrapy crawl clubs_by_url -a codes="CL,EL" -a kind=cup -a season=2020 > ucl_clubs.json

# Scrape Premier League clubs
scrapy crawl clubs_by_url -a codes="GB1" -a kind=league -a season=2020 > epl_clubs.json
```

## Spider Reference

### 1. Confederations Spider

**Name:** `confederations`

**Purpose:** Root spider that generates confederation URLs (Europe, Americas, Africa, Asia, Oceania)

**Parameters:**
- None (standalone)

**Output:**
```json
{"type": "confederation", "href": "/wettbewerbe/europa"}
```

**Example:**
```bash
scrapy crawl confederations > confederations.json
```

---

### 2. Competitions Spider

**Name:** `competitions`

**Purpose:** Scrapes league and competition data from confederation pages

**Parameters:**
- `parents` (required): File or stdin with confederation objects
- `season` (optional): Season filter

**Key Features:**
- Extracts domestic leagues (filters out cups and super cups)
- Deduplicates by country_id + competition_code
- Classifies competition tiers (first_tier, second_tier, etc.)

**Output Fields:**
- `type`: "competition"
- `country_id`, `country_name`: Country information
- `competition_code`: Transfermarkt code (e.g., "GB1" for Premier League)
- `competition_type`: Tier classification
- `total_clubs`, `total_players`: Competition statistics
- `average_age`, `foreigner_percentage`: Squad demographics
- `total_value`: Combined market value
- `href`: Competition URL

**Example:**
```bash
scrapy crawl competitions -a parents=confederations.json > competitions.json
```

---

### 3. Clubs Spider

**Name:** `clubs`

**Purpose:** Scrapes club metadata and complete squad rosters

**Parameters:**
- `parents` (required): File or stdin with competition objects
- `season` (optional): Target season (auto-detects if not specified)

**Key Features:**
- Auto-detects latest available season
- Extracts comprehensive club metadata
- Includes full squad with embedded player details
- Deduplicates players within squad

**Output Fields:**
- `type`: "club"
- `code`, `name`: Club identifiers
- `total_market_value`: Squad value
- `squad_size`, `average_age`: Squad statistics
- `foreigners_number`, `foreigners_percentage`: Foreign player stats
- `national_team_players`: Count of internationals
- `stadium_name`, `stadium_seats`: Venue information
- `net_transfer_record`: Transfer balance
- `coach_name`: Current manager
- `players`: Array of player objects (see structure below)

**Player Object Structure:**
```json
{
  "player_id": 148455,
  "href": "/ederson/profil/spieler/148455",
  "number": "31",
  "name": "Ederson",
  "position": "Goalkeeper",
  "date_of_birth": "Aug 17, 1993",
  "age": 27,
  "nationality": "Brazil",
  "height": "1,88 m",
  "foot": "left",
  "joined": "Jul 1, 2017",
  "signed_from_href": "/sl-benfica/startseite/verein/294",
  "signed_from_name": "Benfica",
  "contract_expires": "Jun 30, 2026",
  "market_value": "€40.00m"
}
```

**Example:**
```bash
scrapy crawl clubs -a parents=competitions.json -a season=2020 > clubs.json
```

---

### 4. Clubs By URL Spider

**Name:** `clubs_by_url`

**Purpose:** Directly scrapes clubs from competition codes without full hierarchy

**Parameters:**
- `codes` (optional): Comma-separated competition codes (e.g., "CL,EL,UCOL")
- `hrefs` (optional): Comma-separated competition hrefs or absolute URLs
- `kind` (optional): "cup" (default) or "league"
- `season` (optional): Season for participants page

**Key Features:**
- Bypasses confederation/competition hierarchy
- Cup competitions: Uses /teilnehmer/ (participants) page
- League competitions: Uses /plus/ variant
- No parent field in output (standalone)

**Output:** Same as `clubs` spider but without parent field

**Example:**
```bash
# Champions League and Europa League
scrapy crawl clubs_by_url -a codes="CL,EL" -a kind=cup -a season=2020

# Premier League
scrapy crawl clubs_by_url -a codes="GB1" -a kind=league -a season=2020
```

---

### 5. Players Spider

**Name:** `players`

**Purpose:** Scrapes comprehensive player profile data

**Parameters:**
- `parents` (required): File or stdin with club objects (containing players array)

**Key Features:**
- Extracts detailed biographical and career data
- Status detection: active, retired, deceased
- Market value parsing with multiple fallback strategies
- Social media links extraction
- Loan information and contract details

**Output Fields:**
- `type`: "player"
- `name`, `last_name`, `name_in_home_country`: Name variants
- `date_of_birth`, `place_of_birth`, `age`: Biographical data
- `date_of_death`: If deceased
- `height`, `foot`, `citizenship`: Physical attributes
- `position`: Playing position
- `player_agent`: Representation details
- `status`: active/retired/deceased
- `current_club`: Current club reference
- `joined`, `contract_expires`, `contract_option`: Contract info
- `current_market_value`, `highest_market_value`: Valuation
- `on_loan_from`, `contract_there_expires`: Loan details
- `social_media`: Array of social media URLs
- `outfitter`: Boot sponsor
- `image_url`: Profile photo

**Example:**
```bash
scrapy crawl players -a parents=clubs.json > players.json
```

---

### 6. Players From File Spider

**Name:** `players_from_file`

**Purpose:** Scrapes player details from a list of player hrefs (standalone)

**Parameters:**
- `parents` (required): File or stdin with player href objects

**Output:** Same as `players` spider

**Use Case:** Refresh specific player data without re-scraping entire clubs

**Example:**
```bash
# Create file with player hrefs
echo '{"type": "player", "href": "/cristiano-ronaldo/profil/spieler/8198"}' > players_to_update.json
scrapy crawl players_from_file -a parents=players_to_update.json > updated_players.json
```

---

### 7. Games Spider

**Name:** `games`

**Purpose:** Scrapes individual match details, results, and events

**Parameters:**
- `parents` (required): File or stdin with competition objects
- `season` (optional): Season filter

**Key Features:**
- Parses competition fixtures page
- Extracts match metadata and results
- Captures all match events (goals, cards, substitutions)
- ISO date format extraction
- Referee and manager information
- Player lineup extraction (starting XI and substitutes for both teams)
- Extracts player names and profile URLs from formation diagram and bench table

**Output Fields:**
- `type`: "game"
- `game_id`: Transfermarkt game ID
- `home_club`, `away_club`: Club references with positions
- `result`, `halftime_score`: Match scores
- `matchday`: Round/matchday label
- `date`, `date_iso`: Match date (both formats)
- `kickoff_time`: Match start time
- `stadium`, `attendance`: Venue information
- `referee`: Referee details
- `home_manager`, `away_manager`: Manager details
- `events`: Array of match events (see structure below)
- `home_starting_lineup`: Array of 11 starting players (name, href)
- `home_substitutes`: Array of substitute players (name, href)
- `away_starting_lineup`: Array of 11 starting players (name, href)
- `away_substitutes`: Array of substitute players (name, href)

**Event Types:**
- Goals (with assists)
- Substitutions (player in/out)
- Yellow cards
- Second yellow cards
- Red cards
- Penalty shootouts

**Event Structure:**
```json
{
  "type": "Goals",
  "minute": 12,
  "extra": null,
  "player": {"href": "/player-href"},
  "club": {"name": "Manchester City", "href": "/club-href"},
  "action": {
    "result": "1:0",
    "description": "Goal",
    "player_in": {"href": null},
    "player_assist": {"href": "/assist-player-href"}
  }
}
```

**Example:**
```bash
scrapy crawl games -a parents=competitions.json -a season=2020 > games.json
```

---

### 8. Game Lineups Spider

**Name:** `game_lineups`

**Purpose:** Scrapes detailed lineup information including formations and squad details

**Parameters:**
- `parents` (required): File or stdin with game objects

**Key Features:**
- Transforms game URL to lineup URL
- Extracts formations (both from page and calculated)
- Starting XI with full player details
- Substitutes with same details
- Team statistics (foreigners, average age, total market value)

**Output Fields:**
- `type`: "game_lineups"
- `game_id`: Match identifier
- `home_club`, `away_club`: Each contains:
  - `href`: Club URL
  - `formation`: Tactical formation (e.g., "4-3-3")
  - `starting_lineup`: Array of 11 players
  - `substitutes`: Array of substitute players
  - `team_stats`: Aggregated team statistics

**Player Object (in lineup):**
```json
{
  "number": "31",
  "name": "Ederson",
  "href": "/ederson/profil/spieler/148455",
  "team_captain": 0,
  "position": "Goalkeeper",
  "nationality": "Brazil",
  "age": "27",
  "market_value": "€40.00m"
}
```

**Example:**
```bash
scrapy crawl game_lineups -a parents=games.json > lineups.json
```

---

### 9. Appearances Spider

**Name:** `appearances`

**Purpose:** Scrapes player match-by-match statistics (individual appearances)

**Parameters:**
- `parents` (required): File or stdin with player objects
- `season` (required): Season year for statistics

**Key Features:**
- Match-level player statistics
- Multiple competitions per player
- Dynamic column mapping (handles different Transfermarkt labels)
- Filters out "on the bench" and "not in squad" entries

**Output Fields:**
- `type`: "appearance"
- `competition_code`: Competition identifier
- `matchday`: Round/matchday label
- `date`: Match date
- `venue`: "H" (home) or "A" (away)
- `for`: Player's club reference
- `opponent`: Opponent club reference
- `result`: Match result
- `pos`: Position played
- `goals`, `assists`: Performance statistics
- `yellow_cards`, `second_yellow_cards`, `red_cards`: Disciplinary
- `minutes_played`: Time on pitch

**Example:**
```bash
scrapy crawl appearances -a parents=players.json -a season=2020 > appearances.json
```

## Usage Examples

### Example 1: Scrape Specific League

```bash
# Get Premier League competition
echo '{"type": "confederation", "href": "/wettbewerbe/europa"}' \
  | scrapy crawl competitions \
  | grep '"competition_code": "GB1"' \
  | scrapy crawl clubs -a season=2020 > premier_league_clubs.json
```

### Example 2: Get All Players from Top European Leagues

```bash
# Define top leagues
LEAGUES="GB1,ES1,IT1,L1,FR1"  # England, Spain, Italy, Germany, France

# Scrape all clubs and players
scrapy crawl clubs_by_url -a codes="$LEAGUES" -a kind=league -a season=2020 \
  | scrapy crawl players > top_leagues_players.json
```

### Example 3: Scrape Champions League Season

```bash
# Get Champions League 2020/21 season
scrapy crawl clubs_by_url -a codes="CL" -a kind=cup -a season=2020 > ucl_clubs.json

# Get all games
echo '{"type": "competition", "competition_code": "CL", "href": "/uefa-champions-league/startseite/wettbewerb/CL"}' \
  | scrapy crawl games -a season=2020 > ucl_games.json

# Get all lineups
scrapy crawl game_lineups -a parents=ucl_games.json > ucl_lineups.json
```

### Example 4: Update Player Data

```bash
# Extract player hrefs from existing data
jq '{type: "player", href: .href}' old_players.json > player_hrefs.json

# Re-scrape player profiles
scrapy crawl players_from_file -a parents=player_hrefs.json > updated_players.json
```

### Example 5: Get Season Statistics

```bash
# Scrape players and their appearances in one pipeline
cat clubs.json \
  | scrapy crawl players \
  | tee players.json \
  | scrapy crawl appearances -a season=2020 > appearances_2020.json
```

## Output Data Formats

All spiders output JSON Lines format (one JSON object per line) to stdout. This format:
- Enables streaming processing
- Supports piping between spiders
- Works with standard Unix tools (grep, head, tail, etc.)
- Can be easily processed with jq for filtering/transformation

### Sample Output Files

See the `samples/` directory for example outputs from each spider:
- `samples/confederations.json`: Confederation objects
- `samples/competitions.json`: Competition objects
- `samples/clubs.json`: Club and squad data
- `samples/players.json`: Player profiles
- `samples/games.json`: Match details
- `samples/appearances.json`: Player match statistics

## Configuration

### Settings File

Key configurations in `tfmkt/settings.py`:

```python
BOT_NAME = 'tfmkt'
ROBOTSTXT_OBEY = True  # Respects robots.txt
FEED_FORMAT = 'jsonlines'  # Output format
FEED_URI = 'stdout:'  # Output destination
LOG_LEVEL = 'ERROR'  # Logging verbosity
HTTPCACHE_ENABLED = True  # HTTP cache for development
HTTPCACHE_DIR = 'httpcache'  # Cache directory
```

### Common Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `parents` | Input file or stdin with parent objects | `-a parents=clubs.json` |
| `season` | Target season year | `-a season=2020` |
| `codes` | Competition codes (clubs_by_url only) | `-a codes="CL,EL"` |
| `hrefs` | Competition hrefs (clubs_by_url only) | `-a hrefs="/premier-league/..."` |
| `kind` | Competition type (clubs_by_url only) | `-a kind=cup` or `-a kind=league` |

### URL Patterns

Understanding Transfermarkt URL structure:

- **Clubs**: `/club-name/startseite/verein/{ID}/saison_id/{YEAR}`
- **Competitions**: `/competition/startseite/wettbewerb/{CODE}`
- **Players**: `/player-name/profil/spieler/{ID}`
- **Games**: `/spielbericht/index/spielbericht/{ID}`
- **Lineups**: `/aufstellung/spielbericht/{ID}`

## Docker Usage

Pre-built Docker image available at [`dcaribou/transfermarkt-scraper`](https://hub.docker.com/repository/docker/dcaribou/transfermarkt-scraper):

```bash
# Basic usage
docker run \
  -ti -v "$(pwd)":/app \
  dcaribou/transfermarkt-scraper:main \
  scrapy crawl competitions -a parents=samples/confederations.json

# With piping
docker run \
  -ti -v "$(pwd)":/app \
  dcaribou/transfermarkt-scraper:main \
  bash -c "cat samples/competitions.json | head -2 | scrapy crawl clubs"
```

## Spider Relationships and Data Flow

### Visual Representation

```
┌─────────────────┐
│ confederations  │ (Root - No input required)
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  competitions   │ (Input: confederations)
└────────┬────────┘
         │
         ├───────────────────────────────┐
         ↓                               ↓
┌─────────────────┐            ┌─────────────────┐
│     clubs       │            │      games      │
│  (+ players[])  │            └────────┬────────┘
└────────┬────────┘                     │
         │                              ↓
         ↓                     ┌─────────────────┐
┌─────────────────┐            │  game_lineups   │
│     players     │            └─────────────────┘
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  appearances    │ (Requires season parameter)
└─────────────────┘

Standalone Spiders (Can be used independently):
┌─────────────────┐
│ clubs_by_url    │ (Input: codes/hrefs)
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│players_from_file│ (Input: player hrefs)
└─────────────────┘
```

### Input/Output Matrix

| Spider | Input Type | Input Source | Output Type | Output Feeds To |
|--------|-----------|--------------|-------------|-----------------|
| confederations | None | - | confederation | competitions |
| competitions | confederation | confederations | competition | clubs, games |
| clubs | competition | competitions | club (with players[]) | players |
| clubs_by_url | codes/hrefs | Command line | club (with players[]) | players |
| players | club | clubs, clubs_by_url | player | appearances |
| players_from_file | player href | File/stdin | player | appearances |
| games | competition | competitions | game | game_lineups |
| game_lineups | game | games | game_lineups | - |
| appearances | player | players, players_from_file | appearance | - |

### Parent-Child Relationships

Each spider (except root spiders) embeds its parent object in the output for traceability:

```json
{
  "type": "club",
  "name": "Manchester City",
  "parent": {
    "type": "competition",
    "competition_code": "GB1",
    "country_name": "England"
  },
  "players": [...]
}
```

This enables:
- Data lineage tracking
- Filtering and grouping in downstream processing
- Understanding context of scraped data

### Deduplication Strategy

Different spiders implement deduplication at various levels:

1. **Competitions Spider**: Deduplicates by `country_id + competition_code`
2. **Clubs Spider**: Deduplicates players within squad by `player_id`
3. **Other Spiders**: No automatic deduplication (assumes unique parent inputs)

## Data Schema Reference

### Confederation Object

```json
{
  "type": "confederation",
  "href": "/wettbewerbe/europa"
}
```

### Competition Object

```json
{
  "type": "competition",
  "parent": {<confederation>},
  "country_id": "189",
  "country_name": "England",
  "total_clubs": "20",
  "total_players": "523",
  "average_age": "27.2",
  "foreigner_percentage": "69.2%",
  "total_value": "€9.31bn",
  "competition_code": "GB1",
  "competition_type": "first_tier",
  "href": "/premier-league/startseite/wettbewerb/GB1"
}
```

### Club Object

```json
{
  "type": "club",
  "href": "/manchester-city/startseite/verein/281/saison_id/2020",
  "parent": {<competition>},
  "code": "manchester-city",
  "name": "Manchester City",
  "total_market_value": "€1.05bn",
  "squad_size": "25",
  "average_age": "27.2",
  "foreigners_number": "16",
  "foreigners_percentage": "64.0%",
  "national_team_players": "13",
  "stadium_name": "Etihad Stadium",
  "stadium_seats": "53,400 Seats",
  "net_transfer_record": "€-678.50m",
  "coach_name": "Pep Guardiola",
  "players": [{<player_in_squad>}, ...]
}
```

### Player (in Squad) Object

```json
{
  "player_id": 148455,
  "href": "/ederson/profil/spieler/148455",
  "number": "31",
  "name": "Ederson",
  "position": "Goalkeeper",
  "date_of_birth": "Aug 17, 1993",
  "age": 27,
  "nationality": "Brazil",
  "height": "1,88 m",
  "foot": "left",
  "joined": "Jul 1, 2017",
  "signed_from_href": "/sl-benfica/startseite/verein/294",
  "signed_from_name": "Benfica",
  "contract_expires": "Jun 30, 2026",
  "market_value": "€40.00m"
}
```

### Player (Full Profile) Object

```json
{
  "type": "player",
  "href": "/ederson/profil/spieler/148455",
  "parent": {<club>},
  "name": "Ederson",
  "last_name": "Ederson",
  "name_in_home_country": "Ederson Santana de Moraes",
  "date_of_birth": "Aug 17, 1993",
  "place_of_birth": {
    "country": "Brazil",
    "city": "Osasco"
  },
  "age": "27",
  "height": "1,88 m",
  "citizenship": "Brazil",
  "position": "Goalkeeper",
  "player_agent": {
    "href": "/agent-href",
    "name": "Agent Name"
  },
  "image_url": "https://...",
  "status": "active",
  "current_club": {
    "href": "/manchester-city/startseite/verein/281"
  },
  "foot": "left",
  "joined": "Jul 1, 2017",
  "contract_expires": "Jun 30, 2026",
  "contract_option": null,
  "day_of_last_contract_extension": null,
  "outfitter": "Puma",
  "current_market_value": 40000000,
  "highest_market_value": "€45.00m",
  "on_loan_from": null,
  "contract_there_expires": null,
  "social_media": ["https://instagram.com/...", "https://twitter.com/..."],
  "code": "ederson",
  "date_of_death": null
}
```

### Game Object

The Game object includes basic lineup information (player names and profile links). For more detailed lineup data including player positions, market values, and formation details, use the game_lineups spider.

```json
{
  "type": "game",
  "href": "/spielbericht/index/spielbericht/3098550",
  "parent": {<competition>},
  "game_id": 3098550,
  "home_club": {
    "type": "club",
    "href": "/manchester-city/startseite/verein/281"
  },
  "home_club_position": "1st",
  "away_club": {
    "type": "club",
    "href": "/liverpool-fc/startseite/verein/31"
  },
  "away_club_position": "5th",
  "result": "2:1",
  "halftime_score": "1:0",
  "matchday": "13. Matchday",
  "date": "Fri, 12/18/20",
  "date_iso": "2020-12-18",
  "kickoff_time": "3:00 PM",
  "stadium": "Etihad Stadium",
  "attendance": "2,000",
  "referee": {
    "name": "Michael Oliver",
    "href": "/michael-oliver/profil/schiedsrichter/..."
  },
  "home_manager": {
    "name": "Pep Guardiola",
    "href": "/pep-guardiola/profil/trainer/..."
  },
  "away_manager": {
    "name": "Jürgen Klopp",
    "href": "/jurgen-klopp/profil/trainer/..."
  },
  "home_starting_lineup": [
    {
      "name": "Ederson",
      "href": "/ederson/profil/spieler/148455"
    },
    {
      "name": "João Cancelo",
      "href": "/joao-cancelo/profil/spieler/182712"
    }
  ],
  "home_substitutes": [
    {
      "name": "Zack Steffen",
      "href": "/zack-steffen/profil/spieler/193778"
    }
  ],
  "away_starting_lineup": [
    {
      "name": "Alisson",
      "href": "/alisson/profil/spieler/105470"
    }
  ],
  "away_substitutes": [
    {
      "name": "Caoimhin Kelleher",
      "href": "/caoimhin-kelleher/profil/spieler/331130"
    }
  ],
  "events": [{<event>}, ...]
}
```

### Event Object

```json
{
  "type": "Goals",
  "minute": 12,
  "extra": null,
  "player": {"href": "/player-href"},
  "club": {
    "name": "Manchester City",
    "href": "/club-href"
  },
  "action": {
    "result": "1:0",
    "description": "Left-footed shot",
    "player_in": {"href": null},
    "player_assist": {"href": "/assist-player-href"}
  }
}
```

### Game Lineups Object

```json
{
  "type": "game_lineups",
  "parent": {
    "href": "/spielbericht/index/spielbericht/3098550",
    "type": "game"
  },
  "href": "/aufstellung/spielbericht/3098550",
  "game_id": 3098550,
  "home_club": {
    "href": "/club-href",
    "formation": "4-3-3",
    "starting_lineup": [{<lineup_player>}, ...],
    "substitutes": [{<lineup_player>}, ...],
    "team_stats": {
      "foreigners": "16",
      "average_age": "27.2",
      "total_market_value": "€1.05bn"
    }
  },
  "away_club": {
    "href": "/club-href",
    "formation": "4-4-2",
    "starting_lineup": [{<lineup_player>}, ...],
    "substitutes": [{<lineup_player>}, ...],
    "team_stats": {...}
  }
}
```

### Lineup Player Object

```json
{
  "number": "31",
  "name": "Ederson",
  "href": "/ederson/profil/spieler/148455",
  "team_captain": 0,
  "position": "Goalkeeper",
  "nationality": "Brazil",
  "age": "27",
  "market_value": "€40.00m"
}
```

### Appearance Object

```json
{
  "type": "appearance",
  "href": "/player/leistungsdaten/spieler/...",
  "parent": {<player>},
  "competition_code": "GB1",
  "matchday": "13. Matchday",
  "date": "12/18/20",
  "venue": "H",
  "for": {
    "type": "club",
    "href": "/manchester-city/spielplan/verein/281/saison_id/2020"
  },
  "opponent": {
    "type": "club",
    "href": "/liverpool-fc/spielplan/verein/31/saison_id/2020"
  },
  "result": "2:1",
  "pos": "GK",
  "goals": "",
  "assists": "",
  "yellow_cards": "",
  "second_yellow_cards": "",
  "red_cards": "",
  "minutes_played": "90'"
}
```

## Advanced Usage Patterns

### Pattern 1: Incremental Updates

Update only specific entities without re-scraping entire hierarchy:

```bash
# Update specific clubs
echo '{"type": "competition", "href": "/premier-league/startseite/wettbewerb/GB1"}' \
  | scrapy crawl clubs -a season=2021 > clubs_updated.json

# Update specific players
jq -r 'select(.name == "Cristiano Ronaldo") | {type: "player", href: .href}' players.json \
  | scrapy crawl players_from_file > ronaldo_updated.json
```

### Pattern 2: Parallel Scraping

Scrape multiple competitions in parallel:

```bash
# Split competitions into batches
split -l 10 competitions.json comp_batch_

# Process in parallel (GNU parallel required)
parallel -j 4 'cat {} | scrapy crawl clubs > clubs_{#}.json' ::: comp_batch_*
```

### Pattern 3: Filtered Scraping

Use jq to filter input before piping to next spider:

```bash
# Scrape only first-tier competitions
jq 'select(.competition_type == "first_tier")' competitions.json \
  | scrapy crawl clubs > top_tier_clubs.json

# Scrape only clubs with high market value
jq 'select(.total_market_value | contains("bn"))' clubs.json \
  | scrapy crawl players > top_clubs_players.json
```

### Pattern 4: Multi-Season Scraping

Scrape same entities across multiple seasons:

```bash
# Scrape clubs for multiple seasons
for season in 2018 2019 2020 2021; do
  scrapy crawl clubs -a parents=competitions.json -a season=$season > clubs_$season.json
done
```

### Pattern 5: Data Enrichment

Combine data from multiple sources:

```bash
# Get clubs with games and lineups
scrapy crawl clubs -a parents=competitions.json > clubs.json

echo '{"type": "competition", "href": "/premier-league/startseite/wettbewerb/GB1"}' \
  | scrapy crawl games > games.json

scrapy crawl game_lineups -a parents=games.json > lineups.json

# Now you can join clubs.json with lineups.json using player hrefs
```

## Troubleshooting

### Common Issues

**Issue**: Spider fails with "No user agent"
```
Solution: Set USER_AGENT in settings.py or via command line
scrapy crawl spider -s USER_AGENT='Mozilla/5.0 ...'
```

**Issue**: No output produced
```
Solution: Check LOG_LEVEL setting, increase to INFO or DEBUG
scrapy crawl spider -s LOG_LEVEL=INFO
```

**Issue**: HTTP 429 (Too Many Requests)
```
Solution: Reduce concurrent requests and add delays
scrapy crawl spider -s CONCURRENT_REQUESTS=1 -s DOWNLOAD_DELAY=2
```

**Issue**: Scraper extracts outdated data
```
Solution: Clear HTTP cache
rm -rf .scrapy/httpcache/
```

**Issue**: Parent file not found
```
Solution: Use absolute path or check file exists
scrapy crawl clubs -a parents=$(pwd)/competitions.json
```

**Issue**: Season not found
```
Solution: Check available seasons on Transfermarkt, some older seasons may not be available
```

### Debugging Tips

1. **Enable verbose logging:**
   ```bash
   scrapy crawl spider -s LOG_LEVEL=DEBUG
   ```

2. **Test with small samples:**
   ```bash
   cat competitions.json | head -1 | scrapy crawl clubs
   ```

3. **Inspect HTTP cache:**
   ```bash
   ls -lh .scrapy/httpcache/tfmkt/
   ```

4. **Use scrapy shell for interactive debugging:**
   ```bash
   scrapy shell "https://www.transfermarkt.co.uk/..."
   ```

5. **Validate output format:**
   ```bash
   scrapy crawl spider | jq empty
   # If jq returns error, JSON is malformed
   ```

## Performance Optimization

### Caching Strategy

HTTP caching is enabled by default for development. For production:

```python
# Disable cache for fresh data
HTTPCACHE_ENABLED = False

# Or use cache with expiration
HTTPCACHE_EXPIRATION_SECS = 86400  # 24 hours
```

### Concurrency Settings

Adjust based on your needs and respect for the target site:

```python
# In settings.py or via command line
CONCURRENT_REQUESTS = 8  # Default: 16
CONCURRENT_REQUESTS_PER_DOMAIN = 4  # Default: 8
DOWNLOAD_DELAY = 1  # Seconds between requests
```

### Memory Management

For large scrapes, use streaming output:

```bash
# Stream directly to gzipped file
scrapy crawl clubs | gzip > clubs.json.gz

# Process in chunks
scrapy crawl clubs | split -l 1000 - club_chunk_
```

## Data Quality and Validation

### Missing Data Handling

Spiders handle missing data gracefully:
- Optional fields return `null` or empty strings
- Missing parent relationships are logged but don't fail the spider
- Deduplication prevents duplicate entries

### Data Validation

Validate scraped data:

```bash
# Check for required fields
jq 'select(.type and .href)' output.json

# Count items by type
jq -r '.type' output.json | sort | uniq -c

# Find items missing specific fields
jq 'select(.market_value == null or .market_value == "")' players.json
```

### Data Completeness

Check scraping completeness:

```bash
# Count expected vs actual
echo "Expected clubs: $(jq -r '.total_clubs' competitions.json | paste -sd+ | bc)"
echo "Scraped clubs: $(wc -l < clubs.json)"

# Check for errors in logs
scrapy crawl clubs 2>&1 | grep -i error
```

## Contributing

### Development Workflow

1. **Fork and clone:**
   ```bash
   git clone https://github.com/your-username/transfermarkt-scraper
   cd transfermarkt-scraper
   poetry install
   ```

2. **Create feature branch:**
   ```bash
   git checkout -b feature/my-enhancement
   ```

3. **Make changes:**
   - Add/modify spiders in `tfmkt/spiders/`
   - Follow existing code patterns
   - Use base classes (`CommonSpider`, `CommonCompClubSpider`)

4. **Test changes:**
   ```bash
   # Test with sample data
   scrapy crawl your_spider -a parents=samples/sample.json

   # Run scrapy contracts
   scrapy check your_spider
   ```

5. **Commit and push:**
   ```bash
   git add .
   git commit -m "Add feature: ..."
   git push origin feature/my-enhancement
   ```

6. **Create Pull Request:**
   - Describe the enhancement
   - Include sample output
   - Reference related issues

### Code Style

- Follow PEP 8 conventions
- Use meaningful variable names
- Add docstrings to spider classes
- Comment complex XPath/CSS selectors

### Testing

Add scrapy contracts to your spiders:

```python
class MySpider(CommonSpider):
    """
    @url http://www.transfermarkt.co.uk/...
    @returns items 1
    @scrapes type href name
    """
    # Spider implementation
```

Run contracts:
```bash
scrapy check my_spider
```

## Additional Documentation

### Project Files

- `pyproject.toml`: Poetry dependency configuration
- `scrapy.cfg`: Scrapy project configuration
- `tfmkt/settings.py`: Spider settings and configuration
- `tfmkt/utils.py`: Helper functions
- `samples/`: Sample output files
- `projects/`: Detailed project documentation

### Related Projects

- [transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets): Real-world usage generating comprehensive datasets

### External Resources

- [Scrapy Documentation](https://docs.scrapy.org/)
- [Transfermarkt Website](https://www.transfermarkt.co.uk/)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [JSON Lines Format](https://jsonlines.org/)

## License

This project follows the same license as the original repository.

## Acknowledgments

Original project by [dcaribou](https://github.com/dcaribou/transfermarkt-scraper)

Data source: [Transfermarkt](https://www.transfermarkt.co.uk/)

## Version History

- **v0.4.0**: Current version with enhanced games and lineups spiders
- See git history for detailed changes

## Support

For issues, questions, or suggestions:
- Open an issue: [GitHub Issues](https://github.com/dcaribou/transfermarkt-scraper/issues)
- Check existing documentation in `projects/` directory
- Review sample outputs in `samples/` directory
