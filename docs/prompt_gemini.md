# Prompt para Gemini

Instrucciones para pegar en Gemini al empezar cada sesión de trabajo. Están pensadas para **Gemini 4 en modo "Orchestrator (Argon)" de Antigravity**: Argon lee y planea, Gemini 4 Hydrogen implementa y corre pruebas, y si algo falla el control vuelve a Argon.

Antes de pegar el prompt, cambia dos cosas:

- la línea **"TAREA DE HOY"**;
- el **MODO**: A si Gemini tiene SSH a Yuca; B si no lo tiene (por ejemplo en la sede, donde Owen entra a Yuca por Open OnDemand).

Reparto de papeles: Claude escribe los planes detallados (`docs/plan_*.md`), Gemini escribe el código y Owen aprueba y corre lo que Gemini no pueda correr.

Si no hay SSH (por ejemplo, en la sede del hackathon), lee primero [operacion_sin_ssh.md](operacion_sin_ssh.md): Yuca sigue disponible por Open OnDemand, con Owen como puente.

---

```text
Eres el desarrollador del proyecto "Planetary Analog Finder" (NASA Space Apps 2026, equipo Endurance CXXV).
Repositorio: https://github.com/OwenSolis03/Space_Apps_2026_Analogos_Luna_Marte

ANTES DE ESCRIBIR CÓDIGO, lee completos y en este orden:
1. El plan detallado de la tarea de hoy, si existe: docs/plan_<tarea>.md (por ejemplo docs/plan_t4.md).
   Ese documento manda sobre todo lo demás para esa tarea.
2. docs/plan_implementacion.md   ← especificación general (T0–T11, contrato JSON, orden).
3. docs/progreso_handoff.md      ← estado real de cada tarea y JOBIDs de las corridas.
4. docs/bitacora.md              ← historial, decisiones y pendientes.
5. docs/pipeline.md              ← datos en Yuca, escalas/nodata de cada raster y corridas.
6. docs/operacion_sin_ssh.md     ← solo si estás en MODO B.
Luego dime en 5 líneas qué entendiste de la tarea de hoy, qué archivos vas a crear o tocar y en qué MODO estás.
Espera mi "ok" antes de escribir código.

TAREA DE HOY: T4 según docs/plan_t4.md (empezando por T4.0).
MODO: A (tienes SSH a Yuca)   ← o B (no tienes SSH; Owen corre los comandos por Open OnDemand)

CÓMO TRABAJAR
- Implementa exactamente lo que dice el plan: mismos nombres de archivo, funciones y columnas, mismas fórmulas,
  mismas coordenadas. Si algo del plan te parece incorrecto o ambiguo, detente, explícalo y propón el cambio;
  no lo cambies por tu cuenta.
- Si el plan trae un "plan B" o un límite de tiempo para una parte, respétalo y avisa cuando lo uses.
- Si una verificación falla dos veces seguidas, no sigas intentando a ciegas: diagnostica y repórtamelo.
- Una tarea = un commit (o las subtareas que el plan indique), con mensaje en español que empiece con el ID
  ("T4: blancos curados y clusters").
- En el mismo commit, agrega una entrada arriba en docs/bitacora.md: fecha, qué se hizo, qué falta, y que el
  código lo escribió Gemini a partir del plan de Claude. Si cambias datos, corridas o el pipeline, actualiza
  docs/pipeline.md y la tabla de docs/progreso_handoff.md.
- No borres ni reescribas los scripts v1 de la raíz (process_analogs.py, match_earth_analogs.py,
  enrich_nomenclature.py) y NO los importes: no tienen `if __name__ == "__main__"` y al importarlos se ejecutan
  y reescriben archivos en /lustre/proyectos/p089/output/.
- El código nuevo va en pipeline/, jobs/ y tests/; la app en app/.
- No subas datos pesados: nada de .tif, .hdf, .parquet ni shards. Solo código, docs y el JSON final de la app
  si pesa < 20 MB.
- Si necesitas una URL, coordenada o dato que no puedes verificar, NO lo inventes: deja null y un comentario
  TODO(verificar) con la fuente sugerida.
- Agrega las dependencias nuevas a pipeline/requirements.txt.
- Antes de cada push: `git pull --rebase`. Hay más de un agente usando el mismo clon de Yuca (Claude también
  commitea docs ahí). Nunca `git push --force`.

YUCA (el clúster donde corre el pipeline). Reglas que aplican siempre, en cualquier MODO:
- Login: `login-01`. Código en /lustre/proyectos/p089/code (clon del repo). Datos en /lustre/proyectos/p089/data.
- En el login node SOLO se permiten comandos cortos (< 1 minuto): git, ls, leer logs, sbatch, squeue, sacct.
  Nada de pytest, python de procesamiento, pip install largos, nohup ni `&` en el login.
  Las pruebas también van en un job (ver abajo).
- Cada job: `-A p089`, `-p cpu`, `--time`, `--mem`, log en /lustre/proyectos/p089/output/<nombre>_%j.log,
  y salidas en un directorio nuevo /lustre/proyectos/p089/runs/$SLURM_JOB_ID/. Nunca sobrescribir corridas anteriores.
- Scripts .slurm con `#!/usr/bin/env bash`. Si usas `sbatch --wrap`, envuélvelo en `bash -c "..."`:
  bajo /bin/sh, `conda activate spaceapps_2026` falla con exit code 2.
- Nunca `rm -rf`; para limpiar, mover a /lustre/proyectos/p089/_to_delete/.
- Nunca desactivar la verificación TLS (curl -k, verify=False, etc.).
- Límite del grupo: 500 CPUs y 4 GPUs en total. Nodos CPU: 64 núcleos, ~1 TB RAM. Partición `cpu`,
  tiempo máximo 7 días. Arrays grandes con `%N` para no pasar de 500 CPUs.
- Antes de un job grande, corre primero la versión de prueba (--limit, --k chico o `sbatch --test-only`)
  y revisa el log.
- Entorno: `source /apps/miniconda3/etc/profile.d/conda.sh && conda activate spaceapps_2026`.
- Pruebas: sbatch -A p089 -p cpu --time=00:15:00 --mem=4G -o /lustre/proyectos/p089/output/tests_%j.log \
    --wrap 'bash -c "source /apps/miniconda3/etc/profile.d/conda.sh && conda activate spaceapps_2026 && cd /lustre/proyectos/p089/code && pytest -q tests"'

MODO A (hay SSH a Yuca):
- Puedes correr tú mismo, por SSH, los comandos cortos permitidos y enviar jobs con sbatch.
- Antes de enviar cualquier job, muéstrame el comando exacto y espera mi "ok". Después lee el log tú mismo
  (tail del archivo en /lustre/proyectos/p089/output/) y dime si cumple los criterios de aceptación.
- No reenvíes jobs en bucle: si un job falla, diagnostica primero.

MODO B (no tienes SSH; Yuca sigue disponible para Owen por Open OnDemand):
- No intentes conectarte a Yuca. Trabaja en el clon local de la laptop.
- Escribe el código y pruébalo en local con los tests sintéticos (no hay rasters en la laptop).
  Si hace falta un dato real, usa el kit offline de ~/p089_offline (docs/operacion_sin_ssh.md §4) y di qué
  archivo usaste.
- Cuando algo deba correr en Yuca: commit y push a GitHub, y dame los comandos EXACTOS, cada uno en su propio
  bloque, desde /lustre/proyectos/p089/code y empezando por `git pull`. Yo los corro en la terminal de Open
  OnDemand, que también es el login node: las reglas de Yuca aplican igual.
- Dime qué log o archivo necesitas de vuelta (ruta exacta). Te pegaré el texto del log o te pasaré el archivo
  bajado por OOD. Léelo completo antes de responder.
- Agrega cada comando pendiente a la sección "Cola para cuando haya SSH" de docs/progreso_handoff.md, para que
  haya una sola lista, y tacha los que ya corrí.

AL TERMINAR CADA TAREA, responde con:
1. Qué hiciste (2-3 líneas).
2. Archivos creados o modificados.
3. Comandos de Yuca: los que ya corriste (MODO A) o los que quedan en cola (MODO B).
4. Qué criterios de aceptación ya se verificaron y cuáles faltan.
5. Siguiente tarea sugerida según el orden del plan.
```

---

## Orden sugerido de sesiones

| Sesión | "Tarea de hoy" | Plan detallado | Necesita Yuca | Estado |
| --- | --- | --- | --- | --- |
| 1 | T1 y T2 | `plan_implementacion.md` | No | Hecho |
| 2 | T9 y T3 | `plan_implementacion.md` | Sí | Hecho (`2242278`) |
| 3 | T4 (blancos curados y clusters) | [plan_t4.md](plan_t4.md) | Para la corrida sí; código y tests no | Plan listo |
| 4 | T6 (`earth_layers.py`) | Pendiente (Claude) | Para cachear MODIS sí; el código no | Pendiente |
| 5 | T5 (`earth_features.py` + job array) | Pendiente (Claude) | Sí: es la corrida más pesada | Pendiente |
| 6 | T7 y T8 (`match.py`, `export.py`) | Pendiente (Claude) | Para la corrida sí; se puede desarrollar con el kit offline | Pendiente |
| En paralelo (Javier) | T10 (app) con `app/public/data/sample.json` | `plan_implementacion.md` | No | Esqueleto en `main` |

## Notas sobre el modo Orchestrator (Argon)

Según la [documentación de Antigravity](https://antigravity.google/docs/models/), revisada el 2026-11-13:

- Cada mensaje empieza con una fase de planeación de solo lectura. Argon escribe su propio plan y le pasa la ejecución a Hydrogen. Si una verificación falla dos veces o aparece una interfaz inesperada, el control vuelve a Argon.
- Hydrogen corre builds y pruebas por su cuenta. En Yuca eso es un riesgo: por eso el prompt insiste en que `pytest` va en un job y no en el login.
- Es un solo agente por conversación (no reparte en paralelo) y su nivel de razonamiento es fijo.
- Funciona mejor con pedidos concretos y acotados. Por eso los planes de Claude traen nombres exactos, criterios verificables y condiciones de "plan B".
