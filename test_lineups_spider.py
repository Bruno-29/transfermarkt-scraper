#!/usr/bin/env python
"""Test script to validate game_lineups spider extraction"""
import json
import os
from scrapy.http import HtmlResponse
import requests

# Set SCRAPY_CHECK to allow spider initialization without parents file
os.environ['SCRAPY_CHECK'] = '1'

# Test URL
test_url = "https://www.transfermarkt.co.uk/ecija-balompie_real-madrid/aufstellung/spielbericht/2283303"

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
from tfmkt.spiders.game_lineups import GameLineupsSpider

# Create spider instance
spider = GameLineupsSpider()

# Create base dict to simulate parent data
base = {
    'href': '/ecija-balompie_real-madrid/aufstellung/spielbericht/2283303',
    'lineups': {
        'home_club': {
            'href': '/ecija-balompie/startseite/verein/11509',
            'formation': None,
            'starting_lineup': [],
            'substitutes': []
        },
        'away_club': {
            'href': '/real-madrid/startseite/verein/418',
            'formation': None,
            'starting_lineup': [],
            'substitutes': []
        }
    },
    'parent': {
        'href': '/spielbericht/index/spielbericht/2283303',
        'type': 'game',
        'game_id': 2283303
    }
}

# Parse the lineups
items = list(spider.parse_lineups(response, base))

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
print(f"✓ href: {item.get('href')}")
print(f"✓ type: {item.get('type')}")

home = item.get('home_club', {})
away = item.get('away_club', {})

print(f"\nHOME TEAM:")
print(f"  ✓ formation: {home.get('formation')}")
print(f"  ✓ starting_lineup count: {len(home.get('starting_lineup', []))}")
print(f"  ✓ substitutes count: {len(home.get('substitutes', []))}")

if home.get('starting_lineup'):
    first_player = home['starting_lineup'][0]
    print(f"\n  First player example:")
    print(f"    - number: {first_player.get('number')}")
    print(f"    - name: {first_player.get('name')}")
    print(f"    - position: {first_player.get('position')}")
    print(f"    - team_captain: {first_player.get('team_captain')}")
    print(f"    - href: {first_player.get('href')}")

print(f"\nAWAY TEAM:")
print(f"  ✓ formation: {away.get('formation')}")
print(f"  ✓ starting_lineup count: {len(away.get('starting_lineup', []))}")
print(f"  ✓ substitutes count: {len(away.get('substitutes', []))}")

if away.get('starting_lineup'):
    first_player = away['starting_lineup'][0]
    print(f"\n  First player example:")
    print(f"    - number: {first_player.get('number')}")
    print(f"    - name: {first_player.get('name')}")
    print(f"    - position: {first_player.get('position')}")
    print(f"    - team_captain: {first_player.get('team_captain')}")
    print(f"    - href: {first_player.get('href')}")

print("\n" + "=" * 80)
