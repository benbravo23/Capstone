from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.contrib import messages
from django.contrib.messages import get_messages


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    """Replace default login messages with a clear, user-specific message.

    Some translations (allauth) may insert a message with a missing name
    (e.g. 'Ha iniciado sesión exitosamente como None.'). To avoid this,
    consume existing messages and add a clear one with the user's display name.
    """
    try:
        # Consume any existing messages so they don't show an incorrect login text
        list(get_messages(request))
    except Exception:
        pass

    display = getattr(user, 'nombre', None) or getattr(user, 'email', None) or getattr(user, 'username', None)
    if not display:
        display = str(user)

    # Log the successful login instead of using messages
    print(f'Has iniciado sesión correctamente "{display}".')
