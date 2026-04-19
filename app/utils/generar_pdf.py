import base64
import html
import os
from datetime import datetime

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer
from app.services.medicacion_service import obtener_medicacion_por_riesgo


ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))
LOGO_PATH = os.path.join(ASSETS_DIR, "Gemini_Generated_Image_.png")
GTK_WINDOWS_BIN_PATHS = [
    r"C:\Program Files\GTK3-Runtime Win64\bin",
    r"C:\Program Files (x86)\GTK3-Runtime Win64\bin",
    r"C:\gtk\bin",
]


def _configurar_dlls_weasyprint_windows() -> None:
    if os.name != "nt":
        return

    path_actual = os.environ.get("PATH", "")
    path_items = path_actual.split(";") if path_actual else []

    for dll_dir in GTK_WINDOWS_BIN_PATHS:
        if not os.path.isdir(dll_dir):
            continue

        try:
            os.add_dll_directory(dll_dir)
        except Exception:
            pass

        if dll_dir not in path_items:
            path_items.insert(0, dll_dir)

    if path_items:
        os.environ["PATH"] = ";".join(path_items)


def _obtener_logo_data_url() -> str:
    if not os.path.exists(LOGO_PATH):
        return ""

    try:
        with open(LOGO_PATH, "rb") as logo_file:
            logo_b64 = base64.b64encode(logo_file.read()).decode("ascii")
        return f"data:image/png;base64,{logo_b64}"
    except Exception:
        return ""


def _formatear_fecha(valor_fecha) -> str:
    if valor_fecha is None:
        return "N/A"
    if isinstance(valor_fecha, datetime):
        return valor_fecha.strftime("%d/%m/%Y %H:%M")
    return str(valor_fecha)


def _si_no(valor) -> str:
    return "Sí" if bool(valor) else "No"


def _formatear_numero(valor, decimales: int = 2) -> str:
    try:
        return f"{float(valor):.{decimales}f}"
    except Exception:
        return "N/A"


def _obtener_pam_consulta(consulta) -> float:
    pam = getattr(consulta, "pam", None)
    try:
        if pam is not None and float(pam) > 0:
            return float(pam)
    except Exception:
        pass

    try:
        sistolica = float(getattr(consulta, "presion_sistolica", 0))
        diastolica = float(getattr(consulta, "presion_diastolica", 0))
        return (sistolica + 2 * diastolica) / 3
    except Exception:
        return 0.0


def _obtener_medicacion_recomendada(riesgo) -> dict:
    riesgo_norm = str(riesgo or "NINGUNO").strip().upper()
    data = obtener_medicacion_por_riesgo(riesgo_norm)
    if not data:
        return {
            "estado": "Sin recomendación",
            "detalle": [],
        }
    return data


def _resumen_medicacion_para_pdf(medicacion_data: dict) -> list[str]:
    lineas: list[str] = []
    estado = str(medicacion_data.get("estado") or "Sin recomendación")
    lineas.append(f"Estado: {estado}")

    detalle = medicacion_data.get("detalle") or []
    if not detalle:
        lineas.append("Sin fármacos para este nivel de riesgo.")
        return lineas

    for grupo in detalle:
        grupo_nombre = str(grupo.get("grupo") or "Sin grupo")
        lineas.append(f"{grupo_nombre}:")

        for med in grupo.get("medicamentos") or []:
            nombre = str(med.get("nombre") or "Sin nombre")

            partes = []
            if med.get("dosis"):
                partes.append(f"dosis {med['dosis']}")
            if med.get("frecuencia"):
                partes.append(f"frecuencia {med['frecuencia']}")
            if med.get("max"):
                partes.append(f"máx {med['max']}")
            if med.get("inicio"):
                partes.append(f"inicio {med['inicio']}")
            if med.get("horario"):
                partes.append(f"horario {med['horario']}")
            if med.get("suspension"):
                partes.append(f"suspensión {med['suspension']}")

            if partes:
                lineas.append(f"- {nombre}: {' | '.join(partes)}")
            else:
                lineas.append(f"- {nombre}")

            if med.get("alerta"):
                lineas.append(f"  Alerta: {med['alerta']}")

    return lineas


def _render_medicacion_html(medicacion_data: dict) -> str:
    estado = html.escape(str(medicacion_data.get("estado") or "Sin recomendación"))
    detalle = medicacion_data.get("detalle") or []

    if not detalle:
        return f'<div class="med-empty">Estado: {estado}. Sin fármacos para este nivel de riesgo.</div>'

    grupos_html = []
    for grupo in detalle:
        grupo_nombre = html.escape(str(grupo.get("grupo") or "Sin grupo"))

        meds_html = []
        for med in grupo.get("medicamentos") or []:
            nombre = html.escape(str(med.get("nombre") or "Sin nombre"))
            campos = []

            for etiqueta, key in (
                ("Dosis", "dosis"),
                ("Frecuencia", "frecuencia"),
                ("Máximo", "max"),
                ("Inicio", "inicio"),
                ("Horario", "horario"),
                ("Suspensión", "suspension"),
            ):
                valor = med.get(key)
                if valor:
                    campos.append(
                        f'<span><b>{etiqueta}:</b> {html.escape(str(valor))}</span>'
                    )

            alerta_html = ""
            if med.get("alerta"):
                alerta_html = (
                    f'<div class="med-alerta">Alerta: {html.escape(str(med.get("alerta")))}</div>'
                )

            meds_html.append(
                """
                <div class="med-card">
                    <div class="med-name">{nombre}</div>
                    <div class="med-meta">{campos}</div>
                    {alerta}
                </div>
                """.format(
                    nombre=nombre,
                    campos="".join(campos) if campos else "<span>Sin dosis registrada</span>",
                    alerta=alerta_html,
                )
            )

        grupos_html.append(
            """
            <div class="med-group">
                <div class="med-group-title">{grupo}</div>
                <div class="med-grid">{meds}</div>
            </div>
            """.format(
                grupo=grupo_nombre,
                meds="".join(meds_html),
            )
        )

    return f'<div class="med-estado">Estado: {estado}</div>{"".join(grupos_html)}'


def _generar_pdf_reportlab_fallback(consulta, paciente, ruta_pdf, riesgo, score, interpretacion):
    doc = SimpleDocTemplate(ruta_pdf)
    styles = getSampleStyleSheet()

    texto_interpretacion = html.escape(str(interpretacion or "Sin interpretación disponible")).replace("\n", "<br/>")
    fecha_consulta = _formatear_fecha(getattr(consulta, "fecha_hora_consulta", None))
    pam = _obtener_pam_consulta(consulta)
    tipo_sangre = str(getattr(paciente, "tipo_sangre", None) or "No especificado")
    medicacion_data = _obtener_medicacion_recomendada(riesgo)
    lineas_medicacion = _resumen_medicacion_para_pdf(medicacion_data)

    contenido = []

    if os.path.exists(LOGO_PATH):
        try:
            contenido.append(Image(LOGO_PATH, width=170, height=170))
            contenido.append(Spacer(1, 8))
        except Exception:
            pass

    contenido.extend([
        Paragraph("Reporte Clínico", styles["Title"]),
        Paragraph("VitaPrenatal - Evaluación de Preeclampsia", styles["Normal"]),
        Spacer(1, 12),
        Paragraph(f"Fecha: {fecha_consulta}", styles["Normal"]),
        Paragraph(f"ID Consulta: {consulta.id}", styles["Normal"]),
        Paragraph(f"Paciente: {paciente.nombre}", styles["Normal"]),
        Paragraph(f"Edad Paciente: {paciente.edad}", styles["Normal"]),
        Paragraph(f"Teléfono: {paciente.telefono}", styles["Normal"]),
        Paragraph(f"Ciudad: {paciente.ciudad}", styles["Normal"]),
        Paragraph(f"Tipo de sangre: {tipo_sangre}", styles["Normal"]),
        Paragraph(f"Edad: {consulta.edad_madre}", styles["Normal"]),
        Paragraph(f"Edad Gestacional: {consulta.edad_gestacional}", styles["Normal"]),
        Paragraph(f"Peso: {consulta.peso}", styles["Normal"]),
        Paragraph(f"Altura: {consulta.altura}", styles["Normal"]),
        Paragraph(f"IMC: {consulta.imc}", styles["Normal"]),
        Paragraph(f"Presión Sistólica: {consulta.presion_sistolica}", styles["Normal"]),
        Paragraph(f"Presión Diastólica: {consulta.presion_diastolica}", styles["Normal"]),
        Paragraph(f"PAM: {_formatear_numero(pam)} mmHg", styles["Normal"]),
        Paragraph(f"Hipertensión previa: {_si_no(paciente.hipertension_previa)}", styles["Normal"]),
        Paragraph(f"Diabetes: {_si_no(paciente.diabetes)}", styles["Normal"]),
        Paragraph(
            f"Antecedentes familiares HTA: {_si_no(paciente.antecedentes_familia_hipertension)}",
            styles["Normal"],
        ),
        Paragraph(f"Cardiopatía familiar: {_si_no(getattr(paciente, 'fam_cardiopatia', False))}", styles["Normal"]),
        Paragraph(f"Enfermedad renal crónica: {_si_no(getattr(paciente, 'enf_renal_cronica', False))}", styles["Normal"]),
        Paragraph(f"Embarazo múltiple: {_si_no(getattr(paciente, 'embarazo_multiple', False))}", styles["Normal"]),
        Paragraph(
            f"Antecedente de preeclampsia en embarazo previo: "
            f"{_si_no(getattr(paciente, 'antecedente_preeclampsia_embarazo_previo', False))}",
            styles["Normal"],
        ),
        Paragraph(f"Muerte fetal: {_si_no(getattr(paciente, 'muerte_fetal', False))}", styles["Normal"]),
        Paragraph(f"Restricción fetal: {_si_no(getattr(paciente, 'restriccion_fetal', False))}", styles["Normal"]),
        Paragraph(f"Abortos previos: {getattr(paciente, 'abortos_previos', 0)}", styles["Normal"]),
        Paragraph(f"Cesáreas previas: {getattr(paciente, 'cesarea_previos', 0)}", styles["Normal"]),
        Paragraph(f"Embarazos previos: {getattr(paciente, 'embarazos_previos', 0)}", styles["Normal"]),
        Paragraph(f"Partos previos: {getattr(paciente, 'partos_previos', 0)}", styles["Normal"]),
        Spacer(1, 10),
        Paragraph(f"Riesgo: {riesgo}", styles["Heading3"]),
        Paragraph(f"Score: {score}", styles["Normal"]),
        Spacer(1, 10),
        Paragraph("Interpretación Clínica", styles["Heading3"]),
        Paragraph(texto_interpretacion, styles["Normal"]),
    ])

    contenido.extend([
        Spacer(1, 10),
        Paragraph("Medicación recomendada", styles["Heading3"]),
    ])

    for linea in lineas_medicacion:
        contenido.append(Paragraph(html.escape(str(linea)), styles["Normal"]))

    doc.build(contenido)


def _generar_pdf_xhtml2pdf_fallback(html_content: str, ruta_pdf: str) -> bool:
    try:
        from xhtml2pdf import pisa
    except Exception as exc:
        print(f"xhtml2pdf no disponible ({exc}).")
        return False

    try:
        with open(ruta_pdf, "wb") as output_pdf:
            pisa_status = pisa.CreatePDF(src=html_content, dest=output_pdf, encoding="utf-8")

        if getattr(pisa_status, "err", 1):
            print("xhtml2pdf no pudo renderizar el HTML del reporte.")
            return False

        return True
    except Exception as exc:
        print(f"Error en fallback xhtml2pdf ({exc}).")
        return False


def generar_html_reporte(consulta, paciente, riesgo, score, interpretacion) -> str:

    riesgo_label = str(riesgo).upper()

    color_riesgo = {
        "NINGUNO": "#95A5A6",
        "MEDIO": "#FDCB6E",
        "ALTO": "#D63031",
        "HOSPITALIZACION": "#2980B9",
    }.get(riesgo_label, "#999")

    logo_data_url = _obtener_logo_data_url()
    fecha_consulta = _formatear_fecha(getattr(consulta, "fecha_hora_consulta", None))
    pam = _obtener_pam_consulta(consulta)

    nombre_paciente = html.escape(str(getattr(paciente, "nombre", "N/A") or "N/A"))
    ciudad = html.escape(str(getattr(paciente, "ciudad", "N/A") or "N/A"))
    telefono = html.escape(str(getattr(paciente, "telefono", "N/A") or "N/A"))
    domicilio = html.escape(str(getattr(paciente, "domicilio", "N/A") or "N/A"))
    estado_civil = html.escape(str(getattr(paciente, "estado_civil", "N/A") or "N/A"))
    tipo_sangre = html.escape(str(getattr(paciente, "tipo_sangre", None) or "No especificado"))

    interpretacion_segura = html.escape(str(interpretacion or "Sin interpretación disponible")).replace("\n", "<br/>")

    antecedente_hta = _si_no(getattr(paciente, "hipertension_previa", False))
    antecedente_diabetes = _si_no(getattr(paciente, "diabetes", False))
    antecedente_familiar = _si_no(getattr(paciente, "antecedentes_familia_hipertension", False))
    antecedente_cardio = _si_no(getattr(paciente, "fam_cardiopatia", False))
    antecedente_renal = _si_no(getattr(paciente, "enf_renal_cronica", False))
    antecedente_embarazo_multiple = _si_no(getattr(paciente, "embarazo_multiple", False))
    antecedente_preeclampsia_previa = _si_no(
        getattr(paciente, "antecedente_preeclampsia_embarazo_previo", False)
    )
    antecedente_muerte_fetal = _si_no(getattr(paciente, "muerte_fetal", False))
    antecedente_restriccion_fetal = _si_no(getattr(paciente, "restriccion_fetal", False))

    abortos_previos = html.escape(str(getattr(paciente, "abortos_previos", 0) or 0))
    cesareas_previas = html.escape(str(getattr(paciente, "cesarea_previos", 0) or 0))
    embarazos_previos = html.escape(str(getattr(paciente, "embarazos_previos", 0) or 0))
    partos_previos = html.escape(str(getattr(paciente, "partos_previos", 0) or 0))

    medicacion_data = _obtener_medicacion_recomendada(riesgo_label)
    medicacion_html = _render_medicacion_html(medicacion_data)

    logo_html = (
        f'<img class="brand-logo" src="{logo_data_url}" alt="Logo VitaPrenatal" />'
        if logo_data_url
        else '<div class="brand-fallback">VitaPrenatal</div>'
    )

    html_content = f"""
    <html>
    <head>
        <style>
            @page {{
                size: A4;
                margin: 10mm;
            }}

            :root {{
                --brand-dark: #241824;
                --brand-main: #c8759f;
                --brand-soft: #f4d8e8;
                --brand-muted: #f8eff5;
                --ink: #332333;
                --ink-soft: #6f5a6a;
                --white: #ffffff;
            }}

            * {{
                box-sizing: border-box;
            }}

            body {{
                font-family: Helvetica, Arial, sans-serif;
                margin: 0;
                padding: 32px;
                background: radial-gradient(circle at top right, #ffeaf5 0%, #f8f1f5 42%, #f4ecf2 100%);
                color: var(--ink);
            }}

            .container {{
                background: var(--white);
                max-width: 880px;
                margin: 0 auto;
                padding: 28px 30px;
                border-radius: 22px;
                border: 1px solid #efd8e6;
                box-shadow: 0 18px 45px rgba(83, 40, 67, 0.13);
            }}

            .header {{
                display: table;
                width: 100%;
                table-layout: fixed;
                margin-bottom: 24px;
                padding: 16px 18px;
                border-radius: 18px;
                background: linear-gradient(125deg, #fff4fb 0%, #f8e6f1 55%, #f5e0ec 100%);
                border: 1px solid #efd4e3;
            }}

            .header-main {{
                display: table-cell;
                width: 72%;
                vertical-align: middle;
                padding-right: 14px;
            }}

            .header-logo {{
                display: table-cell;
                width: 28%;
                text-align: right;
                vertical-align: middle;
            }}

            .brand-logo {{
                width: 110px;
                height: 110px;
                display: block;
                margin-left: auto;
            }}

            .brand-fallback {{
                width: 110px;
                height: 110px;
                border-radius: 16px;
                display: table;
                margin-left: auto;
                background: var(--brand-soft);
                color: var(--brand-dark);
                font-weight: 700;
                text-align: center;
                line-height: 110px;
            }}

            .title {{
                font-size: 29px;
                font-weight: bold;
                color: #5a3350;
                letter-spacing: 0.3px;
                margin-bottom: 6px;
            }}

            .subtitle {{
                font-size: 14px;
                color: var(--ink-soft);
                margin-bottom: 6px;
            }}

            .meta {{
                color: #7d6574;
                font-size: 12px;
            }}

            .section {{
                margin-top: 14px;
                padding: 16px;
                border-radius: 16px;
                background: var(--brand-muted);
                border: 1px solid #ecd6e4;
                page-break-inside: auto;
            }}

            .section-title {{
                font-weight: bold;
                margin-bottom: 10px;
                color: #6f3d5f;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.7px;
            }}

            .grid {{
                font-size: 0;
            }}

            .card {{
                display: inline-block;
                width: 49%;
                margin: 0 2% 10px 0;
                vertical-align: top;
                background: var(--white);
                padding: 10px 12px;
                border-radius: 12px;
                border: 1px solid #efdce8;
                min-height: 58px;
            }}

            .card:nth-child(2n) {{
                margin-right: 0;
            }}

            .card.span-2 {{
                width: 100%;
                margin-right: 0;
            }}

            .label {{
                font-size: 11px;
                color: #967d8d;
                line-height: 1.2;
            }}

            .value {{
                font-weight: bold;
                margin-top: 3px;
                font-size: 16px;
                line-height: 1.15;
                color: #3f2a3a;
                word-break: break-word;
                overflow-wrap: anywhere;
            }}

            .score-card {{
                min-height: auto;
                padding-top: 12px;
                padding-bottom: 12px;
            }}

            .score-value {{
                font-size: 28px;
            }}

            .riesgo {{
                margin-top: 12px;
                padding: 14px;
                text-align: center;
                border-radius: 12px;
                color: white;
                font-weight: bold;
                font-size: 16px;
                letter-spacing: 0.6px;
            }}

            .interpretacion {{
                line-height: 1.5;
                font-size: 13px;
                background: var(--white);
                border: 1px solid #eedee8;
                border-radius: 12px;
                padding: 12px;
            }}

            .footer {{
                margin-top: 22px;
                text-align: center;
                font-size: 11px;
                color: #9c8292;
            }}

            .group-grid {{
                font-size: 0;
            }}

            .subgroup {{
                display: inline-block;
                width: 49%;
                margin: 0 2% 10px 0;
                vertical-align: top;
                background: var(--white);
                border: 1px solid #efdce8;
                border-radius: 12px;
                padding: 10px;
                min-height: 100%;
            }}

            .subgroup:nth-child(2n) {{
                margin-right: 0;
            }}

            .subgroup-title {{
                font-size: 13px;
                font-weight: bold;
                color: #6b445b;
                margin-bottom: 8px;
            }}

            .mini-list {{
                display: block;
            }}

            .mini-item {{
                display: table;
                width: 100%;
                background: #fbf6fa;
                border: 1px solid #f0e4eb;
                border-radius: 8px;
                padding: 6px 8px;
                font-size: 13px;
                line-height: 1.25;
                min-height: 34px;
                margin-bottom: 6px;
            }}

            .mini-item:last-child {{
                margin-bottom: 0;
            }}

            .mini-item span {{
                display: table-cell;
                width: 82%;
                vertical-align: middle;
                line-height: 1.2;
                overflow-wrap: anywhere;
            }}

            .mini-item b {{
                display: table-cell;
                width: 18%;
                vertical-align: middle;
                text-align: right;
            }}

            .med-estado {{
                font-size: 12px;
                margin-bottom: 10px;
                color: #6f5a6a;
            }}

            .med-group {{
                background: var(--white);
                border: 1px solid #efdce8;
                border-radius: 12px;
                padding: 10px;
                margin-bottom: 10px;
            }}

            .med-group-title {{
                font-size: 12px;
                font-weight: bold;
                color: #6b445b;
                margin-bottom: 8px;
            }}

            .med-grid {{
                display: block;
            }}

            .med-card {{
                background: #fbf6fa;
                border: 1px solid #f0e4eb;
                border-radius: 10px;
                padding: 8px;
                margin-bottom: 8px;
            }}

            .med-card:last-child {{
                margin-bottom: 0;
            }}

            .med-name {{
                font-weight: bold;
                margin-bottom: 4px;
            }}

            .med-meta span {{
                display: block;
                font-size: 12px;
                margin-bottom: 2px;
            }}

            .med-alerta {{
                margin-top: 6px;
                font-size: 11px;
                color: #a1405f;
                background: #fff1f5;
                border: 1px solid #f5cddb;
                border-radius: 8px;
                padding: 5px 6px;
            }}

            .med-empty {{
                background: var(--white);
                border: 1px solid #efdce8;
                border-radius: 10px;
                padding: 8px;
                font-size: 12px;
            }}

            @media print {{
                body {{
                    padding: 0;
                    background: #ffffff;
                }}

                .container {{
                    max-width: none;
                    width: 100%;
                    margin: 0;
                    padding: 12px 14px;
                    border-radius: 10px;
                    box-shadow: none;
                }}

                .header {{
                    display: table;
                    width: 100%;
                    margin-bottom: 10px;
                    padding: 10px 12px;
                    border-radius: 10px;
                }}

                .header-main {{
                    width: 74%;
                    padding-right: 10px;
                }}

                .header-logo {{
                    width: 26%;
                }}

                .brand-logo,
                .brand-fallback {{
                    width: 88px;
                    height: 88px;
                    line-height: 88px;
                }}

                .title {{
                    font-size: 24px;
                    margin-bottom: 2px;
                }}

                .subtitle {{
                    font-size: 12px;
                    margin-bottom: 2px;
                }}

                .meta {{
                    font-size: 11px;
                }}

                .section {{
                    margin-top: 10px;
                    padding: 12px;
                    border-radius: 10px;
                }}

                .section.keep-together {{
                    break-inside: avoid;
                    page-break-inside: avoid;
                }}

                .section-title {{
                    font-size: 12px;
                    margin-bottom: 6px;
                    break-after: avoid;
                    page-break-after: avoid;
                }}

                .card {{
                    width: 49%;
                    margin: 0 2% 8px 0;
                    padding: 8px 9px;
                    border-radius: 8px;
                    break-inside: avoid;
                    page-break-inside: avoid;
                    min-height: 52px;
                }}

                .card:nth-child(2n) {{
                    margin-right: 0;
                }}

                .card.span-2 {{
                    width: 100%;
                    margin-right: 0;
                }}

                .label {{
                    font-size: 10px;
                }}

                .value {{
                    font-size: 13px;
                    margin-top: 2px;
                }}

                .score-value {{
                    font-size: 22px;
                }}

                .riesgo {{
                    margin-top: 8px;
                    padding: 10px;
                    font-size: 14px;
                }}

                .interpretacion {{
                    padding: 10px;
                    font-size: 12px;
                }}

                .footer {{
                    margin-top: 10px;
                    font-size: 10px;
                }}

                .subgroup {{
                    width: 49%;
                    margin: 0 2% 8px 0;
                    padding: 8px;
                    border-radius: 8px;
                    break-inside: avoid;
                    page-break-inside: avoid;
                }}

                .subgroup:nth-child(2n) {{
                    margin-right: 0;
                }}

                .mini-item {{
                    padding: 5px 6px;
                    font-size: 12px;
                    line-height: 1.25;
                }}

                .med-group {{
                    padding: 8px;
                    border-radius: 8px;
                    break-inside: avoid;
                    page-break-inside: avoid;
                }}

                .med-name {{
                    font-size: 11px;
                }}

                .med-meta span,
                .med-alerta,
                .med-estado,
                .med-empty {{
                    font-size: 10px;
                }}
            }}
        </style>
    </head>

    <body>
        <div class="container">

            <div class="header">
                <div class="header-main">
                    <div class="title">Reporte Clínico VitaPrenatal</div>
                    <div class="subtitle">Evaluación de riesgo de preeclampsia con datos reales de la consulta</div>
                    <div class="meta">Fecha de evaluación: {fecha_consulta}</div>
                </div>
                <div class="header-logo">
                    {logo_html}
                </div>
            </div>

            <div class="section">
                <div class="section-title">Información General</div>
                <div class="grid">
                    <div class="card">
                        <div class="label">ID Consulta</div>
                        <div class="value">{consulta.id}</div>
                    </div>
                    <div class="card">
                        <div class="label">Paciente</div>
                        <div class="value">{nombre_paciente}</div>
                    </div>
                    <div class="card">
                        <div class="label">Ciudad</div>
                        <div class="value">{ciudad}</div>
                    </div>
                    <div class="card">
                        <div class="label">Teléfono</div>
                        <div class="value">{telefono}</div>
                    </div>
                    <div class="card">
                        <div class="label">Domicilio</div>
                        <div class="value">{domicilio}</div>
                    </div>
                    <div class="card">
                        <div class="label">Estado Civil</div>
                        <div class="value">{estado_civil}</div>
                    </div>
                    <div class="card span-2">
                        <div class="label">Tipo de sangre</div>
                        <div class="value">{tipo_sangre}</div>
                    </div>
                </div>
            </div>

            <div class="section">
                <div class="section-title">Datos Clínicos</div>
                <div class="grid">
                    <div class="card">
                        <div class="label">Edad</div>
                        <div class="value">{consulta.edad_madre} años</div>
                    </div>
                    <div class="card">
                        <div class="label">Edad Gestacional</div>
                        <div class="value">{consulta.edad_gestacional} semanas</div>
                    </div>
                    <div class="card">
                        <div class="label">IMC</div>
                        <div class="value">{consulta.imc}</div>
                    </div>
                    <div class="card">
                        <div class="label">Peso</div>
                        <div class="value">{consulta.peso} kg</div>
                    </div>
                    <div class="card">
                        <div class="label">Altura</div>
                        <div class="value">{consulta.altura} m</div>
                    </div>
                    <div class="card">
                        <div class="label">Presión Sistólica</div>
                        <div class="value">{consulta.presion_sistolica} mmHg</div>
                    </div>
                    <div class="card">
                        <div class="label">Presión Diastólica</div>
                        <div class="value">{consulta.presion_diastolica} mmHg</div>
                    </div>
                    <div class="card">
                        <div class="label">PAM</div>
                        <div class="value">{_formatear_numero(pam)} mmHg</div>
                    </div>
                    <div class="card">
                        <div class="label">Hipertensión previa</div>
                        <div class="value">{antecedente_hta}</div>
                    </div>
                    <div class="card">
                        <div class="label">Diabetes</div>
                        <div class="value">{antecedente_diabetes}</div>
                    </div>
                    <div class="card span-2">
                        <div class="label">Antecedentes familiares HTA</div>
                        <div class="value">{antecedente_familiar}</div>
                    </div>
                </div>
            </div>

            <div class="section">
                <div class="section-title">Antecedentes</div>
                <div class="group-grid">
                    <div class="subgroup">
                        <div class="subgroup-title">Heredo-familiares</div>
                        <div class="mini-list">
                            <div class="mini-item"><span>Cardiopatía familiar</span><b>{antecedente_cardio}</b></div>
                            <div class="mini-item"><span>Antecedentes familiares HTA</span><b>{antecedente_familiar}</b></div>
                        </div>
                    </div>

                    <div class="subgroup">
                        <div class="subgroup-title">Personales patológicos</div>
                        <div class="mini-list">
                            <div class="mini-item"><span>Enfermedad renal crónica</span><b>{antecedente_renal}</b></div>
                            <div class="mini-item"><span>Hipertensión previa</span><b>{antecedente_hta}</b></div>
                            <div class="mini-item"><span>Diabetes</span><b>{antecedente_diabetes}</b></div>
                        </div>
                    </div>

                    <div class="subgroup">
                        <div class="subgroup-title">Ginecoobstétricos</div>
                        <div class="mini-list">
                            <div class="mini-item"><span>Abortos previos</span><b>{abortos_previos}</b></div>
                            <div class="mini-item"><span>Cesáreas previas</span><b>{cesareas_previas}</b></div>
                            <div class="mini-item"><span>Embarazos previos</span><b>{embarazos_previos}</b></div>
                            <div class="mini-item"><span>Partos previos</span><b>{partos_previos}</b></div>
                            <div class="mini-item"><span>Preeclampsia en embarazo previo</span><b>{antecedente_preeclampsia_previa}</b></div>
                        </div>
                    </div>

                    <div class="subgroup">
                        <div class="subgroup-title">Otros</div>
                        <div class="mini-list">
                            <div class="mini-item"><span>Embarazo múltiple</span><b>{antecedente_embarazo_multiple}</b></div>
                            <div class="mini-item"><span>Muerte fetal</span><b>{antecedente_muerte_fetal}</b></div>
                            <div class="mini-item"><span>Restricción fetal</span><b>{antecedente_restriccion_fetal}</b></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="section keep-together">
                <div class="section-title">Resultado</div>

                <div class="card score-card">
                    <div class="label">Score</div>
                    <div class="value score-value">{_formatear_numero(score)}</div>
                </div>

                <div class="riesgo" style="background:{color_riesgo}">
                    {riesgo_label}
                </div>
            </div>

            <div class="section keep-together">
                <div class="section-title">Interpretación Clínica</div>
                <div class="interpretacion">{interpretacion_segura}</div>
            </div>

            <div class="section">
                <div class="section-title">Medicación recomendada</div>
                {medicacion_html}
            </div>

            <div class="footer">
                Sistema Biomédico • Generado automáticamente
            </div>

        </div>
    </body>
    </html>
    """

    return html_content


def generar_pdf(consulta, paciente, ruta_pdf, riesgo, score, interpretacion):
    html_content = generar_html_reporte(
        consulta=consulta,
        paciente=paciente,
        riesgo=riesgo,
        score=score,
        interpretacion=interpretacion,
    )

    try:
        _configurar_dlls_weasyprint_windows()

        # Import diferido para evitar fallo en Windows cuando faltan librerias GTK.
        from weasyprint import HTML

        HTML(string=html_content, base_url=ASSETS_DIR).write_pdf(ruta_pdf)
    except Exception as exc:
        print(f"WeasyPrint no disponible ({exc}). Intentando fallback xhtml2pdf.")

        if _generar_pdf_xhtml2pdf_fallback(html_content=html_content, ruta_pdf=ruta_pdf):
            print("PDF generado con fallback xhtml2pdf.")
            return

        print("xhtml2pdf no disponible/fallo. Usando fallback ReportLab.")
        _generar_pdf_reportlab_fallback(
            consulta=consulta,
            paciente=paciente,
            ruta_pdf=ruta_pdf,
            riesgo=riesgo,
            score=score,
            interpretacion=interpretacion,
        )