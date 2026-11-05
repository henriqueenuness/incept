from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from .models import User, Followers, Interests, Links
import base64
import io
from django.utils import timezone
from datetime import datetime, timedelta
from feed.models import Post, Comments, Saved ,Media , Notification
from django.http import HttpResponse, JsonResponse, Http404
from django.db import transaction
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, validate_email
from django.utils.http import url_has_allowed_host_and_scheme
from supabase import create_client
from PIL import Image
import os
import mimetypes
from django.contrib import messages
import uuid
import re

ALLOWED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_AUDIO_EXTS = {'.mp3'}
MAX_AUDIO_SIZE = 20 * 1024 * 1024
MAX_IMAGE_SIZE = 20 * 1024 * 1024 #antes imagem de post nao tinha limite nenhum
MAX_CORE_PICTURE_UPLOAD = 10 * 1024 * 1024
CORE_PICTURE_SIZE = (512, 512) #a foto e guardada em base64 no banco e vai em todas as paginas, entao reduzimos

NICK_MAX = 25 #mesmo max_length do User.nick
NICK_RE = re.compile(r'^[A-Za-z0-9_.-]+$') #nick vira parte da url (/core/<nick>/), "/" ou "?" quebravam as paginas
CARGOS = ('artista', 'cliente')
INTERESSES = ('song', 'paint', 'media')
MAX_LINKS = 10
WEBSITE_LINK_NAME = "user_website"
#grupos do select de estilo (chaves do User.ART_STYLES)
ART_STYLE_GROUPS = [
    ("Música", ['música clássica', 'jazz', 'blues', 'gospel', 'soul', 'pop', 'rock', 'country']),
    ("Pintura e desenho", ['desenho2d', 'realismo', 'cartoon', 'manga', 'chibi', 'caricatura', 'doodleart', 'surrealismo', 'modelagem3d']),
    ("Audiovisual e design", ['videomaker', 'editordevideo', 'filmmaker', 'roteirista', 'designergrafico', 'editorfotos', 'colorista', 'motiondesigner']),
]

# Create your views here.
def home(request):
    if request.user.is_authenticated:
        return redirect('explore_pg')
    return render(request, 'home.html')


def nick_error(nick):
    """Retorna a mensagem de erro do nick, ou None se estiver ok."""
    if " " in nick:
        return "o campo nick não deve conter espaços. Tente: - ; _ ; . "
    if len(nick) > NICK_MAX:
        return f"o nick pode ter no máximo {NICK_MAX} caracteres"
    if not NICK_RE.match(nick):
        return "o nick só pode ter letras sem acento, números e - _ ."
    return None


def password_error(password):
    """Mesmas regras de senha de antes, mais o tamanho minimo."""
    if len(password) < 8:
        return "a senha deve ter pelo menos 8 caracteres"
    if password == password.lower() or password == password.upper():
        return "a senha deve conter letras minúsculas e maiúsculas"
    if " " in password:
        return "a senha não pode conter espaço"
    if password.isalnum() == True:
        return "a senha deve conter caracteres especiais"
    return None


def normalize_url(url):
    """Coloca https:// quando falta e so aceita http/https (um link javascript: viraria XSS no perfil)."""
    url = (url or '').strip()
    if not url:
        return None
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', url):
        url = "https://" + url
    try:
        URLValidator(schemes=['http', 'https'])(url)
    except ValidationError:
        return None
    return url


def safe_next_url(request, url):
    if url and url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return url
    return None


def signup_pg(request):
    if request.user.is_authenticated:
        return redirect('explore_pg')
    return render(request, 'users/signin.html')
    #quando for chamado, renderiza pagina de cadastro

def signup(request): #registro/cadastro usuario
    if request.method == "POST":
        nick = (request.POST.get('nick') or '').strip()
        email = (request.POST.get('email') or '').strip()
        password = request.POST.get('password') or ''
        cargo = None
    

        if not nick or not email or not password: #antes, campo vazio virava None e quebrava no " " in nick
            return HttpResponse("preencha nick, email e senha")

        erro = nick_error(nick)
        if erro:
            return HttpResponse(erro)
        if User.objects.filter(nick__iexact=nick).exists():
            return HttpResponse("alguém já usa esse nick")
        try:
            validate_email(email)
        except ValidationError:
            return HttpResponse("email inválido")
        if User.objects.filter(email__iexact=email).exists():
            return HttpResponse("esse email já foi cadastrado, deseja fazer login?")

        if not (password == "1" and settings.DEBUG): #atalho de teste, so funciona no ambiente local
            erro = password_error(password)
            if erro:
                return HttpResponse(erro)

        new_user = User.objects.create_user(nick=nick, email=email, password=password, cargo=cargo)
        login(request, new_user)
        return redirect('interests_pg')
    return redirect('signup_pg')

def login_pg(request):
    if request.user.is_authenticated:
        return redirect('explore_pg')
    return render(request, 'users/login.html', {'next': safe_next_url(request, request.GET.get('next')) or ''})

def login_auth(request): #login usuario
    if request.method == "POST": #o nome da funcao nao pode ser login pq o django ja tem uma funcao com esse nome
        email = (request.POST.get('email') or '').strip()
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        if not user:
            return HttpResponse("senha ou email incorretos, tente novamente")
        login(request, user)
        #volta pra pagina que pediu login (?next=), se for do proprio site
        return redirect(safe_next_url(request, request.POST.get('next')) or 'explore_pg')

    return redirect('login_pg')



def follow_list_pg(request, nick):
    #a pagina antiga era um rascunho sem estilo; a lista de "seguindo" ja existe em /core/<nick>/seguindo/
    return redirect('following', nick=nick)


@require_POST
def make_logout(request):
    logout(request)
    return redirect('home')


@login_required
def interests_pg(request):
    return render(request, 'users/interests.html')

def core_pg(request, nick):
    user = get_object_or_404(User, nick=nick)
    logged_user = request.user
    is_owner = logged_user.is_authenticated and logged_user.user_id == user.user_id
    imagens = Post.objects.filter(user=user).prefetch_related('media')
    collabs = Post.objects.filter(collaborator=user).select_related('user').prefetch_related('media')
    #os salvos sao privados: so o dono do perfil ve (antes qualquer visitante via)
    posts_salvos = Post.objects.filter(saved__user=user).distinct().prefetch_related('media') if is_owner else Post.objects.none()
    is_following = Followers.objects.filter(
        follower_id=logged_user.user_id, user_id=user.user_id
    ).exists() if logged_user.is_authenticated else False
    return render(request, "users/core/core.html", {
        "perfil_user": user,
        "imagens": imagens,
        "collabs": collabs,
        "posts_salvos": posts_salvos,
        #so links http/https (um "javascript:" antigo no banco viraria script ao clicar); o site vem primeiro
        "links": sorted(
            [l for l in user.links.all() if l.url.lower().startswith(('http://', 'https://'))],
            key=lambda l: (l.name != WEBSITE_LINK_NAME, l.id),
        ),
        "is_owner": is_owner,
        "is_following": is_following
    })


'''def core_posts(request, nick):
    nick = request.user.user_id #pega o id do usuario com tal nick
    imagens = post.objects.filter(user = user)
    return render(request, "users/core/core.html", {"imagens" : imagens})'''

@login_required
def edit_core_pg(request):
    user = request.user
    website = user.links.filter(name=WEBSITE_LINK_NAME).first()
    extra_links = [
        {"title": l.name, "url": l.url}
        for l in user.links.exclude(name=WEBSITE_LINK_NAME).order_by('id')
    ]
    return render(request, 'users/core/edit-core.html', {
        'website': website.url if website else '',
        'extra_links': extra_links,
        'art_style_groups': [
            (grupo, [(valor, dict(User.ART_STYLES)[valor]) for valor in valores])
            for grupo, valores in ART_STYLE_GROUPS
        ],
    })


def core_picture_error(core_picture):
    if not (core_picture.content_type or '').startswith('image/'):
        return "a foto precisa ser uma imagem (png, jpg, webp ou gif)"
    if core_picture.size > MAX_CORE_PICTURE_UPLOAD:
        return "a foto pode ter no máximo 10 MB"
    return None


def resize_core_picture(core_picture):
    """Abre a imagem com o Pillow (garante que e imagem de verdade), reduz pra 512px e devolve o base64."""
    core_picture.seek(0)
    img = Image.open(core_picture)
    img.thumbnail(CORE_PICTURE_SIZE)
    out = io.BytesIO()
    if img.mode in ('RGBA', 'LA', 'P'):
        img.convert('RGBA').save(out, format='PNG', optimize=True)
    else:
        img.convert('RGB').save(out, format='JPEG', quality=85)
    return base64.b64encode(out.getvalue()).decode('utf-8')


@login_required
def edit_core(request): #edit core
    if request.method != "POST":
        return redirect('edit_core_pg')

    user = request.user
    real_name = request.POST.get('real_name')
    bio = request.POST.get('bio')
    art_style = request.POST.get('art_style')
    nick = (request.POST.get('nick') or '').strip()
    core_picture = request.FILES.get('core_picture')

    #valida tudo antes de salvar qualquer coisa
    if nick and nick != user.nick:
        erro = nick_error(nick)
        if not erro and User.objects.filter(nick__iexact=nick).exclude(user_id=user.user_id).exists():
            erro = "alguém já usa esse nick, tente outro"
        if not erro and user.last_nick_change: #se tiver mudança
            tempo_restante = timedelta(days=14) - (timezone.now() - user.last_nick_change)
            if tempo_restante > timedelta(0): #se a ultima mudança for a menos de 14 dias atras
                dias = tempo_restante.days
                horas = tempo_restante.seconds // 3600
                erro = f"faltam {dias} dias e {horas} horas para poder mudar o nick novamente"
        if erro:
            messages.error(request, erro)
            return redirect('edit_core_pg')
        user.nick = nick
        user.last_nick_change = timezone.now()

    if core_picture:
        erro = core_picture_error(core_picture)
        if not erro:
            try:
                user.core_picture = resize_core_picture(core_picture)
            except Exception: #Pillow nao conseguiu abrir: nao e uma imagem valida
                erro = "não foi possível ler essa imagem, tente outra"
        if erro:
            messages.error(request, erro)
            return redirect('edit_core_pg')

    valid_styles = {c[0] for c in User.ART_STYLES if c[0]}
    if art_style in valid_styles:
        user.art_style = art_style #sem isso, quando o usuario tenta usar edit core sem atualizar esse campo, ele considera como vazio

    if real_name is not None: #se o campo nao vier no POST, mantem o que ja tinha
        user.real_name = real_name.strip()[:255]
    if bio is not None:
        user.bio = bio[:255]

    link_errors = []
    with transaction.atomic():
        user.save()

        if 'website_link' in request.POST:
            website_raw = request.POST.get('website_link')
            website = normalize_url(website_raw)
            if website_raw.strip() and not website:
                link_errors.append(website_raw.strip())
            else:
                #campo vazio apaga o site; antes nao tinha como remover
                Links.objects.filter(user_id = user.user_id, name = WEBSITE_LINK_NAME).delete()
                if website:
                    Links.objects.create(user_id = user.user_id, url = website, name = WEBSITE_LINK_NAME)

        if 'link' in request.POST:
            #os links extras do formulario nunca eram salvos
            novos = []
            for url_raw, nome in zip(request.POST.getlist('link'), request.POST.getlist('link_name')):
                if not url_raw.strip():
                    continue
                url = normalize_url(url_raw)
                if not url:
                    link_errors.append(url_raw.strip())
                    continue
                nome = (nome or '').strip()[:50] or url.split('://', 1)[1].split('/')[0][:50]
                if nome == WEBSITE_LINK_NAME:
                    nome = "site"
                novos.append(Links(user_id = user.user_id, url = url, name = nome))
            Links.objects.filter(user_id = user.user_id).exclude(name = WEBSITE_LINK_NAME).delete()
            Links.objects.bulk_create(novos[:MAX_LINKS])

    if link_errors:
        messages.warning(request, "Estes links não são válidos e não foram salvos: " + ", ".join(link_errors))
    messages.success(request, "Perfil atualizado.")
    return redirect('edit_core_pg') #redirect evita reenviar o formulario ao apertar F5


def storage_path(public_url):
    """'https://x.supabase.co/storage/v1/object/public/posts/1/2/a.png' -> '1/2/a.png'"""
    marker = '/object/public/posts/'
    if public_url and marker in public_url:
        return public_url.split(marker, 1)[1].split('?')[0]
    return None


def remove_post_files(posts):
    """Apaga do Supabase os arquivos dos posts (antes ficavam ocupando espaço pra sempre). Falha aqui nao impede apagar o post."""
    paths = [
        p for p in (storage_path(m.image_url) for m in Media.objects.filter(post__in=posts))
        if p
    ]
    if not paths:
        return
    try:
        get_supabase().storage.from_("posts").remove(paths)
    except Exception:
        pass


@login_required
@require_POST
def delete_account(request):
    user = request.user
    remove_post_files(Post.objects.filter(user=user))
    logout(request)
    user.delete()
    return redirect('home')

@login_required
@require_POST
def delete_core_picture(request):
    user = request.user
    default_core_picture = User._meta.get_field("core_picture").get_default()
    user.core_picture = default_core_picture
    user.save()
    messages.success(request, "Foto removida.")
    return redirect('edit_core_pg')

@login_required
def new_post_pg(request, nick):
    if request.user.cargo == 'artista':
        return render(request, 'users/core/new_post.html', {
            'max_upload_mb': MAX_IMAGE_SIZE // (1024 * 1024),
        })
    else:
        return render(request, 'users/new_artist.html')

@login_required
def new_artist(request):
    user = request.user
    if request.method != 'POST':
        return render(request, 'users/new_artist.html')
    if user.cargo != 'artista':
        user.cargo = 'artista'
        user.save()
    return redirect('new_post_pg', nick=user.nick) #quem escolheu "quero ser artista" quer publicar

_supabase = None

def get_supabase():
    """Cria o cliente do supabase so quando precisa (antes era criado ao importar o arquivo e derrubava o site se faltasse a variavel)."""
    global _supabase
    if _supabase is None:
        _supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    return _supabase

def is_valid_media(f):
    """Retorna True se o arquivo é imagem ou mp3 permitido."""
    ext = os.path.splitext(f.name)[1].lower()
    content_type = (f.content_type or '').lower()

    if ext in ALLOWED_IMAGE_EXTS and content_type.startswith('image/'):
        return f.size <= MAX_IMAGE_SIZE
    if ext in ALLOWED_AUDIO_EXTS and content_type in ('audio/mpeg', 'audio/mp3'):
        return f.size <= MAX_AUDIO_SIZE
    return False


def make_storage_name(original_name):
    """Gera um nome seguro e único: só letras/números + extensão."""
    ext = os.path.splitext(original_name)[1].lower()
    return f"{uuid.uuid4().hex}{ext}"

def upload_image(file, filename):
    file.seek(0)
    data = file.read()

    content_type = (
        getattr(file, "content_type", None)
        or mimetypes.guess_type(filename)[0]
        or "application/octet-stream"
    )
    # normaliza variações não padrão de mp3
    if content_type in ("audio/mp3", "audio/x-mpeg-3"):
        content_type = "audio/mpeg"

    supabase = get_supabase()
    supabase.storage.from_("posts").upload(
        filename, data, file_options={"content-type": content_type}
    )
    result = supabase.storage.from_("posts").get_public_url(filename)

    # normaliza: pode vir como string ou como dict dependendo da versão da lib
    if isinstance(result, dict):
        public_url = (
            result.get("publicUrl")
            or result.get("publicURL")
            or result.get("public_url")
        )
    else:
        public_url = result

    # algumas versões retornam a URL com "?" no final
    return public_url.rstrip("?") if public_url else public_url
def parse_hashtags(raw):
    """'#arte #Pixel, digital' -> ['arte', 'pixel', 'digital']"""
    if not raw:
        return []
    tags = re.split(r'[\s,#]+', raw)
    seen = []
    for t in tags:
        t = t.strip().lower()[:50]
        if t and t not in seen:
            seen.append(t)
    return seen[:20]
@login_required
def new_post(request):
    if request.method == 'POST':
        if request.user.cargo != 'artista': #so artista publica (a tela ja escondia, mas a rota aceitava)
            return redirect('new_post_pg', nick=request.user.nick)
        description = (request.POST.get('post_description') or '').strip()[:255] #o banco aceita no maximo 255
        files = request.FILES.getlist('post_image')  # imagens e mp3 no mesmo input
        u_id = request.user.user_id
        collab = (request.POST.get('collab') or '').strip().lstrip('@')
        like_number = request.POST.get('like_number')
        comment = request.POST.get('comment')
        share = request.POST.get('share')
        roxotag = request.POST.get('roxotag')

        post_data = {'user_id': u_id}
        if description:
            post_data['description'] = description
        if roxotag:
            post_data['roxotags'] = parse_hashtags(roxotag)
        #checkbox marcado manda "True"; desmarcado nao manda nada (e o model usa False)
        post_data['like_number'] = bool(like_number)
        post_data['comment'] = bool(comment)
        post_data['share'] = bool(share)
        if collab and collab.lower() != request.user.nick.lower(): #marcar a si mesmo como collab e ignorado
            collaborator = User.objects.filter(nick__iexact=collab).exclude(user_id=u_id).first()
            if collaborator:
                post_data['collaborator_id'] = collaborator.user_id
            else:
                messages.warning(request, f"Não encontramos o perfil @{collab} para a collab; o post foi publicado sem ela.")

        post_instance = Post.objects.create(**post_data)

        rejected = []
        for f in files:
            if not is_valid_media(f):
                rejected.append(f.name)
                continue

            filename = f"{u_id}/{post_instance.id}/{make_storage_name(f.name)}"
            try:
                public_url = upload_image(f, filename)
            except Exception: #falha no supabase nao pode derrubar a pagina
                rejected.append(f.name)
                continue
            Media.objects.create(post=post_instance, image_url=public_url)

        user = request.user
        if not description and not post_instance.media.exists():
            # nenhum arquivo subiu e nao tem texto: nao deixa um post vazio no feed
            post_instance.delete()
            messages.error(request, "Não foi possível publicar: nenhum arquivo foi enviado.")
            return redirect('new_post_pg', nick=user.nick)

        if rejected:
            messages.warning(
                request,
                "Alguns arquivos não foram enviados (formato inválido, muito grande ou falha no envio): "
                + ", ".join(rejected)
            )

        # Atualiza contador de artes
        user.arts = Post.objects.filter(user=user).count()
        user.save(update_fields=['arts'])
        messages.success(request, "Post publicado.")
        return redirect('core_pg', nick=user.nick) #redirect evita repostar ao apertar F5

    return redirect('new_post_pg', nick=request.user.nick)


@login_required
@require_POST
def delete_post(request, id):
    user = request.user
    nick = user.nick
    post = get_object_or_404(Post, id=id)
    if post.user_id != user.user_id:
        return HttpResponse('erro: você não é o dono deste post', status=403)

    remove_post_files([post])
    post.delete()
    user.arts = Post.objects.filter(user=user).count()
    user.save(update_fields=['arts'])
    return redirect('core_pg', nick=nick)

@login_required
@require_POST
def follow(request, id):
    followed = get_object_or_404(User, user_id=id)
    follower_id = request.user.user_id
    followed_id = followed.user_id
    if followed_id == follower_id:
        return JsonResponse({'error': 'você não pode seguir a si mesmo'}, status=400)

    with transaction.atomic(): #ou grava tudo (relacao + contadores + notificacao) ou nada
        relation = Followers.objects.filter(follower_id=follower_id, user_id=followed_id)

        if relation.exists():
            relation.delete() #apaga tambem linhas duplicadas, se houver
            Notification.objects.filter(user=followed, actor=request.user, type='follow').delete()
            is_following = False
        else:
            Followers.objects.create(follower_id=follower_id, user_id=followed_id)
            Notification.objects.create( #so notifica quando segue, nao quando deixa de seguir
                user=followed,
                actor=request.user,
                type='follow'
            )
            is_following = True

        #recalcula os contadores a partir das relacoes reais: antes o +1/-1 saia do lugar com cliques duplos
        followers_count = Followers.objects.filter(user_id=followed_id).values('follower_id').distinct().count()
        following_count = Followers.objects.filter(follower_id=follower_id).values('user_id').distinct().count()
        User.objects.filter(user_id=followed_id).update(followers=followers_count)
        User.objects.filter(user_id=follower_id).update(following=following_count)
    return JsonResponse({
        'is_following' : is_following,
        'followers': followers_count,
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


@login_required
def interests(request):
    if request.method == 'POST':
        interesses = [i for i in dict.fromkeys(request.POST.getlist('interest')) if i in INTERESSES]
        user = request.user
        if interesses:
            #substitui em vez de acumular: enviar de novo criava linhas repetidas
            Interests.objects.filter(user=user).delete()
            Interests.objects.bulk_create([
                Interests(user=user, interest=interesse)
                for interesse in interesses
            ])
    return redirect('explore_pg')

@login_required
def get_notifications(request):
    notifications = request.user.notifications.filter(read=False).select_related('actor', 'post').order_by('-created_at')
    data = [
        {
            "message": n.get_message(),
            "created_at": n.created_at.strftime("%d/%m/%Y %H:%M"),
            "read": n.read
        }
        for n in notifications
    ]
    return JsonResponse({"notifications": data})

@login_required
def notifications_page(request):
    notifications = list(request.user.notifications.select_related('actor', 'post').order_by('-created_at')[:100])
    #marca como lidas depois de carregar a lista (a pagina ainda mostra quais eram novas); antes ficavam "nao lidas" pra sempre
    request.user.notifications.filter(read=False).update(read=True)
    return render(request, 'feed/notifications.html', {'notifications': notifications})


def followers(request, nick):
    perfil_user = get_object_or_404(User, nick=nick)
    relacoes = Followers.objects.filter(user=perfil_user).select_related('follower')
    seguidores = [r.follower for r in relacoes]

    return render(request, 'users/core/follower.html', {
        'perfil_user': perfil_user,
        'usuarios': seguidores,
        'titulo': 'Seguidores',
    })


def following(request, nick):
    perfil_user = get_object_or_404(User, nick=nick)
    relacoes = Followers.objects.filter(follower=perfil_user).select_related('user')
    seguindo = [r.user for r in relacoes]

    return render(request, 'users/core/follower.html', {
        'perfil_user': perfil_user,
        'usuarios': seguindo,
        'titulo': 'Seguindo',
    })
