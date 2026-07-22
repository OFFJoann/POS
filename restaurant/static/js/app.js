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

    });

    // ─── DataTables ───────────────────────────────────────────────
    function initDataTables() {
        if (typeof $.fn.DataTable !== 'undefined') {
            $('.datatable').each(function() {
                if (!$(this).hasClass('dataTable')) {
                    $(this).DataTable({
                        language: {
                            url: '//cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json'
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
        var container = $('#contenedor-mesas');
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
                                card.removeClass('mesa-libre mesa-activo mesa-parcial mesa-pagada mesa-cerrada')
                                    .addClass('mesa-' + mesa.estado);
                                card.find('.mesa-estado-badge span')
                                    .removeClass('estado-libre estado-activo estado-parcial estado-pagada estado-cerrada')
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

})();
