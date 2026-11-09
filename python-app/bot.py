import zmq
import msgpack
from datetime import datetime
import sys
import time

# helper pra pegar o timestamp
def get_time():
    return datetime.now().isoformat()

def main():
    if len(sys.argv) < 3:
        print("Uso: python bot.py <nome_usuario> <endereco_servidor>")
        return

    usuario = sys.argv[1]
    servidor = sys.argv[2]
    
    ctx = zmq.Context()
    # socket REQ (Request): o cliente que toma a iniciativa de chamar
    s = ctx.socket(zmq.REQ)
    
    print(f"[{usuario}] Conectando a {servidor}...", flush=True)
    s.connect(servidor) 
    
    time.sleep(2) # da um tempo pro socket estabilizar
    
    #  TESTE 1: FAZER LOGIN 
    msg_login = {
        "acao": "login",
        "usuario": usuario,
        "timestamp": get_time()
    }
    s.send(msgpack.packb(msg_login))
    resp_login = msgpack.unpackb(s.recv(), raw=False)
    print(f"[{usuario}] Resposta do login: {resp_login}", flush=True)
    time.sleep(1)

    #  TESTE 2: LISTAR OS CANAIS 
    msg_listar = {
        "acao": "listar_canais",
        "timestamp": get_time()
    }
    s.send(msgpack.packb(msg_listar))
    canais = msgpack.unpackb(s.recv(), raw=False)
    print(f"[{usuario}] Canais disponiveis: {canais}", flush=True)
    time.sleep(1)

    #  TESTE 3: CRIAR UM CANAL NOVO 
    # usa o proprio nome do bot no canal pra ficar facil de ver no print
    novo_canal = f"canal_{usuario}"
    msg_criar = {
        "acao": "criar_canal",
        "canal": novo_canal,
        "timestamp": get_time()
    }
    s.send(msgpack.packb(msg_criar))
    resp_criar = msgpack.unpackb(s.recv(), raw=False)
    print(f"[{usuario}] Status criacao do '{novo_canal}': {resp_criar}", flush=True)
    
    print(f"[{usuario}] Fim da execucao da Parte 1.", flush=True)

if __name__ == '__main__':
    main()