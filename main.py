import threading
import os
import time
import customtkinter as ctk
from tkinter import filedialog, messagebox
from logic import BookProcessor

class AppHibrida(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI Book Architect: Groq + Cerebras Pro")
        self.geometry("1000x980")
        ctk.set_appearance_mode("dark")

        # Configuración y Keys
        config = BookProcessor.cargar_config()
        self.groq_key = ctk.StringVar(value=config.get("groq_key", ""))
        self.cerebras_key = ctk.StringVar(value=config.get("cerebras_key", ""))

        # Variables de Salida (Checkboxes)
        self.gen_epub = ctk.BooleanVar(value=True)
        self.gen_md_clean = ctk.BooleanVar(value=True)
        self.gen_md_raw = ctk.BooleanVar(value=False)

        self.archivo_path = ""
        self.save_path = ""
        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text="🚀 Híbrido: Groq (Editor) + Cerebras (Auditor)", font=("Arial", 24, "bold"), text_color="#60a5fa").pack(pady=15)

        # --- SECCIÓN LLAVES ---
        f_keys = ctk.CTkFrame(self)
        f_keys.pack(fill="x", padx=25, pady=5)

        ctk.CTkLabel(f_keys, text="Groq API Key:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        ctk.CTkEntry(f_keys, textvariable=self.groq_key, width=400, show="*").grid(row=0, column=1, pady=5)

        ctk.CTkLabel(f_keys, text="Cerebras API Key:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        ctk.CTkEntry(f_keys, textvariable=self.cerebras_key, width=400, show="*").grid(row=1, column=1, pady=5)

        # --- SECCIÓN ARCHIVOS ---
        f_files = ctk.CTkFrame(self)
        f_files.pack(fill="x", padx=25, pady=10)
        ctk.CTkButton(f_files, text="📂 Cargar PDF o MD", fg_color="#334155", command=self.click_archivo).pack(side="left", padx=10, pady=10)
        self.lbl_archivo = ctk.CTkLabel(f_files, text="Ningún archivo", text_color="gray")
        self.lbl_archivo.pack(side="left", padx=5)
        ctk.CTkButton(f_files, text="💾 Destino", fg_color="#059669", command=self.click_destino).pack(side="right", padx=10, pady=10)

        # --- SECCIÓN CONFIGURACIÓN (Rango y Lote) ---
        f_cfg = ctk.CTkFrame(self)
        f_cfg.pack(fill="x", padx=25, pady=5)

        self.combo_modo = ctk.CTkOptionMenu(f_cfg, values=["Libro Completo", "Modo Test (10 pág)", "Rango Personalizado"], command=self.toggle_rango)
        self.combo_modo.pack(side="left", padx=10, pady=10)

        self.entry_range = ctk.CTkEntry(f_cfg, width=120, placeholder_text="Ej: 1-20", state="disabled")
        self.entry_range.pack(side="left", padx=5)

        ctk.CTkLabel(f_cfg, text="Lote:").pack(side="left", padx=(15, 2))
        self.entry_batch = ctk.CTkEntry(f_cfg, width=45); self.entry_batch.insert(0, "4")
        self.entry_batch.pack(side="left", padx=5)

        # --- SECCIÓN SALIDAS (Checkboxes) ---
        f_out = ctk.CTkFrame(self)
        f_out.pack(fill="x", padx=25, pady=10)
        ctk.CTkLabel(f_out, text="Generar:", font=("Arial", 12, "bold")).pack(side="left", padx=15)
        ctk.CTkCheckBox(f_out, text="EPUB Final", variable=self.gen_epub).pack(side="left", padx=10)
        ctk.CTkCheckBox(f_out, text="Markdown Limpio", variable=self.gen_md_clean).pack(side="left", padx=10)
        ctk.CTkCheckBox(f_out, text="Markdown RAW", variable=self.gen_md_raw).pack(side="left", padx=10)

        # --- LOGS Y PROGRESO ---
        self.txt_log = ctk.CTkTextbox(self, height=350, font=("Monospace", 11), fg_color="#0f172a")
        self.txt_log.pack(fill="both", padx=25, pady=10)
        self.progress = ctk.CTkProgressBar(self, height=12); self.progress.set(0)
        self.progress.pack(fill="x", padx=25, pady=5)

        self.btn_run = ctk.CTkButton(self, text="⚡ INICIAR PROCESO HÍBRIDO", height=55, font=("Arial", 18, "bold"), command=self.lanzar_hilo)
        self.btn_run.pack(pady=20)

    def log(self, msg):
        self.txt_log.insert("end", f"> {msg}\n"); self.txt_log.see("end")

    def toggle_rango(self, choice):
        if choice == "Rango Personalizado": self.entry_range.configure(state="normal")
        else: self.entry_range.configure(state="disabled")

    def click_archivo(self):
        p = filedialog.askopenfilename(filetypes=[("Libros", "*.pdf *.md")])
        if p:
            self.archivo_path = p
            ext = os.path.splitext(p)[1].upper()
            self.lbl_archivo.configure(text=f"[{ext}] {os.path.basename(p)}", text_color="white")
            self.save_path = p.replace(os.path.splitext(p)[1], "_Procesado.epub")

    def click_destino(self):
        p = filedialog.asksaveasfilename(defaultextension=".epub", filetypes=[("EPUB", "*.epub")])
        if p: self.save_path = p

    def lanzar_hilo(self):
        if not self.groq_key.get() or not self.cerebras_key.get():
            return messagebox.showerror("Error", "Faltan las llaves API")
        if not self.archivo_path:
            return messagebox.showerror("Error", "No has cargado ningún archivo")

        BookProcessor.guardar_config(self.groq_key.get(), self.cerebras_key.get())
        threading.Thread(target=self.ejecutar_pipeline, daemon=True).start()

    def ejecutar_pipeline(self):
        self.btn_run.configure(state="disabled")
        try:
            engine = BookProcessor(self.groq_key.get(), self.cerebras_key.get())
            ext = os.path.splitext(self.archivo_path)[1].lower()

            lista_raw, lista_clean = [], []
            ctx_anterior = ""
            batch = int(self.entry_batch.get())

            if ext == ".pdf":
                total = engine.obtener_paginas(self.archivo_path)
                inicio, fin = 1, total

                # Lógica de Rango
                modo = self.combo_modo.get()
                if modo == "Modo Test (10 pág)": fin = min(10, total)
                elif modo == "Rango Personalizado":
                    r = self.entry_range.get().split("-")
                    inicio, fin = int(r[0]), int(r[1])

                self.log(f"🚀 Iniciando PDF: pág {inicio} a {fin}")
                for i in range(inicio, fin + 1, batch):
                    b_f = min(i + batch - 1, fin)
                    self.log(f"📦 Procesando {i}-{b_f}...")

                    res = engine.converter.convert(source=self.archivo_path, page_range=[i, b_f])
                    raw = res.document.export_to_markdown()
                    lista_raw.append(raw)

                    editado = engine.llamar_editor_groq(raw, ctx_anterior)
                    final = engine.llamar_auditor_cerebras(raw, editado)

                    lista_clean.append(final)
                    ctx_anterior = final
                    self.progress.set((b_f - inicio + 1) / (fin - inicio + 1))
                    time.sleep(5)

            else:
                self.log("🚀 Procesando Markdown...")
                texto = engine.leer_markdown_local(self.archivo_path)
                chunk_size = 7000
                chunks = [texto[i:i+chunk_size] for i in range(0, len(texto), chunk_size)]
                for idx, chunk in enumerate(chunks):
                    self.log(f"📦 Bloque {idx+1}/{len(chunks)}")
                    lista_raw.append(chunk)
                    editado = engine.llamar_editor_groq(chunk, ctx_anterior)
                    final = engine.llamar_auditor_cerebras(chunk, editado)
                    lista_clean.append(final)
                    ctx_anterior = final
                    self.progress.set((idx + 1) / len(chunks))
                    time.sleep(5)

            # --- GESTIÓN DE SALIDAS SEGÚN CHECKBOXES ---
            if self.gen_md_raw.get():
                path = self.save_path.replace(".epub", "_RAW.md")
                with open(path, "w", encoding="utf-8") as f:
                    f.write("# RAW SUCIO\n\n" + "\n\n---\n\n".join(lista_raw))
                self.log("📄 MD RAW guardado.")

            if self.gen_md_clean.get():
                path = self.save_path.replace(".epub", "_LIMPIO.md")
                with open(path, "w", encoding="utf-8") as f:
                    f.write("# LIMPIO FINAL\n\n" + "\n\n---\n\n".join(lista_clean))
                self.log("📄 MD Limpio guardado.")

            if self.gen_epub.get():
                engine.generar_epub(self.save_path, lista_clean)
                self.log("📘 EPUB generado.")

            self.log("✅ PROCESO COMPLETADO.")
            messagebox.showinfo("Hecho", "Proceso finalizado con éxito.")

        except Exception as e: self.log(f"❌ Error: {e}")
        finally: self.btn_run.configure(state="normal")

if __name__ == "__main__":
    app = AppHibrida(); app.mainloop()
