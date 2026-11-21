import streamlit as st
import numpy as np
import pandas as pd
import hashlib
from datetime import datetime

# Para integração com Google Sheets / Drive:
# pip install streamlit gspread google-auth
import gspread
from google.oauth2.service_account import Credentials


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Laboratório Virtual: Volumetria vs. Gravimetria",
    page_icon="🧪",
    layout="wide"
)

# Constantes químicas
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

    # Massa pesada para a titulação (g) - aprox. 0.1200 g a 0.1600 g
    # (garante volume de titulante ~0.10 mol/L entre 18 mL e 30 mL)
    massa_tit = round(float(rng.uniform(0.1200, 0.1600)), 4)

    # Massa pesada para a gravimetria (g) - aprox. 0.4500 g a 0.5500 g
    massa_grav = round(float(rng.uniform(0.4500, 0.5500)), 4)

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
        "conc_agno3": conc_agno3,
        "vol_eq_tit": vol_eq_tit,
        "vol_pf_mohr": vol_pf_mohr,
        "massa_agcl_teorica": massa_agcl_teorica,
    }


# ============================================================
# FUNÇÃO DE SALVAMENTO NO GOOGLE SHEETS (DRIVE)
# ============================================================

def salvar_no_google_sheets(registro: dict):
    """
    Salva o dicionário como uma nova linha na planilha configurada em st.secrets.
    """
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=scopes
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(st.secrets["spreadsheet_id"]).sheet1

        # Cria cabeçalho se a planilha estiver vazia
        if len(sheet.get_all_values()) == 0:
            sheet.append_row(list(registro.keys()))

        sheet.append_row(list(registro.values()))
        return True, "Respostas salvas com sucesso na planilha do professor!"
    except Exception as e:
        return False, f"Não foi possível conectar ao Google Drive: {e}"


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
    "3️⃣ Cálculos Comparativos e Envio"
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
        - Solução titulante na bureta: **$\mathrm{{AgNO_3}}$ `{dados['conc_agno3']:.4f} mol/L`**
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

            # Lógica química realista das condições escolhidas
            if condicao_ph == "Meio fortemente alcalino (pH > 12 com NaOH)":
                cor_hex = "#3E2723"
                status_txt = "⚠️ Precipitado marrom-escuro imediato de Ag₂O! O excesso de OH⁻ precipita a prata antes do cloreto."
            elif indicador != "Cromato de potássio (K₂CrO₄ 5% m/v)":
                cor_hex = "#F5F5F5"
                status_txt = (
                    f"Solução turva esbranquiçada (AgCl formado). "
                    f"Como você não usou K₂CrO₄, não há mudança de cor visível no ponto final!"
                )
            elif condicao_ph == "Meio fortemente ácido (pH < 2 com HNO₃)":
                cor_hex = "#FF9800"
                status_txt = (
                    "⚠️ Solução alaranjada! Em meio ácido, o CrO₄²⁻ converte-se em Cr₂O₇²⁻, "
                    "impedindo a precipitação de Ag₂CrO₄ no ponto de equivalência."
                )
            else:
                # Condições corretas: K2CrO4 + pH 6,5 - 10,0
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
                    color: {'#FFFFFF' if cor_hex in ['#3E2723', '#D84315', '#B71C1C', '#8E24AA'] else '#111111'};
                    font-weight: 600;
                    font-size: 1.05rem;
                ">
                    {status_txt}
                </div>
                """,
                unsafe_allow_html=True,
            )


# ============================================================
# SESSÃO 2: CONTRAPROVA GRAVIMÉTRICA
# ============================================================

with aba2:
    st.header("Sessão 2 — Contraprova por Gravimetria de Precipitação")
    st.markdown(
        f"""
        **Dados da Bancada:**
        - Nova alíquota da mesma amostra pesada em balança analítica: **`{dados['massa_grav']:.4f} g`**
        - Reagente precipitante disponível: **$\mathrm{{AgNO_3}}$ $0{{,}}20\ \mathrm{{mol/L}}$ (em excesso)**
        """
    )

    st.subheader("Selecione o Protocolo Experimental")
    st.caption("Marque as etapas e condições que você aplicará no laboratório antes de pesar o cadinho:")

    etapas_selecionadas = st.multiselect(
        "Etapas do procedimento gravimétrico:",
        [
            "1. Acidificar a solução com HNO₃ diluído antes de precipitar",
            "2. Alcalinizar a solução com NaOH antes de precipitar",
            "3. Adicionar excesso de AgNO₃ sob agitação e aquecer suavemente para coagulação",
            "4. Manter o sistema protegido da luz solar direta",
            "5. Filtrar e lavar o precipitado apenas com água destilada pura",
            "6. Filtrar e lavar o precipitado com solução diluída de HNO₃",
            "7. Secar em estufa a 110–120 °C até massa constante",
        ],
    )

    if st.button("🔬 Executar Procedimento Gravimétrico e Pesar", type="primary"):
        if len(etapas_selecionadas) < 4:
            st.error("Protocolo incompleto! Selecione todas as etapas essenciais do procedimento.")
        else:
            massa_final = dados["massa_agcl_teorica"]
            obs = []

            # Avaliação das escolhas experimentais
            if "2. Alcalinizar a solução com NaOH antes de precipitar" in etapas_selecionadas:
                massa_final *= 1.12
                obs.append("Erro positivo: coprecipitação de Ag₂O/carbonatos por falta de acidificação.")
            elif "1. Acidificar a solução com HNO₃ diluído antes de precipitar" not in etapas_selecionadas:
                massa_final *= 1.06
                obs.append("Erro positivo: ausência de HNO₃ permitiu coprecipitação de interferentes.")

            if "5. Filtrar e lavar o precipitado apenas com água destilada pura" in etapas_selecionadas:
                massa_final *= 0.93
                obs.append("Erro negativo: lavagem com água pura causou peptização parcial do coloide AgCl.")
            elif "6. Filtrar e lavar o precipitado com solução diluída de HNO₃" not in etapas_selecionadas:
                massa_final *= 1.04
                obs.append("Erro positivo: precipitado não lavado adequadamente reteve impurezas adsorvidas.")

            if "4. Manter o sistema protegido da luz solar direta" not in etapas_selecionadas:
                massa_final *= 0.97
                obs.append("Erro negativo: fotodecomposição parcial do AgCl com perda de Cl₂(g).")

            if "7. Secar em estufa a 110–120 °C até massa constante" not in etapas_selecionadas:
                massa_final *= 1.08
                obs.append("Erro positivo: precipitado úmido (não seco até massa constante).")

            st.session_state.massa_agcl_obtida = round(massa_final, 4)
            st.session_state.gravimetria_concluida = True
            st.session_state.diagnostico_grav = (
                "Protocolo executado adequadamente!" if not obs else " | ".join(obs)
            )

    if st.session_state.gravimetria_concluida:
        st.success(
            f"**Massa de $\mathrm{{AgCl}}$ obtida na balança analítica:** "
            f"`{st.session_state.massa_agcl_obtida:.4f} g`"
        )
        st.caption(f"Observação técnica: {st.session_state.diagnostico_grav}")


# ============================================================
# SESSÃO 3: CÁLCULOS DO ESTUDANTE E ENVIO PARA O DRIVE
# ============================================================

with aba3:
    st.header("Sessão 3 — Relatório de Resultados e Comparação")

    st.markdown(
        f"""
        **Resumo dos dados obtidos na sua bancada:**
        - **Titulação:** Massa = `{dados['massa_tit']:.4f} g` | $[\mathrm{{AgNO_3}}]$ = `{dados['conc_agno3']:.4f} mol/L` | Volume anotado = `{st.session_state.volume_adicionado:.2f} mL`
        - **Gravimetria:** Massa = `{dados['massa_grav']:.4f} g` | Massa de $\mathrm{{AgCl}}$ = `{st.session_state.massa_agcl_obtida if st.session_state.massa_agcl_obtida else 'Pendente'} g`
        - **Massas Molares:** $\mathrm{{NaCl}} = 58{{,}}44\ \mathrm{{g\,mol^{{-1}}}}$ | $\mathrm{{AgCl}} = 143{{,}}32\ \mathrm{{g\,mol^{{-1}}}}$
        """
    )

    with st.form("form_relatorio"):
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            vol_informado = st.number_input(
                "Volume final da bureta considerado (mL):",
                min_value=0.0,
                value=float(st.session_state.volume_adicionado),
                step=0.01,
                format="%.2f",
            )
            teor_tit_aluno = st.number_input(
                "Teor de NaCl calculado pela Titulação (% m/m):",
                min_value=0.0,
                max_value=100.0,
                step=0.01,
                format="%.2f",
            )

        with col_r2:
            fg_aluno = st.number_input(
                "Fator Gravimétrico (NaCl / AgCl) calculado:",
                min_value=0.0,
                max_value=2.0,
                step=0.0001,
                format="%.4f",
            )
            teor_grav_aluno = st.number_input(
                "Teor de NaCl calculado pela Gravimetria (% m/m):",
                min_value=0.0,
                max_value=100.0,
                step=0.01,
                format="%.2f",
            )

        discussao = st.text_area(
            "Discussão comparativa (explique por que os meios reacionais diferem entre os dois métodos e avalie a concordância entre os teores obtidos):",
            height=130,
        )

        enviado = st.form_submit_button("📤 Enviar Relatório para o Professor", type="primary")

    if enviado:
        if st.session_state.massa_agcl_obtida is None or vol_informado == 0:
            st.error("Conclua tanto a Titulação quanto a Gravimetria antes de enviar!")
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
                "Vol_Informado_mL": vol_informado,
                "Teor_Tit_Aluno": teor_tit_aluno,
                "Massa_Grav_g": dados["massa_grav"],
                "Massa_AgCl_Teorica_g": dados["massa_agcl_teorica"],
                "Massa_AgCl_Obtida_g": st.session_state.massa_agcl_obtida,
                "FG_Aluno": fg_aluno,
                "Teor_Grav_Aluno": teor_grav_aluno,
                "Diagnostico_Gravimetria": st.session_state.diagnostico_grav,
                "Discussao": discussao.strip(),
            }

            sucesso, msg = salvar_no_google_sheets(registro)
            if sucesso:
                st.success(msg)
            else:
                st.error(msg)

            # Gera sempre um recibo CSV para backup imediato do aluno
            df_recibo = pd.DataFrame([registro])
            st.download_button(
                "⬇️ Baixar Comprovante de Entrega (CSV)",
                data=df_recibo.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                file_name=f"relatorio_{matricula.strip()}.csv",
                mime="text/csv",
            )
