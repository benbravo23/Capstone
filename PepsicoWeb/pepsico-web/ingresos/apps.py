from django.apps import AppConfig


class IngresosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ingresos'
    
    def ready(self):
        import ingresos.signals  # noqa
