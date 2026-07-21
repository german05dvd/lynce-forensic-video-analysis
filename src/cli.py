"""
Lynce Forensics - CLI (headless)

Batch-processes a folder of .avi videos without the desktop GUI.
Designed to run inside Docker or on a headless server.

Usage:
    python -m src.cli --input /path/to/videos --output /path/to/output [--config config.yaml]
"""
import argparse
import time
from pathlib import Path

from src.video_processor import VideoProcessor


def _progress_printer(current, total, name, phase):
    pct = int(current / total * 100) if total else 0
    print(f"\r[{name}] {phase}: {pct}%", end="", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Lynce Forensics - detección forense de personas en video (CLI)")
    parser.add_argument("--input", required=True, help="Carpeta con videos .avi de entrada")
    parser.add_argument("--output", required=True, help="Carpeta donde guardar clips y metadata")
    parser.add_argument("--config", default="config.yaml", help="Ruta al archivo de configuración")
    args = parser.parse_args()

    input_dir = Path(args.input)
    if not input_dir.is_dir():
        raise SystemExit(f"[ERROR] Carpeta de entrada no encontrada: {input_dir}")

    processor = VideoProcessor(config_path=args.config)
    processor.output_dir = Path(args.output)

    videos = sorted(input_dir.glob("*.avi"))
    if not videos:
        print(f"[INFO] No se encontraron videos .avi en {input_dir}")
        return

    print(f"=== Lynce Forensics — {len(videos)} video(s) encontrados ===")
    total_events = 0
    for idx, video_path in enumerate(videos, 1):
        print(f"\n[{idx}/{len(videos)}] Procesando {video_path.name}...")
        start = time.time()
        events = processor.process_video(str(video_path), progress_callback=_progress_printer)
        elapsed = time.time() - start
        total_events += len(events)
        print(f"\n  -> {len(events)} evento(s) detectado(s) en {elapsed:.1f}s")

    print(f"\n=== Completado: {total_events} evento(s) en total. Resultados en {args.output} ===")


if __name__ == "__main__":
    main()
