import base64
import shutil
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import marca
import pdf_rota

SVG_SIMPLES = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>'
SVG_COM_SCRIPT = '<svg xmlns="http://www.w3.org/2000/svg"><script>alert("oi")</script><rect width="5" height="5"/></svg>'
PNG_1X1 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
#______________________________________________________________________________________________________________________#
#Cada teste usa uma pasta temporária como "pasta do projeto" e um st.secrets simulado

class TesteMarca(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp()).resolve()
        self.fora = Path(tempfile.mkdtemp()).resolve()
        self.troca_pasta = mock.patch.object(marca, "PASTA_PROJETO", self.pasta)
        self.troca_pasta.start()
        self.usar_secrets({})

    def tearDown(self):
        self.troca_st.stop()
        self.troca_pasta.stop()
        shutil.rmtree(self.pasta, ignore_errors=True)
        shutil.rmtree(self.fora, ignore_errors=True)

    def usar_secrets(self, secrets):
        if hasattr(self, "troca_st"):
            self.troca_st.stop()
        self.troca_st = mock.patch.object(marca, "st", types.SimpleNamespace(secrets=secrets))
        self.troca_st.start()

    def criar(self, nome, conteudo):
        caminho = self.pasta / nome
        caminho.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(conteudo, str):
            caminho.write_text(conteudo, encoding="utf-8")
        else:
            caminho.write_bytes(conteudo)
        return caminho
#______________________________________________________________________________________________________________________#
#Valores padrão

class TestePadrao(TesteMarca):
    def test_sem_secao_marca(self):
        dados = marca.ler_marca()
        self.assertEqual(dados["nome_curto"], "Empresa Exemplo")
        self.assertEqual(dados["razao_social"], "Empresa Exemplo Ltda.")
        self.assertIsNone(dados["caminho_logo"])
        self.assertEqual(marca.logo_em_img(30), "Empresa Exemplo")

    def test_campos_vazios(self):
        self.usar_secrets({"marca": {"nome_curto": "  ", "razao_social": "", "caminho_logo": ""}})
        self.assertEqual(marca.ler_marca(), marca.marca_padrao())

    def test_secrets_com_erro(self):
        class SecretsQuebrado:
            def get(self, chave, padrao=None):
                raise FileNotFoundError("sem secrets")
        self.usar_secrets(SecretsQuebrado())
        self.assertEqual(marca.ler_marca(), marca.marca_padrao())

    def test_rodape_padrao(self):
        self.assertEqual(marca.texto_rodape(2026), "© 2026 Empresa Exemplo Ltda. Todos os direitos reservados.")
#______________________________________________________________________________________________________________________#
#Caminhos de logo que devem ser recusados

class TesteCaminhoInseguro(TesteMarca):
    def caminho_aceito(self, caminho):
        self.usar_secrets({"marca": {"caminho_logo": caminho}})
        return marca.ler_marca()["caminho_logo"]

    def test_com_dois_pontos(self):
        (self.fora / "logo.svg").write_text(SVG_SIMPLES, encoding="utf-8")
        relativo = "../" + self.fora.name + "/logo.svg"
        self.assertTrue((self.pasta / relativo).resolve().is_file())
        self.assertIsNone(self.caminho_aceito(relativo))

    def test_absoluto_fora_do_projeto(self):
        arquivo = self.fora / "logo.png"
        arquivo.write_bytes(PNG_1X1)
        self.assertIsNone(self.caminho_aceito(str(arquivo)))

    def test_extensao_txt(self):
        self.criar("marca/logo.txt", "texto")
        self.assertIsNone(self.caminho_aceito("marca/logo.txt"))

    def test_extensao_exe(self):
        self.criar("marca/logo.exe", b"MZ")
        self.assertIsNone(self.caminho_aceito("marca/logo.exe"))

    def test_arquivo_inexistente(self):
        self.assertIsNone(self.caminho_aceito("marca/nao_existe.svg"))

    def test_pasta_com_extensao_de_imagem(self):
        (self.pasta / "pasta.svg").mkdir()
        self.assertIsNone(self.caminho_aceito("pasta.svg"))

    def test_valor_que_nao_e_texto(self):
        self.assertIsNone(self.caminho_aceito(123))

    def test_logo_em_img_sem_logo_nao_mostra_caminho(self):
        self.usar_secrets({"marca": {"nome_curto": "Teste", "caminho_logo": "../segredo/logo.svg"}})
        html = marca.logo_em_img(30)
        self.assertEqual(html, "Teste")
        self.assertNotIn("segredo", html)
#______________________________________________________________________________________________________________________#
#Logo válida

class TesteLogoValida(TesteMarca):
    def test_svg_vira_data_uri(self):
        self.criar("marca/logo.svg", SVG_SIMPLES)
        self.usar_secrets({"marca": {"nome_curto": "Teste", "caminho_logo": "marca/logo.svg"}})
        dados = marca.ler_marca()
        self.assertEqual(dados["caminho_logo"], str((self.pasta / "marca/logo.svg").resolve()))
        html = marca.logo_em_img(30)
        self.assertTrue(html.startswith('<img src="data:image/svg+xml;base64,'))
        self.assertIn('alt="Teste"', html)
        self.assertIn("height: 30px", html)

    def test_svg_com_script_nao_fica_inline(self):
        self.criar("marca/logo.svg", SVG_COM_SCRIPT)
        self.usar_secrets({"marca": {"caminho_logo": "marca/logo.svg"}})
        html = marca.logo_em_img(30)
        self.assertNotIn("<script", html)
        self.assertNotIn("<svg", html)
        self.assertNotIn("alert", html)
        conteudo = html.split("base64,")[1].split('"')[0]
        self.assertEqual(base64.b64decode(conteudo).decode("utf-8"), SVG_COM_SCRIPT)

    def test_png_e_jpg(self):
        self.criar("logo.png", PNG_1X1)
        self.criar("logo.JPEG", b"\xff\xd8\xff")
        self.usar_secrets({"marca": {"caminho_logo": "logo.png"}})
        self.assertTrue(marca.logo_em_data_uri().startswith("data:image/png;base64,"))
        self.usar_secrets({"marca": {"caminho_logo": "logo.JPEG"}})
        self.assertTrue(marca.logo_em_data_uri().startswith("data:image/jpeg;base64,"))
#______________________________________________________________________________________________________________________#
#Escape do nome e da razão social

class TesteEscape(TesteMarca):
    def test_nome_com_html_sem_logo(self):
        self.usar_secrets({"marca": {"nome_curto": "<b>x</b>"}})
        self.assertEqual(marca.logo_em_img(30), "&lt;b&gt;x&lt;/b&gt;")

    def test_nome_com_html_no_alt(self):
        self.criar("logo.svg", SVG_SIMPLES)
        self.usar_secrets({"marca": {"nome_curto": '<b>x</b>" onerror="y', "caminho_logo": "logo.svg"}})
        html = marca.logo_em_img(30)
        self.assertNotIn("<b>", html)
        self.assertIn('alt="&lt;b&gt;x&lt;/b&gt;&quot; onerror=&quot;y"', html)

    def test_razao_social_com_html(self):
        self.usar_secrets({"marca": {"razao_social": "<i>Firma</i> & Cia"}})
        texto = marca.texto_rodape(2026)
        self.assertEqual(texto, "© 2026 &lt;i&gt;Firma&lt;/i&gt; &amp; Cia. Todos os direitos reservados.")
#______________________________________________________________________________________________________________________#
#PDF da rota

class TestePdf(TesteMarca):
    PARADAS = [{"titulo": "Cliente A", "tipo": "cliente", "detalhe": "2 volumes", "cliente": "", "endereco": "Rua 1",
                "itens": []}]

    def gerar(self, dados_marca):
        return pdf_rota.montar_pdf("segunda-feira", "16/11/2026", "08:00", "10:00", self.PARADAS, "teste",
                                   "16/11/2026 08:00", dados_marca)

    def test_sem_marca_usa_padrao(self):
        arquivo = pdf_rota.montar_pdf("segunda-feira", "16/11/2026", "08:00", "10:00", self.PARADAS, "teste",
                                      "16/11/2026 08:00")
        self.assertTrue(arquivo.startswith(b"%PDF"))
        self.assertNotIn(b"/Subtype /Image", arquivo)

    def test_logo_png_entra_no_pdf(self):
        self.criar("logo.png", PNG_1X1)
        self.usar_secrets({"marca": {"caminho_logo": "logo.png"}})
        arquivo = self.gerar(marca.ler_marca())
        self.assertIn(b"/Subtype /Image", arquivo)

    def test_logo_svg_vira_texto(self):
        self.criar("logo.svg", SVG_SIMPLES)
        self.usar_secrets({"marca": {"caminho_logo": "logo.svg"}})
        arquivo = self.gerar(marca.ler_marca())
        self.assertTrue(arquivo.startswith(b"%PDF"))
        self.assertNotIn(b"/Subtype /Image", arquivo)


if __name__ == "__main__":
    unittest.main()
