"""
Modelos de la aplicación reportes.

Los reportes se generan a partir de los datos existentes
en las demás aplicaciones. Este archivo existe para mantener
la estructura de la app; los reportes son consultas y exportaciones.
"""
# Los reportes se obtienen consultando los modelos de:
# - apps.ventas.models.Factura
# - apps.ventas.models.Pago
# - apps.caja.models.AperturaCaja
# - apps.caja.models.Egreso
# - apps.productos.models.Producto
# - apps.mesas.models.Pedido
