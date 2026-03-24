import os
import json
import time
import fitz
import markdown
from ebooklib import epub
from groq import Groq
from openai import OpenAI
from docling.document_converter import DocumentConverter
from openai import OpenAI

# Configuración de sistema
CONFIG_DIR = os.path.expanduser("~/.config/groq_epub_editor")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

class BookProcessor:
    def __init__(self, groq_key, cerebras_key):
        self.groq_client = Groq(api_key=groq_key)
        self.cerebras_client = OpenAI(
            base_url="https://api.cerebras.ai/v1",
            api_key=cerebras_key
        )
        # --- NUEVO: Cliente Ollama (Local) ---
        self.ollama_client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama" # Ollama no necesita key real, pero el SDK pide una
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
                "Eres un EDITOR EDITORIAL profesional experto en limpieza de manuscritos.\n\n"
                "CONTEXTO ANTERIOR (para mantener la coherencia):\n"
                f"--- {buffer} ---\n\n"
                "INSTRUCCIONES CRÍTICAS:\n"
                "1. El texto de entrada ya está en Markdown. Tu única misión es eliminar la 'basura' técnica: números de página, encabezados/pies de página que se repiten y artefactos de OCR (caracteres extraños o saltos de línea mal puestos).\n"
                "2. Respeta la estructura de capítulos: Los títulos ya vienen marcados con '##'. No los cambies ni añadidas niveles extra.\n"
                "3. PROHIBIDO RESUMIR O PARAFRASEAR. Debes mantener íntegra cada palabra del autor. No omitas frases ni secciones por parecer 'redundantes'.\n"
                "4. Devuelve exclusivamente el contenido limpio en Markdown, sin notas al lector ni introducciones.\n\n"
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

    def llamar_ollama(self, texto_nuevo, contexto_anterior):
        """Procesamiento local con Ollama usando Llama 3.2 1b."""
        buffer = contexto_anterior[-1500:] if contexto_anterior else "Inicio del libro."

        # Nota: Usamos un prompt algo más directo ya que el modelo 1B es pequeño
        prompt = (
            f"Eres un editor profesional. Limpia el siguiente texto de Markdown de basura "
            f"(números de página, encabezados, errores OCR). No resumas, mantén todo el texto original.\n\n"
            f"CONTEXTO PREVIO: {buffer}\n\n"
            f"TEXTO A LIMPIAR:\n{texto_nuevo}"
        )

        try:
            chat = self.ollama_client.chat.completions.create(
                model="llama3.2:1b", # Asegúrate de haber hecho 'ollama run llama3.2:1b'
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            return chat.choices[0].message.content
        except Exception as e:
            return f"Error en Ollama: {str(e)}"

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
