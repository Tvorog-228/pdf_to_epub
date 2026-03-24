import threading
import os
import time
import customtkinter as ctk
from tkinter import filedialog, messagebox
from logic import BookProcessor

class AppHibrida(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI Book Architect: Multi-Agent Workflow")
        self.geometry("1100(1050") # Slightly taller for new fields
        ctk.set_appearance_mode("dark")

        # Configuration and Keys
        config = BookProcessor.cargar_config()
        self.groq_key = ctk.StringVar(value=config.get("groq_key", ""))
        self.cerebras_key = ctk.StringVar(value=config.get("cerebras_key", ""))

        # Agent Mode
        self.modo_agente = ctk.StringVar(value="Hybrid (Groq + Cerebras)")

        # Output Variables
        self.gen_epub = ctk.BooleanVar(value=True)
        self.gen_md_clean = ctk.BooleanVar(value=True)
        self.gen_md_groq = ctk.BooleanVar(value=False)
        self.gen_md_raw = ctk.BooleanVar(value=False)

        self.archivo_path = ""
        self.save_path = ""
        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text="🚀 AI Editorial Architect", font=("Arial", 24, "bold"), text_color="#60a5fa").pack(pady=15)

        # --- KEYS SECTION ---
        f_keys = ctk.CTkFrame(self)
        f_keys.pack(fill="x", padx=25, pady=5)
        ctk.CTkLabel(f_keys, text="Groq API Key:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        ctk.CTkEntry(f_keys, textvariable=self.groq_key, width=400, show="*").grid(row=0, column=1, pady=5)
        ctk.CTkLabel(f_keys, text="Cerebras API Key:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        ctk.CTkEntry(f_keys, textvariable=self.cerebras_key, width=400, show="*").grid(row=1, column=1, pady=5)

        # --- AGENT SELECTOR ---
        f_agentes = ctk.CTkFrame(self, fg_color="transparent")
        f_agentes.pack(fill="x", padx=25, pady=10)
        ctk.CTkLabel(f_agentes, text="AI Configuration:", font=("Arial", 12, "bold")).pack(side="left", padx=10)
        self.seg_button = ctk.CTkSegmentedButton(f_agentes,
                                                values=["Solo Groq (Fast)", "Hybrid (Groq + Cerebras)"],
                                                variable=self.modo_agente, width=450)
        self.seg_button.pack(side="left", padx=10)

        # --- FILES SECTION ---
        f_files = ctk.CTkFrame(self)
        f_files.pack(fill="x", padx=25, pady=10)
        ctk.CTkButton(f_files, text="📂 Load File", fg_color="#334155", command=self.click_archivo).pack(side="left", padx=10, pady=10)
        self.lbl_archivo = ctk.CTkLabel(f_files, text="No file selected", text_color="gray")
        self.lbl_archivo.pack(side="left", padx=5)
        ctk.CTkButton(f_files, text="💾 Destination", fg_color="#059669", command=self.click_destino).pack(side="right", padx=10, pady=10)

        # --- RESUME & BATCH SECTION ---
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

        # --- OUTPUTS & LOGS (Same as before but translated) ---
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
        if not self.groq_key.get(): return messagebox.showerror("Error", "Groq Key missing")
        if not self.archivo_path: return messagebox.showerror("Error", "No file loaded")
        BookProcessor.guardar_config(self.groq_key.get(), self.cerebras_key.get())
        threading.Thread(target=self.ejecutar_pipeline, daemon=True).start()

    def ejecutar_pipeline(self):
        self.btn_run.configure(state="disabled")
        lista_raw, lista_groq, lista_clean = [], [], []
        try:
            engine = BookProcessor(self.groq_key.get(), self.cerebras_key.get())
            ext = os.path.splitext(self.archivo_path)[1].lower()
            modo_hibrido = (self.modo_agente.get() == "Hybrid (Groq + Cerebras)")

            ctx_anterior = ""
            batch = int(self.entry_batch.get())
            start_page = int(self.entry_start_page.get())

            if ext == ".pdf":
                total = engine.obtener_paginas(self.archivo_path)
                inicio, fin = start_page, total

                modo = self.combo_modo.get()
                if modo == "Test Mode (10 pages)": fin = min(inicio + 9, total)
                elif modo == "Custom Range":
                    r = self.entry_range.get().split("-")
                    inicio, fin = int(r[0]), int(r[1])

                self.log(f"🚀 Starting PDF from page {inicio} to {fin}...")
                for i in range(inicio, fin + 1, batch):
                    b_f = min(i + batch - 1, fin)
                    self.log(f"📦 Batch {i}-{b_f}...")

                    res = engine.converter.convert(source=self.archivo_path, page_range=[i, b_f])
                    raw = res.document.export_to_markdown()
                    lista_raw.append(raw)

                    # AGENTS (With Error Handling)
                    try:
                        editado = engine.llamar_editor_groq(raw, ctx_anterior)
                        lista_groq.append(editado)

                        if modo_hibrido:
                            final = engine.llamar_auditor_cerebras(raw, editado)
                        else:
                            final = editado

                        lista_clean.append(final)
                        ctx_anterior = final
                        self.progress.set((b_f - inicio + 1) / (fin - inicio + 1))
                        time.sleep(2)

                    except Exception as api_err:
                        if "rate_limit_exceeded" in str(api_err).lower() or "429" in str(api_err):
                            self.log("⚠️ RATE LIMIT REACHED! Saving progress and stopping...")
                            self.emergency_save(lista_clean, lista_groq, lista_raw)
                            messagebox.showwarning("Rate Limit", f"Groq limit reached. Progress saved. Please resume from page {i} in a few minutes.")
                            return # Stop the thread
                        else:
                            raise api_err # Re-raise other errors

            # --- NORMAL COMPLETION SAVING ---
            self.save_outputs(lista_raw, lista_groq, lista_clean, engine)
            self.log("✅ PROCESS COMPLETED.")
            messagebox.showinfo("Done", "Process finished successfully.")

        except Exception as e:
            self.log(f"❌ Error: {e}")
            self.emergency_save(lista_clean, lista_groq, lista_raw)
        finally:
            self.btn_run.configure(state="normal")

    def emergency_save(self, clean, groq, raw):
        """Saves current progress to a special file if the app crashes or hits a limit."""
        if not clean: return
        path = self.save_path.replace(".epub", "_PARTIAL_RESUME.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# PARTIAL PROGRESS (RESUME LATER)\n\n" + "\n\n---\n\n".join(clean))
        self.log(f"💾 Emergency backup saved to: {os.path.basename(path)}")

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
    app = AppHibrida(); app.mainloop()
