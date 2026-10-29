"""
Management command para inyectar datos de prueba aleatorios de ~1 mes.
"""
import random
from datetime import date, datetime, timedelta, time
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Max

from apps.mesas.models import Mesa, Pedido
from apps.productos.models import Producto, Categoria, UnidadMedida
from apps.ventas.models import Factura, Pago
from apps.caja.models import AperturaCaja, CategoriaEgreso, Egreso
from apps.creditos.services import crear_credito, registrar_abono
from apps.creditos.models import Cliente


class Command(BaseCommand):
    help = 'Inyecta datos de prueba aleatorios de ~1 mes.'

    def handle(self, *args, **options):
        random.seed(42)
        user = User.objects.filter(is_staff=True).first()
        vendedor = user.vendedor

        mesa, _ = Mesa.objects.get_or_create(
            tipo='caja', numero=9999,
            defaults={'estado': 'libre', 'activa': True},
        )

        cat, _ = Categoria.objects.get_or_create(nombre='General')
        unidad, _ = UnidadMedida.objects.get_or_create(nombre='Unidad')

        productos = list(Producto.objects.filter(estado='activo'))
        if len(productos) < 5:
            for i in range(8):
                p = Producto.objects.create(
                    nombre=f'Producto {i+1}', codigo=f'P{i+1:03d}',
                    categoria=cat, unidad=unidad,
                    precio_venta=Decimal(random.choice([5000, 8000, 12000, 15000, 20000])),
                    costo=Decimal(random.choice([2000, 3000, 5000, 7000])),
                    stock_actual=random.randint(20, 100),
                    stock_minimo=5,
                )
                productos.append(p)
        self.stdout.write(f'Productos: {len(productos)}')

        metodos = ['efectivo', 'transferencia', 'credito']

        hoy = timezone.localdate()
        for d in range(30, 0, -1):
            fecha = hoy - timedelta(days=d)
            inicio = timezone.make_aware(datetime(fecha.year, fecha.month, fecha.day, 8, 0))
            fin = timezone.make_aware(datetime(fecha.year, fecha.month, fecha.day, 20, 0))

            caja = AperturaCaja.objects.create(usuario=user, fecha_apertura=inicio, activa=False)
            caja.fecha_cierre = fin
            caja.save()

            n_ventas = random.randint(3, 8)
            for _ in range(n_ventas):
                n_items = random.randint(1, 4)
                items = random.sample(productos, n_items)
                subtotal = Decimal('0')
                from apps.mesas.models import DetallePedido
                pedido = Pedido.objects.create(
                    mesa=mesa, mesero=vendedor,
                    subtotal=0, total=0, saldo_pendiente=0,
                    estado='pagado', fecha_cierre=fin,
                )
                for prod in items:
                    cant = random.randint(1, 5)
                    pu = prod.precio_venta
                    DetallePedido.objects.create(
                        pedido=pedido, producto=prod, cantidad=cant,
                        precio_unitario=pu, subtotal=pu * cant,
                    )
                    subtotal += pu * cant
                    prod.stock_actual = max(0, prod.stock_actual - cant)
                    prod.save(update_fields=['stock_actual'])

                metodo = random.choice(metodos)
                ultimo_numero = Factura.objects.aggregate(maximo=Max('numero'))['maximo'] or 0
                total = subtotal
                factura = Factura(
                    numero=ultimo_numero + 1,
                    pedido=pedido, mesa=mesa, mesero=vendedor,
                    metodo_pago=metodo, subtotal=total, descuento=Decimal('0'),
                    total=total, valor_recibido=total if metodo != 'credito' else Decimal('0'),
                    cambio=Decimal('0'),
                    created_at=inicio + timedelta(minutes=random.randint(0, 480)),
                )
                factura._skip_inventory_deduction = True
                factura.save()

                if metodo != 'credito':
                    Pago.objects.create(
                        factura=factura, pedido=pedido, metodo=metodo,
                        monto=total, valor_recibido=total, cambio=Decimal('0'),
                        usuario=user, created_at=factura.created_at,
                    )
                else:
                    cliente, _ = Cliente.objects.get_or_create(nombre=f'Cliente {random.randint(1,6)}')
                    crear_credito(factura, cliente.nombre, random.choice([1, 2, 3]),
                                  correo='', monto=total, frecuencia='mensual',
                                  cliente=cliente)
                    if random.random() < 0.4:
                        cred = factura.credito
                        abono_monto = (total * Decimal(random.choice(['0.3', '0.5']))).quantize(Decimal('0.01'))
                        if abono_monto < total:
                            try:
                                registrar_abono(cred, abono_monto, metodo=random.choice(['efectivo', 'transferencia']),
                                                usuario=user, observacion='Abono prueba')
                            except ValueError:
                                pass

                pedido.total = total
                pedido.subtotal = total
                pedido.save(update_fields=['total', 'subtotal'])

            cat_eg, _ = CategoriaEgreso.objects.get_or_create(nombre='Varios')
            for _ in range(random.randint(0, 3)):
                Egreso.objects.create(
                    caja=caja, metodo_pago=random.choice(['efectivo', 'transferencia']),
                    categoria=cat_eg, valor=Decimal(random.choice([10000, 20000, 5000])),
                    motivo='Egreso prueba', usuario=user,
                    created_at=inicio + timedelta(minutes=random.randint(0, 480)),
                )

            self.stdout.write(f'Dia {fecha}: {n_ventas} ventas')

        self.stdout.write(self.style.SUCCESS('Datos de prueba inyectados.'))