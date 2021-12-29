from django.db import models


class Files(models.Model):
    file_start = models.FileField(
        verbose_name='Files', upload_to='imports/start/', null=True, blank=True, default=None)
    file_nice = models.FileField(
        verbose_name='Files', upload_to='imports/nice/', null=True, blank=True, default=None)
    file_problem = models.FileField(
        verbose_name='Files', upload_to='imports/problem/', null=True, blank=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='file creation date', null=True)

    class Meta:
        verbose_name = 'file_import'
        verbose_name_plural = 'files_import'

    def __str__(self):
        return f'{self.id}. {self.file_start} {self.file_nice} {self.file_problem} {self.created_at}'
