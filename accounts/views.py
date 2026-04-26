from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from .models import User, Followers, Interests
import base64
from django.utils import timezone
from datetime import datetime, timedelta
from feed.models import Post, Comments, Saved
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
        if " " in nick:
            return HttpResponse("o campo nick não deve conter espaços. Tente: - ; _ ; . ")
        if User.objects.filter(email=email).exists():
            return HttpResponse("esse email já foi cadastrado, deseja fazer login?")
        
        if password == "1":
            new_user = User.objects.create_user(nick=nick, email=email, password=password, cargo=cargo)
            login(request, new_user)
            return render(request, 'users/interests.html')
        if password == password.lower() or password == password.upper():
            return HttpResponse("a senha deve conter letras minúsculas e maiúsculas")
        if " " in password:
            return HttpResponse("a senha não pode conter espaço")
        if password.isalnum() == True:
            return HttpResponse("a senha deve conter caracteres especiais")
        

        new_user = User.objects.create_user(nick=nick, email=email, password=password, cargo=cargo)
        login(request, new_user)
        return render(request, 'users/interests.html')
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


def interests_pg(request):
    return render(request, 'users/interests.html')

def core_pg(request, nick):
    user = get_object_or_404(User, nick=nick)
    logged_user = request.user
    imagens = Post.objects.filter(user=user)
    salvos = Saved.objects.filter(user=user)
    salvos_id = list(salvos.values_list('post_id', flat=True))
    posts_salvos = Post.objects.filter(id__in=salvos_id) #pega os objetos de cada id listado acima
    is_following = Followers.objects.filter( follower_id=logged_user.user_id, user_id=user.user_id ).exists() if logged_user.is_authenticated else False
    return render(request, "users/core/core.html", {
        "perfil_user" : user, #perfil do cabra que foi pesquisado. Isso garante que na hora de colocar dados na pagina, possa ser diferenciado user.nick de perfil_user.nick
         "imagens": imagens,
         "salvos": salvos,
         "posts_salvos" : posts_salvos,
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
    if request.user.cargo == 'artista':
        return render(request, 'users/core/new_post.html', {"nick" : nick})
    else:
        return render(request, 'users/new_artist.html')
    
def new_artist(request):
    user = request.user
    if request.method == 'POST':
        if user.cargo != 'artista':
            user.cargo = 'artista'
            user.save()
            return redirect('explore_pg')

def new_post(request): #postar post
    if request.method == 'POST':
        description = request.POST.get('post_description')
        img = request.FILES.get('post_image')
        u_id = request.user.user_id
        collab = request.POST.get('collab')
        like_number = request.POST.get('like_number')
        comment = request.POST.get('comment')
        share = request.POST.get('share')
        if img:
            if not img.content_type.startswith('image/'):
                img_compativel = False
                return HttpResponse("erro: formato de arquivo inválido")
            else:
                img_compativel = True
                img_b64 = base64.b64encode(img.read()).decode('utf-8') #transforma a imagem em b64
            
            if Post.objects.filter(image=img_b64).exists(): #se ja tiver uma postagem com aquela imagem, ela não é feita
                img_compativel = False #nao muda muita coisa, mas é bom garantir
                return HttpResponse("erro: essa postagem já foi feita")
                
            else:
                post_data = {'user_id': u_id}

                if description:
                    post_data['description'] = description

                if img_compativel:
                    post_data['image'] = img_b64

                if like_number:
                    post_data['like_number'] = like_number

                if comment:
                    post_data['comment'] = comment

                if share:
                    post_data['share'] = share

                if collab:
                    collaborator = User.objects.filter(nick=collab).first()
                    if collaborator:
                        collaborator_id = collaborator.user_id
                        post_data['collaborator_id'] = collaborator_id

                Post.objects.create(**post_data)
                #parte que adiciona 1 ao numero de postagens do usuario
                user = request.user
                user.arts = Post.objects.filter(user=user).count()
                user.save() #salva a quantidade de artes do user
                nick = user.nick # passa o nick para o core_pg pq ele precisa pra atualizar as postagens no perfil
                return core_pg(request, nick)
        
        else:
            return HttpResponse('erro: algo deu errado na hora de criar seu post')
        

        
def delete_post(request, id):
    user = request.user
    nick = user.nick
    post = Post.objects.get(id=id)
    if post.user_id != user.user_id:
        return HttpResponse('erro: você não é o dono deste post')
    
    post.delete()
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


def interests(request):
    if request.method == 'POST':
        interesses = request.POST.getlist('interest')
        user = request.user
        if interesses:
            Interests.objects.bulk_create([
                Interests(user=user, interest=interesse)
                for interesse in interesses
            ])
        return redirect('explore_pg')