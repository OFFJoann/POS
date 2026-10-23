/**
 * app.js - JavaScript principal del Sistema de Facturación
 *
 * Funcionalidades:
 * - Inicialización de DataTables
 * - Confirmaciones con SweetAlert2
 * - Búsquedas instantáneas
 * - Actualización de mesas en tiempo real
 */

(function() {
    'use strict';

    // ─── Inicialización global ────────────────────────────────────
    $(document).ready(function() {

        // Inicializar DataTables en tablas con clase .datatable
        initDataTables();

        // Configurar confirmaciones para botones de eliminar
        setupDeleteConfirmations();

        // Configurar auto-refresh de mesas cada 10 segundos
        setupTableAutoRefresh();

        // Inicializar tooltips de Bootstrap
        initTooltips();

        // Campos de dinero con puntos de miles (data-miles)
        initCamposMiles();

    });

    // ─── DataTables ───────────────────────────────────────────────
    function initDataTables() {
        if (typeof $.fn.DataTable !== 'undefined') {
            $('.datatable').each(function() {
                if (!$(this).hasClass('dataTable')) {
                    $(this).DataTable({
                        language: {
                            sProcessing: 'Procesando...',
                            sLengthMenu: 'Mostrar _MENU_ registros',
                            sZeroRecords: 'No se encontraron resultados',
                            sEmptyTable: 'Ningún dato disponible en esta tabla',
                            sInfo: 'Mostrando registros del _START_ al _END_ de un total de _TOTAL_ registros',
                            sInfoEmpty: 'Mostrando registros del 0 al 0 de un total de 0 registros',
                            sInfoFiltered: '(filtrado de un total de _MAX_ registros)',
                            sInfoPostFix: '',
                            sSearch: 'Buscar:',
                            sUrl: '',
                            sInfoThousands: ',',
                            sLoadingRecords: 'Cargando...',
                            oPaginate: {
                                sFirst: 'Primero',
                                sLast: 'Último',
                                sNext: 'Siguiente',
                                sPrevious: 'Anterior'
                            },
                            oAria: {
                                sSortAscending: ': Activar para ordenar la columna de manera ascendente',
                                sSortDescending: ': Activar para ordenar la columna de manera descendente'
                            }
                        },
                        pageLength: 25,
                        responsive: true,
                        autoWidth: false,
                        order: []
                    });
                }
            });
        }
    }

    // ─── Confirmaciones de eliminación ────────────────────────────
    function setupDeleteConfirmations() {
        $('[data-confirm]').on('click', function(e) {
            e.preventDefault();
            var message = $(this).data('confirm') || '¿Estás seguro?';
            var href = $(this).attr('href');

            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: '¿Estás seguro?',
                    text: message,
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonColor: '#dc3545',
                    cancelButtonColor: '#6c757d',
                    confirmButtonText: 'Sí, eliminar',
                    cancelButtonText: 'Cancelar'
                }).then(function(result) {
                    if (result.isConfirmed) {
                        window.location.href = href;
                    }
                });
            } else {
                if (confirm(message)) {
                    window.location.href = href;
                }
            }
        });
    }

    // ─── Auto-refresh de mesas (cada 10 segundos) ────────────────
    function setupTableAutoRefresh() {
        var container = $('#contenedor-mesas, #contenedor-cajas');
        if (container.length === 0) return;

        function refreshMesas() {
            $.ajax({
                url: '/mesas/estado/',
                method: 'GET',
                dataType: 'json',
                success: function(data) {
                    if (data.mesas) {
                        data.mesas.forEach(function(mesa) {
                            var card = container.find('[data-mesa-id="' + mesa.id + '"]');
                            if (card.length) {
                                // Actualizar estado visual
                                card.removeClass('mesa-libre mesa-asignada mesa-activo mesa-parcial mesa-pagada mesa-cerrada')
                                    .addClass('mesa-' + mesa.estado);
                                card.find('.mesa-estado-badge span')
                                    .removeClass('estado-libre estado-asignada estado-activo estado-parcial estado-pagada estado-cerrada')
                                    .addClass('estado-' + mesa.estado)
                                    .text(mesa.estado_display);
                            }
                        });
                    }
                }
            });
        }

        // Actualizar cada 10 segundos
        setInterval(refreshMesas, 10000);
    }

    // ─── Tooltips ─────────────────────────────────────────────────
    function initTooltips() {
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            var tooltipTriggerList = [].slice.call(
                document.querySelectorAll('[data-bs-toggle="tooltip"]')
            );
            tooltipTriggerList.map(function(el) {
                return new bootstrap.Tooltip(el);
            });
        }
    }

    // ─── Mostrar mensajes flash como SweetAlert ───────────────────
    function showFlashMessages() {
        var messages = window._flashMessages || [];
        if (messages.length > 0 && typeof Swal !== 'undefined') {
            messages.forEach(function(msg) {
                Swal.fire({
                    icon: msg.tags === 'error' ? 'error' :
                          msg.tags === 'warning' ? 'warning' :
                          msg.tags === 'success' ? 'success' : 'info',
                    title: msg.message,
                    timer: 3000,
                    showConfirmButton: false,
                    toast: true,
                    position: 'top-end'
                });
            });
        }
    }

    // ─── Campos de dinero con puntos de miles ─────────────────────
    // Un <input type="text" data-miles> muestra el valor como 1.250.000
    // (coma para centavos: 3.333,34) mientras se escribe. Al enviar el
    // formulario el valor viaja limpio (1250000 / 3333.34) para Django.

    // Texto escrito por el usuario -> "1.250.000" o "3.333,3".
    function formatearMiles(texto) {
        texto = String(texto).replace(/[^\d,]/g, '');
        var coma = texto.indexOf(',');
        var entero = coma === -1 ? texto : texto.slice(0, coma);
        var decimales = coma === -1 ? null : texto.slice(coma + 1).replace(/,/g, '').slice(0, 2);
        entero = entero.replace(/^0+(?=\d)/, '');
        entero = entero.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        if (decimales !== null) {
            return (entero || '0') + ',' + decimales;
        }
        return entero;
    }

    // Valor que llega del servidor ("15000.00" o "15000,00") -> "15.000".
    function desdeServidor(valor) {
        valor = String(valor || '').trim();
        if (!valor) return '';
        if (valor.indexOf(',') !== -1) {
            valor = valor.replace(/\./g, '').replace(',', '.');
        }
        var n = parseFloat(valor);
        if (isNaN(n)) return '';
        var partes = n.toFixed(2).split('.');
        return formatearMiles(partes[0] + (partes[1] === '00' ? '' : ',' + partes[1]));
    }

    // "1.250.000,5" -> "1250000.5"
    function limpiarMiles(texto) {
        return String(texto).replace(/\./g, '').replace(',', '.');
    }

    function initCamposMiles(raiz) {
        (raiz || document).querySelectorAll('input[data-miles]:not([data-miles-listo])').forEach(function (input) {
            input.setAttribute('data-miles-listo', '1');
            input.value = desdeServidor(input.value);

            input.addEventListener('input', function () {
                // Conserva el cursor contando los dígitos/coma a su izquierda.
                var pos = input.selectionStart || 0;
                var antes = input.value.slice(0, pos).replace(/[^\d,]/g, '').length;
                input.value = formatearMiles(input.value);
                var i = 0, cuenta = 0;
                while (i < input.value.length && cuenta < antes) {
                    if (/[\d,]/.test(input.value[i])) cuenta++;
                    i++;
                }
                input.setSelectionRange(i, i);
            });
        });
    }

    // Al enviar, todos los campos con miles pasan a número limpio.
    document.addEventListener('submit', function (e) {
        e.target.querySelectorAll('input[data-miles]').forEach(function (input) {
            input.value = limpiarMiles(input.value);
        });
    }, true);

    window.initCamposMiles = initCamposMiles;

})();
