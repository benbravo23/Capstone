from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from .models import IngresoTaller, Pausa, Tarea, Documento, HistorialTarea, SolicitudIngreso, RegistroGuardia
from .forms import IngresoTallerForm, CheckInForm, PausaForm, TareaForm, DocumentoForm, SolicitudIngresoForm, GuardRegistroForm, GuardSalidaForm
from core.decorators import role_required
from vehiculos.models import Vehiculo
from usuarios.models import Usuario
from django.utils import timezone
from PIL import Image, UnidentifiedImageError
from django.core.files.uploadedfile import UploadedFile
from datetime import datetime, timedelta
from django.utils.timezone import make_aware
import csv

# Validation limits for uploaded photos
MAX_PHOTOS = 5
MAX_PHOTO_SIZE_MB = 5


@login_required
def ingresos_list(request):
    """Lista de ingresos al taller con filtros. Acceso: Todos los roles."""
    estado_filter = request.GET.get('estado', '')
    query = request.GET.get('q', '')
    
    ingresos = IngresoTaller.objects.select_related('vehiculo', 'supervisor', 'chofer').all()
    
    if estado_filter:
        ingresos = ingresos.filter(estado=estado_filter)
    
    if query:
        ingresos = ingresos.filter(
            Q(vehiculo__patente__icontains=query) |
            Q(motivo__icontains=query)
        )
    
    # Estadísticas
    stats = {
        'total': ingresos.count(),
        'programados': ingresos.filter(estado='PROGRAMADO').count(),
        'en_proceso': ingresos.filter(estado='EN_PROCESO').count(),
        'en_pausa': ingresos.filter(estado='EN_PAUSA').count(),
        'terminados': ingresos.filter(estado='TERMINADO').count(),
    }
    
    context = {
        'ingresos': ingresos[:50],  # Limitar a 50
        'estado_filter': estado_filter,
        'query': query,
        'estados': IngresoTaller.Estado.choices,
        'stats': stats,
    }
    return render(request, 'ingresos/ingresos_list.html', context)


@login_required
def ingreso_detail(request, pk):
    """Detalle completo de un ingreso. Acceso: Todos los roles."""
    ingreso = get_object_or_404(
        IngresoTaller.objects.select_related('vehiculo', 'supervisor', 'chofer'),
        pk=pk
    )
    tareas = ingreso.tareas.select_related('mecanico').all()
    pausas = ingreso.pausas.select_related('registrado_por').all()
    documentos = ingreso.documentos.select_related('subido_por').all()
    
    # Calcular tareas pendientes (no completadas ni canceladas)
    tareas_pendientes = tareas.exclude(estado__in=['COMPLETADA', 'CANCELADA'])
    
    context = {
        'ingreso': ingreso,
        'tareas': tareas,
        'pausas': pausas,
        'documentos': documentos,
        'tareas_pendientes': tareas_pendientes,
        'hay_tareas_pendientes': tareas_pendientes.exists(),
    }
    return render(request, 'ingresos/ingreso_detail.html', context)


@login_required
@role_required(['ADMIN', 'SUPERVISOR'])
def ingreso_create(request):
    """Crear nuevo ingreso (programar). Acceso: Admin, Supervisor."""
    if request.method == 'POST':
        # PRIMERO: procesar el slot del scheduler (si viene)
        slot_iso = request.POST.get('slot', '').strip() or request.POST.get('fecha_programada_scheduler', '').strip()
        
        # Hacer una copia mutable del POST para inyectar fecha_programada si viene del scheduler
        post_data = request.POST.copy()
        if slot_iso:
            # slot_iso tiene formato: "YYYY-MM-DDTHH:MM|MAQUINA_ID"
            if '|' in slot_iso:
                fecha_str, maquina_id = slot_iso.rsplit('|', 1)
                post_data['fecha_programada'] = fecha_str
                post_data['maquina'] = maquina_id
            else:
                post_data['fecha_programada'] = slot_iso
        
        form = IngresoTallerForm(post_data)
        
        if form.is_valid():
            ingreso = form.save(commit=False)

            # Verificar disponibilidad del slot si se seleccionó uno
            if ingreso.fecha_programada:
                inicio = ingreso.fecha_programada
                fin = inicio + timedelta(hours=1)
                
                # Si hay máquina, buscar ocupación en esa máquina específica
                if ingreso.maquina:
                    ocupado = IngresoTaller.objects.filter(
                        fecha_programada__gte=inicio,
                        fecha_programada__lt=fin,
                        maquina=ingreso.maquina,
                        estado__in=['PROGRAMADO', 'EN_PROCESO']
                    ).exists() or SolicitudIngreso.objects.filter(
                        fecha_estimada_ingreso__gte=inicio,
                        fecha_estimada_ingreso__lt=fin,
                        estado='APROBADA'
                    ).exists()
                else:
                    # Si no hay máquina, no validar solapamiento (será requerida máquina)
                    ocupado = False

                if ocupado:
                    messages.error(request, 'La máquina seleccionada ya está ocupada en ese horario. Elige otro slot.')
                    # Continuar sin retornar aquí, dejar que se renderice el formulario con slots
                    pass

            ingreso.estado = 'PROGRAMADO'
            try:
                ingreso.full_clean()  # Validar solapamientos
                ingreso.save()
                messages.success(request, f'Ingreso programado para {ingreso.vehiculo.patente}')
                return redirect('ingreso_detail', pk=ingreso.pk)
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
    else:
        form = IngresoTallerForm()
    
    # Añadir slots del scheduler para Admin/Supervisor si se solicita o por defecto
    slots = None
    count = 0
    user_role = getattr(request.user, 'rol', '')
    try:
        if user_role and user_role.upper() in ['ADMIN', 'SUPERVISOR']:
            try:
                count = int(request.GET.get('count', 4))
            except Exception:
                count = 4

            # Obtener máquinas activas
            from .models import Maquina
            maquinas = Maquina.objects.filter(activa=True).order_by('tipo', 'numero')

            today = timezone.localtime(timezone.now())
            days = [today.date() + timedelta(days=i) for i in range(0, max(1, count))]
            hours = list(range(8, 18))
            slots = []
            
            for day in days:
                # Por cada día, crear un grupo de filas (una por máquina)
                day_group = {'day': day, 'maquinas': []}
                
                for maquina in maquinas:
                    row = []
                    for h in hours:
                        slot_dt = datetime(day.year, day.month, day.day, h, 0, 0)
                        aware_slot = make_aware(slot_dt)
                        # Solo agregar slots futuros
                        if aware_slot < today:
                            continue
                        inicio = aware_slot
                        fin = aware_slot + timedelta(hours=1)
                        # Verificar ocupación de la máquina específica
                        ocupado = IngresoTaller.objects.filter(
                            fecha_programada__gte=inicio,
                            fecha_programada__lt=fin,
                            maquina=maquina,
                            estado__in=['PROGRAMADO', 'EN_PROCESO']
                        ).exists()
                        # Incluir formato compatible con selector: "YYYY-MM-DDTHH:MM|MAQUINA_ID"
                        dt_str = aware_slot.strftime('%Y-%m-%dT%H:%M')
                        slot_value = f"{dt_str}|{maquina.pk}"
                        row.append({'dt': aware_slot, 'dt_str': dt_str, 'ocupado': ocupado, 'slot_value': slot_value})
                    
                    if row:  # Solo agregar si hay slots disponibles
                        day_group['maquinas'].append({
                            'maquina': maquina,
                            'row': row
                        })
                
                if day_group['maquinas']:  # Solo agregar si hay máquinas con slots
                    slots.append(day_group)
    except Exception as e:
        import traceback
        traceback.print_exc()
        slots = None

    context = {'form': form, 'titulo': 'Programar Ingreso', 'slots': slots, 'count': count}
    return render(request, 'ingresos/ingreso_form.html', context)


@login_required
@role_required(['SUPERVISOR', 'ADMIN'])
def ingreso_checkin(request, pk):
    """
    Check-in de vehículo. Solo SUPERVISOR y ADMIN.
    BLOQUEADO hasta que el GUARDIA registre la entrada del vehículo.
    """
    ingreso = get_object_or_404(IngresoTaller, pk=pk)

    # Validar que exista un registro del guardia para este vehículo
    if not ingreso.registro_guardia:
        messages.error(
            request,
            f'❌ No se puede hacer check-in. El guardia aún no ha registrado la entrada del vehículo {ingreso.vehiculo.patente}.'
        )
        return redirect('ingreso_detail', pk=pk)

    if ingreso.estado != 'PROGRAMADO':
        messages.warning(request, 'Este ingreso ya fue registrado.')
        return redirect('ingreso_detail', pk=pk)

    if request.method == 'POST':
        # Procesar el formulario manualmente
        try:
            ingreso.fecha_llegada = request.POST.get('fecha_llegada') or timezone.now()
            ingreso.kilometraje_ingreso = request.POST.get('kilometraje_ingreso') or None
            ingreso.observaciones = request.POST.get('observaciones') or ''
            ingreso.estado = 'EN_PROCESO'
            ingreso.fecha_inicio = timezone.now()
            ingreso.supervisor = request.user  # Registrar supervisor que hace check-in
            ingreso.save()
            messages.success(request, f'✅ Check-in registrado para {ingreso.vehiculo.patente}')
            return redirect('ingreso_detail', pk=pk)
        except Exception as e:
            messages.error(request, f'Error al guardar: {str(e)}')
            return redirect('ingreso_detail', pk=pk)
    
    # Para GET, mostrar formulario con información del registro de guardia
    context = {
        'ingreso': ingreso,
        'titulo': 'Check-in',
        'registro_guardia': ingreso.registro_guardia
    }
    return render(request, 'ingresos/ingreso_checkin.html', context)




@login_required
@role_required(['CHOFER', 'GUARDIA', 'SUPERVISOR', 'ADMIN'])
def ingreso_marcar_retirado(request, pk):
    """Marcar un ingreso como retirado. Acceso: Chofer, Guardia, Supervisor, Admin."""
    ingreso = get_object_or_404(IngresoTaller, pk=pk)

    if ingreso.estado != 'TERMINADO':
        messages.warning(request, 'Solo se pueden marcar como retirados los ingresos terminados.')
        return redirect('ingreso_detail', pk=pk)

    if request.method == 'POST':
        try:
            # Cambiar estado del ingreso a RETIRADO
            ingreso.estado = 'RETIRADO'
            ingreso.save(update_fields=['estado', 'fecha_modificacion'])
            
            # Cambiar solicitud asociada a RETIRADA (si existe)
            SolicitudIngreso.objects.filter(
                ingreso_taller=ingreso,
                estado='COMPLETADA'
            ).update(estado='RETIRADA')
            
            messages.success(request, f'Vehículo {ingreso.vehiculo.patente} marcado como retirado. ¡Proceso completado!')
            return redirect('ingreso_detail', pk=pk)
        except Exception as e:
            messages.error(request, f'Error al guardar: {str(e)}')
    
    context = {'ingreso': ingreso, 'titulo': 'Marcar como Retirado'}
    return render(request, 'ingresos/ingreso_marcar_retirado.html', context)


@login_required
@role_required(['ADMIN', 'SUPERVISOR', 'MECANICO'])
def ingreso_pausar(request, pk):
    """Registrar una pausa. Acceso: Admin, Supervisor, Mecánico."""
    ingreso = get_object_or_404(IngresoTaller, pk=pk)
    
    if ingreso.estado != 'EN_PROCESO':
        messages.warning(request, 'Solo se pueden pausar ingresos en proceso.')
        return redirect('ingreso_detail', pk=pk)
    
    if request.method == 'POST':
        form = PausaForm(request.POST)
        if form.is_valid():
            pausa = form.save(commit=False)
            pausa.ingreso = ingreso
            pausa.registrado_por = request.user
            pausa.save()
            
            ingreso.estado = 'EN_PAUSA'
            ingreso.save()
            
            messages.success(request, 'Pausa registrada correctamente.')
            return redirect('ingreso_detail', pk=pk)
    else:
        form = PausaForm()
    
    context = {'form': form, 'ingreso': ingreso}
    return render(request, 'ingresos/ingreso_pausar.html', context)


@login_required
@role_required(['ADMIN', 'SUPERVISOR', 'MECANICO'])
def ingreso_reanudar(request, pk):
    """Reanudar un ingreso pausado. Acceso: Admin, Supervisor, Mecánico."""
    ingreso = get_object_or_404(IngresoTaller, pk=pk)
    
    if ingreso.estado != 'EN_PAUSA':
        messages.warning(request, 'Este ingreso no está pausado.')
        return redirect('ingreso_detail', pk=pk)
    
    # Cerrar la última pausa activa
    pausa_activa = ingreso.pausas.filter(fecha_fin__isnull=True).first()
    if pausa_activa:
        pausa_activa.fecha_fin = timezone.now()
        pausa_activa.save()
    
    ingreso.estado = 'EN_PROCESO'
    ingreso.save()
    
    messages.success(request, 'Ingreso reanudado correctamente.')
    return redirect('ingreso_detail', pk=pk)


@login_required
@role_required(['ADMIN', 'SUPERVISOR'])
@login_required
@role_required(['ADMIN', 'SUPERVISOR'])
def ingreso_terminar(request, pk):
    """Terminar un ingreso. Acceso: Admin, Supervisor.
    
    Solo permite terminar si TODAS las tareas están COMPLETADAS o CANCELADAS.
    """
    ingreso = get_object_or_404(IngresoTaller, pk=pk)
    
    if ingreso.estado == 'TERMINADO':
        messages.warning(request, 'Este ingreso ya está terminado.')
        return redirect('ingreso_detail', pk=pk)
    
    # Verificar que todas las tareas estén completadas o canceladas
    tareas_pendientes = ingreso.tareas.exclude(estado__in=['COMPLETADA', 'CANCELADA']).count()
    
    if tareas_pendientes > 0:
        messages.error(
            request,
            f'❌ No se puede terminar el ingreso. Hay {tareas_pendientes} tarea(s) pendiente(s). '
            'Todas las tareas deben estar COMPLETADAS o CANCELADAS.'
        )
        return redirect('ingreso_detail', pk=pk)
    
    ingreso.estado = 'TERMINADO'
    ingreso.fecha_termino = timezone.now()
    ingreso.save()
    
    # Actualizar solicitud asociada a COMPLETADA (si existe)
    SolicitudIngreso.objects.filter(
        ingreso_taller=ingreso,
        estado='APROBADA'
    ).update(estado='COMPLETADA')
    
    # Crear notificación para el chofer si existe
    if ingreso.chofer:
        from notificaciones.models import Notificacion
        Notificacion.objects.create(
            usuario=ingreso.chofer,
            tipo='VEHICULO_LISTO_RETIRO',
            titulo=f'🎯 {ingreso.vehiculo.patente} - Listo para Retiro',
            mensaje=f'El vehículo {ingreso.vehiculo.patente} ({ingreso.vehiculo.marca} {ingreso.vehiculo.modelo}) ha sido terminado y está listo para retiro.',
            url=f'/ingresos/notificaciones/',
            metadata={
                'ingreso_id': ingreso.pk,
                'patente': ingreso.vehiculo.patente,
                'marca': ingreso.vehiculo.marca,
                'modelo': ingreso.vehiculo.modelo,
            }
        )
    
    messages.success(request, f'✅ Ingreso terminado. Duración total: {ingreso.duracion_total_minutos} minutos.')
    return redirect('ingreso_detail', pk=pk)


@login_required
@role_required(['ADMIN', 'SUPERVISOR', 'MECANICO'])
def tarea_create(request, ingreso_pk):
    """Crear nueva tarea para un ingreso. Acceso: Admin, Supervisor, Mecánico."""
    ingreso = get_object_or_404(IngresoTaller, pk=ingreso_pk)
    
    if request.method == 'POST':
        form = TareaForm(request.POST)
        if form.is_valid():
            tarea = form.save(commit=False)
            tarea.ingreso = ingreso
            tarea._usuario_modificador = request.user  # Para el signal
            tarea.save()
            messages.success(request, f'Tarea "{tarea.titulo}" creada.')
            return redirect('ingreso_detail', pk=ingreso_pk)
        else:
            # Mostrar errores del formulario en mensajes para facilitar depuración en UI
            # Esto ayuda a ver errores de validación que de otra forma pueden quedarse "silenciosos".
            messages.error(request, f'Errores en el formulario: {form.errors}')
    else:
        form = TareaForm()
    
    context = {'form': form, 'ingreso': ingreso}
    return render(request, 'ingresos/tarea_form.html', context)


@login_required
@role_required(['ADMIN', 'SUPERVISOR', 'MECANICO'])
@login_required
@role_required(['ADMIN', 'SUPERVISOR', 'MECANICO'])
def tarea_editar_estado(request, pk):
    """Editar solo estado, observaciones y repuestos de una tarea. Acceso: Admin, Supervisor, Mecánico."""
    tarea = get_object_or_404(Tarea, pk=pk)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado', tarea.estado)
        observaciones = request.POST.get('observaciones', '').strip()
        repuestos_utilizados = request.POST.get('repuestos_utilizados', '').strip()
        
        # Validar cambios de estado
        if nuevo_estado != tarea.estado:
            # Si pasa de PENDIENTE a EN_PROCESO, registrar fecha_inicio
            if tarea.estado == 'PENDIENTE' and nuevo_estado == 'EN_PROCESO':
                tarea.fecha_inicio = timezone.now()
            # Si se completa, calcular tiempo invertido
            elif nuevo_estado == 'COMPLETADA':
                tarea.fecha_completada = timezone.now()
                if tarea.fecha_inicio:
                    tarea.tiempo_invertido_minutos = tarea.tiempo_transcurrido_minutos
            
            tarea.estado = nuevo_estado
            messages.success(request, f'✅ Estado de la tarea cambió a {tarea.get_estado_display()}.')
        
        if observaciones:
            if tarea.observaciones:
                tarea.observaciones += f"\n[{timezone.now().strftime('%d/%m/%Y %H:%M')}] {observaciones}"
            else:
                tarea.observaciones = observaciones
            messages.success(request, 'Observaciones agregadas.')
        
        # Actualizar repuestos utilizados
        if repuestos_utilizados:
            tarea.repuestos_utilizados = repuestos_utilizados
            messages.success(request, 'Repuestos utilizados registrados.')
        
        tarea._usuario_modificador = request.user
        tarea.save()
        return redirect('tarea_detail', pk=pk)
    
    context = {
        'tarea': tarea,
        'ingreso': tarea.ingreso,
        'estados': Tarea.Estado.choices
    }
    return render(request, 'ingresos/tarea_editar_estado.html', context)


def tarea_edit(request, pk):
    """Editar una tarea existente. Acceso: Admin, Supervisor, Mecánico."""
    tarea = get_object_or_404(Tarea, pk=pk)
    ingreso = tarea.ingreso
    
    if request.method == 'POST':
        form = TareaForm(request.POST, instance=tarea)
        if form.is_valid():
            tarea = form.save(commit=False)
            tarea._usuario_modificador = request.user  # Para el signal
            tarea.save()
            messages.success(request, f'Tarea "{tarea.titulo}" actualizada correctamente.')
            return redirect('ingreso_detail', pk=ingreso.pk)
    else:
        form = TareaForm(instance=tarea)
    
    context = {
        'form': form,
        'ingreso': ingreso,
        'tarea': tarea,
        'editar': True
    }
    return render(request, 'ingresos/tarea_form.html', context)


@login_required
@role_required(['ADMIN', 'SUPERVISOR', 'MECANICO'])
def tarea_completar(request, pk):
    """Marcar tarea como completada. Acceso: Admin, Supervisor, Mecánico."""
    tarea = get_object_or_404(Tarea, pk=pk)
    
    tarea.estado = 'COMPLETADA'
    tarea.fecha_completada = timezone.now()
    # Calcular tiempo invertido automáticamente si la tarea fue iniciada
    if tarea.fecha_inicio:
        tarea.tiempo_invertido_minutos = tarea.tiempo_transcurrido_minutos
    tarea._usuario_modificador = request.user  # Para el signal
    tarea.save()
    
    messages.success(request, f'✅ Tarea "{tarea.titulo}" completada. Tiempo invertido: {tarea.tiempo_invertido_minutos} minutos.')
    
    # Redirigir a la vista de tareas del mecánico si viene de ahí
    referer = request.META.get('HTTP_REFERER', '')
    if 'mecanico_tareas' in referer:
        return redirect('mecanico_tareas')
    return redirect('tarea_detail', pk=pk)


@login_required
@role_required(['ADMIN', 'SUPERVISOR', 'MECANICO'])
def tarea_iniciar(request, pk):
    """Iniciar una tarea (cambiar a EN_PROCESO). Acceso: Admin, Supervisor, Mecánico."""
    tarea = get_object_or_404(Tarea, pk=pk)
    
    if tarea.estado == 'PENDIENTE':
        tarea.estado = 'EN_PROCESO'
        tarea.fecha_inicio = timezone.now()
        tarea.save()
        messages.success(request, f'✅ Tarea "{tarea.titulo}" iniciada.')
    else:
        messages.warning(request, f'No se puede iniciar una tarea en estado {tarea.get_estado_display()}.')
    
    # Redirigir a la vista de tareas del mecánico si viene de ahí
    referer = request.META.get('HTTP_REFERER', '')
    if 'mecanico_tareas' in referer:
        return redirect('mecanico_tareas')
    return redirect('tarea_detail', pk=pk)


@login_required
@role_required(['ADMIN', 'SUPERVISOR', 'MECANICO'])
def tarea_pausar(request, pk):
    """Pausar una tarea (cambiar a PAUSADA). Acceso: Admin, Supervisor, Mecánico."""
    tarea = get_object_or_404(Tarea, pk=pk)
    
    if tarea.estado == 'EN_PROCESO':
        tarea.estado = 'PAUSADA'
        tarea.save()
        messages.success(request, f'⏸ Tarea "{tarea.titulo}" pausada.')
    else:
        messages.warning(request, f'Solo se pueden pausar tareas en proceso.')
    
    # Redirigir a la vista de tareas del mecánico si viene de ahí
    referer = request.META.get('HTTP_REFERER', '')
    if 'mecanico_tareas' in referer:
        return redirect('mecanico_tareas')
    return redirect('tarea_detail', pk=pk)


@login_required
@role_required(['ADMIN', 'SUPERVISOR', 'MECANICO'])
def tarea_reanudar(request, pk):
    """Reanudar una tarea pausada (cambiar a EN_PROCESO). Acceso: Admin, Supervisor, Mecánico."""
    tarea = get_object_or_404(Tarea, pk=pk)
    
    if tarea.estado == 'PAUSADA':
        tarea.estado = 'EN_PROCESO'
        tarea.save()
        messages.success(request, f'▶ Tarea "{tarea.titulo}" reanudada.')
    else:
        messages.warning(request, f'Solo se pueden reanudar tareas pausadas.')
    
    # Redirigir a la vista de tareas del mecánico si viene de ahí
    referer = request.META.get('HTTP_REFERER', '')
    if 'mecanico_tareas' in referer:
        return redirect('mecanico_tareas')
    return redirect('tarea_detail', pk=pk)


@login_required
def tarea_detail(request, pk):
    """Vista detallada de una tarea con su historial completo."""
    tarea = get_object_or_404(
        Tarea.objects.select_related('ingreso__vehiculo', 'mecanico'),
        pk=pk
    )
    historial = tarea.historial.select_related('usuario').all()
    
    context = {
        'tarea': tarea,
        'historial': historial,
        'ingreso': tarea.ingreso,
    }
    return render(request, 'ingresos/tarea_detail.html', context)


@login_required
@role_required(['ADMIN', 'SUPERVISOR', 'MECANICO'])
def tarea_agregar_comentario(request, pk):
    """Agregar un comentario al historial de la tarea."""
    tarea = get_object_or_404(Tarea, pk=pk)
    
    if request.method == 'POST':
        comentario = request.POST.get('comentario', '').strip()
        if comentario:
            HistorialTarea.objects.create(
                tarea=tarea,
                tipo_cambio='COMENTARIO',
                descripcion=comentario,
                usuario=request.user
            )
            messages.success(request, 'Comentario agregado correctamente.')
        else:
            messages.error(request, 'El comentario no puede estar vacío.')
    
    return redirect('tarea_detail', pk=pk)


@login_required
def documento_upload(request, ingreso_pk):
    """Subir documento/foto. Acceso: Todos los roles autenticados."""
    ingreso = get_object_or_404(IngresoTaller, pk=ingreso_pk)
    
    if request.method == 'POST':
        form = DocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.ingreso = ingreso
            documento.vehiculo = ingreso.vehiculo
            documento.subido_por = request.user
            documento.nombre_original = request.FILES['archivo'].name
            documento.save()
            messages.success(request, 'Documento subido correctamente.')
            return redirect('ingreso_detail', pk=ingreso_pk)
    else:
        form = DocumentoForm()
    
    context = {'form': form, 'ingreso': ingreso}
    return render(request, 'ingresos/documento_upload.html', context)


@login_required
@role_required(['GUARDIA'])
def guard_dashboard(request):
    """Dashboard para guardias: registro de entrada/salida de vehículos."""
    from .forms import GuardRegistroForm, GuardSalidaForm
    
    today = timezone.now().date()
    # Ingresos programados hoy
    ingresos_hoy = IngresoTaller.objects.filter(fecha_programada__date=today)
    count_hoy = ingresos_hoy.count()

    # Semana actual (lunes a domingo)
    semana_inicio = today - timezone.timedelta(days=today.weekday())
    semana_fin = semana_inicio + timezone.timedelta(days=6)
    ingresos_semana = IngresoTaller.objects.filter(fecha_programada__date__range=(semana_inicio, semana_fin))
    count_semana = ingresos_semana.count()

    # Total ingresos
    count_total = IngresoTaller.objects.count()

    # En el taller ahora (EN_PROCESO o EN_PAUSA)
    ingresos_en_taller = IngresoTaller.objects.filter(estado__in=['EN_PROCESO', 'EN_PAUSA']).select_related('vehiculo', 'chofer')
    count_en_taller = ingresos_en_taller.count()

    form = GuardRegistroForm()
    form_salida = GuardSalidaForm()

    if request.method == 'POST':
        # Diferenciar entre entrada y salida
        tipo = request.POST.get('tipo', 'entrada')
        
        if tipo == 'salida':
            form_salida = GuardSalidaForm(request.POST)
            if form_salida.is_valid():
                patente = form_salida.cleaned_data['patente'].strip().upper()
                observaciones_salida = form_salida.cleaned_data.get('observaciones', '').strip()
                
                # Buscar el registro más reciente sin salida registrada
                registro = RegistroGuardia.objects.filter(
                    patente__iexact=patente,
                    fecha_salida__isnull=True
                ).order_by('-fecha_entrada').first()
                
                if registro:
                    # Actualizar con fecha de salida
                    registro.fecha_salida = timezone.now()
                    if observaciones_salida:
                        # Agregar observación de salida a las existentes
                        if registro.observaciones:
                            registro.observaciones += f"\n[SALIDA] {observaciones_salida}"
                        else:
                            registro.observaciones = f"[SALIDA] {observaciones_salida}"
                    registro.save()
                    duracion = registro.duracion_minutos or 0
                    horas = duracion // 60
                    minutos = duracion % 60
                    duracion_str = f"{horas}h {minutos}min" if horas > 0 else f"{minutos}min"
                    messages.success(request, f'✅ Salida registrada: {patente} | Tiempo: {duracion_str}')
                else:
                    messages.error(request, f'❌ No hay registro de entrada sin salida para {patente}.')
                
                return redirect('guard_dashboard')
        else:
            form = GuardRegistroForm(request.POST, request.FILES)
            if form.is_valid():
                # Validate uploaded photos (if any)
                files = request.FILES.getlist('photos') if request.FILES else []
                if len(files) > MAX_PHOTOS:
                    messages.error(request, f'No se permiten más de {MAX_PHOTOS} fotos (subiste {len(files)}).')
                    context = {
                        'count_hoy': count_hoy,
                        'count_semana': count_semana,
                        'count_total': count_total,
                        'count_en_taller': count_en_taller,
                        'ingresos_en_taller': ingresos_en_taller,
                        'form': form,
                        'form_salida': form_salida,
                    }
                    return render(request, 'ingresos/guard_dashboard.html', context)

                for f in files:
                    if isinstance(f, UploadedFile) and f.size > MAX_PHOTO_SIZE_MB * 1024 * 1024:
                        messages.error(request, f'La imagen {getattr(f, "name", "(sin nombre)")} supera el tamaño máximo de {MAX_PHOTO_SIZE_MB} MB.')
                        context = {
                            'count_hoy': count_hoy,
                            'count_semana': count_semana,
                            'count_total': count_total,
                            'count_en_taller': count_en_taller,
                            'ingresos_en_taller': ingresos_en_taller,
                            'form': form,
                            'form_salida': form_salida,
                        }
                        return render(request, 'ingresos/guard_dashboard.html', context)
                    content_type = getattr(f, 'content_type', '')
                    if content_type and not str(content_type).startswith('image/'):
                        messages.error(request, f'El archivo {getattr(f, "name", "(sin nombre)")} no es una imagen válida.')
                        context = {
                            'count_hoy': count_hoy,
                            'count_semana': count_semana,
                            'count_total': count_total,
                            'count_en_taller': count_en_taller,
                            'ingresos_en_taller': ingresos_en_taller,
                            'form': form,
                            'form_salida': form_salida,
                        }
                        return render(request, 'ingresos/guard_dashboard.html', context)
                    try:
                        img = Image.open(f)
                        img.verify()
                        try:
                            f.seek(0)
                        except Exception:
                            pass
                    except (UnidentifiedImageError, OSError):
                        messages.error(request, f'El archivo {getattr(f, "name", "(sin nombre)")} no es una imagen válida.')
                        context = {
                            'count_hoy': count_hoy,
                            'count_semana': count_semana,
                            'count_total': count_total,
                            'count_en_taller': count_en_taller,
                            'ingresos_en_taller': ingresos_en_taller,
                            'form': form,
                            'form_salida': form_salida,
                        }
                        return render(request, 'ingresos/guard_dashboard.html', context)

                patente = form.cleaned_data['patente'].strip()
                marca = form.cleaned_data.get('marca') or 'Desconocida'
                modelo = request.POST.get('modelo', '').strip() or 'Desconocido'
                motivo = form.cleaned_data.get('motivo', '').strip()
                chofer_nombre = form.cleaned_data.get('chofer_nombre', '').strip()

                vehiculo = Vehiculo.objects.filter(patente__iexact=patente).first()
                if not vehiculo:
                    # Crear vehículo mínimo si no existe
                    try:
                        año_default = timezone.now().year
                    except Exception:
                        año_default = 0
                    vehiculo = Vehiculo.objects.create(patente=patente, marca=marca, modelo='Desconocido', año=año_default)
                else:
                    # Actualizar marca si se proporcionó
                    if marca and vehiculo.marca != marca:
                        vehiculo.marca = marca
                        vehiculo.save()

                # Intentar encontrar chofer por nombre (si se proporciona)
                chofer = None
                if chofer_nombre:
                    chofer = Usuario.objects.filter(nombre__iexact=chofer_nombre, activo=True).first()
                    if not chofer:
                        chofer = Usuario.objects.filter(nombre__icontains=chofer_nombre, activo=True).first()

                # Crear RegistroGuardia (entrada)
                registro = RegistroGuardia.objects.create(
                    vehiculo=vehiculo,
                    patente=patente,
                    marca=marca,
                    modelo=modelo,
                    motivo=motivo or '',
                    chofer_nombre=chofer_nombre,
                    chofer=chofer,
                    observaciones='Registro de guardia',
                    registrado_por=request.user
                )

                # Auto-vincular con IngresoTaller si existe uno programado
                # Buscar ingreso programado más cercano (hoy o próximos días, sin límite)
                ingreso_programado = IngresoTaller.objects.filter(
                    vehiculo=vehiculo,
                    estado='PROGRAMADO',
                    fecha_programada__gte=timezone.now().date()  # Hoy en adelante
                ).order_by('fecha_programada').first()
                
                if ingreso_programado and not ingreso_programado.registro_guardia:
                    ingreso_programado.registro_guardia = registro
                    ingreso_programado.save()
                    messages.success(
                        request,
                        f'✅ Entrada registrada: {vehiculo.patente} | Auto-vinculado con ingreso programado'
                    )
                else:
                    messages.success(request, f'✅ Entrada registrada: {vehiculo.patente} (ID {registro.pk})')
                
                return redirect('guard_dashboard')

    # Obtener últimos registros del guardia actual
    ultimos_registros = RegistroGuardia.objects.filter(
        registrado_por=request.user
    ).select_related('vehiculo', 'chofer').order_by('-fecha_entrada')[:20]

    context = {
        'count_hoy': count_hoy,
        'count_semana': count_semana,
        'count_total': count_total,
        'count_en_taller': count_en_taller,
        'ingresos_en_taller': ingresos_en_taller,
        'ultimos_registros': ultimos_registros,
        'form': form,
        'form_salida': form_salida,
    }
    return render(request, 'ingresos/guard_dashboard.html', context)


@login_required
@role_required(['GUARDIA'])
def guard_export_registros(request):
    """Exportar los registros (entradas/salidas) creados por el guardia autenticado."""
    registros = RegistroGuardia.objects.filter(registrado_por=request.user).order_by('-fecha_entrada')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f"registros_guardia_{request.user.get_username()}_{timezone.now().strftime('%Y%m%d')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    # BOM para Excel
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Patente', 'Marca', 'Chofer', 'Fecha Entrada', 'Fecha Salida', 'Duración (min)', 'Motivo', 'Observaciones'])

    for r in registros:
        writer.writerow([
            r.patente,
            r.marca,
            r.chofer_nombre or (r.chofer.nombre if r.chofer else ''),
            r.fecha_entrada.strftime('%Y-%m-%d %H:%M') if r.fecha_entrada else '',
            r.fecha_salida.strftime('%Y-%m-%d %H:%M') if r.fecha_salida else '',
            r.duracion_minutos or '',
            (r.motivo or '').replace('\n', ' '),
            (r.observaciones or '').replace('\n', ' '),
        ])

    return response


@login_required
@role_required('MECANICO')
def mecanico_tareas(request):
    """
    Vista de tareas asignadas al mecánico autenticado.
    Muestra solo las tareas asignadas a este mecánico con detalle del vehículo.
    """
    mecanico = request.user
    
    # Obtener todas las tareas del mecánico
    tareas = Tarea.objects.filter(
        mecanico=mecanico
    ).select_related(
        'ingreso__vehiculo'
    ).order_by('-fecha_asignacion')
    
    # Estadísticas
    stats = {
        'total': tareas.count(),
        'pendientes': tareas.filter(estado='PENDIENTE').count(),
        'en_proceso': tareas.filter(estado='EN_PROCESO').count(),
        'completadas': tareas.filter(estado='COMPLETADA').count(),
        'canceladas': tareas.filter(estado='CANCELADA').count(),
    }
    
    # Filtros
    estado_filter = request.GET.get('estado', '')
    if estado_filter:
        tareas = tareas.filter(estado=estado_filter)
    
    context = {
        'tareas': tareas,
        'stats': stats,
        'estado_filter': estado_filter,
    }
    return render(request, 'ingresos/mecanico_tareas.html', context)


# ============================================================================
# VISTAS PARA CHOFER - SOLICITUD DE INGRESO AL TALLER
# ============================================================================

@login_required
@role_required('CHOFER')
def chofer_solicitar_ingreso(request):
    """
    Vista para que el chofer solicite ingreso de un vehículo al taller.
    """
    chofer = request.user
    
    if request.method == 'POST':
        form = SolicitudIngresoForm(request.POST, chofer=chofer)
        if form.is_valid():
            solicitud = form.save()
            messages.success(
                request,
                f'✅ Solicitud de ingreso enviada correctamente para {solicitud.vehiculo.patente}. '
                'El supervisor revisará tu solicitud pronto.'
            )
            return redirect('chofer_mis_solicitudes')
    else:
        form = SolicitudIngresoForm(chofer=chofer)
    
    context = {
        'form': form,
        'titulo': 'Solicitar Ingreso al Taller',
    }
    return render(request, 'ingresos/chofer_solicitar_ingreso.html', context)


@login_required
@role_required('CHOFER')
def chofer_mis_solicitudes(request):
    """
    Vista para que el chofer vea el estado de sus solicitudes.
    """
    chofer = request.user
    
    # Obtener todas las solicitudes del chofer
    solicitudes = SolicitudIngreso.objects.filter(
        chofer=chofer
    ).select_related('vehiculo', 'supervisor').order_by('-fecha_solicitud')
    
    # Filtro por estado
    estado_filter = request.GET.get('estado', '')
    if estado_filter:
        solicitudes = solicitudes.filter(estado=estado_filter)
    
    # Estadísticas
    stats = {
        'total': SolicitudIngreso.objects.filter(chofer=chofer).count(),
        'pendientes': SolicitudIngreso.objects.filter(chofer=chofer, estado='PENDIENTE').count(),
        'aprobadas': SolicitudIngreso.objects.filter(chofer=chofer, estado='APROBADA').count(),
        'completadas': SolicitudIngreso.objects.filter(chofer=chofer, estado__in=['COMPLETADA', 'RETIRADA']).count(),
    }
    
    context = {
        'solicitudes': solicitudes,
        'stats': stats,
        'estado_filter': estado_filter,
    }
    return render(request, 'ingresos/chofer_mis_solicitudes.html', context)


@login_required
@role_required('CHOFER')
def chofer_notificaciones(request):
    """
    Vista de notificaciones para el chofer.
    Muestra los vehículos listos para retiro (estado TERMINADO) y notificaciones del sistema.
    """
    from notificaciones.models import Notificacion
    
    chofer = request.user
    
    # Notificaciones del sistema (vehículos listos para retiro) - Filtrar primero, luego slice
    notificaciones = Notificacion.objects.filter(
        usuario=chofer,
        tipo='VEHICULO_LISTO_RETIRO'
    ).order_by('-fecha_creacion')[:20]
    
    # Contar notificaciones nuevas antes de hacer slice
    notificaciones_nuevas = Notificacion.objects.filter(
        usuario=chofer,
        tipo='VEHICULO_LISTO_RETIRO',
        leida=False
    ).count()
    
    # Ingresos terminados (listos para retiro)
    ingresos_terminados = IngresoTaller.objects.filter(
        chofer=chofer,
        estado='TERMINADO'
    ).select_related('vehiculo', 'supervisor').order_by('-fecha_termino')
    
    # Ingresos en proceso
    ingresos_en_proceso = IngresoTaller.objects.filter(
        chofer=chofer,
        estado__in=['PROGRAMADO', 'EN_PROCESO', 'EN_PAUSA']
    ).select_related('vehiculo', 'supervisor').order_by('-fecha_programada')
    
    # Estadísticas
    stats = {
        'listos_retiro': ingresos_terminados.count(),
        'en_taller': ingresos_en_proceso.count(),
        'nuevas_notificaciones': notificaciones_nuevas,
    }
    
    context = {
        'notificaciones': notificaciones,
        'ingresos_terminados': ingresos_terminados,
        'ingresos_en_proceso': ingresos_en_proceso,
        'stats': stats,
    }
    return render(request, 'ingresos/chofer_notificaciones.html', context)


# ============================================================================
# VISTAS PARA SUPERVISOR - NOTIFICACIONES Y APROBACIÓN DE SOLICITUDES
# ============================================================================

@login_required
@role_required('SUPERVISOR')
def supervisor_notificaciones(request):
    """
    Vista de notificaciones para el supervisor.
    Muestra las solicitudes pendientes de aprobación.
    """
    supervisor = request.user
    
    # Solicitudes pendientes (para todos los supervisores)
    solicitudes_pendientes = SolicitudIngreso.objects.filter(
        estado='PENDIENTE'
    ).select_related('vehiculo', 'chofer').order_by('-fecha_solicitud')
    
    # Solicitudes procesadas por este supervisor
    mis_solicitudes = SolicitudIngreso.objects.filter(
        supervisor=supervisor
    ).select_related('vehiculo', 'chofer').order_by('-fecha_respuesta')[:10]
    
    # Estadísticas
    stats = {
        'pendientes': SolicitudIngreso.objects.filter(estado='PENDIENTE').count(),
        'aprobadas_hoy': SolicitudIngreso.objects.filter(
            supervisor=supervisor,
            estado='APROBADA',
            fecha_respuesta__date=timezone.now().date()
        ).count(),
        'rechazadas': SolicitudIngreso.objects.filter(
            supervisor=supervisor,
            estado='RECHAZADA'
        ).count(),
    }
    
    context = {
        'solicitudes_pendientes': solicitudes_pendientes,
        'mis_solicitudes': mis_solicitudes,
        'stats': stats,
    }
    return render(request, 'ingresos/supervisor_notificaciones.html', context)


@login_required
@role_required('SUPERVISOR')
def supervisor_aprobar_solicitud(request, solicitud_id):
    """
    Vista para que el supervisor apruebe una solicitud de ingreso.
    """
    supervisor = request.user
    solicitud = get_object_or_404(SolicitudIngreso, pk=solicitud_id, estado='PENDIENTE')
    
    if request.method == 'POST':
        # Crear el ingreso al taller basado en la solicitud
        ingreso = IngresoTaller.objects.create(
            vehiculo=solicitud.vehiculo,
            fecha_programada=solicitud.fecha_estimada_ingreso,
            motivo=solicitud.motivo or 'Solicitud de ingreso del chofer',
            chofer=solicitud.chofer,
            supervisor=supervisor,
            estado=IngresoTaller.Estado.PROGRAMADO,
        )
        
        # Actualizar solicitud
        solicitud.estado = 'APROBADA'
        solicitud.supervisor = supervisor
        solicitud.fecha_respuesta = timezone.now()
        solicitud.ingreso_taller = ingreso
        solicitud.save()
        
        messages.success(request, f'✅ Solicitud aprobada. Ingreso creado para {solicitud.vehiculo.patente}')
        return redirect('supervisor_notificaciones')
    
    context = {
        'solicitud': solicitud,
    }
    return render(request, 'ingresos/supervisor_aprobar_solicitud.html', context)


@login_required
@role_required('SUPERVISOR')
def supervisor_agendar_solicitud(request, solicitud_id):
    """
    Vista para que el supervisor elija una fecha/hora (scheduler) para aprobar
    una solicitud pendiente. Muestra disponibilidad por hora y máquina para los próximos 7 días.
    """
    supervisor = request.user
    solicitud = get_object_or_404(SolicitudIngreso, pk=solicitud_id, estado='PENDIENTE')

    # Rango de días y horas (por defecto 7 días, horas 8-17). Se puede
    # ampliar con el parámetro GET `count` para mostrar más días.
    try:
        count = int(request.GET.get('count', 4))
    except Exception:
        count = 4

    # Obtener máquinas activas
    from .models import Maquina
    maquinas = Maquina.objects.filter(activa=True).order_by('tipo', 'numero')

    today = timezone.localtime(timezone.now())
    days = [today.date() + timedelta(days=i) for i in range(0, max(1, count))]
    hours = list(range(8, 18))  # 8:00 .. 17:00

    # Construir slots por máquina y marcar ocupados
    slots = []
    for day in days:
        # Por cada día, crear un grupo de filas (una por máquina)
        day_group = {'day': day, 'maquinas': []}
        
        for maquina in maquinas:
            row = []
            for h in hours:
                slot_dt = datetime(day.year, day.month, day.day, h, 0, 0)
                aware_slot = make_aware(slot_dt)
                # Solo agregar slots futuros
                if aware_slot < today:
                    continue
                # Comprobar si existe un ingreso programado en esa hora para esa máquina
                inicio = aware_slot
                fin = aware_slot + timedelta(hours=1)
                ocupado = IngresoTaller.objects.filter(
                    fecha_programada__gte=inicio,
                    fecha_programada__lt=fin,
                    maquina=maquina,
                    estado__in=['PROGRAMADO', 'EN_PROCESO']
                ).exists() or SolicitudIngreso.objects.filter(
                    fecha_estimada_ingreso__gte=inicio,
                    fecha_estimada_ingreso__lt=fin,
                    estado='APROBADA'
                ).exists()
                # Incluir formato compatible con selector: "YYYY-MM-DDTHH:MM|MAQUINA_ID"
                dt_str = aware_slot.strftime('%Y-%m-%dT%H:%M')
                slot_value = f"{dt_str}|{maquina.pk}"
                row.append({'dt': aware_slot, 'dt_str': dt_str, 'ocupado': ocupado, 'slot_value': slot_value})
            
            if row:  # Solo agregar si hay slots disponibles
                day_group['maquinas'].append({
                    'maquina': maquina,
                    'row': row
                })
        
        if day_group['maquinas']:  # Solo agregar si hay máquinas con slots
            slots.append(day_group)

    if request.method == 'POST':
        slot_iso = request.POST.get('slot')
        if not slot_iso:
            messages.error(request, 'Debes seleccionar una fecha/hora y máquina válidas.')
            return redirect('supervisor_agendar_solicitud', solicitud_id=solicitud.pk)

        # slot_iso tiene formato: "YYYY-MM-DDTHH:MM|MAQUINA_ID"
        maquina_id = None
        try:
            if '|' in slot_iso:
                fecha_str, maquina_id = slot_iso.rsplit('|', 1)
                chosen = datetime.fromisoformat(fecha_str)
                chosen = make_aware(chosen)
                maquina = Maquina.objects.get(pk=int(maquina_id), activa=True)
            else:
                # Compatibilidad con formato antiguo
                chosen = datetime.fromisoformat(slot_iso)
                chosen = make_aware(chosen)
                maquina = None
        except Exception as e:
            messages.error(request, 'Formato de fecha/hora/máquina inválido.')
            return redirect('supervisor_agendar_solicitud', solicitud_id=solicitud.pk)

        # Verificar ocupación del slot en la máquina específica
        inicio = chosen
        fin = chosen + timedelta(hours=1)
        
        if maquina:
            ocupado = IngresoTaller.objects.filter(
                fecha_programada__gte=inicio,
                fecha_programada__lt=fin,
                maquina=maquina,
                estado__in=['PROGRAMADO', 'EN_PROCESO']
            ).exists()
        else:
            ocupado = False

        if ocupado:
            messages.error(request, 'La máquina seleccionada ya está ocupada en ese horario. Elige otro.')
            return redirect('supervisor_agendar_solicitud', solicitud_id=solicitud.pk)

        # Obtener datos adicionales del formulario
        motivo = request.POST.get('motivo', solicitud.motivo or 'Solicitud de ingreso del chofer')
        repuesto_necesario = request.POST.get('repuesto_necesario', '').strip()
        observaciones = request.POST.get('observaciones', '').strip()
        kilometraje_ingreso = request.POST.get('kilometraje_ingreso', '').strip()

        # Crear ingreso con los datos completos
        ingreso = IngresoTaller.objects.create(
            vehiculo=solicitud.vehiculo,
            fecha_programada=chosen,
            motivo=motivo,
            chofer=solicitud.chofer,
            supervisor=supervisor,
            estado=IngresoTaller.Estado.PROGRAMADO,
            repuesto_necesario=repuesto_necesario,
            observaciones=observaciones,
            kilometraje_ingreso=int(kilometraje_ingreso) if kilometraje_ingreso else None,
            maquina=maquina
        )

        solicitud.estado = 'APROBADA'
        solicitud.supervisor = supervisor
        solicitud.fecha_respuesta = timezone.now()
        solicitud.ingreso_taller = ingreso
        solicitud.fecha_estimada_ingreso = chosen
        solicitud.save()

        maquina_str = f" en {maquina.nombre}" if maquina else ""
        messages.success(request, f'Solicitud agendada y aprobada para {solicitud.vehiculo.patente} el {chosen.strftime("%d/%m/%Y %H:%M")}{maquina_str}.')
        return redirect('supervisor_notificaciones')

    context = {
        'solicitud': solicitud,
        'slots': slots,
        'count': count,
    }
    return render(request, 'ingresos/supervisor_agendar_solicitud.html', context)


@login_required
@role_required('SUPERVISOR')
def supervisor_rechazar_solicitud(request, solicitud_id):
    """
    Vista para que el supervisor rechace una solicitud de ingreso.
    """
    supervisor = request.user
    solicitud = get_object_or_404(SolicitudIngreso, pk=solicitud_id, estado='PENDIENTE')
    
    if request.method == 'POST':
        observaciones = request.POST.get('observaciones', '')
        
        solicitud.estado = 'RECHAZADA'
        solicitud.supervisor = supervisor
        solicitud.fecha_respuesta = timezone.now()
        solicitud.observaciones_supervisor = observaciones
        solicitud.save()
        
        messages.info(request, f'Solicitud rechazada para {solicitud.vehiculo.patente}')
        return redirect('supervisor_notificaciones')
    
    context = {
        'solicitud': solicitud,
    }
    return render(request, 'ingresos/supervisor_rechazar_solicitud.html', context)


@login_required
@role_required(['ADMIN', 'SUPERVISOR'])
def ingreso_eliminar(request, pk):
    """
    Eliminar un ingreso con confirmación.
    Acceso: Admin, Supervisor.
    """
    ingreso = get_object_or_404(IngresoTaller, pk=pk)
    
    if request.method == 'POST':
        ingreso.delete()
        messages.success(request, 'Ingreso eliminado correctamente.')
        return redirect('ingresos_list')
    
    return render(request, 'ingresos/ingreso_confirm_delete.html', {'ingreso': ingreso})


@login_required
def api_vehiculo_por_patente(request):
    """API para obtener datos del vehículo por patente (para autocompletar en guardia)."""
    from django.http import JsonResponse
    
    patente = request.GET.get('patente', '').strip().upper()
    
    if not patente or len(patente) < 2:
        return JsonResponse({'error': 'Patente inválida'}, status=400)
    
    # Buscar el vehículo (case-insensitive)
    vehiculo = Vehiculo.objects.filter(patente__iexact=patente).first()
    
    if vehiculo:
        return JsonResponse({
            'marca': vehiculo.marca or '',
            'modelo': vehiculo.modelo or '',
            'success': True
        })
    else:
        return JsonResponse({
            'error': 'Vehículo no encontrado',
            'marca': '',
            'modelo': '',
            'success': False
        })