import streamlit as st
import pandas as pd
from PIL import Image, ImageStat
import piexif
from datetime import datetime
import os
import io
import zipfile
from scipy import stats

# Dependências para gerar o PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="Laboratório Virtual - Teste t e Colorimetria", layout="wide")

st.title("🔬 Laboratório de Colorimetria e Teste t de Student")
st.write("Realize as medições das réplicas, envie os registros fotográficos e insira seus cálculos estatísticos.")

# --- 1. IDENTIFICAÇÃO DO ESTUDANTE ---
st.sidebar.header("Identificação do Aluno")
nome_aluno = st.sidebar.text_input("Nome Completo:")
matricula_input = st.sidebar.text_input("Matrícula (apenas números):")

if not nome_aluno or not matricula_input or not matricula_input.isdigit():
    st.warning("⚠️ Preencha seu nome completo e matrícula na barra lateral para liberar as etapas do exercício.")
    st.stop()

matricula = int(matricula_input)
ultimos_digitos = matricula % 100
ref_kno4 = 100 + ultimos_digitos

# --- FUNÇÃO AUXILIAR: PROCESSAMENTO DA IMAGEM E EXIF ---
def processar_amostra(file_uploader_obj):
    if file_uploader_obj is not None:
        img = Image.open(file_uploader_obj)
        
        # Leitura de EXIF
        data_exif = "EXIF não encontrado"
        try:
            exif_dict = piexif.load(file_uploader_obj.getvalue())
            if "Exif" in exif_dict and piexif.ExifIFD.DateTimeOriginal in exif_dict["Exif"]:
                raw_date = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode('utf-8')
                data_exif = datetime.strptime(raw_date, '%Y:%m:%d %H:%M:%S').strftime('%d/%m/%Y %H:%M:%S')
        except Exception:
            pass
            
        # Extração do Canal Vermelho Médio (R)
        rgb_img = img.convert('RGB')
        stat = ImageStat.Stat(rgb_img)
        r_medio = round(stat.mean[0], 2)
        
        return img, r_medio, data_exif
    return None, None, None

# --- ETAPA 1: ENVIO DAS TRÊS RÉPLICAS ---
st.header("1. Análise Visual das Réplicas")
st.info(f"📍 **Seu valor de referência individual ($\mu_0$):** `{ref_kno4}`")

col1, col2, col3 = st.columns(3)

# Cor base com variação pela matrícula
base_r = 130 + (matricula % 20) 

# Criando imagens sintéticas 200x200 px no formato RGB
arr_a = np.full((200, 200, 3), [base_r, 45, 80], dtype=np.uint8)
arr_b = np.full((200, 200, 3), [base_r - 5, 48, 78], dtype=np.uint8)
arr_c = np.full((200, 200, 3), [base_r + 4, 42, 82], dtype=np.uint8)

img_a, img_b, img_c = Image.fromarray(arr_a), Image.fromarray(arr_b), Image.fromarray(arr_c)

with col1:
    st.subheader("Réplica A")
    st.image(img_a, use_column_width=True)
    r_a = float(base_r)
    st.success(f"**R Médio:** {r_a}")

with col2:
    st.subheader("Réplica B")
    st.image(img_b, use_column_width=True)
    r_b = float(base_r - 5)
    st.success(f"**R Médio:** {r_b}")

with col3:
    st.subheader("Réplica C")
    st.image(img_c, use_column_width=True)
    r_c = float(base_r + 4)
    st.success(f"**R Médio:** {r_c}")

# Só avança se as 3 fotos forem enviadas
if r_a is not None and r_b is not None and r_c is not None:
    st.divider()
    
    # --- ETAPA 2: MANUSCRITO DOS CÁLCULOS ---
    st.header("2. Upload da Folha de Cálculos Manuscrita")
    st.write("Realize os cálculos da **Média**, **Desvio Padrão**, **t calculado** e **t observado/crítico** no papel. Tire uma foto visível e envie abaixo:")
    file_manuscrito = st.file_uploader("Foto da folha de cálculos manuscritos", type=["jpg", "jpeg", "png"], key="manuscrito")
    
    if file_manuscrito:
        img_manuscrito = Image.open(file_manuscrito)
        st.image(img_manuscrito, caption="Folha de Cálculos Enviada", width=400)
        
        st.divider()
        
        # --- ETAPA 3: INSERÇÃO DOS RESULTADOS NO SISTEMA ---
        st.header("3. Inserção dos Resultados Estatísticos")
        st.write("Transcreva abaixo os valores obtidos no seu manuscrito:")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            media_aluno = st.number_input("Média ($\bar{x}$):", step=0.01)
        with c2:
            desvio_aluno = st.number_input("Desvio Padrão ($s$):", step=0.01)
        with c3:
            t_calc_aluno = st.number_input("$t$ calculado ($t_{calc}$):", step=0.001)
        with c4:
            t_obs_aluno = st.number_input("$t$ observado/tabelado ($t_{crit}$):", step=0.001)

        conclusao_aluno = st.radio(
            "Conclusão do Teste t (nível de significância de 5%):",
            ["Selecione...", "Existe diferença estatística significativa", "Não existe diferença estatística significativa"]
        )

        # --- FUNÇÃO PARA GERAR O PDF CONSOLIDADO DO ALUNO ---
        def gerar_pdf_relatorio(nome, mat, r_a, r_b, r_c, media, desvio, t_calc, t_obs, conc, file_script):
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            elements = []
            styles = getSampleStyleSheet()

            # Título
            elements.append(Paragraph(f"<b>Relatório de Atividade Prática - Teste t</b>", styles['Title']))
            elements.append(Spacer(1, 12))
            
            # Cabeçalho
            info_text = f"<b>Aluno:</b> {nome}<br/><b>Matrícula:</b> {mat}<br/><b>Data do Envio:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            elements.append(Paragraph(info_text, styles['Normal']))
            elements.append(Spacer(1, 12))

            # Tabela de Dados Extraídos pelo Sistema
            dados_tabela = [
                ["Réplica", "Valor de R Médio", "Data EXIF da Foto"],
                ["Réplica A", str(r_a), str(exif_a)],
                ["Réplica B", str(r_b), str(exif_b)],
                ["Réplica C", str(r_c), str(exif_c)],
            ]
            t = Table(dados_tabela, colWidths=[100, 150, 200])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            elements.append(t)
            elements.append(Spacer(1, 15))

            # Resultados do Aluno
            res_text = f"""
            <b>Valor de Referência (&mu;<sub>0</sub>):</b> {ref_kno4}<br/>
            <b>Média Calculada (&bar;x):</b> {media}<br/>
            <b>Desvio Padrão (s):</b> {desvio}<br/>
            <b>t Calculado:</b> {t_calc} | <b>t Observado:</b> {t_obs}<br/>
            <b>Conclusão:</b> {conc}
            """
            elements.append(Paragraph(res_text, styles['Normal']))
            elements.append(Spacer(1, 15))

            # Adicionar imagem do manuscrito
            elements.append(Paragraph("<b>Comprovação dos Cálculos Manuscritos:</b>", styles['Heading2']))
            elements.append(Spacer(1, 5))
            
            # Redimensiona imagem mantendo proporção no PDF
            img_m = Image.open(file_script)
            img_m.thumbnail((400, 400))
            img_m_path = f"temp_{mat}.jpg"
            img_m.save(img_m_path)
            
            elements.append(RLImage(img_m_path, width=350, height=350))

            doc.build(elements)
            
            if os.path.exists(img_m_path):
                os.remove(img_m_path)
                
            buffer.seek(0)
            return buffer.getvalue()

        # --- BOTÃO DE SUBMISSÃO FINAL ---
        if st.button("🚀 Enviar Atividade Completa"):
            if conclusao_aluno == "Selecione...":
                st.error("Por favor, selecione a conclusão do seu teste estatístico.")
            else:
                # 1. Gerar arquivo PDF do aluno
                pdf_bytes = gerar_pdf_relatorio(
                    nome_aluno, matricula, r_a, r_b, r_c, 
                    media_aluno, desvio_aluno, t_calc_aluno, t_obs_aluno, 
                    conclusao_aluno, file_manuscrito
                )
                
                # Salvar PDF na pasta relatorios/
                os.makedirs("relatorios", exist_ok=True)
                pdf_filename = f"relatorios/{nome_aluno.replace(' ', '_')}_{matricula}.pdf"
                with open(pdf_filename, "wb") as f:
                    f.write(pdf_bytes)

                # 2. Salvar Registro na Planilha CSV
                registro = {
                    "Nome": nome_aluno.strip().title(),
                    "Matricula": matricula,
                    "DataEnvio": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "Ref_KMnO4": ref_kno4,
                    "R_A": r_a, "R_B": r_b, "R_C": r_c,
                    "Media_Aluno": media_aluno,
                    "Desvio_Aluno": desvio_aluno,
                    "T_Calc_Aluno": t_calc_aluno,
                    "T_Obs_Aluno": t_obs_aluno,
                    "Conclusao_Aluno": conclusao_aluno,
                    "Arquivo_PDF": pdf_filename
                }

                csv_file = "respostas_alunos.csv"
                if os.path.exists(csv_file):
                    df = pd.read_csv(csv_file)
                    df = pd.concat([df, pd.DataFrame([registro])], ignore_index=True)
                else:
                    df = pd.DataFrame([registro])

                # Ordena e salva sempre alfabeticamente
                df = df.sort_values(by="Nome", ascending=True)
                df.to_csv(csv_file, index=False)

                st.success("🎉 Atividade enviada com sucesso! O relatório PDF único foi gerado e registrado.")

# --- ÁREA RESTRITA DO PROFESSOR (PAINEL DE CONTROLE) ---
st.sidebar.write("---")
if st.sidebar.checkbox("🔒 Acesso do Professor"):
    senha = st.sidebar.text_input("Senha:", type="password")
    if senha == "prof123": # Altere para sua senha
        st.header("📊 Painel do Professor - Downloads e Registros")
        
        if os.path.exists("respostas_alunos.csv"):
            df_prof = pd.read_csv("respostas_alunos.csv")
            
            # Exibe Tabela em Ordem Alfabética
            st.subheader("Lista de Alunos Respondentes (Ordem Alfabética)")
            st.dataframe(df_prof)
            
            c_down1, c_down2 = st.columns(2)
            
            # Botão 1: Baixar Planilha CSV
            with c_down1:
                csv_data = df_prof.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar Planilha CSV (Ordenada)",
                    data=csv_data,
                    file_name="lista_alunos_respostas.csv",
                    mime="text/csv"
                )
            
            # Botão 2: Baixar Todos os PDFs em um arquivo ZIP
            with c_down2:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for root, dirs, files in os.walk("relatorios"):
                        for file in files:
                            zf.write(os.path.join(root, file), file)
                
                zip_buffer.seek(0)
                st.download_button(
                    label="📦 Baixar Todos os PDFs em ZIP",
                    data=zip_buffer,
                    file_name="relatorios_alunos_pdf.zip",
                    mime="application/zip"
                )
        else:
            st.info("Nenhuma submissão registrada até o momento.")
    elif senha:
        st.sidebar.error("Senha incorreta.")
