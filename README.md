# Sistema de Rotas de Entrega
🇬🇧 [Read in English](README.en.md)

Painel web em **Python + Streamlit** que monta a rota de entregas do dia: lê os pedidos prontos, busca os dados no ERP **GestãoClick**, calcula o caminho pela **Google Routes API** e gera a rota em ordem, com PDF e link para o Google Maps.
O projeto surgiu de uma necessidade da empresa em que eu trabalhava, que montava as rotas de entrega manualmente. Ele foi usado internamente pela equipe após finalizado. Esta versão é pública apenas para portfólio: o nome da empresa, a logo e todos os dados reais foram removidos.

**Tempo de desenvolvimento:** 4 meses.

## Como foi desenvolvido

Este foi meu primeiro projeto profissional, feito enquanto ainda estou aprendendo.

- **Feito por mim:** a automação original em Python (leitura dos pedidos, integração com as APIs do GestãoClick e do Google e cálculo da rota), as regras de negócio, as decisões de segurança, todas as decisões de design e de experiência do usuário (layout, cores, organização das telas e o que cada uma mostra) e a conferência de todo o código.
- **Com ajuda de IA (Claude Code):** a interface web em Streamlit e partes da evolução do sistema, sempre a partir das regras e do design que eu defini. Todo o código gerado foi revisado e testado por mim antes de entrar no sistema.

## Funcionalidades

- **Lista de pedidos com prioridade**, conferida no ERP (só pedidos concretizados), com Nº da NF, volumes e escolha de entrega no cliente ou na transportadora.
- **Geração de rota** com 1 a 10 paradas, raio máximo de 50 km, horário de saída e de retorno.
- **Agrupamento por transportadora**: tudo o que vai para a mesma transportadora vira uma parada só.
- **Paradas extras** (retiradas, amostras, trocas) buscadas por CPF/CNPJ.
- **PDF da rota** para o motorista e link com as paradas para o Google Maps.
- **Confirmação de entregas** item por item e **histórico** de 60 dias.
- **Controle da cota grátis** do Google, para não gerar cobranças.

## Segurança

- Login com senhas em **bcrypt**, bloqueio após 5 tentativas erradas e troca obrigatória da senha temporária.
- Segredos (tokens, chaves, endereço) só no `st.secrets`, **nunca no código**.
- SQL sempre com **parâmetros** (`?`), contra SQL injection.
- Todo texto vindo de fora passa por **escape**, contra XSS.
- **Minimização de dados**: CPF e telefone são removidos dos nomes antes de gravar; o histórico é apagado após 60 dias.
- **Gravações protegidas contra acesso simultâneo** (`BEGIN IMMEDIATE`): quem salva por último não apaga o trabalho do outro.
- Acesso pela rede interna só por **HTTPS** (Caddy como proxy reverso).
- Código verificado com **Bandit**, **pip-audit** e **Gitleaks**.

## Tecnologias

Python 3.14 · Streamlit · SQLite · bcrypt · requests · fpdf2 · Google Routes API · API GestãoClick · Caddy

## Como rodar

1. Clone o repositório e crie o ambiente virtual:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Copie `secrets.example.toml` para `.streamlit/secrets.toml` e preencha com os seus valores. A senha do administrador é gerada com `python gerar_hash.py`.
3. Inicie: `streamlit run app.py`
4. (Opcional) Para acesso pela rede com HTTPS, baixe o Caddy em [caddyserver.com](https://caddyserver.com/download), coloque o `caddy.exe` na pasta `servidor` e inicie pelo `servidor\iniciar_sistema.bat`.

## Testes

Os testes usam banco temporário e APIs simuladas (nenhuma chamada real):

```bash
python -m unittest testes_rodada1 testes_rodada2 testes_rodada3 testes_marca
```