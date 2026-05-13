# TODO

## Performance
- El modelo actual consume su limite de MAX_IMAGENES_POR_PARTIDA muy rápido, debería esparcirlo mas acorde a su limite de MAX_TURNOS_POR_PARTIDA.
- El modelo LLM (gpt-4.1-mini) es bastante lento para generar el texto de cada Turno.
- El modelo de Imágenes (gpt-image-2) es tarda bastante en generar las imágenes.

## UX
- Listar todas las partidas con los siguientes datos: Nombre de Personaje, Turno, Código de Partida.
- Agregar la opción de resumir una partida, ya sea mediante la lista de partidas o ingresando el Código de Partida.
- Al querer iniciar una partida, debería haber un botón (con forma de dados) que genere la descripción de un personaje al azar, respetando el genero elegido y el limite de caracteres máximo (300).
- Al seleccionar la imagen abrirla como un modal para hacer zoom.

## Storytelling
- ¿Como podría narrar el modelo LLM historias mas interesantes?
- Tratar de que el modelo LLM cierre la historia en su limite de MAX_TURNOS_POR_PARTIDA.
- Items en el Inventario están en ingles.