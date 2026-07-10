/* ============================================================================
 * soa-carimbo.js  -  Carimbo dinamico unico para os folders/catalogo SOA/SOS
 * ----------------------------------------------------------------------------
 * Mostra a data/hora REAL da ultima atualizacao de CADA pagina, lendo o
 * timestamp do ultimo commit do proprio arquivo na API publica do GitHub.
 * Atualiza sozinho a cada push -> o carimbo nunca mais e escrito a mao.
 *
 * USO: incluir UMA linha antes de </body> em cada pagina estatica:
 *   <script src="/financiamento-de-usinas/soa-carimbo.js" defer></script>
 *
 * Ele se autoinjeta: acha o elemento de carimbo existente (#soaStamp, .soa-stamp,
 * .live-stamp, .stamp, ou qualquer elemento cujo texto comece com "Atualizado em")
 * e troca o texto. Se nao achar nenhum, cria um selo fixo no canto sup. direito.
 * Se a API falhar (offline / rate-limit), mantem o texto que ja estava (nao apaga).
 * ============================================================================ */
(function () {
  var REPO = 'trigocom-code/financiamento-de-usinas';

  function pad(n) { return n < 10 ? '0' + n : '' + n; }
  function fmt(d) {
    return pad(d.getDate()) + '/' + pad(d.getMonth() + 1) + '/' + d.getFullYear() +
           ' as ' + pad(d.getHours()) + 'h' + pad(d.getMinutes());
  }

  // caminho do arquivo dentro do repo, a partir da URL publicada no GitHub Pages
  function repoPath() {
    var p = decodeURIComponent(location.pathname);
    var seg = REPO.split('/')[1];               // nome do repo
    var i = p.indexOf('/' + seg + '/');
    if (i >= 0) p = p.slice(i + seg.length + 2);
    else p = p.replace(/^\//, '');
    if (p === '' || p.charAt(p.length - 1) === '/') p += 'index.html';
    return p;
  }

  function findStamp() {
    var el = document.getElementById('soaStamp') ||
             document.querySelector('.soa-stamp, .live-stamp, .stamp');
    if (el) return el;
    var all = document.body ? document.body.getElementsByTagName('*') : [];
    for (var k = 0; k < all.length; k++) {
      var t = (all[k].textContent || '').trim();
      if (all[k].children.length === 0 && /^[●•\s]*Atualizado em/i.test(t)) return all[k];
    }
    return null;
  }

  function setStamp(txt) {
    var el = findStamp();
    if (!el) {
      el = document.createElement('div');
      el.id = 'soaStamp';
      el.style.cssText = 'position:fixed;top:9px;right:12px;z-index:99999;background:#0b1f4d;' +
        'color:#FEC73D;font:600 11px/1.1 Arial,Helvetica,sans-serif;letter-spacing:.03em;' +
        'padding:5px 11px;border-radius:999px;white-space:nowrap;box-shadow:0 2px 8px rgba(0,0,0,.35)';
      (document.body || document.documentElement).appendChild(el);
    }
    el.textContent = txt;
    el.setAttribute('data-soa-carimbo', 'dinamico');
  }

  function docDate() {
    try { var d = new Date(document.lastModified); return isNaN(d.getTime()) ? null : d; }
    catch (e) { return null; }
  }
  function dateOnly(d) { return pad(d.getDate()) + '/' + pad(d.getMonth() + 1) + '/' + d.getFullYear(); }

  function run() {
    var path = repoPath();
    var CK = 'soa_carimbo_' + path, TTL = 6 * 3600 * 1000;

    // 1) Fallback IMEDIATO e sempre fresco: a data de deploy da propria pagina
    //    (document.lastModified). Garante que o valor hardcoded velho NUNCA
    //    apareca, mesmo se a API do GitHub falhar (rate-limit / offline).
    var dd = docDate();
    if (dd) setStamp('● Atualizado em ' + dateOnly(dd));

    // 2) Cache local (evita bater na API a cada refresh / em muitas abas —
    //    era isso que estourava o rate-limit e ressuscitava a data velha).
    try {
      var raw = localStorage.getItem(CK);
      if (raw) { var o = JSON.parse(raw);
        if (o && o.t && (Date.now() - o.t) < TTL && o.d) { setStamp('● Atualizado em ' + o.d); return; } }
    } catch (e) {}

    // 3) Fonte da verdade: data/hora do ULTIMO COMMIT do proprio arquivo.
    var url = 'https://api.github.com/repos/' + REPO + '/commits?path=' +
              encodeURIComponent(path) + '&per_page=1';
    fetch(url, { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (c) {
        if (!c.length) throw 0;
        var txt = fmt(new Date(c[0].commit.committer.date));
        setStamp('● Atualizado em ' + txt);
        try { localStorage.setItem(CK, JSON.stringify({ t: Date.now(), d: txt })); } catch (e) {}
      })
      .catch(function () { /* mantem o document.lastModified — nunca o hardcoded velho */ });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run);
  else run();
})();
