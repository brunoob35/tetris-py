# 🎮 Arcade Tetris – Projeto Final  

Este projeto é uma implementação de Tetris usando **Python + Arcade**, com:

- **Persistência de jogos**
- **Replays**
- **Continuidade de partidas**
- **Usuários**
- Integração com **MySQL no Amazon Aurora (RDS)**

A ideia é entregar um jogo funcional, organizado e com conceitos reais de desenvolvimento: banco em nuvem, replays, saves e uma estrutura básica em camadas.

---

## 🚀 Funcionalidades

### ▶️ Jogar Tetris
- Mecânica clássica
- Rotação, queda suave, hard drop
- Pontuação, nível e linhas

### 💾 Salvamento de partida
- Durante o jogo, ao apertar **ESC** ou **M**, o jogo:
  - Salva a partida atual
  - Volta ao menu principal
- No menu, se houver um jogo salvo, o botão “NOVO JOGO” vira **“CONTINUAR PARTIDA”**.

### 🔁 Replays
- Cada ação do jogador (tecla + tempo) é registrada.
- O replay usa a **mesma seed** do jogo original.
- A sequência de peças e movimentos é reproduzida exatamente como aconteceu.

### 🧱 Jogos interrompidos
- Você pode salvar, sair e continuar depois.
- Ao terminar um jogo, o save ativo é desativado automaticamente (não fica “preso” em uma partida antiga).

### ☁️ Banco de dados em nuvem (AWS RDS)
- Banco MySQL hospedado no **Amazon Aurora (RDS)**.
- Conexão via variáveis de ambiente no `.env`.
- Arquivo `schema.sql` com as tabelas do projeto.

---

## 📦 Estrutura do Projeto

Estrutura simples e organizada em camadas:

``` text
arcade_tetris/
  main.py
  .env
  .gitignore

  db/
    schema.sql
    db.py             # conexão com o banco (Aurora RDS)
    repository.py     # operações com o banco (CRUD)

  tetris/
    __init__.py

    core/
      constants.py      # valores globais do jogo
      factory.py        # funções de desenho e utilidades
      state_codec.py    # serialização do estado do jogo

    models/
      board.py          # tabuleiro (matriz do jogo)
      game.py           # regras do jogo (pontuação, colisões, etc.)
      pieces.py         # definição das peças
      tetromino.py      # lógica individual dos tetrominos

    views/
      gui.py            # telas, menus e lógicas de interface
```
## 🗄️ Banco de Dados (Aurora RDS / MySQL)
O banco já está configurado para rodar em um cluster Aurora RDS.
Para conectar, o projeto usa variáveis no .env.

### Exemplo de .env
``` env
    DB_HOST=seu-host.rds.amazonaws.com
    DB_PORT=3306
    DB_USER=admin
    DB_PASS=suasenha
    DB_NAME=tetrisdb
```

### ▶️ Como rodar o projeto
 1. Criar ambiente virtual
``` bash
    python -m venv .venv

    # macOS / Linux
    source .venv/bin/activate

    # Windows
    .venv\Scripts\activate
```

2. Instalar dependências
``` bash
    pip install arcade mysql-connector-python
```
3. Criar o arquivo .env
- Na raiz do projeto, ao lado do main.py, crie um .env com as variáveis de conexão ao banco.
4. Executar o jogo
``` bash
    python main.py
```

## 👤 Criando um usuário dentro do jogo
Quando abre o jogo pela primeira vez, ele solicita um nome de usuário.
Esse nome é salvo na tabela users e é usado para:
- vincular saves ativos
- associar jogos finalizados
- relacionar replays

Você não precisa criar nada manualmente no banco: o próprio jogo registra o usuário.

### 🧠 Visão geral de como tudo trabalha junto
`main.py`
- Ponto de entrada da aplicação.
- Cria a janela do Arcade.
- Carrega o menu principal.

**Camada de VISÃO** – `tetris/views/gui.py`

Responsável por tudo que o jogador vê e interage:
- Menus, HUD, tela de jogo e replay.
- Captura de teclas (mover, girar, pausar, salvar/voltar).
- Renderização do tabuleiro e do painel lateral.
- Overlay de pausa.
- Tela de replay, com informações do jogo e saída para o menu.

Ela conversa com:
- models para manipular o estado do jogo.
- infra.repository para salvar e buscar dados.
- core.state_codec para transformar o estado do jogo em algo que o banco possa guardar.

**Camada de MODELO – tetris/models**

`game.py`
- Regras principais do Tetris:
  - movimentação e rotação das peças
  - checagem de colisões
  - queda automática
  - limpeza de linhas
  - pontuação e níveis
  - controle de estado (game over, pausa, etc.)
- Usa uma seed para garantir que a sequência de peças seja reprodutível (replays).

`board.py`

- Representa o tabuleiro em forma de matriz.
- Sabe quais células estão vazias e quais estão ocupadas.

`pieces.py` e `tetromino.py`
- Guardam a definição e o comportamento das peças:
  - formatos
  - rotações
  - cores
  
**Núcleo do jogo –** `tetris/core`

`constants.py`
- Configurações gerais:
  - tamanho da tela
  - tamanho do tabuleiro
  - tamanho dos blocos
  - cores usadas
  - fonte e layout
  
`factory.py`
- Funções auxiliares, como:
  - desenhar blocos no estilo 8-bit
  - elementos visuais usados pelas views
    
`state_codec.py`
- Transforma o estado do TetrisGame em um dicionário serializável.
- Faz o caminho inverso: pega os dados salvos no banco e reconstrói o TetrisGame.
- É a “ponte” entre o mundo do jogo e o mundo do banco de dados.

**Database – db/**
`db.py`
- Lê as configurações do `.env.`
- Cria a conexão com o banco Aurora RDS / MySQL.
- Fornece uma função central para obter conexões.

`repository.py`
- Camada que fala diretamente com o banco.
- Principais responsabilidades:
  - criar um novo jogo (`start_game()`)
  - finalizar e atualizar um jogo (`finish_game()`)
  - salvar e carregar o estado de uma partida (`upsert_saved_game()`, `load_active_save()`)
  - salvar eventos de replay e recuperá-los (`save_replay_events()`, `load_replay()`)
  - atualizar e consultar high scores

Todo o acesso a banco fica concentrado aqui, deixando o restante do código mais limpo.

### 🔁 Fluxos principais
**Novo jogo**
1. Usuário escolhe iniciar jogo.
2. `gui.py` cria `TetrisGame()` com seed.
3. `repository.start_game` registra no banco.
4. Jogo começa.

**Salvar e voltar ao menu**
1. Usuário aperta ESC ou M.
2. `gui.py` usa `state_codec.game_to_state()`.
3. `repository.upsert_saved_game` salva.
4. Retorna ao menu.
 
**Continuar partida**
1. Menu verifica save ativo.
2. Se existir, botão vira “CONTINUAR PARTIDA”.
3. `load_active_save` carrega estado salvo.
4. `state_codec.state_to_game` reconstrói o jogo.
5. Partida continua.

**Replay**
1. Durante o jogo: eventos são gravados com tempo exato.
2. Ao finalizar: eventos são persistidos.
3. Replay:
   - carrega seed
   - recria TetrisGame com a seed verdadeira
   - reaplica eventos na ordem original