from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from .models import User
import base64
from .models import base64image
from django.http import HttpResponse


# Create your views here.
def home(request):
    return render(request, 'home.html')


def signup_pg(request):
    return render(request, 'users/signin.html')
    #quando for chamado, renderiza pagina de cadastro

def signup(request): #registro/cadastro usuario
    if request.method == "POST":
        nick = request.POST.get('nick')
        email = request.POST.get('email')
        password = request.POST.get('password')
        cargo = request.POST.get('cargo')

        new_user = User.objects.create_user(nick=nick, email=email, password=password, cargo=cargo)
        return render(request, 'users/login.html')

def login_pg(request):
    return render(request, 'users/login.html')

def login_auth(request): #login usuario
    if request.method == "POST": #o nome da funcao nao pode ser login pq o django ja tem uma funcao com esse nome
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        if user is not None:
            if user.cargo == 'artista':
                login(request, user)
                return render(request, 'home.html')
            elif user.cargo == 'cliente':
                login(request, user)
                return render(request, 'home.html')
            # nesse caso, ambos fazem a mesma coisa, mas futuramente podemos encaminhar para paginas diferentes de acordo com a utilidade de cada funcao para o usuario.
            #por exemplo, um cliente nao vai precisar de botoes para criar conteudo
            
        else:
            return render(request, 'users/signin.html')
            # se der algum erro, volta pro cadastro






def make_logout(request):
    logout(request)
    return render(request, 'home.html')


def explore_pg(request):
    return render(request, 'feed/explore.html')


def core_pg(request, nick):
    user = get_object_or_404(User, nick=nick)
    imagens = base64image.objects.filter(user=user)
    return render(request, "users/core/core.html", {
         "imagens": imagens })



'''def core_posts(request, nick):
    nick = request.user.user_id #pega o id do usuario com tal nick
    imagens = base64image.objects.filter(user = user)
    return render(request, "users/core/core.html", {"imagens" : imagens})'''

def edit_core_pg(request):
    return render(request, 'users/core/edit-core.html')

def edit_core(request): #edit core
    if request.method == "POST":
        real_name = request.POST.get('real_name')
        bio = request.POST.get('bio')
        art_style = request.POST.get('art_style')
        user = request.user
        user.real_name = real_name
        user.bio = bio
        user.art_style = art_style
        user.save()
        return render(request, 'users/core/edit-core.html', {'user': request.user})




def new_post_pg(request, nick):
    nick = request.user.user_id
    return render(request, 'users/core/new_post.html', {"nick" : nick})


def publish_post(request): #postar post
    if request.method == 'POST':
        description = request.POST.get('post_description')
        img = request.FILES.get('post_image')
        u_id = request.user.user_id
        if img:
            img_b64 = base64.b64encode(img.read()).decode('utf-8') #transforma a imagem em b64

            if base64image.objects.filter(image=img_b64).exists(): #se ja tiver uma postagem com aquela imagem, ela não é feita
                return HttpResponse("erro: essa postagem já foi feita")
            else:
                base64image.objects.create(description=description, image=img_b64, user_id = u_id) #cria a postagem
                #decoded_img = base64.b64decode(img_b64, validate=True)
                #parte que adiciona 1 ao numero de postagens do usuario
                user = request.user
                user.arts = base64image.objects.filter(user=user).count()
                user.save() #salva a quantidade de artes do user
                nick = user.nick # passa o nick para o core_pg pq ele precisa pra atualizar as postagens no perfil
                return core_pg(request, nick)
            
        else:
            return HttpResponse('erro: algo deu errado')
        



'''def users_list_pg(request):
    return render(request, 'users/users_list.html')'''


"""def users_list(request):
    new_user = User()
    new_user.nick = request.POST.get('nick')
    new_user.email = request.POST.get('email')
    new_user.password = request.POST.get('password')
    new_user.cargo = request.POST.get('cargo')

    if new_user.cargo == 'artista':
        new_user.save()
        return render(request, 'users/home.html')
    else:
        #mostrar usuarios
        new_user.save()
        users = { 
            'users' : User.objects.all()
            }
        return render(request, 'users/users_list.html', users)"""




"""def auth_user(request):
    username = request.POST.get('email')
    password = request.POST.get('password')
    if User.objects.filter(email=username).exists() and User.objects.filter(password=password).exists():
        return render(request, 'home.html')
    else:
        return render(request, 'users/login.html')"""