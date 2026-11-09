import zmq
import msgpack
import json
import os
import sys

ARQUIVO_DB = "banco_server.json"

# carrega o "banco" do disco pra nao perder tudo se o server reiniciar
def load_db():
    if os.path.exists(ARQUIVO_DB):
        with open(ARQUIVO_DB, "r") as f:
            return json.load(f)
    # se o arquivo nao existir, comeca zerado mas ja com o canal geral
    return {"logins": [], "canais": ["geral"]}

# salva as alteracoes de volta no arquivo
def save_db(db):
    with open(ARQUIVO_DB, "w") as f:
        json.dump(db, f, indent=2)

def main():
    if len(sys.argv) < 2:
        print("Erro: Forneca a porta do servidor.")
        return
        
    porta = sys.argv[1]
    db = load_db()
    
    ctx = zmq.Context()
    # socket REP (Reply): fica passivo esperando alguem chamar
    s = ctx.socket(zmq.REP)
    s.bind(f"tcp://*:{porta}")

    print(f"[SERVER-PY] Iniciado na porta {porta}", flush=True)

    while True:
        # recebe os dados em binario e descompacta o messagepack
        raw_msg = s.recv()
        req = msgpack.unpackb(raw_msg, raw=False)
        
        acao = req.get("acao")
        ts = req.get("timestamp")

        # trata as 3 acoes exigidas na Parte 1 do enunciado
        if acao == "login":
            user = req.get("usuario")
            db["logins"].append({"usuario": user, "ts": ts})
            save_db(db) # persiste no arquivo JSON local
            
            print(f"[SERVER-PY] User '{user}' fez login", flush=True)
            # responde empacotando em binario de novo pra cumprir a regra
            resp = {"status": "ok", "msg": "login efetuado"}
            s.send(msgpack.packb(resp))

        elif acao == "listar_canais":
            print("[SERVER-PY] Pedido de listagem de canais recebido", flush=True)
            s.send(msgpack.packb(db["canais"]))

        elif acao == "criar_canal":
            canal = req.get("canal")
            # checa duplicata antes de criar
            if canal not in db["canais"]:
                db["canais"].append(canal)
                save_db(db)
                print(f"[SERVER-PY] Canal '{canal}' criado com sucesso", flush=True)
                resp = {"status": "ok"}
            else:
                print(f"[SERVER-PY] Erro: Canal '{canal}' ja existe", flush=True)
                resp = {"status": "erro", "msg": "canal duplicado"}
            
            s.send(msgpack.packb(resp))
            
        else:
            print("[SERVER-PY] Acao desconhecida recebida", flush=True)
            s.send(msgpack.packb({"status": "erro", "msg": "acao invalida"}))

if __name__ == '__main__':
    main()