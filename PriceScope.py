import telebot
import requests
import datetime
import time
import threading
from telebot import types

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb+srv://<UserName>:<Password>@cluster.ox6qa.mongodb.net/?retryWrites=true&w=majority&appName=Cluster"

client = MongoClient(uri, server_api=ServerApi('1'))

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

database = client.MercadoLivre

alerta_collection = database['alerta']


API_TOKEN = '<API_KEY>'
bot = telebot.TeleBot(API_TOKEN)

API_TOKEN = '<API_KEY>'
CSE_ID = '<ID>'

COMANDOS_VALIDOS = ['/start', '/ajuda', '/bertoti', '/opcao1', '/opcao2', '/opcao3', '/opcao4', '/opcao5']


@bot.message_handler(commands=['start', 'bertoti'])
def start(mensagem):
    """Menu inicial com botões interativos."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    botao1 = types.InlineKeyboardButton("Buscar melhores preços 🔍", callback_data="opcao1")
    botao2 = types.InlineKeyboardButton("Comparar preços 📊", callback_data="opcao2")
    botao3 = types.InlineKeyboardButton("Sugestões de produtos 🛒", callback_data="opcao3")
    botao4 = types.InlineKeyboardButton("Definir alerta 🔔", callback_data="opcao4")
    botao5 = types.InlineKeyboardButton("Sair 🚪", callback_data="opcao5")
    markup.add(botao1, botao2, botao3, botao4, botao5)

    bot.send_message(mensagem.chat.id, "👋 Bem-vindo ao *Price Scope Bot*!\nEscolha uma opção abaixo:", parse_mode="Markdown", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    """Handler para interações de botões inline."""
    if call.data == "opcao1":
        bot.send_message(call.message.chat.id, "Você escolheu a opção de Buscar melhores preços 🔍.\nDigite o nome do produto que deseja buscar:")
        bot.register_next_step_handler(call.message, obter_preco_mercadolivre)

    elif call.data == "opcao2":
        bot.send_message(call.message.chat.id, "Você escolheu Comparar preços 📊.\nDigite os nomes dos produtos separados por vírgula:")
        bot.register_next_step_handler(call.message, obter_produtos_para_comparar)

    elif call.data == "opcao3":
        bot.send_message(call.message.chat.id, "Você escolheu Sugestões de produtos por categoria 🛒.")
        fornecer_sugestoes(call.message)

    elif call.data == "opcao4":
        bot.send_message(call.message.chat.id, "Você escolheu Definir alerta de oferta 🔔.\nQual produto deseja monitorar?")
        bot.register_next_step_handler(call.message, definir_alerta)

    elif call.data == "opcao5":
        bot.send_message(call.message.chat.id, "🚪 Até logo! Espero te ajudar novamente em breve!")
        bot.answer_callback_query(call.id, "Bot finalizado. Obrigado por usar nossos serviços!")

@bot.message_handler(commands=['ajuda'])
def ajuda(mensagem):
    """Mostra o menu de ajuda."""
    text = """
   🤖 *Price Scope Bot - Ajuda* 📚

    Escolha uma das opções para começar:
    - /opcao1 - Buscar melhores preços de um produto 🔍
    - /opcao2 - Comparar preços de produtos 📊
    - /opcao3 - Sugestões de produtos por categoria 🛒
    - /opcao4 - Definir alerta de oferta 🔔
    - /opcao5 - Sair 🚪

    Você também pode clicar nos botões no menu inicial.
    """
    bot.send_message(mensagem.chat.id, text, parse_mode="Markdown")




@bot.message_handler(commands=['opcao1'])
def buscar_preco(mensagem):
    bot.reply_to(mensagem, "🔍 Qual produto você está procurando? Me informe o máximo de detalhes.")
    bot.register_next_step_handler(mensagem, obter_preco_mercadolivre)


def obter_preco_mercadolivre(mensagem):
    produto = mensagem.text
    bot.reply_to(mensagem, f"🔍 Buscando os melhores preços para *{produto}* no Mercado Livre...")

    url = f"https://api.mercadolibre.com/sites/MLB/search?q={produto}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        resultados = response.json()

        if 'results' in resultados and resultados['results']:
            resposta = []
            for item in resultados['results'][:4]:
                titulo = item['title']
                preco = item['price']
                link = item['permalink']
                resposta.append(f"📌 Produto: {titulo}\n💲 Preço: R$ {preco:.2f}\n🔗 Link: {link}\n")

            bot.reply_to(mensagem, "\n".join(resposta))
        else:
            bot.reply_to(mensagem, f"⚠️ Não foram encontrados resultados para *{produto}*.")
    except requests.exceptions.HTTPError as http_err:
        bot.reply_to(mensagem, f"❌ Ocorreu um erro HTTP: {http_err}")
    except requests.exceptions.RequestException as e:
        bot.reply_to(mensagem, f"❌ Ocorreu um erro ao buscar preços: {str(e)}")
    except Exception as e:
        bot.reply_to(mensagem, f"❌ Ocorreu um erro inesperado: {str(e)}")

    start(mensagem)

@bot.message_handler(commands=['opcao2'])
def comparar_precos(mensagem):
    bot.register_next_step_handler(mensagem, obter_produtos_para_comparar)

def obter_produtos_para_comparar(mensagem):
    produtos = mensagem.text.split(',')
    produtos = [p.strip() for p in produtos]

    if not produtos:
        bot.reply_to(mensagem, "Por favor, forneça pelo menos um produto para comparar. 🛒")
        return

    bot.reply_to(mensagem, f"Buscando os preços para os seguintes produtos: {', '.join(produtos)}...\nAguarde um momento. ⏳")

    resultados = []
    for produto in produtos:
        url = f"https://api.mercadolibre.com/sites/MLB/search?q={produto}"

        try:
            response = requests.get(url)
            response.raise_for_status()
            dados = response.json()

            if 'results' in dados and dados['results']:
                item = dados['results'][0]
                titulo = item['title']
                preco = item['price']
                link = item['permalink']
                resultados.append(f"🛒 Produto: {titulo}\n💲 Preço: R$ {preco:.2f}\n🔗 Link: {link}\n")
            else:
                resultados.append(f"😔 Não encontrei resultados para o produto: {produto}")

        except requests.exceptions.RequestException as e:
            resultados.append(f"⚠️ Ocorreu um erro ao buscar o produto '{produto}': {str(e)}")

    if resultados:
        bot.reply_to(mensagem, "\n".join(resultados))
    else:
        bot.reply_to(mensagem, "Desculpe, não encontrei preços para os produtos que você pesquisou. 😞")

    start(mensagem)


@bot.message_handler(commands=['opcao3'])
def fornecer_sugestoes(mensagem):
    """
    Fornece uma lista de categorias ao usuário com links para escolher diretamente a categoria usando o comando ⁠ /id ⁠.
    """
    url_categorias = "https://api.mercadolibre.com/sites/MLB/categories"

    try:

        response = requests.get(url_categorias)
        response.raise_for_status()
        categorias = response.json()

        lista_categorias = [
            f"/{cat['id']} - {cat['name']}"
            for cat in categorias
        ]

        mensagem_resposta = (
            "Escolha uma categoria clicando no comando correspondente: 🛍️\n" + "\n".join(lista_categorias[:20])
        )

        bot.reply_to(mensagem, mensagem_resposta)
    except requests.exceptions.RequestException as e:
        bot.reply_to(mensagem, f"⚠️ Erro ao buscar categorias: {str(e)}")

@bot.message_handler(func=lambda message: message.text.startswith('/') and message.text not in COMANDOS_VALIDOS)
def processar_comando_id(mensagem):
    """
    Processa o comando ⁠ /id ⁠ enviado pelo usuário, onde ⁠ id ⁠ é o ID da categoria.
    """
    comando = mensagem.text.strip()

    categoria_id = comando[1:]

    if categoria_id:
        bot.reply_to(mensagem, f"✅ Você escolheu a categoria ID: {categoria_id}.")
        buscar_sugestoes(categoria_id, mensagem)
    else:
        bot.reply_to(mensagem, "❌ Erro: ID de categoria não encontrado.")


def buscar_sugestoes(categoria_id, mensagem):
    """
    Busca produtos na categoria escolhida pelo usuário.
    """
    bot.reply_to(mensagem, f"🔍 Buscando produtos na categoria ID: {categoria_id}...")

    try:

        produtos_url = f"https://api.mercadolibre.com/sites/MLB/search?category={categoria_id}"
        produtos_response = requests.get(produtos_url)
        produtos_response.raise_for_status()
        resultados = produtos_response.json()

        if 'results' in resultados and resultados['results']:
            sugestoes = []
            for item in resultados['results'][:5]:
                titulo = item['title']
                preco = item['price']
                link = item['permalink']
                sugestoes.append(f"🛒 {titulo} - R$ {preco:.2f}\n🔗 {link}")

            bot.reply_to(mensagem, "Aqui estão algumas sugestões: ✨\n" + "\n".join(sugestoes))
        else:
            bot.reply_to(mensagem, "😔 Não foram encontrados produtos nessa categoria.")
    except requests.exceptions.RequestException as e:
        bot.reply_to(mensagem, f"⚠️ Erro ao buscar sugestões: {str(e)}")
    start(mensagem)

@bot.message_handler(commands=['opcao4'])
def alerta_preco_baixo(mensagem):
    bot.reply_to(mensagem, "🔔 Qual produto você gostaria de receber alertas de preço baixo? 🛒")
    bot.register_next_step_handler(mensagem, definir_alerta)

def definir_alerta(mensagem):
    produto = mensagem.text
    if not produto:
        bot.reply_to(mensagem, "⚠️ Por favor, insira um nome válido para o produto. Exemplo: 'Cadeira' ou 'Smartphone'.")
        return

    bot.reply_to(mensagem, f"💸 Agora, informe o preço máximo que deseja pagar pelo produto '{produto}':")
    bot.register_next_step_handler(mensagem, salvar_alerta, produto)

def salvar_alerta(mensagem, produto):
    try:
        preco_desejado = float(mensagem.text)
        user_id = mensagem.from_user.id
        user_name = mensagem.from_user.first_name

        alerta_existente = alerta_collection.find_one({"user_id": user_id, "produto": produto})

        if alerta_existente:
            alerta_collection.update_one(
                {"user_id": user_id, "produto": produto},
                {"$set": {"preco_desejado": preco_desejado, "criado_em": datetime.datetime.utcnow()}}
            )
            bot.reply_to(mensagem, f"🔔 Alerta atualizado para o produto '{produto}' com preço máximo de R$ {preco_desejado:.2f}! 💰")
        else:
            alerta = {
                "user_id": user_id,
                "user_name": user_name,
                "produto": produto,
                "preco_desejado": preco_desejado,
                "criado_em": datetime.datetime.utcnow()
            }

            alerta_collection.insert_one(alerta)

            bot.reply_to(mensagem, f"🎉 Alerta configurado para o produto '{produto}' com preço máximo de R$ {preco_desejado:.2f}! 🎯")
    except ValueError:
        bot.reply_to(mensagem, "⚠️ Por favor, insira um valor numérico válido para o preço. Exemplo: '150' ou '300.50'.")
    except Exception as e:
        bot.reply_to(mensagem, f"❌ Erro ao salvar alerta no banco: {str(e)}")
    start(mensagem)

def verificar_alertas():
    alertas = alerta_collection.find()

    for alerta in alertas:
        user_id = alerta["user_id"]
        produto = alerta["produto"]
        preco_desejado = alerta["preco_desejado"]

        preco_atual, link = obter_preco_produto(produto)
        if preco_atual is not None:
            if preco_atual <= preco_desejado:
                bot.send_message(user_id, f"🎉 Alerta de preço! 🎉 O preço do produto '{produto}' caiu para R$ {preco_atual:.2f}, que está abaixo do seu preço desejado de R$ {preco_desejado:.2f}. Confira aqui: {link} 🔗")
                alerta_collection.delete_one({"user_id": user_id, "produto": produto})
    time.sleep(60)

def obter_preco_produto(produto):
    try:
        url = f"https://api.mercadolibre.com/sites/MLB/search?q={produto}"
        response = requests.get(url)
        response.raise_for_status()
        resultados = response.json()

        if 'results' in resultados and resultados['results']:
            preco = resultados['results'][0]['price']
            link_produto = resultados['results'][0]['permalink']

            return preco, link_produto
        else:
            return None, None
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao buscar preço do produto: {e}")

def verificar_alertas_periodicamente():
    while True:
        verificar_alertas()
        time.sleep(60)

alerta_thread = threading.Thread(target=verificar_alertas_periodicamente)
alerta_thread.daemon = True
alerta_thread.start()

bot.polling()

@bot.message_handler(func=lambda message: True)
def resposta_padrao(message):
    bot.reply_to(message, "Digite /ajuda para ver as opções disponíveis. 📲")

@bot.message_handler(commands=['opcao5'])
def sair(mensagem):
    bot.reply_to(mensagem, "👋 Até logo! Espero te ajudar novamente em breve. 😊")