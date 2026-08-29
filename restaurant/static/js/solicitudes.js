(function () {
  'use strict';
  var POLL_MS = 5000;
  var STORAGE_KEY = 'solicitudes_anunciadas';
  var modalEl = null;

  function cargarAnunciadas() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
    } catch (e) {
      return {};
    }
  }

  function guardarAnunciadas(obj) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(obj));
    } catch (e) {}
  }

  function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      var cookies = document.cookie.split(';');
      for (var i = 0; i < cookies.length; i++) {
        var c = cookies[i].trim();
        if (c.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(c.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function obtenerPendientes(silencioso) {
    fetch('/mesas/solicitudes/pendientes/?_=' + Date.now(), {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      cache: 'no-store'
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.solicitudes) return;
        var anunciadas = cargarAnunciadas();
        var hayNuevas = false;
        // El modal solo sale UNA vez por solicitud (persistente entre
        // navegaciones). En la carga inicial (silencioso) solo se registran
        // las existentes sin mostrar el modal.
        data.solicitudes.forEach(function (s) {
          if (!(s.id in anunciadas) && !silencioso) {
            hayNuevas = true;
          }
          anunciadas[s.id] = true;
        });
        guardarAnunciadas(anunciadas);
        renderizar(data.solicitudes);
        if (hayNuevas) mostrarModal();
      })
      .catch(function () {});
  }

  function renderizar(solicitudes) {
    var body = document.getElementById('solicitudesBody');
    if (!body) return;
    if (!solicitudes.length) {
      body.innerHTML = '<p class="text-muted text-center mb-0">No hay pedidos pendientes.</p>';
      return;
    }
    var html = '';
    solicitudes.forEach(function (s) {
      var items = '';
      s.items.forEach(function (i) {
        items += '<li>' + i.cantidad + ' × ' + i.producto + (i.cortesia ? ' 🎁' : '') + '</li>';
      });
      html += '<div class="card mb-2 border-warning">'
        + '<div class="card-header d-flex justify-content-between align-items-center py-2">'
        + '<strong>Mesa ' + s.mesa + '</strong>'
        + '<small class="text-muted">' + s.created_at + ' · ' + s.solicitante + '</small>'
        + '</div>'
        + '<div class="card-body py-2">'
        + '<ul class="mb-2">' + items + '</ul>'
        + '<button class="btn btn-success btn-sm w-100 btn-atender" data-id="' + s.id + '">'
        + '<i class="bi bi-check-lg"></i> Marcar atendida</button>'
        + '</div></div>';
    });
    body.innerHTML = html;
    var botones = body.querySelectorAll('.btn-atender');
    for (var i = 0; i < botones.length; i++) {
      botones[i].addEventListener('click', function () {
        atender(this.getAttribute('data-id'));
      });
    }
  }

  function atender(id) {
    var fd = new FormData();
    fetch('/mesas/solicitudes/' + id + '/atender/', {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: fd
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.ok) {
        var anunciadas = cargarAnunciadas();
        delete anunciadas[id];
        guardarAnunciadas(anunciadas);
        obtenerPendientes(true);
      }
    });
  }

  function mostrarModal() {
    if (!modalEl) modalEl = document.getElementById('modalSolicitudes');
    if (!modalEl) return;
    var m = bootstrap.Modal.getOrCreateInstance(modalEl);
    m.show();
  }

  document.addEventListener('DOMContentLoaded', function () {
    modalEl = document.getElementById('modalSolicitudes');
    obtenerPendientes(true);
    setInterval(function () { obtenerPendientes(false); }, POLL_MS);
  });
})();
