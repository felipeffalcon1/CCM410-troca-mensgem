import zmq
import json
import time
import os
import threading
import socket
from datetime import datetime, timezone

DATA_DIR = "/app/data"
DB_FILE = f"{DATA_DIR}/mensagens.json"

# Na Parte 4, usamos o hostname (container ID) para que cada réplica do servidor 
# seja única e eles consigam se achar pela rede interna do Docker.
NOME_SERVIDOR = socket.gethostname()

relogio_logico = 0
relogio_offset = 0.0 
meu_rank = 0
coordenador_atual = None

def get_tempo_fisico_iso():
    timestamp_sincronizado = time.time() + relogio_offset
    return datetime.fromtimestamp(timestamp_sincronizado, tz=timezone.utc).isoformat()

def salvar_mensagem(canal, mensagem, timestamp, relogio):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DB_FILE, "a") as f:
        log = {"canal": canal, "mensagem": mensagem, "timestamp": timestamp, "relogio_logico": relogio}
        f.write(json.dumps(log) + "\n")

def escutar_coordenador(context):
    """Thread que escuta mensagens no tópico 'servers' para saber quem ganhou a eleição"""
    global coordenador_atual
    sub = context.socket(zmq.SUB)
    sub.connect("tcp://proxy:5558")
    sub.setsockopt_string(zmq.SUBSCRIBE, "servers")
    while True:
        try:
            msg = sub.recv_string()
            topico, nome_coord = msg.split(" ", 1)
            if topico == "servers":
                coordenador_atual = nome_coord
                print(f"\n[*] AVISO: Novo coordenador eleito -> {coordenador_atual}")
        except:
            pass

def iniciar_eleicao(context, pub_socket):
    """Algoritmo de Eleição (Bully)"""
    global coordenador_atual
    print(f"\n[ELEIÇÃO] {NOME_SERVIDOR} iniciando processo de eleição...")
    
    # 1. Pega os ranks na Referência
    ref_socket = context.socket(zmq.REQ)
    ref_socket.connect("tcp://referencia:5556")
    ref_socket.send_json({"comando": "list"})
    lista = ref_socket.recv_json().get("servidores", [])
    ref_socket.close()

    candidatos = [s for s in lista if s["rank"] > meu_rank]
    alguem_respondeu = False

    # 2. Pergunta aos de Rank maior se estão vivos
    for s in candidatos:
        req = context.socket(zmq.REQ)
        req.connect(f"tcp://{s['nome']}:5555")
        req.setsockopt(zmq.RCVTIMEO, 1500) # 1.5s timeout
        try:
            req.send_json({"comando": "eleicao"})
            resp = req.recv_json()
            if resp.get("status") == "OK":
                alguem_respondeu = True
        except:
            pass
        finally:
            req.close()

    if not alguem_respondeu:
        # Ninguém com rank maior respondeu. Eu sou o líder!
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

    threading.Thread(target=escutar_coordenador, args=(context,), daemon=True).start()

    # Força a eleição ao ligar para decidir quem é o Coordenador
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

        # --- Requisições entre Servidores ---
        if comando == "relogio":
            resposta["hora_correta"] = time.time() + relogio_offset
            rep_socket.send_json(resposta)
            continue
            
        elif comando == "eleicao":
            rep_socket.send_json(resposta)
            print("[!] Fui intimado para eleição. Reivindicando liderança...")
            iniciar_eleicao(context, pub_socket)
            continue

        # --- Requisições dos Clientes (Bots) ---
        contador_heartbeat += 1
        contador_sync += 1

        if contador_heartbeat >= 10:
            ref_socket.send_json({"comando": "heartbeat", "nome": NOME_SERVIDOR})
            ref_socket.recv_json()
            contador_heartbeat = 0

        # Sincronização de Relógio (a cada 15 msgs)
        if contador_sync >= 15:
            if coordenador_atual and coordenador_atual != NOME_SERVIDOR:
                req_sync = context.socket(zmq.REQ)
                req_sync.connect(f"tcp://{coordenador_atual}:5555")
                req_sync.setsockopt(zmq.RCVTIMEO, 2000)
                try:
                    req_sync.send_json({"comando": "relogio"})
                    resp_sync = req_sync.recv_json()
                    hora_correta = resp_sync.get("hora_correta")
                    if hora_correta:
                        relogio_offset = hora_correta - time.time()
                        print(f"[SYNC] Relógio ajustado. Novo offset: {relogio_offset:.4f}s")
                except:
                    print(f"[!] Coordenador {coordenador_atual} sumiu! Iniciando eleição...")
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
