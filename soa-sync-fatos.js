/*!
 * soa-sync-fatos.js  ·  SOA/SOS — sincroniza folders comerciais com os JSONs canônicos.
 * Fonte única: o folder NÃO chumba fato/benefício; ele LÊ do JSON aprovado.
 * Governança: só LÊ status=="verificado"; nunca crava; nunca renderiza "pendente".
 * Segurança: injeta via textContent/DOM (nunca innerHTML com dado do JSON).
 *
 * Uso no HTML do folder:
 *   <script src="soa-sync-fatos.js"
 *     data-fontes="Fatos_Regulatorios_Folder_SOA.json,Fatos_Beneficios_ESG_Folder_SOA.json,Fatos_ESG_Folder_SOA.json"></script>
 *
 * Placeholders suportados:
 *   Escalar (dot-path namespaced por fonte):  <span data-fato="beneficios_esg._carimbo.fonte">fallback</span>
 *   Lista de benefícios por VETOR:            <div data-beneficios-vetor="BESS auditável"></div>
 *   Lista por ATOR / CANAL:                   <div data-beneficios-ator="pj"></div> · data-beneficios-canal="imposto"
 *   Pacote (cruzamento de vetores):           <div data-pacote="pkg_datacenter_247"></div>
 *   Carimbo:                                  <span data-carimbo></span>
 * Filtros combinam em E (vetor + ator + canal, se presentes juntos).
 */
(function () {
  "use strict";
  var STATUS_OK = "verificado";

  function getPath(obj, path) {
    return path.split(".").reduce(function (a, k) {
      return a && typeof a === "object" ? a[k] : undefined;
    }, obj);
  }
  function nsFromUrl(url) {
    return url.replace(/^.*\//, "").replace(/\.json$/i, "")
              .replace(/^Fatos_/i, "").replace(/_Folder_SOA$/i, "").toLowerCase();
  }
  function scriptEl() {
    return document.currentScript || document.querySelector('script[src*="soa-sync-fatos"]');
  }
  function fontes() {
    var el = scriptEl(), a = el && el.getAttribute("data-fontes");
    if (!a) return [];
    return a.split(",").map(function (s) { return s.trim(); }).filter(Boolean);
  }
  function collectArray(nsObj, key) {
    var out = [];
    Object.keys(nsObj).forEach(function (k) {
      var v = nsObj[k] && nsObj[k][key];
      if (Array.isArray(v)) out = out.concat(v);
    });
    return out;
  }
  function firstCarimbo(nsObj) {
    var found = null;
    Object.keys(nsObj).forEach(function (k) {
      if (!found && nsObj[k] && nsObj[k]._carimbo) found = nsObj[k]._carimbo;
    });
    return found;
  }
  function cell(tr, tag, cls, s) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    n.textContent = (s === undefined || s === null) ? "" : String(s);
    tr.appendChild(n);
    return n;
  }

  function ensureStyle() {
    if (document.getElementById("soa-sync-style")) return;
    var css = ".soa-ben-tbl{width:100%;border-collapse:collapse;border:1.5px solid #E0E2E2;border-radius:12px;overflow:hidden;font-size:13px;font-family:Arial,Helvetica,sans-serif}" +
      ".soa-ben-tbl thead th{background:#040F2F;color:#fff;text-align:left;padding:11px 13px;font-size:12px}" +
      ".soa-ben-tbl td{padding:11px 13px;border-top:1px solid #E0E2E2;vertical-align:top;line-height:1.5;color:#0d1424}" +
      ".soa-ben-tbl tr:nth-child(even) td{background:#f4f5f6}" +
      ".soa-ben-tit{font-weight:bold;color:#040F2F}.soa-ben-sem{color:#9a3412;font-weight:600}" +
      ".soa-pacote{border:1.5px solid #1C5AAD;border-radius:14px;padding:18px 20px;background:#e7eefb;margin:0 0 16px}" +
      ".soa-pacote h4{margin:0 0 6px;color:#040F2F;font:700 17px Arial,Helvetica,sans-serif}" +
      ".soa-pacote .tese{color:#4a4f55;font-size:14px;margin:0 0 10px;line-height:1.55}" +
      ".soa-pacote .sem{color:#9a3412;font-size:12.5px;font-weight:600;margin-top:10px}";
    var s = document.createElement("style");
    s.id = "soa-sync-style"; s.textContent = css;
    document.head.appendChild(s);
  }

  function tabelaBeneficios(lista) {
    var tbl = document.createElement("table");
    tbl.className = "soa-ben-tbl";
    var thead = document.createElement("thead"), htr = document.createElement("tr");
    ["Benefício", "Base legal", "Mecanismo", "Vigência", "Sem SOA"].forEach(function (h) { cell(htr, "th", null, h); });
    thead.appendChild(htr); tbl.appendChild(thead);
    var tb = document.createElement("tbody");
    lista.forEach(function (b) {
      var tr = document.createElement("tr");
      cell(tr, "td", "soa-ben-tit", b.titulo);
      cell(tr, "td", null, b.base_legal);
      cell(tr, "td", null, b.mecanismo);
      cell(tr, "td", null, b.vigencia);
      cell(tr, "td", "soa-ben-sem", b.sem_soa);
      tb.appendChild(tr);
    });
    tbl.appendChild(tb);
    return tbl;
  }

  function filtrar(beneficios, f) {
    return beneficios.filter(function (b) {
      if (b.status !== STATUS_OK) return false;
      if (f.vetor && !(Array.isArray(b.vetores) && b.vetores.indexOf(f.vetor) !== -1)) return false;
      if (f.ator && !(Array.isArray(b.ator) && b.ator.indexOf(f.ator) !== -1)) return false;
      if (f.canal && b.canal !== f.canal) return false;
      return true;
    });
  }

  function aplicar(nsObj) {
    ensureStyle();
    var beneficios = collectArray(nsObj, "beneficios");
    var pacotes = collectArray(nsObj, "pacotes");

    // 1) escalares (dot-path namespaced), preservando fallback se faltar a chave
    document.querySelectorAll("[data-fato]").forEach(function (n) {
      var v = getPath(nsObj, n.getAttribute("data-fato"));
      if (v === undefined || v === null || v === "") { n.setAttribute("data-fato-status", "fallback"); }
      else { n.textContent = String(v); n.setAttribute("data-fato-status", "sincronizado"); }
    });

    // 2) listas de benefícios por vetor / ator / canal
    document.querySelectorAll("[data-beneficios-vetor],[data-beneficios-ator],[data-beneficios-canal]").forEach(function (host) {
      var f = {
        vetor: host.getAttribute("data-beneficios-vetor") || null,
        ator: host.getAttribute("data-beneficios-ator") || null,
        canal: host.getAttribute("data-beneficios-canal") || null
      };
      var lista = filtrar(beneficios, f);
      if (lista.length) { host.innerHTML = ""; host.appendChild(tabelaBeneficios(lista)); host.setAttribute("data-fato-status", "sincronizado"); }
      else { host.setAttribute("data-fato-status", "fallback"); }
    });

    // 3) pacotes (cruzamento de vetores)
    document.querySelectorAll("[data-pacote]").forEach(function (host) {
      var id = host.getAttribute("data-pacote");
      var p = pacotes.filter(function (x) { return x.id === id && x.status === STATUS_OK; })[0];
      if (!p) { host.setAttribute("data-fato-status", "fallback"); return; }
      var box = document.createElement("div"); box.className = "soa-pacote";
      var h = document.createElement("h4"); h.textContent = p.titulo; box.appendChild(h);
      var t = document.createElement("p"); t.className = "tese"; t.textContent = p.tese; box.appendChild(t);
      var ids = Array.isArray(p.beneficios) ? p.beneficios : [];
      var lista = ids.map(function (bid) { return beneficios.filter(function (b) { return b.id === bid && b.status === STATUS_OK; })[0]; })
                     .filter(Boolean);
      if (lista.length) box.appendChild(tabelaBeneficios(lista));
      if (p.sem_soa) { var s = document.createElement("div"); s.className = "sem"; s.textContent = "Sem a SOA: " + p.sem_soa; box.appendChild(s); }
      host.innerHTML = ""; host.appendChild(box); host.setAttribute("data-fato-status", "sincronizado");
    });

    // 4) carimbo
    var carimbo = firstCarimbo(nsObj) || {};
    document.querySelectorAll("[data-carimbo]").forEach(function (n) {
      var q = carimbo.atualizado_em ? new Date(carimbo.atualizado_em) : null;
      n.textContent = q
        ? "Dados verificados e selados em " + q.toLocaleString("pt-BR") + (carimbo.hash ? " · " + String(carimbo.hash).slice(0, 20) + "…" : "")
        : "Dados do monitor regulatório SOA/SOS";
    });

    document.documentElement.setAttribute("data-soa-sync", "ok");
  }

  function carregar() {
    var urls = fontes();
    if (!urls.length) { console.warn("[soa-sync] sem data-fontes."); return; }
    Promise.all(urls.map(function (url) {
      return fetch(url, { cache: "no-store" })
        .then(function (r) { if (!r.ok) throw new Error(url + " " + r.status); return r.json(); })
        .then(function (j) { return { ns: nsFromUrl(url), data: j }; })
        .catch(function (e) { console.warn("[soa-sync] falha em", url, e); return { ns: nsFromUrl(url), data: {} }; });
    })).then(function (pares) {
      var nsObj = {};
      pares.forEach(function (p) { nsObj[p.ns] = p.data; });   // namespaced por fonte — sem clobbering
      aplicar(nsObj);
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", carregar);
  else carregar();
})();
