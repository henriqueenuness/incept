from django.shortcuts import render
from accounts.models import User, Followers
from .models import Post, Likes, Comments
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404

# Create your views here.
def search_pg(request):
    return render(request, 'feed/search.html')

def cycle_pg(request):
    user = request.user.user_id
    f = Followers.objects.filter(follower_id = user).values_list('user_id', flat=True)
    followings_ids = list(f)
    post = Post.objects.filter(user_id__in = followings_ids)
    #return HttpResponse(", ".join(str(x) for x in followings_ids))
    return render(request, 'feed/cycle.html',
                    {'user' : user,
                   'posts' : post,
                   #'following': list(followings_ids)
                   })

def search_user(request):
    if request.method=="GET":
        search = request.GET.get('search')
        if search:
            users = User.objects.filter(nick__icontains=search)
            users_ids = list(users.values_list("user_id", flat=True))
            #se na lista de seguindo(following) do usuário logado tiver o id do usuário pesquisado, ele mostra "seguindo"
            #else mostra "seguir"

            #1. filtrar o following do usuário logado
            #2. filtrar se o id do usuário buscado está na lista de seguindo do user logado
            followings_ids = Followers.objects.filter(follower_id = request.user.user_id, user_id__in = users_ids).values_list('user_id', flat=True)
        else:
            users = ""
        #return HttpResponse(", ".join(str(x) for x in followings_ids))
        return render(request, 'feed/search.html',
                      {'users' : users,
                       'search' : search,
                       'following': list(followings_ids)})
    
'''def enter_core(request, nick): 
    user = User.objects.get(nick=nick) # pega direto do path
    return render(request, 'users/core/core.html', {'user': user})'''

def like(request, id):
    user = request.user.user_id
    #likes.objects.get(post_id_id=id)
    post = get_object_or_404(Post, id=id)
    if Likes.objects.filter(user=user, post=post).exists():
        Likes.objects.filter(user=user, post=post).delete()
    else:
        Likes.objects.create(post=post, user_id = user) #primeiro o db, dps a variavel python
    return JsonResponse({"likes": post.likes_set.count()})

def comment(request, id):
    user=request.user
    postid =get_object_or_404(Post, id=id)
    content = request.POST.get('comment-content')
    if request.method == 'POST':
        Comments.objects.create(user=user, content=content, post=postid)

    comments = Comments.objects.all()
    post = Post.objects.all()
    return render(request, 'feed/explore.html', {
         "posts": post, 
         "comments" : comments })


