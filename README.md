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