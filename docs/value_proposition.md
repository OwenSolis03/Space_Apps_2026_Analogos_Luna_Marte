# Propuesta de valor: Planetary Analog Finder

Base para el equipo de presentación y video. Define qué problema resolvemos, qué ofrecemos, en qué vamos más allá de lo que pide la NASA y cómo nos distinguimos de otros equipos del mismo challenge. Revisado el 13 de noviembre de 2026 contra la [página del challenge](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/) y `output/analogs.json`.

## 1. La problemática

La NASA lo dice en el propio reto: los análogos terrestres que se usan hoy (Atacama, Haughton, Death Valley, Antártida, Islandia, Hawái) **no están bien caracterizados**, y se eligieron por experiencia o por parecido visual, no por una búsqueda sistemática.

Eso causa tres problemas concretos:

1. **Siempre los mismos sitios.** Las misiones se preparan en un puñado de lugares famosos, caros y remotos. Puede haber análogos mejores, o más baratos de usar, que nadie ha buscado.
2. **"Se parece" no es un dato.** Sin una métrica no se puede decir *qué tan* análogo es un sitio, *en qué* lo es y *en qué no*.
3. **Un análogo no sirve para todo.** Un sitio puede ser bueno para probar movilidad de rovers y malo para térmica. Hoy no hay una forma rápida de elegir el análogo según la prueba que se quiere hacer.

## 2. Propuesta de valor

**En una línea:**

> Un buscador que recorre la Tierra con datos abiertos y te dice qué lugar se parece, con números, a un sitio de la Luna o Marte, en qué se parece, en qué no y para qué prueba sirve.

**Versión de 30 segundos (elevator pitch):**

> Antes de ir a la Luna o a Marte, los equipos de misión ensayan en la Tierra, pero casi siempre en los mismos cinco lugares, elegidos porque "se ven parecidos". Planetary Analog Finder compara el relieve de la Luna y Marte contra el de la Tierra con datos de NASA, USGS y ESA, procesados en la supercomputadora Yuca de la Universidad de Sonora. El resultado es un ranking de sitios terrestres con un puntaje de similitud, la explicación de qué coincide, una sección de dónde se rompe la analogía, y pesos que el usuario ajusta según la misión. No redescubre Atacama: encuentra candidatos que nadie había mirado.

**Para quién (el usuario es el héroe, la herramienta es la guía):**

| Usuario | Qué gana |
| --- | --- |
| Ingeniero de misión | Elegir dónde probar un rover, un traje o una maniobra según el tipo de terreno que enfrentará |
| Geólogo planetario | Candidatos nuevos con métricas para justificar trabajo de campo |
| Agencias y universidades fuera de EE. UU. y Europa | Encontrar análogos cerca de casa, sin depender de sitios lejanos y caros |
| Público y estudiantes | Ver que un lugar que conocen "es" un pedazo de Marte o la Luna, y por qué no del todo |

## 3. Qué hacemos más allá de lo que pide la NASA

El reto pide identificar y caracterizar análogos, explicar qué coincide, dónde se rompe la analogía y cómo ayuda a la exploración. Esto es lo que cubrimos y lo que agregamos:

| Lo que pide la NASA | Lo que hace el proyecto | Por qué es diferente |
| --- | --- | --- |
| "Identificar uno o más lugares" | Búsqueda sistemática: 40 arquetipos de Marte y 40 de la Luna contra 21,906 ventanas de terreno terrestre | No partimos de una lista de sitios; los sitios salen del cálculo |
| "Ir más allá de la similitud visual" | Puntaje con métricas medibles del DEM: rugosidad, pendiente media, pendiente p90 y dispersión del relieve | La analogía se puede auditar y repetir |
| "Ir más allá de los sitios conocidos" | El método no sabe qué es Atacama; propone lo que mejor puntúa | Los candidatos nuevos son consecuencia del método, no de la intuición |
| "Considerar la escala" | Comparamos ventanas de decenas de km, no desiertos enteros | El análogo es un valle o una sierra concreta. Ojo: falta igualar la escala entre cuerpos (ver sección 6) |
| "Dónde se rompe la analogía" | Sección "Límites del análogo" en cada ficha: lo que coincide, lo que no, y lo que la Tierra no puede reproducir (gravedad, vacío, atmósfera, radiación) | La mayoría lo pondrá como nota al final; para nosotros es parte del resultado |
| "Conectar con la exploración" | Pesos ajustables por tipo de misión (movilidad, aterrizaje, construcción, térmica) | El mismo sitio cambia de rango según la prueba; el ranking responde a una pregunta de ingeniería |
| "Usar datos abiertos" | MOLA, THEMIS, LOLA, Copernicus GLO-90 y nomenclatura IAU | Cada arquetipo planetario tiene nombre oficial y cada análogo coordenadas verificables |

Lo que agregamos y el reto no pide:

- **Supercómputo real.** Procesamos decenas de GB de rasters en Yuca (UniSon). Es la razón por la que podemos buscar a escala global y no solo en una región.
- **Un ranking que se reordena.** No entregamos "el" análogo, sino una herramienta para elegirlo según la misión.
- **Logística como criterio.** Un análogo cercano a carreteras y aeropuertos cuesta menos de usar. Está en el plan maestro; aún no está en el pipeline.

## 4. Diferenciador frente a otros equipos

No podemos ver los proyectos de los demás equipos antes de la entrega, así que esto parte de los enfoques que el propio reto sugiere y de los más probables en un hackathon de 48 horas. Son hipótesis, no datos.

| Enfoque probable de otros equipos | Su límite | Nuestra respuesta |
| --- | --- | --- |
| Reporte sobre un sitio famoso (Atacama, Pinacate, Río Tinto) | Es justo lo que el reto pide superar: redescubre un análogo conocido | Los sitios salen de un cálculo global, no de una elección previa |
| Comparación de imágenes o ML visual | El reto advierte que "verse parecido" no basta | Comparamos métricas físicas del relieve, no píxeles |
| Mapa o catálogo de análogos conocidos | Organiza lo que ya existe; no descubre | Proponemos candidatos nuevos con su puntaje |
| Chatbot o app que explica con IA | Explica, pero no mide | Cada afirmación viene de un número calculado |
| Ranking de similitud sin límites | Da un porcentaje que parece absoluto | Mostramos en qué coincide, en qué no y qué la Tierra no puede reproducir |

**Nuestro diferenciador en una frase:** somos el equipo que *mide* la analogía a escala de planeta, con supercómputo, y que muestra con la misma claridad dónde se rompe.

**Ventaja local que nadie más tiene:** el equipo está en Sonora, con acceso a Yuca, y el desierto de Sonora y Baja California aparecen entre los candidatos del prototipo. Podemos decir "esto está a horas de aquí", algo que un equipo de otra región no puede decir de nuestros sitios.

## 5. Prueba: candidatos en México del prototipo actual

De `output/analogs.json` (corrida 2241783). Sirven como ejemplo, no como resultado final, por las limitaciones de la sección 6.

| Sitio objetivo | Análogo terrestre (lat, lon) | Zona aproximada | Rango | Puntaje |
| --- | --- | --- | --- | --- |
| Luna: cráter Schrödinger | 32.36, -115.79 | Norte de Baja California, cerca de Mexicali | 2 | 82.1 |
| Marte: cráter Louth | 30.79, -112.79 | Noroeste de Sonora | 4 | 96.4 |
| Luna: Bose A | 31.79, -110.36 | Frontera Sonora y Arizona | 3 | 97.8 |
| Luna: Repsold B | 31.79, -110.36 | Frontera Sonora y Arizona | 4 | 97.7 |
| Luna: Lacchini | 19.79, -101.79 | Centro de México | 5 | 94.8 |

Schrödinger es una cuenca de impacto cerca del polo sur lunar, la región de interés de Artemis, y Louth es un cráter marciano con hielo de agua en superficie. Son los ganchos más fuertes si sobreviven a las correcciones. Las zonas son aproximadas; hay que confirmar cada punto en un mapa antes de nombrarlo.

## 6. Lo que no debemos afirmar todavía

Para que el pitch aguante preguntas de los jueces:

- **No decir "encontramos el mejor análogo".** Los puntajes vienen de 4 métricas de relieve y la escala de las ventanas aún no es igual entre cuerpos (~118 km en Marte, ~30 km en la Luna, ~46 km en la Tierra).
- **No decir "cobertura global".** Solo hay 6,983 de 26,475 tiles terrestres, entre 0.4° y 45.8° N, y aún no hay máscara árida, por eso muchos análogos lunares caen en el Himalaya.
- **No presentar el puntaje como porcentaje absoluto.** Es una similitud relativa que depende de las métricas y los pesos.
- **No vender mineralogía, térmica o polvo como comparados** hasta que estén en el pipeline. Hoy solo el relieve entra al puntaje.
- **Los blancos del reto** (polo sur lunar / Artemis, sitios de aterrizaje en Marte) aún no son objetivos explícitos; los arquetipos salen de un k-means global.

Detalle y prioridades de corrección en la [bitácora](logbook.md).
