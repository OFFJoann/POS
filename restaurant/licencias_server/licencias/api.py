"""API JSON para el dashboard React del servidor de licencias.

Autenticación por sesión de Django (`/api/panel/login/`), no por token: el
dashboard siempre va detrás de HTTPS en el mismo dominio, así que la cookie
de sesión es suficiente y evita guardar secretos en el navegador.

Todos los endpoints exigen una cuenta con acceso al panel (`requiere_panel`) y
devuelven JSON. Hay dos roles, administrador y visualizador; ver
`licencias/permisos.py`.
"""
import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import Licencia
from .permisos import puede_escribir, requiere_panel, rol_de

# La venta es mensual: cada "Actualizar mensualidad" suma exactamente este mes.
# El botón del panel no manda los días, los pone el servidor, para que el
# botón y lo que realmente ocurre no puedan desincronizarse.
DIAS_MENSUALIDAD = 30


def _json_error(mensaje, status=400):
    return JsonResponse({'ok': False, 'error': mensaje}, status=status)


def _json_ok(**datos):
    return JsonResponse({'ok': True, **datos})


def _body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}


def _precio(valor):
    """Convierte a Decimal lo que llega del formulario.

    Acepta coma o punto decimal y tolera el vacío (0). Devuelve `None` si el
    valor no es un número o es negativo, para que el llamador avise en vez de
    guardar basura. Se usa `Decimal` y no `float` para no arrastrar errores de
    redondeo al sumar mensualidades en el resumen.
    """
    if valor is None or valor == '':
        return Decimal('0')
    try:
        precio = Decimal(str(valor).strip().replace(',', '.'))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return precio if precio >= 0 else None


# ─── Sesión ──────────────────────────────────────────────────────────────────

@ensure_csrf_cookie
@require_http_methods(['GET', 'POST'])
def panel_login(request):
    """GET entrega el token CSRF; POST autentica y abre sesión."""
    if request.method == 'GET':
        # get_token() crea la cookie y devuelve el token enmascarado, que es
        # lo que el panel envía luego en la cabecera X-CSRFToken.
        return _json_ok(csrf=get_token(request))

    datos = _body(request)
    username = (datos.get('username') or '').strip()
    password = datos.get('password') or ''

    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_active:
        return _json_error('Usuario o contraseña incorrectos', 401)
    if rol_de(user) is None:
        return _json_error('El usuario no tiene acceso al panel', 403)

    login(request, user)
    return _json_ok(username=user.username, rol=rol_de(user))


@require_http_methods(['POST'])
def panel_logout(request):
    logout(request)
    return _json_ok()


@requiere_panel
def panel_sesion(request):
    """Devuelve quién está conectado y qué puede hacer; el frontend lo usa al arrancar."""
    rol = rol_de(request.user)
    return _json_ok(
        username=request.user.username,
        email=request.user.email,
        rol=rol,
        puede_escribir=puede_escribir(rol),
        es_admin=puede_escribir(rol),
    )


# ─── Configuración ───────────────────────────────────────────────────────────

@requiere_panel
def panel_configuracion(request):
    """Muestra el secreto compartido y su huella (para mapearlo en los POS).

    El secreto solo se devuelve a administradores: quien lo tenga puede firmar
    una licencia sin pasar por el panel, así que un visualizador no debe poder
    sacarlo de aquí.
    """
    from django.conf import settings

    es_admin = puede_escribir(rol_de(request.user))
    secreto = (getattr(settings, 'LICENCIA_SECRETO', '') or '').strip()
    total = Licencia.objects.count()
    return _json_ok(
        # Sin secreto, pero avisando de que existe: la interfaz explica por qué
        # no lo muestra en vez de parecer que está mal configurado.
        secreto=secreto if es_admin else '',
        secreto_restringido=not es_admin,
        configurado=bool(secreto),
        huella=hashlib.sha256(secreto.encode()).hexdigest()[:12] if secreto else '',
        total_licencias=total,
        licencias_activas=Licencia.objects.filter(activa=True).count(),
    )


# ─── Licencias ───────────────────────────────────────────────────────────────

def _serializar(licencia):
    return {
        'id': licencia.id,
        'codigo': licencia.codigo,
        'cliente': licencia.cliente,
        'fecha_inicio': licencia.fecha_inicio.isoformat(),
        'fecha_vencimiento': licencia.fecha_vencimiento.isoformat(),
        'dias_restantes': licencia.dias_restantes,
        'limite_vendedores': licencia.limite_vendedores,
        # Se manda como texto: en JSON un float perdería decimales al volver.
        'mensualidad': f'{licencia.mensualidad:.2f}',
        'features': licencia.features,
        'activa': licencia.activa,
        'creada_en': licencia.creada_en.isoformat(),
        'actualizada_en': licencia.actualizada_en.isoformat(),
    }


@requiere_panel
def panel_licencias(request):
    """Listado con búsqueda y filtro, o alta (POST)."""
    if request.method == 'GET':
        qs = Licencia.objects.all()
        buscar = (request.GET.get('q') or '').strip()
        if buscar:
            qs = qs.filter(codigo__icontains=buscar) | qs.filter(cliente__icontains=buscar)
        estado = (request.GET.get('estado') or '').strip()
        if estado == 'activas':
            qs = qs.filter(activa=True)
        elif estado == 'pausadas':
            qs = qs.filter(activa=False)
        elif estado == 'por_vencer':
            limite = date.today() + timedelta(days=30)
            qs = qs.filter(activa=True, fecha_vencimiento__lte=limite)
        elif estado == 'vencidas':
            qs = qs.filter(fecha_vencimiento__lt=date.today())
        elif estado == 'por_cobrar':
            # Lo que hay que pasar por caja este mes: vencidas, paused o
            # vencen dentro del mes en curso.
            hoy = date.today()
            qs = qs.filter(Q(activa=False) | Q(fecha_vencimiento__lte=hoy + timedelta(days=DIAS_MENSUALIDAD)))

        return _json_ok(
            licencias=[_serializar(l) for l in qs.order_by('cliente')],
        )

    if request.method == 'POST':
        datos = _body(request)
        codigo = (datos.get('codigo') or '').strip().upper()
        cliente = (datos.get('cliente') or '').strip()
        vencimiento = (datos.get('fecha_vencimiento') or '').strip()

        errores = []
        if not codigo:
            errores.append('El código es obligatorio.')
        if not cliente:
            errores.append('El cliente es obligatorio.')
        if not vencimiento:
            errores.append('La fecha de vencimiento es obligatoria.')
        else:
            try:
                date.fromisoformat(vencimiento)
            except ValueError:
                errores.append('La fecha de vencimiento no es válida.')
        if codigo and Licencia.objects.filter(codigo=codigo).exists():
            errores.append(f'Ya existe una licencia con el código {codigo}.')
        mensualidad = _precio(datos.get('mensualidad'))
        if mensualidad is None:
            errores.append('La mensualidad debe ser un precio válido (0 o mayor).')
        if errores:
            return _json_error(' '.join(errores))

        inicio = (datos.get('fecha_inicio') or '').strip() or date.today().isoformat()
        try:
            inicio_date = date.fromisoformat(inicio)
        except ValueError:
            inicio_date = date.today()

        licencia = Licencia.objects.create(
            codigo=codigo,
            cliente=cliente,
            fecha_inicio=inicio_date,
            fecha_vencimiento=date.fromisoformat(vencimiento),
            limite_vendedores=max(0, int(datos.get('limite_vendedores') or 0)),
            mensualidad=mensualidad,
            features=datos.get('features') or {},
            activa=bool(datos.get('activa', True)),
        )
        return _json_ok(licencia=_serializar(licencia))

    return _json_error('Método no permitido', 405)


@requiere_panel
def panel_licencia_detalle(request, pk):
    """Detalle, edición (PUT) y borrado (DELETE) de una licencia."""
    try:
        licencia = Licencia.objects.get(pk=pk)
    except Licencia.DoesNotExist:
        return _json_error('Licencia no encontrada', 404)

    if request.method == 'GET':
        return _json_ok(licencia=_serializar(licencia))

    if request.method == 'PUT':
        datos = _body(request)
        errores = []

        codigo = (datos.get('codigo') or '').strip().upper()
        if not codigo:
            errores.append('El código es obligatorio.')
        elif Licencia.objects.filter(codigo=codigo).exclude(pk=pk).exists():
            errores.append(f'Ya existe otra licencia con el código {codigo}.')

        cliente = (datos.get('cliente') or '').strip()
        if not cliente:
            errores.append('El cliente es obligatorio.')

        vencimiento = (datos.get('fecha_vencimiento') or '').strip()
        try:
            vencimiento_date = date.fromisoformat(vencimiento)
        except ValueError:
            errores.append('La fecha de vencimiento no es válida.')
            vencimiento_date = licencia.fecha_vencimiento

        inicio = (datos.get('fecha_inicio') or '').strip()
        try:
            inicio_date = date.fromisoformat(inicio) if inicio else licencia.fecha_inicio
        except ValueError:
            inicio_date = licencia.fecha_inicio

        mensualidad = _precio(
            datos['mensualidad'] if 'mensualidad' in datos else licencia.mensualidad
        )
        if mensualidad is None:
            errores.append('La mensualidad debe ser un precio válido (0 o mayor).')

        if errores:
            return _json_error(' '.join(errores))

        licencia.codigo = codigo
        licencia.cliente = cliente
        licencia.fecha_inicio = inicio_date
        licencia.fecha_vencimiento = vencimiento_date
        licencia.limite_vendedores = max(0, int(datos.get('limite_vendedores') or 0))
        licencia.mensualidad = mensualidad
        licencia.features = datos.get('features') or {}
        licencia.activa = bool(datos.get('activa', True))
        licencia.save()
        return _json_ok(licencia=_serializar(licencia))

    if request.method == 'DELETE':
        cliente = licencia.cliente
        licencia.delete()
        return _json_ok(eliminada=cliente)

    return _json_error('Método no permitido', 405)


@requiere_panel
@require_http_methods(['POST'])
@transaction.atomic
def panel_licencias_acciones(request):
    """Acciones sobre licencias: mensualidad, extender N días, pausar, reactivar.

    `mensualidad` es la acción de la venta mensual: suma exactamente 30 días y
    reactiva la licencia. No acepta `dias` a propósito —el botón del panel la
    llama así y el servidor garantiza los 30— para que un cliente mal escrito no
    pueda regalar (o cobrar) un periodo distinto del que dice el botón.
    """
    datos = _body(request)
    ids = datos.get('ids') or []
    accion = datos.get('accion') or ''

    if not isinstance(ids, list) or not ids:
        return _json_error('Selecciona al menos una licencia.')
    ACCIONES = ('mensualidad', 'extender', 'pausar', 'reactivar')
    if accion not in ACCIONES:
        return _json_error('Acción no reconocida.')

    try:
        ids = [int(i) for i in ids]
    except (TypeError, ValueError):
        return _json_error('Identificadores no válidos.')

    licencias = list(Licencia.objects.filter(id__in=ids))
    if not licencias:
        return _json_error('No se encontraron las licencias.', 404)

    hoy = date.today()
    detalles = []
    if accion in ('mensualidad', 'extender'):
        if accion == 'mensualidad':
            dias = DIAS_MENSUALIDAD
        else:
            try:
                dias = int(datos.get('dias') or 0)
            except (TypeError, ValueError):
                return _json_error('Indica cuántos días extender.')
            if dias <= 0:
                return _json_error('Indica cuántos días extender.')
            if dias > 3650:
                return _json_error('Máximo 3650 días por operación.')

        for lic in licencias:
            base = lic.fecha_vencimiento
            # Si ya venció, el mes nuevo arranca desde hoy: el cliente tiene
            # 30 días completos aunque haya pagado con retraso.
            vencida = base < hoy
            if vencida:
                base = hoy
            lic.fecha_vencimiento = base + timedelta(days=dias)
            lic.activa = True
            lic.save(update_fields=['fecha_vencimiento', 'activa', 'actualizada_en'])
            detalles.append(f'{lic.codigo} → {lic.fecha_vencimiento.isoformat()}')
    elif accion == 'pausar':
        for lic in licencias:
            lic.activa = False
            lic.save(update_fields=['activa', 'actualizada_en'])
        detalles.append(f'{len(licencias)} licencia(s) pausada(s)')
    else:
        for lic in licencias:
            lic.activa = True
            lic.save(update_fields=['activa', 'actualizada_en'])
        detalles.append(f'{len(licencias)} licencia(s) reactivada(s)')

    return _json_ok(
        detalles=detalles,
        procesadas=len(licencias),
        # El frontend los usa para confirmar y para mostrar el nuevo vencimiento.
        dias_mensualidad=DIAS_MENSUALIDAD if accion == 'mensualidad' else None,
        hoy=hoy.isoformat(),
    )


@requiere_panel
def panel_dashboard(request):
    """Resumen para la portada del dashboard."""
    hoy = date.today()
    proximo_vencimiento = (
        Licencia.objects.filter(activa=True, fecha_vencimiento__gte=hoy)
        .order_by('fecha_vencimiento').first()
    )

    # Lo que entra cada mes son solo las licencias activas y no vencidas: una
    # pausada o ya vencida no se está cobrando. `potencial` suma todas para ver
    # cuánto dejaría de facturar si se activara/renovara lo que falta.
    def _suma(qs):
        return qs.aggregate(total=Sum('mensualidad'))['total'] or Decimal('0.00')

    mensual = _suma(Licencia.objects.filter(activa=True, fecha_vencimiento__gte=hoy))
    potencial = _suma(Licencia.objects.all())

    return _json_ok(
        total=Licencia.objects.count(),
        activas=Licencia.objects.filter(activa=True).count(),
        pausadas=Licencia.objects.filter(activa=False).count(),
        vencidas=Licencia.objects.filter(fecha_vencimiento__lt=hoy).count(),
        por_vencer_30=Licencia.objects.filter(
            activa=True,
            fecha_vencimiento__gte=hoy,
            fecha_vencimiento__lte=hoy + timedelta(days=30),
        ).count(),
        limite_vendedores_total=Licencia.objects.filter(activa=True)
        .exclude(limite_vendedores=0)
        .aggregate(total=Sum('limite_vendedores'))['total'] or 0,
        # Textos para no perder decimales al serializar a JSON.
        ingreso_mensual=f'{mensual:.2f}',
        ingreso_anual=f'{mensual * 12:.2f}',
        ingreso_potencial=f'{potencial:.2f}',
        proximo={
            'codigo': proximo_vencimiento.codigo,
            'cliente': proximo_vencimiento.cliente,
            'fecha_vencimiento': proximo_vencimiento.fecha_vencimiento.isoformat(),
            'dias_restantes': proximo_vencimiento.dias_restantes,
        } if proximo_vencimiento else None,
        generado_en=timezone.now().isoformat(),
    )