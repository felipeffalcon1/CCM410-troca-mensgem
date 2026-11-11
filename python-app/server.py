import zmq
import json
import time
import os
from datetime import datetime, timezone

DATA_DIR = "/app/data"
DB_FILE = f"{DATA_DIR}/mensagens.json"
NOME_SERVIDOR = "servidor_principal"

relogio_logico = 0
relogio_offset = 0.0 # Diferença entre hora local e hora da referência

def get_tempo_fisico_iso():
    # Aplica a sincronização de relógio baseada no offset
    timestamp_sincronizado = time.time() + relogio_offset
    return datetime.fromtimestamp(timestamp_sincronizado, tz=timezone.utc).isoformat()

def salvar_mensagem(canal, mensagem, timestamp, relogio):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DB_FILE, "a") as f:
        log = {"canal": canal, "mensagem": mensagem, "timestamp": timestamp, "relogio_logico": relogio}
        f.write(json.dumps(log) + "\n")

def main():
    global relogio_logico, relogio_offset
    context = zmq.Context()

    rep_socket = context.socket(zmq.REP)
    rep_socket.bind("tcp://*:5555")

    pub_socket = context.socket(zmq.PUB)
    pub_socket.connect("tcp://proxy:5557")

    ref_socket = context.socket(zmq.REQ)
    ref_socket.connect("tcp://referencia:5556")
    time.sleep(1)

    # 1. Registrar na referência e pegar o Rank
    ref_socket.send_json({"comando": "registrar", "nome": NOME_SERVIDOR})
    meu_rank = ref_socket.recv_json().get("rank")
    print(f"[SERVIDOR] Registrado com Rank {meu_rank}")

    canais = ["geral", "noticias", "esportes"]
    mensagens_recebidas = 0

    while True:
        req = rep_socket.recv_json()
        
        # Atualiza Relógio Lógico: max(local, recebido)
        msg_relogio = req.get("relogio_logico", 0)
        relogio_logico = max(relogio_logico, msg_relogio)
        
        mensagens_recebidas += 1
        
        # Envia Heartbeat a cada 10 mensagens
        if mensagens_recebidas >= 10:
            ref_socket.send_json({"comando": "heartbeat", "nome": NOME_SERVIDOR})
            ref_resp = ref_socket.recv_json()
            hora_referencia = ref_resp.get("timestamp_referencia", time.time())
            
            # Atualiza relógio físico calculando o offset
            relogio_offset = hora_referencia - time.time()
            mensagens_recebidas = 0
            print(f"[SERVIDOR] Heartbeat enviado. Novo offset de relógio: {relogio_offset:.4f}s")

        comando = req.get("comando")
        relogio_logico += 1 # Incrementa antes de responder/publicar

        resposta = {"status": "OK", "relogio_logico": relogio_logico}

        if comando == "listar_canais":
            resposta["canais"] = canais
            rep_socket.send_json(resposta)
        
        elif comando == "criar_canal":
            novo_canal = req.get("canal")
            if novo_canal and novo_canal not in canais:
                canais.append(novo_canal)
                rep_socket.send_json(resposta)
            else:
                resposta["status"] = "erro"
                rep_socket.send_json(resposta)
        
        elif comando == "publicar":
            canal = req.get("canal")
            mensagem = req.get("mensagem")
            
            if canal in canais:
                timestamp_sinc = get_tempo_fisico_iso()
                payload = json.dumps({
                    "mensagem": mensagem, 
                    "timestamp_envio": timestamp_sinc,
                    "relogio_logico": relogio_logico
                })
                pub_socket.send_string(f"{canal} {payload}")
                salvar_mensagem(canal, mensagem, timestamp_sinc, relogio_logico)
                rep_socket.send_json(resposta)
            else:
                resposta["status"] = "erro"
                rep_socket.send_json(resposta)

if __name__ == "__main__":
    main()
