from django.shortcuts import render
from signin.models import User

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
    
def enter_core(request, nick): 
    user = User.objects.get(nick=nick) # pega direto do path
    return render(request, 'users/core/core.html', {'user': user})

