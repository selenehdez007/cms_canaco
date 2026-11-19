from django.urls import path 
from django.contrib.auth import views as auth_views
from . import views  
 
app_name = "home" 
 
urlpatterns = [  
    path('', views.index, name='index'),
    path('contactanos/', views.contactanos_view, name='contactanos'),
    path('categoria/', views.categoria, name='categoria'),
    path('categoria/<int:pk>/', views.categoria, name='categoria_detalle'),
    path('login/', auth_views.LoginView.as_view(template_name='home/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home:login'), name='logout'),
    path('noticia/', views.noticia, name='noticia'),
    path('noticia/<int:pk>/', views.noticia, name='noticia_detalle'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('sign-up/', views.sign_up_view, name='sign_up'),
    path('crear-publicacion/', views.crear_publicacion, name='crear_publicacion'),
    path('crud_noticias/<int:pk>/editar', views.editar_publicacion, name='editar_publicacion'),
    path('crud_noticias/<int:pk>/publicar', views.publicar_publicacion, name='publicar_publicacion'),
    path('crud_noticias/<int:pk>/eliminar', views.eliminar_publicacion, name='eliminar_publicacion'),
    path('crud_usuarios/crear/', views.crear_usuario_view, name='crear_usuario'),
    path('crud/cambiar-contrasena/', views.crud_cambiar_contrasena_view, name='crud_cambiar_contrasena'),
    path('crud/categorias/', views.crud_categorias_view, name='crud_categorias'),
    path('crud/comentarios/', views.crud_comentarios_view, name='crud_comentarios'),
    path("crud_comentarios/<int:pk>/aprobar", views.aprobar_comentario, name="aprobar_comentario"),
    path("crud_comentarios/<int:pk>/bloquear", views.bloquear_comentario, name="bloquear_comentario"),
    path("crud_comentarios/<int:pk>/eliminar", views.eliminar_comentario, name="eliminar_comentario"),
    path('crud/noticias/', views.crud_noticias_view, name='crud_noticias'),
    path('crud/perfil/', views.crud_perfil_view, name='crud_perfil'),
    path('crud/usuarios/', views.crud_usuarios_view, name='crud_usuarios'),
    path('crud_usuarios/editar/<int:pk>/', views.editar_usuario, name='editar_usuario'),
    path('crud_usuarios/bloquear/<int:pk>/', views.bloquear_usuario, name='bloquear_usuario'),
    path('crud_usuarios/eliminar/<int:pk>/', views.eliminar_usuario, name='eliminar_usuario'),
    path('crud_categorias/<int:pk>/editar/', views.editar_categoria, name='editar_categoria'),
    path('crud_categorias/<int:pk>/eliminar/', views.eliminar_categoria, name='eliminar_categoria'),
]