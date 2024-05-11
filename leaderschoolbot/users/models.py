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


class Message(models.Model):
    user = models.ForeignKey(
        to='users.User',
        verbose_name='Профиль',
        on_delete=models.PROTECT,
    )
    text = models.TextField(
        verbose_name='Текст',
    )

    created_at = models.DateTimeField(
        verbose_name='Время получения',
        auto_now_add=True,
    )

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщение'
