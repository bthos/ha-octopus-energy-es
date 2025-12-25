"""Web scraper for Octopus Energy España tariff rates."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)


class TariffScraperError(Exception):
    """Exception raised for tariff scraping errors."""


class TariffScraper:
    """Web scraper for Octopus Energy España tariff pages."""

    BASE_URL = "https://octopusenergy.es"

    def __init__(self) -> None:
        """Initialize tariff scraper."""
        self._session: aiohttp.ClientSession | None = None
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_expiry: dict[str, datetime] = {}
        self._cache_duration = timedelta(days=7)  # Cache for 1 week

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None

    def _is_cache_valid(self, tariff_type: str) -> bool:
        """Check if cached data is still valid."""
        if tariff_type not in self._cache:
            return False
        if tariff_type not in self._cache_expiry:
            return False
        return datetime.now() < self._cache_expiry[tariff_type]

    async def scrape_relax_rates(self) -> dict[str, float]:
        """
        Scrape Octopus Relax fixed rate from website.

        Returns:
            Dictionary with 'fixed_rate' key
        """
        tariff_type = "relax"

        # Check cache
        if self._is_cache_valid(tariff_type):
            return self._cache[tariff_type]

        session = await self._get_session()
        url = f"{self.BASE_URL}/en/precios/tarifa-relax"

        try:
            async with session.get(url) as response:
                response.raise_for_status()
                html = await response.text()

                soup = BeautifulSoup(html, "lxml")

                # Look for price information in the page
                # This is a generic parser - actual selectors may need adjustment
                rates: dict[str, float] = {}

                # Try to find price elements
                # Common patterns: price classes, data attributes, etc.
                price_elements = soup.find_all(
                    class_=lambda x: x
                    and (
                        "price" in x.lower()
                        or "rate" in x.lower()
                        or "precio" in x.lower()
                    )
                )

                for elem in price_elements:
                    text = elem.get_text()
                    # Try to extract numeric price value
                    # Look for patterns like "0.123 €/kWh" or "0,123 €/kWh"
                    import re

                    match = re.search(r"(\d+[.,]\d+)\s*€/kWh", text)
                    if match:
                        price_str = match.group(1).replace(",", ".")
                        try:
                            rate = float(price_str)
                            rates["fixed_rate"] = rate
                            break
                        except ValueError:
                            continue

                if not rates:
                    _LOGGER.warning("Could not find Relax rate on webpage")
                    raise TariffScraperError("Could not scrape Relax rate")

                # Cache the result
                self._cache[tariff_type] = rates
                self._cache_expiry[tariff_type] = datetime.now() + self._cache_duration

                return rates

        except aiohttp.ClientError as err:
            raise TariffScraperError(f"Error scraping Relax rates: {err}") from err

    async def scrape_solar_rates(self) -> dict[str, float]:
        """
        Scrape Octopus Solar P1/P2/P3 rates from website.

        Returns:
            Dictionary with 'p1_rate', 'p2_rate', 'p3_rate', 'solar_surplus_rate' keys
        """
        tariff_type = "solar"

        # Check cache
        if self._is_cache_valid(tariff_type):
            return self._cache[tariff_type]

        session = await self._get_session()
        url = f"{self.BASE_URL}/en/precios/tarifa-solar"

        try:
            async with session.get(url) as response:
                response.raise_for_status()
                html = await response.text()

                soup = BeautifulSoup(html, "lxml")

                rates: dict[str, float] = {}

                # Look for P1, P2, P3 rates
                # Common patterns: tables, price lists, etc.
                import re

                # Try to find rate information
                # Look for patterns like "P1: 0.123 €/kWh" or similar
                text_content = soup.get_text()

                # Pattern for P1/P2/P3 rates
                p1_match = re.search(
                    r"P1[:\s]+(\d+[.,]\d+)\s*€/kWh", text_content, re.IGNORECASE
                )
                p2_match = re.search(
                    r"P2[:\s]+(\d+[.,]\d+)\s*€/kWh", text_content, re.IGNORECASE
                )
                p3_match = re.search(
                    r"P3[:\s]+(\d+[.,]\d+)\s*€/kWh", text_content, re.IGNORECASE
                )

                if p1_match:
                    rates["p1_rate"] = float(p1_match.group(1).replace(",", "."))
                if p2_match:
                    rates["p2_rate"] = float(p2_match.group(1).replace(",", "."))
                if p3_match:
                    rates["p3_rate"] = float(p3_match.group(1).replace(",", "."))

                # Look for solar surplus compensation
                surplus_match = re.search(
                    r"(?:surplus|excedente|compensation)[:\s]+(\d+[.,]\d+)\s*€/kWh",
                    text_content,
                    re.IGNORECASE,
                )
                if surplus_match:
                    rates["solar_surplus_rate"] = float(
                        surplus_match.group(1).replace(",", ".")
                    )

                if not rates:
                    _LOGGER.warning("Could not find Solar rates on webpage")
                    raise TariffScraperError("Could not scrape Solar rates")

                # Cache the result
                self._cache[tariff_type] = rates
                self._cache_expiry[tariff_type] = datetime.now() + self._cache_duration

                return rates

        except aiohttp.ClientError as err:
            raise TariffScraperError(f"Error scraping Solar rates: {err}") from err

    async def scrape_go_rates(self) -> dict[str, float]:
        """
        Scrape Octopus Go P1/P2/P3 rates from website.

        Returns:
            Dictionary with 'p1_rate', 'p2_rate', 'p3_rate' keys
        """
        tariff_type = "go"

        # Check cache
        if self._is_cache_valid(tariff_type):
            return self._cache[tariff_type]

        session = await self._get_session()
        url = f"{self.BASE_URL}/en/precios/tarifa-ev"

        try:
            async with session.get(url) as response:
                response.raise_for_status()
                html = await response.text()

                soup = BeautifulSoup(html, "lxml")

                rates: dict[str, float] = {}

                import re

                text_content = soup.get_text()

                # Pattern for P1/P2/P3 rates
                p1_match = re.search(
                    r"P1[:\s]+(\d+[.,]\d+)\s*€/kWh", text_content, re.IGNORECASE
                )
                p2_match = re.search(
                    r"P2[:\s]+(\d+[.,]\d+)\s*€/kWh", text_content, re.IGNORECASE
                )
                p3_match = re.search(
                    r"P3[:\s]+(\d+[.,]\d+)\s*€/kWh", text_content, re.IGNORECASE
                )

                if p1_match:
                    rates["p1_rate"] = float(p1_match.group(1).replace(",", "."))
                if p2_match:
                    rates["p2_rate"] = float(p2_match.group(1).replace(",", "."))
                if p3_match:
                    rates["p3_rate"] = float(p3_match.group(1).replace(",", "."))

                if not rates:
                    _LOGGER.warning("Could not find Go rates on webpage")
                    raise TariffScraperError("Could not scrape Go rates")

                # Cache the result
                self._cache[tariff_type] = rates
                self._cache_expiry[tariff_type] = datetime.now() + self._cache_duration

                return rates

        except aiohttp.ClientError as err:
            raise TariffScraperError(f"Error scraping Go rates: {err}") from err

