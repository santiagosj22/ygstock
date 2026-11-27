(function (root) {
  "use strict";

  var GRITO = {
    "Usado": "🔥 ¡TODOS NUESTROS EQUIPOS USADOS! 🔥",
    "Exhibición": "🔥 ¡TODOS NUESTROS EQUIPOS DE EXHIBICIÓN! 🔥",
    "Nuevo": "🔥 ¡TODOS NUESTROS EQUIPOS NUEVOS! 🔥",
    "Open box": "🔥 ¡TODOS NUESTROS EQUIPOS OPEN BOX! 🔥",
    "Outlet": "🔥 ¡TODOS NUESTROS EQUIPOS OUTLET! 🔥"
  };
  var CIERRE = {
    "Usado": "🔥 ¡EQUIPOS USADOS A EXCELENTES PRECIOS!",
    "Exhibición": "🔥 ¡EQUIPOS DE EXHIBICIÓN A EXCELENTES PRECIOS!",
    "Nuevo": "🔥 ¡EQUIPOS NUEVOS A EXCELENTES PRECIOS!",
    "Open box": "🔥 ¡EQUIPOS OPEN BOX A EXCELENTES PRECIOS!",
    "Outlet": "🔥 ¡EQUIPOS OUTLET A EXCELENTES PRECIOS!"
  };

  function sinTildes(texto) {
    return String(texto || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  }

  function clasificar(texto) {
    var base = sinTildes(texto).toUpperCase();
    var hallado = base.match(/IPHONE\s+(SE(?:\s*\d)?|\d+\s*E|\d+)(?:\s+(PRO\s+MAX|PRO|PLUS|MINI))?/);
    if (!hallado) {
      return {
        serie: "OTROS",
        tituloSerie: "OTROS EQUIPOS",
        modelo: String(texto || "EQUIPO").trim() || "EQUIPO",
        ordenSerie: -2,
        ordenModelo: 9,
        emojiSerie: "📱",
        emojiModelo: "📱"
      };
    }
    var crudo = hallado[1].replace(/\s+/g, "");
    var variante = (hallado[2] || "").replace(/\s+/g, " ");
    var esE = /^\d+E$/.test(crudo);
    var numero = parseInt(crudo, 10);
    var tieneNumero = !isNaN(numero);
    var serie = tieneNumero ? String(numero) : crudo;
    var generacion = esE ? crudo.replace(/E$/, "e") : serie;
    var ordenModelo = variante === "MINI" ? 0 : esE ? 1 : variante === "PLUS" ? 3 : variante === "PRO" ? 4 : variante === "PRO MAX" ? 5 : 2;
    return {
      serie: serie,
      tituloSerie: "IPHONE " + serie + " SERIES",
      modelo: ("IPHONE " + generacion + (variante ? " " + variante : "")).trim(),
      ordenSerie: tieneNumero ? numero : -1,
      ordenModelo: ordenModelo,
      emojiSerie: serie === "16" ? "👑" : serie === "15" || serie === "14" ? "💎" : serie === "13" ? "🔥" : "📱",
      emojiModelo: variante === "PRO MAX" ? "👑" : variante === "PRO" ? "⭐" : variante === "PLUS" ? "🔥" : "📱"
    };
  }

  function capacidadDe(item) {
    var ram = String(item.ram || "").match(/(\d+)/);
    var memoria = String(item.almacenamiento || "").match(/(\d+)\s*(GB|TB)/i);
    if (ram && memoria) return ram[1] + "+" + memoria[1] + memoria[2].toUpperCase();
    if (memoria) return memoria[1] + memoria[2].toUpperCase();
    return "";
  }

  function pesoMemoria(item) {
    var memoria = String(item.almacenamiento || "").match(/(\d+)\s*(GB|TB)/i);
    if (!memoria) return 0;
    var cantidad = parseInt(memoria[1], 10) || 0;
    return memoria[2].toUpperCase() === "TB" ? cantidad * 1024 : cantidad;
  }

  function simDe(item) {
    var sim = sinTildes(item.sim).toUpperCase();
    if (!sim) return "";
    if (sim.indexOf("E-SIM") !== -1 || sim.indexOf("ESIM") !== -1) return "E-SIM";
    return "SIM FÍSICA";
  }

  function precioDe(item) {
    var numero = String(item.precio || "").replace(/[^\d.]/g, "").replace(/^\.+/, "");
    return numero ? "*$ " + numero + "*" : "";
  }

  function fuenteDe(item) {
    if (/iphone/i.test(item.descripcion || "")) return item.descripcion;
    return item.nombre || item.descripcion || "";
  }

  var ORDEN_CLASE = { "Usado": 0, "Outlet": 1, "Exhibición": 2, "Open box": 3, "Nuevo": 4 };

  function ordenClase(clase) {
    if (!clase) return 9;
    return Object.prototype.hasOwnProperty.call(ORDEN_CLASE, clase) ? ORDEN_CLASE[clase] : 8;
  }

  function ordenSerieVista(fila) {
    if (fila.serie === "OTROS") return 10000;
    if (fila.ordenSerie < 0) return 9000;
    return fila.ordenSerie;
  }

  function ordenSim(sim) {
    if (sim === "SIM FÍSICA") return 0;
    if (sim === "E-SIM") return 1;
    return 2;
  }

  function compararBase(a, b) {
    return ordenSerieVista(a) - ordenSerieVista(b) || a.ordenModelo - b.ordenModelo || a.modelo.localeCompare(b.modelo, "es") || a.almacen - b.almacen || a.ramNum - b.ramNum || ordenSim(a.sim) - ordenSim(b.sim) || b.precioNum - a.precioNum;
  }

  function mensajeDifusion(items, modo) {
    var filas = (items || []).map(function (item) {
      var modelo = clasificar(fuenteDe(item));
      var ram = String(item.ram || "").match(/(\d+)/);
      return {
        serie: modelo.serie,
        tituloSerie: modelo.tituloSerie,
        modelo: modelo.modelo,
        ordenSerie: modelo.ordenSerie,
        ordenModelo: modelo.ordenModelo,
        emojiSerie: modelo.emojiSerie,
        emojiModelo: modelo.emojiModelo,
        capacidad: capacidadDe(item),
        almacen: pesoMemoria(item),
        ramNum: ram ? parseInt(ram[1], 10) : 0,
        sim: simDe(item),
        precio: precioDe(item),
        precioNum: parseInt(String(item.precio || "").replace(/\D/g, ""), 10) || 0,
        clase: item.clase || "",
        color: String(item.color || "").trim().toLocaleUpperCase("es")
      };
    });
    if (!filas.length) return "";

    var grupos = new Map();
    filas.forEach(function (fila) {
      var clave = [fila.modelo, fila.capacidad, fila.sim, fila.clase].join("\n");
      var grupo = grupos.get(clave);
      if (!grupo) {
        grupo = Object.assign({}, fila, { precios: new Map() });
        grupos.set(clave, grupo);
      }
      var colores = grupo.precios.get(fila.precio);
      if (!colores) {
        colores = [];
        grupo.precios.set(fila.precio, colores);
      }
      if (fila.color && colores.indexOf(fila.color) === -1) colores.push(fila.color);
      if (fila.precioNum > grupo.precioNum) grupo.precioNum = fila.precioNum;
    });

    var lista = Array.from(grupos.values());
    lista.forEach(function (grupo) {
      grupo.precios.forEach(function (colores) {
        colores.sort(function (a, b) { return a.localeCompare(b, "es"); });
      });
    });
    var porClase = modo === "clase";
    lista.sort(function (a, b) {
      if (porClase) return ordenClase(a.clase) - ordenClase(b.clase) || compararBase(a, b);
      return ordenSerieVista(a) - ordenSerieVista(b) || a.ordenModelo - b.ordenModelo || a.modelo.localeCompare(b.modelo, "es") || ordenClase(a.clase) - ordenClase(b.clase) || a.almacen - b.almacen || a.ramNum - b.ramNum || ordenSim(a.sim) - ordenSim(b.sim) || b.precioNum - a.precioNum;
    });

    var clases = filas.map(function (fila) { return fila.clase; }).filter(Boolean);
    var unicas = Array.from(new Set(clases));
    var claseUnica = unicas.length === 1 ? unicas[0] : "";

    var cuerpo = [];
    var estado = { serie: "", modelo: "", clase: "", bloque: null };
    lista.forEach(function (grupo) {
      if (porClase && grupo.clase !== estado.bloque) {
        if (estado.bloque !== null) cuerpo.push("");
        estado.bloque = grupo.clase;
        estado.serie = "";
        estado.modelo = "";
        cuerpo.push("━━━━━━━━━━━━━━━━━━");
        cuerpo.push((grupo.clase || "Sin clase").toLocaleUpperCase("es"));
        cuerpo.push("━━━━━━━━━━━━━━━━━━");
        cuerpo.push("");
      }
      if (grupo.serie !== estado.serie) {
        if (estado.serie) cuerpo.push("");
        estado.serie = grupo.serie;
        estado.modelo = "";
        estado.clase = "";
        cuerpo.push("━━━━━━━━━━━━━━━━━━");
        cuerpo.push(grupo.emojiSerie + " " + grupo.tituloSerie);
        cuerpo.push("━━━━━━━━━━━━━━━━━━");
        cuerpo.push("");
      }
      if (grupo.modelo !== estado.modelo) {
        if (estado.modelo) cuerpo.push("");
        estado.modelo = grupo.modelo;
        estado.clase = "";
        cuerpo.push(grupo.emojiModelo + " " + grupo.modelo);
      }
      if (!porClase && grupo.clase !== estado.clase) {
        estado.clase = grupo.clase;
        cuerpo.push(grupo.clase || "Sin clase");
      }
      var detalle = [grupo.capacidad, grupo.sim].filter(Boolean).join(" ");
      var tarifas = Array.from(grupo.precios.entries()).sort(function (a, b) {
        var izquierda = parseInt(String(a[0]).replace(/\D/g, ""), 10) || 0;
        var derecha = parseInt(String(b[0]).replace(/\D/g, ""), 10) || 0;
        return derecha - izquierda;
      });
      var unaTarifa = tarifas.length === 1;
      var linea = "• " + (detalle || grupo.modelo);
      if (unaTarifa && tarifas[0][1].length === 1) linea += " – " + tarifas[0][1][0];
      cuerpo.push(linea);
      if (unaTarifa) {
        if (tarifas[0][0]) cuerpo.push("💰 " + tarifas[0][0]);
        if (tarifas[0][1].length > 1) cuerpo.push("🎨 Disponible en estos colores: " + tarifas[0][1].join(", "));
      } else {
        tarifas.forEach(function (tarifa) {
          cuerpo.push(tarifa[1].join(", ") + " 💰 " + tarifa[0]);
        });
      }
      cuerpo.push("");
    });

    var texto = [
      "🚨🍎 iQLICK – LISTADO DE IPHONES 🍎🚨",
      ""
    ];
    if (GRITO[claseUnica]) {
      texto.push(GRITO[claseUnica]);
      texto.push("");
    }
    texto.push("📱 Excelente variedad de referencias.");
    texto.push("💰 Precios especiales para mayoristas y distribuidores.");
    texto.push("");
    texto = texto.concat(cuerpo);
    texto.push("━━━━━━━━━━━━━━━━━━");
    texto.push("");
    texto.push(CIERRE[claseUnica] || "🔥 ¡EQUIPOS A EXCELENTES PRECIOS!");
    texto.push("");
    texto.push("📲 Escríbenos para consultar disponibilidad y separar tus equipos.");
    texto.push("");
    texto.push("🤝 Atención personalizada");
    texto.push("💰 Precios competitivos");
    texto.push("🚀 ¡Grandes oportunidades para tu negocio!");
    texto.push("");
    texto.push("🍎 iQLICK – TU ALIADO EN TECNOLOGÍA.");
    return texto.join("\n").replace(/\n{3,}/g, "\n\n");
  }

  root.mensajeDifusion = mensajeDifusion;
})(typeof window !== "undefined" ? window : globalThis);
