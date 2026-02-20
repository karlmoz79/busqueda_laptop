"""
Amazon Price Tracker — Script de ejecución automática
Ejecuta el scraper y envía alertas por correo sin necesidad de interfaz web.

Uso:
    uv run tracker.py
    uv run tracker.py --query "MacBook Air M3"
    uv run tracker.py --threshold 600 --min-price 400
"""

import argparse
import asyncio
import logging

from notifier import EmailNotifier
from scraper import AmazonScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main(query: str, threshold: float, min_price: float):
    """Ejecuta el scraper y envía alertas automáticamente."""

    logger.info(f"Iniciando busqueda: '{query}'")
    logger.info(f"Rango de alerta: ${min_price:,.2f} — ${threshold:,.2f}")

    # Ejecutar scraper
    scraper = AmazonScraper(headless=True)
    scraper.search_query = query
    resultados = await scraper.scrape()

    if not resultados:
        logger.warning("No se encontraron resultados o Amazon bloqueo la solicitud.")
        return

    logger.info(f"Se encontraron {len(resultados)} productos.")

    # Procesar y mostrar resultados
    notifier = EmailNotifier()

    for r in resultados:
        precio_texto = f"${r.price_usd:,.2f}" if r.price_usd else "N/D"
        envio = "Si" if r.ships_to_colombia else "No"
        en_rango = " *** EN RANGO ***" if r.price_usd and notifier.target_price_met(r.price_usd, threshold, min_price) else ""
        logger.info(f"  -> {r.title[:60]}... | {precio_texto} | Envio CO: {envio}{en_rango}")

    # Enviar UN solo correo con todos los productos en rango
    enviado = notifier.send_consolidated_alert(resultados, threshold, min_price)
    deals_count = sum(1 for r in resultados if r.price_usd and notifier.target_price_met(r.price_usd, threshold, min_price))

    # Resumen final
    print()
    print("=" * 60)
    print(f"  RESUMEN DE BUSQUEDA")
    print("=" * 60)
    print(f"  Producto buscado : {query}")
    print(f"  Resultados       : {len(resultados)}")
    print(f"  En rango alerta  : {deals_count}")
    print(f"  Correo enviado   : {'Si' if enviado else 'No'}")
    print(f"  Rango de alerta  : ${min_price:,.2f} — ${threshold:,.2f}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Amazon Price Tracker - Alertas automaticas")
    parser.add_argument(
        "--query", "-q",
        type=str,
        default="Lenovo ThinkBook 16",
        help="Producto a buscar (default: Lenovo ThinkBook 16)",
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=749.99,
        help="Precio maximo para alerta en USD (default: 749.99)",
    )
    parser.add_argument(
        "--min-price", "-m",
        type=float,
        default=500.00,
        help="Precio minimo para alerta en USD (default: 500.00)",
    )

    args = parser.parse_args()
    asyncio.run(main(args.query, args.threshold, args.min_price))
