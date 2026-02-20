import asyncio
import logging
from typing import List, Optional
from urllib.parse import quote_plus
from playwright.async_api import async_playwright
from playwright_stealth.stealth import Stealth
from bs4 import BeautifulSoup
from pydantic import BaseModel

# Configuración de logging basado en mejores prácticas de Python Pro
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductData(BaseModel):
    title: str
    price_usd: Optional[float]
    url: str
    ships_to_colombia: bool

class AmazonScraper:
    def __init__(self):
        # Query de búsqueda (Reducido para encontrar más coincidencias en Amazon)
        self.search_query = "Lenovo ThinkBook 16"
        self.base_url = "https://www.amazon.com"
        
    async def scrape(self) -> List[ProductData]:
        """Ejecuta el scraper asincrónico para buscar el producto en Amazon."""
        async with async_playwright() as p:
            # Lanzamos Chromium. Al cambiar headless a False Amazon confía más en nosotros.
            browser = await p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US"
            )
            
            # Establecer moneda en USD (United States Dollar) para evitar precios locales como COP
            await context.add_cookies([{
                "name": "i18n-prefs",
                "value": "USD",
                "domain": ".amazon.com",
                "path": "/"
            }])
            
            page = await context.new_page()
            
            # Aplicar técnicas de stealth para evadir "Bot Detection"
            stealth = Stealth()
            await stealth.apply_stealth_async(page)
            
            try:
                search_url = f"{self.base_url}/s?k={quote_plus(self.search_query)}"
                logger.info(f"Navegando a {search_url}")
                
                # Vamos directamente a la web sin timeouts abusivos
                await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                
                # Simulamos un scroll aleatorio como un humano (espera)
                await page.evaluate("window.scrollBy(0, document.body.scrollHeight / 2)")
                await asyncio.sleep(2)
                
                # Chequeo de captcha
                title = await page.title()
                if "captcha" in title.lower() or await page.locator("form[action='/errors/validateCaptcha']").count() > 0:
                    logger.warning("Amazon solicitó validación de Captcha.")
                    return []
                
                # Esperar a que carguen los resultados o algún elemento del DOM
                try:
                    await page.wait_for_selector("div[data-component-type='s-search-result']", timeout=15000)
                except Exception:
                    logger.info("No se encontraron resultados del grid, intentando modo alternativo. Guardando debug...")
                    await page.screenshot(path="debug_amazon.png")
                    with open("debug_amazon.html", "w", encoding="utf-8") as f:
                        f.write(await page.content())
                
                products = []
                cajas_resultados = await page.locator("div[data-component-type='s-search-result']").all()
                for index, item in enumerate(cajas_resultados[:15]): 
                    try:
                        title_str = ""
                        # Buscar el elemento de título a-text-normal standard o  h2
                        title_locators = [
                            item.locator("h2 span").first,
                            item.locator("h2").first,
                            item.locator("span.a-size-medium.a-color-base.a-text-normal").first
                        ]
                        
                        for loc in title_locators:
                            if await loc.count() > 0:
                                title_str = await loc.inner_text()
                                if not title_str.strip():
                                    title_str = await loc.get_attribute("aria-label") or ""
                                if title_str.strip():
                                    break
                        
                        title_str = title_str.strip()
                        if not title_str:
                            continue
                            
                        # Extract Link
                        link_locator = item.locator("h2 a").first
                        if await link_locator.count() == 0:
                            link_locator = item.locator("a.a-link-normal").first
                        
                        if await link_locator.count() == 0:
                            continue
                            
                        href = await link_locator.get_attribute("href")
                        url = f"{self.base_url}{href}" if href else ""
                        if not url:
                            continue
                            
                        # Extraer precio 
                        price = 0.0
                        price_whole_loc = item.locator("span.a-price-whole").first
                        if await price_whole_loc.count() > 0:
                            price_text = await price_whole_loc.inner_text()
                            price_fraction_loc = item.locator("span.a-price-fraction").first
                            frac_text = await price_fraction_loc.inner_text() if await price_fraction_loc.count() > 0 else "00"
                            
                            clean_price = price_text.replace(',', '').replace('.', '').strip()
                            if clean_price.isdigit():
                                price = float(f"{clean_price}.{frac_text}")
                                
                        # Delivery info (Colombia check)
                        ships_to_colombia = False
                        delivery_loc = item.locator("[data-cy='delivery-recipe']").first
                        if await delivery_loc.count() > 0:
                            delivery_text = await delivery_loc.inner_text()
                            if "Colombia" in delivery_text:
                                ships_to_colombia = True
                        
                        if "Lenovo" in title_str or price > 0:            
                            products.append(ProductData(
                                title=title_str,
                                price_usd=price,
                                seller="Amazon",
                                url=url,
                                ships_to_colombia=ships_to_colombia
                            ))
                    except Exception as eval_elem_e:
                        logger.debug(f"Falla evaluando elemento {index}: {eval_elem_e}")
                        continue
                
                return products
                
            except Exception as e:
                logger.error(f"Error durante el scraping: {e}")
                return []
            finally:
                await browser.close()

# Para pruebas locales rápidas
if __name__ == "__main__":
    async def test():
        scraper = AmazonScraper()
        resultados = await scraper.scrape()
        if not resultados:
            print("No se extrajeron productos. Es posible que el DOM de Amazon haya cambiado o sigamos bloqueados.")
        for r in resultados:
            print(r.model_dump_json(indent=2))
            
    asyncio.run(test())
