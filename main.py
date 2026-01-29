import asyncio
import json
import argparse
import logging
import pandas as pd
from lhkpn_scraper import LHKPNScraper

def parse_max_results(value):
    """Parse max-results argument, allowing 'inf' for infinity."""
    if value.lower() == 'inf':
        return float('inf')
    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid int value: '{value}'")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LHKPN_CLI")

async def main():
    parser = argparse.ArgumentParser(description="Scrape LHKPN data from KPK portal.")
    parser.add_argument("query", help="The name or query to search for.")
    parser.add_argument("--max-results", type=parse_max_results, default=10, help="Maximum number of results to scrape (default: 10). Use 'inf' for unlimited results.")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser in headless mode (default: True).")
    parser.add_argument("--no-headless", action="store_false", dest="headless", help="Run browser in capped (visible) mode.")
    parser.add_argument("--output", type=str, default="lhkpn_results.json", help="Output file path (default: lhkpn_results.json).")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format: json or csv (default: json).")

    args = parser.parse_args()

    scraper = LHKPNScraper(headless=args.headless)
    logger.info(f"Starting scrape for '{args.query}' (max results: {args.max_results})...")
    
    try:
        data = await scraper.run(args.query, max_results=args.max_results)
        
        if not data:
            logger.warning("No data found for the given query.")
            return

        if args.format == "csv":
            # Flatten data for CSV if needed, or just focus on the main fields
            df = pd.DataFrame(data)
            # Reorder columns to put basic info first
            cols = ["name", "lembaga", "unit_kerja", "jabatan", "tanggal_lapor", "jenis_laporan", "total_harta"]
            other_cols = [c for c in df.columns if c not in cols]
            df = df[cols + other_cols]
            df.to_csv(args.output, index=False)
        else:
            with open(args.output, "w") as f:
                json.dump(data, f, indent=4)
            
        logger.info(f"Successfully scraped {len(data)} records. Saved to {args.output}")
        
    except Exception as e:
        logger.error(f"An error occurred during scraping: {e}")

if __name__ == "__main__":
    asyncio.run(main())
