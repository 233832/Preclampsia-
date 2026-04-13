import base64
import html
import os
from datetime import datetime

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer


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


def _generar_pdf_reportlab_fallback(consulta, paciente, ruta_pdf, riesgo, score, interpretacion):
    doc = SimpleDocTemplate(ruta_pdf)
    styles = getSampleStyleSheet()

    texto_interpretacion = html.escape(str(interpretacion or "Sin interpretación disponible")).replace("\n", "<br/>")
    fecha_consulta = _formatear_fecha(getattr(consulta, "fecha_hora_consulta", None))

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
        Paragraph(f"Edad: {consulta.edad_madre}", styles["Normal"]),
        Paragraph(f"Edad Gestacional: {consulta.edad_gestacional}", styles["Normal"]),
        Paragraph(f"Peso: {consulta.peso}", styles["Normal"]),
        Paragraph(f"Altura: {consulta.altura}", styles["Normal"]),
        Paragraph(f"IMC: {consulta.imc}", styles["Normal"]),
        Paragraph(f"Presión Sistólica: {consulta.presion_sistolica}", styles["Normal"]),
        Paragraph(f"Presión Diastólica: {consulta.presion_diastolica}", styles["Normal"]),
        Paragraph(f"Hipertensión previa: {_si_no(paciente.hipertension_previa)}", styles["Normal"]),
        Paragraph(f"Diabetes: {_si_no(paciente.diabetes)}", styles["Normal"]),
        Paragraph(
            f"Antecedentes familiares HTA: {_si_no(paciente.antecedentes_familia_hipertension)}",
            styles["Normal"],
        ),
        Spacer(1, 10),
        Paragraph(f"Riesgo: {riesgo}", styles["Heading3"]),
        Paragraph(f"Score: {score}", styles["Normal"]),
        Spacer(1, 10),
        Paragraph("Interpretación Clínica", styles["Heading3"]),
        Paragraph(texto_interpretacion, styles["Normal"]),
    ])

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

    color_riesgo = {
        "NINGUNO": "#95A5A6",
        "BAJO": "#00B894",
        "MEDIO": "#FDCB6E",
        "ALTO": "#D63031",
    }.get(str(riesgo).upper(), "#999")

    logo_data_url = _obtener_logo_data_url()
    fecha_consulta = _formatear_fecha(getattr(consulta, "fecha_hora_consulta", None))

    nombre_paciente = html.escape(str(getattr(paciente, "nombre", "N/A") or "N/A"))
    ciudad = html.escape(str(getattr(paciente, "ciudad", "N/A") or "N/A"))
    telefono = html.escape(str(getattr(paciente, "telefono", "N/A") or "N/A"))
    domicilio = html.escape(str(getattr(paciente, "domicilio", "N/A") or "N/A"))
    estado_civil = html.escape(str(getattr(paciente, "estado_civil", "N/A") or "N/A"))

    interpretacion_segura = html.escape(str(interpretacion or "Sin interpretación disponible")).replace("\n", "<br/>")

    antecedente_hta = _si_no(getattr(paciente, "hipertension_previa", False))
    antecedente_diabetes = _si_no(getattr(paciente, "diabetes", False))
    antecedente_familiar = _si_no(getattr(paciente, "antecedentes_familia_hipertension", False))

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
                font-family: 'Segoe UI';
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
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 22px;
                margin-bottom: 24px;
                padding: 16px 18px;
                border-radius: 18px;
                background: linear-gradient(125deg, #fff4fb 0%, #f8e6f1 55%, #f5e0ec 100%);
                border: 1px solid #efd4e3;
            }}

            .brand-logo {{
                width: 180px;
                height: 180px;
                object-fit: contain;
                display: block;
            }}

            .brand-fallback {{
                width: 180px;
                height: 180px;
                border-radius: 16px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: var(--brand-soft);
                color: var(--brand-dark);
                font-weight: 700;
            }}

            .title {{
                font-size: 30px;
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
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px 12px;
            }}

            .card {{
                background: var(--white);
                padding: 10px;
                border-radius: 12px;
                border: 1px solid #efdce8;
            }}

            .label {{
                font-size: 11px;
                color: #967d8d;
            }}

            .value {{
                font-weight: bold;
                margin-top: 2px;
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
                    gap: 12px;
                    margin-bottom: 10px;
                    padding: 10px 12px;
                    border-radius: 10px;
                }}

                .brand-logo,
                .brand-fallback {{
                    width: 96px;
                    height: 96px;
                }}

                .title {{
                    font-size: 22px;
                    margin-bottom: 2px;
                }}

                .subtitle {{
                    font-size: 11px;
                    margin-bottom: 2px;
                }}

                .meta {{
                    font-size: 10px;
                }}

                .section {{
                    margin-top: 8px;
                    padding: 10px;
                    border-radius: 10px;
                    break-inside: avoid;
                    page-break-inside: avoid;
                }}

                .section-title {{
                    font-size: 11px;
                    margin-bottom: 6px;
                }}

                .grid {{
                    gap: 6px 8px;
                }}

                .card {{
                    padding: 6px 8px;
                    border-radius: 8px;
                    break-inside: avoid;
                    page-break-inside: avoid;
                }}

                .label {{
                    font-size: 9px;
                }}

                .value {{
                    font-size: 15px;
                }}

                .riesgo {{
                    margin-top: 8px;
                    padding: 8px;
                    font-size: 13px;
                }}

                .interpretacion {{
                    padding: 8px;
                    font-size: 10px;
                }}

                .footer {{
                    margin-top: 8px;
                    font-size: 9px;
                }}
            }}
        </style>
    </head>

    <body>
        <div class="container">

            <div class="header">
                <div>
                    <div class="title">Reporte Clínico VitaPrenatal</div>
                    <div class="subtitle">Evaluación de riesgo de preeclampsia con datos reales de la consulta</div>
                    <div class="meta">Fecha de evaluación: {fecha_consulta}</div>
                </div>
                <div>
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
                        <div class="label">Hipertensión previa</div>
                        <div class="value">{antecedente_hta}</div>
                    </div>
                    <div class="card">
                        <div class="label">Diabetes</div>
                        <div class="value">{antecedente_diabetes}</div>
                    </div>
                    <div class="card">
                        <div class="label">Antecedentes familiares HTA</div>
                        <div class="value">{antecedente_familiar}</div>
                    </div>
                </div>
            </div>

            <div class="section">
                <div class="section-title">Resultado</div>

                <div class="card">
                    <div class="label">Score</div>
                    <div class="value">{score}</div>
                </div>

                <div class="riesgo" style="background:{color_riesgo}">
                    {riesgo}
                </div>
            </div>

            <div class="section">
                <div class="section-title">Interpretación Clínica</div>
                <div class="interpretacion">{interpretacion_segura}</div>
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