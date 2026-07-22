# 🍽️ Sistema de Facturación para Restaurante

Sistema web moderno para administración completa de restaurante.
Desarrollado con Django 5+, Bootstrap 5 y JavaScript Vanilla.

## ✨ Características

- **Autenticación por cédula** - Sin contraseñas, solo ingresa tu número de cédula
- **Gestión de mesas** - Interfaz visual tipo POS con estados de color
- **Pedidos** - Agregar/modificar productos, cantidades, observaciones
- **Pagos** - Efectivo y transferencia, con soporte para pagos parciales
- **Facturación** - Facturas con número consecutivo, exportación PDF
- **Inventario** - Control de stock con movimientos (entradas, salidas, ajustes)
- **Caja** - Apertura y cierre con resumen detallado
- **Egresos** - Registro de gastos (hielo, verduras, domicilios, etc.)
- **Reportes** - Dashboard con ventas del día/mes/año, productos más/menos vendidos
- **Exportación** - Excel y PDF
- **Lista de precios** - Consulta rápida con buscador instantáneo
- **Roles** - Administrador y vendedor con permisos diferenciados

## 🛠️ Tecnologías

| Tecnología | Versión |
|------------|---------|
| Python     | 3.13+   |
| Django     | 5.0+    |
| Bootstrap  | 5.3     |
| SQLite     | Dev     |
| PostgreSQL | Prod    |

## 📋 Requisitos

- Python 3.13 o superior
- pip (gestor de paquetes)
- Virtualenv (recomendado)

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/restaurant.git
cd restaurant
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Migrar base de datos

```bash
python manage.py migrate
```

### 5. Cargar datos iniciales

```bash
python manage.py loaddata fixtures/datos_iniciales.json
```

### 6. Crear superusuario (administrador)

```bash
python manage.py createsuperuser
```

**Importante**: El superusuario debe tener el mismo username que la cédula del vendedor que crearás después. Crea primero el superusuario, luego en el admin crea el Vendedor con la misma cédula.

### 7. Ejecutar servidor

```bash
python manage.py runserver
```

### 8. Acceder al sistema

- **URL**: http://localhost:8000
- **Admin**: http://localhost:8000/admin/

## 👥 Usuarios de prueba

Después de cargar los fixtures, puedes crear vendedores desde el panel de administración.

### Crear vendedor administrador:
1. Ve a `/admin/`
2. Inicia sesión con el superusuario
3. Crea un Vendedor con tu misma cédula
4. Marca al vendedor como activo
5. Ahora puedes iniciar sesión con tu cédula desde la página principal

## 📁 Estructura del proyecto

```
restaurant/
├── config/              # Configuración del proyecto
│   ├── settings.py      # Ajustes generales
│   ├── urls.py          # URLs principales
│   └── wsgi.py          # WSGI
├── apps/
│   ├── usuarios/        # Gestión de vendedores y autenticación
│   ├── productos/       # Productos, categorías, unidades
│   ├── inventario/      # Control de stock y movimientos
│   ├── mesas/           # Mesas y pedidos (POS)
│   ├── ventas/          # Facturación y pagos
│   ├── caja/            # Apertura/cierre y egresos
│   └── reportes/        # Dashboard y exportación
├── templates/           # Plantillas HTML
│   ├── base/            # Base, navbar, messages
│   ├── auth/            # Login
│   ├── usuarios/        # CRUD vendedores, dashboard
│   ├── productos/       # CRUD productos, lista precios
│   ├── inventario/      # Inventario e historial
│   ├── mesas/           # Vista mesas, POS (detalle pedido)
│   ├── ventas/          # Facturas, PDF
│   ├── caja/            # Caja y egresos
│   └── reportes/        # Dashboard reportes
├── static/
│   ├── css/             # Estilos personalizados
│   └── js/              # JavaScript personalizado
├── fixtures/            # Datos de ejemplo
├── media/               # Archivos subidos
└── manage.py            # Administración Django
```

## 📊 Roles y permisos

### Administrador (`is_staff=True`)
- ✅ CRUD vendedores
- ✅ CRUD productos
- ✅ Administrar inventario
- ✅ Abrir/cerrar caja
- ✅ Registrar egresos
- ✅ Ver reportes
- ✅ Modificar pedidos de otros
- ✅ Aplicar descuentos

### Vendedor
- ✅ Ingresar por cédula
- ✅ Abrir pedidos en mesas
- ✅ Agregar/modificar productos
- ✅ Cobrar pedidos propios
- ❌ Modificar pedidos ajenos
- ❌ Administrar inventario
- ❌ Abrir/cerrar caja
- ❌ Ver reportes administrativos

## 🖥️ Interfaz

- **Dashboard**: Resumen con ventas, caja, stock bajo y mesas
- **Mesas**: Tarjetas grandes con colores según estado
- **POS**: Interfaz tipo punto de venta con búsqueda instantánea
- **Lista de precios**: Consulta rápida con filtros
- **Responsive**: Funciona en PC, tablet y celular

## 🗄️ Migración a PostgreSQL

Para migrar de SQLite a PostgreSQL:

1. Instalar psycopg2: `pip install psycopg2-binary`
2. Crear base de datos en PostgreSQL
3. Modificar `config/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'restaurant',
        'USER': 'restaurant_user',
        'PASSWORD': 'tu_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

4. Ejecutar migraciones: `python manage.py migrate`

## 📄 Licencia

Este proyecto es de uso libre y educativo.
