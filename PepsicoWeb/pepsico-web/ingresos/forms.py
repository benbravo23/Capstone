from django import forms
from django.utils import timezone
from .models import IngresoTaller, Pausa, Tarea, Documento, SolicitudIngreso, Maquina
from vehiculos.models import Vehiculo
from usuarios.models import Usuario


class IngresoTallerForm(forms.ModelForm):
    """Formulario para crear/editar ingresos al taller."""
    
    class Meta:
        model = IngresoTaller
        fields = ['vehiculo', 'fecha_programada', 'maquina', 'motivo', 'observaciones', 'repuesto_necesario', 'supervisor', 'chofer', 'kilometraje_ingreso']
        widgets = {
            'vehiculo': forms.Select(attrs={'class': 'form-select'}),
            'fecha_programada': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'maquina': forms.Select(attrs={'class': 'form-select'}),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe el motivo del ingreso...'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Observaciones adicionales (opcional)'}),
            'repuesto_necesario': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Filtro de aceite, pastillas de freno...'}),
            'supervisor': forms.Select(attrs={'class': 'form-select'}),
            'chofer': forms.Select(attrs={'class': 'form-select'}),
            'kilometraje_ingreso': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Kilometraje actual'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo vehículos activos
        self.fields['vehiculo'].queryset = Vehiculo.objects.filter(activo=True)
        # Filtrar supervisores y choferes
        self.fields['supervisor'].queryset = Usuario.objects.filter(rol='SUPERVISOR', activo=True)
        self.fields['chofer'].queryset = Usuario.objects.filter(rol='CHOFER', activo=True)
        # Filtrar solo máquinas activas
        self.fields['maquina'].queryset = Maquina.objects.filter(activa=True)

        # Actualizar fecha programada si ya pasó
        if self.instance and self.instance.fecha_programada and self.instance.fecha_programada < timezone.now():
            self.instance.fecha_programada = timezone.now() + timezone.timedelta(hours=1)
            self.fields['fecha_programada'].initial = self.instance.fecha_programada


class CheckInForm(forms.ModelForm):
    """Formulario simplificado para check-in de chofer."""
    
    class Meta:
        model = IngresoTaller
        fields = ['fecha_llegada', 'kilometraje_ingreso', 'observaciones']
        widgets = {
            'fecha_llegada': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'kilometraje_ingreso': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Kilometraje actual'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones del chofer'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Establecer fecha actual por defecto si instance no es None
        if self.instance and not self.instance.fecha_llegada:
            self.fields['fecha_llegada'].initial = timezone.now()

        # Hacer campos opcionales
        self.fields['fecha_llegada'].required = False
        self.fields['kilometraje_ingreso'].required = False
        self.fields['observaciones'].required = False
    
    def full_clean(self):
        """Sobrescribir full_clean para no validar el modelo completo."""
        self.cleaned_data = {}
        # Limpiar cada campo individualmente
        try:
            self._clean_fields()
        except Exception:
            pass
        try:
            self._clean_form()
        except Exception:
            pass
        # NO llamar _post_clean() para evitar ejecutar model.full_clean()


class PausaForm(forms.ModelForm):
    """Formulario para registrar pausas."""
    
    class Meta:
        model = Pausa
        fields = ['motivo', 'descripcion', 'fecha_inicio']
        widgets = {
            'motivo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Espera de repuesto'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Detalles adicionales'}),
            'fecha_inicio': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_inicio'].initial = timezone.now()


class TareaForm(forms.ModelForm):
    """Formulario para crear/editar tareas."""
    
    class Meta:
        model = Tarea
        fields = ['titulo', 'descripcion', 'mecanico', 'prioridad', 'estado', 'tiempo_estimado_minutos', 'repuestos_utilizados', 'observaciones']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Cambio de aceite'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción detallada de la tarea'}),
            'mecanico': forms.Select(attrs={'class': 'form-select'}),
            'prioridad': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'tiempo_estimado_minutos': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Minutos estimados'}),
            'repuestos_utilizados': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Lista de repuestos utilizados'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones adicionales'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mecanico'].queryset = Usuario.objects.filter(rol='MECANICO', activo=True)
        self.fields['mecanico'].required = False
        self.fields['descripcion'].required = False
        self.fields['tiempo_estimado_minutos'].required = False
        self.fields['repuestos_utilizados'].required = True  # Ahora es obligatorio
        self.fields['observaciones'].required = False
        # El campo 'estado' no se muestra al crear una tarea en la plantilla
        # (solo se muestra al editar). Como el modelo tiene un default
        # (PENDIENTE), aquí lo dejamos no requerido para que la validación
        # no falle cuando el formulario de creación no incluya ese campo.
        if 'estado' in self.fields:
            self.fields['estado'].required = False


class DocumentoForm(forms.ModelForm):
    """Formulario para subir documentos."""
    
    class Meta:
        model = Documento
        fields = ['tipo', 'archivo', 'descripcion']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'archivo': forms.FileInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Descripción del documento'}),
        }


class GuardRegistroForm(forms.Form):
    """Formulario simple para que el guardia registre la llegada de un vehículo.

    Campos solicitados: patente, marca del vehículo, motivo de ingreso, nombre del chofer
    y la posibilidad de subir una o más fotos (imágenes).
    """
    patente = forms.CharField(
        label='Patente',
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: ABC123'})
    )
    marca = forms.CharField(
        label='Marca',
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Ford'})
    )
    motivo = forms.CharField(
        label='Motivo de ingreso',
        required=True,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Motivo del ingreso'})
    )
    chofer_nombre = forms.CharField(
        label='Nombre del chofer',
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del chofer'})
    )
    photos = forms.FileField(
        label='Fotos (opcional)',
        required=False,
    )


class SolicitudIngresoForm(forms.ModelForm):
    """Formulario para que el chofer solicite ingreso al taller."""
    
    patente = forms.CharField(
        label='Patente del Vehículo',
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: ABC-1234',
            'autocomplete': 'off'
        })
    )
    
    class Meta:
        model = SolicitudIngreso
        # El chofer no ingresa fecha (la define el supervisor). Añadimos
        # telefono y ruta (ambos opcionales) y dejamos motivo.
        fields = ['motivo', 'telefono', 'ruta']
        widgets = {
            'motivo': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe el motivo del ingreso (Ej: Mantención preventiva, reparación, inspección)'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono de contacto (opcional)'
            }),
            'ruta': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ruta (opcional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.chofer = kwargs.pop('chofer', None)
        super().__init__(*args, **kwargs)
        self.vehiculo = None  # Inicializar el atributo
    
    def clean_patente(self):
        """Valida que la patente exista y que no haya solicitudes activas o ingresos en proceso."""
        patente = self.cleaned_data.get('patente', '').upper()
        
        if not patente:
            raise forms.ValidationError('La patente es requerida.')
        
        try:
            vehiculo = Vehiculo.objects.get(patente=patente)
        except Vehiculo.DoesNotExist:
            raise forms.ValidationError(f'❌ La patente "{patente}" no existe en el sistema. Por favor verifica.')
        
        # Verificar si ya hay solicitudes activas
        solicitudes_activas = SolicitudIngreso.objects.filter(
            vehiculo=vehiculo,
            estado__in=['PENDIENTE', 'APROBADA']
        )
        
        if solicitudes_activas.exists():
            raise forms.ValidationError(
                f'❌ Este vehículo ya tiene una solicitud activa. No puedes generar otra en este momento.'
            )
        
        # Verificar si hay ingresos en proceso (excluyendo RETIRADO y CANCELADO)
        # Solo bloqueamos si el ingreso está en estado activo: PROGRAMADO, EN_PROCESO, EN_PAUSA o TERMINADO
        ingresos_activos = IngresoTaller.objects.filter(
            vehiculo=vehiculo,
            estado__in=['PROGRAMADO', 'EN_PROCESO', 'EN_PAUSA', 'TERMINADO']
        )
        
        if ingresos_activos.exists():
            raise forms.ValidationError(
                f'❌ Este vehículo ya tiene un ingreso en proceso. Por favor espera a que se marque como retirado antes de solicitar otro.'
            )
        
        self.vehiculo = vehiculo
        return patente
    
    def clean(self):
        """Limpia el formulario completo."""
        cleaned_data = super().clean()
        
        # Si hay errores en patente, no intentar validar el modelo
        if 'patente' in self.errors:
            # No asignar vehiculo al modelo si hay error
            if hasattr(self, 'instance') and self.instance:
                self.instance.vehiculo = None
        
        return cleaned_data
    
    def save(self, commit=True):
        """Guarda la solicitud con el chofer actual."""
        instance = super().save(commit=False)
        
        # Asegurar que vehiculo está asignado
        if self.vehiculo:
            instance.vehiculo = self.vehiculo
        
        if self.chofer:
            instance.chofer = self.chofer

        # Campos opcionales del formulario
        telefono = self.cleaned_data.get('telefono', '')
        ruta = self.cleaned_data.get('ruta', '')
        if telefono:
            instance.telefono = telefono
        if ruta:
            instance.ruta = ruta
        
        if commit:
            instance.save()
        return instance
        
        if commit:
            instance.save()
        return instance


class GuardSalidaForm(forms.Form):
    """Formulario para que el guardia registre la salida de un vehículo."""
    
    patente = forms.CharField(
        label='Patente del vehículo que sale',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: ABC-1234',
            'autocomplete': 'off'
        })
    )
    observaciones = forms.CharField(
        label='Observaciones (opcional)',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Notas sobre la salida (daños, demoras, etc.)'
        })
    )