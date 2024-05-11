from django.db import models


class User(models.Model):
    external_id = models.PositiveBigIntegerField(
        verbose_name='ID пользователя',
    )
    name = models.TextField(
        verbose_name='Имя пользователя',
    )

    def __str__(self):
        return f'#{self.external_id} {self.name}'
    
    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профиль'
