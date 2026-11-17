"""Download pinned Thai Whisper weights and tokenizer into the project."""
from pathlib import Path

from huggingface_hub import hf_hub_download, snapshot_download

MODEL_ID = "Thaweewat/whisper-th-medium-ct2"
MODEL_REVISION = "928ce1ae8acf6c14bfa0afc0ec5fe308a07f0f1a"
TOKENIZER_ID = "biodatlab/whisper-th-medium-combined"
TOKENIZER_REVISION = "eebf84255cc7f242a504f64ec09ec33d32903fe1"
PROJECT_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = PROJECT_DIR / ".runtime" / "models" / "whisper-th-medium-ct2"


def main() -> None:
    print(f"Downloading Thai speech model to {MODEL_DIR}", flush=True)
    snapshot_download(
        repo_id=MODEL_ID,
        revision=MODEL_REVISION,
        local_dir=str(MODEL_DIR),
        allow_patterns=["config.json", "model.bin", "vocabulary.json"],
    )
    # The converted weights omit the tokenizer; use the fine-tuner's tokenizer.
    hf_hub_download(
        repo_id=TOKENIZER_ID,
        revision=TOKENIZER_REVISION,
        filename="tokenizer.json",
        local_dir=str(MODEL_DIR),
    )
    print("Ready. Set these values in backend/.env, then restart the API:")
    print("STT_MODEL=.runtime/models/whisper-th-medium-ct2\nSTT_LANGUAGE=th")


if __name__ == "__main__":
    main()
