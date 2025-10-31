from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        (
            "surveys",
            "0006_rename_surveys_au_scope__6fe6f9_idx_surveys_aud_scope_623a8c_idx_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="CollectionDefinition",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "key",
                    models.SlugField(
                        help_text="Stable key used in response JSON; unique per survey"
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "cardinality",
                    models.CharField(
                        choices=[("one", "One"), ("many", "Many")],
                        default="many",
                        max_length=10,
                    ),
                ),
                ("min_count", models.PositiveIntegerField(default=0)),
                ("max_count", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="children",
                        to="surveys.collectiondefinition",
                    ),
                ),
                (
                    "survey",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="collections",
                        to="surveys.survey",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["survey", "parent"],
                        name="surveys_col_survey__b64b40_idx",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="CollectionItem",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "item_type",
                    models.CharField(
                        choices=[("group", "Group"), ("collection", "Collection")],
                        max_length=20,
                    ),
                ),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "child_collection",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="parent_links",
                        to="surveys.collectiondefinition",
                    ),
                ),
                (
                    "collection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="surveys.collectiondefinition",
                    ),
                ),
                (
                    "group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="surveys.questiongroup",
                    ),
                ),
            ],
            options={
                "ordering": ["order", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="collectionitem",
            constraint=models.UniqueConstraint(
                fields=("collection", "order"),
                name="uq_collectionitem_order_per_collection",
            ),
        ),
        migrations.AddConstraint(
            model_name="collectiondefinition",
            constraint=models.UniqueConstraint(
                fields=("survey", "key"),
                name="surveys_collection_unique_key_per_survey",
            ),
        ),
    ]
