from django.db import models
from django.conf import settings
from accounts.models import User

# Create your models here.

class Post(models.Model):
    description = models.CharField(max_length=255)
    image = models.TextField(null=True)
    def __str__(self):
        return self.description
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, #se apagar o usuario do db, apaga todas as imagens dele
        null = True
    )
    date = models.DateTimeField(auto_now_add=True, null=True)
    class Meta:
        ordering = ["-date"]

class Likes(models.Model):
    #id do post
    #id do cara que curtiu
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        null = True
    )
    user = models.ForeignKey( #n da pra pegar o user da tabela post pq ele ta ligado com o cara q postou
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null = True
    )

class Comments(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True
    )
    content = models.CharField(max_length=255)