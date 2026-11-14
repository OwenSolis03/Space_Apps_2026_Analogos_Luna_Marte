# Entrega y cronograma (NASA Space Apps Sonora, 14 y 15 de noviembre)

Qué hay que entregar, quién lo hace y en qué orden, según las reglas de la sede: [spaceappssonora.org](https://spaceappssonora.org/) y su [guía de pitches](https://spaceappssonora.org/pitches), revisadas el 2026-11-13. Reemplaza al cronograma de 48 horas de `plan_implementacion.md` §6, que suponía dos días completos de trabajo.

**El tiempo real** es el sábado 14 de 9:00 a 21:00 más la mañana del domingo 15. Los pitches son el domingo entre las 9:00 y las 14:00, así que **todo debe estar entregado y publicado antes de que nos toque pasar**. Confirmar en el grupo de WhatsApp la hora límite exacta y nuestro número de equipo.

---

## 1. Qué se entrega

| # | Entregable | Idioma | Requisito de la sede | Responsable sugerido |
| --- | --- | --- | --- | --- |
| 1 | **Página del proyecto** en spaceappschallenge.org | Inglés | Documentación del proyecto; ahí se hace la entrega | P3 (documentación) con Owen |
| 2 | **Video en YouTube** | Inglés | **≤ 30 s**: problema (5 s), solución (15 s), impacto (10 s) | P4 (media) |
| 3 | **Pitch** | Español permitido | **≤ 3 min**, sin preguntas. Láminas en **Canva**; la 1.ª con nombre del proyecto y **número de equipo** | P1 (orador) y P4 |
| 4 | **App web publicada** | Inglés (ya lo está) | Que los jueces la puedan probar; verificar el enlace antes de entregar | Javier (T10) |
| 5 | **Repositorio** con README para instalar | Inglés en la parte que vean los jueces | Instalación, código y dependencias, datos y fuentes citados, capturas | Owen y Gemini |
| 6 | **Uso de IA** ("Super Intelligence") | Inglés | Lo exige la entrega global: describir cómo se usó la IA | Owen, a partir de `docs/bitacora.md` |

**Criterios de evaluación de la sede:**

| Criterio | Qué lo respalda | Qué falta |
| --- | --- | --- |
| Innovación tecnológica | Comparación con la misma métrica a la misma escala en los tres cuerpos (parches AEQD de 32 km), corrida en Yuca | — |
| Impacto social | **Poco trabajado.** Idea: sitios análogos accesibles y baratos en México y Latinoamérica para formar gente, probar instrumentos y hacer divulgación sin ir a la Antártida | Reforzarlo en `propuesta_de_valor.md` y en el minuto 3 del pitch |
| Documentación | `docs/` completo, bitácora y planes | Página del proyecto en inglés y README en inglés |
| Escalabilidad | La tubería es genérica: otro cuerpo u otra capa es otra fila de configuración; corre en HPC | Decirlo con un ejemplo concreto (ej. agregar Mercurio o una capa de radar) |

---

## 2. Cronograma

| Cuándo | Pipeline (Owen + Gemini, Yuca por OOD) | App (Javier) | Contenido (P1, P3, P4) |
| --- | --- | --- | --- |
| **Vie 13, noche** | T6 corrido y revisado. Código de T5 listo y probado en la laptop | Despliegue de prueba (GitHub Pages o Vercel) con `sample.json` | Confirmar el número de equipo; esqueleto del Canva |
| **Sáb 9:00–11:00** | T5: `--limit 500`, revisar y lanzar la corrida completa. Gemini escribe T7/T8 con el kit offline | Panel de pesos, ficha y "Where the analogy breaks" | `limits.json` (T11) y textos de protocolo |
| **Sáb 11:00–14:00** | T5 termina; correr T7/T8 y bajar `analogs_universe.json` por OOD | Conectar el JSON real en cuanto exista | Guion del pitch (3 min) |
| **Sáb 14:00** | **Punto de decisión**: si no hay JSON real, usar el plan B (§4) | — | — |
| **Sáb 14:00–18:00** | Revisión de sentido común (T7: el volcán en escudo para Olympus Mons) y una segunda corrida si hace falta | Desplegar con el JSON real; probar a 1366 × 768 | Láminas en Canva; página del proyecto en inglés |
| **Sáb 18:00–21:00** | **Congelar datos.** README en inglés, capturas de pantalla, texto de uso de IA | **Congelar código.** Verificar el enlace público | Grabar y subir el video de 30 s a YouTube; ensayar el pitch con cronómetro |
| **Dom antes del pitch** | Revisar los enlaces de la página del proyecto | Revisar que la app abre desde otra red (celular) | **Enviar la entrega** y último ensayo |

Los planes de T7/T8 todavía no existen; Claude los escribe cuando Owen lo pida. Para cumplir este cronograma tienen que estar listos el viernes en la noche.

---

## 3. Checklist antes de enviar

**Página del proyecto (inglés):**

- [ ] Problema, solución y resultados, con números reales de la corrida.
- [ ] Qué datos de NASA y de otras agencias se usaron, con enlaces: MOLA, THEMIS, LOLA, LROC WAC, Diviner, MODIS, Copernicus GLO-90, Natural Earth y el gacetero IAU.
- [ ] Qué **no** se resolvió: límites del análogo, rugosidad por debajo de 500 m, sin mineralogía. Base: "lo que no debe afirmarse" en `propuesta_de_valor.md`.
- [ ] Enlaces a la app, al repositorio y al video.
- [ ] Uso de IA: Claude (planes, documentación, revisión), Gemini (código del pipeline) y lo que haya usado el resto del equipo. Base: `docs/bitacora.md`.

**Repositorio:**

- [ ] README con una sección en inglés: qué es, cómo instalar y correr la app (`cd app && npm install && npm run dev`), cómo correr el pipeline (`pip install -r pipeline/requirements.txt`, los jobs) y una captura.
- [ ] Datos y fuentes citados, por ejemplo con una tabla que enlace a `docs/pipeline.md`.
- [ ] No reorganizar carpetas a última hora: la sede *sugiere* `/data`, `/models`, `/scripts` y `/docs`, pero no lo exige.

**App:**

- [ ] Enlace público que abre sin cuenta y desde otra red.
- [ ] Carga `analogs_universe.json` real, o `sample.json` con aviso si es el plan B.
- [ ] Mover un slider reordena la lista en menos de 50 ms (criterio de T10).

**Pitch y video:**

- [ ] 1.ª lámina: "Planetary Analog Finder" y el número de equipo.
- [ ] Minuto 1: problema y contexto. Minuto 2: solución y tecnología (demo). Minuto 3: impacto social y escalabilidad.
- [ ] El video dura 30 s o menos, está en inglés y en YouTube (público o no listado), con el enlace en la página del proyecto.
- [ ] Ensayado con cronómetro: 3:00 o menos.

---

## 4. Plan B (decidir el sábado a las 14:00)

| Situación | Qué se entrega |
| --- | --- |
| T5 terminó y T7/T8 no | La app con los blancos reales de T4 y los parches terrestres de T5, y un ranking calculado de forma simple. Decirlo en la página |
| T5 no terminó | La app con `sample.json` (v1 convertida); se muestran T3 y T4 como resultados v2 (mapas y blancos). Decir "full Earth run pending" |
| Sin acceso a Yuca | Igual que el anterior; el kit offline tiene T3 y los gaceteros |

En cualquier caso: **no afirmar resultados que no se corrieron.**

---

## 5. Riesgos que conviene tener presentes

- **Trabajo previo al 14 de noviembre: resuelto.** La sede dio permiso al equipo de empezar a trabajar desde el 13 de noviembre (confirmado por Owen). En la página del proyecto conviene decirlo así: la bitácora registra con fecha lo que se hizo cada día.
- **Red de la sede:** SSH bloqueado, OOD funciona ([operacion_sin_ssh.md](operacion_sin_ssh.md)). El despliegue de la app no depende de Yuca.
- **Un solo día útil:** si una corrida falla, diagnosticar antes de reenviarla. El tiempo no alcanza para varios intentos a ciegas.
