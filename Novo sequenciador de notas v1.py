import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# ================= CONFIGURAÇÕES =================
st.set_page_config(page_title="Sistema NT A3", layout="wide")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1FxFZ_gZdVbUIWILxKIWy0YRl0Wcfy6Cuo51vT3qQCDU/edit?usp=sharing"
SENHA_ADMIN = "Progen123"
PREFIXO_UNICO = "A3"
SUFIXO_FIXO = "PHD/CGPLAN/DNIT"

COLABORADORES = {
    "Andrei": "Administrador", "Arthur": "Administrador", "Carla": "Engenheiro(a)",
    "José": "Analista Administrativo", "Lucas": "Engenheiro(a)", "Nadya": "Engenheiro(a)",
    "Pedro": "Engenheiro(a)", "Uiter": "Engenheiro(a)", "Yan": "Engenheiro(a)"
}

# ================= CONEXÃO =================
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    return conn.read(spreadsheet=URL_PLANILHA, ttl=600)

def salvar_dados_blindado(df_a3_atu, df_total):
    df_outros = df_total[df_total["prefixo"] != PREFIXO_UNICO]
    df_final = pd.concat([df_outros, df_a3_atu], ignore_index=True)
    conn.update(spreadsheet=URL_PLANILHA, data=df_final)
    st.cache_data.clear()

def obter_sequencial_a3(df_base):
    ano_atu = datetime.now().year
    # Garante que as colunas são numéricas para o cálculo
    df_base["ano"] = pd.to_numeric(df_base["ano"], errors="coerce")
    df_base["numero"] = pd.to_numeric(df_base["numero"], errors="coerce")
    df_f = df_base[df_base["ano"] == ano_atu]
    prox = 1 if df_f.empty else int(df_f["numero"].max()) + 1
    texto = f"NOTA TÉCNICA Nº {PREFIXO_UNICO} {prox:04d}/{ano_atu} {SUFIXO_FIXO}"
    return prox, texto

# ================= CARREGAMENTO =================
df_master = carregar_dados()
df_a3 = df_master[df_master["prefixo"] == PREFIXO_UNICO].copy()

# ================= MENU LATERAL =================
with st.sidebar:
    st.image("https://www.gov.br/dnit/pt-br/central-de-conteudos/publicacoes/manual-de-gestao-da-marca/marcas-dnit/assinaturas-e-marcas/monocromatica-dnit-extenso.png", width=120)
    st.title("📂 Navegação")
    aba = st.radio("Ir para:", ["🏠 Início e Cadastro", "📊 Painel de Notas", "✏️ Editar Status", "🔐 Admin"])
    st.divider()
    if st.button("🔄 Sincronizar Google Sheets"):
        st.cache_data.clear()
        st.rerun()

# ================= PÁGINA 1: BOAS-VINDAS + CADASTRO =================
if aba == "🏠 Início e Cadastro":
    st.title(f"🏛️ Gestão de Notas Técnicas - Coplan")
    st.markdown(f"Bem-vindo, **Mestre**! Este é o seu painel central de trabalho.")
    
    # Previsão da Próxima Nota
    _, prox_formatado = obter_sequencial_a3(df_a3)
    st.metric(label="Próximo Sequencial A3 Disponível", value=prox_formatado.split(" ")[4])
    
    st.divider()
    
    st.subheader("🆕 Cadastrar Nova Nota")
    with st.form("form_cadastro_direto", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        
        with c1:
            nome_novo = st.text_input("Nome do Processo / Assunto")
            num_sei_novo = st.text_input("Nº do processo no SEI")
        
        with c2:
            colab_novo = st.selectbox("Responsável", list(COLABORADORES.keys()), index=2)
            flag_novo = st.checkbox("Gerar número agora")
        
        with c3:
            status_novo = st.selectbox("Status Inicial", ["Em elaboração", "Em análise"])
        
        if st.form_submit_button("🚀 Registrar na Planilha"):
            if not nome_novo:
                st.error("O campo Assunto é obrigatório.")
            else:
                novo_id = 1 if df_master.empty else int(pd.to_numeric(df_master["id_nota"]).max()) + 1
                data_agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                
                nova_l = {
                    "id_nota": novo_id, "nome_nota": nome_novo, "num_sei": num_sei_novo, 
                    "flag_obrigatorio": 1 if flag_novo else 0, "colaborador": colab_novo, 
                    "cargo": COLABORADORES[colab_novo], "status": status_novo, 
                    "data_criacao": data_agora, "ano": None, "numero": None, 
                    "numero_completo": None, "data_analise": None, "publicada": "Não",
                    "prefixo": PREFIXO_UNICO
                }
                
                if status_novo == "Em análise" or flag_novo:
                    num, comp = obter_sequencial_a3(df_a3)
                    nova_l.update({"ano": datetime.now().year, "numero": num, "numero_completo": comp, "data_analise": data_agora})
                
                df_a3_atu = pd.concat([df_a3, pd.DataFrame([nova_l])], ignore_index=True)
                salvar_dados_blindado(df_a3_atu, df_master)
                st.success("Registrado!")
                time.sleep(1)
                st.rerun()

# ================= PÁGINA 2: PAINEL GERAL =================
elif aba == "📊 Painel de Notas":
    st.header("📋 Lista de Processos A3")
    if not df_a3.empty:
        st.dataframe(df_a3.sort_values(by="id_nota", ascending=False), width="stretch", hide_index=True)

# ================= PÁGINA 3: EDITAR STATUS (LÓGICA CORRIGIDA) =================
# --- ABA 3: EDITAR STATUS (COM ESPELHO DE INFORMAÇÕES) ---
elif aba == "✏️ Editar Status":
    st.header("✏️ Atualizar Status e Numeração")
    
    if not df_a3.empty:
        # Preparação das opções do Selectbox
        df_a3['id_nota'] = pd.to_numeric(df_a3['id_nota'], errors='coerce')
        opcs = [f"ID {int(row['id_nota'])} - {row['nome_nota']}" for _, row in df_a3.iterrows() if pd.notna(row['id_nota'])]
        sel = st.selectbox("Selecione a nota para visualizar e editar:", ["—"] + opcs)
        
        if sel != "—":
            # Extração do ID e localização da linha
            id_s = int(sel.split("ID ")[1].split(" -")[0])
            idx = df_a3[df_a3["id_nota"] == id_s].index[0]
            
            # --- PAINEL DE INFORMAÇÕES DA NOTA (ESPELHO) ---
            st.markdown("### 🔍 Detalhes do Registro")
            with st.container(border=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.write(f"**📌 Assunto:**\n{df_a3.at[idx, 'nome_nota']}")
                    st.write(f"**📄 Processo SEI:**\n{df_a3.at[idx, 'num_sei'] or 'Não informado'}")
                with c2:
                    st.write(f"**👤 Responsável:**\n{df_a3.at[idx, 'colaborador']}")
                    st.write(f"**💼 Cargo:**\n{df_a3.at[idx, 'cargo']}")
                with c3:
                    st.write(f"**📅 Criado em:**\n{df_a3.at[idx, 'data_creation'] if 'data_creation' in df_a3.columns else df_a3.at[idx, 'data_criacao']}")
                    num_atual = df_a3.at[idx, 'numero_completo']
                    st.write(f"**🔢 Número Atual:**\n{num_atual if pd.notna(num_atual) else '⚠️ Sem número'}")

            st.divider()

            # --- FORMULÁRIO DE ALTERAÇÃO ---
            st.markdown("### ⚙️ Alterar Status")
            with st.container(border=True):
                n_status = st.selectbox("Mudar Status para:", ["Em elaboração", "Em análise", "Concluído"], 
                                        index=["Em elaboração", "Em análise", "Concluído"].index(df_a3.at[idx, "status"]))
                
                # Lógica de geração de número
                sem_num = pd.isna(df_a3.at[idx, "numero"]) or str(df_a3.at[idx, "numero"]).strip() == ""
                
                gerar_agora = False
                if n_status in ["Em análise", "Concluído"] and sem_num:
                    st.warning("Esta nota ainda não possui um número oficial na sequência A3.")
                    gerar_agora = st.checkbox("Confirmar geração automática do próximo número?")
                
                if st.button("💾 Salvar Alterações"):
                    # Atualiza status
                    df_a3.at[idx, "status"] = n_status
                    
                    # Gera número se solicitado
                    if gerar_agora:
                        num, comp = obter_sequencial_a3(df_a3)
                        df_a3.at[idx, "numero"] = num
                        df_a3.at[idx, "numero_completo"] = comp
                        df_a3.at[idx, "ano"] = datetime.now().year
                        if 'data_analise' in df_a3.columns:
                            df_a3.at[idx, "data_analise"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                    
                    # Salva no Google Sheets
                    salvar_dados_blindado(df_a3, df_master)
                    st.success(f"Nota {id_s} atualizada com sucesso!")
                    time.sleep(1)
                    st.rerun()
    else:
        st.info("Nenhuma nota A3 cadastrada para edição.")
# ================= PÁGINA 4: ADMIN =================
elif aba == "🔐 Admin":
    st.header("⚙️ Painel de Controle Avançado")
    
    # --- SUBSEÇÃO: APAGAR NOTA ÚNICA ---
    with st.expander("🗑️ Apagar Nota Específica", expanded=True):
        id_d = st.number_input("Digite o ID da nota:", min_value=1)
        pw_del = st.text_input("Senha para excluir nota:", type="password", key="pw_del")
        if st.button("Excluir Nota Selecionada"):
            if pw_del == SENHA_ADMIN:
                df_a3_novo = df_a3[df_a3["id_nota"] != id_d]
                salvar_dados_blindado(df_a3_novo, df_master)
                st.success(f"Nota {id_d} removida.")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Senha incorreta.")

    st.divider()

    # --- SUBSEÇÃO: RESET TOTAL DA BASE ---
    with st.expander("🚨 RESET TOTAL DA BASE (Cuidado!)"):
        st.error("Esta ação apagará TODAS as informações da planilha e não pode ser desfeita.")
        confirmar_reset = st.checkbox("EU TENHO CERTEZA QUE DESEJO APAGAR TUDO")
        pw_reset = st.text_input("Senha de Administrador para Reset:", type="password", key="pw_reset")
        
        if st.button("🔥 APAGAR TODA A BASE AGORA"):
            if confirmar_reset and pw_reset == SENHA_ADMIN:
                # Cria um DataFrame vazio apenas com os cabeçalhos originais
                df_reset = pd.DataFrame(columns=df_master.columns)
                conn.update(spreadsheet=URL_PLANILHA, data=df_reset)
                st.cache_data.clear()
                st.success("Base de dados resetada com sucesso!")
                time.sleep(2)
                st.rerun()
            elif not confirmar_reset:
                st.warning("Você precisa marcar o checkbox de confirmação.")
            else:
                st.error("Senha de administrador incorreta.")