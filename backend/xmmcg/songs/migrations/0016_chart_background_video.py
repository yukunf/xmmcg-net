from django.db import migrations, models
import songs.models


class Migration(migrations.Migration):

    dependencies = [
        ('songs', '0015_song_background_video'),
    ]

    operations = [
        migrations.AddField(
            model_name='chart',
            name='background_video',
            field=models.FileField(blank=True, help_text='谱面背景视频（可选）', null=True, upload_to=songs.models.get_chart_video_filename),
        ),
    ]
