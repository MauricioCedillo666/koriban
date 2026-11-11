/* Koriban · interacciones de la landing y el CRM (JavaScript sin dependencias) */
(function () {
  "use strict";

  function cookie(nombre) {
    const m = document.cookie.match("(^|;)\\s*" + nombre + "\\s*=\\s*([^;]+)");
    return m ? decodeURIComponent(m.pop()) : "";
  }
  function post(url, datos) {
    const cuerpo = new FormData();
    Object.keys(datos || {}).forEach(function (k) { cuerpo.append(k, datos[k]); });
    return fetch(url, {
      method: "POST", body: cuerpo, credentials: "same-origin",
      headers: { "X-CSRFToken": cookie("csrftoken"), "X-Requested-With": "fetch" },
    });
  }
  function escapar(t) {
    return String(t || "").replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function resaltar(texto, q) {
    const t = escapar(texto);
    if (!q) return t;
    const i = t.toLowerCase().indexOf(escapar(q).toLowerCase());
    if (i < 0) return t;
    return t.slice(0, i) + "<mark>" + t.slice(i, i + q.length) + "</mark>" + t.slice(i + q.length);
  }

  /* Mensajes flotantes: se ocultan solos */
  document.querySelectorAll(".mensaje").forEach(function (m) {
    setTimeout(function () { m.style.transition = "opacity .4s"; m.style.opacity = "0"; }, 4500);
    setTimeout(function () { m.remove(); }, 5000);
  });

  /* Confirmaciones */
  document.addEventListener("submit", function (e) {
    const texto = e.target.getAttribute("data-confirmar");
    if (texto && !window.confirm(texto)) e.preventDefault();
  });

  /* Campo "Especifica el giro" solo cuando el giro es "Otro" */
  const giro = document.getElementById("id_giro");
  const giroOtro = document.getElementById("id_giro_otro");
  if (giro && giroOtro) {
    const campo = giroOtro.closest(".campo") || giroOtro.parentElement;
    const actualizar = function () { campo.classList.toggle("oculto", giro.value !== "otro"); };
    giro.addEventListener("change", actualizar);
    actualizar();
  }

  /* Recurrencia de tareas: mostrar solo los campos que aplican */
  document.querySelectorAll("select[name=recurrencia]").forEach(function (sel) {
    const form = sel.closest("form");
    const nDias = form.querySelector("[name=cada_n_dias]");
    const hasta = form.querySelector("[name=repetir_hasta]");
    const actualizar = function () {
      if (nDias) (nDias.closest(".campo") || nDias).classList.toggle("oculto", sel.value !== "personalizada");
      if (hasta) (hasta.closest(".campo") || hasta).classList.toggle("oculto", sel.value === "ninguna");
    };
    sel.addEventListener("change", actualizar);
    actualizar();
  });

  /* Cajones (formularios que se despliegan) */
  document.querySelectorAll("[data-abrir]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const objetivo = document.getElementById(btn.getAttribute("data-abrir"));
      if (!objetivo) return;
      objetivo.classList.toggle("abierto");
      const primero = objetivo.querySelector("input:not([type=hidden]), textarea, select");
      if (objetivo.classList.contains("abierto") && primero) primero.focus();
    });
  });

  /* Pestañas del detalle de cliente (recuerda la pestaña por el #hash) */
  document.querySelectorAll("[data-tabs]").forEach(function (grupo) {
    const botones = grupo.querySelectorAll("[data-tab]");
    function activar(nombre) {
      let encontrado = false;
      botones.forEach(function (b) {
        const ok = b.getAttribute("data-tab") === nombre;
        b.classList.toggle("activo", ok);
        const panel = document.getElementById("panel-" + b.getAttribute("data-tab"));
        if (panel) panel.classList.toggle("activo", ok);
        encontrado = encontrado || ok;
      });
      return encontrado;
    }
    botones.forEach(function (b) {
      b.addEventListener("click", function () {
        activar(b.getAttribute("data-tab"));
        history.replaceState(null, "", "#" + b.getAttribute("data-tab"));
      });
    });
    const hash = location.hash.replace("#", "");
    if (!hash || !activar(hash)) activar(botones[0].getAttribute("data-tab"));
  });

  /* Buscador con sugerencias (nombre, empresa, teléfono o correo) */
  document.querySelectorAll("[data-buscador]").forEach(function (input) {
    const url = input.getAttribute("data-buscador");
    const caja = input.parentElement.querySelector(".sugerencias");
    let temporizador = null, indice = -1, ultimo = "", controlador = null;

    function cerrar() { caja.classList.add("oculto"); indice = -1; }
    function marcar() {
      caja.querySelectorAll("a").forEach(function (a, i) { a.classList.toggle("activo", i === indice); });
    }
    function pintar(lista, q) {
      if (!lista.length) {
        caja.innerHTML = '<div class="vacio">Sin coincidencias para «' + escapar(q) + "». Presiona Enter para buscar en todos los campos.</div>";
      } else {
        caja.innerHTML = lista.map(function (r) {
          const ini = (r.nombre || "?").split(" ").slice(0, 2).map(function (p) { return p.charAt(0); }).join("").toUpperCase();
          const sub = [r.empresa, r.telefono, r.email].filter(Boolean).map(function (x) { return resaltar(x, q); }).join(" · ");
          return '<a href="' + r.url + '"><span class="avatar">' + escapar(ini) + '</span><span class="info"><strong>' +
            resaltar(r.nombre, q) + "</strong><span>" + sub + '</span></span><span class="pill p-ok">' + escapar(r.etapa) + "</span></a>";
        }).join("");
      }
      indice = -1;
      caja.classList.remove("oculto");
    }
    function consultar() {
      const q = input.value.trim();
      if (q.length < 2) { cerrar(); return; }
      if (q === ultimo && !caja.classList.contains("oculto")) return;
      ultimo = q;
      if (controlador) controlador.abort();
      controlador = new AbortController();
      fetch(url + "?q=" + encodeURIComponent(q), { credentials: "same-origin", signal: controlador.signal })
        .then(function (r) { return r.json(); })
        .then(function (d) { pintar(d.resultados || [], q); })
        .catch(function () {});
    }
    input.addEventListener("input", function () {
      clearTimeout(temporizador);
      temporizador = setTimeout(consultar, 180);
    });
    input.addEventListener("focus", function () { if (input.value.trim().length >= 2) { ultimo = ""; consultar(); } });
    input.addEventListener("keydown", function (e) {
      const enlaces = caja.querySelectorAll("a");
      if (e.key === "ArrowDown" && enlaces.length) { e.preventDefault(); indice = (indice + 1) % enlaces.length; marcar(); }
      else if (e.key === "ArrowUp" && enlaces.length) { e.preventDefault(); indice = (indice - 1 + enlaces.length) % enlaces.length; marcar(); }
      else if (e.key === "Enter" && indice >= 0 && enlaces[indice]) { e.preventDefault(); window.location = enlaces[indice].href; }
      else if (e.key === "Escape") { cerrar(); }
    });
    document.addEventListener("click", function (e) { if (!input.parentElement.contains(e.target)) cerrar(); });
  });

  /* Embudo: arrastrar tarjetas entre etapas */
  const kanban = document.querySelector(".kanban");
  if (kanban) {
    let arrastrada = null;
    kanban.addEventListener("dragstart", function (e) {
      const t = e.target.closest(".tarjeta-k");
      if (!t) return;
      arrastrada = t;
      t.classList.add("arrastrando");
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", t.dataset.id);
    });
    kanban.addEventListener("dragend", function () {
      if (arrastrada) arrastrada.classList.remove("arrastrando");
      kanban.querySelectorAll(".columna").forEach(function (c) { c.classList.remove("sobre"); });
    });
    kanban.querySelectorAll(".columna").forEach(function (col) {
      col.addEventListener("dragover", function (e) { e.preventDefault(); col.classList.add("sobre"); });
      col.addEventListener("dragleave", function (e) { if (!col.contains(e.relatedTarget)) col.classList.remove("sobre"); });
      col.addEventListener("drop", function (e) {
        e.preventDefault();
        col.classList.remove("sobre");
        if (!arrastrada) return;
        const origen = arrastrada.closest(".columna");
        if (origen === col) return;
        const tarjeta = arrastrada;
        col.querySelector(".tarjetas").appendChild(tarjeta);
        actualizarCuentas();
        post(tarjeta.dataset.url, { etapa: col.dataset.etapa })
          .then(function (r) { if (!r.ok) throw new Error(); })
          .catch(function () {
            origen.querySelector(".tarjetas").appendChild(tarjeta);
            actualizarCuentas();
            alert("No se pudo mover la tarjeta. Intenta de nuevo.");
          });
      });
    });
    function actualizarCuentas() {
      kanban.querySelectorAll(".columna").forEach(function (c) {
        c.querySelector(".cuenta").textContent = c.querySelectorAll(".tarjeta-k").length;
      });
    }
  }

  /* WhatsApp: registra en el historial que se abrió el chat */
  document.querySelectorAll("[data-whatsapp-log]").forEach(function (a) {
    a.addEventListener("click", function () { post(a.getAttribute("data-whatsapp-log"), {}); });
  });
})();
