"""
Servicios de la aplicación ventas.

Contiene la lógica de negocio para facturación.
"""
import os
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


def _fmt_mil(value):
    """Formatea un número con separador de miles (puntos), sin decimales."""
    from decimal import Decimal, ROUND_DOWN
    try:
        v = Decimal(str(value)).quantize(Decimal('1'), rounding=ROUND_DOWN)
        s = str(int(v))
        parts = []
        while s:
            parts.append(s[-3:])
            s = s[:-3]
        return '.'.join(reversed(parts))
    except Exception:
        return '0'


class _PDF:
    """Generador de PDF mínimo usando solo la librería estándar de Python."""

    def __init__(self, width=612, height=792):
        self.W = width
        self.H = height
        self.ops = []

    @staticmethod
    def _esc(s):
        s = str(s)
        return s.replace('\\', r'\\').replace('(', r'\(').replace(')', r'\)')

    def text(self, x, y_top, s, size=10, bold=False):
        y = self.H - y_top
        s = self._esc(s)
        font = 'F2' if bold else 'F1'
        self.ops.append(
            f'BT /{font} {size} Tf 1 0 0 1 {x:.1f} {y:.1f} Tm ({s}) Tj ET'
        )

    def line(self, x1, y1_top, x2, y2_top, w=0.5):
        y1 = self.H - y1_top
        y2 = self.H - y2_top
        self.ops.append(f'{w} w {x1:.1f} {y1:.1f} m {x2:.1f} {y2:.1f} l S')

    def build(self):
        W, H = self.W, self.H
        content = '\n'.join(self.ops)
        content_bytes = content.encode('cp1252', 'replace')
        font_reg = ("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
                    "/Encoding /WinAnsiEncoding >>")
        font_bold = ("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
                     "/Encoding /WinAnsiEncoding >>")
        page = (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] "
                f"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> "
                f"/Contents 6 0 R >>")
        pages = "<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
        catalog = "<< /Type /Catalog /Pages 2 0 R >>"
        header = "<< /Length %d >>\nstream\n" % len(content_bytes)
        objects = {1: catalog, 2: pages, 3: page, 4: font_reg, 5: font_bold}
        out = bytearray()
        out += b"%PDF-1.4\n"
        offsets = {}
        for num in (1, 2, 3, 4, 5):
            offsets[num] = len(out)
            out += ("%d 0 obj\n%s\nendobj\n" % (num, objects[num])).encode('cp1252', 'replace')
        offsets[6] = len(out)
        out += ("6 0 obj\n" + header).encode('cp1252', 'replace')
        out += content_bytes
        out += b"\nendstream\nendobj\n"
        xref_pos = len(out)
        out += b"xref\n0 7\n"
        out += b"0000000000 65535 f \n"
        for num in (1, 2, 3, 4, 5, 6):
            out += ("%010d 00000 n \n" % offsets[num]).encode('cp1252')
        out += ("trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % xref_pos).encode('cp1252')
        return bytes(out)


def generar_factura_pdf(factura):
    """Genera el PDF de una factura usando solo la librería estándar."""
    from apps.configuracion.models import Configuracion
    config = Configuracion.obtener()
    pdf = _PDF()
    x = 40
    y = 40

    pdf.text(x, y, config.nombre_empresa or 'Empresa', size=20, bold=True); y += 22
    pdf.text(x, y, 'Sistema de Facturacion', size=10); y += 16
    pdf.text(x, y, 'FACTURA #%s' % factura.numero, size=14, bold=True); y += 18
    if config.nit:
        pdf.text(x, y, 'NIT: %s' % config.nit, size=10); y += 14
    if config.direccion:
        pdf.text(x, y, config.direccion, size=10); y += 14
    y += 10
    pdf.text(x, y, 'Fecha: %s' % factura.created_at.strftime('%d/%m/%Y'), size=10)
    pdf.text(x + 200, y, 'Hora: %s' % factura.created_at.strftime('%H:%M:%S'), size=10)
    y += 14
    pdf.text(x, y, 'Mesa: %s' % factura.mesa.numero, size=10)
    pdf.text(x + 200, y, 'Mesero: %s %s' % (factura.mesero.nombre, factura.mesero.apellidos), size=10)
    y += 14
    pdf.text(x, y, 'Metodo de pago: %s' % factura.get_metodo_pago_display(), size=10)
    y += 18

    pdf.line(x, y, pdf.W - x, y, 1); y += 6
    pdf.text(x, y, 'Producto', size=10, bold=True)
    pdf.text(x + 270, y, 'Cant', size=10, bold=True)
    pdf.text(x + 330, y, 'Precio', size=10, bold=True)
    pdf.text(x + 430, y, 'Subtotal', size=10, bold=True)
    y += 4
    pdf.line(x, y, pdf.W - x, y, 0.5); y += 12

    detalles = factura.pedido.detalles.select_related('producto').all() if factura.pedido else []
    for d in detalles:
        nombre = d.producto.nombre
        if d.es_cortesia:
            nombre += ' *Cortesia'
        elif d.precio_unitario < d.producto.precio_venta:
            nombre += ' *Desc'
        if len(nombre) > 46:
            nombre = nombre[:43] + '...'
        precio = 'Gratis' if d.es_cortesia else '$%s' % _fmt_mil(d.precio_unitario)
        pdf.text(x, y, nombre, size=9)
        pdf.text(x + 270, y, str(int(d.cantidad)), size=9)
        pdf.text(x + 330, y, precio, size=9)
        pdf.text(x + 430, y, '$%s' % _fmt_mil(d.subtotal), size=9)
        y += 13

    y += 6
    pdf.line(x, y, pdf.W - x, y, 0.5); y += 14
    pdf.text(x + 270, y, 'Subtotal:', size=10, bold=True)
    pdf.text(x + 430, y, '$%s' % _fmt_mil(factura.subtotal), size=10)
    y += 14
    if factura.descuento > 0:
        pdf.text(x + 270, y, 'Descuento:', size=10, bold=True)
        pdf.text(x + 430, y, '-$%s' % _fmt_mil(factura.descuento), size=10)
        y += 14
    pdf.text(x + 270, y, 'Total:', size=12, bold=True)
    pdf.text(x + 430, y, '$%s' % _fmt_mil(factura.total), size=12, bold=True)
    y += 30
    pdf.text(x, y, '¡Gracias por su visita!', size=11, bold=True)

    data = pdf.build()
    response = HttpResponse(data, content_type='application/pdf')
    response['Content-Disposition'] = 'filename=factura_%s.pdf' % factura.numero
    return response


def generar_reporte_ventas_pdf(facturas, fecha_generacion):
    """Genera el PDF del reporte de ventas usando solo la librería estándar."""
    from apps.configuracion.models import Configuracion
    config = Configuracion.obtener()
    pdf = _PDF()
    x = 40
    y = 40
    pdf.text(x, y, '%s - Reporte de Ventas' % (config.nombre_empresa or 'Empresa'), size=16, bold=True)
    y += 18
    pdf.text(x, y, 'Generado: %s' % fecha_generacion.strftime('%d/%m/%Y %H:%M'), size=10)
    y += 16
    pdf.line(x, y, pdf.W - x, y, 1); y += 6
    cols = [x, x + 60, x + 110, x + 175, x + 320, x + 420]
    headers = ['# Fact', 'Fecha', 'Mesa', 'Mesero', 'Metodo', 'Total']
    for i, h in enumerate(headers):
        pdf.text(cols[i], y, h, size=9, bold=True)
    y += 4
    pdf.line(x, y, pdf.W - x, y, 0.5); y += 12
    if not facturas:
        pdf.text(x, y, 'No existen facturas para mostrar.', size=11, bold=True)
    for f in facturas:
        pdf.text(cols[0], y, str(f.numero), size=9)
        pdf.text(cols[1], y, f.created_at.strftime('%d/%m/%Y'), size=9)
        pdf.text(cols[2], y, str(f.mesa.numero), size=9)
        mesero = f.mesero.nombre
        if len(mesero) > 18:
            mesero = mesero[:15] + '...'
        pdf.text(cols[3], y, mesero, size=9)
        pdf.text(cols[4], y, f.get_metodo_pago_display(), size=9)
        pdf.text(cols[5], y, '$%s' % _fmt_mil(f.total), size=9)
        y += 12
    data = pdf.build()
    response = HttpResponse(data, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=reporte_ventas.pdf'
    return response
