from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        # Import signals to ensure our login message override runs
        try:
            import core.signals  # noqa: F401
        except Exception:
            pass
