from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied


def role_required(roles):
    """
    Decorador que verifica si el usuario tiene uno de los roles especificados.
    
    Uso:
        @role_required(['ADMIN', 'SUPERVISOR'])
        @role_required('ADMIN')  # También acepta un string
        def mi_vista(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Debe iniciar sesión.')
                return redirect('account_login')

            # Normalizar roles a mayúsculas para comparaciones insensibles
            try:
                user_rol = (request.user.rol or '').upper()
            except Exception:
                user_rol = ''

            # Soportar tanto string como lista
            if isinstance(roles, str):
                allowed = {roles.upper()}
            else:
                allowed = {str(r).upper() for r in roles}

            if user_rol not in allowed:
                messages.error(request, 'No tiene permisos para acceder a esta página.')
                raise PermissionDenied

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator