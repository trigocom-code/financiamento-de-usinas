#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gatekeeper SOA/SOS v2.0 (01/07/2026) — 3 estagios + anti-regressao."""
import json, sys, os, glob, re, html, subprocess

TERMOS_PROIBIDOS_MARCA = ["líder","lider","patentead","anti-fraude","antifraude",
                          "padrão mundial","padrao mundial","ninguém mais tem","ninguem mais tem",
                          "mais profundo do brasil","maior banco d","incontestável","incontestavel"]
FRASES_ERRO = ["12 dispositivos","dispositivos vetados","22 dispositivos vetados","meta até 2035",
               "portaria normativa mme 878/2025","5,7 gw"]
EMAILS_PROIBIDOS = ["solaroneaccount.com.br","contato@solaroneaccount"]
ANDAIME = [r"\[CORRE[ÇC][ÃA]O", r"\[A VERIFICAR", r"\(a verificar", r"\[TODO", r"\[FIXME", r"\[NOTA:"]
CAMPOS_RENDERIZADOS = ("valor","tema","norma")
# --- schema unificado de benefícios (v1) ---
# Taxonomia ÚNICA (Opção B, decidida 04/07/2026): 7 vetores de PROVA + 3 frentes NÃO-prova.
# V-codes V1..V8 APOSENTADOS — ver _CANON_Mapa_Vetores_Vcode_v1.md (ponte de migração).
VETORES_CANON = {  # Opção B (04/07/2026): 7 de PROVA + 7 NÃO-prova = 14. Nomes canônicos da régua §5.
                 "BESS auditável","CBAM exportável","Compliance SBCE","Contencioso regulatório",
                 "Data centers 24/7 CFE","H2V certificado","MMGD não observável",
                 # 6 propostas de expansão da régua §5 (adotadas sob B) + Mercado & PSM (Monitor v1.2, gap CP17/2026):
                 "Ancilares auditáveis","Seguros & Prova de Risco","Cidades/IPTU Verde","GEC biometano",
                 "M2M & IoT","PNAST & acesso","Mercado & PSM"}
# V-codes legados aceitos SÓ como metadado v_origem (nunca como vetor de destino renderizado):
VCODES_LEGADO = {"V1","V2","V3","V4","V5","V6","V7","V8"}
VCODE_PARA_CANON = {"V1":"PNAST & acesso","V2":"MMGD não observável","V3":"BESS auditável",
                    "V4":"Contencioso regulatório","V5":"Data centers 24/7 CFE",
                    # V6 = gamificação/dNFT (vetor TÉCNICO interno, sem destino comercial renderizado) — não mapeia.
                    # "Mercado & PSM" é vetor NOVO sem V-code (formalizado pós-CP17/2026), não é ex-V6.
                    "V7":"Ancilares auditáveis","V8":"Seguros & Prova de Risco"}
ATORES_CANON = {"pf","pj","industria","municipio","estado","uniao","comercial"}
CANAIS_CANON = {"conta","imposto","credito","captacao","mercado","carbono","relato"}
STATUS_CANON = {"verificado","pendente"}
CAMPOS_BENEF = ("id","ator","vetores","canal","titulo","base_legal","mecanismo","vigencia","sem_soa","status","fonte")
DATA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2})?$")
VETOS_RE = re.compile(r"\b(\d{1,2})\s+vetos\b")

NEGACOES = ("nunca","não é","nao e","não confundir","nao confundir","não '","nao '")
def _negado(low, i):
    ctx = low[max(0,i-30):i]
    return any(ng in ctx for ng in NEGACOES)

def _scan_texto(blob, rotulo, e):
    low = blob.lower()
    for fr in FRASES_ERRO:
        j = low.find(fr)
        while j >= 0:
            if not _negado(low, j): e.append("%s: frase de erro '%s'" % (rotulo, fr)); break
            j = low.find(fr, j+1)
    for t in TERMOS_PROIBIDOS_MARCA:
        j = low.find(t)
        while j >= 0:
            if not _negado(low, j): e.append("%s: termo de marca '%s'" % (rotulo, t)); break
            j = low.find(t, j+1)
    for em in EMAILS_PROIBIDOS:
        if em in low: e.append("%s: e-mail proibido '%s' (canonico: @solaroneaccount.com)" % (rotulo, em))
    for m in VETOS_RE.finditer(low):
        if m.group(1) != "16" and not _negado(low, m.start()):
            e.append("%s: vetos divergente '%s' (canonico: 16 vetos)" % (rotulo, m.group(0)))

def erros_fatos(path):
    e=[]; n=os.path.basename(path)
    try:
        with open(path,encoding="utf-8-sig") as f: d=json.load(f)
    except Exception as ex: return ["%s: JSON inválido — %s" % (n, ex)]
    m=d.get("_meta",{})
    if "regra_fonte_associacao" not in m: e.append("%s: falta _meta.regra_fonte_associacao" % n)
    if not DATA_RE.match(str(m.get("verificado_em",""))): e.append("%s: verificado_em ausente/fmt" % n)
    def walk(o,c=""):
        if isinstance(o,dict):
            for k,v in o.items():
                if "C2_CEO" in k: e.append("%s: chave andaime '%s'" % (n, k))
                walk(v,c+"/"+k)
        elif isinstance(o,list):
            for i,v in enumerate(o): walk(v,c+"[%d]"%i)
        elif isinstance(o,str):
            campo=c.rsplit("/",1)[-1].split("[")[0]
            if campo in CAMPOS_RENDERIZADOS:
                for p in ANDAIME:
                    if re.search(p,o,re.I):
                        e.append("%s%s: andaime em campo renderizado (%s) — mover p/ 'pendencia_verificacao'" % (n,c,p))
    walk(d)
    _scan_texto(json.dumps(d,ensure_ascii=False), n, e)
    return e

def erros_cruzados(base):
    e=[]
    deps_p=os.path.join(base,"Folder_Deps_SOA.json")
    if not os.path.exists(deps_p): return e
    try:
        with open(deps_p,encoding="utf-8-sig") as f: deps=json.load(f)
    except Exception as ex: return ["Folder_Deps_SOA.json: JSON inválido — %s" % ex]
    _scan_texto(json.dumps(deps,ensure_ascii=False),"Folder_Deps_SOA.json",e)
    st_p=os.path.join(base,"_folder_triggers_state.json")
    if os.path.exists(st_p):
        try:
            with open(st_p,encoding="utf-8-sig") as f:
                _scan_texto(f.read(),"_folder_triggers_state.json",e)
        except Exception: pass
    cache={}
    def ids_de(nb):
        if nb in cache: return cache[nb]
        p=os.path.join(base,nb+"_Folder_SOA.json"); s=set()
        if os.path.exists(p):
            try:
                with open(p,encoding="utf-8-sig") as f: d=json.load(f)
                for lista in ("fatos","_pendentes_verificacao"):
                    for fa in d.get(lista) or []:
                        for k in ("fato_id","tema"):
                            if fa.get(k): s.add(str(fa[k]))
            except Exception: pass
        cache[nb]=s; return s
    for fd in deps.get("folders",[]):
        for dep in fd.get("depende_de") or []:
            nb, ref = dep.get("json"), dep.get("ref")
            if not nb or not ref: continue
            if ref not in ids_de(nb):
                e.append("Folder_Deps: '%s' depende de %s::%s — fato NAO encontrado (orfao)" % (fd.get('folder'), nb, ref))
    return e

def erros_html(base):
    e=[]
    for p in sorted(glob.glob(os.path.join(base,"*.html"))):
        n=os.path.basename(p)
        try:
            with open(p,encoding="utf-8",errors="replace") as f: txt=html.unescape(f.read())
        except Exception as ex: e.append("%s: leitura falhou — %s" % (n, ex)); continue
        low=re.sub(r"<script[^>]*src=[^>]*>","",txt.lower())
        for t in ["ninguém mais tem","ninguem mais tem","mais profundo do brasil","maior banco d",
                  "incontestável","incontestavel","padrão mundial","padrao mundial","anti-fraude","antifraude"]:
            j=low.find(t)
            while j>=0:
                if not _negado(low,j): e.append("%s: termo proibido em material '%s'" % (n, t)); break
                j=low.find(t,j+1)
        for em in EMAILS_PROIBIDOS:
            if em in low: e.append("%s: e-mail proibido '%s'" % (n, em))
        for m in VETOS_RE.finditer(low):
            if m.group(1)!="16" and not _negado(low,m.start()): e.append("%s: vetos divergente '%s'" % (n, m.group(0)))
    return e

def erros_regressao(base):
    e=[]
    try:
        msg=subprocess.check_output(["git","log","-1","--pretty=%B"],cwd=base,
                                    stderr=subprocess.DEVNULL).decode("utf-8","replace")
        if "[regressao-aprovada]" in msg.lower(): return []
        mudados=subprocess.check_output(["git","diff","--name-only","HEAD^","HEAD"],cwd=base,
                                        stderr=subprocess.DEVNULL).decode().split()
    except Exception:
        return []
    def parse(txt):
        try:
            d=json.loads(txt)
            return str(d.get("_meta",{}).get("schema_version","")), len(d.get("fatos") or [])
        except Exception: return None,None
    for f in mudados:
        if not re.match(r"Fatos_.*_Folder_SOA\.json$",os.path.basename(f)): continue
        try:
            antes=subprocess.check_output(["git","show","HEAD^:"+f],cwd=base,stderr=subprocess.DEVNULL).decode("utf-8","replace")
        except Exception: continue
        p=os.path.join(base,f)
        if not os.path.exists(p): e.append("%s: REMOVIDO sem [regressao-aprovada]" % f); continue
        if antes and antes[0]=="﻿": antes=antes[1:]
        sv_a,n_a=parse(antes); sv_d,n_d=parse(open(p,encoding="utf-8-sig").read())
        def num(s):
            try: return tuple(int(x) for x in str(s).split("."))
            except Exception: return (0,)
        if sv_a and sv_d and num(sv_d)<num(sv_a):
            e.append("%s: REGRESSAO schema_version %s -> %s (use [regressao-aprovada] se intencional)" % (f, sv_a, sv_d))
        if n_a is not None and n_d is not None and n_d<n_a:
            e.append("%s: REGRESSAO qtde de fatos %d -> %d (use [regressao-aprovada] se intencional)" % (f, n_a, n_d))
    return e

def erros_beneficios(path):
    """Valida o schema unificado de benefícios (arquivos com chave 'beneficios')."""
    e=[]; n=os.path.basename(path)
    try:
        with open(path,encoding="utf-8-sig") as f: d=json.load(f)
    except Exception as ex: return ["%s: JSON inválido — %s" % (n, ex)]
    if "beneficios" not in d: return []   # não é arquivo de benefícios; ignora
    ids=set()
    for i,b in enumerate(d.get("beneficios") or []):
        if not isinstance(b,dict): e.append("%s beneficios[%d]: não é objeto" % (n,i)); continue
        for c in CAMPOS_BENEF:
            if c not in b: e.append("%s beneficios[%d]: falta campo '%s'" % (n,i,c))
        bid=b.get("id")
        if bid in ids: e.append("%s beneficios[%d]: id duplicado '%s'" % (n,i,bid))
        ids.add(bid)
        if b.get("status") not in STATUS_CANON: e.append("%s beneficios[%d] (%s): status inválido '%s'" % (n,i,bid,b.get("status")))
        for v in (b.get("vetores") or []):
            if v not in VETORES_CANON: e.append("%s beneficios[%d] (%s): vetor fora do canônico '%s'" % (n,i,bid,v))
        for a in (b.get("ator") or []):
            if a not in ATORES_CANON: e.append("%s beneficios[%d] (%s): ator inválido '%s'" % (n,i,bid,a))
        if b.get("canal") and b.get("canal") not in CANAIS_CANON:
            e.append("%s beneficios[%d] (%s): canal inválido '%s'" % (n,i,bid,b.get("canal")))
    for i,p in enumerate(d.get("pacotes") or []):
        if p.get("status") not in STATUS_CANON: e.append("%s pacotes[%d] (%s): status inválido" % (n,i,p.get("id")))
        for ref in (p.get("beneficios") or []):
            if ref not in ids: e.append("%s pacotes[%d] (%s): ref de benefício inexistente '%s'" % (n,i,p.get("id"),ref))
        for v in (p.get("vetores") or []):
            if v not in VETORES_CANON: e.append("%s pacotes[%d] (%s): vetor fora do canônico '%s'" % (n,i,p.get("id"),v))
    for i,c in enumerate(d.get("cruzamento_regulatorio") or []):
        if not c.get("fato_id"): e.append("%s cruzamento_regulatorio[%d]: falta fato_id" % (n,i))
        for v in (c.get("vetores") or []):
            if v not in VETORES_CANON: e.append("%s cruzamento_regulatorio[%d] (%s): vetor fora do canônico '%s'" % (n,i,c.get("fato_id"),v))
    return e

def main():
    base=sys.argv[1] if len(sys.argv)>1 else "."
    arqs=[p for p in sorted(glob.glob(os.path.join(base,"Fatos_*_Folder_SOA.json")))
          if "legacy" not in p.lower() and "deprecated" not in p.lower()]
    if not arqs: print("[gate] nenhum Fatos_*_Folder_SOA.json em %s" % base); sys.exit(2)
    todos=[]
    for a in arqs: todos+=erros_fatos(a)
    n1=len(todos)
    for a in arqs: todos+=erros_beneficios(a)
    n4=len(todos)-n1
    todos+=erros_regressao(base);            n0=len(todos)-n1-n4
    todos+=erros_cruzados(base);             n2=len(todos)-n1-n4-n0
    todos+=erros_html(base);                 n3=len(todos)-n1-n4-n0-n2
    print("[gate v2] E1 fatos(%d arqs): %d | E4 beneficios: %d | E0 regressao: %d | E2 cruzado: %d | E3 html: %d" % (len(arqs),n1,n4,n0,n2,n3))
    if todos:
        print("[gate v2] ❌ %d problema(s) — push BARRADO:" % len(todos))
        for x in todos: print("   -",x)
        sys.exit(1)
    print("[gate v2] ✅ 0 problemas."); sys.exit(0)
if __name__=="__main__": main()

