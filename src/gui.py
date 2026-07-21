import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from pathlib import Path
import time

from src.video_processor import VideoProcessor

class ForensicsGUI:
    """
    Interfaz gráfica moderna para Lynce Forensics v4.0 "Ghost".
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Lynce Forensics v4.0 - Ghost")
        self.root.geometry("900x650")
        self.root.configure(bg="#1e1e1e")
        
        # Variables
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(Path.home() / "Lynce_Output_Ghost"))
        self.is_running = False
        self.processor = VideoProcessor()
        
        self._build_ui()

    def _build_ui(self):
        # Marco principal
        main_frame = tk.Frame(self.root, bg="#1e1e1e", padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        # Barra superior
        tk.Label(main_frame, text="◉ Lynce Forensics Ghost v4.0", font=("Segoe UI", 22, "bold"), fg="#4ec9b0", bg="#1e1e1e").pack(anchor="w")
        tk.Label(main_frame, text="Análisis forense por Movimiento + IA | Optimizado para CPU", font=("Segoe UI", 10), fg="#8b949e", bg="#1e1e1e").pack(anchor="w", pady=(0, 20))
        
        # Tarjeta de configuración
        card = tk.Frame(main_frame, bg="#2d2d2d", bd=0, relief="flat", padx=15, pady=15)
        card.pack(fill="x", pady=10)
        
        # Selección de entrada
        tk.Label(card, text="Carpeta de Origen", fg="white", bg="#2d2d2d", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
        tk.Entry(card, textvariable=self.input_dir, width=50, bg="#3c3c3c", fg="white", insertbackground="white").grid(row=1, column=0, padx=(0, 10))
        tk.Button(card, text="Examinar", command=self._select_input, bg="#0e639c", fg="white", padx=10, cursor="hand2").grid(row=1, column=1)
        
        # Selección de salida
        tk.Label(card, text="Carpeta de Destino", fg="white", bg="#2d2d2d", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", pady=(10, 0))
        tk.Entry(card, textvariable=self.output_dir, width=50, bg="#3c3c3c", fg="white", insertbackground="white").grid(row=3, column=0, padx=(0, 10))
        tk.Button(card, text="Examinar", command=self._select_output, bg="#0e639c", fg="white", padx=10, cursor="hand2").grid(row=3, column=1)

        # Botones de acción
        btn_frame = tk.Frame(main_frame, bg="#1e1e1e")
        btn_frame.pack(fill="x", pady=(15, 5))
        self.btn_start = tk.Button(btn_frame, text="▶ Iniciar Análisis Forense", command=self._start_analysis, 
                                   bg="#4ec9b0", fg="black", font=("Segoe UI", 11, "bold"), padx=20, pady=8, cursor="hand2")
        self.btn_start.pack(side="left", padx=(0, 10))
        self.btn_stop = tk.Button(btn_frame, text="⏹ Detener", command=self._stop_analysis, state="disabled",
                                  bg="#d32f2f", fg="white", font=("Segoe UI", 11, "bold"), padx=20, pady=8, cursor="hand2")
        self.btn_stop.pack(side="left")
        
        tk.Button(btn_frame, text="📁 Abrir Resultados", command=self._open_output, bg="#3c3c3c", fg="white", padx=20, pady=8, cursor="hand2").pack(side="left", padx=(10,0))

        # Barras de progreso
        self.lbl_status = tk.Label(main_frame, text="Esperando...", fg="#8b949e", bg="#1e1e1e", font=("Segoe UI", 10))
        self.lbl_status.pack(anchor="w", pady=(15, 5))
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100, mode='determinate', length=400)
        self.progress_bar.pack(fill="x")
        self.lbl_detail = tk.Label(main_frame, text="", fg="#6a9955", bg="#1e1e1e", font=("Consolas", 9))
        self.lbl_detail.pack(anchor="w")

        # Log
        log_frame = tk.Frame(main_frame, bg="#252526", bd=1, relief="solid", padx=10, pady=10)
        log_frame.pack(fill="both", expand=True, pady=(15, 0))
        tk.Label(log_frame, text="Registro de Actividad", fg="white", bg="#252526", font=("Segoe UI", 10)).pack(anchor="w")
        self.log_text = tk.Text(log_frame, height=12, bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 9), wrap="word", state="disabled", bd=0)
        self.log_text.pack(fill="both", expand=True, pady=(5,0))

    def _select_input(self):
        path = filedialog.askdirectory()
        if path:
            self.input_dir.set(path)

    def _select_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_dir.set(path)

    def _start_analysis(self):
        if self.is_running:
            return
        input_path = self.input_dir.get()
        output_path = self.output_dir.get()
        if not Path(input_path).is_dir():
            messagebox.showerror("Error", "Seleccione una carpeta de origen válida.")
            return
        
        self.is_running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self._log("=== INICIO DEL ANÁLISIS FORENSE ===")
        
        videos = list(Path(input_path).glob("*.avi"))
        self._log(f"{len(videos)} videos encontrados en {input_path}")
        
        thread = threading.Thread(target=self._process_thread, args=(videos, output_path))
        thread.start()

    def _process_thread(self, videos, output_path):
        total = len(videos)
        for idx, video_path in enumerate(videos, 1):
            if not self.is_running:
                break
            self._update_progress(idx / total * 100, f"Procesando {video_path.name} ({idx}/{total})")
            self._log(f"⏳ Analizando {video_path.name}...")
            start_t = time.time()
            events = self.processor.process_video(str(video_path), progress_callback=self._on_progress)
            elapsed = time.time() - start_t
            self._log(f"✅ {len(events)} eventos detectados en {elapsed:.1f}s")
        self._finish()

    def _on_progress(self, current_frame, total_frames, video_name, phase):
        pct = int(current_frame / total_frames * 100) if total_frames > 0 else 0
        self._update_progress(pct, f"{phase}: {video_name}")

    def _update_progress(self, value, text):
        self.root.after(0, lambda: self.progress_var.set(value))
        self.root.after(0, lambda: self.lbl_detail.config(text=text))

    def _stop_analysis(self):
        self.is_running = False
        self.btn_stop.config(state="disabled")

    def _finish(self):
        self.is_running = False
        self.root.after(0, lambda: self.btn_start.config(state="normal"))
        self.root.after(0, lambda: self.btn_stop.config(state="disabled"))
        self.root.after(0, lambda: self._log("=== ANÁLISIS COMPLETADO ==="))

    def _open_output(self):
        import webbrowser
        webbrowser.open(f"file://{Path(self.output_dir.get()).absolute()}")

    def _log(self, message):
        self.root.after(0, lambda: self._append_log(message))

    def _append_log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"{time.strftime('%H:%M:%S')} {message}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")