CCM410 - Sistema de Troca de Mensagens (BBS)
Introdução
O projeto consiste em construir um sistema distribuído de troca de mensagens, nos moldes de um clássico Bulletin Board System (BBS). A ideia principal é permitir uma comunicação assíncrona eficiente e a publicação/inscrição de tópicos entre diferentes clientes e servidores, colocando em prática conceitos fundamentais de sistemas distribuídos, como concorrência e troca de mensagens em rede.

Escolhas Técnicas e Arquiteturais
1. Linguagens de Programação
Python e Node.js: A escolha foi baseada na praticidade para lidar com sockets, manipulação de dados em tempo real e na facilidade de encontrar bibliotecas focadas em mensageria assíncrona. Ambas entregam um desenvolvimento ágil e contam com um ecossistema excelente para comunicação de rede.

2. Mecanismo de Serialização
JSON: Escolhido para empacotar e estruturar as mensagens que trafegam entre os nós.

Por que escolhemos: É um formato leve, fácil de ler (human-friendly), independente de linguagem e amplamente suportado, o que simplifica bastante o parse e a validação dos dados enviados.

3. Persistência de Dados
Arquivos locais / Estruturas em memória: As mensagens e os tópicos do sistema são salvos em arquivos locais simples ou gerenciados diretamente em memória com algum dump estruturado.

Por que escolhemos: Para o escopo acadêmico da disciplina, essa abordagem resolve o problema com simplicidade e eficiência, evitando a complexidade desnecessária de subir um banco de dados relacional pesado logo de início.
### 4. Parte 2: Padrão Pub/Sub e Proxy (ZeroMQ)
Nesta etapa, o sistema foi expandido para suportar o padrão Publish/Subscribe usando um nó intermediário (Proxy). O Servidor se conecta ao Proxy via socket `PUB` na porta `5557`, enquanto os clientes (bots) assinam os canais conectando via socket `SUB` na porta `5558`. A comunicação dos comandos de publicação ainda trafega pelo canal `REQ/REP`.

Para permitir a leitura de mensagens em tempo real sem travar a thread principal de envio dos bots, foi implementado o uso de `Threading`. 

### 5. Persistência em Disco
A persistência dos dados e publicações foi implementada através de um volume Docker vinculado à pasta local `./data`, salvando as mensagens estruturadas num formato `mensagens.json`. Foi escolhido o padrão de escrita sequencial em JSON no modo *append* por ser leve, não necessitar de instalação de bancos externos e prevenir corrupção em falhas repentinas.
