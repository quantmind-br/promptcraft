### **PromptCraft**

---

#### **Seção 1: Contexto Estratégico e Visão do Produto**

**1.1. Missão Principal:**
Sua missão é desenvolver uma ferramenta de linha de comando (CLI) em Python, chamada **PromptCraft**. O objetivo principal desta ferramenta é permitir que desenvolvedores de software definam e utilizem "slash commands" (ex: `/revisar`) para gerar prompts complexos e padronizados. Estes prompts serão então usados em outros assistentes de IA via CLI. A ferramenta deve ser agnóstica à IA de destino, funcionando como um pré-processador de prompts universal.

**1.2. Problema a Ser Resolvido (Contexto do "Porquê"):**
Desenvolvedores humanos gastam tempo e energia mental digitando repetidamente as mesmas instruções complexas para IAs. Isso leva a inconsistências, especialmente em equipes, e à perda de "prompts otimizados". PromptCraft abstrai essa complexidade, armazenando a lógica dos prompts em arquivos de template reutilizáveis. Pense nisso como criar "funções" para prompts.

**1.3. Personas de Usuário (Contexto do "Para Quem"):**
* **Daniel (Desenvolvedor Individual):** Ele valoriza a velocidade e a eficiência. Ele usará o PromptCraft para automatizar seus próprios prompts repetitivos para tarefas como gerar testes, documentar código e refatorar. Ele precisa de uma ferramenta rápida, leve e que "simplesmente funcione".
* **Mariana (Líder de Equipe):** Ela valoriza a padronização e a qualidade. Ela usará o PromptCraft para definir um conjunto de comandos para sua equipe (ex: `/revisar_pr`, `/relatar_bug`) em um repositório compartilhado. Isso garante que todos interajam com a IA de forma consistente, seguindo as melhores práticas da equipe.

---

#### **Seção 2: Especificações Técnicas e Arquitetura**

**2.1. Stack de Tecnologia Mandatória:**
* **Linguagem:** Python 3.10 ou superior.
    * *Contexto:* Python oferece excelente suporte multiplataforma (Windows, macOS, Linux), uma vasta biblioteca padrão para manipulação de arquivos e strings, e ecossistemas de pacotes maduros para CLI e distribuição.
* **Framework de CLI:** `click`.
    * *Contexto:* `click` é uma biblioteca declarativa, poderosa e fácil de usar para criar CLIs complexas, lidando com argumentos, flags e subcomandos de forma robusta. É preferível a `argparse` pela sua simplicidade e extensibilidade.
* **Interação com Clipboard:** `pyperclip`.
    * *Contexto:* É uma biblioteca leve e multiplataforma que abstrai a complexidade de interagir com a área de transferência de diferentes sistemas operacionais.
* **Testes:** `pytest`.
    * *Contexto:* `pytest` é o padrão de fato para testes em Python, com uma sintaxe simples e um ecossistema de plugins poderoso.
* **Empacotamento:** `setuptools`.
    * *Contexto:* Utilizaremos `pyproject.toml` e `setup.cfg` para definir os metadados do pacote, dependências e o ponto de entrada do script, seguindo as práticas modernas de empacotamento em Python.

**2.2. Estrutura de Diretórios do Projeto (A ser criada):**

```

promptcraft/
├── .gitignore
├── pyproject.toml
├── README.md
├── src/
│   └── promptcraft/
│       ├── **init**.py
│       ├── main.py         \# Lógica da CLI (usando click)
│       ├── core.py         \# Lógica de descoberta e parsing de comandos
│       └── exceptions.py   \# Exceções customizadas
└── tests/
├── test\_core.py
└── test\_main.py

```

**2.3. Princípios de Design Não-Funcionais (Restrições):**
* **Performance:** A execução deve ser inferior a 150ms. O código deve ser otimizado para um startup rápido.
* **Mínimas Dependências:** Apenas as bibliotecas especificadas devem ser usadas como dependências de produção para manter a ferramenta leve.
* **Clareza de Código:** O código deve seguir estritamente a PEP 8. Todas as funções e classes devem ter docstrings claras explicando seu propósito, argumentos e o que retornam.
* **Tratamento de Erros:** A aplicação deve ser resiliente e nunca travar com um traceback não tratado. Utilize exceções customizadas (definidas em `exceptions.py`) para erros esperados (ex: `CommandNotFoundError`) e forneça mensagens amigáveis ao usuário.

---

#### **Seção 3: Plano de Implementação por Milestones (Passo a Passo)**

**Milestone 1: O Motor Principal (Core Logic)**

* **Objetivo:** Criar a lógica fundamental de encontrar e processar um arquivo de comando.
* **Local:** `src/promptcraft/core.py` e `src/promptcraft/exceptions.py`.
* **Passos:**
    1.  **Definir Exceções:** Em `exceptions.py`, crie exceções customizadas: `CommandNotFoundError(Exception)` e `TemplateReadError(Exception)`.
    2.  **Implementar a Função `find_command_path(command_name: str) -> Path`:**
        * Esta função recebe o nome de um comando (ex: "revisar").
        * Define o caminho do diretório de comandos do projeto: `project_path = Path.cwd() / '.promptcraft' / 'commands'`.
        * Define o caminho do diretório de comandos global: `global_path = Path.home() / '.promptcraft' / 'commands'`.
        * Verifica a existência de `{command_name}.md` em `project_path`. Se existir, retorna o caminho completo.
        * Se não, verifica a existência em `global_path`. Se existir, retorna o caminho completo.
        * Se não encontrar em nenhum, lança `CommandNotFoundError(f"Comando '{command_name}' não encontrado.")`.
    3.  **Implementar a Função `generate_prompt(command_name: str, arguments: list[str]) -> str`:**
        * Chama `find_command_path(command_name)` para obter o caminho do arquivo de template.
        * Lê o conteúdo do arquivo. Se houver um erro de leitura, lança `TemplateReadError`.
        * Concatena os `arguments` em uma única string, separados por espaço.
        * Substitui a ocorrência de `$ARGUMENTS` no conteúdo do template pela string de argumentos.
        * Retorna a string do prompt final.

**Milestone 2: A Interface de Linha de Comando (CLI)**

* **Objetivo:** Expor a lógica do core através de uma interface `click` amigável.
* **Local:** `src/promptcraft/main.py`.
* **Passos:**
    1.  **Setup do CLI:** Crie a função principal `cli()` e a decore com `@click.group()`.
    2.  **Comando Principal:** Crie uma função `run(command: str, args: list[str])`.
        * Use a sintaxe do `click` para capturar um argumento `command` e uma lista de argumentos `args` que podem ser múltiplos.
        * O nome do comando virá com a barra (ex: `/revisar`). Remova a barra inicial.
        * Chame `core.generate_prompt(command_name, args)`.
        * Use `pyperclip.copy()` para copiar o resultado.
        * Imprima uma mensagem de sucesso no terminal, como `click.secho(f"✅ Prompt para '/{command}' copiado!", fg="green")`.
        * Implemente um bloco `try...except` para capturar `CommandNotFoundError` e `TemplateReadError` e imprimir mensagens de erro amigáveis usando `click.secho(..., fg="red")`.
    3.  **Flag `--stdout`:** Adicione uma opção booleana `--stdout` ao comando `run`. Se `True`, em vez de copiar para o clipboard, imprima o prompt final diretamente no `stdout`.

**Milestone 3: Comandos de Utilidade e UX**

* **Objetivo:** Adicionar funcionalidades que melhorem a experiência do usuário.
* **Local:** `src/promptcraft/main.py` e `src/promptcraft/core.py`.
* **Passos:**
    1.  **Implementar `promptcraft --init`:**
        * Crie um novo comando `init()` no `main.py` decorado com `@click.command()`.
        * A lógica deve criar o diretório `.promptcraft/commands` no diretório de trabalho atual.
        * Deve criar um arquivo de exemplo dentro dele, `.promptcraft/commands/exemplo.md`, com conteúdo instrutivo.
        * Imprima mensagens sobre as ações realizadas.
    2.  **Implementar `promptcraft --list`:**
        * Crie um novo comando `list_commands()` no `main.py` decorado com `@click.command()`.
        * A lógica (provavelmente em `core.py`) deve escanear ambos os diretórios (global e de projeto), coletar todos os arquivos `.md` e seus caminhos.
        * Imprima uma lista formatada no terminal, indicando o nome do comando, sua origem (Projeto/Global) e a primeira linha do arquivo como descrição. Utilize a biblioteca `rich` para uma formatação mais agradável, se desejar (adicione-a como dependência).

**Milestone 4: Testes e Validação**

* **Objetivo:** Garantir a robustez e o correto funcionamento da aplicação.
* **Local:** `tests/`.
* **Passos:**
    1.  **Estrutura de Testes:** Use `pytest`. Crie estruturas de diretórios e arquivos temporários usando fixtures do `pytest` (ex: `tmp_path`) para simular os diretórios de comandos globais e de projeto.
    2.  **Testar `test_core.py`:**
        * Teste o sucesso da descoberta de comandos (global, projeto, e a precedência do projeto sobre o global).
        * Teste o lançamento de `CommandNotFoundError`.
        * Teste a geração de prompt com e sem argumentos.
    3.  **Testar `test_main.py`:**
        * Use o `CliRunner` do `click` para invocar os comandos da CLI em testes.
        * Teste a execução bem-sucedida de um comando.
        * Teste a flag `--stdout`.
        * Teste o tratamento de erros (comando não encontrado).
        * Teste os comandos `--init` e `--list`, verificando a saída e os artefatos criados no sistema de arquivos.

**Milestone 5: Empacotamento e Distribuição**

* **Objetivo:** Preparar a aplicação para ser instalada por usuários finais.
* **Local:** `pyproject.toml`.
* **Passos:**
    1.  **Configurar `pyproject.toml`:**
        * Defina os metadados do projeto (nome, versão, autor, descrição).
        * Liste as dependências de produção (`click`, `pyperclip`).
        * Defina o ponto de entrada da CLI para que o `pip` crie o executável `promptcraft` corretamente. Aponte para a função `cli` em `src.promptcraft.main`.
    2.  **Criar `README.md`:** Escreva uma documentação clara sobre como instalar (`pip install .`), configurar (`promptcraft --init`) e usar a ferramenta. Inclua exemplos de criação e uso de comandos.

---
```
