from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('complaints', '0008_alter_complaint_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='complaint',
            name='resolution_image',
            field=models.ImageField(blank=True, null=True, upload_to='resolution_proofs/'),
        ),
        migrations.AddField(
            model_name='complaint',
            name='resolved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
