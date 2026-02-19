from django.db import models
from django.conf import settings
from accounts.models import User

# Create your models here.

class post(models.Model):
    description = models.CharField(max_length=255)
    image = models.TextField(null=True)
    def __str__(self):
        return self.description
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, #se apagar o usuario do db, apaga todas as imagens dele
        null = True
    )

class likes(models.Model):
    #pegar o id do proprietario
    #pegar o id do post
    #pegar o id do usuario que curtiu
    post_owner_user = models.ForeignKey( #poderia pegar direto da tabela posts? sim, mas nao quero
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, #se apagar o usuario do db, apaga todas as imagens dele
        null = True
    )
    data_post = models.ForeignKey(
        post, 
        on_delete=models.CASCADE, 
        null=True
        )
    user = models