Lista de pares etiqueta y valor en mini mono para lecturas de instrumento.

**El consumidor aporta**
- `items` con `label` y `value` cortos; `status: true` convierte el valor en un `Tag`.
- `title` opcional en mayúsculas.

**Cuándo usar**
- Racimos de datos junto a un panel o titular; la etiqueta va en `ink-muted` y el valor en `ink`.

**Qué evitar**
- Valores largos: la columna de valores no se ajusta de línea de forma cuidada.
- Usar el `Tag` para todos los valores: reserva el estado para los que cambian.
