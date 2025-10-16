#!/usr/bin/env python
"""Test script to validate games spider extraction"""
import json
import os
from scrapy import Spider
from scrapy.http import HtmlResponse
import requests

# Set SCRAPY_CHECK to allow spider initialization without parents file
os.environ['SCRAPY_CHECK'] = '1'

# Test URL
test_url = "https://www.transfermarkt.co.uk/spielbericht/index/spielbericht/3098550"

# Fetch the page
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
response_obj = requests.get(test_url, headers=headers)

# Create Scrapy response
response = HtmlResponse(
    url=test_url,
    body=response_obj.content,
    encoding='utf-8'
)

# Import the spider
from tfmkt.spiders.games import GamesSpider

# Create spider instance with empty parents to avoid initialization error
spider = GamesSpider()

# Create a base dict to simulate parent data
base = {
    'href': '/spielbericht/index/spielbericht/3098550',
    'type': 'competition',
    'parent': {}
}

# Parse the game
items = list(spider.parse_game(response, base))

# Print results
print("=" * 80)
print(f"Test URL: {test_url}")
print("=" * 80)
print("\nExtracted Data:")
print(json.dumps(items[0], indent=2, ensure_ascii=False))
print("\n" + "=" * 80)
print("Validation Checklist:")
print("=" * 80)

item = items[0]
print(f"✓ game_id: {item.get('game_id')}")
print(f"✓ home_club href: {item.get('home_club', {}).get('href')}")
print(f"✓ away_club href: {item.get('away_club', {}).get('href')}")
print(f"✓ home_club_position: {item.get('home_club_position')}")
print(f"✓ away_club_position: {item.get('away_club_position')}")
print(f"✓ result: {item.get('result')}")
print(f"✓ matchday: {item.get('matchday')}")
print(f"✓ date: {item.get('date')}")
print(f"✓ stadium: {item.get('stadium')}")
print(f"✓ attendance: {item.get('attendance')}")
print(f"✓ referee: {item.get('referee')}")
print(f"✓ home_manager: {item.get('home_manager')}")
print(f"✓ away_manager: {item.get('away_manager')}")
print(f"✓ events count: {len(item.get('events', []))}")
print(f"\nEvents breakdown:")
events = item.get('events', [])
for event_type in ['Goals', 'Substitutions', 'Cards', 'Shootout']:
    count = len([e for e in events if e.get('type') == event_type])
    print(f"  - {event_type}: {count}")
