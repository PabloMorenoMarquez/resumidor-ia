from flask import Flask, request, render_template, send_file
import openai, fitz, markdown2, requests
import os
from fpdf import FPDF

openai.api_key = os.environ.get("OPENAI_API_KEY")

app = Flask(__name__)

def extraer_texto_pdf(ruta):
    texto = ""
    try:
        doc = fitz.open(ruta)
        for page in doc:
            texto += page.get_text()
    except Exception:
        pass
    return texto.strip()

def generar_resumen(texto):
    texto = texto.strip()[:7000]
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente experto en resumir documentos educativos. "
                        "Resume solo lo útil para estudiar: conceptos clave, definiciones, tipos de diagramas, ejemplos. "
                        "Indica en qué fase del desarrollo se usa cada tipo de diagrama UML y da ejemplos reales. "
                        "Devuelve el resumen en español y en formato Markdown bien estructurado."
                    )
                },
                {
                    "role": "user",
                    "content": texto
                }
            ],
            max_tokens=1000,
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

def markdown_a_pdf(md_texto):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    for linea in md_texto.split("\n"):
        linea = linea.strip()
        if not linea:
            pdf.ln(5)
            continue

        # Estilos para títulos Markdown
        if linea.startswith("### "):
            pdf.set_font("Helvetica", 'B', 13)
            pdf.multi_cell(0, 10, linea[4:])
            pdf.set_font("Helvetica", size=12)
        elif linea.startswith("## "):
            pdf.set_font("Helvetica", 'B', 15)
            pdf.multi_cell(0, 10, linea[3:])
            pdf.set_font("Helvetica", size=12)
        elif linea.startswith("# "):
            pdf.set_font("Helvetica", 'B', 17)
            pdf.multi_cell(0, 12, linea[2:])
            pdf.set_font("Helvetica", size=12)
        elif linea.startswith("- "):
            pdf.cell(5)
            pdf.multi_cell(0, 10, f"- {linea[2:]}")
        else:
            pdf.multi_cell(0, 10, linea)

    ruta = "/tmp/resumen.pdf"
    pdf.output(ruta)
    return ruta


@app.route("/", methods=["GET", "POST"])
def index():
    resumen = None
    resumen_html = None
    if request.method == "POST":
        archivo = request.files.get("pdf")
        texto_manual = request.form.get("texto", "").strip()
        contenido = ""
        if archivo and archivo.filename.endswith(".pdf"):
            ruta = f"/tmp/{archivo.filename}"
            archivo.save(ruta)
            contenido = extraer_texto_pdf(ruta)
        elif texto_manual:
            contenido = texto_manual

        if contenido:
            resumen = generar_resumen(contenido)
            resumen_html = markdown2.markdown(resumen)

    return render_template("index.html", resumen=resumen, resumen_html=resumen_html)

@app.route("/descargar", methods=["POST"])
def descargar():
    resumen = request.form.get("resumen", "")
    ruta = markdown_a_pdf(resumen)
    return send_file(ruta, as_attachment=True)

@app.route("/subscribe", methods=["POST"])
def subscribe():
    email = request.form.get("email", "").strip().lower()
    if "@" in email:
        with open("subscribers.csv", "a") as f:
            f.write(email + "\n")
	# 🔁 Enviar a Make (webhook)
        try:
            requests.post("https://hook.eu2.make.com/sz2liic6b8gkg8ljv21ix6iih92zsg6o", json={"email": email})
        except Exception as e:
            print(f"Error al enviar a Make: {e}")
    return "<script>alert('¡Gracias por suscribirte!'); window.location.href='/'</script>"

@app.route("/feedback", methods=["POST"])
def feedback():
    comentario = request.form.get("comentario", "").strip()
    if comentario:
        with open("feedback.csv", "a") as f:
            f.write(comentario + "\n")
    return "<script>alert('¡Gracias por tu feedback!'); window.location.href='/'</script>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
