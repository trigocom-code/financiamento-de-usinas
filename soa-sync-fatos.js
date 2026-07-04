/*!
 * soa-sync-fatos.js  ·  SOA/SOS — sincroniza folders comerciais com os JSONs canônicos.
 * Fonte única: o folder NÃO chumba fato/benefício; ele LÊ do JSON aprovado.
 * Governança: só LÊ status=="verificado"; nunca crava; nunca renderiza "pendente".
 * Segurança: injeta via textContent/DOM (nunca innerHTML com dado do JSON).
 *
 * Placeholder principal (os TRÊS tópicos do protocolo SOA, num único bloco):
 *   <div data-composicao-vetor="BESS auditável"></div>
 *     1 · O que entregamos   (Evidence Pack / HEC / sHEC do vetor)
 *     2 · O que o cliente ganha  (benefícios filtrados, só verificado)
 *     3 · O que você pode acessar  (adjacências que a composição destrava)
 *
 * Placeholders auxiliares (retrocompatíveis):
 *   <div data-entregaveis-vetor="X"></div> · <div data-beneficios-vetor|ator|canal="X"></div>
 *   <div data-pacote="pkg_id"></div> · <span data-fato="ns.caminho">fallback</span> · <span data-carimbo></span>
 *
 * <script src="soa-sync-fatos.js" data-fontes="Fatos_Regulatorios_Folder_SOA.json,Fatos_Beneficios_ESG_Folder_SOA.json"></script>
 */
(function () {
  "use strict";
  var STATUS_OK = "verificado";

  function getPath(o, p){ return p.split(".").reduce(function(a,k){ return a && typeof a==="object" ? a[k] : undefined; }, o); }
  function nsFromUrl(u){ return u.replace(/^.*\//,"").replace(/\.json$/i,"").replace(/^Fatos_/i,"").replace(/_Folder_SOA$/i,"").toLowerCase(); }
  function scriptEl(){ return document.currentScript || document.querySelector('script[src*="soa-sync-fatos"]'); }
  function fontes(){ var el=scriptEl(), a=el&&el.getAttribute("data-fontes"); return a ? a.split(",").map(function(s){return s.trim();}).filter(Boolean) : []; }
  function collectArray(ns, key){ var out=[]; Object.keys(ns).forEach(function(k){ var v=ns[k]&&ns[k][key]; if(Array.isArray(v)) out=out.concat(v); }); return out; }
  function firstCarimbo(ns){ var f=null; Object.keys(ns).forEach(function(k){ if(!f && ns[k] && ns[k]._carimbo) f=ns[k]._carimbo; }); return f; }
  function el(tag, cls, txt){ var n=document.createElement(tag); if(cls)n.className=cls; if(txt!=null)n.textContent=String(txt); return n; }
  function cell(tr, tag, cls, s){ var n=el(tag,cls, s==null?"":s); tr.appendChild(n); return n; }
  function fallback(){ return el("p","soa-fb","(carregando da base canônica…)"); }

  function ensureStyle(){
    if(document.getElementById("soa-sync-style")) return;
    var css=".soa-comp{font-family:Arial,Helvetica,sans-serif}"+
      ".soa-topic{font:700 18px Arial;color:#040F2F;margin:22px 0 4px;border-bottom:2px solid #E0E2E2;padding-bottom:4px}"+
      ".soa-topic small{display:block;font:400 12.5px Arial;color:#9aa0a6;margin-top:3px}"+
      ".soa-fb{color:#9aa0a6;font:italic 13px Arial}"+
      ".soa-ent{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:8px 0}"+
      ".soa-entc{border:1.5px solid #E0E2E2;border-radius:12px;padding:14px 16px}"+
      ".soa-entc .t{font:700 14px Arial;color:#040F2F}.soa-entc .fmt{font:700 11px Arial;color:#1C5AAD;letter-spacing:.03em;margin:4px 0 6px}.soa-entc .d{font:400 13px Arial;color:#4a4f55;line-height:1.5}"+
      ".soa-ben-tbl{width:100%;border-collapse:collapse;border:1.5px solid #E0E2E2;border-radius:12px;overflow:hidden;font-size:13px;font-family:Arial}"+
      ".soa-ben-tbl thead th{background:#040F2F;color:#fff;text-align:left;padding:11px 13px;font-size:12px}"+
      ".soa-ben-tbl td{padding:11px 13px;border-top:1px solid #E0E2E2;vertical-align:top;line-height:1.5;color:#0d1424}"+
      ".soa-ben-tbl tr:nth-child(even) td{background:#f4f5f6}.soa-ben-tit{font-weight:bold;color:#040F2F}.soa-ben-sem{color:#9a3412;font-weight:600}"+
      ".soa-pkg{border:1.5px solid #1C5AAD;border-radius:14px;padding:16px 18px;background:#e7eefb;margin:8px 0}"+
      ".soa-pkg h4{margin:0 0 6px;color:#040F2F;font:700 16px Arial}.soa-pkg .tese{color:#4a4f55;font-size:13.5px;margin:0;line-height:1.55}.soa-pkg .vet{font:700 11px Arial;color:#1C5AAD;margin-top:8px}"+
      "@media(max-width:640px){.soa-ent{grid-template-columns:1fr}}";
    var s=el("style"); s.id="soa-sync-style"; s.textContent=css; document.head.appendChild(s);
  }

  function tabelaBeneficios(lista){
    var t=el("table","soa-ben-tbl"), th=el("thead"), htr=el("tr");
    ["Benefício","Base legal","Mecanismo","Vigência","Sem SOA"].forEach(function(h){ cell(htr,"th",null,h); });
    th.appendChild(htr); t.appendChild(th);
    var tb=el("tbody");
    lista.forEach(function(b){ var tr=el("tr");
      cell(tr,"td","soa-ben-tit",b.titulo); cell(tr,"td",null,b.base_legal); cell(tr,"td",null,b.mecanismo);
      cell(tr,"td",null,b.vigencia); cell(tr,"td","soa-ben-sem",b.sem_soa); tb.appendChild(tr); });
    t.appendChild(tb); return t;
  }
  function cardsEntregaveis(lista){
    var g=el("div","soa-ent");
    lista.forEach(function(e){ var c=el("div","soa-entc");
      c.appendChild(el("div","t",e.titulo)); c.appendChild(el("div","fmt",e.formato||"")); c.appendChild(el("div","d",e.descricao||""));
      g.appendChild(c); });
    return g;
  }
  function pacoteBox(p, beneficios){
    var box=el("div","soa-pkg"); box.appendChild(el("h4",null,p.titulo)); box.appendChild(el("p","tese",p.tese));
    if(Array.isArray(p.vetores)) box.appendChild(el("div","vet","Compõe: "+p.vetores.join(" + ")));
    return box;
  }
  function topic(titulo, sub){ var h=el("div","soa-topic",titulo); if(sub) h.appendChild(el("small",null,sub)); return h; }

  function filtrar(beneficios, f){
    return beneficios.filter(function(b){
      if(b.status!==STATUS_OK) return false;
      if(f.vetor && !(Array.isArray(b.vetores)&&b.vetores.indexOf(f.vetor)!==-1)) return false;
      if(f.ator && !(Array.isArray(b.ator)&&b.ator.indexOf(f.ator)!==-1)) return false;
      if(f.canal && b.canal!==f.canal) return false;
      return true;
    });
  }
  function adjacentes(vetor, beneficios, pacotes){
    var pkgs=pacotes.filter(function(p){ return p.status===STATUS_OK && Array.isArray(p.vetores) && p.vetores.indexOf(vetor)!==-1; });
    var adjVet={}; pkgs.forEach(function(p){ p.vetores.forEach(function(v){ if(v!==vetor) adjVet[v]=true; }); });
    var seen={}, out=[];
    beneficios.forEach(function(b){
      if(b.status!==STATUS_OK||!Array.isArray(b.vetores)) return;
      var isX=b.vetores.indexOf(vetor)!==-1;
      var isAdj=b.vetores.some(function(v){ return adjVet[v]; });
      if(isAdj && !isX && !seen[b.id]){ seen[b.id]=true; out.push(b); }
    });
    return { pkgs:pkgs, beneficios:out };
  }

  function renderComposicao(host, vetor, all){
    ensureStyle(); host.className=(host.className+" soa-comp").trim(); host.innerHTML="";
    var ent=all.entregaveis.filter(function(e){ return e.vetor===vetor; });
    var gan=filtrar(all.beneficios,{vetor:vetor});
    var adj=adjacentes(vetor, all.beneficios, all.pacotes);

    host.appendChild(topic("1 · O que entregamos","O selo probatório SOA para este vetor — Evidence Pack / HEC / sHEC"));
    host.appendChild(ent.length ? cardsEntregaveis(ent) : fallback());

    host.appendChild(topic("2 · O que o cliente ganha","Benefícios com base legal — só o que é direito verificado"));
    host.appendChild(gan.length ? tabelaBeneficios(gan) : fallback());

    host.appendChild(topic("3 · O que você pode acessar","Adjacências que a composição do protocolo SOA destrava"));
    if(adj.pkgs.length || adj.beneficios.length){
      adj.pkgs.forEach(function(p){ host.appendChild(pacoteBox(p, all.beneficios)); });
      if(adj.beneficios.length) host.appendChild(tabelaBeneficios(adj.beneficios));
    } else { host.appendChild(fallback()); }
    host.setAttribute("data-fato-status","sincronizado");
  }

  function renderOverview(host, all){
    ensureStyle(); host.className=(host.className+" soa-comp").trim(); host.innerHTML="";
    var ent=all.entregaveis.slice();
    var gan=all.beneficios.filter(function(b){ return b.status===STATUS_OK; });
    var pkgs=all.pacotes.filter(function(p){ return p.status===STATUS_OK; });

    host.appendChild(topic("1 · O que entregamos","O selo probatório SOA por vetor — Evidence Pack / HEC / sHEC"));
    host.appendChild(ent.length ? cardsEntregaveis(ent) : fallback());

    host.appendChild(topic("2 · O que o cliente ganha","Direitos com base legal, lidos ao vivo — só o que é verificado"));
    host.appendChild(gan.length ? tabelaBeneficios(gan) : fallback());

    host.appendChild(topic("3 · O que você pode acessar","Composições do protocolo SOA — vetores que se somam num só selo"));
    if(pkgs.length){ pkgs.forEach(function(p){ host.appendChild(pacoteBox(p, all.beneficios)); }); }
    else { host.appendChild(fallback()); }
    host.setAttribute("data-fato-status","sincronizado");
  }

  function aplicar(ns){
    ensureStyle();
    var all={ beneficios:collectArray(ns,"beneficios"), pacotes:collectArray(ns,"pacotes"), entregaveis:collectArray(ns,"entregaveis") };

    document.querySelectorAll("[data-protocolo-overview]").forEach(function(h){ renderOverview(h, all); });

    document.querySelectorAll("[data-fato]").forEach(function(n){
      var v=getPath(ns, n.getAttribute("data-fato"));
      if(v===undefined||v===null||v==="") n.setAttribute("data-fato-status","fallback");
      else { n.textContent=String(v); n.setAttribute("data-fato-status","sincronizado"); }
    });

    document.querySelectorAll("[data-composicao-vetor]").forEach(function(h){ renderComposicao(h, h.getAttribute("data-composicao-vetor"), all); });

    document.querySelectorAll("[data-entregaveis-vetor]").forEach(function(h){
      var v=h.getAttribute("data-entregaveis-vetor"); var l=all.entregaveis.filter(function(e){ return e.vetor===v; });
      if(l.length){ h.innerHTML=""; h.appendChild(cardsEntregaveis(l)); h.setAttribute("data-fato-status","sincronizado"); } else h.setAttribute("data-fato-status","fallback");
    });

    document.querySelectorAll("[data-beneficios-vetor],[data-beneficios-ator],[data-beneficios-canal]").forEach(function(h){
      var l=filtrar(all.beneficios,{ vetor:h.getAttribute("data-beneficios-vetor")||null, ator:h.getAttribute("data-beneficios-ator")||null, canal:h.getAttribute("data-beneficios-canal")||null });
      if(l.length){ h.innerHTML=""; h.appendChild(tabelaBeneficios(l)); h.setAttribute("data-fato-status","sincronizado"); } else h.setAttribute("data-fato-status","fallback");
    });

    document.querySelectorAll("[data-pacote]").forEach(function(h){
      var p=all.pacotes.filter(function(x){ return x.id===h.getAttribute("data-pacote") && x.status===STATUS_OK; })[0];
      if(!p){ h.setAttribute("data-fato-status","fallback"); return; }
      h.innerHTML=""; var box=pacoteBox(p, all.beneficios);
      var ids=Array.isArray(p.beneficios)?p.beneficios:[];
      var lista=ids.map(function(id){ return all.beneficios.filter(function(b){ return b.id===id && b.status===STATUS_OK; })[0]; }).filter(Boolean);
      h.appendChild(box); if(lista.length) h.appendChild(tabelaBeneficios(lista));
      h.setAttribute("data-fato-status","sincronizado");
    });

    var c=firstCarimbo(ns)||{};
    document.querySelectorAll("[data-carimbo]").forEach(function(n){
      var q=c.atualizado_em?new Date(c.atualizado_em):null;
      n.textContent=q ? ("Dados verificados e selados em "+q.toLocaleString("pt-BR")+(c.hash?" · "+String(c.hash).slice(0,20)+"…":"")) : "Dados do monitor regulatório SOA/SOS";
    });
    document.documentElement.setAttribute("data-soa-sync","ok");
  }

  function carregar(){
    var urls=fontes(); if(!urls.length){ console.warn("[soa-sync] sem data-fontes."); return; }
    Promise.all(urls.map(function(u){
      return fetch(u,{cache:"no-store"}).then(function(r){ if(!r.ok) throw new Error(u+" "+r.status); return r.json(); })
        .then(function(j){ return {ns:nsFromUrl(u), data:j}; })
        .catch(function(e){ console.warn("[soa-sync] falha em",u,e); return {ns:nsFromUrl(u), data:{}}; });
    })).then(function(pares){ var ns={}; pares.forEach(function(p){ ns[p.ns]=p.data; }); aplicar(ns); });
  }
  if(document.readyState==="loading") document.addEventListener("DOMContentLoaded", carregar); else carregar();
})();
