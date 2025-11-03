from tfmkt.spiders.common_comp_club import BaseSpider
from scrapy.shell import inspect_response # required for debugging
import re
from tfmkt.utils import background_position_in_px_to_minute

class GamesSpider(BaseSpider):
  name = 'games'

  def parse(self, response, parent):
    """Parse competition page. From this page follow to the games and fixutres page.

    @url https://www.transfermarkt.co.uk/premier-league/startseite/wettbewerb/GB1
    @returns requests 1 1
    @cb_kwargs {"parent": "dummy"}
    @scrapes type href parent
    """

    # uncommenting the two lines below will open a scrapy shell with the context of this request
    # when you run the crawler. this is useful for developing new extractors

    # inspect_response(response, self)
    # exit(1)

    cb_kwargs = {
      'base' : {
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
    """Parse games and fixutres page. From this page follow to each game page.

    @url https://www.transfermarkt.co.uk/premier-league/gesamtspielplan/wettbewerb/GB1/saison_id/2020
    @returns requests 330 390
    @cb_kwargs {"base": {"href": "some_href", "type": "league", "parent": {}}}
    @scrapes type href parent game_id 
    """

    # inspect_response(response, self)
    # exit(1)

    game_links = response.css('a.ergebnis-link')
    for game_link in game_links:
      href = game_link.xpath('@href').get()

      cb_kwargs = {
        'base': {
          'parent': base['parent'],
          'href': href
        }
      }

      yield response.follow(href, self.parse_game, cb_kwargs=cb_kwargs)


  def extract_game_events(self, response, event_type):
    event_elements = response.xpath(
      f"//div[./h2/@class = 'content-box-headline' and normalize-space(./h2/text()) = '{'Penalty shoot-out' if event_type == 'Shootout' else event_type}']//div[@class='sb-aktion']"
    )

    events = []
    for e in event_elements:
      event = {}
      event["type"] = event_type
      if event_type == "Shootout":
        event["minute"] = -1
        extra_minute_text = ''
      else:
        background_position_match = re.match(
          "background-position: ([-+]?[0-9]+)px ([-+]?[0-9]+)px;",
          e.xpath("./div[1]/span[@class='sb-sprite-uhr-klein']/@style").get()
        )
        event["minute"] = background_position_in_px_to_minute(
          int(background_position_match.group(1)),
          int(background_position_match.group(2)),
        )
        extra_minute_text = self.safe_strip(
          e.xpath("./div[1]/span[@class='sb-sprite-uhr-klein']/text()").get()
        )
      if len(extra_minute_text) <= 1:
        extra_minute = None
      else:
        extra_minute = int(extra_minute_text)

      event["extra"] = extra_minute
      event["player"] = {
        "href": e.xpath("./div[@class = 'sb-aktion-spielerbild']/a/@href").get()
      }
      event["club"] = {
        "name": e.xpath("./div[@class = 'sb-aktion-wappen']/a/@title").get(),
        "href": e.xpath("./div[@class = 'sb-aktion-wappen']/a/@href").get()
      }

      action_element = e.xpath("./div[@class = 'sb-aktion-aktion']")
      event["action"] = {
        "result": self.safe_strip(
          e.xpath("./div[@class = 'sb-aktion-spielstand']/b/text()").get()
        ),
        "description": self.safe_strip(
          # goal/card or substitution description
          (" ".join([s.strip() for s in action_element.xpath("./text()").getall()])).strip() 
            or (" ".join(action_element.xpath(".//span[@class = 'sb-aktion-wechsel-aus']/span/text()").getall())).strip()
        ),
        "player_in": {
          "href": action_element.xpath(".//div/a/@href").get()
        },
        "player_assist": {
          "href": action_element.xpath("./a/@href").getall()[1] if len(action_element.xpath("./a/@href").getall()) > 1 else None
        }
      }
      events.append(event)

    return events

  def extract_starting_lineup(self, lineup_section):
    """Extract starting lineup players from the formation section.

    Args:
      lineup_section: A Scrapy Selector for the lineup box (aufstellung-box)

    Returns:
      List of player dictionaries with name and href
    """
    players = []
    player_links = lineup_section.xpath('.//div[@class="formation-player-container"]//span[@class="formation-number-name"]/a')

    for player_link in player_links:
      player_name = self.safe_strip(player_link.xpath('./text()').get())
      player_href = player_link.xpath('./@href').get()

      if player_name and player_href:
        players.append({
          'name': player_name,
          'href': player_href
        })

    return players

  def extract_substitutes(self, lineup_section):
    """Extract substitute players from the bench table.

    Args:
      lineup_section: A Scrapy Selector for the lineup box (aufstellung-box)

    Returns:
      List of player dictionaries with name and href
    """
    players = []
    # Get all rows from the ersatzbank table, excluding the manager row
    player_rows = lineup_section.xpath('.//table[@class="ersatzbank"]/tr[not(contains(@class, "bench-table__tr"))]')

    for row in player_rows:
      player_link = row.xpath('./td[2]/a')
      if player_link:
        player_name = self.safe_strip(player_link.xpath('./@title').get())
        player_href = player_link.xpath('./@href').get()

        if player_name and player_href:
          players.append({
            'name': player_name,
            'href': player_href
          })

    return players

  def parse_game(self, response, base):
    """Parse games and fixutres page. From this page follow to each game page.

    @url https://www.transfermarkt.co.uk/spielbericht/index/spielbericht/3098550
    @returns items 1 1
    @cb_kwargs {"base": {"href": "some_href/3", "type": "league", "parent": {}}}
    @scrapes type href parent game_id result matchday date stadium attendance home_manager away_manager
    """

    # inspect_response(response, self)
    # exit(1)

    game_id = int(base['href'].split('/')[-1])

    game_box = response.css('div.box-content')

    # extract home and away "boxes" attributes
    home_club_box = game_box.css('div.sb-heim')
    away_club_box = game_box.css('div.sb-gast')

    home_club_href = home_club_box.css('a::attr(href)').get()
    away_club_href = away_club_box.css('a::attr(href)').get()

    home_club_position = home_club_box[0].xpath('p/text()').get()
    away_club_position = away_club_box[0].xpath('p/text()').get()

    # extract date and time "box" attributes
    datetime_box = game_box.css('div.sb-spieldaten')[0]

    text_elements = [
      element for element in datetime_box.xpath('p//text()') 
      if len(self.safe_strip(element.get())) > 0
    ]

    matchday = self.safe_strip(text_elements[0].get()).split("  ")[0]
    date = self.safe_strip(datetime_box.xpath('p/a[contains(@href, "datum")]/text()').get())

    # Extract ISO date from href
    date_iso = None
    date_href = datetime_box.xpath('p/a[contains(@href, "datum")]/@href').get()
    if date_href:
      # Extract date from URL like /aktuell/waspassiertheute/aktuell/new/datum/2018-09-26
      date_match = re.search(r'/datum/(\d{4}-\d{2}-\d{2})', date_href)
      if date_match:
        date_iso = date_match.group(1)

    # Extract kick-off time if available
    kickoff_time = None
    for elem in text_elements:
        elem_text = self.safe_strip(elem.get())
        # Look for time pattern like "3:00 PM" or "15:00"
        if re.search(r'\d{1,2}:\d{2}\s*(AM|PM|am|pm)?', elem_text):
            # Extract just the time part
            time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)', elem_text)
            if time_match:
                kickoff_time = time_match.group(1).strip()
                break

    # extract venue "box" attributes
    venue_box = game_box.css('p.sb-zusatzinfos')

    stadium = self.safe_strip(venue_box.xpath('node()')[1].xpath('a/text()').get())
    # Clean attendance format - remove "Attendance: " prefix
    attendance_raw = self.safe_strip(venue_box.xpath('node()')[1].xpath('strong/text()').get())
    attendance = attendance_raw.replace("Attendance: ", "") if attendance_raw else None

    # Extract referee name and href
    referee_element = venue_box.xpath('a[contains(@href, "schiedsrichter")]')
    if referee_element:
      referee_name = self.safe_strip(referee_element.xpath('./@title').get())
      referee_href = referee_element.xpath('./@href').get()
      referee = {
        'name': referee_name,
        'href': referee_href
      } if referee_name else None
    else:
      referee = None

    # extract results "box" attributes
    result_box = game_box.css('div.ergebnis-wrap')

    result = self.safe_strip(result_box.css('div.sb-endstand::text').get())

    # Extract half-time score if available
    halftime_score = None
    # Get all text including text in nested elements like <span>
    halftime_texts = result_box.css('div.sb-halbzeit *::text, div.sb-halbzeit::text').getall()
    if halftime_texts:
      halftime_text = self.safe_strip(''.join(halftime_texts))
      # Extract score pattern like "0:1" or "(0:1)"
      halftime_match = re.search(r'\(?(\d+:\d+)\)?', halftime_text)
      if halftime_match:
        halftime_score = halftime_match.group(1)

    # extract from line-ups "box"
    manager_rows = response.xpath(
        "//tr[(contains(td/b/text(),'Manager')) or (contains(td/div/text(),'Manager'))]/td[2]/a"
      )
    manager_names = [self.safe_strip(row.xpath("./text()").get()) for row in manager_rows]
    manager_hrefs = [row.xpath("./@href").get() for row in manager_rows]

    game_events = (
      self.extract_game_events(response, event_type="Goals") +
      self.extract_game_events(response, event_type="Substitutions") +
      self.extract_game_events(response, event_type="Cards") +
      self.extract_game_events(response, event_type="Shootout")
    )

    # Extract player lineups from both teams
    # Note: Not all lineup sections have consistent class names, so we look for
    # large-6 columns divs that contain formation containers
    lineup_sections = response.xpath('//div[contains(@class, "large-6") and contains(@class, "columns") and .//div[@class="formation-player-container"]]')

    home_starting_lineup = []
    home_substitutes = []
    away_starting_lineup = []
    away_substitutes = []

    if len(lineup_sections) >= 2:
      # First section is home team
      home_starting_lineup = self.extract_starting_lineup(lineup_sections[0])
      home_substitutes = self.extract_substitutes(lineup_sections[0])

      # Second section is away team
      away_starting_lineup = self.extract_starting_lineup(lineup_sections[1])
      away_substitutes = self.extract_substitutes(lineup_sections[1])

    item = {
      **base,
      'type': 'game',
      'game_id': game_id,
      'home_club': {
        'type': 'club',
        'href': home_club_href
      },
      'home_club_position': home_club_position,
      'away_club': {
        'type': 'club',
        'href': away_club_href
      },
      'away_club_position': away_club_position,
      'result': result,
      'halftime_score': halftime_score,
      'matchday': matchday,
      'date': date,
      'date_iso': date_iso,
      'kickoff_time': kickoff_time,
      'stadium': stadium,
      'attendance': attendance,
      'referee': referee,
      'events': game_events,
      'home_starting_lineup': home_starting_lineup,
      'home_substitutes': home_substitutes,
      'away_starting_lineup': away_starting_lineup,
      'away_substitutes': away_substitutes
    }

    if len(manager_names) == 2 and len(manager_hrefs) == 2:
      home_manager_name, away_manager_name = manager_names
      home_manager_href, away_manager_href = manager_hrefs
      item["home_manager"] = {
        'name': home_manager_name,
        'href': home_manager_href
      }
      item["away_manager"] = {
        'name': away_manager_name,
        'href': away_manager_href
      }
    
    yield item
 