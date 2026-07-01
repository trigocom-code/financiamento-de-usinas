/* ============================================================================
 * soa-quadro-vivo.js — Quadro Regulatorio Vivo dos folders comerciais SOA/SOS
 * ----------------------------------------------------------------------------
 * Cada folder comercial (Tipo B, hardcoded) passa a exibir, em runtime, o
 * ESTADO REAL dos fatos regulatorios de que depende — lidos do GitHub raw
 * (Folder_Deps_SOA.json -> Fatos_<orgao>_Folder_SOA.json), com cache-buster.
 * Fecha a promessa do catalogo: o folder reflete o monitor na hora, sem
 * reescrever o HTML. Se qualquer fetch falhar, nao renderiza nada (gracioso).
 * USO: <script src="/financiamento-de-usinas/soa-quadro-vivo.js" defer></script>
 * ============================================================================ */
(function () {
  var RAW = 'https://raw.githubusercontent.com/trigocom-code/financiamento-de-usinas/main/';
  var bust = function (u) { return u + (u.indexOf('?') >= 0 ? '&' : '?') + 'v=' + Date.now(); };
  var page = decodeURIComponent(location.pathname.split('/').pop() || 'index.html');

  function chip(status) { // paleta canonica SOA
    var s = (status || '').toUpperCase();
    if (s.indexOf('VIGENTE') >= 0 || s.indexOf('ANCORADO') >= 0) return ['#1B5E20', 'VIGENTE' === s ? s : status];
    if (s.indexOf('AGENDADO') >= 0) return ['#1C5AAD', status];
    if (s.indexOf('CADUCADA') >= 0) return ['#8B0000', status];
    return ['#B45309', status || 'EM DELIBERAÇÃO']; // EM DELIBERACAO / TRAMITACAO / PENDENTE
  }
  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML; }

  function j(url) { return fetch(bust(url), { cache: 'no-store' }).then(function (r) { if (!r.ok) throw 0; return r.json(); }); }

  j(RAW + 'Folder_Deps_SOA.json').then(function (deps) {
    var fd = (deps.folders || []).filter(function (f) { return f.folder === page; })[0];
    if (!fd || fd.categoria !== 'vivo_sob_gatilho' || !(fd.depende_de || []).length) return;
    var jsons = {};
    (fd.depende_de || []).forEach(function (d) { jsons[d.json] = true; });
    var nomes = Object.keys(jsons);
    return Promise.all(nomes.map(function (nb) {
      return j(RAW + nb + '_Folder_SOA.json').catch(function () { return null; });
    })).then(function (docs) {
      var porJson = {}; nomes.forEach(function (nb, i) { porJson[nb] = docs[i]; });
      var itens = [];
      (fd.depende_de || []).forEach(function (dep) {
        var d = porJson[dep.json]; if (!d) return;
        var todos = (d.fatos || []).concat(d._pendentes_verificacao || []);
        var f = todos.filter(function (x) { return x.fato_id === dep.ref || x.tema === dep.ref; })[0];
        if (f) itens.push(f);
      });
      if (!itens.length) return;
      render(itens);
    });
  }).catch(function () { /* silencio gracioso */ });

  function render(itens) {
    var maxV = itens.map(function (f) { return f.verificado_em || ''; }).sort().pop() || '';
    var wrap = document.createElement('div');
    wrap.id = 'soaQuadroVivo';
    wrap.style.cssText = 'position:fixed;bottom:0;left:0;right:0;z-index:99998;font-family:Arial,Helvetica,sans-serif;';
    var lista = itens.map(function (f) {
      var c = chip(f.status);
      var pend = f.pendencia_verificacao ? ' <span style="color:#FEC73D">· pendência: ' + esc(f.pendencia_verificacao) + '</span>' : '';
      return '<div style="padding:6px 0;border-top:1px solid rgba(255,255,255,.12);font-size:12px;line-height:1.45;color:#E0E2E2">' +
        '<span style="background:' + c[0] + ';color:#fff;border-radius:999px;padding:2px 9px;font-size:10.5px;font-weight:700;letter-spacing:.03em;white-space:nowrap">' + esc(c[1]) + '</span> ' +
        '<strong style="color:#fff">' + esc(f.norma || f.fato_id || '') + '</strong> — ' + esc(f.tema || '') + pend +
        (f.verificado_em ? ' <span style="opacity:.65">(verificado ' + esc(String(f.verificado_em).slice(0, 16).replace('T', ' ')) + ')</span>' : '') +
        '</div>';
    }).join('');
    wrap.innerHTML =
      '<div style="max-width:1080px;margin:0 auto;background:#040F2F;border:1px solid #FEC73D;border-bottom:none;border-radius:10px 10px 0 0;box-shadow:0 -4px 18px rgba(0,0,0,.35)">' +
      '<button id="soaQVtoggle" style="all:unset;cursor:pointer;display:block;width:100%;box-sizing:border-box;padding:9px 16px;color:#FEC73D;font-size:12.5px;font-weight:700;letter-spacing:.02em">' +
      '&#9673; Quadro regulatório vivo — ' + itens.length + ' fato(s) monitorados' +
      (maxV ? ' · verificado em ' + esc(String(maxV).slice(0, 10).split('-').reverse().join('/')) : '') +
      ' <span id="soaQVarrow" style="float:right;color:#E0E2E2">&#9650;</span></button>' +
      '<div id="soaQVbody" style="display:none;padding:2px 16px 12px 16px">' + lista +
      '<div style="padding-top:7px;font-size:10.5px;color:#9aa4b5">Fonte: monitores regulatórios SOA/SOS · JSON canônico lido em tempo real do repositório público · os estados acima mudam quando o monitor valida a fonte oficial.</div>' +
      '</div></div>';
    (document.body || document.documentElement).appendChild(wrap);
    var b = document.getElementById('soaQVbody'), a = document.getElementById('soaQVarrow');
    document.getElementById('soaQVtoggle').addEventListener('click', function () {
      var aberto = b.style.display !== 'none';
      b.style.display = aberto ? 'none' : 'block';
      a.innerHTML = aberto ? '&#9650;' : '&#9660;';
    });
  }
})();
