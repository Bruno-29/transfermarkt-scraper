from tfmkt.spiders.common_comp_club import BaseSpider
import re


class GamesUrlsSpider(BaseSpider):
  """Spider for extracting game URLs and metadata from competition fixtures pages.

  This spider navigates to competition fixtures pages and extracts game URLs along
  with match metadata (date, time, teams, result) without visiting individual game
  pages. This provides a fast way to build rich game inventories for filtering and
  selective scraping with games_by_url.

  Usage:
    scrapy crawl games_urls -a parents=competitions.json
    cat competitions.json | scrapy crawl games_urls > game_urls.json

  Output format (JSON lines):
    {
      "type": "game",
      "href": "/spielbericht/index/spielbericht/3098550",
      "seasoned_href": "https://www.transfermarkt.co.uk/spielbericht/index/spielbericht/3098550",
      "game_id": 3098550,
      "date_iso": "2024-09-26",
      "date_display": "Sep 26, 2024",
      "kickoff_time": "3:00 PM",
      "home_club": {"type": "club", "name": "Arsenal FC", "href": "/arsenal-fc/..."},
      "away_club": {"type": "club", "name": "Liverpool FC", "href": "/liverpool-fc/..."},
      "result": "2:1",
      "parent": {...}
    }

  This spider is approximately 300x faster than the games spider since it only
  makes 1 request per competition instead of visiting every individual game page.
  """

  name = 'games_urls'

  def parse(self, response, parent):
    """Parse competition page and navigate to fixtures page.

    @url https://www.transfermarkt.co.uk/premier-league/startseite/wettbewerb/GB1
    @returns requests 1 1
    @cb_kwargs {"parent": "dummy"}
    @scrapes type href parent
    """
    cb_kwargs = {
      'base': {
        'parent': parent
      }
    }

    footer_links = response.css('div.footer-links')
    for footer_link in footer_links:
      text = footer_link.xpath('a//text()').get().strip()
      if text in [
        "All fixtures & results",
        "All games"
        ]:
        next_url = footer_link.xpath('a/@href').get()

        return response.follow(next_url, self.extract_game_urls, cb_kwargs=cb_kwargs)

  def extract_game_urls(self, response, base):
    """Extract game URLs and metadata from fixtures page without visiting individual games.

    Enhanced to extract match date, time, teams, and results from the fixtures table
    to provide richer game inventory data without additional HTTP requests.

    @url https://www.transfermarkt.co.uk/premier-league/gesamtspielplan/wettbewerb/GB1/saison_id/2020
    @returns items 330 390
    @cb_kwargs {"base": {"href": "some_href", "type": "league", "parent": {}}}
    @scrapes type href seasoned_href parent game_id date_iso date_display kickoff_time home_club away_club result
    """
    # Find all table rows that contain game links
    game_rows = response.xpath('//table//tbody/tr[.//a[@class="ergebnis-link"]]')

    for row in game_rows:
      # Extract game link and ID
      game_link = row.xpath('.//a[@class="ergebnis-link"]')
      href = game_link.xpath('@href').get()

      if not href:
        continue

      # Extract game_id from href pattern: /spielbericht/index/spielbericht/{game_id}
      game_id = int(href.split('/')[-1])

      # Extract date information (ISO format from href)
      date_iso = None
      date_href = row.xpath('.//a[contains(@href, "/datum/")]/@href').get()
      if date_href:
        date_match = re.search(r'/datum/(\d{4}-\d{2}-\d{2})', date_href)
        if date_match:
          date_iso = date_match.group(1)

      # Extract date display format
      date_display = self.safe_strip(
        row.xpath('.//a[contains(@href, "/datum/")]/text()').get()
      )

      # Extract kickoff time
      kickoff_time = self.safe_strip(
        row.xpath('.//td[@class="zentriert hide-for-small"]/text()').get()
      )

      # Extract home team information
      home_team_link = row.xpath('.//td[@class="text-right no-border-rechts hauptlink"]/a')
      home_club = None
      if home_team_link:
        home_name = home_team_link.xpath('@title').get()
        home_href = home_team_link.xpath('@href').get()
        if home_name and home_href:
          home_club = {
            'type': 'club',
            'name': home_name,
            'href': home_href
          }

      # Extract away team information
      away_team_link = row.xpath('.//td[@class="no-border-links hauptlink"]/a')
      away_club = None
      if away_team_link:
        away_name = away_team_link.xpath('@title').get()
        away_href = away_team_link.xpath('@href').get()
        if away_name and away_href:
          away_club = {
            'type': 'club',
            'name': away_name,
            'href': away_href
          }

      # Extract result (may be None for upcoming games)
      result = self.safe_strip(game_link.xpath('text()').get())
      # Normalize empty/upcoming results to None
      if result in ['-:-', '', 'vs']:
        result = None

      # Build full absolute URL for the game
      seasoned_href = f"{self.base_url}{href}"

      # Yield game item with all metadata
      yield {
        'type': 'game',
        'href': href,
        'seasoned_href': seasoned_href,
        'game_id': game_id,
        'date_iso': date_iso,
        'date_display': date_display,
        'kickoff_time': kickoff_time,
        'home_club': home_club,
        'away_club': away_club,
        'result': result,
        'parent': base['parent']
      }
