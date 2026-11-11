# Guion de la presentación (3 minutos)

Abrir antes: la app (https://transciptorcongress.streamlit.app) con la sesión ya elegida y el informe **ya generado** (se abre al instante), y una pestaña con el
video oficial. A los 3:00 cortan.

## 0:00 – 0:30 · Problema

«Una sesión de comisión dura entre una y cuatro horas. En una consultora de asuntos públicos alguien tiene que verla
completa para contarle al cliente qué se dijo sobre su sector. Hablé con tres personas que hacen ese trabajo:
[dato más fuerte de las notas]. Y no pueden usar un resumen automático cualquiera, porque no pueden citarle al cliente
algo que no saben si se dijo.»

## 0:30 – 2:30 · Demo en vivo

1. (0:30) Barra lateral: «Esta es la sesión del 20 de octubre de la Comisión de Energía y Minas, hora y media,
   del canal oficial. Mi cliente vigila minería, hidrocarburos y canon.» Escribir los temas del cliente y pulsar **Ver informe**.
2. (0:50) Indicadores: «44 citas, las 44 comprobadas contra la transcripción. Este informe costó 51 centavos de dólar.»
3. (1:05) Pestaña **Para tu cliente**: leer una mención de relevancia alta (el proyecto de ley de pequeña minería) y hacer clic en el minuto. Se abre el video
   oficial en ese segundo. «Esto no lo verificó el modelo: lo verificó un programa.»
4. (1:35) Pestaña **Informe**: acuerdos y pedidos con plazo. Botón **Descargar en Word** y abrir el archivo.
5. (1:55) En vivo: cambiar los temas (otro cliente) y pulsar **Generar informe**. Mientras Claude lee la sesión,
   mostrar la pestaña **Transcripción** y buscar una palabra.
6. (2:20) Llega el informe nuevo.

## 2:30 – 3:00 · Modelo de negocio

«Paga la consultora: 890 soles al mes por 20 sesiones. Cada informe me cuesta entre 30 y 50 centavos de dólar en tokens.
Usa dos herramientas del curso dentro del producto: Whisper y un LLM con salidas estructuradas. Relatoría: de la
sesión pública al informe verificable.»

## Si algo falla

- La API no responde: los informes guardados se abren sin llamar a la API.
- No hay internet: `docs/video_respaldo.mp4`.
