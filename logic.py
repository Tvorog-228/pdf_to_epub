import os
import json
import time
import fitz
import markdown
from ebooklib import epub
from groq import Groq
from openai import OpenAI
from docling.document_converter import DocumentConverter

# Configuración de sistema
CONFIG_DIR = os.path.expanduser("~/.config/groq_epub_editor")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

class BookProcessor:
    def __init__(self, groq_key, cerebras_key):
        # Cliente Groq para Edición
        self.groq_client = Groq(api_key=groq_key)

        # Cliente Cerebras para Auditoría (Compatible con OpenAI SDK)
        self.cerebras_client = OpenAI(
            base_url="https://api.cerebras.ai/v1",
            api_key=cerebras_key
        )
        self.converter = DocumentConverter()

    @staticmethod
    def cargar_config():
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except: return {}
        return {}

    @staticmethod
    def guardar_config(groq_key, cerebras_key):
        if not os.path.exists(CONFIG_DIR): os.makedirs(CONFIG_DIR)
        with open(CONFIG_FILE, "w") as f:
            json.dump({"groq_key": groq_key, "cerebras_key": cerebras_key}, f)

    def obtener_paginas(self, pdf_path):
        doc = fitz.open(pdf_path)
        count = doc.page_count
        doc.close()
        return count

    def leer_markdown_local(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def llamar_editor_groq(self, texto_nuevo, contexto_anterior):
        """AGENTE 1 (Groq): Limpieza y formato inicial."""
        buffer = contexto_anterior[-2000:] if contexto_anterior else "Inicio del libro."
        prompt = (
            "Eres un EDITOR EDITORIAL profesional. Tu misión es limpiar el texto de un libro.\n\n"
            "CONTEXTO ANTERIOR:\n"
            f"--- {buffer} ---\n\n"
            "INSTRUCCIONES:\n"
            "1. Elimina basura técnica (OCR, números de página, encabezados).\n"
            "2. NO RESUMAS. Mantén cada palabra del autor.\n"
            "3. Estructura con Markdown limpio (# Capítulos).\n\n"
            f"TEXTO A PROCESAR:\n{texto_nuevo}"
        )
        try:
            chat = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            return chat.choices[0].message.content
        except Exception as e:
            return f"Error en Groq: {str(e)}"

    def llamar_auditor_cerebras(self, md_raw, md_editado):
        """AGENTE 2 (Cerebras): Comparación y corrección de fidelidad."""
        prompt = (
            "Eres un AUDITOR DE INTEGRIDAD EDITORIAL. Tu misión es asegurar que el texto "
            "limpio contenga el 100% del mensaje del autor, eliminando ruidos técnicos.\n\n"

            "REGLAS DE ORO:\n"
            "1. FILTRO DE BASURA: Ignora por completo números de página, encabezados repetitivos, "
            "pies de página, marcas de agua digitales y artefactos de OCR del TEXTO ORIGINAL.\n"
            "2. FIDELIDAD NARRATIVA: Si detectas que el TEXTO PROCESADO omitió una frase, un párrafo "
            "o un diálogo que SÍ estaba en el ORIGINAL, recupéralo e insértalo.\n"
            "3. CORRECCIÓN DE ESTRUCTURA: Si los títulos (#) están mal colocados o mezclados "
            "respecto al orden lógico del ORIGINAL, reordénalos.\n"
            "4. NO AÑADAS: No inventes texto, no resumas y, sobre todo, NO devuelvas las etiquetas "
            "de 'Texto Original' o 'Texto Procesado'.\n\n"

            "FORMATO DE SALIDA:\n"
            "Devuelve ÚNICAMENTE el Markdown final corregido, listo para ser publicado.\n\n"

            f"--- TEXTO ORIGINAL (Referencia de contenido) ---\n{md_raw}\n\n"
            f"--- TEXTO PROCESADO (Borrador a corregir) ---\n{md_editado}"
        )
        try:
            chat = self.cerebras_client.chat.completions.create(
                model="llama3.1-8b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            return chat.choices[0].message.content
        except Exception as e:
            print(f"DEBUG Cerebras: {e}")
            return md_editado # Fallback al texto de Groq si falla

    def generar_epub(self, output_path, lista_limpios):
        book = epub.EpubBook()
        book.set_title(os.path.basename(output_path).replace(".epub", ""))
        book.set_language('es')
        full_md = "\n\n".join(lista_limpios)
        html_content = f"<html><body>{markdown.markdown(full_md)}</body></html>"
        cap = epub.EpubHtml(title="Contenido", file_name="libro.xhtml", content=html_content)
        book.add_item(cap)
        book.spine = ['nav', cap]
        epub.write_epub(output_path, book)
