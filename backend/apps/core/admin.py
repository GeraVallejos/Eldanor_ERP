from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django import forms
from apps.core.exceptions import AppError
from .models import Empresa, UserEmpresa, RolUsuario
from .tenant import set_current_empresa, set_current_user
from apps.inventario.models import Bodega

User = get_user_model()


class CustomUserCreationAdminForm(UserCreationForm):
    rol_empresa = forms.ChoiceField(
        label='Rol en empresa activa',
        choices=RolUsuario.choices,
        required=False,
        initial=RolUsuario.VENDEDOR,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = '__all__'


class CustomUserChangeAdminForm(UserChangeForm):
    rol_empresa = forms.ChoiceField(
        label='Rol en empresa activa',
        choices=RolUsuario.choices,
        required=False,
    )

    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance or not self.instance.pk:
            return

        empresa = getattr(self.instance, 'empresa_activa', None)
        if not empresa:
            return

        relacion = (
            self.instance.empresas_rel
            .filter(empresa=empresa)
            .first()
        )
        if relacion:
            self.fields['rol_empresa'].initial = relacion.rol


class UserEmpresaInline(admin.TabularInline):
    model = UserEmpresa
    fk_name = 'user'
    extra = 0
    fields = ('empresa', 'rol', 'activo')
    autocomplete_fields = ('empresa',)
    verbose_name = 'Relacion empresa'
    verbose_name_plural = 'Relaciones por empresa'

    def has_view_or_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class BodegaInline(admin.TabularInline):
    model = Bodega
    extra = 1
    fields = ('nombre', 'activa')
    verbose_name = 'Bodega'
    verbose_name_plural = 'Bodegas'

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'nombre' and formfield and formfield.widget:
            formfield.widget.attrs.setdefault('placeholder', 'Principal')
            formfield.help_text = 'Sugerencia: Principal'
        return formfield

    def has_view_or_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class BulkImportUploadForm(forms.Form):
    file = forms.FileField(help_text='Formato permitido: CSV o XLSX (max 2 MB).')


class BulkImportAdminMixin:
    bulk_import_title = 'Carga masiva'

    def get_bulk_import_url_name(self):
        opts = self.model._meta
        return f'admin:{opts.app_label}_{opts.model_name}_bulk_import'

    def get_bulk_import_url(self):
        return reverse(self.get_bulk_import_url_name())

    def get_bulk_template_url_name(self):
        opts = self.model._meta
        return f'admin:{opts.app_label}_{opts.model_name}_bulk_template'

    def get_bulk_template_url(self):
        return reverse(self.get_bulk_template_url_name())

    def get_bulk_import_button_label(self):
        return self.bulk_import_title

    def get_urls(self):
        urls = super().get_urls()
        opts = self.model._meta
        custom_urls = [
            path(
                'bulk-import/',
                self.admin_site.admin_view(self.bulk_import_view),
                name=f'{opts.app_label}_{opts.model_name}_bulk_import',
            ),
            path(
                'bulk-template/',
                self.admin_site.admin_view(self.bulk_template_view),
                name=f'{opts.app_label}_{opts.model_name}_bulk_template',
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['bulk_import_url'] = self.get_bulk_import_url()
        extra_context['bulk_template_url'] = self.get_bulk_template_url()
        extra_context['bulk_import_button_label'] = self.get_bulk_import_button_label()
        return super().changelist_view(request, extra_context=extra_context)

    def bulk_template_view(self, request):
        if not self.has_change_permission(request):
            raise PermissionDenied

        content, filename = self.handle_bulk_template(request)
        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def bulk_import_view(self, request):
        if not self.has_change_permission(request):
            raise PermissionDenied

        if request.method == 'POST':
            form = BulkImportUploadForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    result = self.handle_bulk_import(request, form.cleaned_data['file'])
                except AppError as exc:
                    messages.error(request, str(exc))
                    return HttpResponseRedirect(request.path)

                created = result.get('created', 0)
                updated = result.get('updated', 0)
                successful_rows = result.get('successful_rows', created + updated)
                errors = result.get('errors') or []

                if successful_rows > 0:
                    messages.success(
                        request,
                        f'Carga finalizada: {created} creados, {updated} actualizados.',
                    )

                if errors:
                    first_error = errors[0]
                    error_text = (
                        f'Se detectaron {len(errors)} errores. '
                        f'Primera fila con error (linea {first_error.get("line", "-")}): '
                        f'{first_error.get("detail", "Error desconocido")}'
                    )
                    if successful_rows > 0:
                        messages.warning(request, error_text)
                    else:
                        messages.error(request, error_text)

                if successful_rows == 0 and not errors:
                    messages.info(request, 'El archivo no contenia filas para procesar.')

                return HttpResponseRedirect(reverse(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist'))
        else:
            form = BulkImportUploadForm()

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'form': form,
            'title': f'{self.bulk_import_title} - {self.model._meta.verbose_name_plural}',
            'back_url': reverse(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist'),
            'bulk_template_url': self.get_bulk_template_url(),
        }
        return TemplateResponse(request, 'admin/bulk_import_form.html', context)

    def handle_bulk_import(self, request, uploaded_file):
        raise NotImplementedError('Debe implementar handle_bulk_import en el ModelAdmin.')

    def handle_bulk_template(self, request):
        raise NotImplementedError('Debe implementar handle_bulk_template en el ModelAdmin.')

class TenantAdminMixin:
    def _resolve_empresa_for_user(self, user):
        if getattr(user, 'empresa_activa', None):
            return user.empresa_activa

        relacion = (
            user.empresas_rel.filter(activo=True)
            .select_related('empresa')
            .first()
        )

        if not relacion:
            return None

        user.empresa_activa = relacion.empresa
        user.save(update_fields=['empresa_activa'])
        return relacion.empresa

    def get_queryset(self, request):
        # Usamos el queryset estándar del Admin
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        empresa_activa = self._resolve_empresa_for_user(request.user)
        if not empresa_activa:
            return qs.none()

        # Filtrar Contacto, Producto, Categoria, etc.
        if hasattr(self.model, 'empresa'):
            return qs.filter(empresa=empresa_activa)
        
        # Filtrar Cliente, Proveedor
        if hasattr(self.model, 'contacto'):
            return qs.filter(contacto__empresa=empresa_activa)
        
        return qs
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            # En lugar de agregar 'empresa', agregamos el nombre del método que crearemos abajo
            if hasattr(self.model, 'empresa'):
                if 'empresa' in readonly: readonly.remove('empresa') # Quitamos el original
                readonly.append('show_empresa_text')
            
            if hasattr(self.model, 'creado_por'):
                if 'creado_por' in readonly: readonly.remove('creado_por')
                readonly.append('show_creado_por_text')
        return readonly

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if not request.user.is_superuser:
            # Creamos una lista limpia
            clean_fields = []
            for f in fields:
                # Si es el campo real, lo ignoramos (porque ya usaremos el 'show_..._text')
                if f in ['empresa', 'creado_por']:
                    continue
                # Si es una de nuestras funciones 'get_...' manuales antiguas, las quitamos
                if str(f).startswith('get_empresa') or str(f).startswith('get_creado'):
                    continue
                clean_fields.append(f)
            return clean_fields
        return fields

    # Métodos para mostrar solo TEXTO sin LINK
    def show_empresa_text(self, obj):
        return obj.empresa.nombre if obj and obj.empresa else "-"
    show_empresa_text.short_description = "Empresa"

    def show_creado_por_text(self, obj):
        return obj.creado_por.username if obj and obj.creado_por else "-"
    show_creado_por_text.short_description = "Creado por"

    def save_model(self, request, obj, form, change):
        if hasattr(obj, 'empresa'):
            empresa_obj = None

            if request.user.is_superuser:
                empresa_obj = getattr(obj, 'empresa', None)
            else:
                empresa_obj = self._resolve_empresa_for_user(request.user)

                if not empresa_obj:
                    raise ValidationError(
                        'Tu usuario no tiene empresa activa. Configura una empresa activa para continuar.'
                    )

                obj.empresa = empresa_obj

            if empresa_obj:
                set_current_empresa(empresa_obj)

        set_current_user(request.user)

        if not change and hasattr(obj, 'creado_por') and not getattr(obj, 'creado_por_id', None):
            obj.creado_por = request.user

        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filtra lo que aparece en los select/combos del formulario"""
        if not request.user.is_superuser:
            empresa_activa = self._resolve_empresa_for_user(request.user)
            if not empresa_activa:
                return super().formfield_for_foreignkey(db_field, request, **kwargs)

            related_model = db_field.remote_field.model
            
            # Si el modelo relacionado tiene el campo 'empresa'
            if hasattr(related_model, 'empresa'):
                # Priorizamos usar all_objects para que el Manager restrictivo 
                # de la API no interfiera con la carga del combo en el Admin
                if hasattr(related_model, 'all_objects'):
                    base_qs = related_model.all_objects.all()
                else:
                    base_qs = related_model.objects.all()
                
                # Aplicamos el filtro de empresa manualmente
                kwargs["queryset"] = base_qs.filter(empresa=empresa_activa)
                
        return super().formfield_for_foreignkey(db_field, request, **kwargs)



@admin.register(User)
class CustomUserAdmin(TenantAdminMixin, UserAdmin):
    add_form = CustomUserCreationAdminForm
    form = CustomUserChangeAdminForm
    inlines = [UserEmpresaInline]
    
    list_display = ("username", "email", "empresa_activa", "is_staff", "is_active")
    
    fieldsets = UserAdmin.fieldsets + (
        ("Información de ERP", {"fields": ("empresa_activa", "rol_empresa", "telefono")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email",
                "username",
                "first_name",
                "last_name",
                "password1",
                "password2",
                "empresa_activa",
                "rol_empresa",
                "is_staff",
                "is_active",
            ),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        empresa_activa = self._resolve_empresa_for_user(request.user)
        if not empresa_activa:
            return qs.none()

        return qs.filter(
            empresas_rel__empresa=empresa_activa,
            empresas_rel__activo=True,
        ).distinct()

    def get_fieldsets(self, request, obj=None):
        # 1. Obtenemos los fieldsets base (que ya traen is_superuser, etc.)
        fieldsets = list(super().get_fieldsets(request, obj))
        
        if not request.user.is_superuser:
            # 2. Convertimos a una estructura editable (listas de listas)
            new_fieldsets = []
            for name, content in fieldsets:
                fields = list(content.get('fields', []))
                
                # REGLA A: Cambiar 'empresa' por nuestro texto sin link
                if 'empresa_activa' in fields:
                    fields[fields.index('empresa_activa')] = 'show_empresa_text'
                
                # REGLA B: Eliminar permisos críticos para no-superusers
                # Quitamos is_superuser, user_permissions y groups
                fields = [
                    f for f in fields
                    if f not in ('is_superuser', 'user_permissions', 'groups', 'rol_empresa')
                ]
                
                new_fieldsets.append((name, {'fields': tuple(fields)}))
            return tuple(new_fieldsets)
            
        return fieldsets

    def get_inline_instances(self, request, obj=None):
        if not request.user.is_superuser:
            return []
        return super().get_inline_instances(request, obj)

    def get_readonly_fields(self, request, obj=None):
        # Usamos la lógica del Mixin pero aseguramos 'show_empresa_text'
        readonly = super().get_readonly_fields(request, obj)
        if not request.user.is_superuser:
            # Forzamos que estos campos sean siempre texto plano
            if 'show_empresa_text' not in readonly:
                readonly.append('show_empresa_text')
            # Si el usuario intenta editar su propio staff status, lo bloqueamos
            if 'is_staff' not in readonly:
                readonly.append('is_staff')
        return readonly

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        empresa = getattr(obj, 'empresa_activa', None)
        if not empresa:
            return

        rol_seleccionado = form.cleaned_data.get('rol_empresa')
        rol_default = RolUsuario.ADMIN if obj.is_staff and not obj.is_superuser else RolUsuario.VENDEDOR
        rol_objetivo = rol_seleccionado or rol_default

        relacion, created = UserEmpresa.objects.get_or_create(
            user=obj,
            empresa=empresa,
            defaults={
                'rol': rol_objetivo,
                'activo': True,
            },
        )

        updated_fields = []
        if not relacion.activo:
            relacion.activo = True
            updated_fields.append('activo')

        if relacion.rol != rol_objetivo:
            relacion.rol = rol_objetivo
            updated_fields.append('rol')

        if updated_fields:
            relacion.save(update_fields=updated_fields)

@admin.register(Empresa)
class EmpresaAdmin(TenantAdminMixin, admin.ModelAdmin):
    # Aquí NO usamos el mixin porque si un usuario normal viera esto, 
    # solo vería su propia empresa. Generalmente, este modelo 
    # es solo para que el Superuser gestione suscripciones.
    list_display = ("nombre", "rut", "plan", "activa")
    search_fields = ("nombre", "rut")
    inlines = [BodegaInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        empresa = form.instance

        # Garantiza onboarding: si no se cargaron bodegas, crea una Principal activa.
        if empresa and not Bodega.all_objects.filter(empresa=empresa).exists():
            Bodega.all_objects.create(
                empresa=empresa,
                creado_por=request.user,
                nombre='Principal',
                activa=True,
            )

    def has_module_permission(self, request):
        # Solo el Superuser ve el módulo "Empresas" en el panel lateral
        return request.user.is_superuser

