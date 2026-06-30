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

  function run() {
    var url = 'https://api.github.com/repos/' + REPO + '/commits?path=' +
              encodeURIComponent(repoPath()) + '&per_page=1';
    fetch(url, { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (c) {
        if (!c.length) throw 0;
        var d = new Date(c[0].commit.committer.date);
        setStamp('● Atualizado em ' + fmt(d));
      })
      .catch(function () { /* mantem o carimbo existente se a API falhar */ });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run);
  else run();
})();
