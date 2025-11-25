INSTRUCCIONES PARA RESTAURAR PEPSICO-WEB EN OTRO DISPOSITIVO

IMPORTANTE: Sigue estos pasos en orden para preservar toda la base de datos.

PASO 1: COPIAR LOS ARCHIVOS NECESARIOS
===========================================
Copia la carpeta completa pepsico-web al nuevo dispositivo, incluyendo:
- db.sqlite3 (CRÍTICO - contiene todos los usuarios, vehículos, ingresos)
- manage.py
- requirements.txt
- Todas las carpetas del proyecto (config, ingresos, vehiculos, reportes, etc.)
- Carpeta templates/
- Carpeta static/
- Carpeta staticfiles/
- Carpeta media/

PASO 2: INSTALAR PYTHON
========================
1. Descarga Python 3.10 o superior desde https://www.python.org/
2. Durante la instalación, marca "Add Python to PATH"
3. Verifica la instalación:
   python --version

PASO 3: CREAR ENTORNO VIRTUAL
==============================
En la carpeta pepsico-web, abre PowerShell y ejecuta:
   python -m venv venv
   .\venv\Scripts\Activate.ps1

(Si aparece error de permisos, ejecuta como Administrador)

PASO 4: INSTALAR DEPENDENCIAS
==============================
Con el entorno virtual activado, ejecuta:
   pip install -r requirements.txt

PASO 5: VERIFICAR LA BASE DE DATOS
==================================
1. Verifica que db.sqlite3 existe en la carpeta raíz
2. Ejecuta las migraciones (por si hay cambios nuevos):
   python manage.py migrate

3. Crea un superusuario SOLO si es la primera vez (si ya tienes usuarios, sáltalo):
   python manage.py createsuperuser

PASO 6: EJECUTAR EL SERVIDOR
=============================
Con el entorno virtual activado, ejecuta:
   python manage.py runserver

La aplicación estará disponible en: http://127.0.0.1:8000

PASO 7: ACCEDER
===============
- Ve a http://127.0.0.1:8000/admin/
- Usa las credenciales del administrador que creaste
- Todos tus usuarios, vehículos e ingresos estarán intactos

NOTAS IMPORTANTES
=================
- NUNCA elimines ni modifiques db.sqlite3
- Si aparecen errores de migraciones, ejecuta:
  python manage.py makemigrations
  python manage.py migrate

- Si el proyecto no carga, verifica:
  1. El archivo db.sqlite3 está presente
  2. Las dependencias están instaladas (pip list)
  3. El entorno virtual está activado (debe mostrar (venv) en el prompt)

PARA ACTUALIZAR DATOS ENTRE DISPOSITIVOS
==========================================
Si quieres actualizar solo algunos datos específicos, no copies db.sqlite3.
En su lugar, usa el admin de Django para importar/exportar datos manualmente,
o usa dumpdata/loaddata:

Exportar datos:
   python manage.py dumpdata > datos_backup.json

Restaurar datos:
   python manage.py loaddata datos_backup.json

PROBLEMAS COMUNES
=================
- "ModuleNotFoundError": Las dependencias no están instaladas. Ejecuta: pip install -r requirements.txt
- "Database locked": Cierra todas las instancias de la aplicación y reinicia
- "Port already in use": Usa otro puerto: python manage.py runserver 8001
