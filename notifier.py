import os
import smtplib
import logging
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Cargar variables de entorno del archivo .env
load_dotenv()

class EmailNotifier:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.sender_email = os.getenv("EMAIL_USER")
        self.sender_password = os.getenv("EMAIL_PASSWORD")
        self.recipient_email = os.getenv("EMAIL_RECIPIENT", self.sender_email)
    
    def target_price_met(self, price_usd: float, threshold: float = 749.99, min_price: float = 500.00) -> bool:
        """Determina si un precio está en el rango de alerta.
        Solo alerta si el precio es <= threshold Y >= min_price.
        Precios menores a min_price se ignoran (posible error o moneda incorrecta)."""
        return price_usd >= min_price and price_usd <= threshold

    def send_consolidated_alert(self, products: list, threshold: float = 749.99, min_price: float = 500.00) -> bool:
        """
        Envía UN solo correo con todos los productos que están en el rango de alerta.
        Recibe una lista de objetos ProductData.
        """
        if not self.sender_email or not self.sender_password:
            logger.error("Credenciales de email no configuradas en .env")
            return False

        # Filtrar solo los que cumplen el rango
        deals = [p for p in products if p.price_usd and self.target_price_met(p.price_usd, threshold, min_price)]

        if not deals:
            logger.info("No hay productos en el rango de alerta. No se envia correo.")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            msg['Subject'] = f"Alerta de Precio: {len(deals)} producto(s) entre ${min_price:,.0f} y ${threshold:,.2f}"

            # Construir el cuerpo del correo
            lines = [
                "Hola!",
                "",
                f"Se encontraron {len(deals)} producto(s) en tu rango de alerta (${min_price:,.0f} - ${threshold:,.2f}):",
                "",
                "=" * 55,
            ]

            for i, p in enumerate(deals, 1):
                envio = "Si" if p.ships_to_colombia else "No/Desconocido"
                lines.extend([
                    f"",
                    f"  #{i} - ${p.price_usd:,.2f}",
                    f"  {p.title}",
                    f"  Envio a Colombia: {envio}",
                    f"  {p.url}",
                    f"",
                    "-" * 55,
                ])

            lines.extend([
                "",
                "-- Amazon Price Tracker",
            ])

            body = "\n".join(lines)
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # Enviar correo
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.set_debuglevel(0)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            server.quit()

            logger.info(f"Correo consolidado enviado a {self.recipient_email} con {len(deals)} producto(s)")
            return True

        except Exception as e:
            logger.error(f"Falla al enviar correo: {e}")
            return False

    # Mantener compatibilidad con app.py (envío individual)
    def send_alert(self, product_data) -> bool:
        """Envía un correo individual (usado por la interfaz web)."""
        return self.send_consolidated_alert([product_data])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    notifier = EmailNotifier()
    class MockProduct:
        title = "Mock Lenovo ThinkBook 16"
        price_usd = 699.99
        ships_to_colombia = True
        url = "https://www.amazon.com"
        
    if notifier.sender_email:
        notifier.send_consolidated_alert([MockProduct()])
    else:
        print("Falta .env, email no será enviado en el standalone test.")
