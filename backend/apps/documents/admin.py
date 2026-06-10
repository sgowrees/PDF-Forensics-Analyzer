from django.contrib import admin

from .models import AnalysisResult, Document


class AnalysisResultInline(admin.StackedInline):
    model = AnalysisResult
    extra = 0
    readonly_fields = [
        "score",
        "risk",
        "baseline_available",
        "reasons",
        "score_breakdown",
        "classification_confidence",
        "created_at",
    ]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        "original_filename",
        "doc_type",
        "issuer",
        "status",
        "created_at",
    ]
    list_filter = ["status", "doc_type"]
    search_fields = ["original_filename", "issuer"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [AnalysisResultInline]
