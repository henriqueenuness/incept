from django.contrib import admin
from django.urls import path

from accounts import views as accounts_views
from feed import views as feed_views


urlpatterns = [
    path("", accounts_views.home, name="home"),
    path("signup/", accounts_views.signup_pg, name="signup_pg"),
    path("signup/auth/", accounts_views.signup, name="signup"),
    path("login/", accounts_views.login_pg, name="login_pg"),
    path("login/auth/", accounts_views.login_auth, name="login"),
    path("logout/", accounts_views.make_logout, name="logout"),
    path("core/new-post/<str:nick>/", accounts_views.new_post_pg, name="new_post_pg"),
    path("core/new-post/post", accounts_views.new_post, name="new_post"),
    path("core/post/delete/<str:id>", accounts_views.delete_post, name="delete_post"),
    path("explore/", accounts_views.explore_pg, name="explore_pg"),
    path("explore/like-post/<id>/", feed_views.like, name="like"),
    path("search/", feed_views.search_pg, name="search_pg"),
    path("cycle/", feed_views.cycle_pg, name="cycle_pg"),
    path("explore/comment/<id>", feed_views.comment, name="comment"),
    path("explore/comment/<id>/list", feed_views.comments_api, name="comments_api"),
    path("explore/search/", feed_views.search_user, name="search_user"),
    path("core/edit-core/", accounts_views.edit_core_pg, name="edit_core_pg"),
    path("delete-account/", accounts_views.delete_account, name="delete_account"),
    path("delete/core-picture/", accounts_views.delete_core_picture, name="delete_core_picture"),
    path("core/edit-core/post", accounts_views.edit_core, name="edit_core"),
    path("core/<str:nick>/", accounts_views.core_pg, name="core_pg"),
    path("core/follow/<id>/", accounts_views.follow, name="follow"),
    path("admin/", admin.site.urls),
]
