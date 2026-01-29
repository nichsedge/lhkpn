import asyncio
import json
import logging
import os
from typing import List, Dict, Any, Optional, Union

import pandas as pd
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page
from playwright_stealth import Stealth
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LHKPNScraper")

class LHKPNScraper:
    """
    A scraper for the LHKPN (Laporan Harta Kekayaan Penyelenggara Negara) website of the KPK.
    """
    BASE_URL = "https://elhkpn.kpk.go.id"
    SEARCH_PAGE = f"{BASE_URL}/portal/user/login#announ"

    def __init__(self, headless: bool = True):
        """
        Initialize the scraper.

        Args:
            headless: Whether to run the browser in headless mode.
        """
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def init_browser(self, playwright: Playwright) -> None:
        """
        Initialize the Playwright browser, context, and page.
        """
        logger.info("Initializing browser...")
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 800}
        )
        self.page = await self.context.new_page()
        await Stealth().apply_stealth_async(self.page)

    async def handle_popups(self) -> None:
        """
        Dismiss common popups and modals that appear on the KPK LHKPN site.
        """
        logger.info("Handling initial popups...")
        try:
            for _ in range(5):
                await self.page.evaluate("""() => {
                    const closeButtons = document.querySelectorAll('.remodal-close');
                    closeButtons.forEach(btn => btn.click());
                    
                    const wrappers = document.querySelectorAll('.remodal-wrapper.remodal-is-opened');
                    wrappers.forEach(w => w.style.display = 'none');
                    
                    const backdrop = document.querySelector('.remodal-overlay');
                    if (backdrop) backdrop.remove();
                    
                    document.body.classList.remove('remodal-is-active');
                    
                    const bootstrapModals = document.querySelectorAll('.modal.in, .modal.show');
                    bootstrapModals.forEach(m => {
                        const close = m.querySelector('button.close, .btn-close');
                        if (close) close.click();
                        else m.style.display = 'none';
                    });
                }""")
                await asyncio.sleep(1)
                active = await self.page.query_selector(".remodal-is-opened, .modal.in, .modal.show")
                if not active:
                    break
        except Exception as e:
            logger.error(f"Error handling popups: {e}")

    async def search(self, name: str) -> None:
        """
        Search for a person's name on the LHKPN portal.

        Args:
            name: The name to search for.
        """
        logger.info(f"Searching for '{name}'...")
        try:
            await self.page.goto(self.SEARCH_PAGE, timeout=60000, wait_until="load")
        except Exception as e:
            logger.warning(f"Initial goto timeout or error: {e}. Retrying with relaxed wait...")
            await self.page.goto(self.SEARCH_PAGE, timeout=60000, wait_until="domcontentloaded")

        await self.handle_popups()

        try:
            announ_tab = self.page.locator("a.page-scroll[href='#announ'], a.anchor-eannoun").first
            await announ_tab.scroll_into_view_if_needed()
            await announ_tab.click()
            await asyncio.sleep(2)
        except Exception as e:
            logger.warning(f"Could not click announcement tab: {e}")
            await self.page.evaluate("window.location.hash = '#announ'")
            await asyncio.sleep(1)

        input_selector = "#CARI_NAMA, input[name='CARI_NAMA']"
        try:
            await self.page.wait_for_selector(input_selector, timeout=20000)
        except:
            logger.warning("Search input not found, attempting to refresh hash and wait again...")
            await self.page.evaluate("window.location.hash = '#announ'")
            await self.page.wait_for_selector(input_selector, timeout=20000)

        input_field = self.page.locator(input_selector).first
        await input_field.scroll_into_view_if_needed()
        
        await input_field.click()
        await self.page.keyboard.press("Control+A")
        await self.page.keyboard.press("Backspace")
        await input_field.fill(name)
        
        search_btn = self.page.locator("button[type='submit'].btn-success")
        await search_btn.scroll_into_view_if_needed()
        await search_btn.click()
        
        logger.info("Waiting for search results...")
        try:
            table_row_selector = "#table-pengumuman tbody tr, table.table-striped tbody tr"
            await self.page.wait_for_selector(table_row_selector, timeout=30000)
            logger.info("Found search results table.")
        except Exception as e:
            logger.error(f"Results table did not appear: {e}")
            await self.page.screenshot(path="search_failure.png")
            
            if await self.page.locator("text='Data Tidak Ditemukan'").is_visible():
                logger.info("Search returned no results.")
        
        await asyncio.sleep(2)

    async def extract_and_detail(self, max_results: Union[int, float] = float('inf')) -> List[Dict[str, Any]]:
        """
        Extract results from the table and attempt to get detailed asset information.

        Args:
            max_results: Maximum number of records to extract.

        Returns:
            A list of dictionaries containing the extracted data.
        """
        logger.info(f"Extracting results (max: {max_results})...")
        
        all_data = []
        page_num = 1
        
        while len(all_data) < max_results:
            logger.info(f"Processing page {page_num}...")
            
            row_selector = "table.table-striped tbody tr, #table-pengumuman tbody tr"
            try:
                await self.page.wait_for_selector(row_selector, timeout=10000)
            except:
                logger.info(f"No results found on page {page_num} or timeout.")
                break

            rows = self.page.locator(row_selector)
            count = await rows.count()
            
            if count > 0:
                first_row_cells = await rows.nth(0).locator("td").count()
                if first_row_cells < 5:
                    logger.info("Page seems empty or loading message visible.")
                    break

            logger.info(f"Found {count} rows on page {page_num}.")
            
            for i in range(count):
                if len(all_data) >= max_results:
                    break
                
                row = rows.nth(i)
                cells = row.locator("td")
                
                try:
                    async def get_cell_text(idx):
                        try:
                            if await cells.nth(idx).count() > 0:
                                return await cells.nth(idx).inner_text()
                        except:
                            pass
                        return ""

                    name = await get_cell_text(6)
                    lembaga = await get_cell_text(7)
                    unit_kerja = await get_cell_text(8)
                    jabatan = await get_cell_text(9)
                    tanggal_lapor = await get_cell_text(10)
                    total_harta = await get_cell_text(12)
                    jenis_laporan = await get_cell_text(11)
                    
                    if not name.strip() or "Rp." not in total_harta:
                        name = await get_cell_text(1)
                        lembaga = await get_cell_text(2)
                        unit_kerja = await get_cell_text(3)
                        jabatan = await get_cell_text(4)
                        tanggal_lapor = await get_cell_text(5)
                        total_harta = await get_cell_text(7)
                        jenis_laporan = await get_cell_text(6)

                    data = {
                        "name": name.strip(),
                        "lembaga": lembaga.strip(),
                        "unit_kerja": unit_kerja.strip(),
                        "jabatan": jabatan.strip(),
                        "tanggal_lapor": tanggal_lapor.strip(),
                        "jenis_laporan": jenis_laporan.strip(),
                        "total_harta": total_harta.strip(),
                        "tanah_bangunan": [],
                        "transportasi": [],
                        "bergerak_lainnya": [],
                        "surat_berharga": [],
                        "kas": [],
                        "harta_lainnya": [],
                        "hutang": []
                    }
                    
                    action_link = row.locator(".perbandingan-announcement, i.fa-history, i.fa-file-text-o")
                    
                    if await action_link.count() > 0:
                        history_btn = row.locator("a.perbandingan-announcement, a[data-toggle='modal'][data-target='#modal-perbandingan-announcement-lhkpn']").first
                        if await history_btn.count() > 0 and await history_btn.is_visible():
                            logger.info(f"Opening details for {name.strip()} ({tanggal_lapor.strip()})...")
                            await history_btn.click()
                            
                            modal_selector = "#modal-perbandingan-announcement-lhkpn"
                            try:
                                await self.page.wait_for_selector(f"{modal_selector} table", timeout=15000)
                                await asyncio.sleep(1.5)
                                
                                modal_html = await self.page.inner_html(modal_selector)
                                details = self.parse_detail(modal_html)
                                data.update(details)
                                
                                close_btn = self.page.locator(f"{modal_selector} .remodal-close, {modal_selector} .btn-danger, button[data-dismiss='modal']").first
                                if await close_btn.is_visible():
                                    await close_btn.click()
                                    await self.page.wait_for_selector(modal_selector, state="hidden", timeout=5000)
                                else:
                                    await self.page.keyboard.press("Escape")
                                    await asyncio.sleep(1)
                            except Exception as e:
                                logger.error(f"Error extracting modal for {name}: {e}")
                                await self.page.keyboard.press("Escape")
                                await asyncio.sleep(1)
                        else:
                            logger.info(f"No history link button visible for {name.strip()} ({tanggal_lapor.strip()})")
                    else:
                        logger.info(f"No detail link for {name.strip()} ({tanggal_lapor.strip()}), saving basic data.")
                    
                    all_data.append(data)
                except Exception as e:
                    logger.error(f"Error processing row {i}: {e}")

            next_btn = self.page.locator("#table-pengumuman_next, li.next a, .paginate_button.next a, a:has-text('Next'), a:has-text('>>')").first
            
            if await next_btn.count() > 0:
                is_visible = await next_btn.is_visible()
                is_disabled = await self.page.evaluate("""(btn) => {
                    const parent = btn.parentElement;
                    return btn.classList.contains('disabled') || 
                           (parent && parent.classList.contains('disabled')) ||
                           btn.getAttribute('aria-disabled') === 'true' ||
                           btn.disabled;
                }""", await next_btn.element_handle())
                
                if is_visible and not is_disabled:
                    logger.info("Clicking Next page...")
                    await next_btn.scroll_into_view_if_needed()
                    await next_btn.click()
                    page_num += 1
                    await asyncio.sleep(5)
                else:
                    logger.info("Reached last page.")
                    break
            else:
                logger.info("No Next page button found.")
                break
                
        return all_data

    async def run(self, query: str, max_results: Union[int, float] = float('inf')) -> List[Dict[str, Any]]:
        """
        Run the scraper.

        Args:
            query: The search query (name).
            max_results: Maximum records to scrape.

        Returns:
            List of scraped records.
        """
        async with async_playwright() as p:
            await self.init_browser(p)
            try:
                await self.search(query)
                all_data = await self.extract_and_detail(max_results=max_results)
                return all_data
            finally:
                if self.browser:
                    await self.browser.close()

    def parse_detail(self, html: str) -> Dict[str, List[Dict[str, str]]]:
        """
        Parse the detail modal HTML using BeautifulSoup.

        Args:
            html: HTML content of the modal.

        Returns:
            Dictionary of categorized asset details.
        """
        soup = BeautifulSoup(html, 'html.parser')
        data = {
            "tanah_bangunan": [],
            "transportasi": [],
            "bergerak_lainnya": [],
            "surat_berharga": [],
            "kas": [],
            "harta_lainnya": [],
            "hutang": []
        }
        
        category_map = {
            "TANAH DAN BANGUNAN": "tanah_bangunan",
            "ALAT TRANSPORTASI DAN MESIN": "transportasi",
            "HARTA BERGERAK LAINNYA": "bergerak_lainnya",
            "SURAT BERHARGA": "surat_berharga",
            "KAS DAN SETARA KAS": "kas",
            "HARTA LAINNYA": "harta_lainnya",
            "HUTANG": "hutang"
        }
        
        current_cat = None
        
        tbody = soup.find("tbody", class_="data_perbandingan_lhkpn")
        if not tbody:
            return data
            
        rows = tbody.find_all("tr")
        
        for row in rows:
            cells = row.find_all(["td", "th"])
            
            new_cat_found = False
            if len(cells) >= 3:
                c1_text = cells[1].get_text(strip=True).upper()
                c2_text = cells[2].get_text(strip=True).upper()
                
                for cat_name, key in category_map.items():
                    if cat_name in c2_text or cat_name in row.get_text(" ", strip=True).upper()[:50]:
                        header_indicators = ["A.", "B.", "C.", "D.", "E.", "F.", "II.", "III."]
                        if any(ind in c1_text or ind in cells[0].get_text(strip=True).upper() for ind in header_indicators):
                            current_cat = key
                            new_cat_found = True
                            break
            
            if new_cat_found:
                continue
                
            if current_cat:
                found_index = False
                desc = ""
                val = ""
                
                for j in range(min(len(cells), 4)):
                    cell_text = cells[j].get_text(strip=True)
                    if cell_text and cell_text[0].isdigit() and cell_text.endswith("."):
                        found_index = True
                        if j + 1 < len(cells):
                            desc = cells[j+1].get_text(strip=True)
                            for k in range(j + 2, len(cells)):
                                k_text = cells[k].get_text(strip=True)
                                if k_text and (k_text[0].isdigit() or (len(k_text) > 1 and k_text[0] in "0123456789")):
                                    val = k_text
                                    break
                        break
                
                if found_index and desc and val:
                    data[current_cat].append({
                        "description": desc,
                        "value": val
                    })

        # Fallback for totals if no detailed list items were found
        for key in data:
            if not data[key]:
                cat_name_search = [k for k, v in category_map.items() if v == key][0]
                for row in rows:
                    row_text = row.get_text(" ", strip=True).upper()
                    if cat_name_search in row_text:
                        cells = row.find_all(["td", "th"])
                        for cell in cells:
                            cell_text = cell.get_text(strip=True)
                            if cell_text and any(c.isdigit() for c in cell_text) and cell_text.replace(".", "").replace(",", "").isdigit():
                                data[key].append({"description": "Total", "value": cell_text})
                                break
                            
        return data
