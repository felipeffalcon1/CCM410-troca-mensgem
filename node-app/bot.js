const zmq = require("zeromq");
const { encode, decode } = require("@msgpack/msgpack");

// pega o timestamp no formato ISO que foi pedido
function getTime() {
    return new Date().toISOString();
}

// helper pra dar sleep entre as mensagen e o terminal nao bugar
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function main() {
    if (process.argv.length < 4) {
        console.log("Uso: node bot.js <nome_usuario> <endereco_servidor>");
        process.exit(1);
    }

    const usuario = process.argv[2];
    const servidor = process.argv[3];

    // socket REQ (Request): o bot chama
    const sock = new zmq.Request();
    
    console.log(`[${usuario}] Conectando a ${servidor}...`);
    sock.connect(servidor);

    await sleep(2000); // espera conectar

    //  TESTE 1: FAZER LOGIN 
    const msgLogin = {
        acao: "login",
        usuario: usuario,
        timestamp: getTime()
    };
    await sock.send(encode(msgLogin));
    let [repLogin] = await sock.receive();
    console.log(`[${usuario}] Resposta do login:`, decode(repLogin));
    await sleep(1000);

    //  TESTE 2: LISTAR OS CANAIS 
    const msgListar = {
        acao: "listar_canais",
        timestamp: getTime()
    };
    await sock.send(encode(msgListar));
    let [repListar] = await sock.receive();
    console.log(`[${usuario}] Canais disponiveis:`, decode(repListar));
    await sleep(1000);

    //  TESTE 3: CRIAR UM CANAL NOVO 
    const novoCanal = `canal_${usuario}`;
    const msgCriar = {
        acao: "criar_canal",
        canal: novoCanal,
        timestamp: getTime()
    };
    await sock.send(encode(msgCriar));
    let [repCriar] = await sock.receive();
    console.log(`[${usuario}] Status criacao do '${novoCanal}':`, decode(repCriar));

    console.log(`[${usuario}] Fim da execucao da Parte 1.`);
    // encerra o processo
    process.exit(0);
}

main();