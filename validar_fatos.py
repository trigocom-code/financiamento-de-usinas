#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gatekeeper dos Fatos_*_Folder_SOA.json (SOA/SOS). CI barra drift. exit 1 se houver."""
import json, sys, os, glob, re
TERMOS_PROIBIDOS_MARCA = ["líder","lider","patentead","anti-fraude","antifraude","padrão mundial","padrao mundial"]
FRASES_ERRO = ["12 dispositivos","dispositivos vetados","22 dispositivos vetados","meta até 2035"]
ANDAIME = [r"\[CORRE[ÇC][ÃA]O", r"\[A VERIFICAR", r"\[TODO", r"\[FIXME", r"\[NOTA:"]
CAMPOS_RENDERIZADOS = ("valor","tema","norma")
DATA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
def erros(path):
    e=[]; n=os.path.basename(path)
    try:
        with open(path,encoding="utf-8-sig") as f: d=json.load(f)
    except Exception as ex: return [f"{n}: JSON inválido — {ex}"]
    m=d.get("_meta",{})
    if "regra_fonte_associacao" not in m: e.append(f"{n}: falta _meta.regra_fonte_associacao")
    if not DATA_RE.match(str(m.get("verificado_em",""))): e.append(f"{n}: verificado_em ausente/fmt")
    def walk(o,c=""):
        if isinstance(o,dict):
            for k,v in o.items():
                if "C2_CEO" in k: e.append(f"{n}: chave andaime '{k}'")
                walk(v,c+"/"+k)
        elif isinstance(o,list):
            for i,v in enumerate(o): walk(v,c+f"[{i}]")
        elif isinstance(o,str):
            low=o.lower(); campo=c.rsplit("/",1)[-1].split("[")[0]
            for fr in FRASES_ERRO:
                if fr in low: e.append(f"{n}{c}: frase de erro '{fr}'")
            for t in TERMOS_PROIBIDOS_MARCA:
                if t in low: e.append(f"{n}{c}: termo de marca '{t}'")
            if campo in CAMPOS_RENDERIZADOS:
                for p in ANDAIME:
                    if re.search(p,o,re.I): e.append(f"{n}{c}: andaime em campo renderizado ({p})")
    walk(d)
    blob=json.dumps(d,ensure_ascii=False)
    for mm in re.finditer(r"\b(\d{1,2})\s+vetos\b",blob):
        if mm.group(1)!="16": e.append(f"{n}: vetos divergente '{mm.group(0)}'")
    return e
def main():
    base=sys.argv[1] if len(sys.argv)>1 else "."
    arqs=[p for p in sorted(glob.glob(os.path.join(base,"Fatos_*_Folder_SOA.json")))
          if "legacy" not in p.lower() and "deprecated" not in p.lower()]
    if not arqs: print(f"[gate] nenhum Fatos_*_Folder_SOA.json em {base}"); sys.exit(2)
    todos=[]
    for a in arqs: todos+=erros(a)
    print(f"[gate] validados {len(arqs)} arquivos.")
    if todos:
        print(f"[gate] ❌ {len(todos)} problema(s) — push BARRADO:")
        for x in todos: print("   -",x)
        sys.exit(1)
    print("[gate] ✅ 0 problemas."); sys.exit(0)
if __name__=="__main__": main()
