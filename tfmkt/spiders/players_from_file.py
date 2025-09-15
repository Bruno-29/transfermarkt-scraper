from tfmkt.spiders.common import BaseSpider
from scrapy.shell import Response
from scrapy.shell import inspect_response # required for debugging
from urllib.parse import unquote, urlparse
import re
import json

class PlayersFromFileSpider(BaseSpider):
  name = 'players_from_file'

  def _extract_date_of_birth(self, response):
    """Safely extract date of birth from birth date element."""
    birth_date_text = response.xpath("//span[@itemprop='birthDate']/text()").get()
    if birth_date_text:
      birth_date_text = birth_date_text.strip()
      if " (" in birth_date_text:
        return birth_date_text.split(" (")[0]
      return birth_date_text
    return None

  def _extract_age(self, response):
    """Safely extract age from birth date element."""
    birth_date_text = response.xpath("//span[@itemprop='birthDate']/text()").get()
    if birth_date_text:
      birth_date_text = birth_date_text.strip()
      if "(" in birth_date_text and ")" in birth_date_text:
        age_part = birth_date_text.split('(')[-1].split(')')[0]
        return age_part
    return None

  def _extract_date_of_death(self, response):
    """Safely extract date of death when present; otherwise return None."""
    death_date_text = response.xpath("//span[normalize-space(text())='Date of death:']/following::span[1]/text()").get()
    if death_date_text:
      death_date_text = death_date_text.strip()
      if " (" in death_date_text:
        return death_date_text.split(" (")[0]
      return death_date_text
    death_date_text_alt = response.xpath("//span[normalize-space(text())='Died on:']/following::span[1]/text()").get()
    if death_date_text_alt:
      death_date_text_alt = death_date_text_alt.strip()
      if " (" in death_date_text_alt:
        return death_date_text_alt.split(" (")[0]
      return death_date_text_alt
    return None

  def parse(self, response, parent):
    """Extract player details from the main page.
    It currently only parses the PLAYER DATA section.

      @url https://www.transfermarkt.co.uk/steven-berghuis/profil/spieler/129554
      @returns items 1 1
      @cb_kwargs {"parent": {"type": "player", "href": "some_href/code", "parent": {}}}
      @scrapes href type parent name last_name number
    """

    # uncommenting the two lines below will open a scrapy shell with the context of this request
    # when you run the crawler. this is useful for developing new extractors

    # inspect_response(response, self)
    # exit(1)

    # parse 'PLAYER DATA' section

    attributes = {"type": "player", "href": parent.get('href')}
    base = parent  # In this spider, parent contains the base data including href

    name_element = response.xpath("//h1[@class='data-header__headline-wrapper']")
    attributes["name"] = self.safe_strip("".join(name_element.xpath("text()").getall()).strip())
    attributes["last_name"] = self.safe_strip(name_element.xpath("strong/text()").get())
    attributes["number"] = self.safe_strip(name_element.xpath("span/text()").get())

    attributes['name_in_home_country'] = response.xpath("//span[text()='Name in home country:']/following::span[1]/text()").get()
    attributes['date_of_birth'] = self._extract_date_of_birth(response)
    attributes['place_of_birth'] = {
      'country': response.xpath("//span[text()='Place of birth:']/following::span[1]/span/img/@title").get(),
      'city': response.xpath("//span[text()='Place of birth:']/following::span[1]/span/text()").get()
    }
    attributes['age'] = self._extract_age(response)
    attributes['height'] = response.xpath("//span[text()='Height:']/following::span[1]/text()").get()
    attributes['citizenship'] = response.xpath("//span[text()='Citizenship:']/following::span[1]/img/@title").get()
    attributes['position'] = self.safe_strip(response.xpath("//span[text()='Position:']/following::span[1]/text()").get())
    
    # The agent name can either be inside the anchor tag, title of the anchor tag or 
    attributes['player_agent'] = {
      'href': response.xpath("//span[text()='Player agent:']/following::span[1]/a/@href").get(),
      'name': response.xpath("//span[text()='Player agent:']/following::span[1]/a/span[@class='cp']/@title").get() or  # Case 1: agent name in title attribute
              response.xpath("//span[text()='Player agent:']/following::span[1]/a/text()").get() or  # Case 2: agent name in <a> text
              response.xpath("//span[text()='Player agent:']/following::span[1]/span/text()").get()  # Case 3: agent name in <span> text without <a>
    }
    attributes['image_url'] = response.xpath("//img[@class='data-header__profile-image']/@src").get()
    # --- STATUS AND CURRENT CLUB ---
    status = 'active'
    date_of_death = self._extract_date_of_death(response)
    if date_of_death:
      status = 'deceased'
      attributes['date_of_death'] = date_of_death

    if status == 'active':
      # Deceased without explicit date: placeholder icon/text/slug in Current club
      current_club_node = response.xpath("//span[normalize-space(text())='Current club:']/following::span[1]")
      deceased_placeholder = False
      if len(current_club_node) > 0:
        icon_alt = current_club_node.xpath(".//img/@alt").get()
        has_title_placeholder = current_club_node.xpath(".//a[@title='---']").get() is not None
        has_text_placeholder = current_club_node.xpath(".//a[normalize-space(text())='---']").get() is not None
        has_slug_placeholder = current_club_node.xpath(".//a[contains(@href,'/-tm/startseite/verein/')]").get() is not None
        deceased_placeholder = (icon_alt == '---') or has_title_placeholder or has_text_placeholder or has_slug_placeholder
      if deceased_placeholder:
        status = 'deceased'

    if status == 'active':
      retired_href = response.xpath("//span[normalize-space(text())='Current club:']/following::span[1]//a[contains(@href,'/retired/')]/@href").get()
      current_club_text = response.xpath("normalize-space(//span[normalize-space(text())='Current club:']/following::span[1])").get()
      if retired_href or (current_club_text and 'retired' in current_club_text.lower()):
        status = 'retired'

    if status in ['retired', 'deceased']:
      attributes['current_club'] = None
    else:
      club_href = response.xpath("(//span[normalize-space(text())='Current club:']/following::span[1]//a[@title and not(contains(@href,'/retired/'))]/@href)[1]").get()
      attributes['current_club'] = {
        'href': club_href
      }
    attributes['status'] = status
    attributes['foot'] = response.xpath("//span[text()='Foot:']/following::span[1]/text()").get()
    attributes['joined'] = response.xpath("//span[text()='Joined:']/following::span[1]/text()").get()
    attributes['contract_expires'] = self.safe_strip(response.xpath("//span[text()='Contract expires:']/following::span[1]/text()").get())
    attributes['day_of_last_contract_extension'] = response.xpath("//span[text()='Date of last contract extension:']/following::span[1]/text()").get()
    attributes['outfitter'] = response.xpath("//span[text()='Outfitter:']/following::span[1]/text()").get()

    # Get the meta description content
    meta_description = self.safe_strip(response.xpath("//meta[@name='description']/@content").get())

    # Use regex to extract the market value (e.g., €25k, €25m) only when `meta_description` contains text
    market_value = None  # default if nothing can be parsed
    if meta_description:
      check_match = re.search(r'Market value: (\€[\d\.]+[km]?)', meta_description)
    else:
      check_match = None

    if check_match:
        market_value_text = check_match.group(1)  # e.g., '€25k'
        
        # Remove the Euro symbol
        market_value_text = market_value_text.replace('€', '').strip()
        
        # Handle the suffix (k = thousand, m = million)
        if 'k' in market_value_text:
            market_value = float(market_value_text.replace('k', '')) * 1000
            
        elif 'm' in market_value_text:
            market_value = float(market_value_text.replace('m', '')) * 1000000
        
        # `market_value` already computed above

    attributes['current_market_value'] = market_value
    attributes['highest_market_value'] = self.safe_strip(response.xpath("//div[@class='tm-player-market-value-development__max-value']/text()").get())

    social_media_value_node = response.xpath("//span[text()='Social-Media:']/following::span[1]")
    if len(social_media_value_node) > 0:
      attributes['social_media'] = []
      for element in social_media_value_node.xpath('div[@class="socialmedia-icons"]/a'):
        href = element.xpath('@href').get()
        attributes['social_media'].append(
          href
        )



    attributes['code'] = unquote(urlparse(base["href"]).path.split("/")[1])

    # --- ON LOAN FROM ---
    attributes['on_loan_from'] = None
    on_loan_from = response.xpath(
        "//span[normalize-space(text())='On loan from:']"
        "/following-sibling::span[1]//a/@href"
    ).get()
    if on_loan_from:
        attributes['on_loan_from'] = on_loan_from.strip()


    # --- CONTRACT OPTION ---
    attributes['contract_option'] = None
    contract_option = response.xpath("//span[text()='Contract option:']/following::span[1]//text()").get()
    if contract_option:
        attributes['contract_option'] = contract_option.strip()

      # --- CONTRACT OPTION ---
    attributes['contract_there_expires'] = None
    contract_there_expires = response.xpath("//span[text()='Contract there expires:']/following::span[1]//text()").get()
    if contract_there_expires:
        attributes['contract_there_expires'] = contract_there_expires.strip()

    yield attributes
