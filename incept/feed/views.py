from django.shortcuts import render
from accounts.models import User
from .models import Post, Likes, Comments
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

# Create your views here.

def search_user(request):
    if request.method=="GET":
        search = request.GET.get('search')
        if search:
            users = User.objects.filter(nick__icontains=search)
        else:
            users = ""
        return render(request, 'feed/explore.html',
                      {'users' : users,
                       'search' : search})
    
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
    return HttpResponse("")

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


