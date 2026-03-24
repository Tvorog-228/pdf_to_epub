import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import fitz  # PyMuPDF
from tkinter import messagebox

class CropAreaSelector(ctk.CTkToplevel):
    def __init__(self, pdf_path, callback):
        super().__init__()
        self.title("Selector de Área de Texto (Cuerpo del Libro)")
        self.geometry("1000x900")

        self.pdf_path = pdf_path
        self.callback = callback
        self.doc = fitz.open(pdf_path)
        self.current_page = 0

        # --- Configuración de UI ---
        self.setup_nav_bar()

        # Contenedor para el Canvas y Scrollbars
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True, padx=10, pady=10)

        # Scrollbars (Importante para no perder bordes)
        self.v_scroll = tk.Scrollbar(self.container, orient="vertical")
        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll = tk.Scrollbar(self.container, orient="horizontal")
        self.h_scroll.pack(side="bottom", fill="x")

        self.canvas = tk.Canvas(
            self.container,
            bg="#333333",
            xscrollcommand=self.h_scroll.set,
            yscrollcommand=self.v_scroll.set,
            highlightthickness=0
        )
        self.canvas.pack(side="left", fill="both", expand=True)

        self.v_scroll.config(command=self.canvas.yview)
        self.h_scroll.config(command=self.canvas.xview)

        # --- Botones de Acción ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        ctk.CTkButton(btn_frame, text="Cancelar", fg_color="#991b1b", command=self.destroy).pack(side="left", padx=50)
        ctk.CTkButton(btn_frame, text="✅ Confirmar Área Seleccionada", fg_color="#166534", command=self.confirm).pack(side="right", padx=50)

        # Variables de dibujo y geometría
        self.rect = None
        self.start_x = self.start_y = 0
        self.scale_factor = 1.0
        # IMPORTANTE: Inicializar los offsets
        self.offset_x = 0
        self.offset_y = 0

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_move)

        self.render_page()

    def setup_nav_bar(self):
        nav_frame = ctk.CTkFrame(self)
        nav_frame.pack(fill="x", pady=5)

        ctk.CTkButton(nav_frame, text="< Ant.", width=80, command=lambda: self.change_page(-1)).pack(side="left", padx=20)
        self.lbl_page = ctk.CTkLabel(nav_frame, text="")
        self.lbl_page.pack(side="left", expand=True)
        ctk.CTkButton(nav_frame, text="Sig. >", width=80, command=lambda: self.change_page(1)).pack(side="left", padx=20)

    def render_page(self):
        page = self.doc[self.current_page]

        self.update_idletasks()
        # Prevenir errores de división si la ventana aún no está lista
        container_w = max(100, self.container.winfo_width() - 20)
        container_h = max(100, self.container.winfo_height() - 20)

        page_rect = page.rect
        page_w = page_rect.width
        page_h = page_rect.height

        scale_w = container_w / page_w
        scale_h = container_h / page_h

        self.scale_factor = min(scale_w, scale_h)

        mat = fitz.Matrix(self.scale_factor, self.scale_factor)
        pix = page.get_pixmap(matrix=mat)

        self.img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.tk_img = ImageTk.PhotoImage(self.img)

        self.canvas.delete("all")

        # IMPORTANTE: Usar self.offset para poder usarlo en confirm()
        self.offset_x = (container_w - pix.width) // 2
        self.offset_y = (container_h - pix.height) // 2

        self.canvas.create_image(self.offset_x, self.offset_y, image=self.tk_img, anchor="nw")

        self.canvas.config(scrollregion=(0, 0, container_w, container_h))

        self.lbl_page.configure(text=f"Página {self.current_page + 1} de {len(self.doc)}")

    def change_page(self, delta):
        new_p = self.current_page + delta
        if 0 <= new_p < len(self.doc):
            self.current_page = new_p
            self.render_page()

    def on_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)

        if self.rect: self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x+1, self.start_y+1, outline='cyan', width=2)

    def on_move(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def confirm(self):
        coords = self.canvas.coords(self.rect)
        if not coords:
            return messagebox.showwarning("Atención", "Dibuja un rectángulo primero")

        # EL ARREGLO ESTÁ AQUÍ:
        # 1. Restamos el margen gris (offset) para que (0,0) sea la esquina de la página real
        # 2. Dividimos por la escala para convertir de píxeles a puntos (pts) del PDF
        x0 = (coords[0] - self.offset_x) / self.scale_factor
        y0 = (coords[1] - self.offset_y) / self.scale_factor
        x1 = (coords[2] - self.offset_x) / self.scale_factor
        y1 = (coords[3] - self.offset_y) / self.scale_factor

        pdf_coords = [x0, y0, x1, y1]
        self.callback(pdf_coords)
        self.destroy()
