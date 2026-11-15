import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from pathlib import Path

def create_document():
    doc = docx.Document()

    # Page Margins (1 inch)
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Palette
    COLOR_PRIMARY = RGBColor(230, 81, 0)      # High-vis Orange (#E65100)
    COLOR_SECONDARY = RGBColor(13, 71, 161)   # Deep Space Blue (#0D47A1)
    COLOR_DARK = RGBColor(33, 33, 33)         # Charcoal Black (#212121)
    COLOR_GRAY = RGBColor(117, 117, 117)      # Muted Gray (#757575)

    def set_cell_shading(cell, color_hex):
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
        cell._tc.get_or_add_tcPr().append(shading)

    def set_cell_margins(cell, top=140, bottom=140, left=200, right=200):
        tcPr = cell._tc.get_or_add_tcPr()
        tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
        tcPr.append(tcMar)

    # --- Title Page / Header ---
    p_kicker = doc.add_paragraph()
    r_kicker = p_kicker.add_run("NASA SPACE APPS CHALLENGE 2026 · SEDE SONORA (HERMOSILLO)")
    r_kicker.font.name = "Arial"
    r_kicker.font.size = Pt(10)
    r_kicker.font.bold = True
    r_kicker.font.color.rgb = COLOR_PRIMARY

    p_title = doc.add_paragraph()
    r_title = p_title.add_run("PROTOTERRA+")
    r_title.font.name = "Arial Black"
    r_title.font.size = Pt(28)
    r_title.font.bold = True
    r_title.font.color.rgb = COLOR_DARK

    p_sub = doc.add_paragraph()
    r_sub = p_sub.add_run("Grounded in Earth. Built for Beyond.\nGuía de Pitch y 5 Propuestas de Speech (≤ 3 Minutos)")
    r_sub.font.name = "Arial"
    r_sub.font.size = Pt(14)
    r_sub.font.color.rgb = COLOR_SECONDARY
    r_sub.font.bold = True

    p_meta = doc.add_paragraph()
    r_meta = p_meta.add_run("Equipo: ENDURANCE CXXV · Supercómputo: ACARUS / Clúster Yuca (Universidad de Sonora)\nFecha del Pitch: Domingo 15 de Noviembre · Duración máxima: 3:00 min")
    r_meta.font.name = "Arial"
    r_meta.font.size = Pt(9.5)
    r_meta.font.italic = True
    r_meta.font.color.rgb = COLOR_GRAY

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # --- Section: Reglas y Criterios ---
    h1 = doc.add_heading(level=1)
    r_h1 = h1.add_run("1. Reglas de la Sede y Criterios de Evaluación")
    r_h1.font.name = "Arial"
    r_h1.font.color.rgb = COLOR_SECONDARY

    p_rules = doc.add_paragraph()
    p_rules.paragraph_format.space_after = Pt(8)
    p_rules.add_run("• Duración: ").bold = True
    p_rules.add_run("3 minutos como máximo (sin preguntas del público). Todo speech debe cronometrarse a ~2:40 para tener margen de seguridad.\n")
    p_rules.add_run("• Idioma: ").bold = True
    p_rules.add_run("El pitch hablado es en ESPAÑOL. Todo el material escrito (Canva, video de 30s y repo) va en INGLÉS.\n")
    p_rules.add_run("• Distribución oficial del tiempo: ").bold = True
    p_rules.add_run("Minuto 1: Problema y contexto · Minuto 2: Solución, tecnología y demo · Minuto 3: Impacto y escalabilidad.")

    # Table of Criteria
    t_crit = doc.add_table(rows=6, cols=3)
    t_crit.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_crit.autofit = False

    crit_headers = ["Criterio Oficial", "¿Qué evalúan los jueces?", "Estrategia PROTOTERRA para el 5"]
    for i, h in enumerate(crit_headers):
        cell = t_crit.cell(0, i)
        set_cell_shading(cell, "0D47A1")
        p = cell.paragraphs[0]
        r = p.add_run(h)
        r.font.name = "Arial"
        r.font.size = Pt(9.5)
        r.font.bold = True
        r.font.color.rgb = RGBColor(255, 255, 255)

    crit_data = [
        ("1. Impacto (Impact)", "Problema significativo, alcance amplio y calidad que supera lo esperado.", "Democratiza la investigación espacial en México y Latinoamérica reduciendo 90% el costo de expediciones análogas."),
        ("2. Creatividad (Creativity)", "Enfoque nuevo que nadie había intentado; rompe lo convencional.", "Rompe el sesgo visual y el 'monopolio' de Atacama/Antártida mediante parches unificados de 32 km a 500m/px."),
        ("3. Validez (Validity)", "Base científica sólida, completamente desarrollada, lista y fácil de usar.", "Geomorfometría física en supercomputadora Yuca (UniSon), 127 jobs en Slurm y aplicación web interactiva ya desplegada (<50ms)."),
        ("4. Relevancia (Relevance)", "Responde directo al reto; datos de NASA son el núcleo.", "Alineación directa con los sitios de aterrizaje de Artemis III y Marte usando LOLA, MOLA, MODIS y EMIT."),
        ("5. Presentación (Presentation)", "Historia clara, bien estructurada, demo transparente de la solución.", "Estructura 1-2-3 min, estética sci-fi/HUD impecable y cálculo explícito de 'dónde se rompe la analogía'.")
    ]

    for row_idx, (c, q, e) in enumerate(crit_data, start=1):
        bg = "F5F5F5" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, text in enumerate([c, q, e]):
            cell = t_crit.cell(row_idx, col_idx)
            set_cell_shading(cell, bg)
            set_cell_margins(cell, top=100, bottom=100, left=150, right=150)
            p = cell.paragraphs[0]
            r = p.add_run(text)
            r.font.name = "Arial"
            r.font.size = Pt(8.5)
            if col_idx == 0:
                r.bold = True

    doc.add_page_break()

    # --- Section: Las 5 Propuestas de Speech ---
    h2 = doc.add_heading(level=1)
    r_h2 = h2.add_run("2. Cinco Propuestas de Speech (Pitch de 3 Minutos)")
    r_h2.font.name = "Arial"
    r_h2.font.color.rgb = COLOR_SECONDARY

    doc.add_paragraph("A continuación se presentan 5 guiones con diferente personalidad y enfoque narrativo. Todos están cronometrados entre 2:25 y 2:40 minutos en lectura natural para nunca ser cortados por el temporizador.")

    speeches = [
        {
            "num": "Propuesta 1",
            "title": "El Enfoque Científico y Riguroso ('Ingeniería Aeroespacial')",
            "perfil": "Ideal si el presentador es analítico, pausado y los jueces tienen perfil técnico o científico. Enfatiza la física del terreno, datos NASA y el cálculo de dónde se rompe la analogía.",
            "tiempo": "2:40 minutos",
            "script": [
                ("[0:00 - 0:15] SLIDE 1: PORTADA",
                 "\"Buenos días miembros del jurado. Somos el equipo Endurance CXXV y presentamos PROTOTERRA: Grounded in Earth, Built for Beyond.\""),
                ("[0:15 - 0:55] SLIDES 2 Y 3: CONTEXTO DEL RETO Y PROBLEMÁTICA (Minuto 1)",
                 "\"Para entrenar astronautas de Artemis III o validar la tracción de un rover marciano, las agencias espaciales necesitan sitios análogos en la Tierra. Pero la propia NASA advirtió el problema en este reto: hoy se eligen por intuición o 'porque se ven rojos y parecidos en fotos', recurriendo siempre a los mismos sitios hipercostosos como Atacama o la Antártida.\nEn ciencia espacial, el parecido visual no es un dato: no existía un modelo cuantitativo que midiera la topografía a escala real, ni una herramienta que calculara con exactitud en qué parámetros físicos difiere la Tierra de otros mundos.\""),
                ("[0:55 - 1:40] SLIDES 4 Y 5: TECNOLOGÍA, RESULTADOS Y DEMO EN VIVO (Minuto 2)",
                 "\"Para resolverlo, desarrollamos un motor computacional desplegado en la supercomputadora Yuca de la Universidad de Sonora. Corrimos 127 trabajos de supercómputo y acumulamos 20 horas de procesador para proyectar la Luna, Marte y la Tierra bajo la misma regla: parches uniformes de 32 por 32 kilómetros a 500 metros por pixel en proyección azimutal equidistante. Evaluamos más de 177,000 parches planetarios y 40,000 candidatos terrestres cruzando datos de elevación LOLA, MOLA, temperatura MODIS y mineralogía EMIT.\n¿El resultado? Descubrimos 3,522 nuevos candidatos no catalogados en el mundo. Nuestra app web reordena en milisegundos los sitios según la misión —ya sea movilidad o construcción de bases— mostrando la distancia real a carreteras y advirtiendo en qué variables físicas se rompe la analogía, como gravedad, presión y radiación cósmica medida por Curiosity.\""),
                ("[1:40 - 2:40] SLIDES 6 Y 7: IMPACTO SOCIAL, ESCALABILIDAD Y CIERRE (Minuto 3)",
                 "\"El impacto es directo: democratiza el acceso a la investigación análoga. Una universidad o startup mexicana ya no necesita cientos de miles de dólares para viajar al polo sur; puede validar prototipos cerca de casa con datos respaldados por supercómputo. Y la arquitectura es modular: incorporar el modelo de elevación de Mercurio de la sonda MESSENGER o datos de radar SAR de Sentinel-1 solo requiere registrar el radio planetario sin reescribir el pipeline.\nEl futuro de la exploración de otros mundos comienza entendiendo el nuestro. Muchas gracias.\"")
            ]
        },
        {
            "num": "Propuesta 2",
            "title": "El Enfoque de Innovación y Disrupción ('Romper el Monopolio Análogo')",
            "perfil": "Ideal si el presentador tiene mucha energía, habla con pasión y se busca maximizar el puntaje en Impacto y Creatividad.",
            "tiempo": "2:35 minutos",
            "script": [
                ("[0:00 - 0:15] SLIDE 1: PORTADA",
                 "\"Hola a todos. Somos Endurance CXXV y venimos a responder una pregunta crítica: ¿por qué para entrenar misiones espaciales siempre vamos a los mismos cinco lugares de la Tierra?\""),
                ("[0:15 - 0:50] SLIDES 2 Y 3: CONTEXTO DEL RETO Y PROBLEMÁTICA (Minuto 1)",
                 "\"Durante décadas, la exploración análoga ha sido un club exclusivo: Hawái, Atacama, Islandia y la Antártida. Lugares remotos, carísimos y elegidos porque 'en fotos se parecen a Marte'. Pero la NASA fue clara en este reto: el parecido visual engaña. Si pruebas la tracción de un rover en una colina de 50 metros, no estás simulando las pendientes de 30 kilómetros de un cráter lunar. Faltaba rigor, faltaba escala y sobraba intuición.\""),
                ("[0:50 - 1:40] SLIDES 4 Y 5: TECNOLOGÍA, RESULTADOS Y DEMO EN VIVO (Minuto 2)",
                 "\"Creamos PROTOTERRA para romper ese monopolio con ciencia de datos a escala planetaria. Aprovechando el clúster de supercómputo Yuca, ejecutamos 127 trabajos en Slurm y barrimos toda la superficie terrestre en 32 franjas paralelas en solo 15 minutos.\nMedimos pendientes, rugosidad y relieve exactamente igual en la Luna, Marte y la Tierra, integrando 7 capas de datos de la NASA.\nEncontramos que el 96% de los análogos del planeta nunca habían sido estudiados: más de 3,500 nuevos candidatos. Desde nuestra plataforma web, un ingeniero ajusta la prioridad de su prueba y obtiene al instante el mejor terreno con su distancia exacta a pistas de aterrizaje y carreteras.\""),
                ("[1:40 - 2:35] SLIDES 6 Y 7: IMPACTO SOCIAL, ESCALABILIDAD Y CIERRE (Minuto 3)",
                 "\"Esto cambia las reglas del juego. Significa que estudiantes, científicos y empresas aeroespaciales emergentes en México y Latinoamérica pueden hacer ciencia análoga de primer nivel sin gastar presupuestos millonarios. Y no nos detenemos aquí: nuestra arquitectura matricial está diseñada para expandirse a radar SAR y a cuerpos como Mercurio con ajustes mínimos de configuración.\nPROTOTERRA: Grounded in Earth, Built for Beyond. Muchas gracias.\"")
            ]
        },
        {
            "num": "Propuesta 3",
            "title": "El Enfoque 'Misión Artemis III y Marte' (Orientado al Reto NASA)",
            "perfil": "Ideal para asegurar calificación perfecta en Relevancia, hablando de las zonas oficiales de astronautas de Artemis III y sitios de rovers.",
            "tiempo": "2:40 minutos",
            "script": [
                ("[0:00 - 0:15] SLIDE 1: PORTADA",
                 "\"Buenos días. Somos el equipo Endurance CXXV y hoy presentamos PROTOTERRA, una solución de supercómputo para las próximas misiones tripuladas de la NASA.\""),
                ("[0:15 - 0:55] SLIDES 2 Y 3: CONTEXTO DEL RETO Y PROBLEMÁTICA (Minuto 1)",
                 "\"El programa Artemis III de la NASA está a punto de llevar humanos al polo sur de la Luna, y misiones robóticas exploran cráteres como Jezero en Marte. El reto exigía identificar ubicaciones terrestres que análoguen estos sitios permanentes. Pero la NASA estableció una regla fundamental: no se queden en lo visual, no repitan los análogos ya conocidos y expliquen con honestidad dónde se rompe la analogía física.\""),
                ("[0:55 - 1:45] SLIDES 4 Y 5: TECNOLOGÍA, RESULTADOS Y DEMO EN VIVO (Minuto 2)",
                 "\"PROTOTERRA responde al reto con números exactos. En el clúster de supercómputo Yuca procesamos 140,000 parches de Marte y 36,000 de la Luna con datos de MOLA y LOLA, comparándolos contra 40,000 parches de tierra seca evaluados con Copernicus DEM y MODIS.\nEn nuestra plataforma interactiva, un usuario puede seleccionar las regiones objetivo reales de Artemis III —como el macizo de Malapert o el cráter Haworth— o sitios marcianos como Arcadia Planitia. El sistema no solo arroja un índice de similitud ponderado por movilidad o hábitats, sino que entrega una ficha técnica con la distancia logística a carreteras y un desglose de dónde difiere la física: advirtiendo la gravedad 2.6 veces mayor y los límites de radiación medidos por el rover Curiosity.\""),
                ("[1:45 - 2:40] SLIDES 6 Y 7: IMPACTO SOCIAL, ESCALABILIDAD Y CIERRE (Minuto 3)",
                 "\"Validamos 76 objetivos prioritarios de la NASA y descubrimos miles de sitios accesibles. Esto permite a agencias espaciales planear campañas logísticas reales con base científica verificable, escalable a nuevos sensores como radar satelital.\nDemostramos que la tecnología para explorar el cosmos se puede construir desde Sonora con datos abiertos. Muchas gracias.\"")
            ]
        },
        {
            "num": "Propuesta 4",
            "title": "El Enfoque Regional y de Supercómputo ('Orgullo Sonora / UniSon')",
            "perfil": "Ideal para conectar emocionalmente con el jurado local de Hermosillo, destacando el clúster Yuca y los análogos encontrados en Sonora.",
            "tiempo": "2:35 minutos",
            "script": [
                ("[0:00 - 0:15] SLIDE 1: PORTADA",
                 "\"Buenos días jueces. Somos Endurance CXXV, estudiantes de Sonora, y presentamos PROTOTERRA: Grounded in Earth, Built for Beyond.\""),
                ("[0:15 - 0:50] SLIDES 2 Y 3: CONTEXTO DEL RETO Y PROBLEMÁTICA (Minuto 1)",
                 "\"Cuando pensamos en entrenar para ir a Marte, solemos pensar en laboratorios de la NASA en Houston o en expediciones a la Antártida. Pero la realidad es que el mundo está lleno de terrenos análogos que nadie ha cuantificado. El reto de Space Apps nos desafió a encontrar estos lugares sin caer en la trampa de 'verse parecido', sino midiendo el terreno con rigor científico y reconociendo sus límites físicos.\""),
                ("[0:50 - 1:40] SLIDES 4 Y 5: TECNOLOGÍA, RESULTADOS Y DEMO EN VIVO (Minuto 2)",
                 "\"Para lograrlo no usamos una laptop: desplegamos nuestra arquitectura en Yuca, la supercomputadora de la Universidad de Sonora. A través de ACARUS ejecutamos 127 trabajos de cómputo de alto rendimiento y acumulamos 20 horas CPU. Desarrollamos un algoritmo que estandarizó más de 177,000 parches en la Luna y Marte a 500 metros por pixel.\nY el gran hallazgo: descubrimos que tenemos análogos planetarios de clase mundial aquí mismo, en el noroeste de México, en regiones de Sonora y Baja California, con más del 90% de similitud para pruebas de movilidad y bases espaciales. Nuestra app web permite filtrar estos sitios, conocer la distancia por carretera y auditar exactamente en qué parámetros físicos se rompe la analogía.\""),
                ("[1:40 - 2:35] SLIDES 6 Y 7: IMPACTO SOCIAL, ESCALABILIDAD Y CIERRE (Minuto 3)",
                 "\"El verdadero valor de PROTOTERRA es demostrar que la infraestructura científica pública de nuestro estado puede generar herramientas de nivel aeroespacial global. Abrimos la puerta para que universidades y jóvenes de nuestra región prueben rovers y trajes espaciales en nuestro propio desierto con sustento matemático.\nDe Sonora para el espacio: muchas gracias.\"")
            ]
        },
        {
            "num": "Propuesta 5",
            "title": "El Pitch Ágil y Contundente ('Estilo Silicon Valley / Keynote')",
            "perfil": "Ideal si el orador prefiere frases cortas, directas, buen ritmo y cero complicaciones. Es el guión más seguro contra el cronómetro.",
            "tiempo": "2:25 minutos",
            "script": [
                ("[0:00 - 0:15] SLIDE 1: PORTADA",
                 "\"Buenos días. Somos Endurance CXXV y esto es PROTOTERRA: el primer buscador cuantitativo de análogos lunares y marcianos.\""),
                ("[0:15 - 0:45] SLIDES 2 Y 3: CONTEXTO DEL RETO Y PROBLEMÁTICA (Minuto 1)",
                 "\"El problema actual de la exploración espacial es simple: entrenamos siempre en los mismos 5 lugares caros del mundo porque 'se ven parecidos'. Pero en ingeniería aeroespacial, una foto no es un dato. Sin una métrica matemática, no puedes saber si un terreno realmente sirve para probar un rover, ni sabes dónde va a fallar la prueba.\""),
                ("[0:45 - 1:30] SLIDES 4 Y 5: TECNOLOGÍA, RESULTADOS Y DEMO EN VIVO (Minuto 2)",
                 "\"PROTOTERRA cambia la intuición por supercómputo. En el clúster Yuca de la UniSon corrimos 127 jobs y analizamos más de 177,000 parches de 32 km en la Luna, Marte y la Tierra, integrando 7 capas de datos de la NASA.\nEncontramos más de 3,500 nuevos análogos no catalogados en el mundo.\nEn nuestra web app, cualquier ingeniero selecciona una zona de aterrizaje de Artemis III o Marte, ajusta el tipo de prueba y en menos de 50 milisegundos recibe los mejores sitios terrestres, con su distancia exacta a carreteras y una alerta clara de dónde se rompe la analogía física.\""),
                ("[1:30 - 2:25] SLIDES 6 Y 7: IMPACTO SOCIAL, ESCALABILIDAD Y CIERRE (Minuto 3)",
                 "\"¿El impacto? Reducimos el costo de expedición en un 90%. Permitimos que universidades y startups en México y el mundo prueben tecnología espacial cerca de casa. Y nuestra arquitectura está lista para incorporar radar y planetas como Mercurio sin cambiar el código.\nPROTOTERRA: Grounded in Earth, Built for Beyond. Gracias.\"")
            ]
        }
    ]

    for item in speeches:
        h3 = doc.add_heading(level=2)
        r_h3 = h3.add_run(f"{item['num']}: {item['title']}")
        r_h3.font.name = "Arial"
        r_h3.font.color.rgb = COLOR_PRIMARY

        p_info = doc.add_paragraph()
        p_info.paragraph_format.space_after = Pt(6)
        r_p1 = p_info.add_run("• Perfil recomendado: ")
        r_p1.bold = True
        p_info.add_run(item["perfil"] + "\n")
        r_p2 = p_info.add_run("• Tiempo estimado de lectura: ")
        r_p2.bold = True
        r_time = p_info.add_run(item["tiempo"])
        r_time.bold = True
        r_time.font.color.rgb = COLOR_PRIMARY

        # Table for the script stages
        t_script = doc.add_table(rows=len(item["script"]) + 1, cols=2)
        t_script.alignment = WD_TABLE_ALIGNMENT.CENTER
        t_script.autofit = False

        headers = ["Tiempo y Diapositiva", "Guión Verbal (Hablado en Español)"]
        for i, h in enumerate(headers):
            cell = t_script.cell(0, i)
            set_cell_shading(cell, "333333")
            p = cell.paragraphs[0]
            r = p.add_run(h)
            r.font.name = "Arial"
            r.font.size = Pt(9)
            r.font.bold = True
            r.font.color.rgb = RGBColor(255, 255, 255)

        for s_idx, (stage, text) in enumerate(item["script"], start=1):
            bg = "FAFAFA" if s_idx % 2 == 1 else "FFFFFF"
            cell_stage = t_script.cell(s_idx, 0)
            cell_text = t_script.cell(s_idx, 1)
            set_cell_shading(cell_stage, bg)
            set_cell_shading(cell_text, bg)
            set_cell_margins(cell_stage, top=100, bottom=100, left=120, right=120)
            set_cell_margins(cell_text, top=100, bottom=100, left=150, right=150)

            p_st = cell_stage.paragraphs[0]
            r_st = p_st.add_run(stage)
            r_st.font.name = "Arial"
            r_st.font.size = Pt(8.5)
            r_st.bold = True
            r_st.font.color.rgb = COLOR_SECONDARY

            p_tx = cell_text.paragraphs[0]
            r_tx = p_tx.add_run(text)
            r_tx.font.name = "Arial"
            r_tx.font.size = Pt(8.5)

        doc.add_paragraph().paragraph_format.space_after = Pt(14)

    doc.add_page_break()

    # --- Section: Cifras Clave ---
    h3_sec = doc.add_heading(level=1)
    r_h3_sec = h3_sec.add_run("3. Cifras Clave Verificadas para Responder a los Jueces")
    r_h3_sec.font.name = "Arial"
    r_h3_sec.font.color.rgb = COLOR_SECONDARY

    doc.add_paragraph("Estos números están comprobados directamente en el clúster Yuca y en la base de datos de PROTOTERRA (analogs_universe.json):")

    facts = [
        ("127 Jobs en Slurm / 19.57 Core-Hours", "Corridos en Yuca (UniSon/ACARUS). 109 completados con éxito y barrido global terrestre en 32 franjas en 15 minutos."),
        ("177,657 Parches Planetarios", "140,916 en Marte (MOLA 463m) y 36,741 en la Luna (LOLA 118m), proyectados a 32 km en local AEQD a 500m/pixel."),
        ("40,244 Parches Terrestres Válidos", "Filtrados de tierra desnuda sin vegetación (MODIS NDVI < 0.15) sobre 26,475 teselas de Copernicus DEM."),
        ("3,522 Nuevos Candidatos Descubiertos", "El 96% de los análogos identificados por PROTOTERRA no estaban catalogados en la literatura científica."),
        ("Sitios de Artemis III Validados", "Análogos calculados directamente para Haworth rim, Malapert Massif, Mons Mouton y Nobile rim."),
        ("Análogos en Sonora y Baja California", "Similitud superior al 90% (MSI) para construcción de bases y tracción de rovers con distancias reales a carreteras."),
        ("Where the Analogy Breaks", "Cálculo explícito de discrepancia física: gravedad (0.38g en Marte), presión (6.4 hPa) y radiación cósmica (Curiosity RAD)."),
        ("Respuesta en App Web < 50 ms", "Arquitectura reactiva en Vue 3 que recalcula el ranking completo en el navegador del usuario.")
    ]

    for title, desc in facts:
        p_f = doc.add_paragraph()
        p_f.paragraph_format.space_after = Pt(4)
        r_t = p_f.add_run(f"• {title}: ")
        r_t.bold = True
        r_t.font.name = "Arial"
        r_t.font.color.rgb = COLOR_PRIMARY
        r_d = p_f.add_run(desc)
        r_d.font.name = "Arial"

    doc.add_page_break()

    # --- Section: Textos para Canva en Inglés ---
    h4_sec = doc.add_heading(level=1)
    r_h4_sec = h4_sec.add_run("4. Textos Exactos para Diapositivas en Canva (Inglés)")
    r_h4_sec.font.name = "Arial"
    r_h4_sec.font.color.rgb = COLOR_SECONDARY

    doc.add_paragraph("Copia y pega estos textos directamente en las cajas HUD de tu presentación en Canva:")

    slides = [
        ("SLIDE 1: COVER & IDENTIFICATION", [
            ("Header", "[PT.0001] // MISSION LAUNCH"),
            ("Title", "PROTOTERRA+"),
            ("Subtitle", "GROUNDED IN EARTH. BUILT FOR BEYOND."),
            ("Team Badge", "TEAM #[NUM] · ENDURANCE CXXV · SONORA LOCAL EVENT"),
            ("Footer", "SUPERCOMPUTING POWERED BY ACARUS · YUCA CLUSTER (UNISON)")
        ]),
        ("SLIDE 2: MISSION CONTEXT // THE NASA CHALLENGE (Diapositiva de Emilio)", [
            ("Header", "SECTION.0001 // MISSION CONTEXT"),
            ("Title", "MISSION CONTEXT // THE NASA CHALLENGE"),
            ("NASA Mandate", "NASA's Artemis III lunar south pole landing and Mars crewed exploration require terrestrial testing grounds to validate rovers, habitats, and extravehicular equipment before flight."),
            ("Critical Rules", "• VISUAL LOOKS ARE NOT DATA: A desert looking red does not mean slope or physics match.\n• SCALE MATTERS: A 50m hill cannot simulate a 32km crater rim.\n• OVER-STUDIED SITES: Atacama and Antarctica are geographically exclusive and costly."),
            ("Objective", "Replace subjective visual intuition with an open-source, planetary-scale HPC search engine that measures similarity and shows where the analogy breaks.")
        ]),
        ("SLIDE 3: SEARCHING FOR OTHER WORLDS IN OUR OWN", [
            ("Header", "SECTION.0002 // THE ANALOG DILEMMA"),
            ("Title", "SEARCHING FOR OTHER WORLDS IN OUR OWN"),
            ("The Famous 5 Trap", "Missions repeatedly rehearse in the same 5 remote sites. Untapped, accessible analogs remain unmapped."),
            ("'Looks Similar' Is Not Data", "Visual resemblance lacks physical rigor. Scale and geomorphology cannot be compared across planets without unified quantitative metrics."),
            ("Critical Gap Callout", "Without physical modeling, you cannot prove how analogous a site is, for what test it works, and crucially: where the analogy breaks.")
        ]),
        ("SLIDE 4: THE PROTOTERRA ENGINE (Supercomputing & Sensors)", [
            ("Header", "SECTION.0003 // SUPERCOMPUTING ARCHITECTURE"),
            ("Title", "THE PROTOTERRA ENGINE"),
            ("HPC Benchmark", "127 Slurm Jobs on Yuca Supercomputer · ~20 CPU Core-Hours aggregated · Full Earth swept in 32 parallel stripes in just 15 minutes."),
            ("Unified 32x32 km Scale", "Reprojected to local Azimuthal Equidistant (500m/px). Slope, relief, roughness (TRI), and hypsometry measured identically across bodies."),
            ("NASA Sensor Fusion", "LOLA & Diviner (Moon) · MOLA & THEMIS (Mars) · Copernicus GLO-90 DEM, MODIS NDVI/LST & EMIT hyperspectral mineralogy (Earth).")
        ]),
        ("SLIDE 5: RESULTS & DATA-BACKED DISCOVERIES", [
            ("Header", "SECTION.0004 // DATA-BACKED DISCOVERY"),
            ("Title", "RESULTS & MISSION SIMILARITY"),
            ("Massive Discovery", "Swept 140,916 Mars + 36,741 Moon patches against ~45,000 Earth candidates. Discovered 3,522 new uncatalogued sites (96% of total) including Northwest Mexico (MSI > 90%)."),
            ("Mission Presets (<50ms)", "Instant client-side re-weighting tailored to specific mission engineering: Rover Mobility, Base Construction, Thermal Stress, or Polar Ice Traps."),
            ("Logistics & Failure Limits", "Every site displays real distance to nearest roads and airports, while explicitly listing where the analogy breaks in physical units.")
        ]),
        ("SLIDE 6: TECH DEMO // LIVE WEB APPLICATION", [
            ("Header", "SECTION.0005 // INTERACTIVE EXPLORER"),
            ("Title", "LIVE WEB APPLICATION"),
            ("Features", "• 76 Planetary Targets (Artemis III Candidate Regions & Mars Landing Sites)\n• Instant Filtering over ~45,000 Valid Earth Candidate Patches\n• Pre-computed on Supercomputer · Query Response Time < 50ms in Browser\n• Dual planetary mapping (Mars MOLA / Earth Blue Marble) + Site Sheet comparison")
        ]),
        ("SLIDE 7: IMPACT & REAL SCALABILITY", [
            ("Header", "SECTION.0006 // DEMOCRATIZING SPACE"),
            ("Title", "IMPACT & SCALABILITY"),
            ("Social Impact", "Field campaigns to Antarctica or Atacama cost hundreds of thousands of dollars. PROTOTERRA empowers Mexican and Latin American student teams to test hardware close to home."),
            ("Public HPC Power", "Demonstrates that high-impact planetary research can be computed on public university infrastructure (ACARUS / UniSon) with 100% open data."),
            ("Extensible Sensors & Bodies", "• Planetary Independence: Adding bodies with global DEMs (e.g. Mercury via MESSENGER 665m data) only requires setting its mean radius.\n• Next Planned Layer: Direct integration of SAR radar backscatter (Sentinel-1 / NISAR) for sub-meter roughness.")
        ])
    ]

    for s_title, fields in slides:
        h_sl = doc.add_heading(level=2)
        r_sl = h_sl.add_run(s_title)
        r_sl.font.name = "Arial"
        r_sl.font.color.rgb = COLOR_DARK

        for f_label, f_val in fields:
            p_f = doc.add_paragraph()
            p_f.paragraph_format.space_after = Pt(3)
            r_l = p_f.add_run(f"[{f_label}]: ")
            r_l.bold = True
            r_l.font.color.rgb = COLOR_PRIMARY
            r_v = p_f.add_run(f_val)
            r_v.font.name = "Consolas"
            r_v.font.size = Pt(8.5)

    output_path = Path("PROTOTERRA_Propuestas_Speech_Pitch.docx")
    doc.save(str(output_path))
    print(f"Document saved successfully at: {output_path.resolve()}")

if __name__ == "__main__":
    create_document()
