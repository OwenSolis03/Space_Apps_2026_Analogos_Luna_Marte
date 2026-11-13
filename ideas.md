# Registro de ideas

Ideas del equipo, discutidas antes del hackathon. Solo contiene las ideas y una evaluación general hecha con Claude, sin datos, herramientas ni sitios. Las evaluaciones son provisionales hasta ver los recursos oficiales del 13 de noviembre. Incluir este registro en la descripción de uso de IA de la entrega.

## Idea 1: app de sitios análogos con puntaje ajustable

**Propuso:** Owen

**Idea:** Tomar el mapa planetario completo, con todas las capas de información posibles, y usar modelos de procesamiento de imágenes para identificar sitios análogos a la Tierra. Después contrastar capa por capa, asignando a cada sitio un puntaje que se ajusta conforme se procesan las capas, tomando en cuenta recursos, radiación, accesibilidad, altitud y otros parámetros. Al final habría una lista que se puede reordenar según cuánto importa cada parámetro. El resultado sería una app que muestra el sitio, su análogo terrestre y los parámetros similares, y que podría indicar para qué tipo de misión sirve el sitio.

**Evaluación:** factible si se reduce el alcance; dudosa tal como está.

| Parte | Evaluación | Razón |
| --- | --- | --- |
| Planeta completo con todas las capas | Dudosa | Demasiado alcance para 48 horas |
| Modelos de procesamiento de imágenes | Dudosa | Entrenarlos y validarlos consume mucho tiempo, y el reto pide ir más allá del parecido visual |
| Puntaje capa por capa | Factible | La lógica es simple si las capas son comparables |
| Lista reordenable según prioridades | Factible | Solo recalcula un puntaje con otros pesos |
| Radiación y otros parámetros sin equivalente terrestre | Dudosa | No se pueden puntuar igual que los que sí son comparables |
| App que muestra sitio, análogo y parámetros | Factible | Es alcanzable si los resultados ya están calculados |
| Tipo de misión por sitio | Factible | Es alcanzable como agregado menor |

**Encaje con el reto:** falta mostrar dónde se rompe la analogía, algo que el reto pide de forma explícita.

### Versión 2: recortada

**Envió:** Owen

**Idea:** Quitar el entrenamiento de modelos y el planeta completo. Usar una base de datos precalculada de sitios clave, con pesos para reordenar la lista según la misión. La ficha de cada lugar tendría una sección "Límites del análogo" que explique qué variables sí coinciden, como mineralogía o terreno, y cuáles no tienen punto de comparación en la Tierra, como la atmósfera o la dosis de radiación.

**Evaluación:** factible.

| Parte | Evaluación | Razón |
| --- | --- | --- |
| Base precalculada de sitios clave | Factible | El alcance es manejable, siempre que se arme a partir del 14 de noviembre |
| Pesos para reordenar según la misión | Factible | Solo recalcula un puntaje con otros pesos |
| Sección "Límites del análogo" | Factible | Responde directamente a lo que pide el reto |
| Coincidencias sin cálculos | Dudosa | El reto pide justificar la analogía con datos, no solo describirla |
| Selección de los sitios | Dudosa | Elegirlos a mano puede llevar a repetir análogos conocidos, y el reto busca ir más allá |

### Versión 3: con índice numérico y clustering

**Envió:** Owen

**Idea:** Armar un vector numérico normalizado por sitio, con elevación, pendiente, albedo, abundancia mineralógica y rango térmico, y calcular un índice de similitud, como similitud de coseno o distancia euclidiana normalizada, contra sitios terrestres. Para no elegir los sitios a mano, correr clustering no supervisado, como K-Means o DBSCAN, sobre una muestra más amplia. Procesar la carga pesada en la supercomputadora Yuca y llevar a la app solo los clusters resultantes.

**Evaluación:** factible en su núcleo; dudosa si depende de Yuca o de todas las métricas.

| Parte | Evaluación | Razón |
| --- | --- | --- |
| Índice de similitud con fórmula comprobable | Factible | Es poco código, y da un resultado verificable |
| Elevación, pendiente y albedo en el vector | Factible | Son comparables si se igualan escala y método de medición |
| Abundancia mineralógica en el vector | Dudosa | Puede no medirse de forma equivalente entre cuerpos |
| Rango térmico en el vector | Dudosa | Los rangos de la Luna o Marte pueden quedar fuera de los terrestres y dominar la distancia |
| Porcentaje de parecido | Dudosa | Depende de las métricas y los pesos elegidos, así que no es una medida absoluta |
| Clustering sobre una muestra amplia | Factible | Es alcanzable si la muestra es acotada y se revisan los grupos |
| Obtener clusters "novedosos" | Dudosa | Un cluster agrupa datos, pero no demuestra que un sitio sea novedoso ni buen análogo |
| Procesar en Yuca | Dudosa | Las colas, la transferencia de datos y el acceso desde la sede pueden fallar en 48 horas; también falta confirmar que el uso esté permitido |

## Ideas complementarias para la ficha de cada sitio

**Envió:** Owen

| Idea | Descripción | Evaluación | Razón |
| --- | --- | --- | --- |
| Bitácora de misión ficticia | Pestaña tipo diario de un astronauta o geólogo planetario, que contrasta la experiencia en el sitio terrestre y en el sitio objetivo | Factible | Cuesta poco, pero debe marcarse como ficción para no confundirse con los resultados |
| Protocolo de entrenamiento en la Tierra | Tarjeta que indica para qué le serviría el sitio a una agencia, como pruebas de movilidad de rovers o simulaciones de aislamiento | Factible | Conecta con lo que pide el reto, siempre que cada recomendación se derive de los parámetros del sitio |
| Impacto logístico y factor humano | Escala cualitativa de hostilidad para una persona: fatiga visual por albedo, complejidad psicológica del paisaje, dificultad de maniobra con traje | Dudosa | Es fácil de mostrar, pero difícil de justificar con datos y podría parecer opinión |
| Curiosidades históricas y cultura pop | Una línea con datos como misiones que entrenaron en ese análogo u obras inspiradas en el sitio | Factible | Es poco trabajo, pero requiere citar fuentes, y un sitio poco conocido puede no tener historia que contar |
