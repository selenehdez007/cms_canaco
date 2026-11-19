import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Archivo, Categoria, Comentario, Publicacion


class HeaderAuthenticationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='selene', password='password123')

    def test_anonymous_header_shows_login_and_registration(self):
        response = self.client.get(reverse('home:index'))

        self.assertContains(response, 'Iniciar sesión')
        self.assertContains(response, 'Registro')
        self.assertNotContains(response, 'Cerrar sesión')

    def test_header_category_menu_shows_saved_categories(self):
        category = Categoria.objects.create(nombre='Educación')

        response = self.client.get(reverse('home:index'))

        self.assertContains(response, category.nombre)
        self.assertContains(
            response,
            reverse('home:categoria_detalle', args=[category.pk]),
        )

    def test_footer_shows_recent_published_news(self):
        published = Publicacion.objects.create(
            titulo='Noticia reciente del footer',
            resumen='Resumen',
            contenido='Contenido',
            estado=Publicacion.ESTADO_PUBLICADO,
        )
        Publicacion.objects.create(
            titulo='Borrador no visible en footer',
            resumen='Resumen',
            contenido='Contenido',
            estado=Publicacion.ESTADO_BORRADOR,
        )

        response = self.client.get(reverse('home:index'))

        self.assertContains(
            response,
            reverse('home:noticia_detalle', args=[published.pk]),
        )
        self.assertContains(response, published.titulo)
        self.assertNotContains(response, 'Borrador no visible en footer')

    def test_footer_shows_only_facebook_social_icon(self):
        response = self.client.get(reverse('home:index'))

        self.assertContains(response, 'aria-label="Facebook"')
        self.assertContains(response, 'class="facebook-social-icon"')
        self.assertNotContains(response, 'icon-instagram')
        self.assertNotContains(response, 'icon-twitter')
        self.assertNotContains(response, 'icon-linkedin')
        self.assertNotContains(response, 'icon-pinterest')
        self.assertNotContains(response, 'icon-dribbble')

    def test_category_page_shows_empty_message_without_sample_article(self):
        response = self.client.get(reverse('home:categoria'))

        self.assertContains(response, 'No hay noticias.')
        self.assertNotContains(response, 'Titulo de la noticia')

    def test_category_page_shows_published_news_and_hides_drafts(self):
        category = Categoria.objects.create(nombre='Tecnología')
        Publicacion.objects.create(
            titulo='Noticia publicada',
            resumen='Resumen publicado',
            contenido='Contenido publicado',
            categoria=category,
            estado=Publicacion.ESTADO_PUBLICADO,
        )
        Publicacion.objects.create(
            titulo='Noticia borrador',
            resumen='Resumen borrador',
            contenido='Contenido borrador',
            categoria=category,
            estado=Publicacion.ESTADO_BORRADOR,
        )

        response = self.client.get(reverse('home:categoria'))

        self.assertContains(response, 'Noticia publicada')
        self.assertNotContains(response, 'Noticia borrador')
        self.assertNotContains(response, 'No hay noticias.')

    def test_category_page_filters_by_selected_category(self):
        selected_category = Categoria.objects.create(nombre='Tecnología')
        other_category = Categoria.objects.create(nombre='Eventos')
        Publicacion.objects.create(
            titulo='Noticia de tecnología',
            resumen='Resumen',
            contenido='Contenido',
            categoria=selected_category,
            estado=Publicacion.ESTADO_PUBLICADO,
        )
        Publicacion.objects.create(
            titulo='Noticia de eventos',
            resumen='Resumen',
            contenido='Contenido',
            categoria=other_category,
            estado=Publicacion.ESTADO_PUBLICADO,
        )

        response = self.client.get(
            reverse('home:categoria'),
            {'categoria': selected_category.pk},
        )

        self.assertContains(response, 'Noticia de tecnología')
        self.assertNotContains(response, 'Noticia de eventos')

    def test_category_detail_route_filters_publications(self):
        category = Categoria.objects.create(nombre='Cultura')
        publication = Publicacion.objects.create(
            titulo='Artículo de cultura',
            resumen='Resumen',
            contenido='Contenido',
            categoria=category,
            estado=Publicacion.ESTADO_PUBLICADO,
        )

        response = self.client.get(
            reverse('home:categoria_detalle', args=[category.pk]),
        )

        self.assertContains(response, publication.titulo)
        self.assertContains(
            response,
            reverse('home:noticia_detalle', args=[publication.pk]),
        )

    def test_login_authenticates_user(self):
        response = self.client.post(reverse('home:login'), {
            'username': 'selene',
            'password': 'password123',
        })

        self.assertRedirects(response, reverse('home:index'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_header_logout_ends_session(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('home:logout'))

        self.assertRedirects(response, reverse('home:login'))
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(self.client.get(reverse('home:index')), 'Iniciar sesión')

    def test_signup_creates_user_and_profile(self):
        response = self.client.post(reverse('home:sign_up'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'apellido_paterno': 'User',
            'apellido_materno': 'Example',
            'password1': 'secure-password-123',
            'password2': 'secure-password-123',
        })

        self.assertRedirects(response, reverse('home:login'))
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertEqual(user.last_name, 'User Example')
        self.assertEqual(user.perfil.apellido_paterno, 'User')
        self.assertEqual(user.perfil.apellido_materno, 'Example')

    def test_signup_rejects_mismatched_passwords(self):
        response = self.client.post(reverse('home:sign_up'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'password-one',
            'password2': 'password-two',
        })

        self.assertRedirects(response, reverse('home:sign_up'))
        self.assertFalse(User.objects.filter(username='newuser').exists())

    def test_profile_edit_updates_user_and_profile_fields(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('home:crud_perfil'), {
            'username': 'selene_updated',
            'email': 'selene@example.com',
            'first_name': 'Selene',
            'apellido_paterno': 'Hernández',
            'apellido_materno': 'López',
        })

        self.assertRedirects(response, reverse('home:perfil'))
        self.user.refresh_from_db()
        self.user.perfil.refresh_from_db()
        self.assertEqual(self.user.username, 'selene_updated')
        self.assertEqual(self.user.email, 'selene@example.com')
        self.assertEqual(self.user.first_name, 'Selene')
        self.assertEqual(self.user.last_name, 'Hernández López')
        self.assertEqual(self.user.perfil.apellido_paterno, 'Hernández')
        self.assertEqual(self.user.perfil.apellido_materno, 'López')

    def test_profile_edit_rejects_another_users_username(self):
        User.objects.create_user(username='another', password='password123')
        self.client.force_login(self.user)

        response = self.client.post(reverse('home:crud_perfil'), {
            'username': 'another',
            'email': '',
            'first_name': '',
            'apellido_paterno': '',
            'apellido_materno': '',
        })

        self.assertRedirects(response, reverse('home:crud_perfil'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'selene')

    def test_profile_edit_page_receives_current_profile(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('home:crud_perfil'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['perfil_usuario'], self.user.perfil)

    def test_profile_edit_saves_uploaded_photo(self):
        self.client.force_login(self.user)
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(reverse('home:crud_perfil'), {
                    'username': 'selene',
                    'email': '',
                    'first_name': '',
                    'apellido_paterno': '',
                    'apellido_materno': '',
                    'foto': SimpleUploadedFile(
                        'avatar.png',
                        b'profile image content',
                        content_type='image/png',
                    ),
                })

                self.assertRedirects(response, reverse('home:perfil'))
                self.user.perfil.refresh_from_db()
                self.assertIsNotNone(self.user.perfil.foto_perfil)
                self.assertTrue(
                    self.user.perfil.foto_perfil.ruta.storage.exists(
                        self.user.perfil.foto_perfil.ruta.name
                    )
                )
                self.assertEqual(Archivo.objects.count(), 1)

    def test_users_panel_creates_missing_profiles_and_lists_users(self):
        another_user = User.objects.create_user(username='another', password='password123')
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)

        response = self.client.get(reverse('home:crud_usuarios'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'another')
        self.assertTrue(hasattr(another_user, 'perfil'))
        self.assertEqual(
            list(response.context['usuarios']),
            list(User.objects.select_related('perfil').order_by('date_joined')),
        )

    def test_admin_can_create_user_from_users_panel_route(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)

        response = self.client.post(reverse('home:crear_usuario'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'apellido_paterno': 'User',
            'apellido_materno': 'Example',
            'rol': 'editor',
            'password1': 'secure-password-123',
            'password2': 'secure-password-123',
        })

        self.assertRedirects(response, reverse('home:crud_usuarios'))
        new_user = User.objects.get(username='newuser')
        self.assertTrue(new_user.is_staff)
        self.assertFalse(new_user.is_superuser)
        self.assertEqual(new_user.perfil.apellido_paterno, 'User')
        self.assertTrue(new_user.check_password('secure-password-123'))

    def test_operator_can_create_publication(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        category = Categoria.objects.create(nombre='Noticias')
        self.client.force_login(self.user)

        response = self.client.post(reverse('home:crear_publicacion'), {
            'titulo': 'Publicación nueva',
            'resumen': 'Resumen nuevo',
            'contenido': '<p>Contenido nuevo</p>',
            'categoria': str(category.pk),
            'estado': Publicacion.ESTADO_PUBLICADO,
        })

        self.assertRedirects(response, reverse('home:crud_noticias'))
        publication = Publicacion.objects.get(titulo='Publicación nueva')
        self.assertEqual(publication.autor, self.user)
        self.assertEqual(publication.categoria, category)
        self.assertEqual(publication.estado, Publicacion.ESTADO_PUBLICADO)

    def test_operator_can_create_publication_with_cover_and_gallery(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse('home:crear_publicacion'),
                    {
                        'titulo': 'Publicación con imágenes',
                        'resumen': 'Resumen',
                        'contenido': '<p>Contenido</p>',
                        'estado': Publicacion.ESTADO_BORRADOR,
                        'imagen_portada': SimpleUploadedFile(
                            'cover.jpg',
                            b'cover image',
                            content_type='image/jpeg',
                        ),
                        'galeria': [
                            SimpleUploadedFile(
                                'gallery.jpg',
                                b'gallery image',
                                content_type='image/jpeg',
                            ),
                        ],
                    },
                )

                self.assertRedirects(response, reverse('home:crud_noticias'))
                publication = Publicacion.objects.get(titulo='Publicación con imágenes')
                self.assertIsNotNone(publication.imagen_portada)
                self.assertEqual(publication.galeria.count(), 1)
                self.assertTrue(
                    publication.imagen_portada.ruta.storage.exists(
                        publication.imagen_portada.ruta.name,
                    )
                )

    def test_operator_can_edit_publication(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)
        publication = Publicacion.objects.create(
            titulo='Título anterior',
            resumen='Resumen anterior',
            contenido='Contenido anterior',
        )

        response = self.client.post(
            reverse('home:editar_publicacion', args=[publication.pk]),
            {
                'titulo': 'Título actualizado',
                'resumen': 'Resumen actualizado',
                'contenido': '<p>Contenido actualizado</p>',
                'categoria': '',
                'estado': Publicacion.ESTADO_BORRADOR,
            },
        )

        self.assertRedirects(response, reverse('home:crud_noticias'))
        publication.refresh_from_db()
        self.assertEqual(publication.titulo, 'Título actualizado')
        self.assertEqual(publication.contenido, '<p>Contenido actualizado</p>')

    def test_publication_edit_get_loads_publication_and_categories(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)
        category = Categoria.objects.create(nombre='Cultura')
        publication = Publicacion.objects.create(
            titulo='Artículo editable',
            resumen='Resumen',
            contenido='Contenido',
            categoria=category,
        )

        response = self.client.get(
            reverse('home:editar_publicacion', args=[publication.pk]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['publicacion'], publication)
        self.assertContains(response, 'Artículo editable')
        self.assertContains(response, 'Cultura')

    def test_operator_can_publish_and_delete_publication(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)
        publication = Publicacion.objects.create(
            titulo='Publicación a moderar',
            resumen='Resumen',
            contenido='Contenido',
        )

        response = self.client.post(
            reverse('home:publicar_publicacion', args=[publication.pk]),
        )

        self.assertRedirects(response, reverse('home:crud_noticias'))
        publication.refresh_from_db()
        self.assertEqual(publication.estado, Publicacion.ESTADO_PUBLICADO)

        response = self.client.post(
            reverse('home:eliminar_publicacion', args=[publication.pk]),
        )

        self.assertRedirects(response, reverse('home:crud_noticias'))
        self.assertFalse(Publicacion.objects.filter(pk=publication.pk).exists())

    def test_publication_detail_shows_published_content_and_approved_comments(self):
        publication = Publicacion.objects.create(
            titulo='Noticia completa',
            resumen='Resumen de la noticia',
            contenido='<p>Contenido de la noticia</p>',
            estado=Publicacion.ESTADO_PUBLICADO,
        )
        approved_comment = Comentario.objects.create(
            publicacion=publication,
            user=self.user,
            contenido='Comentario aprobado visible',
            estado=Comentario.ESTADO_APROBADO,
        )
        Comentario.objects.create(
            publicacion=publication,
            user=self.user,
            contenido='Comentario pendiente oculto',
        )

        response = self.client.get(
            reverse('home:noticia_detalle', args=[publication.pk]),
        )

        self.assertContains(response, publication.titulo)
        self.assertContains(response, 'Contenido de la noticia')
        self.assertContains(response, 'Comentario aprobado visible')
        self.assertNotContains(response, 'Comentario pendiente oculto')
        self.assertEqual(list(response.context['comentarios']), [approved_comment])
        publication.refresh_from_db()
        self.assertEqual(publication.visitas, 1)

    def test_publication_detail_hides_draft_from_regular_users(self):
        publication = Publicacion.objects.create(
            titulo='Borrador privado',
            resumen='Resumen',
            contenido='Contenido',
        )

        response = self.client.get(
            reverse('home:noticia_detalle', args=[publication.pk]),
        )

        self.assertEqual(response.status_code, 404)

    def test_operator_can_view_draft_publication(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)
        publication = Publicacion.objects.create(
            titulo='Borrador de operador',
            resumen='Resumen',
            contenido='Contenido',
        )

        response = self.client.get(
            reverse('home:noticia_detalle', args=[publication.pk]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, publication.titulo)

    def test_news_route_without_id_redirects_home_when_no_publications_exist(self):
        response = self.client.get(reverse('home:noticia'))

        self.assertRedirects(response, reverse('home:index'))

    def test_authenticated_user_comment_is_saved_pending_review(self):
        publication = Publicacion.objects.create(
            titulo='Noticia comentable',
            resumen='Resumen',
            contenido='Contenido',
            estado=Publicacion.ESTADO_PUBLICADO,
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('home:noticia_detalle', args=[publication.pk]),
            {'contenido': 'Comentario nuevo'},
        )

        self.assertRedirects(
            response,
            reverse('home:noticia_detalle', args=[publication.pk]),
        )
        comment = Comentario.objects.get(publicacion=publication)
        self.assertEqual(comment.user, self.user)
        self.assertEqual(comment.estado, Comentario.ESTADO_PENDIENTE)

    def test_anonymous_comment_submission_redirects_to_login(self):
        publication = Publicacion.objects.create(
            titulo='Noticia comentable',
            resumen='Resumen',
            contenido='Contenido',
            estado=Publicacion.ESTADO_PUBLICADO,
        )

        response = self.client.post(
            reverse('home:noticia_detalle', args=[publication.pk]),
            {'contenido': 'Comentario nuevo'},
            follow=True,
        )

        self.assertRedirects(response, reverse('home:login'))
        self.assertContains(response, 'Debes iniciar sesión para comentar.')
        self.assertFalse(Comentario.objects.filter(publicacion=publication).exists())

    def test_admin_can_create_user_without_email(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)

        response = self.client.post(reverse('home:crear_usuario'), {
            'username': 'newuser',
            'password1': 'secure-password-123',
            'password2': 'secure-password-123',
        })

        self.assertRedirects(response, reverse('home:crud_usuarios'))
        new_user = User.objects.get(username='newuser')
        self.assertEqual(new_user.email, '')
        self.assertTrue(new_user.check_password('secure-password-123'))
        self.assertTrue(hasattr(new_user, 'perfil'))

    def test_create_user_route_displays_creation_form(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)

        response = self.client.get(reverse('home:crear_usuario'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home/crear_usuario.html')
        self.assertContains(response, 'Crear una cuenta')

    def test_admin_cannot_create_user_without_username_or_password(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)

        response = self.client.post(reverse('home:crear_usuario'), {
            'username': '',
            'password1': '',
            'password2': '',
        }, follow=True)

        self.assertContains(response, 'Usuario y contraseña son obligatorios.')
        self.assertEqual(User.objects.count(), 1)

    def test_users_panel_renders_action_urls_for_existing_users(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)

        response = self.client.get(reverse('home:crud_usuarios'))

        self.assertContains(response, reverse('home:editar_usuario', args=[self.user.pk]))
        self.assertContains(response, reverse('home:bloquear_usuario', args=[self.user.pk]))
        self.assertContains(response, reverse('home:eliminar_usuario', args=[self.user.pk]))

    def test_operator_can_edit_user_and_profile(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        target = User.objects.create_user(username='target', password='password123')
        self.client.force_login(self.user)

        response = self.client.post(reverse('home:editar_usuario', args=[target.pk]), {
            'username': 'target_updated',
            'email': 'target@example.com',
            'first_name': 'Target',
            'apellido_paterno': 'Family',
            'apellido_materno': 'Name',
            'rol': 'editor',
            'password1': 'new-password-123',
            'password2': 'new-password-123',
        })

        self.assertRedirects(response, reverse('home:crud_usuarios'))
        target.refresh_from_db()
        self.assertEqual(target.username, 'target_updated')
        self.assertEqual(target.last_name, 'Family Name')
        self.assertTrue(target.is_staff)
        self.assertTrue(target.check_password('new-password-123'))
        self.assertEqual(target.perfil.apellido_paterno, 'Family')
        self.assertEqual(target.perfil.apellido_materno, 'Name')

    def test_operator_cannot_block_own_account(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)

        response = self.client.post(reverse('home:bloquear_usuario', args=[self.user.pk]))

        self.assertRedirects(response, reverse('home:crud_usuarios'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_inactive_staff_cannot_access_users_panel(self):
        self.user.is_staff = True
        self.user.is_active = False
        self.user.save(update_fields=['is_staff', 'is_active'])
        self.client.force_login(self.user)

        response = self.client.get(reverse('home:crud_usuarios'))

        self.assertRedirects(
            response,
            f"{reverse('home:login')}?next={reverse('home:crud_usuarios')}",
        )

    def test_operator_can_add_category_and_category_list_is_ordered(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)

        older = Categoria.objects.create(nombre='Primera')
        newer = Categoria.objects.create(nombre='Segunda')
        response = self.client.post(reverse('home:crud_categorias'), {
            'nombre': 'Nueva',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[-1][0], reverse('home:crud_categorias'))
        self.assertContains(response, 'Categoría agregada correctamente.')
        self.assertTrue(Categoria.objects.filter(nombre='Nueva', fk_user=self.user).exists())
        listed = self.client.get(reverse('home:crud_categorias'))
        self.assertEqual(
            list(listed.context['categorias']),
            list(Categoria.objects.order_by('createdat')),
        )
        self.assertLessEqual(older.createdat, newer.createdat)

    def test_category_create_rejects_empty_name(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)

        response = self.client.post(reverse('home:crud_categorias'), {
            'nombre': '   ',
        }, follow=True)

        self.assertContains(response, 'El nombre de la categoría es obligatorio.')
        self.assertEqual(Categoria.objects.count(), 0)

    def test_operator_can_edit_category(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)
        category = Categoria.objects.create(nombre='Anterior')

        response = self.client.post(
            reverse('home:editar_categoria', args=[category.pk]),
            {'nombre': 'Actualizada'},
        )

        self.assertRedirects(response, reverse('home:crud_categorias'))
        category.refresh_from_db()
        self.assertEqual(category.nombre, 'Actualizada')

    def test_operator_can_delete_category(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)
        category = Categoria.objects.create(nombre='Eliminar')

        response = self.client.post(
            reverse('home:eliminar_categoria', args=[category.pk]),
        )

        self.assertRedirects(response, reverse('home:crud_categorias'))
        self.assertFalse(Categoria.objects.filter(pk=category.pk).exists())

    def test_category_ajax_create_edit_and_delete_return_json(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)
        ajax_headers = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        created = self.client.post(
            reverse('home:crud_categorias'),
            {'nombre': 'Nueva'},
            **ajax_headers,
        )
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()['categoria']['nombre'], 'Nueva')
        category_id = created.json()['categoria']['id']

        updated = self.client.post(
            reverse('home:editar_categoria', args=[category_id]),
            {'nombre': 'Actualizada'},
            **ajax_headers,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['categoria']['nombre'], 'Actualizada')

        deleted = self.client.post(
            reverse('home:eliminar_categoria', args=[category_id]),
            **ajax_headers,
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertTrue(deleted.json()['success'])
        self.assertFalse(Categoria.objects.filter(pk=category_id).exists())

    def test_category_ajax_rejects_empty_name(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('home:crud_categorias'),
            {'nombre': '   '},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['message'],
            'El nombre de la categoría es obligatorio.',
        )
        self.assertEqual(Categoria.objects.count(), 0)

    def test_operator_comments_panel_lists_comments_with_related_data(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)
        publication = Publicacion.objects.create(
            titulo='Publicación de prueba',
            resumen='Resumen',
            contenido='Contenido',
        )
        comment = Comentario.objects.create(
            publicacion=publication,
            user=self.user,
            contenido='Comentario de prueba',
        )

        response = self.client.get(reverse('home:crud_comentarios'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Comentario de prueba')
        self.assertContains(response, 'Publicación de prueba')
        self.assertEqual(list(response.context['comentarios']), [comment])

    def test_operator_can_approve_comment(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)
        publication = Publicacion.objects.create(
            titulo='Publicación',
            resumen='Resumen',
            contenido='Contenido',
        )
        comment = Comentario.objects.create(
            publicacion=publication,
            user=self.user,
            contenido='Comentario',
        )

        response = self.client.post(
            reverse('home:aprobar_comentario', args=[comment.pk]),
        )

        self.assertRedirects(response, reverse('home:crud_comentarios'))
        comment.refresh_from_db()
        self.assertEqual(comment.estado, Comentario.ESTADO_APROBADO)

    def test_operator_can_block_comment(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)
        publication = Publicacion.objects.create(
            titulo='Publicación',
            resumen='Resumen',
            contenido='Contenido',
        )
        comment = Comentario.objects.create(
            publicacion=publication,
            user=self.user,
            contenido='Comentario',
        )

        response = self.client.post(
            reverse('home:bloquear_comentario', args=[comment.pk]),
        )

        self.assertRedirects(response, reverse('home:crud_comentarios'))
        comment.refresh_from_db()
        self.assertEqual(comment.estado, Comentario.ESTADO_BLOQUEADO)

    def test_operator_can_delete_comment(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)
        publication = Publicacion.objects.create(
            titulo='Publicación',
            resumen='Resumen',
            contenido='Contenido',
        )
        comment = Comentario.objects.create(
            publicacion=publication,
            user=self.user,
            contenido='Comentario',
        )

        response = self.client.post(
            reverse('home:eliminar_comentario', args=[comment.pk]),
        )

        self.assertRedirects(response, reverse('home:crud_comentarios'))
        self.assertFalse(Comentario.objects.filter(pk=comment.pk).exists())

    def test_regular_user_cannot_access_users_panel(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('home:crud_usuarios'))

        self.assertRedirects(
            response,
            f"{reverse('home:login')}?next={reverse('home:crud_usuarios')}",
        )

    def test_password_change_updates_password_and_keeps_user_logged_in(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('home:crud_cambiar_contrasena'), {
            'actual': 'password123',
            'nueva': 'new-password-123',
            'confirmar': 'new-password-123',
        })

        self.assertRedirects(response, reverse('home:crud_cambiar_contrasena'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('new-password-123'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_password_change_rejects_incorrect_current_password(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('home:crud_cambiar_contrasena'), {
            'actual': 'incorrect-password',
            'nueva': 'new-password-123',
            'confirmar': 'new-password-123',
        }, follow=True)

        self.assertContains(response, 'La contraseña actual es incorrecta.')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('password123'))

    def test_password_change_rejects_unconfirmed_new_password(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('home:crud_cambiar_contrasena'), {
            'actual': 'password123',
            'nueva': 'new-password-123',
            'confirmar': 'different-password',
        }, follow=True)

        self.assertContains(response, 'Las nuevas contraseñas no coinciden.')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('password123'))
