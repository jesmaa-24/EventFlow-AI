"""
Unit tests for the deterministic Venue Search Tool.
Run with: pytest tests/test_venue_tool.py -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.venue_tool import search_venues, VenueSearchError


def test_filters_by_capacity():
    results = search_venues(location="Chennai", attendees=200)
    assert all(v["capacity"] >= 200 for v in results)


def test_filters_by_location():
    results = search_venues(location="Chennai", attendees=50)
    assert all(v["location"].lower() == "chennai" for v in results)

    results_cbe = search_venues(location="Coimbatore", attendees=50)
    assert all(v["location"].lower() == "coimbatore" for v in results_cbe)


def test_filters_by_venue_type():
    results = search_venues(location="Chennai", attendees=100, venue_type="outdoor")
    assert all(v["type"] == "outdoor" for v in results)


def test_no_matching_venue_returns_empty_list():
    results = search_venues(location="Chennai", attendees=100000)
    assert results == []


def test_invalid_attendees_raises_error():
    with pytest.raises(VenueSearchError):
        search_venues(location="Chennai", attendees=0)
    with pytest.raises(VenueSearchError):
        search_venues(location="Chennai", attendees=-5)


def test_results_sorted_by_price_ascending():
    results = search_venues(location="Chennai", attendees=100)
    prices = [v["price"] for v in results]
    assert prices == sorted(prices)
