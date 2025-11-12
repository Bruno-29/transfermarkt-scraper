from tfmkt.spiders.games import GamesSpider


class GamesByUrlSpider(GamesSpider):
  """Spider for directly scraping individual games from a list of game URLs/IDs.

  This spider bypasses the competition hierarchy and allows cherry-picking
  specific games for scraping. It accepts JSON lines input where each line
  contains game information.

  Usage:
    scrapy crawl games_by_url -a parents=games.json
    echo '{"type":"game","href":"/spielbericht/index/spielbericht/3426901"}' | scrapy crawl games_by_url

  Expected input format (JSON lines):
    {"type": "game", "href": "/spielbericht/index/spielbericht/3426901", "game_id": 3426901}
    {"type": "game", "href": "/spielbericht/index/spielbericht/3426916", "game_id": 3426916}

  The spider reuses all parsing logic from GamesSpider.parse_game() to extract
  comprehensive game data including lineups, events, managers, referee, etc.
  """

  name = 'games_by_url'

  def __init__(self, *args, **kwargs):
    """Initialize spider and preserve parent fields from input.

    BaseSpider.__init__() deletes nested parent fields to prevent infinite
    nesting (lines 44-46 in common_comp_club.py). However, for games the
    parent field contains essential competition information that must be
    preserved and passed through to the final output.

    This override saves parent data before calling super().__init__() and
    restores it afterward.
    """
    import json
    import gzip
    import sys

    # Extract parents parameter to determine input source
    parents_file = kwargs.get('parents')
    saved_parent_data = {}

    # Pre-read input to save parent data before BaseSpider deletes it
    if parents_file:
      # Determine if file is gzipped
      extension = parents_file.split(".")[-1]
      is_gzipped = (extension == "gz")

      # Open and read the file
      open_fn = gzip.open if is_gzipped else open
      mode = 'rt' if is_gzipped else 'r'

      with open_fn(parents_file, mode) as f:
        for line in f:
          entry = json.loads(line)
          # Save the nested parent field (competition info) keyed by href
          if entry.get('href') and entry.get('parent'):
            saved_parent_data[entry['href']] = entry['parent']

    elif not sys.stdin.isatty():
      # Handle piped input from stdin
      for line in sys.stdin:
        entry = json.loads(line)
        if entry.get('href') and entry.get('parent'):
          saved_parent_data[entry['href']] = entry['parent']

    # Call parent init (this will load data and delete parent fields)
    super().__init__(*args, **kwargs)

    # Restore parent data to entrypoints
    for entry in self.entrypoints:
      href = entry.get('href')
      if href in saved_parent_data:
        entry['parent'] = saved_parent_data[href]

  def parse(self, response, parent):
    """Parse game page directly from URL.

    Receives game URLs from jsonlines (output of games_urls spider)
    and delegates to parse_game() to extract all game details including
    lineups, events, managers, referee, etc.

    @url https://www.transfermarkt.co.uk/liverpool-fc_afc-bournemouth/index/spielbericht/4625774
    @returns items 1 1
    @cb_kwargs {"parent": {"type": "game", "href": "/liverpool-fc_afc-bournemouth/index/spielbericht/4625774", "game_id": 4625774}}
    @scrapes type href parent game_id result matchday date stadium attendance
    """
    # Reformat parent data to match what parse_game expects
    base = {
      'parent': parent.get('parent', {}),
      'href': parent.get('href')
    }

    # Delegate to parse_game from parent GamesSpider class
    yield from self.parse_game(response, base=base)
