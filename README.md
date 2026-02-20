# Rastreador de Precios Amazon - Lenovo ThinkBook 16

Este proyecto es una aplicación desarrollada en Python diseñada para buscar, extraer y monitorear el precio de las laptops "Lenovo ThinkBook 16" en Amazon. Incorpora una interfaz web profesional, técnicas de evasión de detección de bots, un sistema de notificaciones automáticas por correo electrónico y ejecución automatizada cada hora vía cron.

## 📌 Función del Programa

El objetivo principal es permitir a los usuarios hacer seguimiento del precio de la laptop **Lenovo ThinkBook 16** en Amazon de forma rápida, con dos modos de operación:

- **Interfaz web** — Frontend profesional (HTML/CSS/JS) con backend FastAPI para búsquedas interactivas.
- **Terminal** — Script `tracker.py` que ejecuta la búsqueda y envía alertas automáticamente sin necesidad de abrir el navegador.

El programa automatiza el acceso a la web, extrae información relevante (nombre exacto, precio en dólares `USD`, disponibilidad de envío a Colombia, y el enlace de compra), y muestra estos datos en tarjetas interactivas. Además, envía un **correo electrónico consolidado de alerta** si detecta productos con precio dentro del rango configurado (por defecto **$500.00 — $749.99 USD**).

## 🔄 Flujo del Programa

### Modo Web (`app.py`)

1. **Inicio del servidor:** Se levanta un servidor FastAPI que sirve el frontend estático y expone la API REST.
2. **Activación de Búsqueda:** El usuario ingresa el producto, configura el umbral de precio y presiona "Buscar en Amazon".
3. **Scraping Asíncrono:** Se ejecuta el scraper con Playwright (navegador visible para mayor confiabilidad).
4. **Resultados:** Se despliegan en tarjetas con precio, envío y enlace directo a Amazon.

### Modo Terminal (`tracker.py`)

1. **Ejecución directa:** `uv run tracker.py` lanza el scraper en modo headless (sin ventana).
2. **Alertas automáticas:** Envía un correo consolidado con todos los productos en rango.
3. **Cron:** Configurado para ejecutarse cada hora automáticamente.

## 📚 Librerías Utilizadas y Por Qué

- **`playwright` & `playwright-stealth`**: Amazon tiene protecciones estrictas contra bots. Playwright permite controlar un navegador Chromium real de forma asíncrona, y la extensión `stealth` inyecta configuraciones que camuflan el bot para parecer un usuario humano.
- **`fastapi` & `uvicorn`**: Backend API REST que sirve el frontend y procesa las búsquedas. Reemplaza a Gradio para tener control total del diseño de la interfaz.
- **`pydantic`**: Provee validación de datos. Garantiza que la información extraída siempre cumpla con el tipado exacto, evitando caídas inesperadas del programa.
- **`python-dotenv`**: Manejo de credenciales (correos, contraseñas, configuración SMTP) mediante un archivo local `.env`, evitando subir secretos al código fuente.
- **`asyncio`**: La asincronía evita que el servidor o el programa se bloquee durante las operaciones de red.

## 🏗️ Estructura del Proyecto

```
busqueda_laptop/
├── app.py               # Backend FastAPI + servidor web
├── tracker.py           # Ejecución automática sin interfaz
├── scraper.py           # Scraper de Amazon con Playwright
├── notifier.py          # Sistema de alertas por email
├── static/
│   ├── index.html       # Frontend HTML
│   ├── styles.css       # Estilos CSS (dark mode)
│   └── app.js           # Lógica JavaScript
├── pyproject.toml       # Dependencias del proyecto
├── .python-version      # Python 3.13
└── .env                 # Credenciales (no incluido en Git)
```

- **`app.py`** _(Backend)_: Servidor FastAPI con endpoint `/api/search`. Sirve el frontend estático y procesa las búsquedas.
- **`tracker.py`** _(Automatización)_: Script independiente que ejecuta el scraper en modo headless y envía alertas sin necesidad de interfaz web.
- **`scraper.py`** _(Extracción)_: Contiene `AmazonScraper` con toda la lógica de Playwright, simulación humana, reintentos y extracción de datos.
- **`notifier.py`** _(Servicio)_: Clase `EmailNotifier` que envía correos consolidados con todos los productos en rango de alerta.
- **`static/`** _(Frontend)_: Interfaz web con diseño dark mode profesional (Space Grotesk + DM Sans).

## ✨ Características Especiales

1. **Simulación de Comportamiento Humano**: El scraper navega primero a la homepage de Amazon, escribe en la barra de búsqueda carácter por carácter, mueve el mouse aleatoriamente y hace scrolls graduales.
2. **Reintentos Automáticos**: Hasta 3 intentos con espera progresiva si Amazon bloquea la solicitud.
3. **User-Agents Rotativos**: Selecciona aleatoriamente entre Chrome 131 en Linux, Windows y Mac.
4. **Fijación de Cookies de Divisa**: Inyecta la cookie `"i18n-prefs": "USD"` para evitar precios en moneda local (COP).
5. **Correo Consolidado**: En vez de enviar un correo por producto, envía uno solo con todos los deals encontrados, evitando rate limiting del servidor SMTP.
6. **Modo Dual**: `headless=False` para la interfaz web (mayor confiabilidad), `headless=True` para ejecución automatizada vía cron.
7. **Detección de Bloqueos**: Identifica automáticamente captchas, páginas de error y otros indicadores de bloqueo.
8. **Validación Escalada de Localizadores**: Prueba múltiples selectores CSS (`h2 span`, `h2`, `span.a-size-medium...`) para extraer títulos de forma robusta.
