Mosaico rectangular con chaflán de 45° arriba a la derecha, etiqueta en la cabecera y un código grande abajo.

**El consumidor aporta**
- `label` y `note` en texto corto, que el panel pone en mayúsculas.
- `code` de dos a cuatro caracteres (`A0.`, `2.C`); si es más largo, usa `Headline` fuera del panel.
- El ancho y el alto: el panel mide al menos 192px de alto y se estira a su contenedor.
- `children` solo para datos pequeños (`Readout`, `Progress`).

**Cuándo usar cada tono**
- `signal`: el mosaico activo o el foco de la composición; texto `on-signal`.
- `tint`: módulo secundario cerca de uno `signal`.
- `graphite`: estado inactivo o contenido de apoyo; texto `on-graphite`.
- `raised`: contenido que se lee de corrido sobre `surface`.
- `sunken`: espacio reservado o vacío.
- `outline`: panel que debe recibir otro elemento encima.

**Qué evitar**
- Más de un panel `signal` por zona de la composición.
- Poner `signal-ink` sobre `sunken` (3,5:1 en Hangar).
- Apilar sombras o bordes redondeados: el panel no los admite.
