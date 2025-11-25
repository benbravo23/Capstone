import csv
import io
import openpyxl
from django.contrib.auth.hashers import make_password
from vehiculos.models import Vehiculo
from usuarios.models import Usuario


def read_file_to_dict(file):
    """
    Lee un archivo CSV o Excel y lo convierte en una lista de diccionarios.
    Detecta automáticamente el formato.
    """
    filename = file.name.lower()
    
    if filename.endswith('.xlsx'):
        # Leer archivo Excel
        workbook = openpyxl.load_workbook(file)
        sheet = workbook.active
        
        # Obtener headers (primera fila)
        headers = [str(cell.value).strip() if cell.value else '' for cell in sheet[1]]
        
        # Limpiar headers: remover BOM y espacios
        headers = [h.replace('\ufeff', '').strip().lower() for h in headers]
        
        # Leer datos
        data = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            row_dict = {}
            for i in range(len(headers)):
                if i < len(row):
                    value = row[i]
                    if value is not None:
                        row_dict[headers[i]] = str(value).strip()
                    else:
                        row_dict[headers[i]] = ''
            data.append(row_dict)
        
        return data
    
    else:
        # Leer archivo CSV
        # Intentar diferentes codificaciones
        try:
            decoded_file = file.read().decode('utf-8-sig')  # Maneja BOM automáticamente
        except:
            try:
                decoded_file = file.read().decode('utf-8')
            except:
                decoded_file = file.read().decode('latin-1')
        
        io_string = io.StringIO(decoded_file)
        
        # Detectar el separador
        sample = decoded_file[:1024]
        delimiter = ';' if sample.count(';') > sample.count(',') else ','
        
        reader = csv.DictReader(io_string, delimiter=delimiter)
        # Normalizar las keys: convertir a minúsculas y remover BOM
        data = []
        for row in reader:
            normalized_row = {k.replace('\ufeff', '').strip().lower(): v.strip() if v else '' for k, v in row.items()}
            data.append(normalized_row)
        
        return data

def import_vehiculos_from_csv(csv_file):
    """
    Importa vehículos desde un archivo CSV o Excel.
    
    Formato esperado:
    patente,marca,modelo,año,tipo,flota,kilometraje,activo
    """
    
    try:
        data = read_file_to_dict(csv_file)
    except Exception as e:
        return {
            'created': 0,
            'updated': 0,
            'errors': [f'Error al leer el archivo: {str(e)}'],
            'total': 0
        }
    
    created = 0
    updated = 0
    errors = []
    
    for row_num, row in enumerate(data, start=2):
        try:
            # Saltar filas vacías
            if not any(row.values()):
                continue
            
            patente = str(row.get('patente', '')).strip().upper()
            
            if not patente or patente == 'PATENTE':  # También saltar el header si aparece duplicado
                errors.append(f"Fila {row_num}: La patente es obligatoria")
                continue
            
            # Obtener marca y modelo (obligatorios)
            marca = str(row.get('marca', '')).strip()
            modelo = str(row.get('modelo', '')).strip()
            
            if not marca or not modelo:
                errors.append(f"Fila {row_num}: Marca y modelo son obligatorios")
                continue
            
            # Mapear tipo de vehículo
            tipo_map = {
                'CAMION': 'CAMION',
                'CAMIONETA': 'CAMIONETA',
                'FURGON': 'FURGON',
                'OTRO': 'OTRO',
            }
            tipo = tipo_map.get(str(row.get('tipo', '')).strip().upper(), 'CAMION')
            
            # Convertir año (con valor por defecto si está vacío)
            try:
                año_value = row.get('año', '')
                año = int(año_value) if año_value and str(año_value).strip() else 2020
            except (ValueError, TypeError):
                año = 2020
            
            # Convertir kilometraje (con valor por defecto si está vacío)
            try:
                km_value = row.get('kilometraje', '')
                kilometraje = int(km_value) if km_value and str(km_value).strip() else 0
            except (ValueError, TypeError):
                kilometraje = 0
            
            # Convertir activo a booleano
            activo_str = str(row.get('activo', 'true')).strip().lower()
            activo = activo_str in ['true', '1', 'si', 'yes', 'activo', '']  # Vacío = activo por defecto
            
            # Buscar o crear vehículo
            vehiculo, created_flag = Vehiculo.objects.update_or_create(
                patente=patente,
                defaults={
                    'marca': marca,
                    'modelo': modelo,
                    'año': año,
                    'tipo': tipo,
                    'flota': str(row.get('flota', '')).strip(),
                    'kilometraje': kilometraje,
                    'activo': activo,
                }
            )
            
            if created_flag:
                created += 1
            else:
                updated += 1
                
        except Exception as e:
            errors.append(f"Fila {row_num}: {str(e)}")
    
    return {
        'created': created,
        'updated': updated,
        'errors': errors,
        'total': created + updated
    }


def import_usuarios_from_csv(csv_file):
    """
    Importa usuarios desde un archivo CSV o Excel.
    
    Formato esperado:
    email,nombre,rut,rol,telefono,activo
    """
    
    try:
        data = read_file_to_dict(csv_file)
    except Exception as e:
        return {
            'created': 0,
            'updated': 0,
            'errors': [f'Error al leer el archivo: {str(e)}'],
            'total': 0,
            'passwords': []
        }

    
    created = 0
    updated = 0
    errors = []
    passwords = []
    
    for row_num, row in enumerate(data, start=2):
        try:
            email = str(row.get('email', '')).strip().lower()
            
            if not email:
                errors.append(f"Fila {row_num}: El email es obligatorio")
                continue
            
            # Mapear rol
            rol_map = {
            'ADMIN': 'ADMIN',
            'ADMINISTRADOR': 'ADMIN',
            'SUPERVISOR': 'SUPERVISOR',
            'MECANICO': 'MECANICO',
            'MECÁNICO': 'MECANICO',
            'CHOFER': 'CHOFER',
            'GUARDIA': 'GUARDIA',      # NUEVO
            'BODEGA': 'BODEGA',        # NUEVO
            'EHS': 'EHS',              # NUEVO
            }
            rol = rol_map.get(str(row.get('rol', '')).strip().upper(), 'CHOFER')
            
            # Convertir activo a booleano
            activo_str = str(row.get('activo', 'true')).strip().lower()
            activo = activo_str in ['true', '1', 'si', 'yes', 'activo']
            
            # Generar contraseña temporal
            password = f"Pepsi{str(row.get('rut', '12345678'))[:4]}"
            
            # Buscar o crear usuario
            usuario, created_flag = Usuario.objects.update_or_create(
                email=email,
                defaults={
                    'nombre': str(row.get('nombre', '')).strip(),
                    'rut': str(row.get('rut', '')).strip(),
                    'telefono': str(row.get('telefono', '')).strip(),
                    'rol': rol,
                    'activo': activo,
                }
            )
            
            # Si es nuevo, establecer contraseña
            if created_flag:
                usuario.set_password(password)
                usuario.save()
                passwords.append({
                    'email': email,
                    'password': password,
                    'nombre': usuario.nombre
                })
                created += 1
            else:
                updated += 1
                
        except Exception as e:
            errors.append(f"Fila {row_num}: {str(e)}")
    
    return {
        'created': created,
        'updated': updated,
        'errors': errors,
        'total': created + updated,
        'passwords': passwords
    }

def generate_vehiculos_csv_template():
    """Genera un CSV de ejemplo para vehículos (formato Excel español)."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')  # Cambiar a punto y coma
    
    # Header
    writer.writerow(['patente', 'marca', 'modelo', 'año', 'tipo', 'flota', 'kilometraje', 'activo'])
    
    # Ejemplos
    writer.writerow(['ABCD12', 'Mercedes-Benz', 'Actros', '2020', 'CAMION', 'Flota Norte', '50000', 'true'])
    writer.writerow(['EFGH34', 'Volvo', 'FH16', '2019', 'CAMION', 'Flota Sur', '75000', 'true'])
    writer.writerow(['IJKL56', 'Chevrolet', 'N300', '2021', 'FURGON', 'Flota Centro', '30000', 'true'])
    
    return output.getvalue()


def generate_usuarios_csv_template():
    """Genera un CSV de ejemplo para usuarios (formato Excel español)."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')  # Cambiar a punto y coma
    
    # Header
    writer.writerow(['email', 'nombre', 'rut', 'rol', 'telefono', 'activo'])
    
    # Ejemplos
    writer.writerow(['supervisor@pepsico.cl', 'Juan Pérez', '12345678-9', 'SUPERVISOR', '+56912345678', 'true'])
    writer.writerow(['mecanico1@pepsico.cl', 'Pedro González', '98765432-1', 'MECANICO', '+56987654321', 'true'])
    writer.writerow(['chofer1@pepsico.cl', 'María López', '11223344-5', 'CHOFER', '+56911223344', 'true'])
    
    return output.getvalue()
