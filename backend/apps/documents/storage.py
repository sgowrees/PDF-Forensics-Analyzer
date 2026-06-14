from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage

BASELINES_DIR = Path(settings.BASE_DIR) / "templates" / "baselines" / "documents"
BASELINES_DIR.mkdir(parents=True, exist_ok=True)

baseline_storage = FileSystemStorage(
    location=BASELINES_DIR,
    base_url=None,
)
