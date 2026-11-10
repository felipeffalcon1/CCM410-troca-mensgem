import zmq
import json
import time
import os

# Caminho para persistência em disco mapeado no Docker
DATA_DIR = "/app/data"
DB_FILE = f"{DATA_DIR}/mensagens.json"

def salvar_mensagem(canal, mensagem, timestamp):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DB_FILE, "a") as f:
        log = {"canal": canal, "mensagem": mensagem, "timestamp": timestamp}
        f.write(json.dumps(log) + "\n")

def main():
    context = zmq.Context()

    # Socket REQ/REP para responder comandos
    rep_socket = context.socket(zmq.REP)
    rep_socket.bind("tcp://*:5555")

    # Socket PUB conectando ao Proxy para publicar nos canais
    pub_socket = context.socket(zmq.PUB)
    pub_socket.connect("tcp://proxy:5557")
    time.sleep(1) # Aguarda a conexão firmar

    canais = ["geral", "noticias", "esportes"]

    print("[SERVIDOR] Iniciado (REP: 5555 | PUB -> proxy:5557)...")

    while True:
        req = rep_socket.recv_json()
        comando = req.get("comando")

        if comando == "listar_canais":
            rep_socket.send_json({"status": "OK", "canais": canais})
        
        elif comando == "criar_canal":
            novo_canal = req.get("canal")
            if novo_canal and novo_canal not in canais:
                canais.append(novo_canal)
                rep_socket.send_json({"status": "OK", "mensagem": f"Canal {novo_canal} criado"})
            else:
                rep_socket.send_json({"status": "erro", "mensagem": "Canal invalido ou ja existe"})
        
        elif comando == "publicar":
            canal = req.get("canal")
            mensagem = req.get("mensagem")
            timestamp_envio = req.get("timestamp_envio")

            if canal in canais:
                # Envia no formato "topico payload" para o ZeroMQ filtrar
                payload = json.dumps({"mensagem": mensagem, "timestamp_envio": timestamp_envio})
                pub_socket.send_string(f"{canal} {payload}")
                
                salvar_mensagem(canal, mensagem, timestamp_envio)
                rep_socket.send_json({"status": "OK"})
            else:
                rep_socket.send_json({"status": "erro"})

if __name__ == "__main__":
    main()
