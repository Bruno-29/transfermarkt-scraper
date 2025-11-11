# Transfermarkt Scraper - API Reference

This document provides a detailed API reference for programmatic and AI client usage of the transfermarkt-scraper package.

## Table of Contents

- [Spider API](#spider-api)
- [Data Contracts](#data-contracts)
- [Input/Output Specifications](#inputoutput-specifications)
- [Error Handling](#error-handling)
- [Integration Examples](#integration-examples)

## Spider API

### Common Interface

All spiders inherit from either `CommonSpider` or `CommonCompClubSpider` and share common patterns:

#### Base Parameters

All spiders (except `confederations`) accept:

```python
# Via command line
-a parents=<file_path_or_stdin>  # Parent objects (JSON Lines format)
-a season=<year>                  # Season year (optional, some spiders auto-detect)
```

#### Return Format

All spiders output JSON Lines format to stdout:
- One JSON object per line
- Each object is a complete, valid JSON document
- Objects are NOT wrapped in an array
- Newline-separated for streaming

Example:
```json
{"type": "club", "name": "Club 1", ...}
{"type": "club", "name": "Club 2", ...}
{"type": "club", "name": "Club 3", ...}
```

### Spider Specifications

---

## 1. Confederations Spider

### Command
```bash
scrapy crawl confederations
```

### Input
None (standalone spider)

### Output Schema
```typescript
interface Confederation {
  type: "confederation";
  href: string;  // Relative URL path
}
```

### Example Output
```json
{"type": "confederation", "href": "/wettbewerbe/europa"}
{"type": "confederation", "href": "/wettbewerbe/amerika"}
{"type": "confederation", "href": "/wettbewerbe/asien"}
{"type": "confederation", "href": "/wettbewerbe/afrika"}
```

### Returns
4 confederation objects (hardcoded list)

---

## 2. Competitions Spider

### Command
```bash
scrapy crawl competitions -a parents=<confederations_file>
```

### Input Schema
```typescript
interface ConfederationInput {
  type: "confederation";
  href: string;
}
```

### Output Schema
```typescript
interface Competition {
  type: "competition";
  parent: Confederation;
  country_id: string;
  country_name: string;
  total_clubs: string;
  total_players: string;
  average_age: string;
  foreigner_percentage: string;
  total_value: string;
  competition_code: string;  // e.g., "GB1", "ES1", "CL"
  competition_type: string;  // e.g., "first_tier", "second_tier"
  href: string;
}
```

### Parameters
- `parents` (required): File or stdin with confederation objects
- `season` (optional): Season filter

### Behavior
- Deduplicates by `country_id + competition_code`
- Filters out cups and super cups
- Focuses on domestic league competitions
- Classifies competition tiers

### Returns
Variable number of competition objects (typically 100-200)

---

## 3. Clubs Spider

### Command
```bash
scrapy crawl clubs -a parents=<competitions_file> [-a season=<year>]
```

### Input Schema
```typescript
interface CompetitionInput {
  type: "competition";
  href: string;
  // Other fields optional
}
```

### Output Schema
```typescript
interface Club {
  type: "club";
  href: string;
  parent: Competition;
  code: string;
  name: string;
  total_market_value: string;
  squad_size: string;
  average_age: string;
  foreigners_number: string;
  foreigners_percentage: string;
  national_team_players: string;
  stadium_name: string;
  stadium_seats: string;
  net_transfer_record: string;
  coach_name: string;
  players: PlayerInSquad[];
}

interface PlayerInSquad {
  player_id: number;
  href: string;
  number: string;
  name: string;
  position: string;
  date_of_birth: string;
  age: number;
  nationality: string;
  height: string;
  foot: string;
  joined: string;
  signed_from_href: string | null;
  signed_from_name: string | null;
  contract_expires: string;
  market_value: string;
}
```

### Parameters
- `parents` (required): File or stdin with competition objects
- `season` (optional): Target season (auto-detects if not specified)

### Behavior
- Auto-detects latest available season if not specified
- Deduplicates players within squad by `player_id`
- Handles variable table column layouts
- Embeds full player roster in `players` array

### Returns
Variable number of club objects (depends on input competitions)

---

## 4. Clubs By URL Spider

### Command
```bash
scrapy crawl clubs_by_url -a codes="<code1>,<code2>" -a kind=<cup|league> [-a season=<year>]
# OR
scrapy crawl clubs_by_url -a hrefs="<href1>,<href2>" -a kind=<cup|league> [-a season=<year>]
```

### Input
Command-line parameters only (no parent file)

### Output Schema
```typescript
interface ClubByUrl {
  type: "club";
  href: string;
  code: string;
  name: string;
  competition_id: string;
  competition_href: string;
  competition_name: string;
  // Same fields as Club but NO parent field
  players: PlayerInSquad[];
}
```

### Parameters
- `codes` (optional): Comma-separated competition codes (e.g., "CL,EL,UCOL")
- `hrefs` (optional): Comma-separated hrefs or absolute URLs
- `kind` (optional): "cup" (default) or "league"
- `season` (optional): Season for participants page

### Behavior
- Bypasses confederation/competition hierarchy
- Cup competitions: Uses `/teilnehmer/` page
- League competitions: Uses `/plus/` variant
- No parent field in output
- Special handling for UEFA U19 teams

### Returns
Variable number of club objects (depends on competition size)

---

## 5. Players Spider

### Command
```bash
scrapy crawl players -a parents=<clubs_file>
```

### Input Schema
```typescript
interface ClubInput {
  type: "club";
  players: Array<{
    href: string;
    // Other fields optional
  }>;
}
```

### Output Schema
```typescript
interface Player {
  type: "player";
  href: string;
  parent: Club;
  name: string;
  last_name: string;
  name_in_home_country: string;
  date_of_birth: string;
  place_of_birth: {
    country: string;
    city: string;
  };
  age: string;
  height: string;
  citizenship: string;
  position: string;
  player_agent: {
    href: string;
    name: string;
  } | null;
  image_url: string;
  status: "active" | "retired" | "deceased";
  current_club: {
    href: string;
  };
  foot: string;
  joined: string;
  contract_expires: string;
  contract_option: string | null;
  day_of_last_contract_extension: string | null;
  outfitter: string;
  current_market_value: number;  // Numeric value in euros
  highest_market_value: string;
  on_loan_from: string | null;
  contract_there_expires: string | null;
  social_media: string[];
  code: string;
  date_of_death: string | null;
}
```

### Parameters
- `parents` (required): File or stdin with club objects (containing players array)

### Behavior
- Extracts players from `players` array in club objects
- Status detection: active, retired, deceased
- Market value parsing with multiple fallback strategies
- Social media links extraction
- Handles loan information

### Returns
Variable number of player objects (sum of all squad sizes)

---

## 6. Players From File Spider

### Command
```bash
scrapy crawl players_from_file -a parents=<player_hrefs_file>
```

### Input Schema
```typescript
interface PlayerHrefInput {
  type: "player";
  href: string;
}
```

### Output Schema
Same as Players Spider (Player interface) but without nested parent structure

### Parameters
- `parents` (required): File or stdin with player href objects

### Behavior
- Standalone player scraping
- Same extraction logic as players spider
- Useful for refreshing specific players

### Returns
Variable number of player objects (one per input href)

---

## 7. Games Spider

### Command
```bash
scrapy crawl games -a parents=<competitions_file> [-a season=<year>]
```

### Input Schema
```typescript
interface CompetitionInput {
  type: "competition";
  href: string;
  // Other fields optional
}
```

### Output Schema
```typescript
interface Game {
  type: "game";
  href: string;
  parent: Competition;
  game_id: number;
  home_club: {
    type: "club";
    href: string;
  };
  home_club_position: string;
  away_club: {
    type: "club";
    href: string;
  };
  away_club_position: string;
  result: string;  // e.g., "2:1"
  halftime_score: string;  // e.g., "1:0"
  matchday: string;
  date: string;  // e.g., "Fri, 12/18/20"
  date_iso: string;  // e.g., "2020-12-18"
  kickoff_time: string;
  stadium: string;
  attendance: string;
  referee: {
    name: string;
    href: string;
  } | null;
  home_manager: {
    name: string;
    href: string;
  } | null;
  away_manager: {
    name: string;
    href: string;
  } | null;
  events: GameEvent[];
  home_starting_lineup: GamePlayer[];  // 11 players
  home_substitutes: GamePlayer[];      // Bench players
  away_starting_lineup: GamePlayer[];  // 11 players
  away_substitutes: GamePlayer[];      // Bench players
}

interface GamePlayer {
  name: string;
  href: string;  // Player profile URL
}

interface GameEvent {
  type: "Goals" | "Substitutions" | "Yellow cards" | "Second yellow cards" | "Red cards" | "Penalty shootout";
  minute: number;
  extra: number | null;  // Extra time minutes
  player: {
    href: string;
  };
  club: {
    name: string;
    href: string;
  };
  action: {
    result: string | null;  // For goals
    description: string;
    player_in: { href: string | null };  // For substitutions
    player_assist: { href: string | null };  // For goals
  };
}
```

### Parameters
- `parents` (required): File or stdin with competition objects
- `season` (optional): Season filter

### Behavior
- Parses competition fixtures page
- Extracts comprehensive match metadata
- ISO date format extraction from URL
- Events extraction (goals, cards, substitutions, shootouts)
- Event timing with extra time support
- Player lineup extraction (starting XI and substitutes for both teams)
- Extracts player names and profile URLs from formation diagram and bench table

### Returns
Variable number of game objects (depends on competition fixtures)

---

## 8. Games URLs Spider

### Command
```bash
scrapy crawl games_urls -a parents=<competitions_file> [-a season=<year>]
```

### Input Schema
```typescript
interface CompetitionInput {
  type: "competition";
  href: string;
  // Other fields optional
}
```

### Output Schema
```typescript
interface GameWithMetadata {
  type: "game";
  href: string;  // e.g., "/spielbericht/index/spielbericht/3426901"
  game_id: number;
  date_iso: string | null;  // ISO format: "YYYY-MM-DD"
  date_display: string | null;  // Human-readable: "22/08/25"
  kickoff_time: string | null;  // e.g., "7:30 PM" (may be null for unscheduled)
  home_club: {
    type: "club";
    name: string;
    href: string;
  } | null;
  away_club: {
    type: "club";
    name: string;
    href: string;
  } | null;
  result: string | null;  // e.g., "6:0" (null for upcoming games)
  parent: Competition;  // Parent competition object
}
```

### Parameters
- `parents` (required): File or stdin with competition objects
- `season` (optional): Season filter

### Behavior
- **Fast metadata extraction**: Navigates to competition fixtures page and extracts rich metadata
- **No game page visits**: Extracts all data from fixtures table without parsing individual games
- **~300x faster**: 1 request per competition vs 300+ for `games` spider
- **Rich filtering capability**: Date, teams, and result data enables pre-filtering
- **Minimal bandwidth**: Only downloads fixtures pages, not game detail pages
- **Direct feed to games_by_url**: Output format compatible with `games_by_url` input

### Use Cases
- Build comprehensive game inventories with metadata quickly
- Discover all available games with schedule and result information
- Pre-filter games by date, teams, or completion status before detailed scraping
- Feed filtered output into `games_by_url` for two-stage scraping workflow
- Rapid game analysis and scheduling insights
- Identify upcoming vs completed games without visiting individual pages

### Returns
Variable number of game objects with metadata (typically 330-390 per competition)

### Example Output
```json
{"type": "game", "href": "/bayern-munich_rb-leipzig/index/spielbericht/4632805", "game_id": 4632805, "date_iso": "2025-08-22", "date_display": "22/08/25", "kickoff_time": "7:30 PM", "home_club": {"type": "club", "name": "Bayern Munich", "href": "/fc-bayern-munchen/spielplan/verein/27/saison_id/2025"}, "away_club": {"type": "club", "name": "RB Leipzig", "href": "/rasenballsport-leipzig/spielplan/verein/23826/saison_id/2025"}, "result": "6:0", "parent": {"type": "competition", "competition_code": "GB1"}}
{"type": "game", "href": "/eintracht-frankfurt_sv-werder-bremen/index/spielbericht/4633376", "game_id": 4633376, "date_iso": "2025-08-23", "date_display": "23/08/25", "kickoff_time": "2:30 PM", "home_club": {"type": "club", "name": "Eintracht Frankfurt", "href": "/eintracht-frankfurt/spielplan/verein/24/saison_id/2025"}, "away_club": {"type": "club", "name": "SV Werder Bremen", "href": "/sv-werder-bremen/spielplan/verein/86/saison_id/2025"}, "result": "4:1", "parent": {"type": "competition", "competition_code": "GB1"}}
```

### Performance Comparison
| Spider | Requests per Competition | Time per Competition | Data Extracted | Use Case |
|--------|-------------------------|---------------------|----------------|----------|
| `games_urls` | 1 | ~2 seconds | URLs + metadata | Fast inventory with filtering |
| `games` | ~330 | ~10 minutes | Full game details | Complete game data |
| `games_urls` → `games_by_url` | 1 + N (selected) | Variable | Filtered full details | Selective detailed scraping |

---

## 9. Games By URL Spider

### Command
```bash
scrapy crawl games_by_url -a parents=<games_file>
```

### Input Schema
```typescript
interface GameInput {
  type: "game";
  href: string;  // Must be /spielbericht/index/spielbericht/<id>
  game_id?: number;  // Optional
  parent?: object;  // Optional parent tracking
}
```

### Output Schema
Identical to `games` spider output schema (see section 7):

```typescript
interface Game {
  type: "game";
  href: string;
  parent: object;  // Passed through from input
  game_id: number;
  home_club: { type: "club"; href: string };
  home_club_position: string;
  away_club: { type: "club"; href: string };
  away_club_position: string;
  result: string;
  halftime_score: string;
  matchday: string;
  date: string;
  date_iso: string;
  kickoff_time: string;
  stadium: string;
  attendance: string;
  referee: { name: string; href: string } | null;
  home_manager: { name: string; href: string } | null;
  away_manager: { name: string; href: string } | null;
  events: GameEvent[];
  home_starting_lineup: GamePlayer[];
  home_substitutes: GamePlayer[];
  away_starting_lineup: GamePlayer[];
  away_substitutes: GamePlayer[];
}
```

### Parameters
- `parents` (required): File or stdin with game objects containing hrefs

### Behavior
- **Bypasses competition hierarchy**: Skips `parse()` and `extract_game_urls()` methods
- **Direct game page scraping**: Creates requests directly to game detail pages
- **Reuses parsing logic**: Uses same `parse_game()` method as `games` spider
- **Cherry-picking support**: Ideal for targeted game updates or specific match selection
- **Parent passthrough**: Maintains any parent object from input for traceability

### Use Cases
- Refresh specific game data without re-scraping entire competitions
- Update recently completed matches from a curated list
- Target high-profile games or specific matchdays
- Process game lists from external sources or APIs
- Re-scrape games with updated/corrected data

### Returns
Variable number of game objects (one per input game)

### Example Input File
```json
{"type": "game", "href": "/spielbericht/index/spielbericht/3426901", "game_id": 3426901}
{"type": "game", "href": "/spielbericht/index/spielbericht/3426916", "game_id": 3426916}
```

---

## 10. Game Lineups Spider

### Command
```bash
scrapy crawl game_lineups -a parents=<games_file>
```

### Input Schema
```typescript
interface GameInput {
  type: "game";
  href: string;  // Must be /spielbericht/index/spielbericht/<id>
  // Other fields optional
}
```

### Output Schema
```typescript
interface GameLineups {
  type: "game_lineups";
  parent: {
    href: string;
    type: "game";
  };
  href: string;  // /aufstellung/spielbericht/<id>
  game_id: number;
  home_club: TeamLineup;
  away_club: TeamLineup;
}

interface TeamLineup {
  href: string;
  formation: string;  // e.g., "4-3-3"
  starting_lineup: LineupPlayer[];  // Length: 11
  substitutes: LineupPlayer[];
  team_stats: {
    foreigners: string;
    average_age: string;
    total_market_value: string;
  };
}

interface LineupPlayer {
  number: string;
  name: string;
  href: string;
  team_captain: number;  // 0 or 1
  position: string;
  nationality: string;
  age: string;
  market_value: string;
}
```

### Parameters
- `parents` (required): File or stdin with game objects

### Behavior
- Transforms game URL to lineup URL (/index → /aufstellung)
- Extracts formation from page and calculates from positions
- Starting lineup always has 11 players
- Substitutes variable length
- Team statistics aggregated

### Returns
Variable number of game lineup objects (one per input game)

---

## 11. Appearances Spider

### Command
```bash
scrapy crawl appearances -a parents=<players_file> -a season=<year>
```

### Input Schema
```typescript
interface PlayerInput {
  type: "player";
  href: string;
  // Other fields optional
}
```

### Output Schema
```typescript
interface Appearance {
  type: "appearance";
  href: string;
  parent: Player;
  competition_code: string;
  matchday: string;
  date: string;
  venue: "H" | "A";  // Home or Away
  for: {
    type: "club";
    href: string;
  };
  opponent: {
    type: "club";
    href: string;
  };
  result: string;
  pos: string;  // Position played
  goals: string;
  assists: string;
  yellow_cards: string;
  second_yellow_cards: string;
  red_cards: string;
  minutes_played: string;
}
```

### Parameters
- `parents` (required): File or stdin with player objects
- `season` (required): Season year for statistics

### Behavior
- Navigates to player's "View full stats" page
- Parses multiple competition tables per player
- Filters out "on the bench" and "not in squad" rows
- Dynamic column header mapping

### Returns
Variable number of appearance objects (depends on player match history)

---

## Data Contracts

### Type Discriminators

All objects have a `type` field for discrimination:

```typescript
type ScraperOutput =
  | Confederation
  | Competition
  | Club
  | Player
  | Game
  | GameLineups
  | Appearance;
```

### Parent-Child Relationships

Objects maintain parent references for lineage:

```typescript
// Hierarchy chain
Confederation
  └─ Competition (parent: Confederation)
      ├─ Club (parent: Competition)
      │   └─ Player (parent: Club)
      │       └─ Appearance (parent: Player)
      └─ Game (parent: Competition)
          └─ GameLineups (parent: Game)
```

### Null Handling

Fields may be `null` when:
- Data not available on source page
- Player is deceased (`date_of_death` present)
- Contract details not disclosed
- Optional relationships (e.g., `player_agent`, `on_loan_from`)

### String Formats

#### Dates
- `date`: Variable format (e.g., "Fri, 12/18/20", "12/18/20")
- `date_iso`: ISO 8601 format "YYYY-MM-DD"
- `date_of_birth`: "Mon DD, YYYY" format

#### URLs
- All `href` fields are relative paths starting with `/`
- Base URL: `https://www.transfermarkt.co.uk`
- Construct full URL: `base_url + href`

#### Money Values
- String format: "€X.XXm", "€X.XXbn"
- Numeric format: Integer in euros (e.g., 40000000 for €40m)

#### Percentages
- String format: "XX.X%"

## Input/Output Specifications

### File Input

Spiders accept three input methods:

1. **File path**
   ```bash
   scrapy crawl spider -a parents=/path/to/file.json
   ```

2. **Stdin pipe**
   ```bash
   cat file.json | scrapy crawl spider
   ```

3. **Gzipped file**
   ```bash
   scrapy crawl spider -a parents=/path/to/file.json.gz
   ```

### Output Redirection

All output goes to stdout by default:

```bash
# Redirect to file
scrapy crawl spider > output.json

# Pipe to another spider
scrapy crawl spider1 | scrapy crawl spider2

# Gzip output
scrapy crawl spider | gzip > output.json.gz

# Filter with jq
scrapy crawl spider | jq 'select(.type == "club")'
```

### JSON Lines Format

Each line is a complete JSON object:

```python
# Python reading
with open('output.json') as f:
    for line in f:
        obj = json.loads(line)
        # Process obj

# Python writing
import json
with open('output.json', 'w') as f:
    for obj in objects:
        f.write(json.dumps(obj) + '\n')
```

```javascript
// JavaScript reading (Node.js)
const fs = require('fs');
const readline = require('readline');

const rl = readline.createInterface({
  input: fs.createReadStream('output.json')
});

rl.on('line', (line) => {
  const obj = JSON.parse(line);
  // Process obj
});
```

```bash
# Shell processing
# Count objects
wc -l < output.json

# Get first 10
head -10 output.json

# Search for field
grep '"competition_code": "GB1"' output.json

# Parse with jq
jq -r '.name' output.json
```

## Error Handling

### Spider Errors

Common error scenarios:

1. **Missing User Agent**
   ```
   Error: No user agent specified
   Solution: Set USER_AGENT in settings.py or via -s USER_AGENT
   ```

2. **Invalid Parent Format**
   ```
   Error: Parent objects must be JSON Lines format
   Solution: Ensure one JSON object per line, not array
   ```

3. **Season Not Available**
   ```
   Warning: Season not found, using latest available
   Solution: Check Transfermarkt for available seasons
   ```

4. **Network Errors**
   ```
   Error: HTTP 429 Too Many Requests
   Solution: Reduce CONCURRENT_REQUESTS, add DOWNLOAD_DELAY
   ```

5. **Parsing Errors**
   ```
   Warning: Field not found, returning null
   Solution: Check if page structure changed, update selectors
   ```

### Validation

Validate output:

```python
import json
import sys

def validate_json_lines(file_path):
    """Validate JSON Lines file."""
    with open(file_path) as f:
        for i, line in enumerate(f, 1):
            try:
                obj = json.loads(line)
                if 'type' not in obj:
                    print(f"Line {i}: Missing 'type' field")
                if 'href' not in obj:
                    print(f"Line {i}: Missing 'href' field")
            except json.JSONDecodeError as e:
                print(f"Line {i}: Invalid JSON - {e}")

validate_json_lines('output.json')
```

### Logging

Control log verbosity:

```bash
# Error only (default)
scrapy crawl spider -s LOG_LEVEL=ERROR

# Include warnings
scrapy crawl spider -s LOG_LEVEL=WARNING

# Include info
scrapy crawl spider -s LOG_LEVEL=INFO

# Full debug
scrapy crawl spider -s LOG_LEVEL=DEBUG
```

## Integration Examples

### Python Integration

```python
import subprocess
import json

def scrape_competitions():
    """Scrape competitions from confederations."""
    # Run confederations spider
    result = subprocess.run(
        ['scrapy', 'crawl', 'confederations'],
        capture_output=True,
        text=True
    )

    # Write confederations to temp file
    with open('temp_confederations.json', 'w') as f:
        f.write(result.stdout)

    # Run competitions spider
    result = subprocess.run(
        ['scrapy', 'crawl', 'competitions',
         '-a', 'parents=temp_confederations.json'],
        capture_output=True,
        text=True
    )

    # Parse competitions
    competitions = []
    for line in result.stdout.split('\n'):
        if line.strip():
            competitions.append(json.loads(line))

    return competitions

def scrape_premier_league_clubs(season=2020):
    """Scrape Premier League clubs for a season."""
    # Create competition object
    competition = {
        "type": "competition",
        "href": "/premier-league/startseite/wettbewerb/GB1"
    }

    # Run clubs spider with pipe
    process = subprocess.Popen(
        ['scrapy', 'crawl', 'clubs', '-a', f'season={season}'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True
    )

    stdout, _ = process.communicate(json.dumps(competition))

    # Parse clubs
    clubs = []
    for line in stdout.split('\n'):
        if line.strip():
            clubs.append(json.loads(line))

    return clubs

def scrape_specific_games(game_ids):
    """Scrape specific games by their IDs."""
    import tempfile

    # Create temp file with game objects
    games_input = []
    for game_id in game_ids:
        games_input.append({
            "type": "game",
            "href": f"/spielbericht/index/spielbericht/{game_id}",
            "game_id": game_id
        })

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        for game in games_input:
            f.write(json.dumps(game) + '\n')
        temp_file = f.name

    # Run games_by_url spider
    result = subprocess.run(
        ['scrapy', 'crawl', 'games_by_url',
         '-a', f'parents={temp_file}'],
        capture_output=True,
        text=True
    )

    # Parse games
    games = []
    for line in result.stdout.split('\n'):
        if line.strip():
            games.append(json.loads(line))

    return games

def scrape_game_urls_fast(competition_code):
    """Extract all game URLs from a competition quickly (no game parsing)."""
    # Create competition object
    competition = {
        "type": "competition",
        "href": f"/{competition_code}/startseite/wettbewerb/{competition_code}"
    }

    # Run games_urls spider
    process = subprocess.Popen(
        ['scrapy', 'crawl', 'games_urls'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True
    )

    stdout, _ = process.communicate(json.dumps(competition))

    # Parse game URLs
    game_urls = []
    for line in stdout.split('\n'):
        if line.strip():
            game_urls.append(json.loads(line))

    return game_urls

def scrape_games_two_stage(competition_code):
    """Two-stage scraping: fast URL extraction, then selective parsing."""
    # Stage 1: Extract all game URLs (fast)
    print("Stage 1: Extracting game URLs...")
    game_urls = scrape_game_urls_fast(competition_code)
    print(f"Found {len(game_urls)} games")

    # Stage 2: Selectively scrape games (e.g., first 10)
    print("Stage 2: Parsing selected games...")
    selected_games = game_urls[:10]

    # Write to temp file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        for game in selected_games:
            f.write(json.dumps(game) + '\n')
        temp_file = f.name

    # Parse selected games
    result = subprocess.run(
        ['scrapy', 'crawl', 'games_by_url',
         '-a', f'parents={temp_file}'],
        capture_output=True,
        text=True
    )

    games = []
    for line in result.stdout.split('\n'):
        if line.strip():
            games.append(json.loads(line))

    return games
```

### Node.js Integration

```javascript
const { spawn } = require('child_process');
const readline = require('readline');

function scrapeCompetitions() {
  return new Promise((resolve, reject) => {
    const confederations = spawn('scrapy', ['crawl', 'confederations']);
    const competitions = spawn('scrapy', ['crawl', 'competitions']);

    // Pipe confederations to competitions
    confederations.stdout.pipe(competitions.stdin);

    const results = [];
    const rl = readline.createInterface({
      input: competitions.stdout
    });

    rl.on('line', (line) => {
      if (line.trim()) {
        results.push(JSON.parse(line));
      }
    });

    rl.on('close', () => resolve(results));
    competitions.on('error', reject);
  });
}

async function scrapeClubsByCode(codes, season = 2020) {
  return new Promise((resolve, reject) => {
    const spider = spawn('scrapy', [
      'crawl', 'clubs_by_url',
      '-a', `codes=${codes}`,
      '-a', 'kind=league',
      '-a', `season=${season}`
    ]);

    const results = [];
    const rl = readline.createInterface({
      input: spider.stdout
    });

    rl.on('line', (line) => {
      if (line.trim()) {
        results.push(JSON.parse(line));
      }
    });

    rl.on('close', () => resolve(results));
    spider.on('error', reject);
  });
}

async function scrapeSpecificGames(gameIds) {
  return new Promise((resolve, reject) => {
    const fs = require('fs');
    const tmpFile = '/tmp/games_input.json';

    // Write game objects to temp file
    const gamesInput = gameIds.map(id => ({
      type: 'game',
      href: `/spielbericht/index/spielbericht/${id}`,
      game_id: id
    }));

    fs.writeFileSync(tmpFile, gamesInput.map(g => JSON.stringify(g)).join('\n'));

    // Run games_by_url spider
    const spider = spawn('scrapy', [
      'crawl', 'games_by_url',
      '-a', `parents=${tmpFile}`
    ]);

    const results = [];
    const rl = readline.createInterface({
      input: spider.stdout
    });

    rl.on('line', (line) => {
      if (line.trim()) {
        results.push(JSON.parse(line));
      }
    });

    rl.on('close', () => {
      fs.unlinkSync(tmpFile);  // Clean up
      resolve(results);
    });

    spider.on('error', reject);
  });
}

async function scrapeGameUrlsFast(competitionCode) {
  return new Promise((resolve, reject) => {
    const competition = {
      type: 'competition',
      href: `/${competitionCode}/startseite/wettbewerb/${competitionCode}`
    };

    const spider = spawn('scrapy', ['crawl', 'games_urls']);

    // Write competition to stdin
    spider.stdin.write(JSON.stringify(competition));
    spider.stdin.end();

    const results = [];
    const rl = readline.createInterface({
      input: spider.stdout
    });

    rl.on('line', (line) => {
      if (line.trim()) {
        results.push(JSON.parse(line));
      }
    });

    rl.on('close', () => resolve(results));
    spider.on('error', reject);
  });
}

async function scrapGamesTwoStage(competitionCode) {
  // Stage 1: Fast URL extraction
  console.log('Stage 1: Extracting game URLs...');
  const gameUrls = await scrapeGameUrlsFast(competitionCode);
  console.log(`Found ${gameUrls.length} games`);

  // Stage 2: Selectively parse games (first 10)
  console.log('Stage 2: Parsing selected games...');
  const selectedGames = gameUrls.slice(0, 10);

  return new Promise((resolve, reject) => {
    const fs = require('fs');
    const tmpFile = '/tmp/selected_games.json';

    // Write selected games to temp file
    fs.writeFileSync(tmpFile, selectedGames.map(g => JSON.stringify(g)).join('\n'));

    // Parse selected games
    const spider = spawn('scrapy', [
      'crawl', 'games_by_url',
      '-a', `parents=${tmpFile}`
    ]);

    const results = [];
    const rl = readline.createInterface({
      input: spider.stdout
    });

    rl.on('line', (line) => {
      if (line.trim()) {
        results.push(JSON.parse(line));
      }
    });

    rl.on('close', () => {
      fs.unlinkSync(tmpFile);  // Clean up
      resolve(results);
    });

    spider.on('error', reject);
  });
}
```

### Shell Script Integration

```bash
#!/bin/bash

# scrape_league.sh - Scrape entire league hierarchy

LEAGUE_CODE=$1
SEASON=$2
OUTPUT_DIR=$3

# Validate inputs
if [ -z "$LEAGUE_CODE" ] || [ -z "$SEASON" ] || [ -z "$OUTPUT_DIR" ]; then
  echo "Usage: $0 <league_code> <season> <output_dir>"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "Scraping clubs for $LEAGUE_CODE season $SEASON..."
scrapy crawl clubs_by_url \
  -a codes="$LEAGUE_CODE" \
  -a kind=league \
  -a season="$SEASON" \
  > "$OUTPUT_DIR/clubs.json"

echo "Scraping players..."
scrapy crawl players \
  -a parents="$OUTPUT_DIR/clubs.json" \
  > "$OUTPUT_DIR/players.json"

echo "Scraping appearances..."
scrapy crawl appearances \
  -a parents="$OUTPUT_DIR/players.json" \
  -a season="$SEASON" \
  > "$OUTPUT_DIR/appearances.json"

echo "Done! Output in $OUTPUT_DIR"
echo "Clubs: $(wc -l < $OUTPUT_DIR/clubs.json)"
echo "Players: $(wc -l < $OUTPUT_DIR/players.json)"
echo "Appearances: $(wc -l < $OUTPUT_DIR/appearances.json)"
```

### REST API Wrapper Example

```python
from flask import Flask, jsonify, request
import subprocess
import json
import tempfile

app = Flask(__name__)

@app.route('/api/clubs/<competition_code>')
def get_clubs(competition_code):
    """API endpoint to get clubs for a competition."""
    season = request.args.get('season', '2020')

    # Run spider
    result = subprocess.run(
        ['scrapy', 'crawl', 'clubs_by_url',
         '-a', f'codes={competition_code}',
         '-a', 'kind=league',
         '-a', f'season={season}'],
        capture_output=True,
        text=True
    )

    # Parse output
    clubs = []
    for line in result.stdout.split('\n'):
        if line.strip():
            clubs.append(json.loads(line))

    return jsonify(clubs)

@app.route('/api/player/<player_id>')
def get_player(player_id):
    """API endpoint to get player details."""
    # Create temp file with player href
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        player_href = {
            "type": "player",
            "href": f"/spieler/profil/spieler/{player_id}"
        }
        f.write(json.dumps(player_href))
        temp_file = f.name

    # Run spider
    result = subprocess.run(
        ['scrapy', 'crawl', 'players_from_file',
         '-a', f'parents={temp_file}'],
        capture_output=True,
        text=True
    )

    # Parse output
    player = None
    for line in result.stdout.split('\n'):
        if line.strip():
            player = json.loads(line)
            break

    return jsonify(player)

if __name__ == '__main__':
    app.run(debug=True)
```

## Best Practices

### 1. Respect Rate Limits
```python
# In settings.py
CONCURRENT_REQUESTS = 4
DOWNLOAD_DELAY = 1
AUTOTHROTTLE_ENABLED = True
```

### 2. Use Caching for Development
```python
# Enable during development
HTTPCACHE_ENABLED = True

# Disable for production
HTTPCACHE_ENABLED = False
```

### 3. Handle Missing Data
```python
import json

def safe_get(obj, key, default=None):
    """Safely get value from object."""
    value = obj.get(key, default)
    return value if value not in [None, '', 'null'] else default

with open('players.json') as f:
    for line in f:
        player = json.loads(line)
        market_value = safe_get(player, 'current_market_value', 0)
        print(f"{player['name']}: €{market_value}")
```

### 4. Validate Output
```bash
# Check JSON validity
jq empty < output.json && echo "Valid JSON Lines"

# Count objects
echo "Total objects: $(wc -l < output.json)"

# Check required fields
jq -r 'select(.type and .href) | .type' output.json | sort | uniq -c
```

### 5. Incremental Processing
```python
def process_in_chunks(file_path, chunk_size=100):
    """Process JSON Lines file in chunks."""
    chunk = []
    with open(file_path) as f:
        for line in f:
            obj = json.loads(line)
            chunk.append(obj)

            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []

        if chunk:
            yield chunk

# Usage
for chunk in process_in_chunks('clubs.json'):
    # Process chunk
    pass
```

## Performance Considerations

### Memory Usage

For large scrapes, process streaming:

```python
# BAD: Loads entire file in memory
with open('clubs.json') as f:
    clubs = [json.loads(line) for line in f]

# GOOD: Processes line by line
with open('clubs.json') as f:
    for line in f:
        club = json.loads(line)
        process_club(club)
```

### Parallel Processing

Process multiple competitions in parallel:

```bash
# GNU parallel
cat competitions.json | parallel -j 4 --pipe \
  'scrapy crawl clubs > clubs_{#}.json'
```

### Output Compression

Save space with compression:

```bash
# Compress during scraping
scrapy crawl clubs | gzip > clubs.json.gz

# Read compressed file
zcat clubs.json.gz | scrapy crawl players
```

## Troubleshooting Reference

| Issue | Cause | Solution |
|-------|-------|----------|
| Empty output | No matching data | Check input, increase LOG_LEVEL |
| JSON parse error | Malformed output | Validate with `jq empty` |
| Spider not found | Typo in spider name | Check `scrapy list` |
| Missing fields | Page structure changed | Update selectors |
| Slow scraping | High concurrency | Reduce CONCURRENT_REQUESTS |
| HTTP 429 | Rate limiting | Add DOWNLOAD_DELAY |
| Memory error | Large dataset | Process in chunks |

## Version Compatibility

- **Python**: 3.8+
- **Scrapy**: 2.11.0+
- **Poetry**: 1.0.0+

## Support and Resources

- GitHub Issues: Report bugs and request features
- Sample Data: See `samples/` directory
- Project Docs: See `projects/` directory
- Main Documentation: See `DOCUMENTATION.md`
