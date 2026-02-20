import os
import smtplib
import logging
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
    
    def target_price_met(self, price_usd: float, threshold: float = 750.00) -> bool:
        """Determina si un precio bajó de la meta definida ($750 por defecto).
        Nota: el amazon devuelve COP a veces, si el scraper obtiene el precio local
        convertiremos para la lógica en base al input en test o asumiremos USD estricto.""" 
        return price_usd > 0 and price_usd < threshold
        
    def send_alert(self, product_data) -> bool:
        """
        Envía un correo de alerta con información del producto.
        Recibe un objeto ProductData (del scraper).
        """
        if not self.sender_email or not self.sender_password:
            logger.error("Credenciales de email no configuradas en .env")
            return False
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            msg['Subject'] = f"¡Alerta de Precio! Laptop Lenovo ThinkBook"
            
            body = f"""
            ¡Hola!
            
            Encontramos esta alerta de precio para la laptop que estabas buscando:
            
            Detalles del Producto:
            ---------------------
            - Título: {product_data.title}
            - Precio (Extraído): {product_data.price_usd}
            - Envío a Colombia: {'Sí' if product_data.ships_to_colombia else 'No/Desconocido'}
            
            Enlace de Compra:
            {product_data.url}
            """
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Setup conexión segura SMTP
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.set_debuglevel(0)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Correo de alerta enviado con éxito a {self.recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"Falla al enviar correo: {e}")
            return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    notifier = EmailNotifier()
    class MockProduct:
        title = "Mock Lenovo ThinkBook 16"
        price_usd = 699.99
        ships_to_colombia = True
        url = "https://www.amazon.com"
        
    if notifier.sender_email:
        notifier.send_alert(MockProduct())
    else:
        print("Falta .env, email no será enviado en el standalone test.")
