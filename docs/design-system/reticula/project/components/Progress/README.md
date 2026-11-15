Barra de progreso con marco de 1px, relleno naranja, lectura en porcentaje y una cola opcional de rayas de peligro.

**El consumidor aporta**
- `label` corto (aparece en mayúsculas) y `value` entre 0 y 1.
- El ancho del contenedor: la barra ocupa todo el ancho disponible.

**Cuándo usar**
- Procesos con avance conocido. Para esperas sin porcentaje no hay componente.
- La cola de rayas cuando la barra no es el único ornamento de la zona; `hazard={false}` si ya hay otro.

**Qué evitar**
- Quitar la lectura en porcentaje: el naranja sobre el marco no distingue el avance por sí solo.
- Más de tres barras apiladas.
