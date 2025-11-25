from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.http import HttpResponse
from core.decorators import role_required
from core.forms import CSVImportForm, CrearUsuarioForm, EditarUsuarioForm
from core.utils import (
    import_vehiculos_from_csv,
    import_usuarios_from_csv,
    generate_vehiculos_csv_template,
    generate_usuarios_csv_template
)


def home(request):
    """Página de inicio."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('account_login')


@login_required
def dashboard(request):
    """Dashboard principal."""
    # Si el usuario es guardia, redirigir al dashboard de guardia específico
    if hasattr(request.user, 'rol') and request.user.rol == 'GUARDIA':
        return redirect('guard_dashboard')

    context = {}
    
    # Si es mecánico, obtener sus tareas recientes (máximo 5)
    if hasattr(request.user, 'rol') and request.user.rol == 'MECANICO':
        from ingresos.models import Tarea
        tareas_recientes = Tarea.objects.filter(
            mecanico=request.user
        ).select_related(
            'ingreso__vehiculo'
        ).order_by('-fecha_asignacion')[:5]
        context['tareas_recientes'] = tareas_recientes

    return render(request, 'core/dashboard.html', context)


@login_required
def user_logout(request):
    """Cerrar sesión del usuario."""
    logout(request)
    messages.success(request, '✅ Has cerrado sesión correctamente.')
    return redirect('account_login')


@login_required
@role_required(['ADMIN', 'SUPERVISOR'])
def import_vehiculos(request):
    """Vista para importar vehículos desde CSV."""
    
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            
            try:
                result = import_vehiculos_from_csv(csv_file)
                
                # Guardar resultado en sesión para mostrar en página de éxito
                request.session['import_result'] = {
                    'tipo': 'vehiculos',
                    'created': result['created'],
                    'updated': result['updated'],
                    'errors': result['errors'],
                    'total': result['total']
                }
                
                return redirect('import_result')
                    
            except Exception as e:
                messages.error(request, f"Error al procesar el archivo: {str(e)}")
    else:
        form = CSVImportForm()
    
    context = {
        'form': form,
        'titulo': 'Importar Vehículos desde CSV',
        'tipo': 'vehiculos'
    }
    return render(request, 'core/import_csv.html', context)


@login_required
@role_required(['ADMIN'])
def import_usuarios(request):
    """Vista para importar usuarios desde CSV."""
    
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            
            try:
                result = import_usuarios_from_csv(csv_file)
                
                # Guardar resultado en sesión
                request.session['import_result'] = {
                    'tipo': 'usuarios',
                    'created': result['created'],
                    'updated': result['updated'],
                    'errors': result['errors'],
                    'total': result['total'],
                    'passwords': result['passwords']
                }
                
                return redirect('import_result')
                    
            except Exception as e:
                messages.error(request, f"Error al procesar el archivo: {str(e)}")
    else:
        form = CSVImportForm()
    
    context = {
        'form': form,
        'titulo': 'Importar Usuarios desde CSV',
        'tipo': 'usuarios'
    }
    return render(request, 'core/import_csv.html', context)


@login_required
def import_result(request):
    """Muestra el resultado detallado de la importación."""
    result = request.session.get('import_result', None)
    
    if not result:
        messages.warning(request, 'No hay resultados de importación para mostrar.')
        return redirect('dashboard')
    
    # Limpiar la sesión
    del request.session['import_result']
    
    context = {'result': result}
    return render(request, 'core/import_result.html', context)


@login_required
@role_required(['ADMIN'])
def import_usuarios(request):
    """Vista para importar usuarios desde CSV."""
    
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            
            try:
                result = import_usuarios_from_csv(csv_file)
                
                # Mostrar resultados
                if result['created'] > 0:
                    messages.success(request, f"✅ {result['created']} usuarios creados")
                    
                    # Mostrar contraseñas generadas
                    if result['passwords']:
                        passwords_text = "\n".join([
                            f"{p['nombre']} ({p['email']}): {p['password']}"
                            for p in result['passwords'][:10]
                        ])
                        messages.warning(
                            request,
                            f"⚠️ Contraseñas generadas (guárdalas):\n{passwords_text}"
                        )
                
                if result['updated'] > 0:
                    messages.info(request, f"ℹ️ {result['updated']} usuarios actualizados")
                    
                if result['errors']:
                    for error in result['errors'][:5]:
                        messages.error(request, error)
                    if len(result['errors']) > 5:
                        messages.warning(request, f"...y {len(result['errors']) - 5} errores más")
                
                if result['total'] > 0:
                    # Guardar contraseñas en sesión para mostrarlas en otra página
                    request.session['imported_passwords'] = result['passwords']
                    return redirect('import_usuarios_success')
                    
            except Exception as e:
                messages.error(request, f"Error al procesar el archivo: {str(e)}")
    else:
        form = CSVImportForm()
    
    context = {
        'form': form,
        'titulo': 'Importar Usuarios desde CSV',
        'tipo': 'usuarios'
    }
    return render(request, 'core/import_csv.html', context)


@login_required
@role_required(['ADMIN'])
def import_usuarios_success(request):
    """Muestra las contraseñas generadas después de importar usuarios."""
    passwords = request.session.get('imported_passwords', [])
    
    # Limpiar la sesión
    if 'imported_passwords' in request.session:
        del request.session['imported_passwords']
    
    context = {'passwords': passwords}
    return render(request, 'core/import_usuarios_success.html', context)


@login_required
def download_vehiculos_template(request):
    """Descarga plantilla CSV de vehículos."""
    csv_content = generate_vehiculos_csv_template()
    
    response = HttpResponse(csv_content, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="plantilla_vehiculos.csv"'
    return response


@login_required
def download_usuarios_template(request):
    """Descarga plantilla CSV de usuarios."""
    csv_content = generate_usuarios_csv_template()
    
    response = HttpResponse(csv_content, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="plantilla_usuarios.csv"'
    return response


@login_required
@role_required(['ADMIN'])
def crear_usuario(request):
    """Vista para crear nuevo usuario."""
    if request.method == 'POST':
        form = CrearUsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, f'✅ Usuario {usuario.nombre} ({usuario.email}) creado correctamente.')
            return redirect('gestionar_usuarios')
    else:
        form = CrearUsuarioForm()
    
    context = {
        'form': form,
        'titulo': 'Crear Nuevo Usuario'
    }
    return render(request, 'core/crear_usuario.html', context)


@login_required
@role_required(['ADMIN'])
def gestionar_usuarios(request):
    """Vista para gestionar usuarios."""
    from usuarios.models import Usuario
    
    usuarios = Usuario.objects.all().order_by('nombre')
    context = {
        'usuarios': usuarios,
        'titulo': 'Gestionar Usuarios'
    }
    return render(request, 'core/gestionar_usuarios.html', context)


@login_required
@role_required(['ADMIN'])
def editar_usuario(request, usuario_id):
    """Vista para editar un usuario específico."""
    from usuarios.models import Usuario
    from core.forms import EditarUsuarioForm
    
    usuario = Usuario.objects.get(id=usuario_id)
    
    if request.method == 'POST':
        form = EditarUsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Usuario {usuario.nombre} actualizado correctamente.')
            return redirect('gestionar_usuarios')
    else:
        form = EditarUsuarioForm(instance=usuario)
    
    context = {
        'form': form,
        'usuario': usuario,
        'titulo': f'Editar Usuario: {usuario.nombre}'
    }
    return render(request, 'core/editar_usuario.html', context)


@login_required
@role_required(['ADMIN'])
def eliminar_usuario(request, usuario_id):
    """Vista para eliminar un usuario con confirmación."""
    from usuarios.models import Usuario
    
    usuario = Usuario.objects.get(id=usuario_id)
    
    # Evitar eliminar el usuario administrador actual
    if usuario.id == request.user.id:
        messages.error(request, '❌ No puedes eliminar tu propia cuenta.')
        return redirect('gestionar_usuarios')
    
    if request.method == 'POST':
        nombre_usuario = usuario.nombre
        usuario.delete()
        messages.success(request, f'✅ Usuario "{nombre_usuario}" eliminado correctamente.')
        return redirect('gestionar_usuarios')
    
    # GET: mostrar página de confirmación
    context = {
        'usuario': usuario,
        'titulo': f'Eliminar Usuario: {usuario.nombre}'
    }
    return render(request, 'core/eliminar_usuario.html', context)