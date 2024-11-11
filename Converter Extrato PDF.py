import streamlit as st
import pdfplumber
import pandas as pd
from io import BytesIO
import re

# Função para extrair dados de transações do PDF
def extract_transactions(pdf_file):
    daily_movements = []
    date_pattern = re.compile(r"^\d{2}/\d{2}$")  # Padrão para data no formato DD/MM
    current_date = None  # Armazena a data atual para transações subsequentes sem data

    with pdfplumber.open(pdf_file) as pdf:
        # Processa cada página individualmente
        for page in pdf.pages:
            lines = page.extract_text().split('\n')
            
            # Processa cada linha da página para identificar transações
            for line in lines:
                parts = line.split()
                
                # Verifica se a primeira parte é uma data válida usando o padrão
                if parts and date_pattern.match(parts[0]):
                    current_date = parts[0]  # Atualiza a data atual
                    # Separa a descrição, considerando o possível nº do documento e valores no final
                    description = " ".join(parts[1:-2]) if len(parts) > 2 else ""
                    document_no = parts[-3] if len(parts) > 3 and parts[-3].isdigit() else None
                else:
                    # Caso a linha não tenha uma data, usa a data e o nº do documento anteriores
                    description = " ".join(parts[:-2]) if len(parts) > 2 else ""
                    document_no = parts[-3] if len(parts) > 3 and parts[-3].isdigit() else None
                
                # Identifica créditos e débitos com base nas duas últimas posições, com verificação de formato
                credit = None
                debit = None
                if len(parts) >= 2:
                    last_value = parts[-1]
                    second_last_value = parts[-2]
                    
                    # Verifica se o último valor é um débito (sinal "-") ou um crédito
                    if re.match(r"^\d+,\d{2}-$", last_value):  # Débito com sinal de "-"
                        debit = float(last_value[:-1].replace(",", "."))
                    elif re.match(r"^\d+,\d{2}$", last_value):  # Crédito sem sinal
                        credit = float(last_value.replace(",", "."))
                    
                    # Verifica se o penúltimo valor também é um débito ou crédito
                    if credit is None and re.match(r"^\d+,\d{2}-$", second_last_value):
                        debit = float(second_last_value[:-1].replace(",", "."))
                    elif debit is None and re.match(r"^\d+,\d{2}$", second_last_value):
                        credit = float(second_last_value.replace(",", "."))

                # Adiciona a transação à lista apenas se houver uma data e pelo menos um valor real
                if current_date and (credit is not None or debit is not None):
                    daily_movements.append({
                        "Data": current_date,
                        "Descrição": description.strip() if description else "N/A",
                        "Nº Documento": document_no if document_no else "",
                        "Receita (R$)": credit if credit is not None else 0,
                        "Despesa (R$)": debit if debit is not None else 0,
                    })
    
    # Converte a lista de transações em um DataFrame
    return pd.DataFrame(daily_movements)

# Interface do Streamlit
st.title("Organizador de Extrato Bancário")
st.write("Faça upload do seu extrato em PDF para gerar uma tabela organizada de movimentação.")

# Upload do arquivo
uploaded_file = st.file_uploader("Escolha um arquivo PDF", type="pdf")

# Processa e exibe a tabela
if uploaded_file is not None:
    transactions_df = extract_transactions(uploaded_file)
    st.write("### Movimentação Diária Completa")
    st.dataframe(transactions_df)

    # Download da tabela como Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        transactions_df.to_excel(writer, index=False)
    st.download_button(
        label="Baixar Movimentação em Excel",
        data=output.getvalue(),
        file_name="Movimentacao_Extrato_Completo_Corrigido.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )