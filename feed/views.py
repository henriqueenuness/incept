from django.shortcuts import render, redirect
from accounts.models import User, Followers
from .models import Reports, Post, Likes, Comments, Saved , Notification
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Prefetch, Q
from django.utils.timesince import timesince
from accounts.views import parse_hashtags

FEED_LIMIT = 60 #antes o feed carregava todos os posts do banco de uma vez
SUGGESTED_LIMIT = 30
SEARCH_LIMIT = 50
COMMENT_MAX = 255 #mesmo max_length do Comments.content

# Create your views here.
FILTROS_BUSCA = [('artistas', 'Artistas'), ('musica', 'Música'), ('visual', 'Artes visuais'), ('video', 'Vídeo')]

def search_pg(request):
    return render(request, 'feed/search.html', {'filtros_busca': FILTROS_BUSCA})


def feed_queryset():
    """Posts com autor, mídias, comentários (já ordenados) e totais de curtidas/comentários em poucas consultas.
    Antes o template percorria TODOS os comentários do banco para cada post."""
    return (Post.objects
            .select_related('user', 'collaborator')
            .prefetch_related(
                'media',
                Prefetch('comments_set', queryset=Comments.objects.select_related('user').order_by('date'), to_attr='comments_list'),
            )
            .annotate(
                like_total=Count('likes', distinct=True),
                comment_total=Count('comments', distinct=True),
            )
            .order_by('-date'))


def feed_context(request, posts):
    """Estado inicial dos botões: antes curtidas e salvos sempre apareciam desmarcados ao recarregar a página."""
    liked_ids, saved_ids, following_ids = set(), set(), []
    if request.user.is_authenticated:
        post_ids = [p.id for p in posts]
        liked_ids = set(Likes.objects.filter(user=request.user, post_id__in=post_ids).values_list('post_id', flat=True))
        saved_ids = set(Saved.objects.filter(user=request.user, post_id__in=post_ids).values_list('post_id', flat=True))
        following_ids = list(Followers.objects.filter(follower_id=request.user.user_id).values_list('user_id', flat=True))
    return {
        "posts": posts,
        "liked_ids": liked_ids,
        "saved_ids": saved_ids,
        "following_ids": following_ids,
    }


def explore_pg(request):
    posts = list(feed_queryset()[:FEED_LIMIT])
    context = feed_context(request, posts)
    suggested = User.objects.order_by('nick')
    if request.user.is_authenticated:
        suggested = suggested.exclude(user_id=request.user.user_id)
    context["suggested_users"] = list(suggested[:SUGGESTED_LIMIT])
    return render(request, 'feed/explore.html', context)

@login_required
def cycle_pg(request):
    followings_ids = Followers.objects.filter(follower_id=request.user.user_id).values_list('user_id', flat=True)
    posts = list(feed_queryset().filter(Q(user_id__in=followings_ids) | Q(collaborator_id__in=followings_ids))[:FEED_LIMIT])
    return render(request, 'feed/cycle.html', feed_context(request, posts))

SEARCH_FILTERS = {
    #filtro da busca -> estilos (chaves do User.ART_STYLES)
    'musica': ['música clássica', 'jazz', 'blues', 'gospel', 'soul', 'pop', 'rock', 'country'],
    'visual': ['desenho2d', 'realismo', 'cartoon', 'manga', 'chibi', 'caricatura', 'doodleart', 'surrealismo', 'modelagem3d', 'designergrafico', 'colorista'],
    'video': ['videomaker', 'editordevideo', 'filmmaker', 'roteirista', 'motiondesigner', 'editorfotos'],
}

def search_user(request):
    search = (request.GET.get('search') or '').strip()[:100]
    filtro = request.GET.get('filtro') or ''
    if filtro not in SEARCH_FILTERS and filtro != 'artistas':
        filtro = ''
    users = []
    posts = []
    followings_ids = []

    if search.startswith('#'):
        tags = parse_hashtags(search)
        if tags:
            # posts que possuem TODAS as hashtags digitadas
            posts = (Post.objects
                     .filter(roxotags__contains=tags)
                     .select_related('user')
                     .prefetch_related('media') #antes cada post fazia mais uma consulta
                     .order_by('-date')[:SEARCH_LIMIT])
            # use roxotags__overlap=tags se quiser posts com QUALQUER uma delas

    elif search or filtro:
        users = User.objects.all()
        if search:
            #antes so buscava pelo nick; agora tambem pelo nome e pelo estilo
            users = users.filter(Q(nick__icontains=search) | Q(real_name__icontains=search) | Q(art_style__icontains=search))
        if filtro == 'artistas':
            users = users.filter(cargo='artista')
        elif filtro:
            users = users.filter(art_style__in=SEARCH_FILTERS[filtro])
        users = list(users.order_by('nick')[:SEARCH_LIMIT])
        followings_ids = list(
            Followers.objects.filter(
                follower_id=request.user.user_id,
                user_id__in=[u.user_id for u in users]
            ).values_list('user_id', flat=True)
        ) if request.user.is_authenticated else []

    return render(request, 'feed/search.html', {
        'users': users,
        'posts': posts,
        'search': search,
        'filtro': filtro,
        'filtros_busca': FILTROS_BUSCA,
        'following': followings_ids,
    })

'''def enter_core(request, nick):
    user = User.objects.get(nick=nick) # pega direto do path
    return render(request, 'users/core/core.html', {'user': user})'''

@login_required
@require_POST
def like(request, id):
    post = get_object_or_404(Post, id=id)
    like_qs = Likes.objects.filter(user=request.user, post=post)

    if like_qs.exists():
        like_qs.delete()
        liked = False
        #descurtiu: tira a notificacao que ainda nao foi lida
        Notification.objects.filter(user=post.user, actor=request.user, type='like', post=post, read=False).delete()
    else:
        Likes.objects.create(post=post, user=request.user)
        liked = True

        #curtir/descurtir/curtir criava uma notificacao nova a cada vez
        if post.user_id and post.user_id != request.user.user_id and not Notification.objects.filter(
            user=post.user, actor=request.user, type='like', post=post
        ).exists():
            Notification.objects.create(
                user=post.user,
                actor=request.user,
                type='like',
                post=post,
            )

    return JsonResponse({
        "likes": Likes.objects.filter(post=post).count(),
        "liked": liked,
    })

@login_required
@require_POST
def save(request, id):
    user = request.user.user_id
    post = get_object_or_404(Post, id=id)
    if Saved.objects.filter(user=user, post=post).exists():
        Saved.objects.filter(user=user, post=post).delete()
        saved = False
    else:
        Saved.objects.create(post=post, user_id = user)
        saved = True
    return JsonResponse({"saved" : saved,
                         "post_id" : post.id })

REPORT_REASONS = ['Conteúdo explícito', 'IA', 'Ofensivo'] #mesmas opcoes do report.html

@login_required
def report_post(request, post_id):
    post = get_object_or_404(Post.objects.select_related('user').prefetch_related('media'), id=post_id)
    context = {"post": post, "reasons": REPORT_REASONS}

    if request.method == "POST":
        reason = (request.POST.get("reason") or "").strip()[:100]
        if reason == "Outro" or not reason: #quem so escreveu o texto sem marcar "Outro" tambem conta
            reason = (request.POST.get("other_reason") or "").strip()[:500]
        if not reason: #sem motivo o banco recusava (reason nao aceita null)
            context["error"] = "Escolha um motivo ou descreva o problema."
            return render(request, "feed/report.html", context)

        if not Reports.objects.filter(user=request.user, post=post).exists(): #a mesma pessoa nao denuncia o mesmo post varias vezes
            Reports.objects.create(
                user=request.user,
                post=post,
                reason=reason
            )
        messages.success(request, "Denúncia enviada. Obrigado por avisar.")
        return redirect("explore_pg")  # redireciona de volta para feed/explore

    return render(request, "feed/report.html", context)

def serialize_comment(comment):
    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "content": comment.content,
        "created_relative": f"há {timesince(comment.date).split(',')[0]}",
        "user": {
            "id": comment.user.user_id if comment.user else None,
            "nick": comment.user.nick if comment.user else "usuario",
            "core_picture": comment.user.core_picture if comment.user else "",
        },
    }

@require_GET
def comments_api(request, id):
    post = get_object_or_404(Post, id=id)
    if not post.comment: #comentarios desativados: nao expoe os antigos
        return JsonResponse({"comments": [], "count": 0})
    comments = list(Comments.objects.filter(post=post).select_related("user").order_by("date"))
    return JsonResponse({
        "comments": [serialize_comment(comment) for comment in comments],
        "count": len(comments),
    })

@login_required
@require_POST
def comment(request, id):
    user = request.user
    postid = get_object_or_404(Post, id=id)
    cancomment = postid.comment
    if not cancomment:
        return JsonResponse({"ok": False, "error": "os comentários estão desativados para esta arte"}, status=400)
    content = (request.POST.get('comment-content') or '').strip()
    if len(content) > COMMENT_MAX: #o banco aceita no maximo 255; antes passava disso e dava erro 500
        return JsonResponse({"ok": False, "error": f"o comentário pode ter no máximo {COMMENT_MAX} caracteres"}, status=400)
    comment = None
    if content:
        comment = Comments.objects.create(user=user, content=content, post=postid)

    wants_json = request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("accept", "")
    if wants_json:
        return JsonResponse({
            "ok": bool(comment),
            "comment": serialize_comment(comment) if comment else None,
            "count": postid.comments_set.count(),
        })

    return redirect('explore_pg') #antes voltava pro HTTP_REFERER, que vem do navegador e podia apontar pra outro site
