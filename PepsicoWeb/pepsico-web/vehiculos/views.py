import openpyxl
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Vehiculo, DocumentoVehiculo
from .forms import VehiculoForm, DocumentoVehiculoForm
from core.decorators import role_required


@login_required
@role_required(['ADMIN', 'SUPERVISOR'])
def eliminar_documento_vehiculo(request, doc_id):
    """Elimina un documento asociado a un vehículo."""
    documento = get_object_or_404(DocumentoVehiculo, id=doc_id)
    vehiculo_pk = documento.vehiculo.pk
    if request.method == 'POST':
        documento.delete()
        messages.success(request, 'Documento eliminado correctamente.')
        return redirect('vehiculo_edit', pk=vehiculo_pk)
    # Si no es POST, redirigir de todos modos
    return redirect('vehiculo_edit', pk=vehiculo_pk)

import openpyxl
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Vehiculo, DocumentoVehiculo
from .forms import VehiculoForm, DocumentoVehiculoForm
from core.decorators import role_required

@login_required
@role_required(['ADMIN', 'SUPERVISOR', 'MECANICO', 'BODEGA', 'EHS'])
def vehiculos_export_excel(request):
    """Exporta la lista de vehículos a un archivo Excel."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Vehículos"
    headers = [
        'Patente', 'Marca', 'Modelo', 'Año', 'Tipo', 'Flota', 'Kilometraje', 'Activo'
    ]
    ws.append(headers)
    for v in Vehiculo.objects.all():
        ws.append([
            v.patente,
            v.marca,
            v.modelo,
            v.año,
            v.get_tipo_display(),
            v.flota or '',
            v.kilometraje,
            'Sí' if v.activo else 'No',
        ])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=vehiculos.xlsx'
    wb.save(response)
    return response


@login_required
@role_required(['ADMIN', 'SUPERVISOR', 'MECANICO', 'BODEGA', 'EHS'])
def vehiculos_list(request):
    """Lista de vehículos con búsqueda. Acceso: Admin, Supervisor, Mecánico, Bodega, EHS."""
    query = request.GET.get('q', '')
    tipo_filter = request.GET.get('tipo', '')
    activo_filter = request.GET.get('activo', '')

    vehiculos = Vehiculo.objects.all()

    if query:
        vehiculos = vehiculos.filter(
            Q(patente__icontains=query) |
            Q(marca__icontains=query) |
            Q(modelo__icontains=query) |
            Q(flota__icontains=query)
        )

    if tipo_filter:
        vehiculos = vehiculos.filter(tipo=tipo_filter)

    if activo_filter:
        vehiculos = vehiculos.filter(activo=activo_filter == 'true')

    total_vehiculos = vehiculos.count()
    total_activos = vehiculos.filter(activo=True).count()
    total_inactivos = vehiculos.filter(activo=False).count()

    context = {
        'vehiculos': vehiculos,
        'query': query,
        'tipo_filter': tipo_filter,
        'activo_filter': activo_filter,
        'tipos': Vehiculo.TipoVehiculo.choices,
        'total_vehiculos': total_vehiculos,
        'total_activos': total_activos,
        'total_inactivos': total_inactivos,
    }
    return render(request, 'vehiculos/vehiculos_list.html', context)


@login_required
@role_required(['ADMIN', 'SUPERVISOR', 'MECANICO', 'BODEGA', 'EHS'])
def vehiculo_detail(request, pk):
    """Detalle de un vehículo con historial de ingresos. Acceso: Admin, Supervisor, Mecánico, Bodega, EHS."""
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    ingresos = vehiculo.ingresos.all()[:10]  # Últimos 10 ingresos
    documentos = vehiculo.documentos_vehiculo.all()
    context = {
        'vehiculo': vehiculo,
        'ingresos': ingresos,
        'documentos': documentos,
    }
    return render(request, 'vehiculos/vehiculo_detail.html', context)


@login_required
@role_required(['ADMIN', 'SUPERVISOR'])
def vehiculo_create(request):
    """Crear nuevo vehículo."""
    doc_form = DocumentoVehiculoForm()
    documentos = []
    if request.method == 'POST':
        form = VehiculoForm(request.POST)
        if form.is_valid():
            vehiculo = form.save()
            # Procesar documentos si se subieron
            if request.FILES.get('archivo'):
                doc_form = DocumentoVehiculoForm(request.POST, request.FILES)
                if doc_form.is_valid():
                    doc = doc_form.save(commit=False)
                    doc.vehiculo = vehiculo
                    doc.save()
            messages.success(request, f'Vehículo {vehiculo.patente} creado exitosamente.')
            return redirect('vehiculo_detail', pk=vehiculo.pk)
    else:
        form = VehiculoForm()
    context = {'form': form, 'doc_form': doc_form, 'documentos': documentos, 'titulo': 'Agregar Vehículo'}
    return render(request, 'vehiculos/vehiculo_form.html', context)


@login_required
@role_required(['ADMIN', 'SUPERVISOR'])
def vehiculo_edit(request, pk):
    """Editar vehículo existente."""
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    documentos = vehiculo.documentos_vehiculo.all()
    doc_form = DocumentoVehiculoForm()
    if request.method == 'POST':
        form = VehiculoForm(request.POST, instance=vehiculo)
        if form.is_valid():
            vehiculo = form.save()
            # Procesar documentos si se subieron
            if request.FILES.get('archivo'):
                doc_form = DocumentoVehiculoForm(request.POST, request.FILES)
                if doc_form.is_valid():
                    doc = doc_form.save(commit=False)
                    doc.vehiculo = vehiculo
                    doc.save()
            messages.success(request, f'Vehículo {vehiculo.patente} actualizado exitosamente.')
            return redirect('vehiculo_detail', pk=vehiculo.pk)
    else:
        form = VehiculoForm(instance=vehiculo)
    context = {'form': form, 'vehiculo': vehiculo, 'doc_form': doc_form, 'documentos': documentos, 'titulo': 'Editar Vehículo'}
    return render(request, 'vehiculos/vehiculo_form.html', context)


@login_required
@role_required(['ADMIN'])
def vehiculo_delete(request, pk):
    """Eliminar vehículo (solo admin)."""
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    
    if request.method == 'POST':
        patente = vehiculo.patente
        vehiculo.delete()
        messages.success(request, f'Vehículo {patente} eliminado exitosamente.')
        return redirect('vehiculos_list')
    
    context = {'vehiculo': vehiculo}
    return render(request, 'vehiculos/vehiculo_confirm_delete.html', context)