"""
Servicios de la aplicación ventas.

Contiene la lógica de negocio para facturación.
"""
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from django.db.models import Max
from .models import Factura


def generar_numero_factura():
    """Genera el siguiente número de factura consecutivo."""
    ultima = Factura.objects.aggregate(max_id=Max('numero'))['max_id'] or 0
    return ultima + 1


def obtener_ventas_del_dia(fecha=None):
    """Retorna las facturas de un día específico."""
    from datetime import date
    if not fecha:
        fecha = date.today()
    return Factura.objects.filter(created_at__date=fecha)


def obtener_ventas_del_mes(anio=None, mes=None):
    """Retorna las facturas de un mes específico."""
    from datetime import date
    hoy = date.today()
    if not anio:
        anio = hoy.year
    if not mes:
        mes = hoy.month
    return Factura.objects.filter(
        created_at__year=anio,
        created_at__month=mes
    )


def obtener_ventas_por_mesero(vendedor, fecha_inicio=None, fecha_fin=None):
    """Retorna las ventas de un mesero en un rango de fechas."""
    facturas = Factura.objects.filter(mesero=vendedor)
    if fecha_inicio:
        facturas = facturas.filter(created_at__gte=fecha_inicio)
    if fecha_fin:
        facturas = facturas.filter(created_at__lte=fecha_fin)
    return facturas


def generar_pdf_bytes(template_path, context):
    """
    Genera un PDF a partir de una plantilla HTML y retorna los bytes.

    Intenta con weasyprint primero, luego xhtml2pdf.
    Si no hay ninguna librería instalada, retorna None.
    """
    try:
        from weasyprint import HTML
        template = get_template(template_path)
        html = template.render(context)
        return HTML(string=html).write_pdf()
    except ImportError:
        try:
            from xhtml2pdf import pisa
            template = get_template(template_path)
            html = template.render(context)
            result = BytesIO()
            pdf = pisa.pisaDocument(BytesIO(html.encode('UTF-8')), result)
            if not pdf.err:
                return result.getvalue()
        except ImportError:
            pass
    return None


def render_pdf(template_path, context):
    """
    Genera un HttpResponse con el PDF.
    Si no hay librería PDF, retorna un HttpResponse con error 500.
    """
    pdf_bytes = generar_pdf_bytes(template_path, context)
    if pdf_bytes:
        return HttpResponse(pdf_bytes, content_type='application/pdf')
    from django.http import HttpResponseServerError
    return HttpResponseServerError(
        'No hay librería PDF instalada. Instala weasyprint o xhtml2pdf.'
    )
