import zmq
import json
import time
import os
import threading
import socket
from datetime import datetime, timezone

DATA_DIR = "/app/data"
DB_FILE = f"{DATA_DIR}/mensagens.json"
NOME_SERVIDOR = socket.gethostname()

relogio_logico = 0
relogio_offset = 0.0 
meu_rank = 0
coordenador_atual = None

# Lock para evitar corromper o arquivo quando várias threads tentarem salvar ao mesmo tempo
db_lock = threading.Lock()

def get_tempo_fisico_iso():
    timestamp_sincronizado = time.time() + relogio_offset
    return datetime.fromtimestamp(timestamp_sincronizado, tz=timezone.utc).isoformat()

def salvar_mensagem(canal, mensagem, timestamp, relogio):
    os.makedirs(DATA_DIR, exist_ok=True)
    with db_lock:
        with open(DB_FILE, "a") as f:
            log = {"canal": canal, "mensagem": mensagem, "timestamp": timestamp, "relogio_logico": relogio}
            f.write(json.dumps(log) + "\n")

def escutar_eventos_internos(context):
    """Thread que escuta eleição ('servers') e replicação ('REPLICA')"""
    global coordenador_atual
    sub = context.socket(zmq.SUB)
    sub.connect("tcp://proxy:5558")
    
    # Assina os tópicos internos
    sub.setsockopt_string(zmq.SUBSCRIBE, "servers")
    sub.setsockopt_string(zmq.SUBSCRIBE, "REPLICA")
    
    while True:
        try:
            msg = sub.recv_string()
            partes = msg.split(" ", 2)
            topico = partes[0]
            
            if topico == "servers":
                coordenador_atual = partes[1]
                print(f"\n[*] AVISO: Novo coordenador eleito -> {coordenador_atual}")
                
            elif topico == "REPLICA":
                remetente = partes[1]
                payload_str = partes[2]
                
                # Só salva se a mensagem não foi enviada por mim mesmo
                if remetente != NOME_SERVIDOR:
                    payload = json.loads(payload_str)
                    salvar_mensagem(
                        payload.get("canal"),
                        payload.get("mensagem"),
                        payload.get("timestamp_envio"),
                        payload.get("relogio_logico")
                    )
                    print(f"[REPLICA] Mensagem sincronizada via {remetente}.")
        except Exception:
            pass

def iniciar_eleicao(context, pub_socket):
    global coordenador_atual
    print(f"\n[ELEIÇÃO] {NOME_SERVIDOR} iniciando processo de eleição...")
    
    ref_socket = context.socket(zmq.REQ)
    ref_socket.connect("tcp://referencia:5556")
    ref_socket.send_json({"comando": "list"})
    lista = ref_socket.recv_json().get("servidores", [])
    ref_socket.close()

    candidatos = [s for s in lista if s["rank"] > meu_rank]
    alguem_respondeu = False

    for s in candidatos:
        req = context.socket(zmq.REQ)
        req.connect(f"tcp://{s['nome']}:5555")
        req.setsockopt(zmq.RCVTIMEO, 1500)
        try:
            req.send_json({"comando": "eleicao"})
            if req.recv_json().get("status") == "OK":
                alguem_respondeu = True
        except:
            pass
        finally:
            req.close()

    if not alguem_respondeu:
        coordenador_atual = NOME_SERVIDOR
        print(f"[ELEIÇÃO] Venci! Eu sou o novo coordenador.")
        pub_socket.send_string(f"servers {NOME_SERVIDOR}")
    else:
        print("[ELEIÇÃO] Um servidor com rank maior assumiu. Aguardando anúncio...")

def main():
    global relogio_logico, relogio_offset, meu_rank, coordenador_atual
    context = zmq.Context()

    rep_socket = context.socket(zmq.REP)
    rep_socket.bind("tcp://*:5555")

    pub_socket = context.socket(zmq.PUB)
    pub_socket.connect("tcp://proxy:5557")

    ref_socket = context.socket(zmq.REQ)
    ref_socket.connect("tcp://referencia:5556")
    time.sleep(1)

    ref_socket.send_json({"comando": "registrar", "nome": NOME_SERVIDOR})
    meu_rank = ref_socket.recv_json().get("rank")
    print(f"[SERVIDOR {NOME_SERVIDOR}] Registrado | Rank: {meu_rank}")

    threading.Thread(target=escutar_eventos_internos, args=(context,), daemon=True).start()

    iniciar_eleicao(context, pub_socket)

    canais = ["geral", "noticias", "esportes"]
    contador_heartbeat = 0
    contador_sync = 0

    while True:
        req = rep_socket.recv_json()
        comando = req.get("comando")
        
        msg_relogio = req.get("relogio_logico", 0)
        relogio_logico = max(relogio_logico, msg_relogio)
        relogio_logico += 1
        
        resposta = {"status": "OK", "relogio_logico": relogio_logico}

        if comando == "relogio":
            resposta["hora_correta"] = time.time() + relogio_offset
            rep_socket.send_json(resposta)
            continue
            
        elif comando == "eleicao":
            rep_socket.send_json(resposta)
            iniciar_eleicao(context, pub_socket)
            continue

        contador_heartbeat += 1
        contador_sync += 1

        if contador_heartbeat >= 10:
            ref_socket.send_json({"comando": "heartbeat", "nome": NOME_SERVIDOR})
            ref_socket.recv_json()
            contador_heartbeat = 0

        if contador_sync >= 15:
            if coordenador_atual and coordenador_atual != NOME_SERVIDOR:
                req_sync = context.socket(zmq.REQ)
                req_sync.connect(f"tcp://{coordenador_atual}:5555")
                req_sync.setsockopt(zmq.RCVTIMEO, 2000)
                try:
                    req_sync.send_json({"comando": "relogio"})
                    hora_correta = req_sync.recv_json().get("hora_correta")
                    if hora_correta:
                        relogio_offset = hora_correta - time.time()
                except:
                    iniciar_eleicao(context, pub_socket)
                finally:
                    req_sync.close()
            elif not coordenador_atual:
                iniciar_eleicao(context, pub_socket)
            
            contador_sync = 0

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
                
                # Adicionado 'canal' no payload para o servidor que replicar saber onde salvar
                payload = json.dumps({
                    "canal": canal,
                    "mensagem": mensagem, 
                    "timestamp_envio": timestamp_sinc,
                    "relogio_logico": relogio_logico
                })
                
                # Salva localmente
                salvar_mensagem(canal, mensagem, timestamp_sinc, relogio_logico)
                
                # Envia para os clientes (Bots) assinantes
                pub_socket.send_string(f"{canal} {payload}")
                
                # PARTE 5: Publica a mensagem para replicar nos outros servidores
                pub_socket.send_string(f"REPLICA {NOME_SERVIDOR} {payload}")
                
                rep_socket.send_json(resposta)
            else:
                resposta["status"] = "erro"
                rep_socket.send_json(resposta)

if __name__ == "__main__":
    main()
