# NASA Space Apps 2026: análogos terrestres de la Luna y Marte

Proyecto del equipo Endurance CXXV: **Planetary Analog Finder**, un buscador de sitios en la Tierra análogos a sitios de la Luna y Marte, comparados con datos abiertos de topografía y capas térmicas. El procesamiento pesado corre en la supercomputadora Yuca (UniSon) y la app consume el JSON resultante.

Estado: prototipo. El pipeline corre de punta a punta; los pendientes están en la [bitácora](docs/logbook.md).

## Estructura

| Ruta | Qué contiene |
| --- | --- |
| `setup_and_download.sh`, `download_full_night.sh` | Descarga inicial de datos en Yuca (ya corrida) |
| `run_download_missing.slurm` | Job que baja lo que faltó, con URLs corregidas |
| `run_download_extra.slurm`, `download_earthdata.py` | Job de capas terrestres extra: MODIS (NDVI, LST) y Natural Earth |
| `tools/explore_datasets.py`, `jobs/explore_datasets.slurm` | Reporte HTML para explorar los datasets descargados |
| `docs/implementation_plan.md` | Plan de la v2 tarea por tarea (para implementar con Gemini) |
| `docs/plan_t4.md` | Plan detallado de T4 (blancos curados y clusters) |
| `docs/gemini_prompt.md` | Prompt de trabajo para Gemini 4 Orchestrator (con y sin SSH a Yuca) |
| `docs/handoff.md` | Estado por tarea, JOBIDs y cola de comandos pendientes en Yuca |
| `docs/HISTORY.md` | Project history in English: decisions, reasons, commits and Slurm jobs |
| `docs/submission.md` | Qué se entrega, checklist y cronograma del 14 y 15 de noviembre |
| `docs/working_without_ssh.md` | Trabajar sin SSH: flujo por Open OnDemand, kit offline y plan B |
| `process_analogs.py`, `run_clustering.slurm` | Arquetipos de Marte y la Luna (k-means sobre ventanas del DEM) |
| `enrich_nomenclature.py` | Nombres IAU para cada arquetipo |
| `match_earth_analogs.py`, `run_earth_matching.slurm` | Búsqueda de análogos en Copernicus GLO-90 |
| `output/` | `planetary_baselines.json` y `analogs.json` de la última corrida |
| `logs/` | Logs de descargas y de los jobs de Slurm |
| `docs/pipeline.md` | Cómo funciona el pipeline, datos y corridas |
| `docs/value_proposition.md` | Problemática, propuesta de valor y diferenciadores, para presentación y video |
| `docs/logbook.md` | Registro de lo que se ha hecho y pendientes |
| `docs/master_plan.md` | Plan completo (meta, no estado actual) |
| `docs/ideas.md` | Ideas del equipo y su evaluación |

Los rasters (~32 GB más los tiles de Copernicus) viven en Yuca en `/lustre/proyectos/p089/data` y no se suben al repo.

## Challenge

Notas de referencia del challenge, revisadas el 1 de noviembre de 2026.

- **Challenge:** [Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/)
- **Dificultad:** avanzada, intermedia y principiante/juvenil
- **Temas:** ciencias de la Tierra, planetas y lunas, software, exploración espacial

## Equipo: Endurance CXXV

[Página del equipo](https://www.spaceappschallenge.org/2026/find-a-team/endurance-cxxv1/). Tiene 6 integrantes, el máximo permitido, y no busca más gente.

- Fernando Borquez Guerrero (aparece como Team Owner)
- Owen Adiel Solis Zatarain
- Emily Beltrán Zazueta
- Flor María Machado Félix
- Elías Peregrina Cázares
- Javier Leonardo Miranda Sanchez

## Sede: NASA Space Apps Sonora (Tec de Monterrey)

El equipo está inscrito en **NASA Space Apps Sonora 2026**, en el Tec de Monterrey, Campus Sonora Norte, Salón de Congresos, Hermosillo. Antes el README apuntaba a la sede de la UTH; ese **no** es nuestro evento. Información revisada el 2026-11-13 en [spaceappssonora.org](https://spaceappssonora.org/) y en su [guía de pitches](https://spaceappssonora.org/pitches).

| Día | Horario (hora de Hermosillo) | Qué ocurre |
| --- | --- | --- |
| Viernes 13 | 14:00–16:00 | Bootcamp, Salón de Congresos |
| Viernes 13 | 16:00 | Inauguración |
| Sábado 14 | 9:00–21:00 | Hackathon (comida a las 13:00) |
| Domingo 15 | 9:00–14:00 | **Pitches** y cierre |

- **Contacto:** el grupo de WhatsApp de participantes, que es obligatorio, más Instagram y Facebook. La página no publica correo ni nombres de los organizadores.
- **Mentores:** Edgar León (Tec de Monterrey), Julio Waissman (UNISON), Eddy Varela, Jesús Medina, Octavio López y Michelle Sesteaga.
- **Hora límite de entrega:** la página no la da. El cierre global es el 15 a las 23:59, pero los pitches son el domingo en la mañana, así que todo debe estar listo **antes del pitch**. Confirmarlo en el grupo de WhatsApp.
- **Red:** la red de la sede bloquea SSH; usar Open OnDemand ([working_without_ssh.md](docs/working_without_ssh.md)).

### Qué hay que entregar (reglas de la sede)

Checklist completa y cronograma ajustado en [docs/submission.md](docs/submission.md).

- **Pitch:**
  - máximo **3 minutos**, sin preguntas;
  - puede ser en español;
  - láminas en **Canva**, con el nombre del proyecto y el **número de equipo** en la primera;
  - estructura sugerida: problema y contexto, luego solución y tecnología, luego impacto y escalabilidad (un minuto cada parte).
- **Documentación en inglés:** en la página del proyecto en spaceappschallenge.org.
- **Video en inglés:** en YouTube, de **máximo 30 segundos** (problema 5 s, solución 15 s, impacto 10 s).
- **App web publicada** para que los jueces la prueben; verificar el enlace antes de entregar.
- **Criterios de evaluación:**
  - innovación tecnológica;
  - impacto social;
  - documentación;
  - escalabilidad.

## Qué pide

Buscar en la Tierra lugares, ambientes o procesos que sirvan como análogos de posibles bases lunares permanentes o de sitios de aterrizaje y exploración en Marte. Hay que caracterizarlos con datos abiertos de la NASA y de otras agencias, y presentar los resultados como mapa, visualización u otra herramienta.

La solución debe explicar:

1. Qué características o procesos hacen fuerte la analogía.
2. Dónde se rompe la analogía.
3. Cómo ayudaría ese análogo a preparar la exploración de la Luna o Marte.

## Formatos aceptados

Reporte escrito, mapa interactivo, visualización, app, historia, sistema de ranking por similitud, herramienta de machine learning, juego u otro enfoque. Puede centrarse en un solo lugar, comparar varios o proponer un método sistemático de búsqueda global.

## Dimensiones de comparación sugeridas

- Geología, mineralogía y materiales de superficie
- Terreno, elevación, pendiente, rugosidad y cráteres
- Temperatura, iluminación y extremos ambientales
- Agua, hielo, permafrost y otros recursos
- Polvo, viento, erosión y procesos atmosféricos
- Biología, extremófilos, habitabilidad y biofirmas
- Cuevas, tubos de lava y otros ambientes subterráneos
- Condiciones para aterrizaje, movilidad, navegación, operaciones y construcción

## Lo que el challenge recalca

- **No basta el parecido visual:** la analogía debe justificarse con datos.
- **No hace falta que coincida todo:** un sitio puede ser buen análogo geológico y mal análogo térmico.
- **Los procesos también cuentan:** no solo los lugares, también sedimentación, tormentas de polvo, vulcanismo o dinámica del hielo.
- **Hay que ir más allá de lo conocido:** Antártida, Atacama, Islandia y Hawái ya están muy estudiados, y no se busca solo redescubrir sitios famosos.
- **La escala importa:** un cráter, valle o sistema de cuevas concreto puede ser mejor análogo que un desierto entero.
- **Hay que conectar con la exploración:** cómo ayuda a probar instrumentos, preparar operaciones, buscar recursos o reducir riesgos.
- **La Tierra tiene límites:** no reproduce la gravedad reducida, el vacío lunar, la atmósfera tenue de Marte ni su radiación. Reconocerlo es parte de un buen análisis.

## Fechas (2026)

| Fecha | Qué ocurre |
| --- | --- |
| 3 de noviembre | Abre Space Apps Connect y su guía |
| 13 de noviembre | Se publican los recursos del challenge, las Global Offers y las guías de entrega y de evaluación |
| 14 de noviembre, 9:00 | Abre la entrega de proyectos (hora local) |
| 15 de noviembre, 23:59 | Cierra la entrega de proyectos (hora local); también cierran registro, evento y equipos |
| 30 de noviembre | Encuesta de participantes |
| Diciembre | Anuncio de nominados, finalistas y menciones honoríficas |
| Enero de 2027 | Anuncio de ganadores globales |

## Reglas clave

- **No se puede empezar antes:** la regla global dice que no se trabaja en el challenge antes del 14 de noviembre. **Nuestra sede nos dio permiso de empezar desde el 13** (confirmado por Owen el 2026-11-13).
- **Equipos:** máximo 6 personas. El mínimo para la evaluación global es 1 en un Local Event como el nuestro.
- **Una sola participación:** cada persona va en un solo equipo y cada equipo aborda un solo challenge.
- **Entrega:** se hace desde la página del proyecto del equipo. Hay que seguir la hora de cierre del Local Event elegido.
- **Uso de IA:** está permitido, pero la entrega debe describir cómo se usó. El sitio la llama "Super Intelligence" (SI).
- **Menores de 18:** los registra su madre, padre o tutor, y aplican restricciones de fotos, voz e imagen.

## Pendientes antes del hackathon

- [x] Formar equipo para este challenge (Endurance CXXV)
- [x] Inscribirse en NASA Space Apps Sonora (Tec de Monterrey, Campus Sonora Norte)
- [ ] Confirmar en el grupo de WhatsApp la hora límite de entrega y el número de equipo
- [ ] Revisar los recursos y las guías del 13 de noviembre

## Fuentes

- [Página del challenge](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/)
- [Pasos del hackathon 2026](https://www.spaceappschallenge.org/2026/)
- [Preguntas frecuentes para participantes](https://www.spaceappschallenge.org/resources/participant-faqs/)
- [NASA Space Apps Sonora 2026](https://spaceappssonora.org/) y su [guía de pitches](https://spaceappssonora.org/pitches)
