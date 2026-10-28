/* Cadenza Inc. — conmutador de idioma.
   La visibilidad la resuelve el atributo data-idioma de <html>; este archivo
   solo guarda la elección, actualiza la dirección y mantiene el botón activo. */

(function () {
  "use strict";

  var CLAVE = "cadenza-idioma";

  function idiomaActual() {
    return document.documentElement.getAttribute("data-idioma") === "en" ? "en" : "es";
  }

  function sincroniza() {
    if (window.cadenzaIdioma && window.cadenzaIdioma.aplica) {
      window.cadenzaIdioma.aplica(idiomaActual());
    }
  }

  document.addEventListener("click", function (evento) {
    var boton = evento.target.closest ? evento.target.closest("[data-ir]") : null;
    if (!boton) return;
    var elegido = boton.getAttribute("data-ir") === "en" ? "en" : "es";
    if (window.cadenzaIdioma && window.cadenzaIdioma.aplica) {
      window.cadenzaIdioma.aplica(elegido);
    } else {
      document.documentElement.setAttribute("data-idioma", elegido);
      document.documentElement.setAttribute("lang", elegido);
    }
    try {
      localStorage.setItem(CLAVE, elegido);
    } catch (error) {
      /* navegación privada sin almacenamiento: la elección dura la página */
    }
    try {
      var destino = new URL(window.location.href);
      destino.searchParams.set("lang", elegido);
      window.history.replaceState(null, "", destino);
    } catch (error) {
      /* sin History API: el idioma queda igualmente aplicado */
    }
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", sincroniza);
  } else {
    sincroniza();
  }
})();
