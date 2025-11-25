from django.contrib.messages import get_messages
from django.contrib import messages
from django.template.response import TemplateResponse


class FilterLoginMessagesMiddleware:
    """Middleware que filtra mensajes de login defectuosos (por ejemplo 'como None').

    Funciona tomando todos los mensajes, eliminando los que contienen el patrón
    problemático y reinyectando los restantes antes de que se renderice la plantilla.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        def _filter():
            try:
                stored = list(get_messages(request))
            except Exception:
                return

            # Filtrar mensajes que contengan el patrón problemático
            filtered = []
            for m in stored:
                text = str(m)
                # Patrón común observado: 'Ha iniciado sesión exitosamente como None.'
                if 'como None' in text or 'como None.' in text:
                    continue
                if text.strip().startswith('Ha iniciado sesión exitosamente como') and 'None' in text:
                    continue
                filtered.append(m)

            # Reagregar mensajes filtrados
            for fm in filtered:
                try:
                    messages.add_message(request, fm.level, fm.message, extra_tags=fm.tags)
                except Exception:
                    # Fallback simple
                    messages.add_message(request, fm.level, fm.message)

        # Si la respuesta es una TemplateResponse no renderizada, ejecutar antes de render
        if isinstance(response, TemplateResponse) and not response.is_rendered:
            response.add_post_render_callback(lambda r: _filter())
        else:
            # Para respuestas ya renderizadas o no template, filtrar igualmente
            _filter()

        return response
