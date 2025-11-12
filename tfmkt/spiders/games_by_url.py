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
