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
        null = True,
        related_name='author'
    )
    collaborator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null = True,
        related_name='collaborator'
    )
    date = models.DateTimeField(auto_now_add=True, null=True)
    class Meta:
        ordering = ["-date"]
    comment = models.BooleanField(default=False, null=False)
    like_number = models.BooleanField(default=False, null=False)
    share = models.BooleanField(default=False, null=False)
    roxotags =models.TextField(null=True)


class Hashtags(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
    )
    hashtag = models.CharField(max_length=100)
    
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

class Media(models.Model):
    post = models.ForeignKey(Post, related_name="media", on_delete=models.CASCADE)
    image_url = models.URLField(null=True, blank=True)


class Saved(models.Model):
     user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
     post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        null = True
    )

class Reports(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        null = True
    )
    reason = models.TextField(null=False)

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('follow', 'Follow'),
        ('like', 'Like'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")  # quem vai receber a notificação
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="actor_notifications")  # quem deu like ou seguiu
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    post = models.ForeignKey('Post', on_delete=models.CASCADE, null=True, blank=True)  # post que deu like
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return self.get_message()

    def get_message(self):
        if self.type == 'follow':
            return f"{self.actor.username} começou a seguir você."
        elif self.type == 'like' and self.post:
            return f"{self.actor.username} deu like no seu post '{self.post.title}'."
        return "Nova notificação."