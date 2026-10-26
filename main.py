import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image, ImageStat
import piexif
from datetime import datetime
import os
import io
import zipfile

# Suporte nativo a imagens de iPhone (.HEIC)
from pillow_heif import register_heif_opener
register_heif_opener()

# Dependências do ReportLab para geração do PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

st.set_page_config(page_title="Laboratório Virtual - Teste t e Colorimetria", layout="wide")

st.title("🔬 Laboratório de Colorimetria e Teste t de Student")
st.write("Analise as réplicas na tela, capture cada foto com o celular, realize os cálculos no papel e envie os registros.")

# --- 1. IDENTIFICAÇÃO DO ESTUDANTE ---
st.sidebar.header("Identificação do Aluno")
nome_aluno = st.sidebar.text_input("Nome Completo:")
matricula_input = st.sidebar.text_input("Matrícula (apenas números):")

if not nome_aluno or not matricula_input or not matricula_input.isdigit():
    st.warning("⚠️ Preencha seu nome completo e apenas números da matrícula na barra lateral para iniciar a atividade.")
    st.stop()

matricula = int(matricula_input)
ultimos_digitos = matricula % 100
ref_kno4 = 120 + ultimos_digitos

# --- FUNÇÃO AUXILIAR: PROCESSAMENTO DA FOTO DO ALUNO E EXIF ---
def processar_foto_aluno(file_uploader_obj):
    if file_uploader_obj is not None:
        img = Image.open(file_uploader_obj)
        
        # Leitura dos Metadados EXIF
        data_exif = "Sem registro EXIF"
        try:
            exif_dict = piexif.load(file_uploader_obj.getvalue())
            if "Exif" in exif_dict and piexif.ExifIFD.DateTimeOriginal in exif_dict["Exif"]:
                raw_date = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode('utf-8')
                data_exif = datetime.strptime(raw_date, '%Y:%m:%d %H:%M:%S').strftime('%d/%m/%Y %H:%M:%S')
        except Exception:
            pass
            
        # Extração da Média do Canal Vermelho (R) da foto enviada
        rgb_img = img.convert('RGB')
        stat = ImageStat.Stat(rgb_img)
        r_medio = round(stat.mean[0], 2)
        
        return img, r_medio, data_exif
    return None, None, None

# --- ETAPA 1: EXIBIÇÃO DAS RÉPLICAS GERADAS NO CÓDIGO ---
st.header("1. Amostras para Análise Visual")
st.info(f"📍 **Seu valor de referência individual ($\mu_0$):** `{ref_kno4}` (Fórmula: 100 + últimos 2 dígitos da matrícula)")

col_disp1, col_disp2, col_disp3 = st.columns(3)

# Gerando matrizes sintéticas únicas por matrícula (sem exibir os valores brutos de R)
base_r = 125 + (matricula % 25)
arr_a = np.full((180, 180, 3), [base_r, 40, 85], dtype=np.uint8)
arr_b = np.full((180, 180, 3), [base_r - 6, 42, 80], dtype=np.uint8)
arr_c = np.full((180, 180, 3), [base_r + 5, 38, 88], dtype=np.uint8)

with col_disp1:
    st.subheader("Réplica A")
    st.image(Image.fromarray(arr_a), use_column_width=True)

with col_disp2:
    st.subheader("Réplica B")
    st.image(Image.fromarray(arr_b), use_column_width=True)

with col_disp3:
    st.subheader("Réplica C")
    st.image(Image.fromarray(arr_c), use_column_width=True)

st.divider()

# --- ETAPA 2: UPLOAD DAS FOTOS TIRADAS PELO CELULAR ---
st.header("2. Validação Fotográfica e Medição de R")
st.write("Use a câmera do celular para fotografar cada réplica exibida na tela do computador e envie nos campos abaixo:")

col_up1, col_up2, col_up3 = st.columns(3)

with col_up1:
    st.subheader("Upload Réplica A")
    file_a = st.file_uploader("Foto da Réplica A (Celular)", type=["jpg", "jpeg", "png", "heic"], key="up_a")
    img_a, r_a, exif_a = processar_foto_aluno(file_a)
    if img_a:
        st.image(img_a, use_column_width=True)
        st.success(f"**R Médio Lido:** {r_a}")
        st.caption(f"Data Foto: {exif_a}")

with col_up2:
    st.subheader("Upload Réplica B")
    file_b = st.file_uploader("Foto da Réplica B (Celular)", type=["jpg", "jpeg", "png", "heic"], key="up_b")
    img_b, r_b, exif_b = processar_foto_aluno(file_b)
    if img_b:
        st.image(img_b, use_column_width=True)
        st.success(f"**R Médio Lido:** {r_b}")
        st.caption(f"Data Foto: {exif_b}")

with col_up3:
    st.subheader("Upload Réplica C")
    file_c = st.file_uploader("Foto da Réplica C (Celular)", type=["jpg", "jpeg", "png", "heic"], key="up_c")
    img_c, r_c, exif_c = processar_foto_aluno(file_c)
    if img_c:
        st.image(img_c, use_column_width=True)
        st.success(f"**R Médio Lido:** {r_c}")
        st.caption(f"Data Foto: {exif_c}")

# Libera as etapas seguintes apenas se as 3 fotos das réplicas forem enviadas
if r_a is not None and r_b is not None and r_c is not None:
    st.divider()
    
    # --- ETAPA 3: UPLOAD DO MANUSCRITO DE CÁLCULOS ---
    st.header("3. Resolução e Cálculos Manuscritos")
    st.write(f"Utilize as médias obtidas (**$R_A = {r_a}$**, **$R_B = {r_b}$**, **$R_C = {r_c}$**) e a referência **$\mu_0 = {ref_kno4}$** para calcular em uma folha de papel:")
    st.markdown("- Média ($\bar{x}$) e Desvio Padrão ($s$)\n- Valor de $t$ calculado ($t_{calc}$) e $t$ observado/crítico ($t_{crit}$)\n- Conclusão da hipótese estatística")
    
    file_manuscrito = st.file_uploader("Envie a foto da folha com os cálculos manuscritos", type=["jpg", "jpeg", "png", "heic"], key="up_manuscrito")
    
    if file_manuscrito:
        img_manuscrito = Image.open(file_manuscrito)
        st.image(img_manuscrito, caption="Manuscrito Registrado", width=350)
        st.divider()
        
        # --- ETAPA 4: INSERÇÃO DOS RESULTADOS E CONCLUSÃO ---
        st.header("4. Transcrição dos Resultados")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            media_aluno = st.number_input("Média ($\bar{x}$):", step=0.01)
        with c2:
            desvio_aluno = st.number_input("Desvio Padrão ($s$):", step=0.01)
        with c3:
            t_calc_aluno = st.number_input("$t$ calculado ($t_{calc}$):", step=0.001)
        with c4:
            t_obs_aluno = st.number_input("$t$ observado ($t_{crit}$):", step=0.001)

        conclusao_aluno = st.radio(
            "Resultado da análise estatística (nível de significância $\alpha = 0,05$):",
            ["Selecione...", "Existe diferença estatística significativa", "Não existe diferença estatística significativa"]
        )

        # --- GERADOR DE RELATÓRIO PDF ---
        def gerar_pdf_relatorio(nome, mat, r_a, r_b, r_c, media, desvio, t_calc, t_obs, conc, file_script):
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            elements = []
            styles = getSampleStyleSheet()

            elements.append(Paragraph("<b>Relatório de Atividade Prática - Teste t de Student</b>", styles['Title']))
            elements.append(Spacer(1, 10))
            
            info = f"<b>Aluno:</b> {nome}<br/><b>Matrícula:</b> {mat}<br/><b>Data de Envio:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            elements.append(Paragraph(info, styles['Normal']))
            elements.append(Spacer(1, 12))

            # Tabela com as leituras das fotos
            data_tab = [
                ["Amostra", "R Médio Extraído", "Metadados EXIF"],
                ["Réplica A", str(r_a), str(exif_a)],
                ["Réplica B", str(r_b), str(exif_b)],
                ["Réplica C", str(r_c), str(exif_c)]
            ]
            t = Table(data_tab, colWidths=[100, 130, 220])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            elements.append(t)
            elements.append(Spacer(1, 12))

            resumo = f"""
            <b>Referência (&mu;<sub>0</sub>):</b> {ref_kno4}<br/>
            <b>Média (&bar;x):</b> {media} | <b>Desvio Padrão (s):</b> {desvio}<br/>
            <b>t Calculado:</b> {t_calc} | <b>t Observado:</b> {t_obs}<br/>
            <b>Conclusão do Aluno:</b> {conc}
            """
            elements.append(Paragraph(resumo, styles['Normal']))
            elements.append(Spacer(1, 12))

            # Ajuste e inserção da foto do manuscrito no PDF
            elements.append(Paragraph("<b>Comprovação dos Cálculos Manuscritos:</b>", styles['Heading2']))
            elements.append(Spacer(1, 5))
            
            img_m = Image.open(file_script).convert("RGB")
            img_m.thumbnail((400, 400))
            temp_path = f"temp_{mat}.jpg"
            img_m.save(temp_path)
            
            elements.append(RLImage(temp_path, width=320, height=320))

            doc.build(elements)
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            buffer.seek(0)
            return buffer.getvalue()

        # --- SUBMISSÃO FINAL ---
        if st.button("🚀 Enviar Atividade Completa"):
            if conclusao_aluno == "Selecione...":
                st.error("Por favor, selecione a conclusão da sua análise antes de enviar.")
            else:
                # 1. Gera o PDF único
                pdf_bytes = gerar_pdf_relatorio(
                    nome_aluno, matricula, r_a, r_b, r_c, 
                    media_aluno, desvio_aluno, t_calc_aluno, t_obs_aluno, 
                    conclusao_aluno, file_manuscrito
                )
                
                os.makedirs("relatorios", exist_ok=True)
                pdf_path = f"relatorios/{nome_aluno.replace(' ', '_')}_{matricula}.pdf"
                with open(pdf_path, "wb") as f:
                    f.write(pdf_bytes)

                # 2. Grava na planilha CSV
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
                    "Caminho_PDF": pdf_path
                }

                csv_file = "respostas_alunos.csv"
                if os.path.exists(csv_file):
                    df = pd.read_csv(csv_file)
                    df = pd.concat([df, pd.DataFrame([registro])], ignore_index=True)
                else:
                    df = pd.DataFrame([registro])

                df = df.sort_values(by="Nome", ascending=True)
                df.to_csv(csv_file, index=False)

                st.success("🎉 Atividade enviada com sucesso! Seu relatório único em PDF e seus dados foram salvos.")

# --- PAINEL DE CONTROLE DO PROFESSOR ---
st.sidebar.write("---")
if st.sidebar.checkbox("🔒 Acesso do Professor"):
    senha = st.sidebar.text_input("Senha de Acesso:", type="password")
    if senha == "prof123":
        st.header("📊 Painel do Professor")
        
        if os.path.exists("respostas_alunos.csv"):
            df_prof = pd.read_csv("respostas_alunos.csv")
            st.subheader("Lista de Respostas (Ordem Alfabética)")
            st.dataframe(df_prof)
            
            col_d1, col_d2 = st.columns(2)
            
            with col_d1:
                csv_data = df_prof.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar Planilha CSV (Ordenada)",
                    data=csv_data,
                    file_name="respostas_alunos_ordenadas.csv",
                    mime="text/csv"
                )
            
            with col_d2:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for root, dirs, files in os.walk("relatorios"):
                        for file in files:
                            zf.write(os.path.join(root, file), file)
                
                zip_buffer.seek(0)
                st.download_button(
                    label="📦 Baixar Todos os Relatórios PDF (ZIP)",
                    data=zip_buffer,
                    file_name="relatorios_alunos.zip",
                    mime="application/zip"
                )
        else:
            st.info("Nenhuma submissão realizada ainda.")
    elif senha:
        st.sidebar.error("Senha incorreta.")
