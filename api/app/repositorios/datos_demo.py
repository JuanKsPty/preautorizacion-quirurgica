"""
Datos de demostracion. Son los MISMOS que se siembran en Notion.

Existen por dos razones. La primera es que el enlace publico tiene que funcionar
aunque Notion este caido o el token no este configurado. La segunda es que cada
informe esta construido para recorrer un camino de dictamen distinto: hay uno
que se aprueba limpio, uno que choca con la carencia, uno excluido por estetico,
uno con papeles faltantes, uno con una preexistencia sin declarar, una urgencia
que exonera la carencia, uno que se pasa del tope y uno con la poliza en mora.

Poder demostrar los ocho en vivo, sin inventar datos en el momento, es lo que
diferencia una demo de una captura de pantalla.

Codigos CPT y CIE-10 reales; nombres, cedulas y polizas ficticios.
"""

from datetime import date

from app.dominio.esquemas import InformeMedico, Poliza, Procedimiento

# Nombres canonicos de los documentos. La comparacion se hace normalizada
# (sin tildes, en minusculas), asi que el hospital puede teclearlos como quiera.
DOC_INFORME = "Informe médico firmado"
DOC_CEDULA = "Copia de cédula"
DOC_COTIZACION = "Cotización del hospital"
DOC_IMAGENES = "Estudio de imágenes"
DOC_LABORATORIO = "Resultados de laboratorio"
DOC_HISTORIA = "Historia clínica"
DOC_PREANESTESICA = "Evaluación preanestésica"
DOC_PATOLOGIA = "Informe de patología"


PROCEDIMIENTOS: list[Procedimiento] = [
    Procedimiento(
        cpt="47562",
        nombre="Colecistectomía laparoscópica",
        sinonimos=[
            "colecistectomia laparoscopica",
            "extirpación de vesícula por laparoscopia",
            "cirugía de vesícula",
            "colelap",
        ],
        categoria="Cirugía general",
        carencia_dias={"basico": 180, "preferente": 90, "ejecutivo": 60},
        cobertura_porcentaje={"basico": 80, "preferente": 90, "ejecutivo": 100},
        documentos_requeridos=[
            DOC_INFORME,
            DOC_CEDULA,
            DOC_COTIZACION,
            DOC_IMAGENES,
            DOC_LABORATORIO,
        ],
    ),
    Procedimiento(
        cpt="44970",
        nombre="Apendicectomía laparoscópica",
        sinonimos=[
            "apendicectomia",
            "apendicectomia laparoscopica",
            "cirugía de apéndice",
            "extirpación del apéndice",
        ],
        categoria="Cirugía de urgencia",
        carencia_dias={"basico": 90, "preferente": 30, "ejecutivo": 0},
        cobertura_porcentaje={"basico": 80, "preferente": 90, "ejecutivo": 100},
        documentos_requeridos=[DOC_INFORME, DOC_CEDULA, DOC_LABORATORIO],
    ),
    Procedimiento(
        cpt="49505",
        nombre="Hernioplastia inguinal",
        sinonimos=[
            "hernioplastia inguinal",
            "reparación de hernia inguinal",
            "herniorrafia inguinal",
            "cirugía de hernia",
        ],
        categoria="Cirugía general",
        carencia_dias={"basico": 180, "preferente": 90, "ejecutivo": 60},
        cobertura_porcentaje={"basico": 80, "preferente": 90, "ejecutivo": 100},
        documentos_requeridos=[DOC_INFORME, DOC_CEDULA, DOC_COTIZACION, DOC_LABORATORIO],
    ),
    Procedimiento(
        cpt="29881",
        nombre="Meniscectomía artroscópica de rodilla",
        sinonimos=[
            "meniscectomia",
            "artroscopia de rodilla",
            "cirugía de menisco",
            "meniscectomia artroscopica",
        ],
        categoria="Ortopedia",
        carencia_dias={"basico": 365, "preferente": 180, "ejecutivo": 120},
        cobertura_porcentaje={"basico": 70, "preferente": 85, "ejecutivo": 100},
        documentos_requeridos=[
            DOC_INFORME,
            DOC_CEDULA,
            DOC_COTIZACION,
            DOC_IMAGENES,
            DOC_PREANESTESICA,
        ],
    ),
    Procedimiento(
        cpt="63030",
        nombre="Discectomía lumbar",
        sinonimos=[
            "discectomia lumbar",
            "microdiscectomia",
            "cirugía de hernia discal",
            "laminectomía lumbar",
        ],
        categoria="Neurocirugía / columna",
        carencia_dias={"basico": 365, "preferente": 270, "ejecutivo": 180},
        cobertura_porcentaje={"basico": 70, "preferente": 85, "ejecutivo": 100},
        documentos_requeridos=[
            DOC_INFORME,
            DOC_CEDULA,
            DOC_COTIZACION,
            DOC_IMAGENES,
            DOC_HISTORIA,
            DOC_PREANESTESICA,
        ],
    ),
    Procedimiento(
        cpt="27447",
        nombre="Artroplastia total de rodilla",
        sinonimos=[
            "artroplastia total de rodilla",
            "prótesis de rodilla",
            "reemplazo total de rodilla",
        ],
        categoria="Ortopedia mayor",
        carencia_dias={"basico": 365, "preferente": 270, "ejecutivo": 180},
        cobertura_porcentaje={"basico": 60, "preferente": 80, "ejecutivo": 100},
        documentos_requeridos=[
            DOC_INFORME,
            DOC_CEDULA,
            DOC_COTIZACION,
            DOC_IMAGENES,
            DOC_PREANESTESICA,
        ],
    ),
    Procedimiento(
        cpt="58571",
        nombre="Histerectomía laparoscópica total",
        sinonimos=[
            "histerectomia laparoscopica",
            "extirpación del útero",
            "histerectomia total",
        ],
        categoria="Ginecología",
        carencia_dias={"basico": 300, "preferente": 180, "ejecutivo": 120},
        cobertura_porcentaje={"basico": 75, "preferente": 90, "ejecutivo": 100},
        documentos_requeridos=[
            DOC_INFORME,
            DOC_CEDULA,
            DOC_COTIZACION,
            DOC_IMAGENES,
            DOC_PATOLOGIA,
        ],
    ),
    Procedimiento(
        cpt="66984",
        nombre="Facoemulsificación con lente intraocular",
        sinonimos=[
            "facoemulsificacion",
            "cirugía de cataratas",
            "extracción de catarata",
            "lente intraocular",
        ],
        categoria="Oftalmología",
        carencia_dias={"basico": 180, "preferente": 90, "ejecutivo": 60},
        cobertura_porcentaje={"basico": 70, "preferente": 85, "ejecutivo": 100},
        documentos_requeridos=[DOC_INFORME, DOC_CEDULA, DOC_COTIZACION, DOC_IMAGENES],
    ),
    Procedimiento(
        cpt="43644",
        nombre="Bypass gástrico laparoscópico",
        sinonimos=[
            "bypass gastrico",
            "cirugía bariátrica",
            "derivación gástrica en Y de Roux",
        ],
        categoria="Cirugía bariátrica",
        carencia_dias={"basico": 730, "preferente": 545, "ejecutivo": 365},
        # El plan Básico no incluye bariátrica: cobertura 0.
        cobertura_porcentaje={"basico": 0, "preferente": 50, "ejecutivo": 80},
        documentos_requeridos=[
            DOC_INFORME,
            DOC_CEDULA,
            DOC_COTIZACION,
            DOC_HISTORIA,
            DOC_LABORATORIO,
            DOC_PREANESTESICA,
        ],
    ),
    Procedimiento(
        cpt="15877",
        nombre="Lipectomía asistida por succión",
        sinonimos=["liposuccion", "lipoescultura", "liposucción abdominal", "lipectomia"],
        categoria="Cirugía plástica",
        carencia_dias={"basico": 0, "preferente": 0, "ejecutivo": 0},
        cobertura_porcentaje={"basico": 0, "preferente": 0, "ejecutivo": 0},
        documentos_requeridos=[DOC_INFORME, DOC_CEDULA],
        exclusion=(
            "cirugía con fines estéticos, excluida en todos los planes "
            "por condiciones generales de la póliza"
        ),
    ),
]


POLIZAS: list[Poliza] = [
    Poliza(
        numero="POL-2024-0148",
        titular="Ricardo Mendoza Barría",
        cedula="8-812-2043",
        plan="preferente",
        estado="vigente",
        inicio_vigencia=date(2024, 3, 1),
        fin_vigencia=date(2027, 2, 28),
        deducible_anual=500.0,
        deducible_consumido=500.0,
        coaseguro_porcentaje=20,
        tope_anual=50_000.0,
        tope_consumido=4_200.0,
        preexistencias_declaradas=["Hipertensión arterial esencial"],
        dependientes=["Lucía Mendoza Sanjur"],
    ),
    Poliza(
        numero="POL-2026-0731",
        titular="Yaritza Camaño Ríos",
        cedula="8-901-1187",
        plan="basico",
        estado="vigente",
        # Afiliada hace poco: es la poliza que choca con la carencia.
        inicio_vigencia=date(2026, 7, 15),
        fin_vigencia=date(2027, 7, 14),
        deducible_anual=750.0,
        deducible_consumido=0.0,
        coaseguro_porcentaje=30,
        tope_anual=25_000.0,
        tope_consumido=0.0,
    ),
    Poliza(
        numero="POL-2023-0092",
        titular="Luis Alberto Quintero",
        cedula="4-742-1908",
        plan="ejecutivo",
        estado="vigente",
        inicio_vigencia=date(2023, 1, 10),
        fin_vigencia=date(2027, 1, 9),
        deducible_anual=300.0,
        deducible_consumido=300.0,
        coaseguro_porcentaje=10,
        tope_anual=150_000.0,
        tope_consumido=2_500.0,
        preexistencias_declaradas=["Diabetes mellitus tipo 2"],
    ),
    Poliza(
        numero="POL-2022-0455",
        titular="Marisol Ortega Peña",
        cedula="8-455-0921",
        plan="preferente",
        estado="vigente",
        inicio_vigencia=date(2022, 9, 5),
        fin_vigencia=date(2027, 9, 4),
        deducible_anual=500.0,
        deducible_consumido=120.0,
        coaseguro_porcentaje=20,
        tope_anual=50_000.0,
        # Ya consumio casi toda la suma asegurada del ano: quedan 3.200.
        tope_consumido=46_800.0,
    ),
    Poliza(
        numero="POL-2025-0310",
        titular="Ernesto Villalaz Gómez",
        cedula="7-112-0784",
        plan="basico",
        # Primas pendientes: cualquier solicitud se rechaza de entrada.
        estado="en_mora",
        inicio_vigencia=date(2025, 4, 20),
        fin_vigencia=date(2027, 4, 19),
        deducible_anual=750.0,
        deducible_consumido=0.0,
        coaseguro_porcentaje=30,
        tope_anual=25_000.0,
        tope_consumido=0.0,
    ),
    Poliza(
        numero="POL-2024-0602",
        titular="Daniela Sáenz Aguilar",
        cedula="8-877-2210",
        plan="preferente",
        estado="vigente",
        inicio_vigencia=date(2024, 11, 2),
        fin_vigencia=date(2027, 11, 1),
        deducible_anual=500.0,
        deducible_consumido=500.0,
        coaseguro_porcentaje=20,
        tope_anual=50_000.0,
        tope_consumido=1_100.0,
        # No declaro nada al contratar. El informe INF-2026-0035 menciona una
        # condicion de anos atras: ahi salta la revision medica.
        preexistencias_declaradas=[],
    ),
]


INFORMES: list[InformeMedico] = [
    # 1. Camino limpio: todo conforme -> APROBADO.
    InformeMedico(
        codigo="INF-2026-0031",
        paciente="Ricardo Mendoza Barría",
        cedula="8-812-2043",
        numero_poliza="POL-2024-0148",
        hospital="Hospital Punta Pacífica",
        medico_tratante="Dra. Ileana Sáez Moreno",
        especialidad="Cirugía general",
        fecha_informe=date(2026, 9, 4),
        fecha_cirugia_propuesta=date(2026, 9, 22),
        es_emergencia=False,
        monto_cotizado=6_800.0,
        documentos_adjuntos=[
            DOC_INFORME,
            DOC_CEDULA,
            DOC_COTIZACION,
            DOC_IMAGENES,
            DOC_LABORATORIO,
        ],
        texto=(
            "Paciente masculino de 54 años que acude a consulta por cuadro de tres meses "
            "de dolor en hipocondrio derecho, de tipo cólico, desencadenado por comidas "
            "grasas, acompañado de náuseas y distensión. Ha presentado cuatro episodios, "
            "el último de ocho horas de duración.\n\n"
            "Antecedentes: hipertensión arterial en tratamiento con losartán 50 mg diarios, "
            "controlada. Niega cirugías abdominales previas. No alergias conocidas.\n\n"
            "Examen físico: abdomen blando, Murphy positivo, sin signos de irritación "
            "peritoneal. Afebril, signos vitales estables.\n\n"
            "Ultrasonido abdominal (02/09/2026): vesícula biliar de paredes engrosadas de "
            "4 mm, con múltiples litos en su interior, el mayor de 18 mm. Vía biliar "
            "intrahepática y extrahepática no dilatada. Páncreas sin alteraciones.\n\n"
            "Laboratorios (02/09/2026): hemograma normal, bilirrubina total 0.9 mg/dL, "
            "fosfatasa alcalina 88 U/L, TGO 24 U/L, TGP 31 U/L, amilasa 62 U/L.\n\n"
            "Diagnóstico: colelitiasis con colecistitis crónica (K80.1).\n\n"
            "Plan: se indica extirpación de la vesícula biliar por vía laparoscópica, "
            "programada de forma electiva. Se explicó al paciente el procedimiento, los "
            "riesgos y la posibilidad de conversión a cirugía abierta. Estancia estimada "
            "de un día."
        ),
    ),
    # 2. Carencia no cumplida: afiliada en julio, plan Básico exige 365 dias.
    InformeMedico(
        codigo="INF-2026-0032",
        paciente="Yaritza Camaño Ríos",
        cedula="8-901-1187",
        numero_poliza="POL-2026-0731",
        hospital="Clínica Hospital San Fernando",
        medico_tratante="Dr. Abdiel Rodríguez Pinto",
        especialidad="Ortopedia y traumatología",
        fecha_informe=date(2026, 9, 5),
        fecha_cirugia_propuesta=date(2026, 9, 25),
        es_emergencia=False,
        monto_cotizado=4_200.0,
        documentos_adjuntos=[
            DOC_INFORME,
            DOC_CEDULA,
            DOC_COTIZACION,
            DOC_IMAGENES,
            DOC_PREANESTESICA,
        ],
        texto=(
            "Paciente femenina de 33 años, con dolor en rodilla derecha de seis semanas "
            "de evolución tras torsión practicando fútbol recreativo. Refiere bloqueo "
            "articular intermitente y sensación de chasquido al flexionar.\n\n"
            "Examen físico: derrame articular leve, McMurray positivo en compartimento "
            "medial, dolor a la palpación de interlínea interna. Estabilidad ligamentaria "
            "conservada. Rango de movilidad 0-110 grados, limitado por dolor.\n\n"
            "Resonancia magnética de rodilla derecha (28/08/2026): rotura horizontal del "
            "cuerpo y segmento posterior del menisco medial, sin extensión a la superficie "
            "articular. Ligamentos cruzados y colaterales íntegros. Cartílago conservado.\n\n"
            "Diagnóstico: rotura de menisco medial de rodilla derecha (S83.2).\n\n"
            "Plan: tras ocho semanas de manejo conservador con fisioterapia sin mejoría "
            "sintomática, se indica artroscopia de rodilla derecha con meniscectomía "
            "parcial medial. Procedimiento ambulatorio."
        ),
    ),
    # 3. Exclusion absoluta: finalidad estetica.
    InformeMedico(
        codigo="INF-2026-0033",
        paciente="Luis Alberto Quintero",
        cedula="4-742-1908",
        numero_poliza="POL-2023-0092",
        hospital="Centro Médico Paitilla",
        medico_tratante="Dr. Ramón Escobar Villar",
        especialidad="Cirugía plástica",
        fecha_informe=date(2026, 9, 2),
        fecha_cirugia_propuesta=date(2026, 10, 6),
        es_emergencia=False,
        monto_cotizado=5_500.0,
        documentos_adjuntos=[DOC_INFORME, DOC_CEDULA],
        texto=(
            "Paciente masculino de 47 años que solicita valoración por acumulación de "
            "tejido adiposo en región abdominal y flancos, persistente a pesar de dieta "
            "supervisada y ejercicio regular durante los últimos catorce meses. Ha "
            "descendido 9 kg de peso en ese periodo.\n\n"
            "Antecedentes: diabetes mellitus tipo 2 en tratamiento con metformina 850 mg "
            "dos veces al día, hemoglobina glicosilada 6.4%.\n\n"
            "Examen físico: IMC 27.1. Panículo adiposo localizado en abdomen inferior y "
            "flancos, sin hernias, sin diastasis de rectos significativa. Piel con buena "
            "elasticidad. No hay dermatitis intertriginosa ni lesiones asociadas.\n\n"
            "Diagnóstico: lipodistrofia localizada abdominal, sin repercusión funcional.\n\n"
            "Plan: el paciente solicita mejorar el contorno corporal. Se indica "
            "lipoescultura de abdomen y flancos con fines de remodelación estética. Se "
            "explicó que no existe indicación médica funcional para el procedimiento."
        ),
    ),
    # 4. Expediente incompleto: faltan historia clinica y preanestesica.
    InformeMedico(
        codigo="INF-2026-0034",
        paciente="Luis Alberto Quintero",
        cedula="4-742-1908",
        numero_poliza="POL-2023-0092",
        hospital="Centro Médico Paitilla",
        medico_tratante="Dr. Fernando Bethancourt Lao",
        especialidad="Neurocirugía",
        fecha_informe=date(2026, 9, 7),
        fecha_cirugia_propuesta=date(2026, 10, 1),
        es_emergencia=False,
        monto_cotizado=14_500.0,
        # Faltan DOC_HISTORIA y DOC_PREANESTESICA.
        documentos_adjuntos=[DOC_INFORME, DOC_CEDULA, DOC_COTIZACION, DOC_IMAGENES],
        texto=(
            "Paciente masculino de 47 años con lumbalgia irradiada a miembro inferior "
            "izquierdo de cinco meses de evolución, con parestesias en cara lateral de "
            "pierna y dorso del pie. Escala visual analógica de dolor 8/10. No responde a "
            "AINEs, gabapentina ni doce sesiones de fisioterapia.\n\n"
            "Examen físico: Lasègue positivo a 35 grados en el lado izquierdo. Hipoestesia "
            "en territorio L5 izquierdo. Fuerza de dorsiflexión del pie 4/5. Reflejos "
            "aquíleos conservados y simétricos. No hay alteración esfinteriana.\n\n"
            "Resonancia magnética lumbosacra (30/08/2026): hernia discal extruida L4-L5 "
            "de localización paramedial izquierda, con compromiso del receso lateral y "
            "contacto con la raíz L5 izquierda. Canal lumbar de calibre conservado en el "
            "resto de los niveles.\n\n"
            "Diagnóstico: hernia de disco lumbar L4-L5 con radiculopatía L5 izquierda (M51.1).\n\n"
            "Plan: se indica microdiscectomía lumbar L4-L5 por vía posterior. El paciente "
            "es diabético conocido, en tratamiento y con buen control metabólico."
        ),
    ),
    # 5. Preexistencia no declarada: la hernia es anterior a la poliza.
    InformeMedico(
        codigo="INF-2026-0035",
        paciente="Daniela Sáenz Aguilar",
        cedula="8-877-2210",
        numero_poliza="POL-2024-0602",
        hospital="Hospital Nacional",
        medico_tratante="Dr. Jorge Aizpurúa Delgado",
        especialidad="Cirugía general",
        fecha_informe=date(2026, 9, 8),
        fecha_cirugia_propuesta=date(2026, 9, 29),
        es_emergencia=False,
        monto_cotizado=5_200.0,
        documentos_adjuntos=[DOC_INFORME, DOC_CEDULA, DOC_COTIZACION, DOC_LABORATORIO],
        texto=(
            "Paciente femenina de 41 años que consulta por aumento de volumen en región "
            "inguinal derecha. Refiere que la tumoración fue detectada por primera vez en "
            "2021 y que en aquel momento fue valorada en consulta externa de cirugía, donde "
            "se le indicó manejo expectante por ser de pequeño tamaño y poco sintomática. "
            "En los últimos seis meses ha crecido y aparece dolor al final del día y al "
            "cargar peso en el trabajo.\n\n"
            "Antecedentes quirúrgicos: cesárea en 2016. Sin otros antecedentes de "
            "relevancia. No fumadora.\n\n"
            "Examen físico: tumoración inguinal derecha de aproximadamente 4 cm, reductible, "
            "con maniobra de Valsalva positiva, sin signos de incarceración. Anillo inguinal "
            "izquierdo competente.\n\n"
            "Laboratorios (05/09/2026): hemograma, química y coagulación dentro de "
            "parámetros normales.\n\n"
            "Diagnóstico: hernia inguinal derecha reductible (K40.9).\n\n"
            "Plan: se indica reparación de hernia inguinal derecha con colocación de malla, "
            "por vía abierta. Procedimiento de corta estancia."
        ),
    ),
    # 6. Urgencia: la carencia no aplica. El escenario mas ilustrativo.
    InformeMedico(
        codigo="INF-2026-0036",
        paciente="Yaritza Camaño Ríos",
        cedula="8-901-1187",
        numero_poliza="POL-2026-0731",
        hospital="Clínica Hospital San Fernando",
        medico_tratante="Dra. Katherine Ng Barría",
        especialidad="Cirugía de urgencia",
        fecha_informe=date(2026, 9, 10),
        fecha_cirugia_propuesta=date(2026, 9, 10),
        es_emergencia=True,
        monto_cotizado=3_900.0,
        documentos_adjuntos=[DOC_INFORME, DOC_CEDULA, DOC_LABORATORIO],
        texto=(
            "Paciente femenina de 33 años que ingresa por el servicio de urgencias con "
            "dolor abdominal de dieciocho horas de evolución, de inicio periumbilical y "
            "migración posterior a fosa iliaca derecha, acompañado de anorexia, náuseas y "
            "un vómito. Temperatura 38.1 grados centígrados.\n\n"
            "Examen físico: dolor a la palpación en fosa iliaca derecha con defensa "
            "localizada, Blumberg positivo, McBurney positivo, Rovsing positivo. Ruidos "
            "intestinales disminuidos.\n\n"
            "Laboratorios (10/09/2026): leucocitos 15.400/mm3 con 84% de neutrófilos, "
            "proteína C reactiva 62 mg/L. Prueba de embarazo negativa. Examen de orina sin "
            "alteraciones.\n\n"
            "Ultrasonido abdominal en urgencias: estructura tubular no compresible en fosa "
            "iliaca derecha de 9 mm de diámetro, con líquido periapendicular.\n\n"
            "Puntuación de Alvarado: 9 puntos.\n\n"
            "Diagnóstico: apendicitis aguda no perforada (K35.80).\n\n"
            "Plan: se indica apendicectomía por laparoscopia de forma urgente, en las "
            "próximas horas. Se inicia antibioticoterapia y se mantiene a la paciente en "
            "ayunas. El retraso del procedimiento conlleva riesgo de perforación y "
            "peritonitis."
        ),
    ),
    # 7. El tope anual ya casi agotado: aprueba, pero con condiciones.
    InformeMedico(
        codigo="INF-2026-0037",
        paciente="Marisol Ortega Peña",
        cedula="8-455-0921",
        numero_poliza="POL-2022-0455",
        hospital="Hospital Santo Tomás",
        medico_tratante="Dr. Eduardo Chanis Pérez",
        especialidad="Ortopedia y traumatología",
        fecha_informe=date(2026, 9, 3),
        fecha_cirugia_propuesta=date(2026, 10, 14),
        es_emergencia=False,
        monto_cotizado=32_000.0,
        documentos_adjuntos=[
            DOC_INFORME,
            DOC_CEDULA,
            DOC_COTIZACION,
            DOC_IMAGENES,
            DOC_PREANESTESICA,
        ],
        texto=(
            "Paciente femenina de 68 años con gonalgia derecha de cuatro años de evolución, "
            "progresiva, con dolor en reposo y nocturno en los últimos ocho meses. Camina "
            "con bastón y refiere limitación importante para las actividades de la vida "
            "diaria. Ha recibido tres ciclos de viscosuplementación y analgesia escalonada "
            "sin respuesta sostenida.\n\n"
            "Examen físico: deformidad en varo de 12 grados, crepitación palpable, rango de "
            "movilidad 10-95 grados. Marcha claudicante. No hay signos de infección.\n\n"
            "Radiografías de rodilla en carga (25/08/2026): pinzamiento completo del "
            "compartimento femorotibial medial con contacto hueso-hueso, esclerosis "
            "subcondral, osteofitos marginales y quistes subcondrales. Kellgren-Lawrence "
            "grado IV.\n\n"
            "Diagnóstico: gonartrosis primaria grado IV de rodilla derecha (M17.1).\n\n"
            "Plan: se indica reemplazo total de rodilla derecha con prótesis cementada. "
            "Se prevé hospitalización de tres días y rehabilitación posterior."
        ),
    ),
    # 8. Poliza en mora: se rechaza antes de mirar el resto del expediente.
    InformeMedico(
        codigo="INF-2026-0038",
        paciente="Ernesto Villalaz Gómez",
        cedula="7-112-0784",
        numero_poliza="POL-2025-0310",
        hospital="Centro Oftalmológico Metropolitano",
        medico_tratante="Dra. Sofía Arjona Cedeño",
        especialidad="Oftalmología",
        fecha_informe=date(2026, 9, 1),
        fecha_cirugia_propuesta=date(2026, 9, 24),
        es_emergencia=False,
        monto_cotizado=2_800.0,
        documentos_adjuntos=[DOC_INFORME, DOC_CEDULA, DOC_COTIZACION, DOC_IMAGENES],
        texto=(
            "Paciente masculino de 71 años con disminución progresiva de la agudeza visual "
            "en ojo izquierdo durante los últimos dos años, con deslumbramiento nocturno y "
            "dificultad para conducir y leer.\n\n"
            "Agudeza visual: ojo derecho 20/30 corregida, ojo izquierdo 20/200 corregida.\n\n"
            "Biomicroscopía: opacidad nuclear y cortical densa en cristalino izquierdo, "
            "grado NO4 NC4 según clasificación LOCS III. Cámara anterior amplia, pupila "
            "reactiva. Ojo derecho con esclerosis nuclear incipiente.\n\n"
            "Fondo de ojo: dificultad de visualización en ojo izquierdo por la opacidad; "
            "retina aplicada en la periferia explorable. Ojo derecho sin retinopatía.\n\n"
            "Biometría y cálculo de lente intraocular (28/08/2026): longitud axial 23.4 mm, "
            "lente monofocal de 21.0 dioptrías.\n\n"
            "Diagnóstico: catarata senil nuclear del ojo izquierdo (H25.1).\n\n"
            "Plan: se indica extracción de catarata por facoemulsificación con implante de "
            "lente intraocular monofocal en cámara posterior, ojo izquierdo. Procedimiento "
            "ambulatorio con anestesia tópica."
        ),
    ),
]
