#!/usr/bin/env python
"""Analyze lineup page HTML to identify additional data points"""
from scrapy.http import HtmlResponse

# Load the saved HTML
with open('/tmp/lineup_2283303.html', 'rb') as f:
    html_content = f.read()

response = HtmlResponse(
    url="https://www.transfermarkt.co.uk/ecija-balompie_real-madrid/aufstellung/spielbericht/2283303",
    body=html_content,
    encoding='utf-8'
)

print("=" * 80)
print("LINEUP PAGE ADDITIONAL DATA POINTS ANALYSIS")
print("=" * 80)

# 1. Check for player ages
print("\n1. PLAYER AGES")
print("-" * 40)
starting_tables = response.xpath("//div[./h2[contains(@class, 'content-box-headline')] and normalize-space(./h2/text()[2]) = 'Starting Line-up']//table[@class='items']")
if starting_tables:
    first_table = starting_tables[0]
    # Look for age in player rows
    player_rows = first_table.xpath(".//tr[.//a[contains(@href, '/profil/spieler/')]]")
    if player_rows:
        first_player = player_rows[0]
        age = first_player.xpath(".//td//text()").getall()
        print(f"First player row texts: {[a.strip() for a in age if a.strip()][:10]}")

# 2. Check for player market values
print("\n2. PLAYER MARKET VALUES")
print("-" * 40)
market_values = response.xpath("//table[@class='items']//td[@class='rechts hauptlink']//text()").getall()
print(f"Market value elements: {market_values[:5]}")

# 3. Check for manager information
print("\n3. MANAGER INFORMATION")
print("-" * 40)
manager_sections = response.xpath("//div[@class='large-12 columns' and .//h2[contains(text(), 'Manager')]]")
print(f"Manager sections found: {len(manager_sections)}")
for idx, section in enumerate(manager_sections[:2]):
    manager_name = section.xpath(".//a[@class='spielprofil_tooltip']/text()").get()
    manager_href = section.xpath(".//a[@class='spielprofil_tooltip']/@href").get()
    manager_img = section.xpath(".//img[@class='bilderrahmen-fixed']/@src").get()
    # Look for additional manager info in the table
    manager_info = section.xpath(".//div[@class='info-table']//span//text()").getall()
    print(f"\nManager {idx+1}:")
    print(f"  Name: {manager_name}")
    print(f"  Href: {manager_href}")
    print(f"  Image: {manager_img}")
    print(f"  Additional info: {[i.strip() for i in manager_info if i.strip()]}")

# 4. Check for team statistics
print("\n4. TEAM STATISTICS")
print("-" * 40)
stats_table = response.xpath("//div[@class='large-12 columns']//table[@class='items']")
if stats_table:
    for idx, table in enumerate(stats_table[:2]):
        # Check if this is a stats table
        headers = table.xpath(".//thead//th/text()").getall()
        if headers:
            print(f"\nTable {idx+1} headers: {headers}")
        # Get first row data
        first_row = table.xpath(".//tbody/tr[1]//text()").getall()
        print(f"First row sample: {[r.strip() for r in first_row if r.strip()][:10]}")

# 5. Check for formation visualization or tactical details
print("\n5. FORMATION/TACTICAL DETAILS")
print("-" * 40)
formation_text = response.xpath("//div[@class='row']//text()[contains(., 'Formation')]").getall()
print(f"Formation mentions: {[f.strip() for f in formation_text if 'Formation' in f]}")

# 6. Check for player nationalities
print("\n6. PLAYER NATIONALITIES")
print("-" * 40)
# Nationalities are often in img alt or title attributes
nationalities = response.xpath("//table[@class='items']//td//img[@class='flaggenrahmen']/@title").getall()
print(f"Nationality flags found: {nationalities[:10]}")

# 7. Check for player ages in detail
print("\n7. DETAILED PLAYER INFO (Age, Date of Birth)")
print("-" * 40)
player_info = response.xpath("//table[@class='items']//tr")
if player_info:
    # Get a player row with full details
    for row in player_info[:5]:
        player_name = row.xpath(".//a[@class='spielprofil_tooltip']/@title").get()
        if player_name:
            # Look for age or DOB nearby
            all_text = row.xpath(".//text()").getall()
            print(f"\n{player_name}: {[t.strip() for t in all_text if t.strip() and t.strip() != player_name][:8]}")

# 8. Check for average age and market value summary
print("\n8. TEAM SUMMARY STATS")
print("-" * 40)
# These are usually in a footer or summary section
summary_boxes = response.xpath("//div[@class='large-6 columns']//div[@class='box']")
for idx, box in enumerate(summary_boxes[:4]):
    box_title = box.xpath(".//div[@class='table-header']/text()").get()
    box_content = box.xpath(".//text()").getall()
    print(f"\nBox {idx+1}: {box_title}")
    print(f"  Content: {[c.strip() for c in box_content if c.strip()][:10]}")

# 9. Check for substitution details
print("\n9. SUBSTITUTE BENCH INFO")
print("-" * 40)
subs_section = response.xpath("//div[./h2[contains(@class, 'content-box-headline')] and normalize-space(./h2/text()[2]) = 'Substitutes']")
print(f"Substitutes sections found: {len(subs_section)}")

# 10. Check for any additional metadata
print("\n10. PAGE METADATA")
print("-" * 40)
page_title = response.xpath("//head/title/text()").get()
print(f"Page title: {page_title}")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
