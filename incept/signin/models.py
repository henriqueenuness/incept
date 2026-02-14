from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

# Create your models here.
#aqui ficam as tabelas de database

"""class User(models.Model):
    id_user = models.AutoField(primary_key=True)
    email = models.CharField(max_length=255, unique=True) 
    password = models.CharField(max_length=255) 
    nick = models.CharField(max_length=25, unique=True)
    cargo = models.TextField(max_length=7)
    art_type = models.TextField(max_length=30, null=True)"""


class UserManager(BaseUserManager):
    def create_user(self,email, password=None, **extra_fields):
        if not email:
            raise ValueError('ta faltando o email')
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self.db)
        return user
    
class User(AbstractBaseUser):
    user_id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    nick = models.CharField(max_length=25, unique=True)
    cargo = models.CharField(max_length=50, default="nulo")
    followers = models.IntegerField(default=0)
    following = models.IntegerField(default=0)
    arts = models.IntegerField(default=0)
    real_name = models.CharField(max_length=255, null=True, default="")
    bio = models.CharField(max_length=255, null=True, default="")

    ART_STYLES = [
        ("","selecione um estilo"),
        ("música clássica", "música clássica"),
        ("jazz", "jazz"),
        ("blues", "blues"),
        ("gospel", "gospel"),
        ("soul", "soul"),
        ("pop", "pop"),
        ("rock", "rock"),
        ("country", "country"),
        ("desenho2d", "desenho 2d"),
        ("realismo", "realismo"),
        ("cartoon", "cartoon"),
        ("manga", "mangá"),
        ("chibi", "chibi"),
        ("caricatura", "caricatura"),
        ("doodleart", "doodleart"),
        ("surrealismo", "surrealismo"),
        ("modelagem3d", "modelagem 3d"),
        ("videomaker", "videomaker"),
        ("editordevideo", "editor de vídeos"),
        ("filmmaker", "filmmaker"),
        ("roteirista", "roteirista"),
        ("designergrafico", "designer gráfico"),
        ("editorfotos", "editor de fotos"),
        ("colorista", "colorista"),
        ("motiondesigner", "motiondesigner"),
    ]

    art_style = models.CharField(
        max_length=50,
        choices=ART_STYLES,
        null=True,
        default="",
    )


    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['nick']