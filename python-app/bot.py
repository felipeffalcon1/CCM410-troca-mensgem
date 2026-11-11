import zmq
import json
import time
import random
import string
import threading
from datetime import datetime, timezone

relogio_logico = 0
relogio_lock = threading.Lock()

def atualiza_relogio_recebido(relogio_msg):
    global relogio_logico
    with relogio_lock:
        relogio_logico = max(relogio_logico, relogio_msg)

def incrementa_e_pega_relogio():
    global relogio_logico
    with relogio_lock:
        relogio_logico += 1
        return relogio_logico

def gerar_texto():
    return ''.join(random.choices(string.ascii_letters, k=8))

def escutar_mensagens(sub_socket):
    while True:
        try:
            msg = sub_socket.recv_string()
            canal, payload_str = msg.split(" ", 1)
            payload = json.loads(payload_str)
            
            # Atualiza relógio lógico ao receber PUB
            relogio_msg = payload.get('relogio_logico', 0)
            atualiza_relogio_recebido(relogio_msg)
            
            timestamp_recebimento = datetime.now(timezone.utc).isoformat()
            
            print(f"\n[MENSAGEM] Canal: {canal} | Relógio Lógico Atual: {relogio_logico}")
            print(f" > Mensagem: {payload.get('mensagem')}")
            print(f" > Enviado em:  {payload.get('timestamp_envio')}")
            print(f" > Recebido em: {timestamp_recebimento}\n")
        except Exception:
            pass

def enviar_req(req_socket, payload):
    payload["relogio_logico"] = incrementa_e_pega_relogio()
    req_socket.send_json(payload)
    resp = req_socket.recv_json()
    atualiza_relogio_recebido(resp.get("relogio_logico", 0))
    return resp

def main():
    context = zmq.Context()

    req_socket = context.socket(zmq.REQ)
    req_socket.connect("tcp://server:5555")

    sub_socket = context.socket(zmq.SUB)
    sub_socket.connect("tcp://proxy:5558")

    threading.Thread(target=escutar_mensagens, args=(sub_socket,), daemon=True).start()

    resp = enviar_req(req_socket, {"comando": "listar_canais"})
    canais = resp.get("canais", [])
    
    if len(canais) < 5:
        novo = f"canal_{random.randint(100,999)}"
        enviar_req(req_socket, {"comando": "criar_canal", "canal": novo})
        canais.append(novo)

    inscricoes = random.sample(canais, min(3, len(canais)))
    for c in inscricoes:
        sub_socket.setsockopt_string(zmq.SUBSCRIBE, c)
        print(f"[*] Inscrito no canal: {c}")

    time.sleep(1)

    while True:
        canal_alvo = random.choice(canais)
        for _ in range(10):
            enviar_req(req_socket, {
                "comando": "publicar",
                "canal": canal_alvo,
                "mensagem": gerar_texto()
            })
            time.sleep(1)

if __name__ == "__main__":
    main()
