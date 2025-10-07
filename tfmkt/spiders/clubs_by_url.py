from typing import List, Dict, Optional
from urllib.parse import urlparse, unquote
import re

from scrapy import Request
from tfmkt.spiders.clubs import ClubsSpider


class ClubsByUrlSpider(ClubsSpider):
    """
    Scrape club squad pages from given competition URLs or codes.

    Key behaviors:
    - For CUP competitions, transforms /startseite/... to the participants page /teilnehmer/...
    - Collects club links from the competition page.
    - Builds squad (roster) request URLs **including the slug** when available:
        /{slug}/kader/verein/{club_id}/plus/1
      If a slug cannot be parsed from the club href, uses:
        /kader/verein/{club_id}/plus/1
    - Does NOT retry without /plus/1.
    - Drops any 'parent' field before yielding the club item.
    """
    name = "clubs_by_url"

    def __init__(
        self,
        base_url: Optional[str] = None,
        parents: Optional[str] = None,
        codes: Optional[str] = None,
        hrefs: Optional[str] = None,
        kind: str = "cup",
        season: Optional[int] = None,
    ):
        """
        Args
        ----
        - codes: comma-separated competition codes (e.g. "CL,EL,UCOL").
        - hrefs: comma-separated competition href paths or absolute URLs.
        - kind: 'cup' (default, uses 'pokalwettbewerb') or 'league' (uses 'wettbewerb').
        - season: optional integer season for *participants page only* (not used on club squad URLs).
        """
        self._input_codes = [c.strip() for c in codes.split(",")] if codes else []
        self._input_hrefs = [h.strip() for h in hrefs.split(",")] if hrefs else []
        self._kind = (kind or "cup").strip().lower()
        self.season = int(season) if season else None

        super().__init__(base_url=base_url, parents=parents)

        try:
            self.logger.info(
                "clubs_by_url initialized: kind=%s season=%s codes=%d hrefs=%d",
                self._kind,
                self.season,
                len(self._input_codes),
                len(self._input_hrefs),
            )
            if self._input_codes:
                self.logger.debug("codes: %s", ",".join(self._input_codes))
            if self._input_hrefs:
                self.logger.debug("hrefs(raw): %s", ",".join(self._input_hrefs))
        except Exception:
            pass

    # -------------------------
    # Helpers for entry points
    # -------------------------

    def _errback_start(self, failure):
        """Errback for competition entry requests."""
        try:
            request = getattr(failure, "request", None)
            self.logger.error("Start request failed: url=%s err=%r", getattr(request, "url", None), failure.value)
        except Exception:
            pass

    def _errback_club(self, failure):
        """Errback for club squad requests."""
        try:
            request = getattr(failure, "request", None)
            self.logger.error("Club request failed: url=%s err=%r", getattr(request, "url", None), failure.value)
        except Exception:
            pass

    def _body_preview(self, response, limit: int = 400) -> str:
        try:
            text = getattr(response, "text", "") or ""
            return (text[:limit]).replace("\n", " ") if text else ""
        except Exception:
            return ""

    def _normalize_href(self, href: str) -> str:
        """Return a site-relative href beginning with '/'. Accepts absolute URLs too."""
        if not href:
            return href
        if href.startswith(("http://", "https://")):
            parsed = urlparse(href)
            normalized = parsed.path.rstrip("/")
        else:
            normalized = href.rstrip("/")
        if normalized != href:
            try:
                self.logger.debug("normalize_href: %s -> %s", href, normalized)
            except Exception:
                pass
        return normalized

    def _hrefs_from_codes(self, codes: List[str]) -> List[str]:
        base_segment = "pokalwettbewerb" if self._kind == "cup" else "wettbewerb"
        hrefs = [f"/startseite/{base_segment}/{code}" for code in codes if code]
        try:
            self.logger.info(
                "Resolved %d code(s) to hrefs (kind=%s)", len(hrefs), self._kind
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
                len(normalized_hrefs),
            )
            self.logger.debug("entry_hrefs: %s", ",".join(entry_hrefs))
        except Exception:
            pass
        return [{"type": "competition", "href": href} for href in entry_hrefs]

    def _build_competition_url(self, href: str) -> str:
        """
        Build the correct request URL for a competition entrypoint.
        For cups, navigate to the participants page; for leagues, ensure /plus/ variant.
        Append saison_id when a season is provided (participants page only).
        """
        path = self._normalize_href(href)
        is_cup = self._kind == "cup" or ("/pokalwettbewerb/" in path)

        if is_cup:
            original_path = path
            if "/teilnehmer/" not in path:
                if "/startseite/" in path:
                    path = path.replace("/startseite/", "/teilnehmer/")
                elif "/plus/" in path:
                    path = path.replace("/plus/", "/teilnehmer/")
                elif "/pokalwettbewerb/" in path and "/teilnehmer/pokalwettbewerb/" not in path:
                    path = path.replace("/pokalwettbewerb/", "/teilnehmer/pokalwettbewerb/")

            # saison_id on participants is optional; include if provided
            try:
                if self.season:
                    path = re.sub(r"/saison_id/\d+", "", path).rstrip("/")
                    path = f"{path}/saison_id/{int(self.season)}"
            except Exception:
                pass

            try:
                if path != original_path:
                    self.logger.info("Cup URL adjusted: %s -> %s", original_path, path)
            except Exception:
                pass
            return f"{self.base_url}{path}"

        # League: ensure plus listing variant
        if "/plus/" not in path:
            path = path.rstrip("/") + "/plus/"
        return f"{self.base_url}{path}"

    # -------------------------
    # Requests & competition parse
    # -------------------------

    def start_requests(self):
        items: List[Dict] = []
        for item in self.entrypoints:
            url = self._build_competition_url(item["href"])
            item["seasoned_href"] = url
            try:
                self.logger.info("Start request prepared: %s", url)
            except Exception:
                pass
            items.append(item)

        return [
            Request(
                item["seasoned_href"],
                cb_kwargs={"parent": item},
                handle_httpstatus_all=True,
                errback=self._errback_start,
            )
            for item in items
        ]

    def parse(self, response, parent):
        """
        Parse participants/list page, collect club /startseite/ links,
        and request each **slugged** squad page /{slug}/kader/verein/{id}/plus/1.
        """
        try:
            self.logger.info("Parsing competition page: %s status=%s", response.url, getattr(response, "status", None))
        except Exception:
            pass

        club_links = response.css("table.items td.links.hauptlink a::attr(href)").getall()
        if not club_links:
            club_links = response.css("a.vereinprofil_tooltip::attr(href)").re(
                r".*/startseite/verein/\d+"
            )
        if not club_links:
            ids = response.css("div.grid-view div.keys span::text").getall()
            club_links = [f"/dummy-slug/startseite/verein/{vid}" for vid in ids]
        if not club_links:
            try:
                self.logger.warning(
                    "No club links found on %s status=%s preview=%s",
                    response.url,
                    getattr(response, "status", None),
                    self._body_preview(response),
                )
            except Exception:
                pass

        seen = set()
        for href in club_links:
            href = self._normalize_href(href)  # e.g. /fc-chelsea/startseite/verein/631
            if not href or href in seen:
                continue
            seen.add(href)

            club_id = self._extract_club_id(href)
            slug = self._extract_slug(href)

            if not club_id:
                try:
                    self.logger.warning("Skip club without id: %s", href)
                except Exception:
                    pass
                continue

            # Build **one** roster URL (no retries, no saison_id)
            if slug:
                roster_path = f"/{slug}/kader/verein/{club_id}/plus/1"
            else:
                roster_path = f"/kader/verein/{club_id}/plus/1"

            request_url = f"{self.base_url}{roster_path}"
            base = {"type": "club", "href": href}
            try:
                self.logger.debug("Club request prepared: href=%s url=%s", href, request_url)
            except Exception:
                pass

            yield Request(
                request_url,
                callback=self.parse_details,
                cb_kwargs={"base": base},
                handle_httpstatus_all=True,
                errback=self._errback_club,
            )

    def _extract_club_id(self, href: str) -> Optional[str]:
        m = re.search(r"/verein/(\d+)", href)
        return m.group(1) if m else None

    def _extract_slug(self, href: str) -> Optional[str]:
        """
        Expect typical club start page hrefs like:
        /fc-chelsea/startseite/verein/631
        Returns 'fc-chelsea' or None if not present.
        """
        m = re.match(r"^/([^/]+)/startseite/verein/\d+(?:/.*)?$", href)
        return m.group(1) if m else None

    # -------------------------
    # Club & players parse (same as your working logic)
    # -------------------------

    def parse_details(self, response, base):
        """
        Same fields as in your working ClubsSpider.parse_details, but we ensure
        the yielded item has no 'parent' key to keep it competition-agnostic.
        """
        safe = self.safe_strip
        try:
            self.logger.info(
                "Parsing club details: response_url=%s status=%s base_href=%s",
                response.url,
                getattr(response, "status", None),
                base.get("href"),
            )
        except Exception:
            pass

        attributes: Dict[str, Optional[str]] = {}
        attributes["total_market_value"] = response.css("div.dataMarktwert a::text").get()

        attributes["squad_size"] = safe(
            response.xpath("//li[contains(text(),'Squad size:')]/span/text()").get()
        )
        attributes["average_age"] = safe(
            response.xpath("//li[contains(text(),'Average age:')]/span/text()").get()
        )

        foreigners_li = response.xpath("//li[contains(text(),'Foreigners:')]")
        if foreigners_li:
            attributes["foreigners_number"] = safe(foreigners_li[0].xpath("span/a/text()").get())
            attributes["foreigners_percentage"] = safe(
                foreigners_li[0].xpath("span/span/text()").get()
            )
        else:
            attributes["foreigners_number"] = None
            attributes["foreigners_percentage"] = None

        attributes["national_team_players"] = safe(
            response.xpath("//li[contains(text(),'National team players:')]/span/a/text()").get()
        )

        stadium_li = response.xpath("//li[contains(text(),'Stadium:')]")
        if stadium_li:
            attributes["stadium_name"] = safe(stadium_li[0].xpath("span/a/text()").get())
            attributes["stadium_seats"] = safe(stadium_li[0].xpath("span/span/text()").get())
        else:
            attributes["stadium_name"] = None
            attributes["stadium_seats"] = None

        attributes["net_transfer_record"] = safe(
            response.xpath("//li[contains(text(),'Current transfer record:')]/span/span/a/text()").get()
        )

        coach_name = response.xpath(
            '//div[contains(@data-viewport, "Mitarbeiter")]//div[@class="container-hauptinfo"]/a/text()'
        ).get()
        attributes["coach_name"] = coach_name.strip() if coach_name else None

        # Prefer canonical for the code (slug); fallback to base href
        canonical = response.css('link[rel="canonical"]::attr(href)').get()
        if canonical:
            attributes["code"] = unquote(urlparse(canonical).path.split("/")[1])
        else:
            attributes["code"] = unquote(urlparse(base["href"]).path.split("/")[1])

        name_val = response.xpath("//span[@itemprop='legalName']/text()").get() or \
                   response.xpath('//h1[contains(@class,"data-header__headline-wrapper")]/text()').get()
        attributes["name"] = self.safe_strip(name_val)

        # Normalize whitespace
        for k, v in list(attributes.items()):
            if isinstance(v, str):
                attributes[k] = v.strip()

        # ---- Players table ----
        seen_player_ids: set[int] = set()

        def parse_player_row(tr):
            link = tr.css("td.posrela a[href*='/profil/spieler/']::attr(href)").get()
            if not link:
                return None

            tds = tr.css("td")
            if len(tds) < 10:
                return None

            m_id = re.search(r"/spieler/(\d+)", link)
            if not m_id:
                return None
            pid = int(m_id.group(1))

            if pid in seen_player_ids:
                return None
            seen_player_ids.add(pid)

            number = safe(tds[0].css("div.rn_nummer::text").get())
            name = safe(tr.css("td.posrela a::text").get())
            position = safe(tr.css("td.posrela tr:nth-child(2) td::text").get())

            dob_age_td = tds[-8]
            nat_td = tds[-7]
            height_td = tds[-6]
            foot_td = tds[-5]
            joined_td = tds[-4]
            signed_from_td = tds[-3]
            contract_td = tds[-2]
            value_td = tds[-1]

            dob_age = safe(dob_age_td.xpath("normalize-space()").get())
            dob, age = None, None
            if dob_age:
                dob, _, rest = dob_age.partition("(")
                dob = safe(dob)
                rest = rest.rstrip(")")
                age = int(rest) if rest.isdigit() else None

            nat = ", ".join(
                safe(img.attrib.get("title"))
                for img in nat_td.css("img[title]")
                if safe(img.attrib.get("title"))
            ) or None

            return {
                "player_id": pid,
                "href": link,
                "number": None if number in {"", "-"} else number,
                "name": name,
                "position": position,
                "date_of_birth": dob,
                "age": age,
                "nationality": nat,
                "height": safe(height_td.xpath("text()").get()),
                "foot": safe(foot_td.xpath("text()").get()),
                "joined": safe(joined_td.xpath("text()").get()),
                "signed_from_href": signed_from_td.css("a::attr(href)").get(),
                "signed_from_name": safe(signed_from_td.css("a::attr(title)").get()),
                "contract_expires": safe(contract_td.xpath("text()").get()),
                "market_value": safe(value_td.css("a::text").get()),
            }

        players = [
            row
            for tr in response.css("div.responsive-table table.items tbody tr")
            if (row := parse_player_row(tr))
        ]

        if not players:
            try:
                self.logger.warning(
                    "No players parsed for %s status=%s preview=%s",
                    response.url,
                    getattr(response, "status", None),
                    self._body_preview(response),
                )
            except Exception:
                pass

        club_item = {**base, **attributes, "players": players}
        try:
            self.logger.info(
                "Club parsed: name=%s code=%s players=%d",
                club_item.get("name"),
                club_item.get("code"),
                len(players),
            )
        except Exception:
            pass

        # Ensure no competition association is kept
        club_item.pop("parent", None)
        yield club_item