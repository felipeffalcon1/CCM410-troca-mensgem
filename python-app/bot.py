import zmq
import json
import time
import random
import string
import threading
from datetime import datetime, timezone

def gerar_texto():
    return ''.join(random.choices(string.ascii_letters, k=8))

# Thread separada para escutar mensagens sem travar o loop de envio
def escutar_mensagens(sub_socket):
    while True:
        try:
            msg = sub_socket.recv_string()
            canal, payload_str = msg.split(" ", 1)
            payload = json.loads(payload_str)
            
            timestamp_recebimento = datetime.now(timezone.utc).isoformat()
            
            print(f"\n[MENSAGEM RECEBIDA] Canal: {canal}")
            print(f" | Mensagem: {payload.get('mensagem')}")
            print(f" | Enviado em:  {payload.get('timestamp_envio')}")
            print(f" | Recebido em: {timestamp_recebimento}\n")
        except Exception:
            pass

def main():
    context = zmq.Context()

    req_socket = context.socket(zmq.REQ)
    req_socket.connect("tcp://server:5555")

    sub_socket = context.socket(zmq.SUB)
    sub_socket.connect("tcp://proxy:5558")

    # Inicia a escuta em segundo plano
    threading.Thread(target=escutar_mensagens, args=(sub_socket,), daemon=True).start()

    # Regra 1: Verificar/Criar canais (< 5)
    req_socket.send_json({"comando": "listar_canais"})
    canais = req_socket.recv_json().get("canais", [])
    
    if len(canais) < 5:
        novo = f"canal_{random.randint(100,999)}"
        req_socket.send_json({"comando": "criar_canal", "canal": novo})
        req_socket.recv_json()
        canais.append(novo)

    # Regra 2: Inscrever-se em canais (pelo menos 3)
    inscricoes = random.sample(canais, min(3, len(canais)))
    for c in inscricoes:
        sub_socket.setsockopt_string(zmq.SUBSCRIBE, c)
        print(f"[*] Inscrito no canal: {c}")

    time.sleep(1) # Aguarda proxy processar inscricoes

    # Regra 3: Loop infinito publicando 10 mensagens
    while True:
        canal_alvo = random.choice(canais)
        print(f"\n[!] Publicando 10 mensagens no canal '{canal_alvo}'...")
        
        for _ in range(10):
            req = {
                "comando": "publicar",
                "canal": canal_alvo,
                "mensagem": gerar_texto(),
                "timestamp_envio": datetime.now(timezone.utc).isoformat()
            }
            req_socket.send_json(req)
            req_socket.recv_json() # Descarta OK
            time.sleep(1)

if __name__ == "__main__":
    main()
