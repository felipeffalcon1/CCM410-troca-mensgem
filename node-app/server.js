const zmq = require("zeromq");
const { encode, decode } = require("@msgpack/msgpack");
const fs = require("fs");

const ARQUIVO_DB = "banco_server.json";

// le do disco pra nao perder os dados se o container reiniciar
function loadDb() {
    if (fs.existsSync(ARQUIVO_DB)) {
        const data = fs.readFileSync(ARQUIVO_DB, "utf8");
        return JSON.parse(data);
    }
    // base zerada se for a primeira vez
    return { logins: [], canais: ["geral"] };
}

// salva as alteracoes de volta no arquivo
function saveDb(db) {
    fs.writeFileSync(ARQUIVO_DB, JSON.stringify(db, null, 2));
}

async function main() {
    if (process.argv.length < 3) {
        console.log("Erro: Forneca a porta do servidor. Ex: node server.js 5556");
        process.exit(1);
    }

    const porta = process.argv[2];
    const db = loadDb();

    // socket REP (Reply): passivo esperando
    const sock = new zmq.Reply();
    await sock.bind(`tcp://*:${porta}`);
    console.log(`[SERVER-NODE] Iniciado na porta ${porta}`);

    // loop principal do zeromq no node 
    for await (const [msg] of sock) {
        // descompacta o binario do messagepack
        const req = decode(msg);
        
        const acao = req.acao;
        const ts = req.timestamp;

        if (acao === "login") {
            const user = req.usuario;
            db.logins.push({ usuario: user, ts: ts });
            saveDb(db); // persiste no arquivo JSON local

            console.log(`[SERVER-NODE] User '${user}' fez login`);
            // responde empacotando em binario
            const resp = { status: "ok", msg: "login efetuado" };
            await sock.send(encode(resp));

        } else if (acao === "listar_canais") {
            console.log("[SERVER-NODE] Pedido de listagem de canais recebido");
            await sock.send(encode(db.canais));

        } else if (acao === "criar_canal") {
            const canal = req.canal;
            // checa duplicata antes de criar
            if (!db.canais.includes(canal)) {
                db.canais.push(canal);
                saveDb(db);
                console.log(`[SERVER-NODE] Canal '${canal}' criado com sucesso`);
                await sock.send(encode({ status: "ok" }));
            } else {
                console.log(`[SERVER-NODE] Erro: Canal '${canal}' ja existe`);
                await sock.send(encode({ status: "erro", msg: "canal duplicado" }));
            }
        } else {
            console.log("[SERVER-NODE] Acao desconhecida");
            await sock.send(encode({ status: "erro", msg: "acao invalida" }));
        }
    }
}

main();