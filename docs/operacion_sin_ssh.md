# Operación sin SSH a Yuca (14 y 15 de noviembre)

La red de la sede (UTH) bloquea SSH, así que durante el hackathon no habrá acceso a Yuca desde ahí. Este documento dice qué hacer **la noche antes** (mientras sí hay SSH), qué se puede avanzar **sin Yuca** y cómo **recuperar** el acceso. Escrito el 2026-11-13 por Claude.

---

## 1. Qué se pierde sin SSH

| Qué | Dónde vive | Sin SSH |
| --- | --- | --- |
| Código | GitHub y el clon de Yuca (`/lustre/proyectos/p089/code`) | Se trabaja en un clon local de la laptop y se sube a GitHub |
| Rasters (MOLA, THEMIS, LOLA, WAC, Copernicus 26,475 tiles, MODIS) | Solo Yuca (~80 GB) | **No disponibles.** No se pueden calcular rasgos nuevos |
| Corrida T3 (`runs/2242278/`) | Yuca | Disponible en el **kit offline** (sección 3) |
| Gacetero IAU, Natural Earth, caché de Diviner | Yuca | Disponibles en el kit offline |
| Jobs de Slurm | Yuca | **No se pueden enviar ni revisar** |
| Memoria de Claude Code | Yuca (`/lustre/home/owen/.claude/...`) | Claude en la laptop **no la tiene**; el contexto está en `docs/` del repo |

Consecuencia: todo lo que necesite rasters (T4 curados, T5, T6 con MODIS y las corridas de T7) **tiene que correr en Yuca**. Sin SSH se puede escribir y probar código, la app y el contenido.

---

## 2. Lista para la noche del 13 (con SSH)

En orden de prioridad:

1. **Repo al día en GitHub.** Desde la laptop, `git pull` en el clon local.
2. **Bajar el kit offline** a la laptop (sección 3).
3. **Entorno local en la laptop**, para que Gemini pueda correr las pruebas sin Yuca:

   ```bash
   cd <clon-local> && python -m venv .venv && source .venv/bin/activate && pip install -r pipeline/requirements.txt
   ```

   ```bash
   pytest -q tests
   ```

   Las pruebas son sintéticas y no tocan los rasters: deben pasar las 17 en la laptop. Para la app hacen falta Node 20 y `cd app && npm install`.
4. **Si Gemini termina T4 esta noche:** correr T4 en Yuca (menos de 15 minutos, ver `plan_t4.md` §11) y agregar los resultados al kit. Con eso T7 se puede desarrollar mañana con blancos reales:

   ```bash
   cd /lustre/proyectos/p089 && tar -czf kit/t4_<JOBID>.tar.gz runs/<JOBID>/targets.parquet runs/<JOBID>/targets.json runs/<JOBID>/clusters_mars.parquet runs/<JOBID>/clusters_moon.parquet
   ```

   y bajarlo igual que el kit (sección 3).
5. **No dejar jobs largos sin revisar.** T5 y T6 aún no tienen código, así que no hay nada pesado que dejar corriendo esta noche. No enviar jobs "por si acaso".

---

## 3. Kit offline

Ya está armado en Yuca:

- **Archivo:** `/lustre/proyectos/p089/kit/offline_kit_2026-11-13.tar.gz`
- **Tamaño:** 88 MB
- **sha256 (inicio):** `54cb3c5c0403a2dd`

| Ruta dentro del kit | Qué es |
| --- | --- |
| `runs/2242278/features_mars.parquet` | T3: 140,916 parches de Marte (rasgos + THEMIS) |
| `runs/2242278/features_moon.parquet` | T3: 36,741 parches de la Luna (rasgos + WAC, hielo y Diviner) |
| `runs/2242278/map_*_mean_slope_deg.png` | Mapas de control de T3 |
| `data/raw/nomenclature/{MARS,MOON}_nomenclature_center_pts.*` | Gacetero IAU (`.shp`, `.dbf`, …) |
| `data/raw/earth/naturalearth/ne_10m_{roads,airports,admin_0_countries}.zip` | Logística y países (T6 y T8) |
| `data/derived/diviner_prp_south.parquet` | Caché de Diviner PRP sur |

No incluye MODIS (2 GB) ni ningún raster.

Bajarlo **desde la laptop**. Usa el mismo usuario y host con los que entras por SSH:

```bash
scp owen@<host-de-yuca>:/lustre/proyectos/p089/kit/offline_kit_2026-11-13.tar.gz .
```

```bash
mkdir -p ~/p089_offline && tar -xzf offline_kit_2026-11-13.tar.gz -C ~/p089_offline
```

La carpeta `~/p089_offline` imita la estructura de `/lustre/proyectos/p089`. Los scripts del pipeline aceptan `--project-dir`, así que basta con pasarles `--project-dir ~/p089_offline`. Ejemplo: la parte de clusters de T4 corre en la laptop con

```bash
python -m pipeline.targets --project-dir ~/p089_offline --t3-dir ~/p089_offline/runs/2242278 --out-dir ~/p089_offline/runs/local_t4 --skip-curated
```

Los blancos curados **no** se pueden calcular sin los rasters.

---

## 4. Qué se puede avanzar sin Yuca

| Tarea | Sin Yuca | Cómo |
| --- | --- | --- |
| T4 código y pruebas | Sí | Todo, con pruebas sintéticas. Los clusters también corren con el kit (`--skip-curated`) |
| T4 corrida de curados | No | Queda en la cola (sección 6) |
| T6 código y pruebas | Sí | La logística (Natural Earth) se prueba con el kit. NDVI y LST necesitan MODIS: probar con rasters sintéticos |
| T5 código y pruebas | Sí | Pruebas sintéticas y un VRT sintético de 2 tiles. La corrida necesita Copernicus en Yuca |
| T7 y T8 código | Sí | Con blancos del kit (clusters) y parches terrestres sintéticos; con `t4_<JOBID>.tar.gz` si se alcanzó a correr T4 |
| T10 app | Sí, completa | Con `app/public/data/sample.json`. Sin dependencia de Yuca |
| T11 contenido (`limits.json`, protocolos, pitch, video) | Sí, completo | — |

**Regla para Gemini en MODO B:** cada comando de Yuca que quede pendiente se agrega a la sección "Cola para cuando haya SSH" de `progreso_handoff.md`, con el orden y el criterio para revisar el log.

---

## 5. Cómo recuperar el acceso

Ninguna de estas opciones está probada en la sede; probarlas en ese orden.

1. **Hotspot del celular.** Las redes móviles normalmente no bloquean el puerto 22. Al conectarse, Gemini (que corre en la laptop) también tiene SSH. Probar con:

   ```bash
   ssh -o ConnectTimeout=8 owen@<host-de-yuca> hostname
   ```

   Si responde `login-01`, se puede volver a MODO A.
2. **Preguntar a la sede (Local Lead)** si hay una red alternativa sin el bloqueo.
3. **Otro integrante** que trabaje desde una red sin bloqueo y tenga cuenta en `p089` (`aborquez` o `javier`), siguiendo la cola de la sección 6.

No intentar túneles, proxies ni nada que rodee el bloqueo de la red de la institución.

---

## 6. Cola para cuando vuelva el SSH

La cola vive en [progreso_handoff.md](progreso_handoff.md#cola-para-cuando-haya-ssh), para que haya una sola lista. Al volver la conexión:

1. `cd /lustre/proyectos/p089/code && git pull`
2. Correr la cola en orden, siempre primero la versión de prueba de cada job.
3. Bajar las salidas pequeñas (`targets.json`, `analogs_universe.json`) y subir a la app el JSON final.

---

## 7. Si no vuelve el SSH

Es el plan B de `plan_implementacion.md` §6. La app funciona sola con `app/public/data/sample.json`, que es la v1 convertida al esquema v2. En la presentación:

- decir que es el resultado de la v1 y mostrar la metodología v2 con las pruebas;
- enseñar la corrida T3 de Marte y la Luna (mapas del kit) y los blancos definidos en `plan_t4.md`;
- **no** afirmar resultados v2 que no se corrieron (ver la lista de "lo que no debe afirmarse" en `propuesta_de_valor.md`).
