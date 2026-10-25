# 🛑 [DECOMMISSIONED] lhkpn

> [!WARNING]
> This repository has been decommissioned and archived.
> Its components have been consolidated into active repositories as part of the workstation data architecture modernization:
>
> 1. **Web Scraping Logic (KPK LHKPN State Official Wealth Scraper)**:
>    - Moved to **[indoscraping](https://github.com/nichsedge/indoscraping)** (`src/indoscraping/scraper/governance/lhkpn.py`).
>    - Executable via:
>      ```bash
>      uv run indoscraping run lhkpn
>      uv run indoscraping inspect lhkpn
>      uv run indoscraping export lhkpn --format csv
>      uv run indoscraping export lhkpn --format parquet
>      ```

---

## 📜 Historical Project Overview

A robust, asynchronous web scraper for the **Laporan Harta Kekayaan Penyelenggara Negara (LHKPN)** portal by the KPK (Komisi Pemberantasan Korupsi) Indonesia.

This tool allows you to search for public officials and extract their reported asset information, including detailed breakdowns of land, vehicles, assets, cash, and debts.

### Features
- **Asynchronous**: Built with Playwright and asyncio for efficiency.
- **Stealth**: Uses `playwright-stealth` to reduce detection.
- **Detailed Data**: Extracts both summary information and detailed asset breakdowns from modals.
- **Flexible CLI**: Search by name, limit results, and export to JSON or CSV.
- **Pagination Support**: Automatically crawls through multiple pages of search results.

---

## 🔗 Active Migration Target

- 🕷️ **IndoScraping Suite**: [github.com/nichsedge/indoscraping](https://github.com/nichsedge/indoscraping)
