#!/usr/bin/env python
"""Analyze game page HTML to identify additional data points"""
from scrapy.http import HtmlResponse
import re

# Load the saved HTML
with open('/tmp/game_3098550.html', 'rb') as f:
    html_content = f.read()

response = HtmlResponse(
    url="https://www.transfermarkt.co.uk/spielbericht/index/spielbericht/3098550",
    body=html_content,
    encoding='utf-8'
)

print("=" * 80)
print("ADDITIONAL DATA POINTS ANALYSIS")
print("=" * 80)

# 1. Check for kick-off time
print("\n1. KICK-OFF TIME")
print("-" * 40)
time_elements = response.xpath("//p[@class='sb-datum hide-for-small']//text()").getall()
print(f"Time elements found: {time_elements}")

# 2. Check for competition name/logo
print("\n2. COMPETITION NAME")
print("-" * 40)
comp_name = response.xpath("//div[@class='sb-spieldaten']//a[contains(@href, 'wettbewerb')]/@title").get()
comp_href = response.xpath("//div[@class='sb-spieldaten']//a[contains(@href, 'wettbewerb')]/@href").get()
print(f"Competition: {comp_name}")
print(f"Competition href: {comp_href}")

# 3. Check for half-time score
print("\n3. HALF-TIME/FULL-TIME SCORES")
print("-" * 40)
ht_score = response.xpath("//div[@class='sb-halbzeit']/text()").get()
ft_score = response.xpath("//div[@class='sb-endstand']/text()").get()
print(f"Half-time: {ht_score}")
print(f"Full-time: {ft_score}")

# 4. Check for additional referee info
print("\n4. REFEREE DETAILS")
print("-" * 40)
referee_link = response.xpath("//a[contains(@href, 'schiedsrichter')]")
referee_name = referee_link.xpath("@title").get()
referee_href = referee_link.xpath("@href").get()
print(f"Referee name: {referee_name}")
print(f"Referee href: {referee_href}")

# 5. Check for stadium capacity or additional venue info
print("\n5. VENUE DETAILS")
print("-" * 40)
venue_box = response.css('p.sb-zusatzinfos')
venue_text = venue_box.xpath('.//text()').getall()
print(f"Venue raw text: {[t.strip() for t in venue_text if t.strip()]}")

# 6. Check for team names (not just hrefs)
print("\n6. TEAM NAMES")
print("-" * 40)
home_team = response.xpath("//div[@class='sb-heim']//a/@title").get()
away_team = response.xpath("//div[@class='sb-gast']//a/@title").get()
print(f"Home team: {home_team}")
print(f"Away team: {away_team}")

# 7. Check for manager hrefs (currently only extracting names)
print("\n7. MANAGER DETAILS")
print("-" * 40)
manager_elements = response.xpath("//tr[(contains(td/b/text(),'Manager')) or (contains(td/div/text(),'Manager'))]/td[2]")
for idx, elem in enumerate(manager_elements):
    name = elem.xpath("a/text()").get()
    href = elem.xpath("a/@href").get()
    print(f"Manager {idx+1}: {name} ({href})")

# 8. Check for assistant referees or other officials
print("\n8. MATCH OFFICIALS")
print("-" * 40)
officials = response.xpath("//p[@class='sb-zusatzinfos']//text()").getall()
print(f"Officials section: {[o.strip() for o in officials if o.strip()]}")

# 9. Check date format and see if we can extract more granular info
print("\n9. DATE/TIME DETAILS")
print("-" * 40)
date_link = response.xpath("//p[@class='sb-datum hide-for-small']/a[contains(@href, 'datum')]")
date_text = date_link.xpath("text()").get()
date_href = date_link.xpath("@href").get()
print(f"Date text: {date_text}")
print(f"Date href: {date_href}")

# 10. Check for any match statistics
print("\n10. MATCH STATISTICS")
print("-" * 40)
stats_section = response.xpath("//div[contains(@class, 'large-12') and .//h2[contains(text(), 'Statistics')]]")
if stats_section:
    print("Statistics section found!")
    stats = stats_section.xpath(".//text()").getall()
    print(f"Stats: {[s.strip() for s in stats if s.strip()][:20]}")
else:
    print("No statistics section found on this page")

# 11. Look for any additional data in the events
print("\n11. EVENT DETAILS")
print("-" * 40)
goal_events = response.xpath("//div[./h2[@class='content-box-headline' and normalize-space(text()) = 'Goals']]/following-sibling::div[@class='large-8']//div[@class='sb-aktion']")
print(f"Number of goal events: {len(goal_events)}")
if goal_events:
    first_goal = goal_events[0]
    print("\nFirst goal detailed structure:")
    minute_style = first_goal.xpath('./div[1]/span[@class="sb-sprite-uhr-klein"]/@style').get()
    extra_min = first_goal.xpath('./div[1]/span[@class="sb-sprite-uhr-klein"]/text()').get()
    player_href = first_goal.xpath('./div[@class="sb-aktion-spielerbild"]/a/@href').get()
    player_img = first_goal.xpath('./div[@class="sb-aktion-spielerbild"]/a/img/@src').get()
    action_text = first_goal.xpath('./div[@class="sb-aktion-aktion"]//text()').getall()
    print(f"- Minute sprite style: {minute_style}")
    print(f"- Extra minute: {extra_min}")
    print(f"- Player href: {player_href}")
    print(f"- Player img: {player_img}")
    print(f"- Action full text: {action_text}")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
