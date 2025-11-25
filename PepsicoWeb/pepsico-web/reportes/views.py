from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Avg, Sum, Q, F, ExpressionWrapper, DurationField
from django.utils import timezone
from datetime import timedelta
from core.decorators import role_required
from ingresos.models import IngresoTaller, Tarea, Pausa
from vehiculos.models import Vehiculo
from usuarios.models import Usuario
import csv
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from io import BytesIO
from .utils import parse_spanish_date


@login_required
@role_required(['ADMIN', 'EHS'])
def dashboard_reportes(request):
    """Dashboard ejecutivo con KPIs y gráficos."""
    
    # Filtros de fecha
    fecha_desde_param = request.GET.get('fecha_desde')
    fecha_hasta_param = request.GET.get('fecha_hasta')
    
    # Determinar rango de fechas
    usar_filtro_fechas = False
    if fecha_desde_param or fecha_hasta_param:
        usar_filtro_fechas = True
        fecha_desde = fecha_desde_param or (timezone.now() - timedelta(days=365)).date()
        fecha_hasta = fecha_hasta_param or timezone.now().date()
    else:
        # Si no se especifican fechas, usar todas las fechas (sin filtro)
        fecha_desde = None
        fecha_hasta = None
    
    # KPIs principales
    if usar_filtro_fechas and fecha_desde and fecha_hasta:
        ingresos = IngresoTaller.objects.filter(
            fecha_programada__range=[fecha_desde, fecha_hasta]
        )
    else:
        ingresos = IngresoTaller.objects.all()
        # Para mostrar en contexto cuando no hay filtro
        fecha_desde = IngresoTaller.objects.order_by('fecha_programada').first()
        fecha_hasta = IngresoTaller.objects.order_by('-fecha_programada').first()
        if fecha_desde:
            fecha_desde = fecha_desde.fecha_programada.date()
        if fecha_hasta:
            fecha_hasta = fecha_hasta.fecha_programada.date()
    
    # 1. Tiempo promedio en taller (solo terminados o retirados)
    ingresos_terminados = ingresos.filter(estado__in=['TERMINADO', 'RETIRADO'])
    tiempo_promedio_minutos = 0
    tiempo_promedio_formateado = "0 min"
    total_terminados = ingresos_terminados.count()
    
    if ingresos_terminados.exists():
        tiempos = [ing.duracion_total_minutos for ing in ingresos_terminados if ing.duracion_total_minutos]
        if tiempos:
            tiempo_promedio_minutos = sum(tiempos) / len(tiempos)
            # Formatear a horas y minutos
            horas = int(tiempo_promedio_minutos // 60)
            minutos = int(tiempo_promedio_minutos % 60)
            if horas > 0:
                tiempo_promedio_formateado = f"{horas}h {minutos}min"
            else:
                tiempo_promedio_formateado = f"{minutos}min"
    
    # 2. Vehículos por estado
    vehiculos_por_estado = {
        'programados': ingresos.filter(estado='PROGRAMADO').count(),
        'en_proceso': ingresos.filter(estado='EN_PROCESO').count(),
        'en_pausa': ingresos.filter(estado='EN_PAUSA').count(),
        'terminados': ingresos.filter(estado__in=['TERMINADO', 'RETIRADO']).count(),
    }
    
    # 3. Productividad por mecánico
    mecanicos = Usuario.objects.filter(rol='MECANICO', activo=True)
    productividad_mecanicos = []
    for mecanico in mecanicos:
        tareas_completadas = Tarea.objects.filter(
            mecanico=mecanico,
            estado='COMPLETADA',
            fecha_completada__range=[fecha_desde, fecha_hasta]
        ).count()
        productividad_mecanicos.append({
            'nombre': mecanico.nombre,
            'tareas': tareas_completadas
        })
    
    # 4. Ingresos por mes (últimos 6 meses)
    ingresos_por_mes = []
    for i in range(5, -1, -1):
        mes = timezone.now() - timedelta(days=30*i)
        count = IngresoTaller.objects.filter(
            fecha_programada__year=mes.year,
            fecha_programada__month=mes.month
        ).count()
        ingresos_por_mes.append({
            'mes': mes.strftime('%b %Y'),
            'count': count
        })
    
    # 5. Top 5 vehículos con más ingresos
    top_vehiculos = Vehiculo.objects.annotate(
        num_ingresos=Count('ingresos')
    ).order_by('-num_ingresos')[:5]
    
    context = {
        'tiempo_promedio': tiempo_promedio_formateado,
        'tiempo_promedio_minutos': round(tiempo_promedio_minutos, 2),
        'total_ingresos': ingresos.count(),
        'total_terminados': total_terminados,
        'vehiculos_por_estado': vehiculos_por_estado,
        'productividad_mecanicos': productividad_mecanicos,
        'ingresos_por_mes': ingresos_por_mes,
        'top_vehiculos': top_vehiculos,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'usar_filtro_fechas': usar_filtro_fechas,
    }
    
    return render(request, 'reportes/dashboard.html', context)


@login_required
@role_required(['ADMIN', 'SUPERVISOR'])
def reporte_tiempos(request):
    """Reporte detallado de tiempos de taller."""
    
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    estado = request.GET.get('estado', '')
    
    if not fecha_desde:
        fecha_desde = (timezone.now() - timedelta(days=30)).date()
    if not fecha_hasta:
        fecha_hasta = timezone.now().date()
    
    ingresos = IngresoTaller.objects.filter(
        fecha_programada__range=[fecha_desde, fecha_hasta]
    ).select_related('vehiculo', 'supervisor')
    
    if estado:
        ingresos = ingresos.filter(estado=estado)
    
    # Calcular estadísticas
    ingresos_data = []
    for ingreso in ingresos:
        ingresos_data.append({
            'ingreso': ingreso,
            'duracion_minutos': ingreso.duracion_total_minutos,
            'duracion_horas': round(ingreso.duracion_total_minutos / 60, 2) if ingreso.duracion_total_minutos else 0,
            'num_pausas': ingreso.pausas.count(),
        })
    
    context = {
        'ingresos_data': ingresos_data,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'estado': estado,
        'estados': IngresoTaller.Estado.choices,
    }
    
    return render(request, 'reportes/reporte_tiempos.html', context)


@login_required
@role_required(['ADMIN', 'SUPERVISOR'])
def reporte_productividad(request):
    """Reporte de productividad por mecánico."""
    
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    if not fecha_desde:
        fecha_desde = (timezone.now() - timedelta(days=30)).date()
    if not fecha_hasta:
        fecha_hasta = timezone.now().date()
    
    mecanicos = Usuario.objects.filter(rol='MECANICO', activo=True)
    
    mecanicos_data = []
    for mecanico in mecanicos:
        tareas = Tarea.objects.filter(
            mecanico=mecanico,
            fecha_asignacion__range=[fecha_desde, fecha_hasta]
        )
        
        tareas_completadas = tareas.filter(estado='COMPLETADA').count()
        tareas_pendientes = tareas.filter(estado='PENDIENTE').count()
        tareas_en_proceso = tareas.filter(estado='EN_PROCESO').count()
        
        mecanicos_data.append({
            'mecanico': mecanico,
            'total_tareas': tareas.count(),
            'completadas': tareas_completadas,
            'pendientes': tareas_pendientes,
            'en_proceso': tareas_en_proceso,
            'porcentaje_completadas': round((tareas_completadas / tareas.count() * 100) if tareas.count() > 0 else 0, 2)
        })
    
    context = {
        'mecanicos_data': mecanicos_data,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    }
    
    return render(request, 'reportes/reporte_productividad.html', context)


@login_required
@role_required(['ADMIN', 'SUPERVISOR'])
def exportar_reporte_csv(request):
    """Exportar reporte a CSV."""
    
    tipo = request.GET.get('tipo', 'tiempos')
    fecha_desde_str = request.GET.get('fecha_desde', '')
    fecha_hasta_str = request.GET.get('fecha_hasta', '')
    
    # Parse Spanish formatted dates
    fecha_desde = parse_spanish_date(fecha_desde_str) if fecha_desde_str else (timezone.now() - timedelta(days=30)).date()
    fecha_hasta = parse_spanish_date(fecha_hasta_str) if fecha_hasta_str else timezone.now().date()
    
    # Validate dates
    if not fecha_desde or not fecha_hasta:
        return HttpResponse('❌ Error en el formato de fechas. Use DD de mes de YYYY (Ej: 20 de octubre de 2025)', status=400)
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="reporte_{tipo}_{timezone.now().strftime("%Y%m%d")}.csv"'
    response.write('\ufeff')  # BOM para Excel
    
    writer = csv.writer(response, delimiter=';')
    
    if tipo == 'tiempos':
        writer.writerow(['Patente', 'Fecha Ingreso', 'Estado', 'Duración (min)', 'Supervisor', 'Motivo'])
        
        ingresos = IngresoTaller.objects.filter(
            fecha_programada__range=[fecha_desde, fecha_hasta]
        ).select_related('vehiculo', 'supervisor')
        
        for ingreso in ingresos:
            writer.writerow([
                ingreso.vehiculo.patente,
                ingreso.fecha_programada.strftime('%Y-%m-%d'),
                ingreso.get_estado_display(),
                ingreso.duracion_total_minutos or 0,
                ingreso.supervisor.nombre if ingreso.supervisor else '',
                ingreso.motivo
            ])
    
    elif tipo == 'productividad':
        writer.writerow(['Mecánico', 'Total Tareas', 'Completadas', 'Pendientes', 'En Proceso', '% Completadas'])
        
        mecanicos = Usuario.objects.filter(rol='MECANICO', activo=True)
        
        for mecanico in mecanicos:
            tareas = Tarea.objects.filter(
                mecanico=mecanico,
                fecha_asignacion__range=[fecha_desde, fecha_hasta]
            )
            
            total = tareas.count()
            completadas = tareas.filter(estado='COMPLETADA').count()
            pendientes = tareas.filter(estado='PENDIENTE').count()
            en_proceso = tareas.filter(estado='EN_PROCESO').count()
            porcentaje_completadas = round((completadas / total * 100) if total > 0 else 0, 2)
            
            writer.writerow([
                mecanico.nombre,
                total,
                completadas,
                pendientes,
                en_proceso,
                porcentaje_completadas
            ])
    
    return response

@login_required
@role_required(['ADMIN', 'SUPERVISOR'])
def exportar_reporte_pdf(request):
    """Exportar reporte a PDF con formato profesional."""
    
    tipo = request.GET.get('tipo', 'tiempos')
    fecha_desde_str = request.GET.get('fecha_desde', '')
    fecha_hasta_str = request.GET.get('fecha_hasta', '')
    
    # Parse Spanish formatted dates
    fecha_desde = parse_spanish_date(fecha_desde_str) if fecha_desde_str else (timezone.now() - timedelta(days=30)).date()
    fecha_hasta = parse_spanish_date(fecha_hasta_str) if fecha_hasta_str else timezone.now().date()
    
    # Validate dates
    if not fecha_desde or not fecha_hasta:
        return HttpResponse('❌ Error en el formato de fechas. Use DD de mes de YYYY', status=400)
    
    # Crear el objeto BytesIO para el PDF
    buffer = BytesIO()
    
    # Crear el documento PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=50,
        bottomMargin=30,
    )
    
    # Contenedor para los elementos del PDF
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#004B93'),
        spaceAfter=30,
        alignment=TA_CENTER,
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.grey,
        spaceAfter=20,
        alignment=TA_CENTER,
    )
    
    # Título
    if tipo == 'tiempos':
        title = Paragraph("Reporte de Tiempos de Taller", title_style)
    else:
        title = Paragraph("Reporte de Productividad por Mecánico", subtitle_style)
    
    elements.append(title)
    
    # Subtítulo con fechas
    subtitle = Paragraph(
        f"Período: {fecha_desde} al {fecha_hasta}<br/>Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}",
        subtitle_style
    )
    elements.append(subtitle)
    elements.append(Spacer(1, 20))
    
    # Generar tabla según el tipo
    if tipo == 'tiempos':
        # Obtener datos
        ingresos = IngresoTaller.objects.filter(
            fecha_programada__range=[fecha_desde, fecha_hasta]
        ).select_related('vehiculo', 'supervisor')
        
        # Crear tabla
        data = [['Patente', 'Vehículo', 'Fecha', 'Estado', 'Duración (min)', 'Supervisor']]
        
        for ingreso in ingresos:
            data.append([
                ingreso.vehiculo.patente,
                f"{ingreso.vehiculo.marca} {ingreso.vehiculo.modelo}",
                ingreso.fecha_programada.strftime('%d/%m/%Y'),
                ingreso.get_estado_display(),
                str(ingreso.duracion_total_minutos or 'N/A'),
                ingreso.supervisor.nombre if ingreso.supervisor else 'N/A'
            ])
        
        # Estadísticas
        total_ingresos = ingresos.count()
        terminados = ingresos.filter(estado__in=['TERMINADO', 'RETIRADO']).count()
        
        stats_text = Paragraph(
            f"<b>Total de ingresos:</b> {total_ingresos} | <b>Terminados:</b> {terminados}",
            styles['Normal']
        )
        elements.append(stats_text)
        elements.append(Spacer(1, 10))
    
    elif tipo == 'productividad':
        # Obtener datos
        mecanicos = Usuario.objects.filter(rol='MECANICO', activo=True)
        
        # Crear tabla
        data = [['Mecánico', 'Total Tareas', 'Completadas', 'Pendientes', 'En Proceso', '% Completadas']]
        
        for mecanico in mecanicos:
            tareas = Tarea.objects.filter(
                mecanico=mecanico,
                fecha_asignacion__range=[fecha_desde, fecha_hasta]
            )
            
            total = tareas.count()
            completadas = tareas.filter(estado='COMPLETADA').count()
            pendientes = tareas.filter(estado='PENDIENTE').count()
            en_proceso = tareas.filter(estado='EN_PROCESO').count()
            porcentaje = round((completadas / total * 100) if total > 0 else 0, 2)
            
            data.append([
                mecanico.nombre,
                str(total),
                str(completadas),
                str(pendientes),
                str(en_proceso),
                f"{porcentaje}%"
            ])
    
    # Crear y estilizar la tabla
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#004B93')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Contenido
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    
    elements.append(table)
    
    # Footer
    elements.append(Spacer(1, 30))
    footer = Paragraph(
        "PepsiCo Chile - Sistema de Gestión de Taller<br/>Documento generado automáticamente",
        ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER,
        )
    )
    elements.append(footer)
    
    # Construir el PDF
    doc.build(elements)
    # Obtener el valor del buffer y crear la respuesta
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_{tipo}_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
    response.write(pdf)
    
    return response


@login_required
@role_required(['ADMIN', 'SUPERVISOR'])
def reporte_repuestos(request):
    """Reporte de repuestos más utilizados."""
    
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    if not fecha_desde:
        fecha_desde = (timezone.now() - timedelta(days=30)).date()
    if not fecha_hasta:
        fecha_hasta = timezone.now().date()
    
    # Obtener todas las tareas completadas en el período
    # Buscar por fecha_completada si existe, si no, por fecha_creacion
    tareas = Tarea.objects.filter(
        estado='COMPLETADA'
    ).filter(
        Q(fecha_completada__range=[fecha_desde, fecha_hasta]) |
        Q(fecha_completada__isnull=True, fecha_creacion__range=[fecha_desde, fecha_hasta])
    ).exclude(repuestos_utilizados__isnull=True).exclude(repuestos_utilizados='')
    
    # Obtener todos los ingresos en el período con repuestos necesarios
    ingresos = IngresoTaller.objects.filter(
        fecha_programada__range=[fecha_desde, fecha_hasta]
    ).exclude(repuesto_necesario__isnull=True).exclude(repuesto_necesario='')
    
    # Contar repuestos
    repuestos_dict = {}
    
    # Procesar repuestos de tareas
    for tarea in tareas:
        if tarea.repuestos_utilizados:
            # Dividir por comas o saltos de línea
            repuestos = [r.strip() for r in tarea.repuestos_utilizados.replace('\n', ',').split(',') if r.strip()]
            for repuesto in repuestos:
                # Normalizar: convertir a minúsculas y eliminar espacios extras
                repuesto_normalizado = ' '.join(repuesto.lower().split())
                if repuesto_normalizado in repuestos_dict:
                    repuestos_dict[repuesto_normalizado] += 1
                else:
                    repuestos_dict[repuesto_normalizado] = 1
    
    # Procesar repuestos de ingresos
    for ingreso in ingresos:
        if ingreso.repuesto_necesario:
            # Dividir por comas o saltos de línea
            repuestos = [r.strip() for r in ingreso.repuesto_necesario.replace('\n', ',').split(',') if r.strip()]
            for repuesto in repuestos:
                # Normalizar: convertir a minúsculas y eliminar espacios extras
                repuesto_normalizado = ' '.join(repuesto.lower().split())
                if repuesto_normalizado in repuestos_dict:
                    repuestos_dict[repuesto_normalizado] += 1
                else:
                    repuestos_dict[repuesto_normalizado] = 1
    
    # Ordenar por cantidad
    repuestos_data = sorted(
        [{'nombre': k, 'cantidad': v} for k, v in repuestos_dict.items()],
        key=lambda x: x['cantidad'],
        reverse=True
    )[:20]  # Top 20
    
    context = {
        'repuestos_data': repuestos_data,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'total_tareas': tareas.count(),
    }
    
    return render(request, 'reportes/reporte_repuestos.html', context)


@login_required
@role_required(['ADMIN', 'SUPERVISOR', 'EHS'])
def reporte_vehiculos_criticos(request):
    """Reporte de vehículos con más mantenimientos y tiempos críticos."""
    
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    if not fecha_desde:
        fecha_desde = (timezone.now() - timedelta(days=90)).date()  # 3 meses por defecto
    if not fecha_hasta:
        fecha_hasta = timezone.now().date()
    
    # Obtener vehículos con estadísticas
    vehiculos = Vehiculo.objects.filter(activo=True)
    vehiculos_data = []
    
    for vehiculo in vehiculos:
        ingresos = IngresoTaller.objects.filter(
            vehiculo=vehiculo,
            fecha_programada__range=[fecha_desde, fecha_hasta]
        )
        
        num_ingresos = ingresos.count()
        if num_ingresos == 0:
            continue
        
        # Calcular tiempo promedio
        ingresos_terminados = ingresos.filter(estado__in=['TERMINADO', 'RETIRADO'])
        tiempos = [ing.duracion_total_minutos for ing in ingresos_terminados if ing.duracion_total_minutos]
        tiempo_promedio_minutos = sum(tiempos) / len(tiempos) if tiempos else 0
        
        # Formatear tiempo promedio
        horas = int(tiempo_promedio_minutos // 60) if tiempo_promedio_minutos > 0 else 0
        minutos = int(tiempo_promedio_minutos % 60) if tiempo_promedio_minutos > 0 else 0
        tiempo_formateado = f"{horas}h {minutos}min" if horas > 0 else f"{minutos}min"
        
        # Contar tareas
        total_tareas = Tarea.objects.filter(
            ingreso__vehiculo=vehiculo,
            ingreso__fecha_programada__range=[fecha_desde, fecha_hasta]
        ).count()
        
        vehiculos_data.append({
            'vehiculo': vehiculo,
            'num_ingresos': num_ingresos,
            'tiempo_promedio': round(tiempo_promedio_minutos, 2),
            'tiempo_promedio_formateado': tiempo_formateado,
            'total_tareas': total_tareas,
            'criticidad': 'ALTA' if num_ingresos > 5 else 'MEDIA' if num_ingresos > 2 else 'BAJA'
        })
    
    # Ordenar por número de ingresos
    vehiculos_data.sort(key=lambda x: x['num_ingresos'], reverse=True)
    
    context = {
        'vehiculos_data': vehiculos_data,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    }
    
    return render(request, 'reportes/reporte_vehiculos_criticos.html', context)