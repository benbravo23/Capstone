from django import forms
from usuarios.models import Usuario


class CSVImportForm(forms.Form):
    """Formulario para importar archivos CSV o Excel."""
    
    csv_file = forms.FileField(
        label='Archivo CSV o Excel',
        help_text='Selecciona un archivo CSV o Excel (.xlsx) para importar',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx'  # Aceptar ambos formatos
        })
    )
    
    def clean_csv_file(self):
        file = self.cleaned_data['csv_file']
        
        # Validar extensión
        if not (file.name.endswith('.csv') or file.name.endswith('.xlsx')):
            raise forms.ValidationError('El archivo debe ser CSV (.csv) o Excel (.xlsx)')
        
        # Validar tamaño (máximo 10MB)
        if file.size > 10 * 1024 * 1024:
            raise forms.ValidationError('El archivo no debe superar los 10MB')
        
        return file


class CrearUsuarioForm(forms.ModelForm):
    """Formulario para crear nuevos usuarios."""
    
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa una contraseña segura'
        })
    )
    password2 = forms.CharField(
        label='Confirmar Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirma la contraseña'
        })
    )
    
    class Meta:
        model = Usuario
        fields = ['email', 'nombre', 'rut', 'telefono', 'rol', 'activo']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo'
            }),
            'rut': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 12345678-9'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de teléfono (opcional)'
            }),
            'rol': forms.Select(attrs={
                'class': 'form-select'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError('Las contraseñas no coinciden.')
        
        return password2
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError('Este email ya está registrado.')
        return email
    
    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data['password1'])
        if commit:
            usuario.save()
        return usuario


class EditarUsuarioForm(forms.ModelForm):
    """Formulario para editar usuarios existentes (sin cambio de contraseña)."""
    
    class Meta:
        model = Usuario
        fields = ['email', 'nombre', 'rut', 'telefono', 'rol', 'activo']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo'
            }),
            'rut': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 12345678-9'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de teléfono (opcional)'
            }),
            'rol': forms.Select(attrs={
                'class': 'form-select'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        usuario_id = self.instance.id
        # Permitir que el usuario mantenga su email actual
        if Usuario.objects.filter(email=email).exclude(id=usuario_id).exists():
            raise forms.ValidationError('Este email ya está registrado por otro usuario.')
        return email
    
    def save(self, commit=True):
        usuario = super().save(commit=commit)
        return usuario