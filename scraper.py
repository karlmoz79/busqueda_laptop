import asyncio
import logging
import random
from typing import List, Optional
from urllib.parse import quote_plus
from playwright.async_api import async_playwright
from playwright_stealth.stealth import Stealth
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
    def __init__(self, headless: bool = False):
        # Query de búsqueda
        self.search_query = "Lenovo ThinkBook 16"
        self.base_url = "https://www.amazon.com"
        self.max_retries = 3
        self.headless = headless
        
    async def _human_delay(self, min_sec: float = 1.0, max_sec: float = 3.5):
        """Simula un retraso humano aleatorio."""
        await asyncio.sleep(random.uniform(min_sec, max_sec))
    
    async def _smooth_scroll(self, page, steps: int = 3):
        """Simula un scroll humano gradual en lugar de un salto abrupto."""
        for i in range(steps):
            scroll_amount = random.randint(200, 500)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(random.uniform(0.3, 0.8))
    
    async def _simulate_mouse_movement(self, page):
        """Mueve el mouse de forma aleatoria como un humano."""
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 1200)
            y = random.randint(100, 600)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.4))

    def _is_blocked(self, title: str, page_content: str) -> bool:
        """Detecta si Amazon nos bloqueó."""
        blocked_signals = [
            "sorry" in title.lower(),
            "captcha" in title.lower(),
            "robot" in title.lower(),
            "something went wrong" in page_content.lower()[:2000],
            "validateCaptcha" in page_content[:3000],
            "Type the characters you see" in page_content[:3000],
        ]
        return any(blocked_signals)

    async def scrape(self) -> List[ProductData]:
        """Ejecuta el scraper asincrónico para buscar el producto en Amazon."""
        
        for attempt in range(1, self.max_retries + 1):
            logger.info(f"Intento {attempt} de {self.max_retries}...")
            
            result = await self._attempt_scrape()
            
            if result is not None:
                return result
            
            if attempt < self.max_retries:
                wait_time = random.uniform(5, 10) * attempt
                logger.info(f"Esperando {wait_time:.1f}s antes de reintentar...")
                await asyncio.sleep(wait_time)
        
        logger.error("Se agotaron todos los reintentos.")
        return []

    async def _attempt_scrape(self) -> Optional[List[ProductData]]:
        """Un intento individual de scraping. Retorna None si fue bloqueado."""
        async with async_playwright() as p:
            # User agents actualizados y realistas (Chrome 131 en Linux)
            user_agents = [
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            ]
            
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-infobars",
                    "--window-size=1920,1080",
                ]
            )

            context = await browser.new_context(
                user_agent=random.choice(user_agents),
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/New_York",
                # Simular permisos reales del navegador
                permissions=["geolocation"],
                java_script_enabled=True,
            )
            
            # Establecer moneda en USD
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
                # === PASO 1: Ir primero a la homepage (como un humano) ===
                logger.info("Navegando a la homepage de Amazon...")
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
                await self._human_delay(2.0, 4.0)
                await self._simulate_mouse_movement(page)
                
                # Verificar si la homepage ya nos bloqueó
                title = await page.title()
                content = await page.content()
                if self._is_blocked(title, content):
                    logger.warning("Bloqueado en la homepage. Abortando intento.")
                    await browser.close()
                    return None
                
                # === PASO 2: Usar la barra de búsqueda como un humano ===
                logger.info(f"Buscando: {self.search_query}")
                search_box = page.locator("#twotabsearchtextbox")
                
                if await search_box.count() > 0:
                    await search_box.click()
                    await self._human_delay(0.5, 1.0)
                    
                    # Escribir carácter por carácter (simula tipeo humano)
                    for char in self.search_query:
                        await search_box.press(char)
                        await asyncio.sleep(random.uniform(0.05, 0.15))
                    
                    await self._human_delay(0.5, 1.5)
                    await page.keyboard.press("Enter")
                else:
                    # Fallback: navegar directamente a la URL de búsqueda
                    logger.info("No se encontró barra de búsqueda, usando URL directa.")
                    search_url = f"{self.base_url}/s?k={quote_plus(self.search_query)}"
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                
                await self._human_delay(2.0, 4.0)
                await self._smooth_scroll(page)
                
                # === PASO 3: Verificar bloqueo en resultados ===
                title = await page.title()
                content = await page.content()
                if self._is_blocked(title, content):
                    logger.warning("Bloqueado en la página de resultados.")
                    await page.screenshot(path="debug_amazon.png")
                    await browser.close()
                    return None
                
                # Esperar a que carguen los resultados
                try:
                    await page.wait_for_selector("div[data-component-type='s-search-result']", timeout=15000)
                except Exception:
                    logger.info("No se encontraron resultados del grid. Guardando debug...")
                    await page.screenshot(path="debug_amazon.png")
                    with open("debug_amazon.html", "w", encoding="utf-8") as f:
                        f.write(await page.content())
                    await browser.close()
                    return []
                
                # === PASO 4: Extraer productos ===
                await self._smooth_scroll(page, steps=4)
                await self._human_delay(1.0, 2.0)
                
                products = []
                cajas_resultados = await page.locator("div[data-component-type='s-search-result']").all()
                logger.info(f"Se encontraron {len(cajas_resultados)} resultados en la página.")
                
                for index, item in enumerate(cajas_resultados[:15]): 
                    try:
                        title_str = ""
                        # Estrategia primaria: extraer el texto completo de la imagen del producto
                        # Amazon siempre incluye la descripción completa en el 'alt' de su clase s-image
                        img_loc = item.locator("img.s-image").first
                        if await img_loc.count() > 0:
                            title_str = await img_loc.get_attribute("alt") or ""
                        
                        # Fallback a los h2/span si la imagen no da un título completo (> 15 chars)
                        if not title_str or len(title_str.strip()) < 15:
                            title_locators = [
                                item.locator("h2 a span").first,
                                item.locator("span.a-size-medium.a-color-base.a-text-normal").first,
                                item.locator("span.a-size-base-plus.a-color-base.a-text-normal").first,
                                item.locator("h2").first
                            ]
                            
                            for loc in title_locators:
                                if await loc.count() > 0:
                                    temp_str = await loc.inner_text()
                                    if not temp_str.strip():
                                        temp_str = await loc.get_attribute("aria-label") or ""
                                    
                                    # Si encontramos una mejor descripción, la tomamos
                                    if temp_str and len(temp_str.strip()) > len(title_str.strip()):
                                        title_str = temp_str.strip()
                                        if len(title_str) > 20:
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
