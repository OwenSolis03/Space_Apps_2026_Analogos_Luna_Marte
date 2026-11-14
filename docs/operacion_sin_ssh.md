# Operación sin SSH a Yuca (14 y 15 de noviembre)

La red de la sede (UTH) bloquea SSH, pero **Open OnDemand (OOD) sí funciona**: es el portal web de Yuca y va por HTTPS. Así se trabajó el 2026-11-13 y así se trabaja durante el hackathon. Este documento describe ese flujo, el kit offline y el plan B. Escrito el 2026-11-13 por Claude.

---

## 1. Flujo de trabajo con Open OnDemand (MODO B)

Gemini trabaja en el clon **local** de la laptop y no tiene acceso a Yuca. Owen es el puente, a través del navegador.

```text
Gemini (laptop)  ──commit + push──►  GitHub  ──git pull──►  Yuca (shell de OOD, Owen)
       ▲                                                         │
       └──────── Owen pega el log o sube el archivo ◄────────────┘
```

1. Gemini escribe el código y corre en la laptop las pruebas sintéticas.
2. Gemini hace commit y push a GitHub y le da a Owen los comandos exactos de Yuca, cada uno en su bloque.
3. Owen abre en OOD la terminal de Yuca (shell del login node) y corre los comandos.
4. Owen le pasa a Gemini el resultado: el texto del log, copiado de la terminal, o el archivo, bajado con el gestor de archivos de OOD.
5. Gemini revisa el log contra los criterios de aceptación y sigue.

**Reglas que no cambian por usar OOD.** La terminal de OOD corre en el login node:

- Ahí solo van comandos cortos: `git pull`, `sbatch`, `squeue`, `sacct`, `tail` de logs y `ls`.
- Las pruebas y todo el procesamiento van con `sbatch`, igual que por SSH.
- Si OOD ofrece "Interactive Apps" o sesiones de escritorio, no usarlas para correr el pipeline: los jobs van por `sbatch` con sus logs en `output/`.

**Atajos útiles en OOD:**

- **Ver un log sin copiarlo de la terminal:** el gestor de archivos (Files) abre `/lustre/proyectos/p089/output/<log>` directamente.
- **Bajar salidas pequeñas a la laptop:** usar Files → Download. Sirve para `targets.json`, `analogs_universe.json`, los PNG y los kits de `/lustre/proyectos/p089/kit/`.
- **Subir un archivo a Yuca:** evitarlo. El código siempre llega por `git pull`, para que Yuca y GitHub no se desincronicen.

---

## 2. Lo que hay en cada lado

| Qué | Dónde vive | Desde la sede |
| --- | --- | --- |
| Código | GitHub, clon local y clon de Yuca (`/lustre/proyectos/p089/code`) | Laptop → GitHub → `git pull` en OOD |
| Rasters (MOLA, THEMIS, LOLA, WAC, Copernicus 26,475 tiles, MODIS) | Solo Yuca (~80 GB) | Solo los usan los jobs de Yuca. No se bajan |
| Corridas (`runs/<JOBID>/`) | Yuca | Se ven y se bajan por OOD. Las de T3 también están en el kit offline |
| Jobs de Slurm | Yuca | Se envían y revisan desde la terminal de OOD |
| Memoria de Claude Code | Yuca (`/lustre/home/owen/.claude/...`) | Claude en la laptop **no la tiene**; el contexto está en `docs/` del repo |

---

## 3. Lista para la noche del 13

1. **Repo al día.** En la laptop, `git pull` en el clon local.
2. **Bajar el kit offline** (sección 4), por OOD o por `scp`. Sirve para que Gemini pruebe en la laptop con datos reales de T3 sin esperar a Yuca.
3. **Entorno local en la laptop**, para que Gemini corra las pruebas:

   ```bash
   cd <clon-local> && python -m venv .venv && source .venv/bin/activate && pip install -r pipeline/requirements.txt
   ```

   ```bash
   pytest -q tests
   ```

   Las pruebas son sintéticas: deben pasar las 17 en la laptop. Para la app hacen falta Node 20 y `cd app && npm install`.
4. **Confirmar que entras a OOD** desde una red que no sea la de casa, si es posible (por ejemplo, con los datos del celular). Así se descarta que también OOD esté bloqueado en otras redes.

---

## 4. Kit offline

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

**Bajarlo:** en OOD, abrir Files, ir a `/lustre/proyectos/p089/kit/` y hacer Download. Con SSH también sirve `scp owen@<host-de-yuca>:/lustre/proyectos/p089/kit/offline_kit_2026-11-13.tar.gz .`. Después:

```bash
mkdir -p ~/p089_offline && tar -xzf offline_kit_2026-11-13.tar.gz -C ~/p089_offline
```

`~/p089_offline` imita la estructura de `/lustre/proyectos/p089`, y los scripts del pipeline aceptan `--project-dir`. Por ejemplo, los clusters de T4 corren en la laptop con:

```bash
python -m pipeline.targets --project-dir ~/p089_offline --t3-dir ~/p089_offline/runs/2242278 --out-dir ~/p089_offline/runs/local_t4 --skip-curated
```

Los blancos curados **no** se pueden calcular en la laptop porque necesitan los rasters: esa parte se corre en Yuca.

**Kits nuevos.** Cuando una corrida produzca algo que Gemini necesite en local (por ejemplo, la salida de T4 para desarrollar T7), se empaqueta en la terminal de OOD y se baja por Files:

```bash
cd /lustre/proyectos/p089 && tar -czf kit/t4_<JOBID>.tar.gz runs/<JOBID>/targets.parquet runs/<JOBID>/targets.json runs/<JOBID>/clusters_mars.parquet runs/<JOBID>/clusters_moon.parquet
```

Es un `tar` de unos cuantos MB: corre en segundos y está permitido en el login. Para algo de más de 1 GB, usar un job.

---

## 5. Qué se puede avanzar y dónde

| Tarea | En la laptop (Gemini) | En Yuca (Owen por OOD) |
| --- | --- | --- |
| T4 | Código, pruebas, clusters con el kit | Pruebas en job, humo `--k 5 --body Moon`, corrida completa |
| T6 | Código, pruebas; logística con el kit | Caché de NDVI y LST desde MODIS |
| T5 | Código, pruebas con VRT sintético de 2 tiles | `--limit 500` y luego el array completo (la corrida más pesada) |
| T7 y T8 | Código con blancos y parches del kit | Corrida real; bajar `analogs_universe.json` por OOD y subirlo a `app/public/data/` |
| T10 app | Completa, con `sample.json` y después con el JSON real | — |
| T11 contenido | Completo | — |

**Regla para Gemini en MODO B:** cada comando de Yuca que quede pendiente se agrega a la sección "Cola para cuando haya SSH" de [progreso_handoff.md](progreso_handoff.md#cola-para-cuando-haya-ssh), aunque se vaya a correr por OOD. Así Owen tiene una sola lista.

---

## 6. Si OOD tampoco funciona

En orden:

1. **Hotspot del celular.** Con datos móviles normalmente pasan SSH y OOD. Para probar SSH: `ssh -o ConnectTimeout=8 owen@<host-de-yuca> hostname`; si responde `login-01`, se puede volver a MODO A.
2. **Preguntar a la sede (Local Lead)** si hay otra red sin el bloqueo.
3. **Otro integrante** con cuenta en `p089` (`aborquez` o `javier`) desde una red sin bloqueo, siguiendo la cola.

No intentar túneles, proxies ni nada que rodee el bloqueo de la red de la institución.

---

## 7. Si no hay ningún acceso a Yuca

Es el plan B de `plan_implementacion.md` §6. La app funciona sola con `app/public/data/sample.json`, que es la v1 convertida al esquema v2. En la presentación:

- decir que es el resultado de la v1 y mostrar la metodología v2 con las pruebas;
- enseñar la corrida T3 (mapas del kit) y los blancos definidos en `plan_t4.md`;
- **no** afirmar resultados v2 que no se corrieron (ver "lo que no debe afirmarse" en `propuesta_de_valor.md`).
