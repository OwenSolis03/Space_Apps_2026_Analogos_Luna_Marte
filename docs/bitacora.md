# Bitácora

Registro de lo que se hace en el proyecto, de lo más reciente a lo más antiguo. Sirve también para la descripción de uso de IA de la entrega.

## 2026-11-13: propuesta de valor

- Claude redactó [propuesta_de_valor.md](propuesta_de_valor.md) para el equipo de presentación y video: problemática, propuesta de valor, qué agrega el proyecto frente a lo que pide la NASA, diferenciador frente a otros equipos y candidatos en México del prototipo.
- Incluye una lista de lo que no debe afirmarse todavía, por las limitaciones del prototipo.
- El diferenciador frente a otros equipos es una hipótesis: sus proyectos no son visibles antes de la entrega.
- Se subió el mismo contenido a un doc de Claude para el equipo: [Propuesta de valor: Planetary Analog Finder](https://claude.ai/artifact/563rMStp47364hAEc9pCmV). Es privado hasta que se comparta.

## 2026-11-13: revisión del prototipo y repositorio

**Qué se hizo**

- Se bajaron de Yuca los scripts, los logs y `output.zip` (sin los rasters).
- Claude revisó scripts, logs y salidas.
- Se ordenó la carpeta: logs en `logs/`, JSON de salida en `output/`, documentación en `docs/`.
- Se creó el repositorio en GitHub (privado) y se invitó al equipo con permiso de escritura: Javier033x, FernyBoy, EmiB-05, FlorMMF y verdielias.

**Estado del prototipo**

El pipeline corre completo: DEM de Marte y Luna, luego 40 arquetipos por cuerpo con nombre IAU, y luego top-5 análogos terrestres. `output/analogs.json` ya sirve para conectar la app.

**Puntos a mejorar, por prioridad**

1. **Escala.** Las ventanas miden ~118 km en Marte (256 px × 463 m), ~30 km en la Luna (256 × 118 m) y ~46 km en la Tierra (512 × 90 m). La pendiente y la rugosidad dependen de la resolución, así que hay que remuestrear a una resolución común y usar ventanas de la misma extensión en km.
2. **Máscara árida.** No hay filtro de vegetación (`masks/` vacía). Muchos análogos lunares caen en el Himalaya, Tíbet y los Andes de Colombia.
3. **Capa lunar.** El archivo llamado "Albedo" se bajó de la URL de `ClrShade` (relieve sombreado a color). Hay que cambiar la URL por una capa de albedo o de rugosidad real.
4. **Cobertura terrestre.** Solo 6,983 de 26,475 tiles; los análogos quedan entre 0.4° y 45.8° N. La descarga nocturna se cortó y 976 tiles fallaron por un `\r` en las URLs, que ya está corregido en el script.
5. **THEMIS Night.** La URL `..._v14.tif` da 404; falta encontrar la correcta.
6. **Blancos.** El k-means es global; faltan blancos reales del reto (polo sur lunar / Artemis, sitios de aterrizaje en Marte).
7. **Puntaje.** Pasar de `100/(1+0.35d)` al RBF con σ por dimensión del plan maestro.
8. **Menores.** `tri` es en realidad desviación absoluta a la mediana; `themis_ir_day` está en valores crudos; las etiquetas IAU lunares suelen ser cráteres satélite; `analyze_earth_tile` ignora errores sin avisar.

**Pendiente de confirmar**

- Con el Local Lead: si la descarga de datos y las corridas antes del 14 de noviembre cuentan como trabajo previo.

## 2026-11-12: descargas y primeras corridas en Yuca

- Descarga de MOLA, THEMIS Day y LOLA LDEM (`logs/descargas/download.log`).
- Descarga nocturna de Copernicus GLO-90; se interrumpió a medias (`logs/descargas/night_download.log`).
- Corridas de clustering (jobs 2241770, 2241771, 2241773) y de matching (2241781, 2241782, 2241783). Detalle en [pipeline.md](pipeline.md).

## Antes del 12 de noviembre

- Ideas del equipo y su evaluación: [../ideas.md](../ideas.md).
- Plan maestro: [../plan_maestro_y_especificaciones_del_proyecto.md](../plan_maestro_y_especificaciones_del_proyecto.md).
