RETÍCULA es una interfaz de consola de telemetría: fondo gris claro, una sola tinta de señal naranja, grafito para la estructura y tipografía monoespaciada en mayúsculas. Se compone como un panel de instrumentos: mucho vacío, grupos pequeños de datos y geometría fina.

## Contenido y voz

- Escribe como el sistema que informa, no como una persona: sin "tú", sin "yo", sin exclamaciones, sin emoji. Frases nominales y estados cortos.
- Todo texto de interfaz va en MAYÚSCULAS (etiquetas, titulares, botones, estados). Solo el texto corrido (`body`, `lead`, `footnote`) usa mayúsculas y minúsculas.
- Los identificadores se escriben como códigos con punto o guion como separador y ceros a la izquierda: `CARGA.4139.A64`, `SECTOR 45-A46AF`, `00E-1`.
- Los estados van entre corchetes cuando son una anotación: `[SEGURIDAD DE TRIPULACIÓN]`, `[ERROR DE SISTEMA]`.
- Ejemplos de la voz: "PROTOCOLOS DE CIFRADO CUÁNTICO", "CALIBRACIÓN LISTA", "CONTROL DE VUELO", "OPERATIVO", "COMPROBADO", "INICIADO".
- Un estado se dice con palabras, nunca solo con color: `OPERATIVO` y `INICIADO` llevan su etiqueta aunque el relleno ya sea naranja o grafito.

## Fundamentos visuales

**Color**
- Toda composición empieza en `surface`. El naranja `signal` es la única tinta de acento y ocupa normalmente menos de una sexta parte del área; los mosaicos completamente naranjas son la excepción de las láminas de tarjetas.
- Estructura en `graphite`; paneles elevados en `surface-raised` (blanco); mosaicos vacíos o inactivos en `surface-sunken`; el naranja velado `signal-tint` para módulos translúcidos.
- Texto: `ink` para lo principal, `ink-muted` para datos y cuerpo. Texto naranja sobre claro: solo `signal-ink`. `signal` nunca es color de texto ni de borde informativo sobre `surface` (1,8:1).
- Texto sobre relleno naranja: `on-signal`. Sobre `graphite`: `on-graphite`.
- `surface-paper` y `surface-cool` son fondos de láminas de especímenes y de logotipo, no de interfaz.
- Vigilia es el tema oscuro: mismos roles, el naranja se usa también como color de texto (`signal-ink` = `signal`).

**Tipografía**
- Display y etiquetas: Martian Mono, en mayúsculas. Titulares grandes en peso 300 con tracking 0,12em (`display-a`); códigos en un panel con `code`. Para cifras secundarias a tamaño display usa la clase `tm-outline` (contorno de 1px, sin relleno).
- Texto corrido: Roboto en columnas estrechas (30 a 40 caracteres), `body` en `ink-muted`. Citas: `quote`, Roboto Condensed en mayúsculas.
- Nunca menos de 11px (`label`). Un solo `display-a` por vista.
- Carga las fuentes con `<link href="https://fonts.googleapis.com/css2?family=Martian+Mono:wght@300;400;500;700&family=Roboto:wght@300;400;500&family=Roboto+Condensed:wght@400&display=swap" rel="stylesheet">`. Sin ellas caen a `Share Tech Mono` y a la fuente del sistema.

**Espacio y composición**
- Rejilla de 4px (`space-1` a `space-9`); la retícula de puntos usa `dot-size` y `dot-pitch` (4px cada 16px) y todo bloque decorativo se mide en múltiplos de `dot-pitch`.
- Dos columnas principales con un hueco amplio (`space-7`); composición asimétrica con bloques alineados al borde izquierdo de su columna. Deja vacío entre el 40% y el 60% del lienzo: el vacío es parte del diseño.
- Los datos pequeños se agrupan en racimos (etiqueta, línea de datos, retícula) y se separan con `space-5` o más.

**Forma, borde y profundidad**
- Ángulos rectos (`radius-0`). El único corte es el chaflán de 45° en la esquina superior derecha de paneles y mosaicos (`chamfer-md`; `chamfer-lg` desde 320px de lado).
- Círculos (`radius-round`) solo en `IconButton` y en los círculos grandes decorativos.
- Sin sombras, sin degradados, sin desenfoque. La profundidad sale del valor del relleno y de líneas: `stroke-hairline` (1px) para marcos, `stroke-line` (2px) para anillos y bordes de control, `stroke-bar` (4px) para reglas naranjas, `stroke-heavy` (8px) para barras.
- Las rayas de peligro (`Hazard`) y las barras segmentadas (`Barcode`) son ornamento de borde: una por composición como máximo.

**Estados**
- Hover: el borde pasa de `line` a `ink`; los botones rellenos pasan a `ink` con texto `surface`.
- Activo o seleccionado: anillo en `ink` y la marca `tick-left` en naranja a su lado.
- Foco: anillo sólido `focus` de 2px con separación de 2px, siempre fuera del relleno.
- Deshabilitado: `surface-sunken` con `ink-muted`.
- Movimiento: no hay movimiento definido. Cambia los estados al instante; si animas, 120ms lineales como máximo y respeta `prefers-reduced-motion`.

**Imágenes**
- No hay fotografía ni ilustración dentro de la interfaz. Una imagen pendiente se marca con `Frame` (caja con aspas y pie de figura `FIG.003`).

## Iconografía

- Las marcas son pictogramas de instrumento, no iconos ilustrativos: miras (`plus`, `close`), tics (`tick-left`, `tick-right`), esquinas (`bracket`, `corner`), barras oblicuas (`slash`, `slash-pair`), chevrones y puntos. Todas se dibujan en `Glyph`, sobre una rejilla de 24px con trazo de 1,5px (3 a 3,5px en barras y chevrones), extremos rectos y huecos deliberados en cruces y esquinas.
- Se pintan con `currentColor`: `ink`, `muted`, `graphite`, o `signal` solo como adorno junto a un elemento que ya dice lo mismo con texto.
- No uses emoji, fuentes de iconos ni iconos rellenos. Si falta un pictograma, dibújalo con la misma gramática (líneas finas, huecos, 45°) antes de importar otro estilo.
- No hay logotipo: el nombre RETÍCULA se escribe en `display-a` o `display-c`, en mayúsculas.

## Componentes

- `Panel`: mosaico con chaflán, etiqueta arriba y código grande abajo. Tonos `raised`, `signal`, `tint`, `graphite`, `sunken`, `outline`.
- `Headline`: regla naranja, titular display, subtítulo en `signal-ink` y firma.
- `Tag`: etiqueta de estado rellena de `graphite`, `signal` o con contorno; admite corchetes.
- `Readout`: lista de pares etiqueta/valor en mini mono, con estados.
- `Progress`: barra con lectura en porcentaje y cola de rayas.
- `Button` e `IconButton`: acción rellena de naranja o con contorno; el segundo es un círculo con mira y siempre lleva `label`.
- `Frame`: marcador de imagen con pie de figura.
- `Hazard`, `DotGrid`, `Barcode`, `Glyph`: ornamento y marcas.
- Adición intencional: `Button` rectangular. Las imágenes solo muestran botones circulares; el rectangular se deriva de `Tag` y de los anillos para tener una acción primaria con texto.

## Accesibilidad

- Cada pareja de texto cumple 4,5:1 en ambos temas con los tokens indicados en su nota; el texto display de 24px o más sobre `surface` puede usar `graphite` (3,7:1).
- El naranja sobre `surface` (1,8:1) y el blanco sobre naranja (2,4:1) que aparecen en las imágenes fallan: úsalos solo como relleno y marca, y en texto emplea `signal-ink` y `on-signal`.
- Los estados se acompañan siempre de palabra o marca (`Tag`, porcentaje, `tick-left`); no dependen solo del tono.
