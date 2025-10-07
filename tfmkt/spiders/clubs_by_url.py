from urllib.parse import urlparse
from typing import List, Dict, Optional
import re

from tfmkt.spiders.clubs import ClubsSpider
from scrapy import Request


class ClubsByUrlSpider(ClubsSpider):
    name = 'clubs_by_url'

    def __init__(self, base_url=None, parents=None, codes: Optional[str] = None, hrefs: Optional[str] = None, kind: str = 'cup'):
        """
        Spider to scrape clubs from given competition URLs or codes, without
        associating the resulting club items to any competition parent.

        - codes: comma-separated competition codes (e.g. "CL,EL,ECLQ").
        - hrefs: comma-separated competition href paths or absolute URLs.
        - kind: 'cup' (default, uses 'pokalwettbewerb') or 'league' (uses 'wettbewerb').
        """
        self._input_codes = [c.strip() for c in codes.split(',')] if codes else []
        self._input_hrefs = [h.strip() for h in hrefs.split(',')] if hrefs else []
        self._kind = (kind or 'cup').strip().lower()

        # Call Base init last so that scrape_parents can use the fields above
        super().__init__(base_url=base_url, parents=parents)
        try:
            self.logger.info(
                "clubs_by_url initialized: kind=%s, codes=%d, hrefs=%d",
                self._kind,
                len(self._input_codes),
                len(self._input_hrefs)
            )
            if self._input_codes:
                self.logger.debug("codes: %s", ",".join(self._input_codes))
            if self._input_hrefs:
                self.logger.debug("hrefs(raw): %s", ",".join(self._input_hrefs))
        except Exception:
            pass

    def _normalize_href(self, href: str) -> str:
        """Return a site-relative href beginning with '/'. Accepts absolute URLs too."""
        if not href:
            return href
        if href.startswith('http://') or href.startswith('https://'):
            parsed = urlparse(href)
            normalized = parsed.path.rstrip('/')
        else:
            normalized = href.rstrip('/')
        if normalized != href:
            try:
                self.logger.debug("normalize_href: %s -> %s", href, normalized)
            except Exception:
                pass
        return normalized

    def _hrefs_from_codes(self, codes: List[str]) -> List[str]:
        base_segment = 'pokalwettbewerb' if self._kind == 'cup' else 'wettbewerb'
        # Prefer minimal canonical path that Transfermarkt accepts; slug is optional
        hrefs = [f"/startseite/{base_segment}/{code}" for code in codes if code]
        try:
            self.logger.info(
                "Resolved %d code(s) to hrefs (kind=%s)",
                len(hrefs),
                self._kind
            )
            self.logger.debug("hrefs(from codes): %s", ",".join(hrefs))
        except Exception:
            pass
        return hrefs

    def scrape_parents(self) -> List[Dict]:
        hrefs_from_codes = self._hrefs_from_codes(self._input_codes) if self._input_codes else []
        normalized_hrefs = [self._normalize_href(h) for h in self._input_hrefs]
        entry_hrefs = [h for h in [*hrefs_from_codes, *normalized_hrefs] if h]

        if not entry_hrefs:
            raise Exception("Please provide either 'codes' or 'hrefs' to clubs_by_url spider")
        try:
            self.logger.info(
                "Prepared %d competition entrypoint(s) (codes=%d, hrefs=%d)",
                len(entry_hrefs),
                len(hrefs_from_codes),
                len(normalized_hrefs)
            )
            self.logger.debug("entry_hrefs: %s", ",".join(entry_hrefs))
        except Exception:
            pass
        return [
            {
                'type': 'competition',
                'href': href
            }
            for href in entry_hrefs
        ]

    def _build_competition_url(self, href: str) -> str:
        """Build the correct request URL for a competition entrypoint.
        For cups, navigate to the participants page; for leagues, ensure plus/ variant.
        Append saison_id when a season is provided.
        """
        path = self._normalize_href(href)
        is_cup = self._kind == 'cup' or ('/pokalwettbewerb/' in path)

        if is_cup:
            # Transform to participants path for cups
            original_path = path
            if '/teilnehmer/' not in path:
                if '/startseite/' in path:
                    path = path.replace('/startseite/', '/teilnehmer/')
                elif '/plus/' in path:
                    path = path.replace('/plus/', '/teilnehmer/')
                elif '/pokalwettbewerb/' in path and '/teilnehmer/pokalwettbewerb/' not in path:
                    path = path.replace('/pokalwettbewerb/', '/teilnehmer/pokalwettbewerb/')
            # Add saison_id if provided
            try:
                season_val = getattr(self, 'season', None)
                if season_val:
                    path = re.sub(r'/saison_id/\d+', '', path).rstrip('/')
                    path = f"{path}/saison_id/{int(season_val)}"
            except Exception:
                pass
            try:
                if path != original_path:
                    self.logger.info("Cup URL adjusted: %s -> %s", original_path, path)
            except Exception:
                pass
            return f"{self.base_url}{path}"
        else:
            # League: ensure plus variant
            if '/plus/' not in path:
                path = path.rstrip('/') + '/plus/'
            return f"{self.base_url}{path}"

    def start_requests(self):
        items: List[Dict] = []
        for item in self.entrypoints:
            url = self._build_competition_url(item['href'])
            item['seasoned_href'] = url
            try:
                self.logger.info("Start request prepared: %s", url)
            except Exception:
                pass
            items.append(item)

        return [
            Request(
                item['seasoned_href'],
                cb_kwargs={'parent': item}
            )
            for item in items
        ]

    def parse_details(self, response, base):
        """
        Override to remove competition association from the yielded club items.
        Reuses the original ClubsSpider.parse_details implementation with a final
        step that drops the 'parent' field.
        """
        # -- Begin: inline copy of ClubsSpider.parse_details with final cleanup --
        safe = self.safe_strip
        try:
            self.logger.info(
                "Parsing club details: response_url=%s base_href=%s",
                response.url,
                base.get('href')
            )
        except Exception:
            pass
        attributes = {}

        attributes['total_market_value'] = response.css('div.dataMarktwert a::text').get()

        attributes['squad_size'] = self.safe_strip(
            response.xpath("//li[contains(text(),'Squad size:')]/span/text()").get()
        )
        attributes['average_age'] = self.safe_strip(
            response.xpath("//li[contains(text(),'Average age:')]/span/text()").get()
        )

        foreigners_li = response.xpath("//li[contains(text(),'Foreigners:')]")
        if foreigners_li:
            attributes['foreigners_number'] = self.safe_strip(foreigners_li[0].xpath("span/a/text()").get())
            attributes['foreigners_percentage'] = self.safe_strip(
                foreigners_li[0].xpath("span/span/text()").get()
            )
        else:
            attributes['foreigners_number'] = None
            attributes['foreigners_percentage'] = None

        attributes['national_team_players'] = self.safe_strip(
            response.xpath("//li[contains(text(),'National team players:')]/span/a/text()").get()
        )

        stadium_li = response.xpath("//li[contains(text(),'Stadium:')]")
        if stadium_li:
            attributes['stadium_name'] = self.safe_strip(stadium_li[0].xpath("span/a/text()").get())
            attributes['stadium_seats'] = self.safe_strip(stadium_li[0].xpath("span/span/text()").get())
        else:
            attributes['stadium_name'] = None
            attributes['stadium_seats'] = None

        attributes['net_transfer_record'] = self.safe_strip(
            response.xpath("//li[contains(text(),'Current transfer record:')]/span/span/a/text()").get()
        )
        coach_name = response.xpath('//div[contains(@data-viewport, "Mitarbeiter")]//div[@class="container-hauptinfo"]/a/text()').get()
        attributes['coach_name'] = coach_name.strip() if coach_name else None

        from urllib.parse import unquote, urlparse as _urlparse
        attributes['code'] = unquote(_urlparse(base["href"]).path.split("/")[1])
        name_val = response.xpath("//span[@itemprop='legalName']/text()").get() or \
                   response.xpath('//h1[contains(@class,"data-header__headline-wrapper")]/text()').get()
        attributes['name'] = self.safe_strip(name_val)

        for key, value in attributes.items():
            if isinstance(value, str):
                attributes[key] = value.strip()

        seen_player_ids: set[int] = set()

        def parse_player_row(tr):
            link = tr.css("td.posrela a[href*='/profil/spieler/']::attr(href)").get()
            if not link:
                return None

            tds = tr.css("td")
            if len(tds) < 10:
                return None

            import re as _re
            m_id = _re.search(r"/spieler/(\d+)", link)
            if not m_id:
                return None
            pid = int(m_id.group(1))

            if pid in seen_player_ids:
                return None
            seen_player_ids.add(pid)

            tds = tr.css("td")
            number   = safe(tds[0].css("div.rn_nummer::text").get())
            name     = safe(tr.css("td.posrela a::text").get())
            position = safe(tr.css("td.posrela tr:nth-child(2) td::text").get())

            self.logger.debug("PAY ATTENTION TO THIS: %s", len(tds))

            dob_age_td       = tds[-8]
            nat_td           = tds[-7]
            height_td        = tds[-6]
            foot_td          = tds[-5]
            joined_td        = tds[-4]
            signed_from_td   = tds[-3]
            contract_td      = tds[-2]
            value_td         = tds[-1]

            dob_age = safe(dob_age_td.xpath("normalize-space()").get())
            dob, age = None, None
            if dob_age:
                dob, _, rest = dob_age.partition("(")
                dob = safe(dob)
                age = int(rest.rstrip(")")) if rest.rstrip(")").isdigit() else None

            nat = ", ".join(
                safe(img.attrib.get("title"))
                for img in nat_td.css("img[title]")
                if safe(img.attrib.get("title"))
            ) or None

            return {
                "player_id"        : pid,
                "href"             : link,
                "number"           : None if number in {"", "-"} else number,
                "name"             : name,
                "position"         : position,
                "date_of_birth"    : dob,
                "age"              : age,
                "nationality"      : nat,
                "height"           : safe(height_td.xpath("text()").get()),
                "foot"             : safe(foot_td.xpath("text()").get()),
                "joined"           : safe(joined_td.xpath("text()").get()),
                "signed_from_href" : signed_from_td.css("a::attr(href)").get(),
                "signed_from_name" : safe(signed_from_td.css("a::attr(title)").get()),
                "contract_expires" : safe(contract_td.xpath("text()").get()),
                "market_value"     : safe(value_td.css("a::text").get()),
            }

        players = [
            row for tr in response.css("div.responsive-table table.items tbody tr")
            if (row := parse_player_row(tr))
        ]

        club_item = {**base, **attributes, "players": players}
        try:
            self.logger.info(
                "Club parsed: name=%s code=%s players=%d",
                club_item.get('name'),
                club_item.get('code'),
                len(players)
            )
        except Exception:
            pass
        # Drop any competition association
        if 'parent' in club_item:
            del club_item['parent']
        yield club_item
        # -- End: inline copy --


