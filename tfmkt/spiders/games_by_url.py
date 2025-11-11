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

  def start_requests(self):
    """Generate requests directly to game pages, skipping competition hierarchy.

    Reads from self.entrypoints (populated by BaseSpider from file or stdin)
    and creates requests that go directly to parse_game().

    @returns requests 1+
    """
    for entry in self.entrypoints:
      # Extract href and any parent info from the entry
      href = entry.get('href')

      if not href:
        self.logger.warning(f"Skipping entry without href: {entry}")
        continue

      # Prepare base kwargs similar to what extract_game_urls would do
      cb_kwargs = {
        'base': {
          'parent': entry.get('parent', {}),
          'href': href
        }
      }

      # Create request directly to parse_game, bypassing parse() and extract_game_urls()
      yield self.make_request(
        href,
        callback=self.parse_game,
        cb_kwargs=cb_kwargs
      )
