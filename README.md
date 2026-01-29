# LHKPN Scraper

A robust, asynchronous web scraper for the Laporan Harta Kekayaan Penyelenggara Negara (LHKPN) portal by the KPK (Komisi Pemberantasan Korupsi) Indonesia.

This tool allows you to search for public officials and extract their reported asset information, including detailed breakdowns of land, vehicles, assets, cash, and debts.

## Features

- **Asynchronous**: Built with `Playwright` and `asyncio` for efficiency.
- **Stealth**: Uses `playwright-stealth` to reduce detection.
- **Detailed Data**: Extracts both summary information and detailed asset breakdowns from modals.
- **Flexible CLI**: Search by name, limit results, and export to JSON or CSV.
- **Pagination Support**: Automatically crawls through multiple pages of search results.

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd lhkpn
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Install Playwright browsers:
   ```bash
   uv run playwright install chromium
   ```

## Usage

### Command Line Interface (CLI)

The easiest way to use the scraper is via the `main.py` script.

```bash
# Basic search (saves to lhkpn_results.json by default)
uv run python main.py "Prabowo Subianto" --max-results inf

# Export to CSV with result limit
uv run python main.py "Prabowo Subianto" --max-results 5 --format csv --output prabowo_assets.csv

# Run in visible mode (not headless)
uv run python main.py "Prabowo Subianto" --no-headless
```

### Library Usage

You can also use the `LHKPNScraper` class in your own Python projects:

```python
import asyncio
from lhkpn_scraper import LHKPNScraper

async def run():
    scraper = LHKPNScraper(headless=True)
    results = await scraper.run("Official Name", max_results=10)
    for record in results:
        print(f"{record['name']} - Total Assets: {record['total_harta']}")

if __name__ == "__main__":
    asyncio.run(run())
```

## Disclaimer

This tool is for educational and research purposes only. Please respect the KPK portal's terms of service and robots.txt. Ensure your usage complies with Indonesian law regarding public data access.

## License

MIT License. See [LICENSE](LICENSE) for details.
