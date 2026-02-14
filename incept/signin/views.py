from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from .models import User


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


def core_pg(request):
    return render(request, 'users/core/core.html')

def edit_core(request):
    return render(request, 'users/core/edit-core.html')

def change_core(request):
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

def users_list_pg(request):
    return render(request, 'users/users_list.html')





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