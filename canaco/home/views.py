from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import (
    Archivo,
    Categoria,
    Comentario,
    GaleriaPublicacion,
    Perfil,
    Publicacion,
)


def es_operador(user):
    return user.is_authenticated and user.is_staff and user.is_active


operador_required = user_passes_test(es_operador)


# Create your views here.
def index(request): 
    publicaciones = Publicacion.objects.filter(
        estado=Publicacion.ESTADO_PUBLICADO,
    ).select_related('categoria', 'imagen_portada').order_by('-createdat')
    return render(request, 'home/index.html', {
        'noticias_destacadas': publicaciones[:3],
        'noticias': publicaciones[:6],
    })


def base_view(request):
    return render(request, 'home/base.html')

def contactanos_view(request):
    return render(request, 'home/contactanos.html')

def categoria(request, pk=None):
    categorias = Categoria.objects.order_by('nombre')
    categoria_id = str(pk) if pk is not None else request.GET.get('categoria')
    categoria_seleccionada = None
    if categoria_id and categoria_id.isdecimal():
        categoria_seleccionada = categorias.filter(pk=int(categoria_id)).first()
        if pk is not None and categoria_seleccionada is None:
            get_object_or_404(Categoria, pk=pk)
    publicaciones = Publicacion.objects.filter(
        estado=Publicacion.ESTADO_PUBLICADO,
    ).select_related('categoria', 'imagen_portada').order_by('-createdat')

    if categoria_seleccionada:
        publicaciones = publicaciones.filter(categoria=categoria_seleccionada)

    return render(request, 'home/categoria.html', {
        'categorias': categorias,
        'categoria_seleccionada': categoria_seleccionada,
        'publicaciones': publicaciones,
    })

def noticia(request, pk=None):
    if es_operador(request.user):
        publicaciones = Publicacion.objects.all()
    else:
        publicaciones = Publicacion.objects.filter(
            estado=Publicacion.ESTADO_PUBLICADO,
        )
    publicaciones = publicaciones.select_related(
        'categoria',
        'autor',
        'imagen_portada',
    )
    publicacion = (
        get_object_or_404(publicaciones, pk=pk)
        if pk is not None
        else publicaciones.order_by('-createdat').first()
    )

    if not publicacion:
        messages.info(request, 'Todavía no hay noticias publicadas.')
        return redirect('home:index')

    Publicacion.objects.filter(pk=publicacion.pk).update(visitas=F('visitas') + 1)
    publicacion.refresh_from_db()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'Debes iniciar sesión para comentar.')
            return redirect('home:login')

        contenido = request.POST.get('contenido', '').strip()
        if contenido:
            Comentario.objects.create(
                publicacion=publicacion,
                user=request.user,
                contenido=contenido,
            )
            messages.success(
                request,
                'Comentario enviado. Será visible cuando lo apruebe el administrador.',
            )
            return redirect('home:noticia_detalle', pk=publicacion.pk)

    recientes = Publicacion.objects.filter(
        estado=Publicacion.ESTADO_PUBLICADO,
    ).exclude(
        pk=publicacion.pk,
    ).select_related(
        'imagen_portada',
    ).order_by('-createdat')[:4]
    comentarios = publicacion.comentarios.filter(
        estado=Comentario.ESTADO_APROBADO,
    ).select_related('user').order_by('-createdat')
    categorias = Categoria.objects.order_by('nombre')

    return render(request, 'home/noticia.html', {
        'publicacion': publicacion,
        'recientes': recientes,
        'comentarios': comentarios,
        'categorias': categorias,
    })
@login_required
def perfil_view(request):
    perfil_usuario, _ = Perfil.objects.get_or_create(user=request.user)
    return render(request, 'home/perfil.html', {'perfil_usuario': perfil_usuario})

def sign_up_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        apellido_paterno = request.POST.get('apellido_paterno', '').strip()
        apellido_materno = request.POST.get('apellido_materno', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if not username or not email or not password1 or not password2:
            messages.error(request, 'Completa todos los campos obligatorios.')
            return redirect('home:sign_up')

        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('home:sign_up')

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, 'El nombre de usuario ya está en uso.')
            return redirect('home:sign_up')

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, 'El correo electrónico ya está registrado.')
            return redirect('home:sign_up')

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=' '.join(filter(None, [apellido_paterno, apellido_materno])),
            )
            perfil, _ = Perfil.objects.get_or_create(user=user)
            perfil.apellido_paterno = apellido_paterno
            perfil.apellido_materno = apellido_materno
            perfil.save()

        messages.success(request, 'Tu cuenta se creó correctamente. Ahora puedes iniciar sesión.')
        return redirect('home:login')

    return render(request, 'home/sign_up.html')

@operador_required
def crear_publicacion(request):
    categorias = Categoria.objects.all().order_by('nombre')
    if request.method == 'POST':
        return _guardar_publicacion(request)
    return render(request, 'home/crear_publicacion.html', {
        'categorias': categorias,
    })


def guardar_archivo(upload, user):
    return Archivo.objects.create(
        nombre=upload.name,
        nombre_temporal=upload.name,
        ruta=upload,
        tipo=upload.content_type or '',
        tamano=upload.size,
        fk_user=user,
    )


def _guardar_publicacion(request, publicacion=None):
    titulo = request.POST.get('titulo', '').strip()
    resumen = request.POST.get('resumen', '').strip()
    contenido = request.POST.get('contenido', '').strip()
    categoria_id = request.POST.get('categoria', '').strip()
    estado = request.POST.get('estado', Publicacion.ESTADO_BORRADOR)
    editar = publicacion is not None
    formulario_url = 'home:editar_publicacion' if editar else 'home:crear_publicacion'
    formulario_args = [publicacion.pk] if editar else []

    if not titulo or not resumen or not contenido:
        messages.error(request, 'Completa el título, resumen y contenido.')
        return redirect(formulario_url, *formulario_args)

    categoria = None
    if categoria_id:
        if not categoria_id.isdecimal():
            messages.error(request, 'Selecciona una categoría válida.')
            return redirect(formulario_url, *formulario_args)
        categoria = Categoria.objects.filter(pk=int(categoria_id)).first()
        if categoria is None:
            messages.error(request, 'La categoría seleccionada no existe.')
            return redirect(formulario_url, *formulario_args)

    if estado not in {value for value, _ in Publicacion.ESTADOS}:
        messages.error(request, 'Selecciona un estado válido.')
        return redirect(formulario_url, *formulario_args)

    with transaction.atomic():
        if publicacion is None:
            publicacion = Publicacion(autor=request.user)
        publicacion.titulo = titulo
        publicacion.resumen = resumen
        publicacion.contenido = contenido
        publicacion.categoria = categoria
        publicacion.estado = estado
        publicacion.save()

        imagen_portada = request.FILES.get('imagen_portada')
        if imagen_portada:
            publicacion.imagen_portada = guardar_archivo(imagen_portada, request.user)
            publicacion.save(update_fields=['imagen_portada', 'updatedat'])

        for imagen in request.FILES.getlist('galeria'):
            archivo = guardar_archivo(imagen, request.user)
            GaleriaPublicacion.objects.create(
                publicacion=publicacion,
                archivo=archivo,
            )

    messages.success(
        request,
        'Publicación actualizada correctamente.' if editar
        else 'Publicación creada correctamente.',
    )
    return redirect('home:crud_noticias')


@operador_required
def editar_publicacion(request, pk):
    publicacion = get_object_or_404(Publicacion, pk=pk)
    if request.method == 'POST':
        return _guardar_publicacion(request, publicacion)

    return render(request, 'home/crear_publicacion.html', {
        'publicacion': publicacion,
        'categorias': Categoria.objects.order_by('nombre'),
    })


@operador_required
def publicar_publicacion(request, pk):
    if request.method != 'POST':
        return redirect('home:crud_noticias')

    publicacion = get_object_or_404(Publicacion, pk=pk)
    if publicacion.estado != Publicacion.ESTADO_PUBLICADO:
        publicacion.estado = Publicacion.ESTADO_PUBLICADO
        mensaje = 'Publicación publicada correctamente.'
    else:
        publicacion.estado = Publicacion.ESTADO_BORRADOR
        mensaje = 'Publicación ocultada correctamente.'
    publicacion.save(update_fields=['estado', 'updatedat'])
    messages.success(request, mensaje)
    return redirect('home:crud_noticias')


@operador_required
def eliminar_publicacion(request, pk):
    if request.method == 'POST':
        publicacion = get_object_or_404(Publicacion, pk=pk)
        publicacion.delete()
        messages.success(request, 'Publicación eliminada correctamente.')
    return redirect('home:crud_noticias')

@operador_required
def crear_usuario_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        apellido_paterno = request.POST.get('apellido_paterno', '').strip()
        apellido_materno = request.POST.get('apellido_materno', '').strip()
        rol = request.POST.get('rol', 'colaborador')
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if not username or not password1:
            messages.error(request, 'Usuario y contraseña son obligatorios.')
            return redirect('home:crear_usuario')

        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('home:crear_usuario')

        if rol not in {'colaborador', 'editor', 'administrador'}:
            messages.error(request, 'Selecciona un rol válido.')
            return redirect('home:crear_usuario')

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, 'El nombre de usuario ya está en uso.')
            return redirect('home:crear_usuario')

        if email and User.objects.filter(email__iexact=email).exists():
            messages.error(request, 'El correo electrónico ya está registrado.')
            return redirect('home:crear_usuario')

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
            )
            user.first_name = first_name
            user.last_name = ' '.join(filter(None, [apellido_paterno, apellido_materno]))
            user.is_staff = rol in {'editor', 'administrador'}
            user.is_superuser = rol == 'administrador'
            user.save()

            perfil, _ = Perfil.objects.get_or_create(user=user)
            perfil.apellido_paterno = apellido_paterno
            perfil.apellido_materno = apellido_materno
            perfil.save()

        messages.success(request, 'Usuario creado correctamente.')
        return redirect('home:crud_usuarios')

    return render(request, 'home/crear_usuario.html')

@login_required
def crud_cambiar_contrasena_view(request):
    if request.method == 'POST':
        actual = request.POST.get('actual', '')
        nueva = request.POST.get('nueva', '')
        confirmar = request.POST.get('confirmar', '')
        user = request.user

        if not user.check_password(actual):
            messages.error(request, 'La contraseña actual es incorrecta.')
            return redirect('home:crud_cambiar_contrasena')

        if nueva != confirmar:
            messages.error(request, 'Las nuevas contraseñas no coinciden.')
            return redirect('home:crud_cambiar_contrasena')

        user.set_password(nueva)
        user.save()
        update_session_auth_hash(request, user)

        messages.success(request, 'Contraseña actualizada correctamente.')
        return redirect('home:crud_cambiar_contrasena')

    return render(request, 'home/crud_cambiar_contrasena.html')

@operador_required
def crud_categorias_view(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if nombre:
            categoria = Categoria.objects.create(nombre=nombre, fk_user=request.user)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Categoría agregada correctamente.',
                    'categoria': _categoria_ajax_data(categoria),
                })
            messages.success(request, 'Categoría agregada correctamente.')
            return redirect('home:crud_categorias')

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'El nombre de la categoría es obligatorio.',
            }, status=400)
        messages.error(request, 'El nombre de la categoría es obligatorio.')

    categorias = Categoria.objects.select_related('fk_user').order_by('createdat')
    return render(request, 'home/crud_categorias.html', {'categorias': categorias})

@operador_required
def crud_comentarios_view(request):
    comentarios = Comentario.objects.select_related(
        'publicacion',
        'user',
    ).order_by('-createdat')
    return render(request, 'home/crud_comentarios.html', {'comentarios': comentarios})


@operador_required
def aprobar_comentario(request, pk):
    if request.method == 'POST':
        comentario = get_object_or_404(Comentario, pk=pk)
        comentario.estado = Comentario.ESTADO_APROBADO
        comentario.save()
        messages.success(request, 'Comentario aprobado correctamente.')
    return redirect('home:crud_comentarios')


@operador_required
def bloquear_comentario(request, pk):
    if request.method == 'POST':
        comentario = get_object_or_404(Comentario, pk=pk)
        comentario.estado = Comentario.ESTADO_BLOQUEADO
        comentario.save()
        messages.success(request, 'Comentario bloqueado correctamente.')
    return redirect('home:crud_comentarios')


@operador_required
def eliminar_comentario(request, pk):
    if request.method == 'POST':
        comentario = get_object_or_404(Comentario, pk=pk)
        comentario.delete()
        messages.success(request, 'Comentario eliminado correctamente.')
    return redirect('home:crud_comentarios')

@login_required
def crud_noticias_view(request):
    publicaciones = Publicacion.objects.select_related(
        'autor',
        'categoria',
    ).order_by('-createdat')
    return render(request, 'home/crud_noticias.html', {
        'publicaciones': publicaciones,
    })

@login_required
def crud_perfil_view(request):
    perfil_usuario, _ = Perfil.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        apellido_paterno = request.POST.get('apellido_paterno', '').strip()
        apellido_materno = request.POST.get('apellido_materno', '').strip()
        foto = request.FILES.get('foto')

        if not username:
            messages.error(request, 'El nombre de usuario es obligatorio.')
            return redirect('home:crud_perfil')

        if User.objects.filter(username__iexact=username).exclude(pk=request.user.pk).exists():
            messages.error(request, 'Ese nombre de usuario ya está en uso.')
            return redirect('home:crud_perfil')

        if email and User.objects.filter(email__iexact=email).exclude(pk=request.user.pk).exists():
            messages.error(request, 'Ese correo electrónico ya está registrado.')
            return redirect('home:crud_perfil')

        with transaction.atomic():
            user = request.user
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = ' '.join(filter(None, [apellido_paterno, apellido_materno]))
            user.save()

            perfil_usuario.apellido_paterno = apellido_paterno
            perfil_usuario.apellido_materno = apellido_materno

            if foto:
                archivo_foto = Archivo.objects.create(
                    nombre=foto.name,
                    nombre_temporal=foto.name,
                    ruta=foto,
                    tipo=foto.content_type or '',
                    tamano=foto.size,
                    fk_user=user,
                )
                perfil_usuario.foto_perfil = archivo_foto

            perfil_usuario.save()

        messages.success(request, 'Perfil actualizado correctamente.')
        return redirect('home:perfil')

    return render(request, 'home/crud_perfil.html', {'perfil_usuario': perfil_usuario})

@operador_required
def crud_usuarios_view(request):
    for usuario in User.objects.all():
        Perfil.objects.get_or_create(user=usuario)

    usuarios = User.objects.select_related('perfil').order_by('date_joined')
    return render(request, 'home/crud_usuarios.html', {'usuarios': usuarios})


@operador_required
def editar_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    perfil, _ = Perfil.objects.get_or_create(user=usuario)

    if request.method == 'POST':
        username = request.POST.get('username', usuario.username).strip()
        email = request.POST.get('email', usuario.email).strip()
        first_name = request.POST.get('first_name', usuario.first_name).strip()
        apellido_paterno = request.POST.get(
            'apellido_paterno',
            perfil.apellido_paterno,
        ).strip()
        apellido_materno = request.POST.get(
            'apellido_materno',
            perfil.apellido_materno,
        ).strip()
        rol = request.POST.get('rol')
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if not username or not email:
            messages.error(request, 'El usuario y el correo son obligatorios.')
            return redirect('home:editar_usuario', pk=usuario.pk)

        if User.objects.filter(username__iexact=username).exclude(pk=usuario.pk).exists():
            messages.error(request, 'El nombre de usuario ya está en uso.')
            return redirect('home:editar_usuario', pk=usuario.pk)

        if User.objects.filter(email__iexact=email).exclude(pk=usuario.pk).exists():
            messages.error(request, 'El correo electrónico ya está registrado.')
            return redirect('home:editar_usuario', pk=usuario.pk)

        if rol and rol not in {'colaborador', 'editor', 'administrador'}:
            messages.error(request, 'Selecciona un rol válido.')
            return redirect('home:editar_usuario', pk=usuario.pk)

        if (password1 or password2) and password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('home:editar_usuario', pk=usuario.pk)

        with transaction.atomic():
            usuario.username = username
            usuario.email = email
            usuario.first_name = first_name
            perfil.apellido_paterno = apellido_paterno
            perfil.apellido_materno = apellido_materno
            usuario.last_name = ' '.join(filter(None, [
                perfil.apellido_paterno,
                perfil.apellido_materno,
            ]))
            if rol:
                usuario.is_staff = rol in {'editor', 'administrador'}
                usuario.is_superuser = rol == 'administrador'
            if password1:
                usuario.set_password(password1)
            usuario.save()
            perfil.save()

        messages.success(request, 'Usuario actualizado correctamente.')
        return redirect('home:crud_usuarios')

    return render(request, 'home/crear_usuario.html', {
        'usuario_editado': usuario,
        'perfil_editado': perfil,
    })


@operador_required
def bloquear_usuario(request, pk):
    if request.method != 'POST':
        return redirect('home:crud_usuarios')

    usuario = get_object_or_404(User, pk=pk)
    if usuario == request.user:
        messages.error(request, 'No puedes bloquear tu propia cuenta.')
        return redirect('home:crud_usuarios')

    usuario.is_active = not usuario.is_active
    usuario.save(update_fields=['is_active'])
    messages.success(request, 'Estado del usuario actualizado.')
    return redirect('home:crud_usuarios')


@operador_required
def eliminar_usuario(request, pk):
    if request.method != 'POST':
        return redirect('home:crud_usuarios')

    usuario = get_object_or_404(User, pk=pk)
    if usuario == request.user:
        messages.error(request, 'No puedes eliminar tu propia cuenta desde este panel.')
        return redirect('home:crud_usuarios')

    usuario.delete()
    messages.success(request, 'Usuario eliminado correctamente.')
    return redirect('home:crud_usuarios')

@operador_required
def editar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if nombre:
            categoria.nombre = nombre
            categoria.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Categoría actualizada correctamente.',
                    'categoria': _categoria_ajax_data(categoria),
                })
            messages.success(request, 'Categoría actualizada correctamente.')
            return redirect('home:crud_categorias')

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'El nombre de la categoría es obligatorio.',
            }, status=400)
        messages.error(request, 'El nombre de la categoría es obligatorio.')

    return render(request, 'home/editar_categoria.html', {'categoria': categoria})


@operador_required
def eliminar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Categoría eliminada correctamente.',
            })
        messages.success(request, 'Categoría eliminada correctamente.')
    return redirect('home:crud_categorias')


def _categoria_ajax_data(categoria):
    fecha = (
        timezone.localtime(categoria.createdat).strftime('%Y-%m-%d %H:%M')
        if categoria.createdat else ''
    )
    return {
        'id': categoria.pk,
        'nombre': categoria.nombre,
        'usuario': categoria.fk_user.username if categoria.fk_user else '-',
        'fecha': fecha,
        'edit_url': reverse('home:editar_categoria', args=[categoria.pk]),
        'delete_url': reverse('home:eliminar_categoria', args=[categoria.pk]),
    }