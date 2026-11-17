"""Time the configured STT pipeline with a selected CPU or GPU profile."""
import argparse
import json
from pathlib import Path
import statistics
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.services.stt import get_model, transcribe_audio
from backend.app.settings import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--compute-type")
    parser.add_argument("--cpu-threads", type=int, default=0)
    parser.add_argument("--audio", type=Path, action="append", required=True)
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.repeat < 1 or args.cpu_threads < 0:
        parser.error("repeat must be positive and cpu-threads must be non-negative")

    # These overrides belong only to this benchmark process; .env is untouched.
    settings = get_settings()
    settings.stt_device = args.device
    settings.stt_compute_type = args.compute_type or ("int8_float16" if args.device == "cuda" else "int8")
    settings.stt_cpu_threads = args.cpu_threads
    started = perf_counter()
    model = get_model()
    report = {
        "device": model.model.device,
        "compute_type": model.model.compute_type,
        "cpu_threads": args.cpu_threads,
        "load_seconds": round(perf_counter() - started, 3),
        "samples": [],
    }
    print(json.dumps({key: value for key, value in report.items() if key != "samples"}), flush=True)
    for path in args.audio:
        audio_bytes = path.read_bytes()
        timings, texts = [], []
        for _ in range(args.repeat):
            started = perf_counter()
            texts.append(transcribe_audio(audio_bytes, path.suffix))
            timings.append(round(perf_counter() - started, 3))
        result = {"file": str(path), "texts": texts, "seconds": timings,
                  "median_seconds": round(statistics.median(timings), 3)}
        report["samples"].append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
