# TODO

## Performance

- [x] El modelo actual consume su limite de MAX_IMAGENES_POR_PARTIDA muy rápido, debería esparcirlo mas acorde a su limite de MAX_TURNOS_POR_PARTIDA.
- [x] El modelo LLM (gpt-4.1-mini) es bastante lento para generar el texto de cada Turno.
- [x] El modelo de Imágenes (gpt-image-2) es tarda bastante en generar las imágenes.

## UX

- [x] Listar todas las partidas con los siguientes datos: Nombre de Personaje, Turno, Código de Partida.
- [x] Agregar la opción de resumir una partida, ya sea mediante la lista de partidas o ingresando el Código de Partida.
- [x] Al querer iniciar una partida, debería haber un botón (con forma de dados) que genere la descripción de un personaje al azar, respetando el genero elegido y el limite de caracteres máximo (300).
- [x] Al seleccionar la imagen abrirla como un modal para hacer zoom.
- [x] Agregar una sidebar con la lista de partidas para reanudar, y en el encabezado la opción de volver a la pantalla inicial.

## Storytelling

- [ ] ¿Como podría narrar el modelo LLM historias mas interesantes?
- [ ] Tratar de que el modelo LLM cierre la historia en su limite de MAX_TURNOS_POR_PARTIDA.
- [ ] Objetivo e Items en el Inventario están en ingles.
- [ ] Incluir RAG en la arquitectura para mejorar la coherencia del modelo y optimizar uso de tokens.
