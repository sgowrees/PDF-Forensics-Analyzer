from pathlib import Path

from django.conf import settings

from apps.documents.models import TemplateDocument


def sync_filesystem_baselines() -> int:
    """Register on-disk baseline PDFs that are not yet tracked in the database."""
    baselines_dir = Path(settings.BASE_DIR) / "templates" / "baselines" / "documents"
    if not baselines_dir.exists():
        return 0

    tracked_names = set(TemplateDocument.objects.values_list("name", flat=True))
    created = 0

    for pdf_path in sorted(baselines_dir.glob("*.pdf")):
        if pdf_path.name in tracked_names:
            continue

        template = TemplateDocument(name=pdf_path.name)
        template.file.name = pdf_path.name
        template.save()
        created += 1

    return created
