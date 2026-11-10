import zmq

def main():
    context = zmq.Context()

    # XSUB (5557): Recebe as publicações enviadas pelo Servidor
    frontend = context.socket(zmq.XSUB)
    frontend.bind("tcp://*:5557")

    # XPUB (5558): Repassa as mensagens para os Bots (que assinaram os canais)
    backend = context.socket(zmq.XPUB)
    backend.bind("tcp://*:5558")

    print("[PROXY] Iniciado nas portas 5557 (XSUB) e 5558 (XPUB)...")
    try:
        zmq.proxy(frontend, backend)
    except KeyboardInterrupt:
        pass
    finally:
        frontend.close()
        backend.close()
        context.term()

if __name__ == "__main__":
    main()
