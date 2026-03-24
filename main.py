import threading
import os
import time
import customtkinter as ctk
from tkinter import filedialog, messagebox
import fitz  # PyMuPDF para el recorte preciso
from logic import BookProcessor
from area_selector import CropAreaSelector

class AppHibrida(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI Book Architect: Multi-Agent Workflow")
        self.geometry("1100x1050") # Corregido: 'x' en lugar de '('
        ctk.set_appearance_mode("dark")

        # Configuración y Keys
        config = BookProcessor.cargar_config()
        self.groq_key = ctk.StringVar(value=config.get("groq_key", ""))
        self.cerebras_key = ctk.StringVar(value=config.get("cerebras_key", ""))

        # Modo de Agente (Añadida opción No AI)
        self.modo_agente = ctk.StringVar(value="Hybrid (Groq + Cerebras)")

        # Variables de Salida
        self.gen_epub = ctk.BooleanVar(value=True)
        self.gen_md_clean = ctk.BooleanVar(value=True)
        self.gen_md_groq = ctk.BooleanVar(value=False)
        self.gen_md_raw = ctk.BooleanVar(value=False)

        self.crop_coords = None # Guardará [x0, y0, x1, y1]
        self.archivo_path = ""
        self.save_path = ""
        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text="🚀 AI Editorial Architect", font=("Arial", 24, "bold"), text_color="#60a5fa").pack(pady=15)

        # --- SECCIÓN LLAVES ---
        f_keys = ctk.CTkFrame(self)
        f_keys.pack(fill="x", padx=25, pady=5)
        ctk.CTkLabel(f_keys, text="Groq API Key:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        ctk.CTkEntry(f_keys, textvariable=self.groq_key, width=400, show="*").grid(row=0, column=1, pady=5)
        ctk.CTkLabel(f_keys, text="Cerebras API Key:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        ctk.CTkEntry(f_keys, textvariable=self.cerebras_key, width=400, show="*").grid(row=1, column=1, pady=5)

        # --- SELECTOR DE AGENTES (Incluye No AI) ---
        f_agentes = ctk.CTkFrame(self, fg_color="transparent")
        f_agentes.pack(fill="x", padx=25, pady=10)
        ctk.CTkLabel(f_agentes, text="AI Configuration:", font=("Arial", 12, "bold")).pack(side="left", padx=10)
        self.seg_button = ctk.CTkSegmentedButton(
            f_agentes,
            values=[
                "Solo Groq (Fast)",
                "Hybrid (Groq + Cerebras)",
                "Solo Ollama (Local)", # <-- Nueva opción
                "No AI (Direct PDF to MD)"
            ],
            variable=self.modo_agente,
            width=700 # Aumentamos un poco el ancho
        )
        self.seg_button.pack(side="left", padx=10)

        # --- SECCIÓN ARCHIVOS ---
        f_files = ctk.CTkFrame(self)
        f_files.pack(fill="x", padx=25, pady=10)
        ctk.CTkButton(f_files, text="📂 Load File", fg_color="#334155", command=self.click_archivo).pack(side="left", padx=10, pady=10)
        self.lbl_archivo = ctk.CTkLabel(f_files, text="No file selected", text_color="gray")
        self.lbl_archivo.pack(side="left", padx=5)
        ctk.CTkButton(f_files, text="💾 Destination", fg_color="#059669", command=self.click_destino).pack(side="right", padx=10, pady=10)
        ctk.CTkButton(f_files, text="🎯 Set Crop Area", fg_color="#7c3aed", command=self.open_crop_tool).pack(side="left", padx=10)

        # --- SECCIÓN CONFIGURACIÓN ---
        f_cfg = ctk.CTkFrame(self)
        f_cfg.pack(fill="x", padx=25, pady=5)
        self.combo_modo = ctk.CTkOptionMenu(f_cfg, values=["Full Book", "Test Mode (10 pages)", "Custom Range"], command=self.toggle_rango)
        self.combo_modo.pack(side="left", padx=10, pady=10)
        self.entry_range = ctk.CTkEntry(f_cfg, width=100, placeholder_text="e.g. 1-20", state="disabled")
        self.entry_range.pack(side="left", padx=5)
        ctk.CTkLabel(f_cfg, text="Start at Page:").pack(side="left", padx=(15, 2))
        self.entry_start_page = ctk.CTkEntry(f_cfg, width=45); self.entry_start_page.insert(0, "1")
        self.entry_start_page.pack(side="left", padx=5)
        ctk.CTkLabel(f_cfg, text="Batch:").pack(side="left", padx=(15, 2))
        self.entry_batch = ctk.CTkEntry(f_cfg, width=45); self.entry_batch.insert(0, "4")
        self.entry_batch.pack(side="left", padx=5)

        # --- SALIDAS Y LOGS ---
        f_out = ctk.CTkFrame(self)
        f_out.pack(fill="x", padx=25, pady=10)
        ctk.CTkCheckBox(f_out, text="Final EPUB", variable=self.gen_epub).pack(side="left", padx=10)
        ctk.CTkCheckBox(f_out, text="Clean MD", variable=self.gen_md_clean).pack(side="left", padx=10)
        ctk.CTkCheckBox(f_out, text="Groq MD", variable=self.gen_md_groq).pack(side="left", padx=10)

        self.txt_log = ctk.CTkTextbox(self, height=300, font=("Monospace", 11), fg_color="#0f172a")
        self.txt_log.pack(fill="both", padx=25, pady=10)
        self.progress = ctk.CTkProgressBar(self, height=12); self.progress.set(0)
        self.progress.pack(fill="x", padx=25, pady=5)

        self.btn_run = ctk.CTkButton(self, text="⚡ START PROCESSING", height=55, font=("Arial", 18, "bold"), command=self.lanzar_hilo)
        self.btn_run.pack(pady=20)

    def log(self, msg):
        self.txt_log.insert("end", f"> {msg}\n"); self.txt_log.see("end")

    def toggle_rango(self, choice):
        if choice == "Custom Range": self.entry_range.configure(state="normal")
        else: self.entry_range.configure(state="disabled")

    def click_archivo(self):
        p = filedialog.askopenfilename(filetypes=[("Books", "*.pdf *.md")])
        if p:
            self.archivo_path = p
            self.lbl_archivo.configure(text=os.path.basename(p), text_color="white")
            self.save_path = p.replace(os.path.splitext(p)[1], "_Processed.epub")

    def click_destino(self):
        p = filedialog.asksaveasfilename(defaultextension=".epub", filetypes=[("EPUB", "*.epub")])
        if p: self.save_path = p

    def lanzar_hilo(self):
        modo = self.modo_agente.get()
        if modo != "No AI (Direct PDF to MD)" and not self.groq_key.get():
            return messagebox.showerror("Error", "Groq Key missing")
        if not self.archivo_path:
            return messagebox.showerror("Error", "No file loaded")

        BookProcessor.guardar_config(self.groq_key.get(), self.cerebras_key.get())
        threading.Thread(target=self.ejecutar_pipeline, daemon=True).start()

    def ejecutar_pipeline(self):
        self.btn_run.configure(state="disabled")
        lista_raw, lista_groq, lista_clean = [], [], []
        temp_pdf = "temp_cropped_book.pdf" # Variable para el archivo temporal

        try:
            engine = BookProcessor(self.groq_key.get(), self.cerebras_key.get())
            ext = os.path.splitext(self.archivo_path)[1].lower()

            # Identificamos el modo seleccionado
            modo_actual = self.modo_agente.get()
            is_no_ai = (modo_actual == "No AI (Direct PDF to MD)")
            modo_hibrido = (modo_actual == "Hybrid (Groq + Cerebras)")
            is_ollama = (modo_actual == "Solo Ollama (Local)")

            ctx_anterior = ""
            batch = int(self.entry_batch.get())
            start_page = int(self.entry_start_page.get())

            if ext == ".pdf":
                # --- NUEVO: APLICAR EL CORTE FÍSICO SEGURO ---
                path_a_procesar = self.archivo_path

                if self.crop_coords:
                    self.log("🎯 Applying safe physical crop to PDF...")
                    doc = fitz.open(self.archivo_path)
                    user_rect = fitz.Rect(self.crop_coords).normalize()

                    for page in doc:
                        media_box = page.rect
                        # Intersección para evitar el error "CropBox not in MediaBox"
                        safe_rect = user_rect & media_box
                        if not safe_rect.is_empty:
                            page.set_cropbox(safe_rect)

                    doc.save(temp_pdf)
                    doc.close()
                    path_a_procesar = temp_pdf # El motor ahora usará el PDF sin bordes
                # ---------------------------------------------

                total = engine.obtener_paginas(path_a_procesar)
                inicio, fin = start_page, total

                modo_cfg = self.combo_modo.get()
                if modo_cfg == "Test Mode (10 pages)": fin = min(inicio + 9, total)
                elif modo_cfg == "Custom Range":
                    r = self.entry_range.get().split("-")
                    inicio, fin = int(r[0]), int(r[1])

                self.log(f"🚀 Starting PDF from page {inicio} to {fin}...")

                for i in range(inicio, fin + 1, batch):
                    b_f = min(i + batch - 1, fin)
                    self.log(f"📦 Batch {i}-{b_f}...")

                    # --- TU EXTRACCIÓN ORIGINAL (Usa el path recortado si existe) ---
                    res = engine.converter.convert(source=path_a_procesar, page_range=[i, b_f])
                    raw = res.document.export_to_markdown()
                    lista_raw.append(raw)

                    # --- LÓGICA DE PROCESAMIENTO ---
                    if is_no_ai:
                        # Si es "No AI", el resultado final es simplemente la extracción
                        final = raw
                    elif is_ollama:
                        self.log("  🦙 Ollama Local (Llama 3.2 1b)...")
                        final = engine.llamar_ollama(raw, ctx_anterior)
                    else:
                        # AGENTS (Con manejo de errores)
                        try:
                            self.log("  🤖 Groq Editor...")
                            editado = engine.llamar_editor_groq(raw, ctx_anterior)
                            lista_groq.append(editado)

                            if modo_hibrido:
                                self.log("  🧠 Cerebras Auditor...")
                                final = engine.llamar_auditor_cerebras(raw, editado)
                            else:
                                final = editado

                            time.sleep(2)
                        except Exception as api_err:
                            if "rate_limit_exceeded" in str(api_err).lower() or "429" in str(api_err):
                                self.log("⚠️ RATE LIMIT REACHED! Saving progress...")
                                self.emergency_save(lista_clean, lista_groq, lista_raw)
                                messagebox.showwarning("Rate Limit", f"Groq limit reached. Progress saved. Please resume from page {i}.")
                                return
                            raise api_err

                    lista_clean.append(final)
                    ctx_anterior = final
                    self.progress.set((b_f - inicio + 1) / (fin - inicio + 1))

            # --- GUARDADO FINAL ---
            self.save_outputs(lista_raw, lista_groq, lista_clean, engine)
            self.log("✅ PROCESS COMPLETED.")
            messagebox.showinfo("Done", "Process finished successfully.")

        except Exception as e:
            self.log(f"❌ Error: {e}")
            self.emergency_save(lista_clean, lista_groq, lista_raw)
        finally:
            # Limpiamos el PDF temporal si se creó
            if os.path.exists(temp_pdf):
                try:
                    os.remove(temp_pdf)
                except Exception:
                    pass
            # ESTO SOLUCIONA EL BLOQUEO: El botón siempre se reactiva al final
            self.btn_run.configure(state="normal")

    def open_crop_tool(self):
        if not self.archivo_path or not self.archivo_path.lower().endswith(".pdf"):
            return messagebox.showerror("Error", "Load a PDF file first")
        CropAreaSelector(self.archivo_path, self.save_crop_coords)

    def save_crop_coords(self, coords):
        self.crop_coords = coords
        self.log(f"🎯 Crop area set: {coords}")

    def emergency_save(self, clean, groq, raw):
        if not clean: return
        path = self.save_path.replace(".epub", "_PARTIAL.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# PARTIAL RESUME\n\n" + "\n\n---\n\n".join(clean))
        self.log(f"💾 Saved partial progress.")

    def save_outputs(self, raw, groq, clean, engine):
        if self.gen_md_raw.get() and raw:
            with open(self.save_path.replace(".epub", "_RAW.md"), "w", encoding="utf-8") as f:
                f.write("\n\n---\n\n".join(raw))
        if self.gen_md_groq.get() and groq:
            with open(self.save_path.replace(".epub", "_GROQ.md"), "w", encoding="utf-8") as f:
                f.write("\n\n---\n\n".join(groq))
        if self.gen_md_clean.get() and clean:
            with open(self.save_path.replace(".epub", "_CLEAN.md"), "w", encoding="utf-8") as f:
                f.write("\n\n---\n\n".join(clean))
        if self.gen_epub.get() and clean:
            engine.generar_epub(self.save_path, clean)

if __name__ == "__main__":
    app = AppHibrida()
    app.mainloop()
