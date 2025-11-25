
from django import forms
from .models import DocumentoVehiculo, Vehiculo

class DocumentoVehiculoForm(forms.ModelForm):
    class Meta:
        model = DocumentoVehiculo
        fields = ['tipo_documento', 'archivo', 'descripcion']
        widgets = {
            'tipo_documento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: SOAP, Siniestro, Permiso de Circulación'}),
            'archivo': forms.FileInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Descripción del documento (opcional)'}),
        }
from django import forms
from .models import Vehiculo


class VehiculoForm(forms.ModelForm):
    """Formulario para crear/editar vehículos."""
    
    class Meta:
        model = Vehiculo
        fields = ['patente', 'marca', 'modelo', 'año', 'vin', 'tipo', 'flota', 'kilometraje', 'activo']
        widgets = {
            'patente': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: AB1234'}),
            'marca': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Mercedes-Benz'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Actros'}),
            'año': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '2023'}),
            'vin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número VIN (opcional)'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'flota': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de flota'}),
            'kilometraje': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }