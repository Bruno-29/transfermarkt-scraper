# Player Schema Documentation

This document describes the complete schema for player data returned by the `players` spider, with particular focus on the new `national_career` field.

## Schema Overview

Each player object contains profile information and career statistics. The **new addition** is the `national_career` array which contains international career data for all national teams a player has represented.

---

## Complete Player Object

```typescript
interface Player {
  // === Metadata ===
  type: "player";                    // Always "player"
  href: string;                      // Player profile URL path (e.g., "/lamine-yamal/profil/spieler/937958")
  parent: object;                    // Parent club entity (structure varies)

  // === Basic Information ===
  name: string;                      // Full display name (e.g., "Lamine Yamal")
  last_name: string | null;          // Last name only (e.g., "Yamal")
  number: string | null;             // Jersey number (e.g., "#10")
  code: string;                      // URL-decoded player slug (e.g., "lamine-yamal")
  name_in_home_country: string | null;

  // === Birth & Demographics ===
  date_of_birth: string | null;      // Format: "Jul 13, 2007"
  age: string | null;                // Age in years (e.g., "18")
  place_of_birth: {
    country: string | null;          // Country name (e.g., "Spain")
    city: string | null;             // City name (e.g., "Esplugues de Llobregat")
  };
  citizenship: string | null;        // Primary citizenship (e.g., "Spain")
  date_of_death: string | null;      // Only for deceased players

  // === Physical Attributes ===
  height: string | null;             // Height with unit (e.g., "1,80 m")
  foot: string | null;               // Preferred foot: "right", "left", "both", or null

  // === Career Information ===
  position: string | null;           // Primary position (e.g., "Right Winger")
  status: "active" | "retired" | "deceased";
  current_club: {
    href: string;                    // Club URL path
  } | null;                          // null if retired/deceased

  // === Contract Details ===
  joined: string | null;             // Join date (e.g., "Jul 1, 2023")
  contract_expires: string | null;   // Expiry date (e.g., "Jun 30, 2031")
  day_of_last_contract_extension: string | null;
  on_loan_from: string | null;       // Club URL if on loan
  contract_option: string | null;    // Contract option details
  contract_there_expires: string | null;  // Loan contract expiry

  // === Market Value ===
  current_market_value: number | null;   // Value in euros (e.g., 200000000)
  highest_market_value: string | null;   // Formatted string (e.g., "€200.00m")

  // === Additional Info ===
  player_agent: {
    href: string | null;             // Agent profile URL
    name: string | null;             // Agent name
  };
  image_url: string | null;          // Profile image URL
  outfitter: string | null;          // Equipment sponsor (e.g., "Nike")
  social_media: string[] | undefined; // Array of social media URLs

  // === NEW: National Career ===
  national_career: NationalTeamCareer[];  // Array of career entries per national team
}
```

---

## National Career Schema (NEW)

The `national_career` field is an **array** containing one entry for each national team the player has represented. This includes senior teams and youth teams (U21, U19, U17, etc.).

### Key Characteristics

| Property | Description |
|----------|-------------|
| **Type** | `NationalTeamCareer[]` (array) |
| **Empty State** | `[]` (empty array) if player has no international career |
| **Ordering** | Senior team first (if exists), then youth teams in dropdown order |
| **Requests** | One HTTP request per national team to fetch data |

### NationalTeamCareer Object

```typescript
interface NationalTeamCareer {
  national_team: NationalTeam;       // Team identification
  totals: CareerTotals | null;       // Aggregated career statistics
  competitions: CompetitionStats[];  // Per-competition breakdown
  matches: MatchRecord[];            // Individual match records
}
```

---

## National Team Object

```typescript
interface NationalTeam {
  id: string;      // Transfermarkt team ID (e.g., "3375")
  name: string;    // Team name (e.g., "Spain", "Spain U21", "Spain U19")
  href: string;    // Team page URL path (e.g., "/spain/startseite/verein/3375")
}
```

### Example Values

| id | name | href |
|----|------|------|
| `"3375"` | `"Spain"` | `"/spain/startseite/verein/3375"` |
| `"9567"` | `"Spain U21"` | `"/spain-u21/startseite/verein/9567"` |
| `"12609"` | `"Spain U19"` | `"/spain-u19/startseite/verein/12609"` |
| `"12395"` | `"Spain U17"` | `"/spain-u17/startseite/verein/12395"` |

---

## Career Totals Object

Aggregated statistics across all matches for a specific national team.

```typescript
interface CareerTotals {
  appearances: number;         // Total matches played (integer >= 0)
  goals: number;               // Total goals scored (integer >= 0)
  assists: number;             // Total assists (integer >= 0)
  yellow_cards: number;        // Total yellow cards (integer >= 0)
  second_yellow_cards: number; // Total second yellows (integer >= 0)
  red_cards: number;           // Total red cards (integer >= 0)
  minutes_played: number;      // Total minutes on pitch (integer >= 0)
}
```

### Example

```json
{
  "appearances": 23,
  "goals": 6,
  "assists": 12,
  "yellow_cards": 3,
  "second_yellow_cards": 0,
  "red_cards": 0,
  "minutes_played": 1651
}
```

### Notes
- All values are **integers** (not strings)
- Minimum value is `0` (never negative)
- `null` is returned for `totals` only if the stats table doesn't exist on the page

---

## Competition Stats Object

Per-competition aggregated statistics.

```typescript
interface CompetitionStats {
  name: string | null;         // Competition name (e.g., "UEFA Nations League")
  href: string | null;         // Competition URL path
  icon_url: string | null;     // Competition logo URL
  appearances: number;         // Matches in this competition
  goals: number;
  assists: number;
  yellow_cards: number;
  second_yellow_cards: number;
  red_cards: number;
  minutes_played: number;
}
```

### Example

```json
{
  "name": "UEFA Nations League",
  "href": "/uefa-nations-league-a/startseite/pokalwettbewerb/UNLA",
  "icon_url": "https://tmssl.akamaized.net//images/logo/tiny/unla.png?lm=1512858223",
  "appearances": 7,
  "goals": 3,
  "assists": 1,
  "yellow_cards": 2,
  "second_yellow_cards": 0,
  "red_cards": 0,
  "minutes_played": 606
}
```

### Common Competition Names
- `"UEFA Euro"`
- `"UEFA Nations League"`
- `"European Qualifiers"`
- `"World Cup qualification"`
- `"International Friendlies"`
- `"FIFA World Cup"`
- `"Copa America"`
- `"UEFA U21 Championship"`

---

## Match Record Object

Individual match details with performance statistics.

```typescript
interface MatchRecord {
  // === Match Identification ===
  competition: string | null;        // Competition name
  competition_href: string | null;   // Competition URL with season
  game_id: number | null;            // Unique match ID (integer)
  game_href: string | null;          // Match report URL path

  // === Match Details ===
  matchday: string | null;           // Round/matchday (e.g., "Group A", "Round of 16", "Final")
  date: string | null;               // Match date (format: "DD/MM/YY", e.g., "08/09/23")
  venue: string | null;              // "H" (home), "A" (away), or null

  // === Teams ===
  team: string | null;               // Player's national team name
  team_href: string | null;          // Team URL with season
  opponent: string | null;           // Opponent team name
  opponent_href: string | null;      // Opponent URL with season

  // === Result ===
  result: string | null;             // Score (e.g., "1:7", "3:0", "2:2")
  result_type: "win" | "loss" | "draw";  // Match outcome for player's team

  // === Player Performance (when played) ===
  position: string | null;           // Position code (e.g., "RW", "DM", "CF")
  position_full: string | null;      // Full position name (e.g., "Right Winger")
  goals: number;                     // Goals scored in match
  assists: number;                   // Assists in match
  yellow_cards: number;              // Yellow cards received (0 or 1)
  second_yellow_cards: number;       // Second yellow (0 or 1)
  red_cards: number;                 // Direct red cards (0 or 1)
  minutes_played: number;            // Minutes on pitch

  // === Unavailability ===
  unavailable: string | null;        // Reason if didn't play, null if played
}
```

### Match States

A match can be in one of two states:

#### 1. Player Participated
```json
{
  "competition": "European Qualifiers",
  "matchday": "Group A",
  "date": "08/09/23",
  "venue": "A",
  "team": "Spain",
  "opponent": "Georgia",
  "result": "1:7",
  "result_type": "win",
  "game_id": 3941392,
  "position": "RW",
  "position_full": "Right Winger",
  "goals": 1,
  "assists": 0,
  "yellow_cards": 0,
  "second_yellow_cards": 0,
  "red_cards": 0,
  "minutes_played": 46,
  "unavailable": null
}
```

#### 2. Player Unavailable (injury, suspension, etc.)
```json
{
  "competition": "European Qualifiers",
  "matchday": "Group A",
  "date": "12/10/23",
  "venue": "H",
  "team": "Spain",
  "opponent": "Scotland",
  "result": "2:0",
  "result_type": "win",
  "game_id": 3941386,
  "position": null,
  "position_full": null,
  "goals": 0,
  "assists": 0,
  "yellow_cards": 0,
  "second_yellow_cards": 0,
  "red_cards": 0,
  "minutes_played": 0,
  "unavailable": "muscular problems"
}
```

### Unavailability Reasons

Common values for the `unavailable` field:

| Value | Description |
|-------|-------------|
| `null` | Player participated in the match |
| `"muscular problems"` | Muscle injury |
| `"strain"` | Muscle strain |
| `"Ankle injury"` | Ankle injury |
| `"Groin problems"` | Groin injury |
| `"Pubalgia"` | Pubic bone inflammation |
| `"Knee injury"` | Knee injury |
| `"suspended"` | Suspended due to cards |
| `"on the bench"` | In squad but didn't play |

### Position Codes

Common position abbreviations:

| Code | Full Name |
|------|-----------|
| `"GK"` | Goalkeeper |
| `"CB"` | Centre-Back |
| `"LB"` | Left-Back |
| `"RB"` | Right-Back |
| `"DM"` | Defensive Midfield |
| `"CM"` | Central Midfield |
| `"AM"` | Attacking Midfield |
| `"LM"` | Left Midfield |
| `"RM"` | Right Midfield |
| `"LW"` | Left Winger |
| `"RW"` | Right Winger |
| `"CF"` | Centre-Forward |
| `"SS"` | Second Striker |

### Result Type Logic

The `result_type` is determined by the score and which team the player represents:

- `"win"`: Player's team scored more goals
- `"loss"`: Player's team scored fewer goals
- `"draw"`: Equal score

**Note**: For away matches where score shows `"1:7"`, if the player's team (Spain) is the away team and scored 7, this is a `"win"`.

---

## Complete Example

```json
{
  "type": "player",
  "href": "/lamine-yamal/profil/spieler/937958",
  "parent": { "type": "club", "href": "/fc-barcelona/startseite/verein/131" },
  "name": "Lamine Yamal",
  "last_name": "Yamal",
  "number": "#10",
  "code": "lamine-yamal",
  "date_of_birth": "Jul 13, 2007",
  "age": "18",
  "place_of_birth": {
    "country": "Spain",
    "city": "Esplugues de Llobregat"
  },
  "citizenship": "Spain",
  "height": "1,80 m",
  "foot": "left",
  "position": "Right Winger",
  "status": "active",
  "current_club": { "href": "/fc-barcelona/startseite/verein/131" },
  "current_market_value": 200000000,
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
          "href": "/uefa-nations-league-a/startseite/pokalwettbewerb/UNLA",
          "icon_url": "https://tmssl.akamaized.net//images/logo/tiny/unla.png",
          "appearances": 7,
          "goals": 3,
          "assists": 1,
          "yellow_cards": 2,
          "second_yellow_cards": 0,
          "red_cards": 0,
          "minutes_played": 606
        }
      ],
      "matches": [
        {
          "competition": "European Qualifiers",
          "competition_href": "/european-qualifiers/startseite/pokalwettbewerb/EMQ/saison_id/2022",
          "matchday": "Group A",
          "date": "08/09/23",
          "venue": "A",
          "team": "Spain",
          "team_href": "/spanien/spielplan/verein/3375/saison_id/2022",
          "opponent": "Georgia",
          "opponent_href": "/georgien/spielplan/verein/3669/saison_id/2022",
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
          "unavailable": null
        }
      ]
    },
    {
      "national_team": {
        "id": "12609",
        "name": "Spain U19",
        "href": "/spain-u19/startseite/verein/12609"
      },
      "totals": {
        "appearances": 5,
        "goals": 2,
        "assists": 3,
        "yellow_cards": 0,
        "second_yellow_cards": 0,
        "red_cards": 0,
        "minutes_played": 380
      },
      "competitions": [],
      "matches": []
    }
  ]
}
```

---

## Edge Cases

### Player with No International Career
```json
{
  "national_career": []
}
```

### Player with Only Youth Teams
```json
{
  "national_career": [
    {
      "national_team": { "id": "9567", "name": "Spain U21", "href": "..." },
      "totals": { ... },
      "competitions": [ ... ],
      "matches": [ ... ]
    }
  ]
}
```

### Match Where Player Was on Bench
```json
{
  "position": null,
  "minutes_played": 0,
  "unavailable": "on the bench"
}
```

### Failed to Fetch National Career (Network Error)
```json
{
  "national_career": []
}
```
The spider gracefully degrades and returns an empty array if fetching fails.

---

## Data Type Summary

| Field | Type | Nullable |
|-------|------|----------|
| `national_career` | `array` | No (empty array `[]` if none) |
| `national_team.id` | `string` | No |
| `national_team.name` | `string` | No |
| `totals` | `object` | Yes (null if no table) |
| `totals.*` | `number` | No (integer >= 0) |
| `competitions` | `array` | No (can be empty) |
| `matches` | `array` | No (can be empty) |
| `match.game_id` | `number` | Yes |
| `match.result_type` | `string` | No (always one of three values) |
| `match.unavailable` | `string` | Yes (null if played) |
| `match.position` | `string` | Yes (null if unavailable) |
| `match.goals` etc. | `number` | No (integer >= 0) |
