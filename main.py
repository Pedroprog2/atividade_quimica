import streamlit as st
import numpy as np
import pandas as pd
import hashlib
import requests
from datetime import datetime


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Laboratório Virtual: Volumetria vs. Gravimetria",
    page_icon="🧪",
    layout="wide"
)

# Constantes químicas (g/mol)
MM_NACL = 58.44
MM_AGCL = 143.32


# ============================================================
# FUNÇÃO DE GERAÇÃO DETERMINÍSTICA POR MATRÍCULA
# ============================================================

def gerar_parametros_aluno(matricula: str):
    """
    Gera parâmetros exclusivos e reprodutíveis a partir da matrícula.
    """
    limpa = "".join(filter(str.isalnum, matricula.strip().upper()))
    seed = int(hashlib.sha256(limpa.encode("utf-8")).hexdigest()[:12], 16)
    rng = np.random.default_rng(seed)

    # Teor real de NaCl na amostra (%) - oculto do aluno
    teor_real = round(float(rng.uniform(74.0, 95.5)), 2)

    # Massa pesada para a titulação (g)
    massa_tit = round(float(rng.uniform(0.1200, 0.1600)), 4)

    # Massa pesada para a gravimetria (g)
    massa_grav = round(float(rng.uniform(0.4500, 0.5500)), 4)

    # Massa do cadinho filtrante vazio (g)
    massa_cadinho = round(float(rng.uniform(18.2000, 24.8000)), 4)

    # Concentração padronizada do AgNO3 (mol/L)
    conc_agno3 = round(float(rng.uniform(0.0980, 0.1040)), 4)

    # Volume teórico exato do ponto de equivalência na titulação (mL)
    mols_nacl_tit = (massa_tit * (teor_real / 100.0)) / MM_NACL
    vol_eq_tit = (mols_nacl_tit / conc_agno3) * 1000.0

    # Erro do branco do indicador de Mohr (~0.04 mL)
    vol_pf_mohr = round(vol_eq_tit + 0.04, 2)

    # Massa teórica exata de AgCl na gravimetria (g)
    mols_nacl_grav = (massa_grav * (teor_real / 100.0)) / MM_NACL
    massa_agcl_teorica = round(mols_nacl_grav * MM_AGCL, 4)

    return {
        "teor_real": teor_real,
        "massa_tit": massa_tit,
        "massa_grav": massa_grav,
        "massa_cadinho": massa_cadinho,
        "conc_agno3": conc_agno3,
        "vol_eq_tit": vol_eq_tit,
        "vol_pf_mohr": vol_pf_mohr,
        "massa_agcl_teorica": massa_agcl_teorica,
    }

def salvar_no_google_forms(registro: dict):
    """
    Envia os dados diretamente para um Google Forms vinculado a uma Planilha no Drive.
    """
    # 1. Substitua pelo link do seu formulário terminando em /formResponse
    FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfT9FP6VuirUdoRaebDt_4fufS5-g2TDAkh3oZRbNUAd-TUxA/formResponse"

    # 2. Substitua os códigos entry.XXXXXXX pelos obtidos no 'Link preenchido automaticamente'
  resumo_numerico = (
        f"Data: {registro['Data_Hora']} | "
        f"Gabarito_Real: {registro['Teor_Real_Gabarito']}% | "
        f"Tit_Aluno: {registro['Teor_Tit_Aluno']}% "
        f"(Vol: {registro['Vol_Escoado_mL']}/{registro['Vol_PF_Teorico_mL']} mL; "
        f"m={registro['Massa_Tit_g']}g; C={registro['Conc_AgNO3']}M) | "
        f"Grav_Aluno: {registro['Teor_Grav_Aluno']}% "
        f"(AgCl: {registro['Massa_AgCl_Obtida_g']}/{registro['Massa_AgCl_Teorica_g']} g; "
        f"m={registro['Massa_Grav_g']}g) | "
        f"Diag_Grav: {registro['Diagnostico_Gravimetria']}"
    )

    payload = {
        "entry.901326228": registro["Matricula"],
        "entry.1845306876": registro["Nome"],
        "entry.1100499664": resumo_numerico,
        "entry.823625954": registro["Discussao"],
    }

    try:
        resposta = requests.post(FORM_URL, data=payload, timeout=10)
        if resposta.status_code == 200:
            return True, "✅ Respostas enviadas e registradas com sucesso na planilha do professor!"
        return (
            False,
            f"⚠️ O formulário retornou código {resposta.status_code}. "
            "Verifique os IDs (entry) ou baixe o comprovante CSV abaixo."
        )
    except Exception as e:
        return (
            False,
            f"⚠️ Falha de conexão ao enviar ({e}). "
            "Baixe o comprovante CSV abaixo e envie ao professor."
        )


# ============================================================
# ESTADO DA SESSÃO
# ============================================================

if "volume_adicionado" not in st.session_state:
    st.session_state.volume_adicionado = 0.0
if "gravimetria_concluida" not in st.session_state:
    st.session_state.gravimetria_concluida = False
if "massa_agcl_obtida" not in st.session_state:
    st.session_state.massa_agcl_obtida = None
if "diagnostico_grav" not in st.session_state:
    st.session_state.diagnostico_grav = ""


# ============================================================
# CABEÇALHO E IDENTIFICAÇÃO DO ESTUDANTE
# ============================================================

st.title("🧪 Controle de Qualidade: Volumetria vs. Gravimetria")
st.markdown(
    "Determinação do teor de **cloreto de sódio ($\mathrm{NaCl}$)** em amostra sólida impura "
    "por **Argentometria (Método de Mohr)** e contraprova por **Gravimetria de Precipitação**."
)

with st.container(border=True):
    c1, c2 = st.columns([2, 1])
    with c1:
        nome_aluno = st.text_input("Nome completo do(a) estudante:")
    with c2:
        matricula = st.text_input("Número de Matrícula (ex.: 2024012345):")

if not nome_aluno.strip() or len(matricula.strip()) < 4:
    st.info("👆 Preencha seu **Nome** e **Número de Matrícula** para receber sua amostra exclusiva.")
    st.stop()

dados = gerar_parametros_aluno(matricula)

st.success(f"Amostra gerada para **{nome_aluno}** (Matrícula: `{matricula.strip()}`)")


# ============================================================
# ABAS DAS DUAS SESSÕES + RELATÓRIO FINAL
# ============================================================

aba1, aba2, aba3 = st.tabs([
    "1️⃣ Sessão 1: Titulação (Método de Mohr)",
    "2️⃣ Sessão 2: Contraprova Gravimétrica",
    "3️⃣ Comparação e Envio"
])


# ============================================================
# SESSÃO 1: TITULAÇÃO DE PRECIPITAÇÃO (MOHR)
# ============================================================

with aba1:
    st.header("Sessão 1 — Titulação Argentométrica (Método de Mohr)")
    st.markdown(
        f"""
        **Dados da Bancada:**
        - Massa da amostra pesada e dissolvida em Erlenmeyer: **`{dados['massa_tit']:.4f} g`**
        - Solução titulante na bureta (zerada em `0,00 mL`): **$\mathrm{{AgNO_3}}$ `{dados['conc_agno3']:.4f} mol/L`**
        - Massa molar do $\mathrm{{NaCl}}$: **`58,44 g/mol`**
        """
    )

    col_cond, col_sim = st.columns([1, 1.3])

    with col_cond:
        st.subheader("1. Preparo do Meio Reacional")
        indicador = st.selectbox(
            "Selecione o indicador adequado:",
            [
                "Selecione...",
                "Fenolftaleína (1% m/v)",
                "Cromato de potássio (K₂CrO₄ 5% m/v)",
                "Alaranjado de metila (0,1% m/v)",
                "Ferroína (0,025 mol/L)",
            ],
        )

        condicao_ph = st.selectbox(
            "Selecione o ajuste de pH do meio:",
            [
                "Selecione...",
                "Meio fortemente ácido (pH < 2 com HNO₃)",
                "Meio neutro a levemente alcalino (pH 6,5 a 10,0)",
                "Meio fortemente alcalino (pH > 12 com NaOH)",
            ],
        )

        condicoes_definidas = (
            indicador != "Selecione..." and condicao_ph != "Selecione..."
        )

        if condicoes_definidas:
            st.markdown("---")
            st.subheader("2. Controle da Bureta")
            b1, b2, b3, b4 = st.columns(4)
            if b1.button("+ 1,00 mL", use_container_width=True):
                st.session_state.volume_adicionado = round(st.session_state.volume_adicionado + 1.00, 2)
            if b2.button("+ 0,10 mL", use_container_width=True):
                st.session_state.volume_adicionado = round(st.session_state.volume_adicionado + 0.10, 2)
            if b3.button("+ 0,05 mL", use_container_width=True):
                st.session_state.volume_adicionado = round(st.session_state.volume_adicionado + 0.05, 2)
            if b4.button("🔄 Zerar", use_container_width=True):
                st.session_state.volume_adicionado = 0.00

            vol_atual = st.session_state.volume_adicionado
            st.metric("Volume de AgNO₃ escoado", f"{vol_atual:.2f} mL")

    with col_sim:
        st.subheader("Visualização do Erlenmeyer")
        if not condicoes_definidas:
            st.warning("Escolha o indicador e a condição de pH ao lado para iniciar a titulação.")
        else:
            vol = st.session_state.volume_adicionado
            pf = dados["vol_pf_mohr"]

            if condicao_ph == "Meio fortemente alcalino (pH > 12 com NaOH)":
                cor_hex = "#3E2723"
                status_txt = (
                    "⚠️ Precipitado marrom-escuro imediato de Ag₂O! "
                    "O excesso de OH⁻ precipita a prata antes do cloreto."
                )
            elif indicador != "Cromato de potássio (K₂CrO₄ 5% m/v)":
                cor_hex = "#F5F5F5"
                status_txt = (
                    "Solução turva esbranquiçada (AgCl formado). "
                    "Como você não usou K₂CrO₄, não há mudança de cor visível no ponto final!"
                )
            elif condicao_ph == "Meio fortemente ácido (pH < 2 com HNO₃)":
                cor_hex = "#FF9800"
                status_txt = (
                    "⚠️ Solução alaranjada! Em meio ácido, o CrO₄²⁻ converte-se em Cr₂O₇²⁻, "
                    "impedindo a precipitação de Ag₂CrO₄ no ponto de equivalência."
                )
            else:
                if vol == 0:
                    cor_hex = "#FFF176"
                    status_txt = "Solução amarela límpida (íons CrO₄²⁻ em solução)."
                elif vol < pf - 0.15:
                    cor_hex = "#FFF59D"
                    status_txt = "Suspensão amarelo-leitosa: AgCl(s) precipitando enquanto CrO₄²⁻ permanece em solução."
                elif pf - 0.15 <= vol < pf:
                    cor_hex = "#FFE082"
                    status_txt = "Próximo ao ponto final! Surge coloração avermelhada local que desaparece sob agitação."
                elif pf <= vol <= pf + 0.15:
                    cor_hex = "#D84315"
                    status_txt = "✅ PONTO DE VIRAGEM ATINGIDO! Precipitado vermelho-tijolo persistente de Ag₂CrO₄."
                else:
                    cor_hex = "#8E24AA" if vol > pf + 2 else "#B71C1C"
                    status_txt = "⚠️ Passou do ponto final! Excesso elevado de AgNO₃."

            texto_claro = cor_hex in ["#3E2723", "#D84315", "#B71C1C", "#8E24AA"]
            st.markdown(
                f"""
                <div style="
                    background-color: {cor_hex};
                    border: 3px solid #444;
                    border-radius: 16px;
                    height: 180px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                    text-align: center;
                    color: {'#FFFFFF' if texto_claro else '#111111'};
                    font-weight: 600;
                    font-size: 1.05rem;
                ">
                    {status_txt}
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.subheader("3. Resultado da Titulação")
    teor_tit_aluno = st.number_input(
        "Com base no volume de AgNO₃ escoado até o ponto de viragem, calcule e informe o teor de NaCl (% m/m):",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=0.01,
        format="%.2f",
        key="input_teor_tit",
    )


# ============================================================
# SESSÃO 2: CONTRAPROVA GRAVIMÉTRICA
# ============================================================

with aba2:
    st.header("Sessão 2 — Contraprova por Gravimetria de Precipitação")
    st.markdown(
        f"""
        **Dados Iniciais da Bancada:**
        - Nova alíquota da mesma amostra pesada em balança analítica: **`{dados['massa_grav']:.4f} g`**
        - Massa do cadinho filtrante limpo e seco (tara): **`{dados['massa_cadinho']:.4f} g`**
        - Reagente precipitante disponível: **$\mathrm{{AgNO_3}}$ $0{{,}}20\ \mathrm{{mol/L}}$ (em excesso)**
        - Massas molares: **$\mathrm{{NaCl}} = 58{{,}}44\ \mathrm{{g/mol}}$** | **$\mathrm{{AgCl}} = 143{{,}}32\ \mathrm{{g/mol}}$**
        """
    )

    st.subheader("1. Monte o Protocolo na Ordem Cronológica de Execução")
    st.caption(
        "⚠️ **Atenção:** Selecione as etapas **na exata ordem** em que devem ser realizadas no laboratório "
        "(a ordem em que você clica define a sequência do procedimento)."
    )

    OP_DISSOLVER = "Dissolver a amostra em água destilada e acidificar com HNO₃ diluído"
    OP_ALCALINIZAR = "Dissolver a amostra e alcalinizar com NaOH diluído"
    OP_PRECIPITAR = "Adicionar excesso de AgNO₃ sob agitação e aquecer suavemente para coagulação"
    OP_LUZ = "Manter o béquer protegido da incidência direta de luz"
    OP_FILTRAR_HNO3 = "Filtrar no cadinho tarado e lavar o precipitado com solução diluída de HNO₃"
    OP_FILTRAR_AGUA = "Filtrar no cadinho tarado e lavar o precipitado apenas com água destilada pura"
    OP_SECAR = "Secar o cadinho em estufa a 110–120 °C até massa constante"

    etapas_selecionadas = st.multiselect(
        "Clique nas etapas na sequência correta:",
        [
            OP_FILTRAR_HNO3,
            OP_SECAR,
            OP_ALCALINIZAR,
            OP_PRECIPITAR,
            OP_DISSOLVER,
            OP_FILTRAR_AGUA,
            OP_LUZ,
        ],
    )

    if etapas_selecionadas:
        st.markdown("**Sequência montada por você:**")
        for idx, item in enumerate(etapas_selecionadas, start=1):
            st.write(f"**{idx}º.** {item}")

    if st.button("🔬 Executar Procedimento e Realizar Pesagens", type="primary"):
        if len(etapas_selecionadas) < 4:
            st.error("Protocolo incompleto! Selecione todas as etapas necessárias.")
        else:
            pos_precip = (
                etapas_selecionadas.index(OP_PRECIPITAR)
                if OP_PRECIPITAR in etapas_selecionadas
                else -1
            )
            pos_filtrar = max(
                etapas_selecionadas.index(OP_FILTRAR_HNO3) if OP_FILTRAR_HNO3 in etapas_selecionadas else -1,
                etapas_selecionadas.index(OP_FILTRAR_AGUA) if OP_FILTRAR_AGUA in etapas_selecionadas else -1,
            )
            pos_secar = (
                etapas_selecionadas.index(OP_SECAR)
                if OP_SECAR in etapas_selecionadas
                else -1
            )

            if pos_precip == -1 or pos_filtrar == -1:
                st.error("Faltam etapas essenciais de precipitação ou filtração no seu protocolo.")
            elif pos_filtrar < pos_precip:
                st.error("❌ Erro de sequência física: você tentou filtrar antes de precipitar o AgCl!")
            elif pos_secar != -1 and pos_secar < pos_filtrar:
                st.error("❌ Erro de sequência física: você colocou o cadinho na estufa antes de filtrar o precipitado!")
            else:
                massa_final = dados["massa_agcl_teorica"]
                obs = []

                pos_meio = max(
                    etapas_selecionadas.index(OP_DISSOLVER) if OP_DISSOLVER in etapas_selecionadas else -1,
                    etapas_selecionadas.index(OP_ALCALINIZAR) if OP_ALCALINIZAR in etapas_selecionadas else -1,
                )

                if OP_ALCALINIZAR in etapas_selecionadas:
                    massa_final *= 1.12
                    obs.append("Erro positivo: meio alcalino causou coprecipitação de Ag₂O/carbonatos.")
                elif OP_DISSOLVER not in etapas_selecionadas:
                    massa_final *= 1.06
                    obs.append("Erro positivo: falta de acidificação prévia com HNO₃ permitiu coprecipitação.")
                elif pos_meio > pos_precip:
                    massa_final *= 1.04
                    obs.append("Erro de ordem: o HNO₃ foi adicionado após a precipitação, retendo interferentes coprecipitados.")

                if OP_FILTRAR_AGUA in etapas_selecionadas:
                    massa_final *= 0.93
                    obs.append("Erro negativo: lavagem com água pura causou peptização parcial do AgCl.")
                elif OP_FILTRAR_HNO3 not in etapas_selecionadas:
                    massa_final *= 1.04
                    obs.append("Erro positivo: precipitado não lavado adequadamente.")

                if OP_LUZ not in etapas_selecionadas:
                    massa_final *= 0.97
                    obs.append("Erro negativo: fotodecomposição parcial do AgCl pela luz.")

                if OP_SECAR not in etapas_selecionadas:
                    massa_final *= 1.08
                    obs.append("Erro positivo: precipitado pesado úmido (sem secagem até massa constante).")

                st.session_state.massa_agcl_obtida = round(massa_final, 4)
                st.session_state.gravimetria_concluida = True
                st.session_state.diagnostico_grav = (
                    "Ordem e protocolo corretos!" if not obs else " | ".join(obs)
                )

    if st.session_state.gravimetria_concluida:
        m_cad = dados["massa_cadinho"]
        m_agcl = st.session_state.massa_agcl_obtida
        m_total_constante = round(m_cad + m_agcl, 4)
        m_primeira_secagem = round(m_total_constante + 0.0042, 4)

        st.markdown("---")
        st.subheader("2. Leituras da Balança Analítica")
        b_col1, b_col2, b_col3 = st.columns(3)
        b_col1.metric("1. Cadinho vazio (tara)", f"{m_cad:.4f} g")
        b_col2.metric("2. Cadinho + Precipitado (1ª secagem)", f"{m_primeira_secagem:.4f} g")
        b_col3.metric("3. Cadinho + Precipitado (Massa constante)", f"{m_total_constante:.4f} g")

        st.caption(f"Status operacional: {st.session_state.diagnostico_grav}")

    st.markdown("---")
    st.subheader("3. Resultado da Gravimetria")
    teor_grav_aluno = st.number_input(
        "Com base na massa de AgCl obtida (por diferença entre o cadinho com precipitado e o cadinho vazio), calcule e informe o teor de NaCl (% m/m):",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=0.01,
        format="%.2f",
        key="input_teor_grav",
    )


# ============================================================
# SESSÃO 3: COMPARAÇÃO E ENVIO PARA O DRIVE
# ============================================================

with aba3:
    st.header("Sessão 3 — Análise Comparativa e Envio de Resultados")

    col_res1, col_res2 = st.columns(2)
    with col_res1:
        with st.container(border=True):
            st.subheader("1️⃣ Resumo — Titulação (Mohr)")
            st.write(f"- **Massa da amostra:** `{dados['massa_tit']:.4f} g`")
            st.write(f"- **Volume de $\mathrm{{AgNO_3}}$ escoado:** `{st.session_state.volume_adicionado:.2f} mL`")
            st.write(f"- **Teor de $\mathrm{{NaCl}}$ informado por você:** **`{teor_tit_aluno:.2f}%`**")

    with col_res2:
        with st.container(border=True):
            st.subheader("2️⃣ Resumo — Gravimetria")
            st.write(f"- **Massa da amostra:** `{dados['massa_grav']:.4f} g`")
            if st.session_state.gravimetria_concluida:
                m_total = round(dados["massa_cadinho"] + st.session_state.massa_agcl_obtida, 4)
                st.write(f"- **Cadinho vazio / Massa constante:** `{dados['massa_cadinho']:.4f} g` / `{m_total:.4f} g`")
            else:
                st.write("- **Pesagem:** *Pendente (execute a Sessão 2)*")
            st.write(f"- **Teor de $\mathrm{{NaCl}}$ informado por você:** **`{teor_grav_aluno:.2f}%`**")

    with st.form("form_relatorio"):
        discussao = st.text_area(
            "Discussão comparativa (explique por que as condições de pH diferem entre os dois métodos e avalie a concordância entre os teores de NaCl encontrados):",
            height=140,
        )

        enviado = st.form_submit_button("📤 Enviar Relatório Final", type="primary")

    if enviado:
        if st.session_state.volume_adicionado <= 0 or st.session_state.massa_agcl_obtida is None:
            st.error("Conclua o procedimento experimental nas Sessões 1 e 2 antes de enviar.")
        elif teor_tit_aluno <= 0 or teor_grav_aluno <= 0:
            st.error("Preencha os teores de NaCl calculados nas Sessões 1 e 2 (devem ser maiores que 0,00%) antes de enviar.")
        elif len(discussao.strip()) < 15:
            st.warning("Escreva uma breve discussão comparativa antes de enviar.")
        else:
            registro = {
                "Data_Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Matricula": matricula.strip(),
                "Nome": nome_aluno.strip(),
                "Teor_Real_Gabarito": dados["teor_real"],
                "Massa_Tit_g": dados["massa_tit"],
                "Conc_AgNO3": dados["conc_agno3"],
                "Vol_PF_Teorico_mL": dados["vol_pf_mohr"],
                "Vol_Escoado_mL": st.session_state.volume_adicionado,
                "Teor_Tit_Aluno": teor_tit_aluno,
                "Massa_Grav_g": dados["massa_grav"],
                "Massa_AgCl_Teorica_g": dados["massa_agcl_teorica"],
                "Massa_AgCl_Obtida_g": st.session_state.massa_agcl_obtida,
                "Teor_Grav_Aluno": teor_grav_aluno,
                "Diagnostico_Gravimetria": st.session_state.diagnostico_grav,
                "Discussao": discussao.strip(),
            }

            sucesso, msg = salvar_no_google_forms(registro)
            if sucesso:
                st.success(msg)
            else:
                st.error(msg)

            df_recibo = pd.DataFrame([registro])
            st.download_button(
                "⬇️ Baixar Comprovante de Entrega (CSV)",
                data=df_recibo.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                file_name=f"relatorio_{matricula.strip()}.csv",
                mime="text/csv",
            )

