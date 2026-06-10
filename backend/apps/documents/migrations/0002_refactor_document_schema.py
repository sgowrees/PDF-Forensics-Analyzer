import uuid

import django.db.models.deletion
from django.db import migrations, models

import apps.documents.models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(model_name="document", name="uploaded_By"),
        migrations.RemoveField(model_name="document", name="filename"),
        migrations.RemoveField(model_name="document", name="file_size"),
        migrations.RemoveField(model_name="document", name="uploaded_At"),
        migrations.RemoveField(model_name="document", name="risk_level"),
        migrations.RemoveField(model_name="document", name="findings"),
        migrations.RemoveField(model_name="document", name="analyzed_At"),
        migrations.AddField(
            model_name="document",
            name="original_filename",
            field=models.CharField(default="upload.pdf", max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="document",
            name="doc_type",
            field=models.CharField(
                choices=[
                    ("invoice", "Invoice"),
                    ("bank_statement", "Bank Statement"),
                    ("payslip", "Payslip"),
                    ("certificate", "Certificate"),
                    ("unknown", "Unknown"),
                ],
                default="unknown",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="issuer",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="document",
            name="issuer_slug",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="document",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name="document",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AlterField(
            model_name="document",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("processing", "Processing"),
                    ("complete", "Complete"),
                    ("failed", "Failed"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="document",
            name="file",
            field=models.FileField(upload_to=apps.documents.models.document_upload_path),
        ),
        migrations.CreateModel(
            name="AnalysisResult",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("score", models.IntegerField()),
                (
                    "risk",
                    models.CharField(
                        choices=[
                            ("LOW", "Low"),
                            ("MEDIUM", "Medium"),
                            ("HIGH", "High"),
                        ],
                        max_length=10,
                    ),
                ),
                ("baseline_available", models.BooleanField(default=False)),
                ("reasons", models.JSONField(default=list)),
                ("score_breakdown", models.JSONField(default=dict)),
                ("classification_confidence", models.FloatField(default=0.0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "document",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analysis",
                        to="documents.document",
                    ),
                ),
            ],
            options={
                "verbose_name": "Analysis Result",
                "verbose_name_plural": "Analysis Results",
            },
        ),
    ]
