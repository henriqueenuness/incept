from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from .models import User, Followers
import base64
from django.utils import timezone
from datetime import datetime, timedelta
from feed.models import Post, Comments
from django.http import HttpResponse, JsonResponse
from django.db.models import F


# Create your views here.
def home(request):
    if request.user.is_authenticated:
        return redirect('explore_pg')
    return render(request, 'home.html')


def signup_pg(request):
    if request.user.is_authenticated:
        return redirect('explore_pg')
    return render(request, 'users/signin.html')
    #quando for chamado, renderiza pagina de cadastro

def signup(request): #registro/cadastro usuario
    if request.method == "POST":
        nick = request.POST.get('nick')
        email = request.POST.get('email')
        password = request.POST.get('password')
        cargo = request.POST.get('cargo')
        if User.objects.filter(nick=nick).exists():
            return HttpResponse("alguém já usa esse nick")
        if User.objects.filter(email=email).exists():
            return HttpResponse("esse email já foi cadastrado, deseja fazer login?")
        new_user = User.objects.create_user(nick=nick, email=email, password=password, cargo=cargo)
        return render(request, 'users/login.html', {
            'success_message': 'Conta criada. Agora entre para abrir o feed.',
            'prefill_email': email,
        })
    return redirect('signup_pg')

def login_pg(request):
    if request.user.is_authenticated:
        return redirect('explore_pg')
    return render(request, 'users/login.html')

def login_auth(request): #login usuario
    if request.method == "POST": #o nome da funcao nao pode ser login pq o django ja tem uma funcao com esse nome
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        if not user:
            return HttpResponse("senha ou email incorretos, tente novamente")
        login(request, user)
        return redirect('explore_pg')

    return redirect('login_pg')






def make_logout(request):
    logout(request)
    return redirect('home')


def explore_pg(request):
    post = Post.objects.all()
    comments = Comments.objects.all()
    suggested_users = User.objects.exclude(user_id=request.user.user_id).order_by('nick') if request.user.is_authenticated else User.objects.all().order_by('nick')
    users_with_posts = list(Post.objects.values_list('user_id', flat=True).distinct())
    following_ids = list(
        Followers.objects.filter(follower_id=request.user.user_id).values_list('user_id', flat=True)
    ) if request.user.is_authenticated else []
    return render(request, 'feed/explore.html', {
         "posts": post,
         "comments": comments,
         "suggested_users": suggested_users,
         "users_with_posts": users_with_posts,
         "following_ids": following_ids,
    })


def core_pg(request, nick):
    user = get_object_or_404(User, nick=nick)
    logged_user = request.user
    imagens = Post.objects.filter(user=user)
    is_following = Followers.objects.filter( follower_id=logged_user.user_id, user_id=user.user_id ).exists()
    return render(request, "users/core/core.html", {
        "perfil_user" : user, #perfil do cabra que foi pesquisado. Isso garante que na hora de colocar dados na pagina, possa ser diferenciado user.nick de perfil_user.nick
         "imagens": imagens,
          "is_following": is_following })


'''def core_posts(request, nick):
    nick = request.user.user_id #pega o id do usuario com tal nick
    imagens = post.objects.filter(user = user)
    return render(request, "users/core/core.html", {"imagens" : imagens})'''

def edit_core_pg(request):
    return render(request, 'users/core/edit-core.html')

def edit_core(request): #edit core
    if request.method == "POST":
        real_name = request.POST.get('real_name')
        bio = request.POST.get('bio')
        art_style = request.POST.get('art_style')
        nick = request.POST.get('nick')
        core_picture = request.FILES.get('core_picture')
        user = request.user
        if core_picture:
            if core_picture.content_type.startswith('image/'):
                core_p = base64.b64encode(core_picture.read()).decode('utf-8')
                user.core_picture = core_p
        if art_style:
            user.art_style = art_style #sem isso, quando o usuario tenta usar edit core sem atualizar esse campo, ele considera como vazio
        if nick and nick != user.nick:
    
            if User.objects.filter(nick=nick).exclude(user_id=user.user_id).exists():
                return HttpResponse("algúem já usa esse nick, tente outro")
            if user.last_nick_change: #se tiver mudança
                tempo_restante = timedelta(days=14) - (timezone.now() - user.last_nick_change)
                if tempo_restante > timedelta(0): #se a ultima mudança for a menos de 14 dias atras
                    
                    dias = tempo_restante.days
                    horas = tempo_restante.seconds // 3600
                    return HttpResponse(f"faltam {dias} dias e {horas} horas para poder mudar o nick novamente")
                else:
                    user.nick = nick
                    user.last_nick_change = timezone.now()
            else:
                user.nick = nick
                user.last_nick_change = timezone.now()

                    

        user.real_name = real_name
        user.bio = bio
        user.save()
        return render(request, 'users/core/edit-core.html', {'user': request.user})


def delete_account(request):
    user = request.user
    user.delete()
    return redirect('home')

def delete_core_picture(request):
    user = request.user
    default_core_picture = User._meta.get_field("core_picture").get_default()
    user.core_picture = default_core_picture
    user.save()
    return render(request, 'users/core/edit-core.html', {'user': request.user})

def new_post_pg(request, nick):
    nick = request.user.user_id
    return render(request, 'users/core/new_post.html', {"nick" : nick})


def new_post(request): #postar post
    if request.method == 'POST':
        description = request.POST.get('post_description')
        img = request.FILES.get('post_image')
        u_id = request.user.user_id
        if img:
            if not img.content_type.startswith('image/'):
                img_compativel = False
                return HttpResponse("erro: formato de arquivo inválido")
            else:
                img_compativel = True
                img_b64 = base64.b64encode(img.read()).decode('utf-8') #transforma a imagem em b64

            if Post.objects.filter(image=img_b64).exists(): #se ja tiver uma postagem com aquela imagem, ela não é feita
                return HttpResponse("erro: essa postagem já foi feita")
            else:
                if description:
                    if img_compativel == True:
                        Post.objects.create(description=description, image=img_b64, user_id = u_id) #cria a postagem
                    else:
                        Post.objects.create(description=description, user_id = u_id) #cria a postagem sem imagem
                else:
                    if img_compativel == True:
                        Post.objects.create( image=img_b64, user_id = u_id) #cria a postagem
                    else:
                        Post.objects.create(user_id = u_id) #cria a postagem sem imagem
                #parte que adiciona 1 ao numero de postagens do usuario
                user = request.user
                user.arts = Post.objects.filter(user=user).count()
                user.save() #salva a quantidade de artes do user
                nick = user.nick # passa o nick para o core_pg pq ele precisa pra atualizar as postagens no perfil
                return core_pg(request, nick)
            
        else:
            return HttpResponse('erro: algo deu errado')
        
def delete_post(request, id):
    user_post = Post.objects.get(id=id)
    user_post.delete()
    user = request.user
    nick = user.nick
    user.arts = Post.objects.filter(user=user).count()
    user.save()
    return core_pg(request, nick)

def follow(request, id):
    follower_id = request.user.user_id
    followed_id = id
    relation = Followers.objects.filter(follower_id=follower_id, user_id=followed_id)

    if relation.exists():
        relation.delete()
        User.objects.filter(user_id=follower_id).update(following=F('following')-1) #nao entendi muito bem como funciona essa linha, mas ela funciona ent DEIXA AI
        User.objects.filter(user_id=followed_id).update(followers=F('followers')-1)
        is_following = False
    else:
        Followers.objects.create(follower_id=follower_id, user_id=followed_id)
        User.objects.filter(user_id=follower_id).update(following=F('following')+1)
        User.objects.filter(user_id=followed_id).update(followers=F('followers')+1)
        is_following = True

    return JsonResponse({
        'is_following' : is_following,
    })

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
