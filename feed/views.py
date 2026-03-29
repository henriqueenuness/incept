from django.shortcuts import render, redirect
from accounts.models import User, Followers
from .models import Post, Likes, Comments
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from django.utils.timesince import timesince

# Create your views here.
def search_pg(request):
    return render(request, 'feed/search.html')

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

def cycle_pg(request):
    user = request.user.user_id
    f = Followers.objects.filter(follower_id = user).values_list('user_id', flat=True)
    followings_ids = list(f)
    post = Post.objects.filter(user_id__in = followings_ids)
    comments = Comments.objects.all()
    #return HttpResponse(", ".join(str(x) for x in followings_ids))
    return render(request, 'feed/cycle.html',
                    {'user' : user,
                    'posts' : post,
                    'comments': comments,
                    #'following': list(followings_ids)
                    })

def search_user(request):
    if request.method=="GET":
        search = request.GET.get('search')
        users = []
        followings_ids = []
        if search:
            users = User.objects.filter(nick__icontains=search)
            users_ids = list(users.values_list("user_id", flat=True))
            #se na lista de seguindo(following) do usuário logado tiver o id do usuário pesquisado, ele mostra "seguindo"
            #else mostra "seguir"

            #1. filtrar o following do usuário logado
            #2. filtrar se o id do usuário buscado está na lista de seguindo do user logado
            followings_ids = list(
                Followers.objects.filter(
                    follower_id = request.user.user_id, 
                    user_id__in = users_ids)
                    .values_list('user_id', flat=True)
                    )

        else:
            users = ""
        return render(request, 'feed/search.html',
                    {'users' : users,
                    'search' : search,
                    'following': followings_ids})
        #return HttpResponse(", ".join(str(x) for x in followings_ids))

    
'''def enter_core(request, nick): 
    user = User.objects.get(nick=nick) # pega direto do path
    return render(request, 'users/core/core.html', {'user': user})'''

def like(request, id):
    user = request.user.user_id
    #likes.objects.get(post_id_id=id)
    post = get_object_or_404(Post, id=id)
    if Likes.objects.filter(user=user, post=post).exists():
        Likes.objects.filter(user=user, post=post).delete()
        liked = False
    else:
        Likes.objects.create(post=post, user_id = user) #primeiro o db, dps a variavel python
        liked = True
    return JsonResponse({"likes": post.likes_set.count(),
                         "liked" : liked }) #

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
    comments = Comments.objects.filter(post=post).select_related("user").order_by("date")
    return JsonResponse({
        "comments": [serialize_comment(comment) for comment in comments],
        "count": comments.count(),
    })

@require_POST
def comment(request, id):
    user = request.user
    postid = get_object_or_404(Post, id=id)
    content = (request.POST.get('comment-content') or '').strip()
    comment = None
    if content:
        comment = Comments.objects.create(user=user, content=content, post=postid)

    wants_json = request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("accept", "")
    if wants_json:
        return JsonResponse({
            "ok": bool(comment),
            "comment": serialize_comment(comment) if comment else None,
            "count": post.comments_set.count(),
        })

    return redirect(request.META.get('HTTP_REFERER', 'explore_pg'))


