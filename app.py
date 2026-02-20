import asyncio
import gradio as gr
from scraper import AmazonScraper
from notifier import EmailNotifier

def run_tracking():
    # Creamos un loop asincrónico para Gradio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    scraper = AmazonScraper()
    resultados = loop.run_until_complete(scraper.scrape())
    
    if not resultados:
        return "No se encontraron resultados o Amazon bloqueó la solicitud.", []
    
    # Preparar datos para la tabla y verificar alertas
    notifier = EmailNotifier()
    data = []
    alertas_enviadas = 0
    alerta_thresh = 750.00
    
    for r in resultados:
        envio_col = "Sí" if r.ships_to_colombia else "No / N/D"
        # Convertir a texto para la UI
        precio_texto = f"${r.price_usd:,.2f}" if r.price_usd else "N/D"
        
        # Enviar alerta si aplica
        if r.price_usd and notifier.target_price_met(r.price_usd, alerta_thresh):
            enviado = notifier.send_alert(r)
            if enviado:
                alertas_enviadas += 1
                
        # Link en Markdown para la UI
        link_md = f"[Ver en Amazon]({r.url})"
        
        data.append([r.title, precio_texto, envio_col, link_md])
        
    status = f"Búsqueda exitosa. Se extrajeron {len(resultados)} productos."
    if alertas_enviadas > 0:
        status += f"\n¡Se enviaron {alertas_enviadas} alertas al email por precios menores a ${alerta_thresh}!"
        
    return status, data

with gr.Blocks(theme=gr.themes.Soft(primary_hue="blue")) as demo:
    gr.Markdown("# 🛒 Rastreador de Precios Amazon")
    gr.Markdown("### Objetivo: Lenovo ThinkBook 16")
    
    with gr.Row():
        buscar_btn = gr.Button("🔍 Buscar Laptop Ahora", variant="primary")
        
    status_box = gr.Textbox(label="Estado de la Búsqueda", interactive=False)
    
    resultados_tb = gr.Dataframe(
        headers=["Título", "Precio (USD)", "Envío a Colombia", "Enlace"],
        datatype=["str", "str", "str", "markdown"],
        label="Resultados de Amazon",
        wrap=True
    )
    
    buscar_btn.click(
        fn=run_tracking,
        inputs=[],
        outputs=[status_box, resultados_tb]
    )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)
