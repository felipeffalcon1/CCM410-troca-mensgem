import zmq
import time

def main():
    context = zmq.Context()
    rep = context.socket(zmq.REP)
    rep.bind("tcp://*:5556")

    servidores = {}
    next_rank = 1
    TIMEOUT = 30 

    print("[REFERENCIA] Iniciado na porta 5556 (Parte 4 - Sem timestamp no Heartbeat)...")

    while True:
        req = rep.recv_json()
        comando = req.get("comando")
        nome = req.get("nome")
        
        agora = time.time()
        
        servidores_ativos = {k: v for k, v in servidores.items() if agora - v["last_heartbeat"] < TIMEOUT}
        servidores = servidores_ativos

        if comando == "registrar":
            if nome not in servidores:
                servidores[nome] = {"rank": next_rank, "last_heartbeat": agora, "nome": nome}
                next_rank += 1
            else:
                servidores[nome]["last_heartbeat"] = agora
            rep.send_json({"rank": servidores[nome]["rank"]})

        elif comando == "list":
            lista = [{"nome": k, "rank": v["rank"]} for k, v in servidores.items()]
            rep.send_json({"servidores": lista})

        elif comando == "heartbeat":
            if nome in servidores:
                servidores[nome]["last_heartbeat"] = agora
            # PARTE 4: Responde apenas OK, sem enviar a hora!
            rep.send_json({"status": "OK"})

if __name__ == "__main__":
    main()
