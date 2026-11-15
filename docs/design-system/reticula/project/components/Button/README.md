Botón rectangular de acción con texto en mayúsculas, relleno de naranja o con contorno de `ink`.

**El consumidor aporta**
- El texto en `children`, de una a tres palabras, y `onClick`.
- `type="submit"` dentro de formularios.

**Cuándo usar**
- `primary` para la acción principal de la vista, una sola por zona.
- `secondary` para acciones de apoyo o cancelar.
- `arrow` solo para avanzar a un paso siguiente.

**Qué evitar**
- Botones con solo icono: para eso está `IconButton`.
- Texto blanco sobre naranja: el botón usa `on-signal`.
- Dos botones `primary` juntos.

El botón rectangular es una adición del sistema: las imágenes solo muestran botones circulares.
