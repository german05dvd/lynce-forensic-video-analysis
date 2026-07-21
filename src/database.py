import csv, json
from pathlib import Path
from typing import List, Dict
from datetime import datetime

class MetadataStore:
    # Clase de utilidad para guardar resultados en CSV/JSON similar a la versión anterior pero adaptada.
    def save_events(self, events: List[Dict], output_dir: str):
        meta_dir = Path(output_dir) / "metadata"
        meta_dir.mkdir(parents=True, exist_ok=True)
        
        csv_path = meta_dir / "events.csv"
        with open(csv_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["video", "fecha", "hora_inicio", "hora_fin", "duracion", "clip_path"])
            if csv_path.stat().st_size == 0:
                writer.writeheader()
            for ev in events:
                writer.writerow({
                    "video": ev['video_name'],
                    "fecha": ev['date'],
                    "hora_inicio": ev['time_start'],
                    "hora_fin": ev['time_end'],
                    "duracion": f"{ev['end_time'] - ev['start_time']:.2f}s",
                    "clip_path": ev.get('clip_path', '')
                })