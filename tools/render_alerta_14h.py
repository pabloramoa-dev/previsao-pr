"""Plantão Paraná: usa estúdio HyperFrames Bia com pauta de alerta verificada."""
import json, os, subprocess, sys
from pathlib import Path
from tools.alerta_14h import validar
from tools.alerta_14h_roteiro import batidas, texto_para_arquivo

def main():
    rel=validar(json.loads(Path("output/alertas/consulta.json").read_text()))
    out=Path("output/alertas/ALERTA.mp4")
    out.parent.mkdir(parents=True,exist_ok=True)
    # Os seis pontos têm previsão horária REAL do ICON, preservando o
    # quadro obrigatório do canal sem simular bairros ou temperaturas.
    ancoras=[
      ("curitiba","Curitiba","z_curitiba"),
      ("paranagua","Paranaguá","z_litoral"),
      ("ponta_grossa","Ponta Grossa","z_campos_gerais"),
      ("londrina","Londrina","z_norte"),
      ("maringa","Maringá","z_noroeste"),
      ("cascavel","Cascavel","z_oeste"),
    ]
    locais=[]
    for ident,nome,zona in ancoras:
        t=rel["temperaturas_reais"][nome]
        locais.append({"id":ident,"name":nome,"zone":zona,
           "min_c":t["min"],"max_c":t["max"],"rain_mm":t["chuva_mm"]})
    bloco={"date":rel["data"],"locations":locais}
    snap={"forecast":{"today":bloco,"tomorrow":bloco},"alerta_14h":rel}
    Path("output/alertas/snapshot.json").write_text(json.dumps(snap,ensure_ascii=False))
    original=Path("hyperframes/gerar_hf.py").read_text()
    antigo="batidas = prepare(snapshot, formato, topic=topico)['beats']"
    novo="from tools.alerta_14h_roteiro import batidas as gerar_alerta; batidas = gerar_alerta(snapshot['alerta_14h'])"
    if antigo not in original:
        raise RuntimeError("A entrada do estúdio Paraná mudou; revisar antes de publicar")
    texto=original.replace(antigo,novo)
    arquivo=Path("hyperframes/gerar_alerta_14h.py")
    arquivo.write_text(texto,encoding="utf-8")
    legenda=texto_para_arquivo(rel,"output/alertas/LEGENDA.txt")
    env=dict(os.environ,PREVISAO_HORA_ALVO="14")
    subprocess.run([sys.executable,str(arquivo),"--snapshot","output/alertas/snapshot.json",
                    "--personagem","bia","--format","antes_de_sair",
                    "--out",str(out)],check=True,env=env)
    if not out.exists() or out.stat().st_size<100000:
        raise RuntimeError("MP4 de alerta do Paraná incompleto")
    print("ALERTA PR:",out,out.stat().st_size)

if __name__=="__main__": main()
