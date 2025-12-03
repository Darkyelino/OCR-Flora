# -*- coding: utf-8 -*-
import easyocr
import re
import pandas as pd
import os
import numpy as np
from thefuzz import process, fuzz # Importando fuzz também para comparações diretas se necessário

# --- CONFIGURAÇÕES E CONSTANTES ---

MUNICIPIOS_ACRE = [
    "Acrelândia", "Assis Brasil", "Brasiléia", "Bujari", "Capixaba",
    "Cruzeiro do Sul", "Epitaciolândia", "Feijó", "Jordão", "Manoel Urbano",
    "Marechal Thaumaturgo", "Mâncio Lima", "Plácido de Castro", "Porto Acre",
    "Porto Walter", "Rio Branco", "Rodrigues Alves", "Santa Rosa do Purus",
    "Sena Madureira", "Senador Guiomard", "Tarauacá", "Xapuri"
]

MUNICIPIOS_ABREV = {
    "AB": "Assis Brasil", "CZ": "Cruzeiro do Sul", "MU": "Manoel Urbano", "MT": "Marechal Thaumaturgo", 
    "ML": "Mâncio Lima", "PC": "Plácido de Castro", "PA": "Porto Acre", 
    "PW": "Porto Walter", "RB": "Rio Branco", "RA": "Rodrigues Alves", 
    "SP": "Santa Rosa do Purus", "SM": "Sena Madureira", "SG": "Senador Guiomard"
}

ESTADOS_BRASIL = {
    'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas', 'BA': 'Bahia', 
    'CE': 'Ceará', 'DF': 'Distrito Federal', 'ES': 'Espírito Santo', 'GO': 'Goiás', 
    'MA': 'Maranhão', 'MT': 'Mato Grosso', 'MS': 'Mato Grosso do Sul', 'MG': 'Minas Gerais', 
    'PA': 'Pará', 'PB': 'Paraíba', 'PR': 'Paraná', 'PE': 'Pernambuco', 'PI': 'Piauí', 
    'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte', 'RS': 'Rio Grande do Sul', 
    'RO': 'Rondônia', 'RR': 'Roraima', 'SC': 'Santa Catarina', 'SP': 'São Paulo', 
    'SE': 'Sergipe', 'TO': 'Tocantins'
}

# --- LISTA NEGRA (BLOCKLIST) ---
PALAVRAS_IGNORADAS = [
    "ACRE", "BRASIL", "AMAZONIA", "FLORA", "PROJETO", "UNIVERSIDADE", "FEDERAL", "ESTADUAL", 
    "INSTITUTO", "JARDIM", "BOTANICO", "HORTUS", "MUSEU", "COLECAO", "COLEÇÃO", "LABORATORIO",
    "PROGRAMA", "PREFEITURA", "SECRETARIA", "DIRECAO", "DIREÇÃO", "COORDENACAO", "COORDENAÇÃO",
    "CAPES", "CNPQ", "FAPEAC", "GOVERNO", "MINISTERIO", "MINISTÉRIO", "PESQUISA", "DEPARTAMENTO",
    "EX-REAL", "MUNICÍPIO", "MUNICIPIO", "MUN", "MUNIC", "ESTADO", "RODOVIA", "ESTRADA", "FAZENDA", 
    "SÍTIO", "SITIO", "CHÁCARA", "CHACARA", "RAMAL", "IGARAPÉ", "IGARAPE", "RIO", "FLORESTA",
    "MATO", "PARQUE", "RESERVA", "ÁREA", "AREA", "PRÓXIMO", "PROXIMO", "ENTRE", "LIMITE",
    "COMUNIDADE", "VILA", "ZONA", "URBANA", "RURAL", "SUL", "NORTE", "LESTE", "OESTE", "CENTRO",
    "DATA", "COLETA", "NÚMERO", "NUMERO", "Nº", "NO", "LATITUDE", "LONGITUDE", "COORDENADAS",
    "LAT", "LONG", "ALT", "ALTURA", "METROS", "M", "KM", "HERBARIO", "HERB", "DET", "DETERMINADOR", 
    "FAMILIA", "FAMILY", "NOME", "VULGAR", "ESPÉCIE", "ESPECIE", "GÊNERO", "GENERO", "G", "COM", 
    "FLORES", "FRUTOS", "PLANTAS", "SEMENTES", "ARVORE", "ÁRVORE", "ARBUSTO", "HERBÁCEA", 
    "CAULE", "FOLHA", "TRONCO", "N.V", "N.V.", "OCCASIONAL", "SECONDARY", "FOREST", "TREE", 
    "FRUITS", "WARTY", "FIELD", "WORK", "SUPPORTED", "FOUNDATION", "PROPERTY", "OWNER"
]

# --- 1. FUNÇÃO DE EXTRAÇÃO DE TEXTO ---
def extrair_texto_com_acuracia(caminho_imagem):
    print(f"\nProcessando imagem: {os.path.basename(caminho_imagem)}")
    try:
        os.environ['EASYOCR_LOGGER'] = 'ERROR'
        reader = easyocr.Reader(['pt', 'en'], gpu=False)
        resultado_ocr = reader.readtext(caminho_imagem)
        if not resultado_ocr:
            print(" -> Nenhum texto detectado.")
            return "", 0.0
        
        texto_completo = "\n".join([res[1] for res in resultado_ocr])
        confiancas = [res[2] for res in resultado_ocr]
        media_confianca = np.mean(confiancas)
        print(f" -> Texto extraído com acurácia média de: {media_confianca:.2%}")
        return texto_completo, media_confianca
    except Exception as e:
        print(f" -> Ocorreu um erro ao processar a imagem: {e}")
        return "", 0.0

# --- 2. "ESPECIALISTAS" AUXILIARES ---
def encontrar_familia(texto):
    match = re.search(r'\b([A-Za-zÀ-ú]{3,})ACEAE\b', texto, re.IGNORECASE)
    return match.group(0) if match else ''

def encontrar_coordenadas(texto):
    lat, ns, long, ew = '', '', '', ''
    texto_limpo = re.sub(r'\s+', ' ', texto)
    match_lat = re.search(r'(\d{1,3})\D+(\d{1,2})\D+(\d{1,2}[\.,]?\d?)\D*([SN])', texto_limpo, re.IGNORECASE)
    if match_lat:
        lat = f"{match_lat.group(1)}{match_lat.group(2)}{match_lat.group(3)}".replace(',','').replace('.','')
        ns = match_lat.group(4).upper()
    match_long = re.search(r'(\d{1,3})\D+(\d{1,2})\D+(\d{1,2}[\.,]?\d?)\D*([WE])', texto_limpo, re.IGNORECASE)
    if match_long:
        long = f"{match_long.group(1)}{match_long.group(2)}{match_long.group(3)}".replace(',','').replace('.','')
        ew = match_long.group(4).upper()
    return lat, ns, long, ew

def encontrar_data_coleta(texto):
    match_num = re.search(r'\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})\b', texto)
    if match_num:
        dd, mm, yy = match_num.groups()
        if len(yy) == 2: yy = f"19{yy}" if int(yy) > 50 else f"20{yy}"
        return dd, mm, yy
    
    match_en = re.search(r'([A-Z][a-z]+)\s+(\d{1,2})\s*,\s*(\d{4})', texto)
    if match_en:
        mes_str, dia, ano = match_en.groups()
        meses = {'January':'01', 'February':'02', 'March':'03', 'April':'04', 'May':'05', 'June':'06', 
                 'July':'07', 'August':'08', 'September':'09', 'October':'10', 'November':'11', 'December':'12'}
        mes = meses.get(mes_str, '00')
        return dia, mes, ano

    return '', '', ''

# <-- VALIDAÇÃO INTELIGENTE COM FUZZY MATCHING NA BLOCKLIST -->
def validar_nome_coletor(nome):
    if len(nome) < 3: return False
    # Deve conter letras
    if not re.search(r'[a-zA-Z]', nome): return False
    
    # Normaliza o nome para comparação
    palavras_nome = nome.upper().replace(',', '').replace('.', '').split()
    
    # Prepara a lista negra completa (Termos proibidos + Locais conhecidos)
    locais_proibidos = PALAVRAS_IGNORADAS + [x.upper() for x in MUNICIPIOS_ACRE] + [x.upper() for x in ESTADOS_BRASIL.values()]
    
    # Threshold de similaridade (85 é bem rigoroso, 90 é muito seguro)
    LIMITE_SIMILARIDADE = 85 

    for p in palavras_nome:
        if len(p) < 3: continue # Ignora palavras muito curtas como "DE", "DA"
        
        # O PULO DO GATO: Fuzzy Match contra a lista negra
        # extractOne retorna (melhor_match, score)
        melhor_match, score = process.extractOne(p, locais_proibidos)
        
        if score >= LIMITE_SIMILARIDADE:
            # print(f"DEBUG: Palavra '{p}' rejeitada por parecer demais com '{melhor_match}' (Score: {score})")
            return False
            
    return True

# --- 3. ESPECIALISTA DE COLETOR (VERSÃO CASCATA ROBUSTA) ---
def encontrar_coletor_info(texto):
    texto_plano = re.sub(r'\s+', ' ', texto)
    
    collector, number, addcoll = '', '', ''

    # Regex para encontrar datas
    padrao_data = r'(?:\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})'
    
    matches_data = list(re.finditer(padrao_data, texto_plano, re.IGNORECASE))
    
    if not matches_data:
        return encontrar_coletor_sem_data(texto_plano)

    # Itera sobre as datas encontradas (da última para a primeira)
    for match_data in reversed(matches_data):
        texto_anterior = texto_plano[:match_data.start()].strip()
        texto_posterior = texto_plano[match_data.end():].strip()

        # Busca número antes da data
        match_numero = re.search(r'(.*?)[\s,;]*(?:n[ºo\.]?|com|col\.|no\.)?[\s,]*(\d{1,6})[\s,;-]*$', texto_anterior, re.IGNORECASE)

        if match_numero:
            raw_name = match_numero.group(1).strip()
            number = match_numero.group(2).strip()
        else:
            raw_name = texto_anterior
            number = ''

        # Limpeza do nome
        raw_name = re.sub(r'(?:;|com|n[ºo\.]?)$', '', raw_name, flags=re.IGNORECASE).strip()
        
        palavras = raw_name.split()
        if len(palavras) > 6:
            candidato_nome = " ".join(palavras[-6:])
        else:
            candidato_nome = raw_name

        # Validação com Fuzzy Matching
        if validar_nome_coletor(candidato_nome):
            collector = candidato_nome
            
            # Co-coletores
            addcoll = texto_posterior.split('Det.')[0].split('Data')[0].split('Field')[0].split('General')[0].strip()
            addcoll = re.sub(padrao_data, '', addcoll).strip()
            
            return collector, number, addcoll[:100]

    return encontrar_coletor_sem_data(texto_plano)

def encontrar_coletor_sem_data(texto_plano):
    # Fallback: Procura por "Coletor:", "Leg." ou padrão "Nome, I. 123"
    
    match = re.search(r'(?:Coletor|Leg\.|Col\.)\s*:?\s*([A-Za-z\.\s,]+?)(?:\s+(\d{1,5}))?', texto_plano, re.IGNORECASE)
    if match:
        nome = match.group(1).strip()
        num = match.group(2).strip() if match.group(2) else ''
        if validar_nome_coletor(nome): return nome, num, ''

    match = re.search(r'([A-Z][a-z]+,\s*[A-Z\.]+)\s+(\d{1,5})', texto_plano)
    if match:
        nome = match.group(1).strip()
        num = match.group(2).strip()
        if validar_nome_coletor(nome): return nome, num, ''

    return '', '', ''

def encontrar_localizacao(texto):
    country, majorarea, minorarea = '', '', ''
    SIMILARITY_THRESHOLD = 80
    
    texto_plano = re.sub(r'\s+', ' ', texto)

    if 'brasil' in texto.lower() or 'brazil' in texto.lower():
        country = 'Brasil'

    if not minorarea:
        match_abrev = re.search(r'\b([A-Z]{2,})\b\s*[-/]\s*\b(AC)\b', texto_plano, re.IGNORECASE)
        if match_abrev:
            abrev_potencial = match_abrev.group(1).upper()
            best_match_abrev, score = process.extractOne(abrev_potencial, MUNICIPIOS_ABREV.keys())
            if score >= SIMILARITY_THRESHOLD:
                minorarea = MUNICIPIOS_ABREV[best_match_abrev]

    if not minorarea:
        match_prefix = re.search(r'(?:Mun[ií]c[ií]pio\s+de|Mun\.?|Municipality\s+of)\s+([A-Za-z\sÀ-ú]+)', texto_plano, re.IGNORECASE)
        if match_prefix:
            cidade_potencial = match_prefix.group(1).strip()
            best_match, score = process.extractOne(cidade_potencial, MUNICIPIOS_ACRE)
            if score >= SIMILARITY_THRESHOLD:
                minorarea = best_match

    if not minorarea:
        for cidade in MUNICIPIOS_ACRE:
            if re.search(r'\b' + re.escape(cidade) + r'\b', texto_plano, re.IGNORECASE):
                minorarea = cidade
                break

    if minorarea:
        majorarea = 'Acre'
        country = 'Brasil'
    elif not country: 
        texto_upper = texto.upper()
        for sigla, nome in ESTADOS_BRASIL.items():
            if f' {sigla} ' in texto_upper or f'-{sigla}' in texto_upper or f' {nome.upper()} ' in texto_upper:
                majorarea = nome
                country = 'Brasil'
                break
                
    return country, majorarea, minorarea

# --- 3. FUNÇÃO ORQUESTRADORA DO PARSER ---
def parse_texto_etiqueta(texto):
    dados = {}
    dados['family'] = encontrar_familia(texto)
    dados['lat'], dados['NS'], dados['long'], dados['EW'] = encontrar_coordenadas(texto)
    dados['colldd'], dados['collmm'], dados['collyy'] = encontrar_data_coleta(texto)
    dados['collector'], dados['number'], dados['addcoll'] = encontrar_coletor_info(texto)
    dados['country'], dados['majorarea'], dados['minorarea'] = encontrar_localizacao(texto)
    return dados

# --- 4. FLUXO DE EXECUÇÃO PRINCIPAL ---
def main():
    pasta_imagens = "imagens_para_processar"
    arquivo_saida_excel = "dados_coleta_plantas.xlsx"
    if not os.path.exists(pasta_imagens):
        print(f"Erro: A pasta '{pasta_imagens}' não foi encontrada.")
        return
    lista_resultados = []
    arquivos_imagens = [f for f in os.listdir(pasta_imagens) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not arquivos_imagens:
        print(f"Nenhuma imagem encontrada na pasta '{pasta_imagens}'.")
        return
    for nome_arquivo in arquivos_imagens:
        caminho_completo = os.path.join(pasta_imagens, nome_arquivo)
        texto, acuracia = extrair_texto_com_acuracia(caminho_completo)
        if texto:
            dados_extraidos = parse_texto_etiqueta(texto)
            dados_extraidos['arquivo_origem'] = nome_arquivo
            dados_extraidos['acuracia_ocr'] = f"{acuracia:.2%}"
            dados_extraidos['texto_bruto_ocr'] = texto
            lista_resultados.append(dados_extraidos)
    if not lista_resultados:
        print("\nNenhum dado foi extraído.")
        return
    print(f"\nProcesso finalizado. Salvando {len(lista_resultados)} registros em '{arquivo_saida_excel}'...")
    df = pd.DataFrame(lista_resultados)
    ordem_colunas = [
        'arquivo_origem', 'acuracia_ocr', 'family', 'collector', 'number', 'addcoll',
        'colldd', 'collmm', 'collyy', 'country', 'majorarea', 'minorarea', 
        'lat', 'NS', 'long', 'EW', 'texto_bruto_ocr'
    ]
    colunas_finais = ordem_colunas + [col for col in df.columns if col not in ordem_colunas]
    df = df[colunas_finais]
    df.to_excel(arquivo_saida_excel, index=False)
    print("Arquivo salvo com sucesso!")

if __name__ == "__main__":
    main()