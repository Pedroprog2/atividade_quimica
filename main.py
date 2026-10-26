import streamlit as st
import pandas as pd
from PIL import Image, ImageStat
import piexif
from datetime import datetime
import os
import numpy as np

st.set_page_config(page_title="Laboratório Prático de Análise e Teste t", layout="wide")

st.title("🔬 Laboratório Virtual: Amostragem e Teste t de Student")
st.write("Atividade prática individualizada baseada em coleta de cor e análise estatística.")

# --- 1. IDENTIFICAÇÃO DO ESTUDANTE ---
st.sidebar.header("Identificação")
nome_aluno = st.sidebar.text_input("Nome Completo do Aluno:")
matricula_input = st.sidebar.text_input("Matrícula (somente números):")

if not nome_aluno or not matricula_input or not matricula_input.isdigit():
    st.warning("⚠️ Digite seu nome completo e apenas os números da sua matrícula na barra lateral para começar.")
    st.stop()

matricula = int(matricula_input)
ultimos_digitos = matricula % 100

# --- QUESTÃO 1: CÁLCULO DA REFERÊNCIA ---
st.header("1. Valor de Referência Individualizado")
ref_kno4 = 100 + ultimos_digitos

st.info(f"📍 **Seu valor de referência para a análise de $KMnO_4$ é:** `{ref_kno4}`")
st.caption("Fórmula: 100 + (últimos 2 dígitos da matrícula)")


# --- EXIBIÇÃO DAS 3 RÉPLICAS DE IMAGEM NO STREAMLIT ---
st.header("📸 Réplicas para Medição")
st.write("Abaixo estão as 3 amostras do lote. Realize o procedimento descrito na Questão 2.")

col_a, col_b, col_c = st.columns(3)

# Exemplo: criando 3 imagens sintéticas com pequenas variações no Canal R (ou carregando imagens reais do seu servidor)
# Substitua por: img_a = Image.open('amostra_A.jpg'), etc.
base_color = 120 + (matricula % 15) # Dá uma variação sutil baseada na matrícula do aluno

# Gerando matrizes com pequenas variações para o canal R
arr_a = np.full((150, 150, 3), [base_color, 40, 80], dtype=np.uint8)
arr_b = np.full((150, 150, 3), [base_color - 4, 42, 78], dtype=np.uint8)
arr_c = np.full((150, 150, 3), [base_color + 3, 38, 82], dtype=np.uint8)

img_a, img_b, img_c = Image.fromarray(arr_a), Image.fromarray(arr_b), Image.fromarray(arr_c)

with col_a:
    st.image(img_a, caption="Réplica A", use_column_width=True)
with col_b:
    st.image(img_b, caption="Réplica B", use_column_width=True)
with col_c:
    st.image(img_c, caption="Réplica C", use_column_width=True)

st.divider()

# --- UPLOAD DA FOTO COMPROBATÓRIA DO ALUNO ---
st.subheader("Envio da Comprovação (Câmera do Celular)")
uploaded_file = st.file_uploader("Envie a foto tirada pelo celular mostrando a tela + papel manuscrito", type=["jpg", "jpeg", "png"])

# --- UPLOAD DA FOTO E VERIFICAÇÃO DE METADADOS ---
st.header("2. Coleta da Imagem da Amostra (Canal Vermelho)")
st.write("Envie a foto da sua amostra com um papel manuscrito ao lado contendo seu nome e a data de hoje.")

uploaded_file = st.file_uploader("Selecione ou tire a foto da amostra", type=["jpg", "jpeg"])

data_exif_str = "Sem metadados EXIF"

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Imagem enviada pelo aluno", use_column_width=True)

    # Extração e Validação de Metadados EXIF
    try:
        exif_dict = piexif.load(uploaded_file.getvalue())
        if "Exif" in exif_dict and piexif.ExifIFD.DateTimeOriginal in exif_dict["Exif"]:
            data_exif_raw = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode('utf-8')
            data_exif_str = datetime.strptime(data_exif_raw, '%Y:%m:%d %H:%M:%S').strftime('%d/%m/%Y às %H:%M:%S')
            st.success(f"📸 **Metadados EXIF detectados:** Foto tirada em **{data_exif_str}**")
        else:
            st.warning("⚠️ A imagem enviada não contém a data original de captura nos metadados (pode ser ter sido enviada via app de mensagem que remove EXIF).")
    except Exception:
        st.info("ℹ️ Não foi possível extrair metadados EXIF detalhados desta imagem.")

    # Extração da intensidade média do Canal Vermelho (Red) da imagem enviada
    # Converte imagem para RGB e extrai o canal R
    rgb_image = image.convert('RGB')
    stat = ImageStat.Stat(rgb_image)
    canal_vermelho_medio_sistema = round(stat.mean[0], 2) # Canal 0 = Red

    st.write("---")
    st.subheader("3. Medições e Teste t (Inserção de Dados do Aluno)")
    st.write(f"Sua imagem tem uma intensidade média global do Canal Vermelho de: **{canal_vermelho_medio_sistema}** (referência do sistema).")

    # --- QUESTÃO 2: ENTRADA DOS DADOS E CÁLCULOS DO ALUNO ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        media_aluno = st.number_input("Digite a média ($\bar{x}$) que você calculou para o Canal R:", value=0.0, step=0.01)
    with col2:
        desvio_aluno = st.number_input("Digite o desvio padrão ($s$) que você calculou:", value=0.0, step=0.01)
    with col3:
        t_calculado_aluno = st.number_input("Digite o valor de $t_{calc}$ que você obteve:", value=0.0, step=0.001)

    conclusao_aluno = st.radio(
        "Com base no seu Teste t, a amostra difere significativamente do valor de referência?",
        ["Selecione...", "Sim, há diferença estatística significativa", "Não, a diferença não é significativa"]
    )

    # --- BOTÃO PARA SALVAR RESPOSTAS ---
    if st.button("Enviar Respostas do Exercício"):
        if conclusao_aluno == "Selecione...":
            st.error("Por favor, selecione a conclusão da sua análise estatística antes de enviar.")
        else:
            # Estrutura do registro
            novo_registro = {
                "Nome": nome_aluno.strip().title(),
                "Matricula": matricula,
                "DataEnvio": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "Referencia_KMnO4": ref_kno4,
                "Exif_DataFoto": data_exif_str,
                "CanalR_Sistema": canal_vermelho_medio_sistema,
                "Media_Aluno": media_aluno,
                "Desvio_Aluno": desvio_aluno,
                "T_Calc_Aluno": t_calculado_aluno,
                "Conclusao": conclusao_aluno
            }

            # Salvar em CSV e ordenar alfabeticamente
            csv_file = "respostas_alunos.csv"
            
            if os.path.exists(csv_file):
                df = pd.read_csv(csv_file)
                df = pd.concat([df, pd.DataFrame([novo_registro])], ignore_index=True)
            else:
                df = pd.DataFrame([novo_registro])

            # Ordenar lista sempre em ordem alfabética pelo nome
            df = df.sort_values(by="Nome", ascending=True)
            df.to_csv(csv_file, index=False)

            st.success("✅ Atividade enviada com sucesso! Suas respostas e dados foram registrados.")

# --- ÁREA RESTRITA DO PROFESSOR (OPCIONAL) ---
st.sidebar.write("---")
if st.sidebar.checkbox("Modo Professor (Acesso às respostas)"):
    senha = st.sidebar.text_input("Senha de acesso:", type="password")
    if senha == "prof123": # Altere para sua senha de preferência
        st.header("📊 Painel do Professor - Lista de Respostas (Ordem Alfabética)")
        if os.path.exists("respostas_alunos.csv"):
            df_prof = pd.read_csv("respostas_alunos.csv")
            st.dataframe(df_prof)
            
            # Botão para baixar planilha pronta
            csv_data = df_prof.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar Lista em CSV (Ordem Alfabética)",
                data=csv_data,
                file_name="relatorio_alunos_ordenado.csv",
                mime="text/csv"
            )
        else:
            st.info("Nenhuma resposta enviada ainda.")
    elif senha:
        st.sidebar.error("Senha incorreta.")
