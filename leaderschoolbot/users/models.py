from django.db import models


class User(models.Model):
    external_id = models.PositiveIntegerField(
        verbose_name='ID пользователя',
        unique=True,
    )
    name = models.TextField(
        verbose_name='Юзернейм',
        null=True,
    )

    first_last_name = models.TextField(
        verbose_name='Имя и фамилия',
        null=True,
    )

    CHOICES = [
        ('Admin', 'Админ'),
        ('User', 'Пользователь'),
        ('Operator', 'Оператор'),
    ]

    access_level = models.CharField(
        max_length=10,
        choices=CHOICES,
        verbose_name='Уровень доступа',)

    def __str__(self):
        return f'#{self.external_id} {self.name}'

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профиль'


class Message(models.Model):
    user = models.ForeignKey(
        to='users.User',
        verbose_name='Профиль',
        on_delete=models.CASCADE,
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


class Call(models.Model):
    user = models.ForeignKey(
        to='users.User',
        verbose_name='Профиль',
        on_delete=models.CASCADE,
    )
    message = models.TextField(
        verbose_name='Текст сообщения',
    )

    created_at = models.DateTimeField(
        verbose_name='Время получения',
        auto_now_add=True,
    )

    class Meta:
        verbose_name = 'Запрос звонка'
        verbose_name_plural = 'Запрос звонка'
