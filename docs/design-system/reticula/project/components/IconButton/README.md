Botón circular de 40px con un anillo de `stroke-line` y una marca de instrumento dentro.

**El consumidor aporta**
- `label`, obligatorio: el botón no tiene texto visible y el nombre accesible sale de ahí.
- `glyph` entre los nombres de `Glyph`; `plus`, `close` y `dots` son los habituales.
- `pressed` si el botón alterna un estado.

**Cuándo usar**
- Controles de panel que se repiten (añadir, cerrar, abrir menú).
- Pares como `plus` y `close` a la cabecera de un panel.

**Qué evitar**
- Usar `pressed` sin una señal de texto cercana que diga el estado.
- Cambiar el tamaño por debajo de 40px.
