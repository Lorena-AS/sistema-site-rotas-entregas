from fpdf import FPDF
import marca

AZUL_MARINHO = (15, 42, 74)
AZUL = (11, 92, 168)
CINZA = (91, 107, 130)
CINZA_CLARO = (227, 232, 239)
EXTENSOES_LOGO_PDF = (".png", ".jpg", ".jpeg")
#______________________________________________________________________________________________________________________#
#Troca os caracteres que a fonte do PDF não tem por "?" (evita erro com nomes e endereços fora do comum)

def limpar(texto):
    texto = str(texto)
    trocas = {"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-"}
    for caractere, substituto in trocas.items():
        texto = texto.replace(caractere, substituto)
    return texto.encode("latin-1", "replace").decode("latin-1")
#______________________________________________________________________________________________________________________#
#Modelo de página: o rodapé se repete em todas as páginas

class PdfRota(FPDF):
    texto_rodape = ""

    def footer(self):
        self.set_y(-15)
        self.set_draw_color(*CINZA_CLARO)
        self.line(15, self.get_y() - 2, 195, self.get_y() - 2)
        self.set_font("Helvetica", size=8)
        self.set_text_color(*CINZA)
        self.cell(90, 8, self.texto_rodape)
        self.cell(90, 8, f"Página {self.page_no()}", align="R")
#______________________________________________________________________________________________________________________#
#Monta o PDF da rota e devolve o arquivo em bytes (nada é salvo no computador)

def montar_pdf(dia_semana, data, saida, retorno, paradas, usuario, gerada_em, dados_marca=None):
    if dados_marca is None:
        dados_marca = marca.marca_padrao()
    caminho_logo = dados_marca["caminho_logo"]

    pdf = PdfRota(format="A4")
    pdf.texto_rodape = limpar(f"Gerado por {usuario} em {gerada_em}")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(True, margin=22)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*AZUL_MARINHO)
    if caminho_logo is not None and caminho_logo.lower().endswith(EXTENSOES_LOGO_PDF):
        pdf.image(caminho_logo, x=15, y=pdf.get_y(), h=10)
        pdf.cell(90, 10, "")
    else:
        pdf.cell(90, 10, limpar(dados_marca["nome_curto"]))
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(90, 8, "Rota de entregas", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(*CINZA)
    pdf.cell(180, 6, limpar(f"{dia_semana}, {data}"), align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)
    pdf.set_draw_color(*CINZA_CLARO)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(5)

    pdf.set_text_color(*AZUL_MARINHO)
    resumo = [("Saída: ", saida), ("Retorno previsto: ", retorno), ("Entregas: ", str(len(paradas)))]
    for rotulo, valor in resumo:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(pdf.get_string_width(rotulo) + 1, 7, rotulo)
        pdf.set_font("Helvetica", size=11)
        pdf.cell(45, 7, limpar(valor))
    pdf.ln(12)

    numero = 1
    for parada in paradas:
        titulo = parada["titulo"]
        if parada["tipo"] == "transportadora":
            titulo += "  ·  Transportadora"

        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(*AZUL)
        pdf.cell(12, 7, str(numero))
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*AZUL_MARINHO)
        pdf.multi_cell(168, 6, limpar(titulo), new_x="LMARGIN", new_y="NEXT")
        for linha in [parada["detalhe"], parada["cliente"]]:
            if linha != "":
                pdf.set_x(27)
                pdf.set_font("Helvetica", size=10)
                pdf.set_text_color(*AZUL_MARINHO)
                pdf.multi_cell(168, 5, limpar(linha), new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(27)
        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(*CINZA)
        pdf.multi_cell(168, 5, limpar(parada["endereco"]), new_x="LMARGIN", new_y="NEXT")

        for item in parada["itens"]:
            pdf.ln(1)
            pdf.set_x(31)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*AZUL_MARINHO)
            pdf.multi_cell(164, 5, limpar("- " + item["titulo"]), new_x="LMARGIN", new_y="NEXT")
            if item["detalhe"] != "":
                pdf.set_x(34)
                pdf.set_font("Helvetica", size=10)
                pdf.set_text_color(*CINZA)
                pdf.multi_cell(161, 5, limpar(item["detalhe"]), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        pdf.set_draw_color(*CINZA_CLARO)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(3)
        numero += 1

    altura_assinaturas = 40
    if pdf.get_y() > pdf.h - 22 - altura_assinaturas:
        pdf.add_page()

    y_linha = pdf.h - 22 - 20
    pdf.set_draw_color(*AZUL_MARINHO)
    pdf.line(15, y_linha, 95, y_linha)
    pdf.line(115, y_linha, 195, y_linha)
    pdf.set_y(y_linha + 1)
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(*CINZA)
    pdf.set_x(15)
    pdf.cell(80, 5, "Expedição", align="C")
    pdf.set_x(115)
    pdf.cell(80, 5, "Motorista", align="C")

    pdf.set_y(y_linha + 11)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*AZUL_MARINHO)
    pdf.cell(0, 5, limpar(dados_marca["razao_social"]), align="C")

    return bytes(pdf.output())
#______________________________________________________________________________________________________________________#