from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_file
import sqlite3
import json
import re
import uuid
from datetime import datetime
import bcrypt
from init_db import criar_banco
from functools import wraps
from flask_login import LoginManager, UserMixin, login_required, current_user, login_user, logout_user
import os
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as ImageReader
from reportlab.platypus import Image
import logging
from collections import Counter, defaultdict

# Configuração do logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__, 
            static_folder='static', 
            static_url_path='/static')
app.secret_key = os.urandom(24).hex()

# === INICIALIZA O LoginManager ===
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, role=None):
        self.id = id
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, role FROM usuarios WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return User(row['id'], row['role'])
    return None

# Criar o banco de dados
criar_banco()

# Registrar a fonte personalizada para o PDF
try:
    pdfmetrics.registerFont(TTFont('Poppins', 'static/fonts/Poppins-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('Poppins-Bold', 'static/fonts/Poppins-Bold.ttf'))
except Exception as e:
    logging.error(f"Erro ao registrar fontes Poppins: {str(e)}")

# Mapeamento de macrorregiões, regiões e municípios
regioes_por_macrorregiao = {
    '1ª': {
        '1ª': ['Alhandra', 'Bayeux', 'Caaporã', 'Cabedelo', 'Conde', 'Cruz do Espírito Santo', 'João Pessoa', 'Lucena', 'Mari', 'Pitimbu', 'Riachão do Poço', 'Santa Rita', 'Sapé', 'Sobrado'],
        '2ª': ['Alagoinha', 'Araçagi', 'Araruna', 'Bananeiras', 'Belém', 'Borborema', 'Cacimba de Dentro', 'Caiçara', 'Casserengue', 'Cuitegi', 'Dona Inês', 'Duas Estradas', 'Guarabira', 'Lagoa de Dentro', 'Logradouro', 'Mulungu', 'Pilões', 'Pilõezinhos', 'Pirpirituba', 'Riachão', 'Serra da Raiz', 'Serraria', 'Sertãozinho', 'Solânea', 'Tacima'],
        '12ª': ['Caldas Brandão', 'Gurinhém', 'Ingá', 'Itabaiana', 'Itatuba', 'Juarez Távora', 'Juripiranga', 'Mogeiro', 'Pedras de Fogo', 'Pilar', 'Riachão do Bacamarte', 'Salgado de São Félix', 'São José dos Ramos', 'São Miguel de Taipu'],
        '14ª': ['Baía da Traição', 'Capim', 'Cuité de Mamanguape', 'Curral de Cima', 'Itapororoca', 'Jacaraú', 'Marcação', 'Mamanguape', 'Mataraca', 'Pedro Régis', 'Rio Tinto']
    },
    '2ª': {
        '3ª': ['Alagoa Grande', 'Alagoa Nova', 'Algodão de Jandaíra', 'Arara', 'Areia', 'Areial', 'Esperança', 'Lagoa Seca', 'Matinhas', 'Montadas', 'Remígio', 'São Sebastião de Lagoa de Roça'],
        '4ª': ['Baraúna', 'Barra de Santana', 'Cubati', 'Cuité', 'Damião', 'Frei Martinho', 'Nova Floresta', 'Nova Palmeira', 'Pedra Lavrada', 'Picuí', 'São Vicente do Seridó', 'Sossêgo'],
        '5ª': ['Amparo', 'Camalaú', 'Caraúbas', 'Congo', 'Coxixola', 'Gurjão', 'Monteiro', 'Ouro Velho', 'Parari', 'Prata', 'São João do Cariri', 'São João do Tigre', 'São José dos Cordeiros', 'São Sebastião do Umbuzeiro', 'Serra Branca', 'Sumé', 'Zabelê'],
        '15ª': ['Alcantil', 'Aroeiras', 'Barra de Santa Rosa', 'Barra de São Miguel', 'Boqueirão', 'Cabaceiras', 'Caturité', 'Gado Bravo', 'Natuba', 'Queimadas', 'Riacho de Santo Antônio', 'Santa Cecília', 'São Domingos do Cariri', 'Umbuzeiro'],
        '16ª': ['Assunção', 'Boa Vista', 'Campina Grande', 'Fagundes', 'Juazeirinho', 'Livramento', 'Massaranduba', 'Olivedos', 'Pocinhos', 'Puxinanã', 'Santo André', 'Serra Redonda', 'Soledade', 'Taperoá', 'Tenório']
    },
    '3ª': {
        '6ª': ['Areia de Baraúnas', 'Cacimba de Areia', 'Cacimbas', 'Catingueira', 'Condado', 'Desterro', 'Emas', 'Junco do Seridó', 'Mãe d\'Água', 'Malta', 'Maturéia', 'Passagem', 'Patos', 'Quixaba', 'Salgadinho', 'Santa Luzia', 'Santa Teresinha', 'São José de Espinharas', 'São José do Bonfim', 'São José do Sabugi', 'São Mamede', 'Teixeira', 'Várzea', 'Vista Serrana'],
        '7ª': ['Aguiar', 'Boa Ventura', 'Conceição', 'Coremas', 'Curral Velho', 'Diamante', 'Ibiara', 'Igaracy', 'Itaporanga', 'Nova Olinda', 'Olho d\'Água', 'Pedra Branca', 'Piancó', 'Santa Inês', 'Santana de Mangueira', 'Santana dos Garrotes', 'São José de Caiana', 'Serra Grande'],
        '8ª': ['Belém do Brejo do Cruz', 'Bom Sucesso', 'Brejo do Cruz', 'Brejo dos Santos', 'Catolé do Rocha', 'Jericó', 'Mato Grosso', 'Riacho dos Cavalos', 'São Bento', 'São José do Brejo do Cruz'],
        '9ª': ['Bernardino Batista', 'Bom Jesus', 'Bonito de Santa Fé', 'Cachoeira dos Índios', 'Cajazeiras', 'Carrapateira', 'Joca Claudino', 'Monte Horebe', 'Poço Dantas', 'Poço de José de Moura', 'Santa Helena', 'São João do Rio do Peixe', 'São José de Piranhas', 'Triunfo', 'Uiraúna'],
        '10ª': ['Aparecida', 'Lastro', 'Marizópolis', 'Nazarezinho', 'Santa Cruz', 'São Francisco', 'São José da Lagoa Tapada', 'Sousa', 'Vieirópolis'],
        '11ª': ['Água Branca', 'Imaculada', 'Juru', 'Manaíra', 'Princesa Isabel', 'São José de Princesa', 'Tavares'],
        '13ª': ['Cajazeirinhas', 'Lagoa', 'Paulista', 'Pombal', 'São Bentinho', 'São Domingos']
    }
}

# Função auxiliar para encontrar macrorregião e região de um município
def find_macrorregiao_regiao(municipio):
    for macro, regioes in regioes_por_macrorregiao.items():
        for regiao, municipios in regioes.items():
            if municipio in municipios:
                return macro, regiao
    return None, None

# Mapeamento para deficiência
DEFICIENCIA_MAP = {
    'Sim': 'Sim',
    'Não': 'Não',
    'Não informado': 'Não informado',
    'nao_informado': 'Não informado'
}

# Mapeamento para gênero
GENERO_MAP = {
    'mulher_cisgenero': 'Mulher Cisgênero',
    'homem_trans': 'Homem Trans',
    'pessoa_nao_binaria': 'Pessoa Não-Binária',
    'outro': 'Outro',
    'nao_informado': 'Não Informado'
}

# Mapeamento para sexualidade
SEXUALIDADE_MAP = {
    'heterossexual': 'Heterossexual',
    'homossexual': 'Homossexual',
    'bissexual': 'Bissexual',
    'outro': 'Outro',
    'nao_informado': 'Não Informado'
}

# Mapeamento para raça/cor/etnia
RACA_COR_ETNIA_MAP = {
    'branca': 'Branca',
    'preta': 'Preta',
    'parda': 'Parda',
    'amarela': 'Amarela',
    'indigena': 'Indígena',
    'indígena': 'Indígena',  # aceita com acento também
    'indigena ': 'Indígena', # com espaço
    '': 'Não informado',
    None: 'Não informado'
}

def get_etnia_nome(etnia_codigo):
    """Converte código de etnia para nome (COMPLETO - igual ao HTML)"""
    ETNIA_MAP = {
        # Não declarar
        'nao_declarar': 'Não declarar',
        
        # Etnias principais (0001-0264)
        '0001': 'ACONAS (WAKONAS, NACONAS, JAKONA, ACORANES)',
        '0002': 'AIKANA (AIKANA, MAS SAKA,TUBARAO)',
        '0003': 'AJURU',
        '0004': 'AKUNSU (AKUNT\'\'SU)',
        '0005': 'AMANAYE',
        '0006': 'AMONDAWA',
        '0007': 'ANAMBE',
        '0008': 'APARAI (APALAI)',
        '0009': 'APIAKA (APIACA)',
        '0010': 'APINAYE (APINAJE/APINAIE/APINAGE)',
        '0011': 'APURINA (APORINA, IPURINA, IPURINAN)',
        '0012': 'ARANA (ARACUAI DO VALE DO JEQUITINHONHA)',
        '0013': 'ARAPASO (ARAPACO)',
        '0014': 'ARARA DE RONDONIA (KARO, URUCU, URUKU)',
        '0015': 'ARARA DO ACRE (SHAWANAUA, AMAWAKA)',
        '0016': 'ARARA DO ARIPUANA (ARARA DO BEIRADAO/ARI-PUANA)',
        '0017': 'ARARA DO PARA (UKARAGMA, UKARAMMA)',
        '0018': 'ARAWETE (ARAUETE)',
        '0019': 'ARIKAPU (ARICAPU, ARIKAPO, MASUBI, MAXUBI)',
        '0020': 'ARIKEM (ARIQUEN, ARIQUEME, ARIKEME)',
        '0021': 'ARIKOSE (ARICOBE)',
        '0022': 'ARUA',
        '0023': 'ARUAK (ARAWAK)',
        '0024': 'ASHANINKA (KAMPA)',
        '0025': 'ASURINI DO TOCANTINS (AKUAWA/AKWAWA)',
        '0026': 'ASURINI DO XINGU (AWAETE)',
        '0027': 'ATIKUM (ATICUM)',
        '0028': 'AVA - CANOEIRO',
        '0029': 'AWETI (AUETI/AUETO)',
        '0030': 'BAKAIRI (KURA, BACAIRI)',
        '0031': 'BANAWA YAFI (BANAWA, BANAWA-JAFI)',
        '0032': 'BANIWA (BANIUA, BANIVA, WALIMANAI, WAKUENAI)',
        '0033': 'BARA (WAIPINOMAKA)',
        '0034': 'BARASANA (HANERA)',
        '0035': 'BARE',
        '0036': 'BORORO (BOE)',
        '0037': 'BOTOCUDO (GEREN)',
        '0038': 'CANOE',
        '0039': 'CASSUPA',
        '0040': 'CHAMACOCO',
        '0041': 'CHIKUITANO (XIQUITANO)',
        '0042': 'CIKIYANA (SIKIANA)',
        '0043': 'CINTA LARGA (MATETAMAE)',
        '0044': 'COLUMBIARA (CORUMBIARA)',
        '0045': 'DENI',
        '0046': 'DESANA (DESANA, DESANO, DESSANO, WIRA, UMUKOMASA)',
        '0047': 'DIAHUI (JAHOI, JAHUI, DIARROI)',
        '0048': 'ENAWE-NAWE (SALUMA)',
        '0049': 'FULNI-O',
        '0050': 'GALIBI (GALIBI DO OIAPOQUE, KARINHA)',
        '0051': 'GALIBI MARWORNO (GALIBI DO UACA, ARUA)',
        '0052': 'GAVIAO DE RONDONIA (DIGUT)',
        '0053': 'GAVIAO KRIKATEJE',
        '0054': 'GAVIAO PARKATEJE (PARKATEJE)',
        '0055': 'GAVIAO PUKOBIE (PUKOBIE, PYKOPJE, GAVIAO DO MARANHAO)',
        '0056': 'GUAJA (AWA, AVA)',
        '0057': 'GUAJAJARA (TENETEHARA)',
        '0058': 'GUARANI KAIOWA (PAI TAVYTERA)',
        '0059': 'GUARANI M\'\'BYA',
        '0060': 'GUARANI NANDEVA (AVAKATUETE, CHIRIPA,NHANDEWA, AVA GUARANI)',
        '0061': 'GUATO',
        '0062': 'HIMARIMA (HIMERIMA)',
        '0063': 'INGARIKO (INGARICO, AKAWAIO, KAPON)',
        '0064': 'IRANXE (IRANTXE)',
        '0065': 'ISSE',
        '0066': 'JABOTI (JABUTI, KIPIU, YABYTI)',
        '0067': 'JAMAMADI (YAMAMADI, DJEOROMITXI)',
        '0068': 'JARAWARA',
        '0069': 'JIRIPANCO (JERIPANCO, GERIPANCO)',
        '0070': 'JUMA (YUMA)',
        '0071': 'JURUNA',
        '0072': 'JURUTI (YURITI)',
        '0073': 'KAAPOR (URUBU-KAAPOR, KA\'\'APOR, KAAPORTE)',
        '0074': 'KADIWEU (CADUVEO, CADIUEU)',
        '0075': 'KAIABI (CAIABI, KAYABI)',
        '0076': 'KAIMBE (CAIMBE)',
        '0077': 'KAINGANG (CAINGANGUE)',
        '0078': 'KAIXANA (CAIXANA)',
        '0079': 'KALABASSA (CALABASSA, CALABACAS)',
        '0080': 'KALANCO',
        '0081': 'KALAPALO (CALAPALO)',
        '0082': 'KAMAYURA (CAMAIURA, KAMAIURA)',
        '0083': 'KAMBA (CAMBA)',
        '0084': 'KAMBEBA (CAMBEBA, OMAGUA)',
        '0085': 'KAMBIWA (CAMBIUA)',
        '0086': 'KAMBIWA PIPIPA (PIPIPA)',
        '0087': 'KAMPE',
        '0088': 'KANAMANTI (KANAMATI, CANAMANTI)',
        '0089': 'KANAMARI (CANAMARI, KANAMARY, TUKUNA)',
        '0090': 'KANELA APANIEKRA (CANELA)',
        '0091': 'KANELA RANKOKAMEKRA (CANELA)',
        '0092': 'KANINDE',
        '0093': 'KANOE (CANOE)',
        '0094': 'KANTARURE (CANTARURE)',
        '0095': 'KAPINAWA (CAPINAUA)',
        '0096': 'KARAJA (CARAJA)',
        '0097': 'KARAJA/JAVAE (JAVAE)',
        '0098': 'KARAJA/XAMBIOA (KARAJA DO NORTE)',
        '0099': 'KARAPANA (CARAPANA, MUTEAMASA, UKOPINOPONA)',
        '0100': 'KARAPOTO (CARAPOTO)',
        '0101': 'KARIPUNA (CARIPUNA)',
        '0102': 'KARIPUNA DO AMAPA (CARIPUNA)',
        '0103': 'KARIRI (CARIRI)',
        '0104': 'KARIRI-XOCO (CARIRI-CHOCO)',
        '0105': 'KARITIANA (CARITIANA)',
        '0106': 'KATAWIXI (KATAUIXI,KATAWIN, KATAWISI, CATAUICHI)',
        '0107': 'KATUENA (CATUENA, KATWENA)',
        '0108': 'KATUKINA (PEDA DJAPA)',
        '0109': 'KATUKINA DO ACRE',
        '0110': 'KAXARARI (CAXARARI)',
        '0111': 'KAXINAWA (HUNI-KUIN, CASHINAUA, CAXINAUA)',
        '0112': 'KAXIXO',
        '0113': 'KAXUYANA (CAXUIANA)',
        '0114': 'KAYAPO (CAIAPO)',
        '0115': 'KAYAPO KARARAO (KARARAO)',
        '0116': 'KAYAPO TXUKAHAMAE (TXUKAHAMAE)',
        '0117': 'KAYAPO XICRIM (XIKRIN)',
        '0118': 'KAYUISANA (CAIXANA, CAUIXANA, KAIXANA)',
        '0119': 'KINIKINAWA (GUAN, KOINUKOEN, KINIKINAO)',
        '0120': 'KIRIRI',
        '0121': 'KOCAMA (COCAMA, KOKAMA)',
        '0122': 'KOKUIREGATEJE',
        '0123': 'KORUBO',
        '0124': 'KRAHO (CRAO, KRAO)',
        '0125': 'KREJE (KRENYE)',
        '0126': 'KRENAK (BORUN, CRENAQUE)',
        '0127': 'KRIKATI (KRINKATI)',
        '0128': 'KUBEO (CUBEO, COBEWA, KUBEWA, PAMIWA, CUBEU)',
        '0129': 'KUIKURO (KUIKURU, CUICURO)',
        '0130': 'KUJUBIM (KUYUBI, CUJUBIM)',
        '0131': 'KULINA PANO (CULINA)',
        '0132': 'KULINA/MADIHA (CULINA, MADIJA, MADIHA)',
        '0133': 'KURIPAKO (CURIPACO, CURRIPACO, CORIPACO, WAKUENAI)',
        '0134': 'KURUAIA (CURUAIA)',
        '0135': 'KWAZA (COAIA, KOAIA)',
        '0136': 'MACHINERI (MANCHINERI, MANXINERI)',
        '0137': 'MACURAP (MAKURAP)',
        '0138': 'MAKU DOW (DOW)',
        '0139': 'MAKU HUPDA (HUPDA)',
        '0140': 'MAKU NADEB (NADEB)',
        '0141': 'MAKU YUHUPDE (YUHUPDE)',
        '0142': 'MAKUNA (MACUNA, YEBA-MASA)',
        '0143': 'MAKUXI (MACUXI, MACHUSI, PEMON)',
        '0144': 'MARIMAM (MARIMA)',
        '0145': 'MARUBO',
        '0146': 'MATIPU',
        '0147': 'MATIS',
        '0148': 'MATSE (MAYORUNA)',
        '0149': 'MAXAKALI (MAXACALI)',
        '0150': 'MAYA (MAYA)',
        '0151': 'MAYTAPU',
        '0152': 'MEHINAKO (MEINAKU, MEINACU)',
        '0153': 'MEKEN (MEQUEM, MEKHEM, MICHENS)',
        '0154': 'MENKY (MYKY, MUNKU, MENKI, MYNKY)',
        '0155': 'MIRANHA (MIRANHA, MIRANA)',
        '0156': 'MIRITI TAPUIA (MIRITI-TAPUYA, BUIA-TAPUYA)',
        '0157': 'MUNDURUKU (MUNDURUCU)',
        '0158': 'MURA',
        '0159': 'NAHUKWA (NAFUQUA)',
        '0160': 'NAMBIKWARA DO CAMPO (HALOTESU, KITHAULU, WAKALITESU, SAWENTES, MANDUKA)',
        '0161': 'NAMBIKWARA DO NORTE (NEGAROTE ,MAMAINDE, LATUNDE, SABANE E MANDUKA, TAWANDE)',
        '0162': 'NAMBIKWARA DO SUL (WASUSU ,HAHAINTESU, ALANTESU, WAIKISU, ALAKETESU, WASUSU, SARARE)',
        '0163': 'NARAVUTE (NARUVOTO)',
        '0164': 'NAWA (NAUA)',
        '0165': 'NUKINI (NUQUINI, NUKUINI)',
        '0166': 'OFAIE (OFAYE-XAVANTE)',
        '0167': 'ORO WIN',
        '0168': 'PAIAKU (JENIPAPO-KANINDE)',
        '0169': 'PAKAA NOVA (WARI, PACAAS NOVOS)',
        '0170': 'PALIKUR (AUKWAYENE, AUKUYENE, PALIKU\'\'ENE)',
        '0171': 'PANARA (KRENHAKARORE , KRENAKORE, KRENA-KARORE)',
        '0172': 'PANKARARE (PANCARARE)',
        '0173': 'PANKARARU (PANCARARU)',
        '0174': 'PANKARARU KALANKO (KALANKO)',
        '0175': 'PANKARARU KARUAZU (KARUAZU)',
        '0176': 'PANKARU (PANCARU)',
        '0177': 'PARAKANA (PARACANA, APITEREWA, AWAETE)',
        '0178': 'PARECI (PARESI, HALITI)',
        '0179': 'PARINTINTIN',
        '0180': 'PATAMONA (KAPON)',
        '0181': 'PATAXO',
        '0182': 'PATAXO HA-HA-HAE',
        '0183': 'PAUMARI (PALMARI)',
        '0184': 'PAUMELENHO',
        '0185': 'PIRAHA (MURA PIRAHA)',
        '0186': 'PIRATUAPUIA (PIRATAPUYA, PIRATAPUYO, PIRA-TAPUYA, WAIKANA)',
        '0187': 'PITAGUARI',
        '0188': 'POTIGUARA',
        '0189': 'POYANAWA (POIANAUA)',
        '0190': 'RIKBAKTSA (CANOEIROS, ERIGPAKTSA)',
        '0191': 'SAKURABIAT(MEKENS, SAKIRABIAP, SAKIRABIAR)',
        '0192': 'SATERE-MAWE (SATERE-MAUE)',
        '0193': 'SHANENAWA (KATUKINA)',
        '0194': 'SIRIANO (SIRIA-MASA)',
        '0195': 'SURIANA',
        '0196': 'SURUI DE RONDONIA (PAITER)',
        '0197': 'SURUI DO PARA (AIKEWARA)',
        '0198': 'SUYA (SUIA/KISEDJE)',
        '0199': 'TAPAYUNA (BEICO-DE-PAU)',
        '0200': 'TAPEBA',
        '0201': 'TAPIRAPE (TAPI\'\'IRAPE)',
        '0202': 'TAPUIA (TAPUIA-XAVANTE, TAPUIO)',
        '0203': 'TARIANO (TARIANA, TALIASERI)',
        '0204': 'TAUREPANG (TAULIPANG, PEMON, AREKUNA, PAGEYN)',
        '0205': 'TEMBE',
        '0206': 'TENHARIM',
        '0207': 'TERENA',
        '0208': 'TICUNA (TIKUNA, TUKUNA, MAGUTA)',
        '0209': 'TINGUI BOTO',
        '0210': 'TIRIYO EWARHUYANA (TIRIYO, TRIO, TARONA, YAWI, PIANOKOTO)',
        '0211': 'TIRIYO KAH\'\'YANA (TIRIYO, TRIO, TARONA, YAWI, PIANOKOTO)',
        '0212': 'TIRIYO TSIKUYANA (TIRIYO, TRIO, TARONA, YAWI, PIANOKOTO)',
        '0213': 'TORA',
        '0214': 'TREMEMBE',
        '0215': 'TRUKA',
        '0216': 'TRUMAI',
        '0217': 'TSOHOM DJAPA (TSUNHUM-DJAPA)',
        '0218': 'TUKANO (TUCANO, YE\'\'PA-MASA, DASEA)',
        '0219': 'TUMBALALA',
        '0220': 'TUNAYANA',
        '0221': 'TUPARI',
        '0222': 'TUPINAMBA',
        '0223': 'TUPINIQUIM',
        '0224': 'TURIWARA',
        '0225': 'TUXA',
        '0226': 'TUYUKA (TUIUCA, DOKAPUARA, UTAPINOMAKAPHONA)',
        '0227': 'TXIKAO (TXICAO, IKPENG)',
        '0228': 'UMUTINA (OMOTINA, BARBADOS)',
        '0229': 'URU-EU-WAU-WAU (URUEU-UAU-UAU, URUPAIN, URUPA)',
        '0230': 'WAI WAI HIXKARYANA (HIXKARYANA)',
        '0231': 'WAI WAI KARAFAWYANA (KARAFAWYANA, KARA-PAWYANA)',
        '0232': 'WAI WAI XEREU (XEREU)',
        '0233': 'WAI WAI KATUENA (KATUENA)',
        '0234': 'WAI WAI MAWAYANA (MAWAYANA)',
        '0235': 'WAIAPI (WAYAMPI, OYAMPI, WAYAPY)',
        '0236': 'WAIMIRI ATROARI (KINA)',
        '0237': 'WANANO (UANANO, WANANA)',
        '0238': 'WAPIXANA (UAPIXANA, VAPIDIANA, WAPISIANA, WAPISHANA)',
        '0239': 'WAREKENA (UAREQUENA, WEREKENA)',
        '0240': 'WASSU',
        '0241': 'WAURA (UAURA, WAUJA)',
        '0242': 'WAYANA (WAIANA, UAIANA)',
        '0243': 'WITOTO (UITOTO, HUITOTO)',
        '0244': 'XAKRIABA (XACRIABA)',
        '0245': 'XAVANTE (A\'\'UWE, AKWE, AWEN, AKWEN)',
        '0246': 'XERENTE (AKWE, AWEN, AKWEN)',
        '0247': 'XETA',
        '0248': 'XIPAIA (SHIPAYA, XIPAYA)',
        '0249': 'XOKLENG (SHOKLENG, XOCLENG)',
        '0250': 'XOKO (XOCO, CHOCO)',
        '0251': 'XUKURU (XUCURU)',
        '0252': 'XUKURU KARIRI (XUCURU-KARIRI)',
        '0253': 'YAIPIYANA',
        '0254': 'YAMINAWA (JAMINAWA, IAMINAWA)',
        '0255': 'YANOMAMI NINAM (IANOMAMI, IANOAMA, XIRIANA)',
        '0256': 'YANOMAMI SANUMA (IANOMAMI, IANOAMA, XIRIANA)',
        '0257': 'YANOMAMI YANOMAM (IANOMAMI, IANOAMA, XIRIANA)',
        '0258': 'YAWALAPITI (IAUALAPITI)',
        '0259': 'YAWANAWA (IAUANAUA)',
        '0260': 'YEKUANA (MAIONGON, YE\'\'KUANA, YEKWANA, MAYONGONG)',
        '0261': 'YUDJA (JURUNA, YURUNA)',
        '0262': 'ZO\'\'E (POTURU)',
        '0263': 'ZORO (PAGEYN)',
        '0264': 'ZURUAHA (SOROWAHA, SURUWAHA)',
        
        # Códigos Xxxx (extensões)
        'X265': 'AHANENAWA',
        'X266': 'AICABA',
        'X267': 'AIKANÃ-KWASÁ',
        'X268': 'AKUNTSU',
        'X269': 'ALANTESU',
        'X271': 'AMAWÁKA',
        'X272': 'ANACÉ',
        'X273': 'APURINÃ',
        'X274': 'ARANÃ',
        'X275': 'ARAPAÇO',
        'X276': 'ARARA APOLIMA',
        'X277': 'ARARA DO ARIPUANA',
        'X278': 'ARIPUANÁ',
        'X279': 'ASSURINI',
        'X280': 'AWUARÁ',
        'X281': 'BORBA',
        'X282': 'CABIXI',
        'X283': 'CAMARARÉ',
        'X284': 'CAMASURI',
        'X285': 'CARA PRETA',
        'X286': 'CHARRUA',
        'X287': 'CUJUBIM',
        'X288': 'DAW',
        'X289': 'GAVIÃO',
        'X290': 'GUARANI',
        'X291': 'HALANTESU',
        'X292': 'HALOTESU',
        'X293': 'HENGATÚ',
        'X294': 'HIXKARYANA',
        'X295': 'HUPDE',
        'X296': 'HUPDES',
        'X297': 'IAUANAUA',
        'X298': 'IAUARETE AÇU',
        'X299': 'IKPENG',
        'X300': 'INAMBU',
        'X301': 'INHABARANA',
        'X302': 'JAVAE',
        'X303': 'JENIPAPO',
        'X304': 'JENIPAPO-KANINDE',
        'X305': 'JIAHOI',
        'X306': 'KAIOWA',
        'X307': 'KAMPA',
        'X308': 'KANELA',
        'X309': 'KARAFAWYANA',
        'X310': 'KARARAO',
        'X311': 'KARUBO',
        'X312': 'KASSUPÁ',
        'X313': 'KATITHÃULU',
        'X314': 'KATOKIN',
        'X315': 'KATUKINA PANO',
        'X316': 'KATUKINA PEDA DJAPA',
        'X317': 'KATUKINA SHANENAUWA',
        'X318': 'KAXAGO',
        'X319': 'KAYABI',
        'X320': 'KINÃ (WAIMIRI-ATROARI)',
        'X321': 'KIRIRI-BARRA',
        'X322': 'KITHÃULU',
        'X323': 'KOIAIÁ',
        'X324': 'KOIUPANKÁ',
        'X325': 'KONTANAWA',
        'X326': 'KRAHÔ KANELA',
        'X327': 'KULINA',
        'X328': 'LATUNDÊ',
        'X329': 'MAKU',
        'X330': 'MAKUNAMBÉ',
        'X331': 'MAMAINDÊ',
        'X332': 'MAMURI',
        'X333': 'MANACAPURU',
        'X334': 'MANAIRISSU',
        'X335': 'MANCHINERI',
        'X336': 'MANDUCA',
        'X337': 'MARIBONDO',
        'X338': 'MASSAKA',
        'X339': 'MAWAYANA',
        'X340': 'MAWÉ',
        'X341': 'MAYORUNA',
        'X342': 'MIQUELENO',
        'X343': 'MOKURIÑ',
        'X344': 'MON ORO WARAM',
        'X345': 'MUTUM',
        'X346': 'MYKY',
        'X347': 'NADEB',
        'X348': 'NAMBIKWARA',
        'X349': 'NEGAROTÊ',
        'X350': 'NHENGATU',
        'X351': 'OFAIE XAVANTE',
        'X352': 'ONÇA',
        'X353': 'ORO AT',
        'X354': 'ORO EO',
        'X355': 'ORO JOWIN',
        'X356': 'ORO MIYLIN',
        'X357': 'ORO MON',
        'X358': 'ORO NÁO',
        'X359': 'ORO WAM',
        'X360': 'ORO WARAM',
        'X361': 'ORO WARAM XIJEIN',
        'X362': 'PACA',
        'X363': 'PANKARÁ',
        'X364': 'PAPAGAIO',
        'X365': 'PAYAYÁ',
        'X366': 'PIPIPAN',
        'X367': 'PIRATA',
        'X368': 'PUROBORÁ',
        'X369': 'SABANÊ',
        'X370': 'SANUMA',
        'X371': 'SAWENTESÚ',
        'X372': 'SILCY-TAPUYA',
        'X373': 'SIUCI',
        'X374': 'TABAJARA',
        'X375': 'TAKUARA',
        'X376': 'TATU',
        'X377': 'TAWANDÊ',
        'X378': 'TEFÉ',
        'X379': 'TIMBIRA',
        'X380': 'TORÁ DO BAIXO GRANDE',
        'X381': 'TSUNHUM-DJAPÁ',
        'X382': 'TUBARÃO',
        'X383': 'TUPAIU',
        'X384': 'TUPI',
        'X385': 'TUPINAMBÁ DE BELMONTE',
        'X386': 'URUBU',
        'X387': 'URUBU KAAPOR',
        'X388': 'URUPÁ',
        'X389': 'WAI WAI',
        'X390': 'WAIKISU',
        'X391': 'WAKALITESÚ',
        'X392': 'WASSUSU',
        'X393': 'XEREU',
        'X394': 'XI EIN',
        'X395': 'XICRIN',
        'X396': 'XIPAYA',
        'X397': 'XIRIANA',
        'X398': 'XIRUAI',
        'X399': 'YEPAMASSÃ',
        'X400': 'TIRIYÓ',
        'X401': 'YANOMAMI',
        'X402': 'ARARA',
        'X403': 'SAKIRIABAR',
        'X404': 'TATZ',
        'X405': 'SEM INFORMACAO',
        '0304': 'PURI',
        '0315': 'WARAO',
        
        # Vazio
        '': ''
    }
    return ETNIA_MAP.get(etnia_codigo, etnia_codigo or 'Não informado')

# Mapeamentos de chaves internas para rótulos
CARACTERISTICAS_MAP = {
    '15anos': '≤ 15 anos',
    '40anos': '≥ 40 anos',
    'nao_aceita_gravidez': 'Não aceitação da gravidez',
    'violencia_domestica': 'Indícios de Violência Doméstica',
    'rua_indigena_quilombola': 'Situação de rua / indígena ou quilombola',
    'sem_escolaridade': 'Sem escolaridade',
    'tabagista_ativo': 'Tabagista ativo',
    'raca_negra': 'Raça negra',
    'situacao_rua': 'Situação de Rua',
    'quilombola': 'Quilombola',
    'indigena': 'Indígena',
}

AVALIACAO_NUTRICIONAL_MAP = {
    'baixo_peso': 'Baixo Peso (IMC < 18.5)',
    'sobrepeso': 'Sobrepeso (IMC 25-29.9)',
    'obesidade1': 'Obesidade Grau I e II (IMC 30-39.9)',
    'obesidade_morbida': 'Obesidade Mórbida (IMC ≥ 40)'
}

COMORBIDADES_MAP = {
    'aids_hiv': 'AIDS/HIV',
    'alteracoes_tireoide': 'Alterações da tireoide (hipotireoidismo sem controle e hipertireoidismo)',
    'diabetes_mellitus': 'Diabetes Mellitus',
    'endocrinopatias': 'Endocrinopatias sem controle',
    'cardiopatia': 'Cardiopatia diagnosticada',
    'cancer': 'Câncer Diagnosticado',
    'cirurgia_bariatrica': 'Cirurgia Bariátrica há menos de 1 ano',
    'doencas_autoimunes': 'Doenças Autoimunes (colagenoses)',
    'doencas_psiquiatricas': 'Doenças Psiquiátricas (Encaminhar ao CAPS)',
    'doenca_renal': 'Doença Renal Grave',
    'dependencia_drogas': 'Dependência de Drogas (Encaminhar ao CAPS)',
    'epilepsia': 'Epilepsia e doenças neurológicas graves de difícil controle',
    'hepatites': 'Hepatites (encaminhar ao infectologista)',
    'has_controlada': 'HAS crônica controlada (Sem hipotensor e exames normais)',
    'has_complicada': 'HAS crônica complicada',
    'ginecopatia': 'Ginecopatia (Miomatose ≥ 7cm, malformação uterina, massa anexial ≥ 8cm ou com características complexas)',
    'pneumopatia': 'Pneumopatia grave de difícil controle',
    'tuberculose': 'Tuberculose em tratamento ou com diagnóstico na gestação (Encaminhar ao Pneumologista)',
    'trombofilia': 'Trombofilia ou Tromboembolia',
    'teratogenico': 'Uso de medicações com potencial efeito teratogênico',
    'varizes': 'Varizes acentuadas',
    'doencas_hematologicas': 'Doenças hematológicas (PTI, Anemia Falciforme, PTT, Coagulopatias, Talassemias)',
    'transplantada': 'Transplantada em uso de imunossupressor'
}

HISTORIA_OBSTETRICA_MAP = {
    'abortamentos': '2 abortamentos espontâneos consecutivos ou 3 não consecutivos (confirmados clínico/laboratorial)',
    'abortamentos_consecutivos': '3 ou mais abortamentos espontâneos consecutivos',
    'prematuros': 'Mais de um Prematuro com menos de 36 semanas',
    'obito_fetal': 'Óbito Fetal sem causa determinada',
    'preeclampsia': 'Pré-eclâmpsia ou Pré-eclâmpsia superposta',
    'eclampsia': 'Eclâmpsia',
    'hipertensao_gestacional': 'Hipertensão Gestacional',
    'acretismo': 'Acretismo placentário',
    'descolamento_placenta': 'Descolamento prematuro de placenta',
    'insuficiencia_istmo': 'Insuficiência Istmo Cervical',
    'restricao_crescimento': 'Restrição de Crescimento Intrauterino',
    'malformacao_fetal': 'História de malformação Fetal complexa',
    'isoimunizacao': 'Isoimunização em gestação anterior',
    'diabetes_gestacional': 'Diabetes gestacional',
    'psicose_puerperal': 'Psicose Puerperal',
    'tromboembolia': 'História de tromboembolia'
}

CONDICOES_GESTACIONAIS_MAP = {
    'ameaca_aborto': 'Ameaça de aborto - Encaminhar URGÊNCIA',
    'acretismo_placentario_atual': 'Acretismo Placentário',
    'placenta_previa': 'Placenta Pós',
    'anemia_grave': 'Anemia não responsiva à tratamento (Hb≤8) e hemopatia',
    'citologia_anormal': 'Citologia Cervical anormal (LIEAG) – Encaminhar para PTGI',
    'tireoide_gestacao': 'Doenças da tireoide diagnosticada na gestação',
    'diabetes_gestacional_atual': 'Diabetes gestacional',
    'doenca_hipertensiva': 'Doença Hipertensiva na Gestação (Pré-eclâmpsia, Hipertensão gestacional e Pré-eclâmpsia superada)',
    'doppler_anormal': 'Alteração no doppler das Artérias uterinas (aumento da resistência) e/ou alto risco para Pré-eclâmpsia',
    'doenca_hemolitica': 'Doença Hemolítica',
    'gemelar': 'Gemelar',
    'isoimunizacao_rh': 'Isoimunizacao Rh',
    'insuficiencia_istmo_atual': 'Insuficiência Istmo cervical',
    'colo_curto': 'Colo curto no morfológico 2T',
    'malformacao_congenita': 'Malformação Congênita Fetal',
    'neoplasia_cancer': 'Neoplasia ginecológica ou Câncer diagnosticado na gestação',
    'polidramnio_oligodramnio': 'Polidrâmnio/Oligodrâmnio',
    'restricao_crescimento': 'Restrição de crescimento fetal Intrauterino',
    'toxoplasmose': 'Toxoplasmose',
    'sifilis_complicada': 'Sífilis terciária, Alterações ultrassom sugestivas de sífilis neonatal ou resistência ao tratamento com Penicilina Benzatina',
    'infeccao_urinaria_repeticao': 'Infecção Urinária de repetição (pielonefrite ou ITU≥3x)',
    'hiv_htlv_hepatites': 'HIV, HTLV ou Hepatites Agudas',
    'condilomacao_acuminado': 'Condiloma acuminado (no canal vaginal/colo ou lesões extensas em região genital/perianal)',
    'feto_percentil': 'Feto com percentil > P90 (GIG) ou entre P3-10 (PIG), com doppler normal',
    'hepatopatias': 'Hepatopatias (colestase ou aumento das transaminases)',
    'hanseníase': 'Hanseníase diagnosticada na gestação',
    'tuberculose_gestacao': 'Tuberculose diagnosticada na gestação',
    'dependencia_drogas_atual': 'Dependência e/ou uso abusivo de drogas lícitas e ilícitas'
}

DESFECHO_MAP = {
    'A96': 'Morte',
    'W82': 'Aborto espontâneo',
    'W83': 'Aborto provocado',
    'W90': 'Parto sem complicações de nascido vivo',
    'W91': 'Parto sem complicações de natimorto',
    'W92': 'Parto com complicações de nascido vivo',
    'W93': 'Parto com complicações de natimorto',
    '': 'Não informado',
    None: 'Não informado'
}

def get_db_connection():
    conn = sqlite3.connect('banco.db')
    conn.row_factory = sqlite3.Row
    return conn

def draw_wrapped_text(canvas, text, x, y, max_width, font='Helvetica', font_size=9):
    if not text or not isinstance(text, str) or not text.strip():
        text = "Não informado"
    
    try:
        canvas.setFont(font, font_size)
        logging.debug(f"Fonte definida: {font}, tamanho: {font_size} para texto: {text[:50]}...")
    except Exception as e:
        logging.error(f"Erro ao configurar fonte {font}: {str(e)}. Usando Helvetica como padrão.")
        canvas.setFont('Helvetica', font_size)

    lines = []
    current_line = []
    words = text.split()
    
    for word in words:
        current_line.append(word)
        test_line = ' '.join(current_line)
        if canvas.stringWidth(test_line, font, font_size) > max_width:
            current_line.pop()
            lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    
    if not lines:
        lines.append('Não informado')
    
    line_spacing = 14
    for i, line in enumerate(lines):
        canvas.drawString(x, y - i * line_spacing, line)
    
    total_lines = len(lines)
    total_text_height = total_lines * line_spacing
    new_y = y - total_text_height - 28.35
    
    return new_y

def map_item(campo, item):
    if not item or not isinstance(item, str):
        logging.warning(f"Item inválido para {campo}: {item}")
        return "Item Não Informado"

    item = item.strip()
    mapping = {
        'caracteristicas': CARACTERISTICAS_MAP,
        'avaliacao_nutricional': AVALIACAO_NUTRICIONAL_MAP,
        'comorbidades': COMORBIDADES_MAP,
        'historia_obstetrica': HISTORIA_OBSTETRICA_MAP,
        'condicoes_gestacionais': CONDICOES_GESTACIONAIS_MAP,
        'genero': GENERO_MAP,
        'sexualidade': SEXUALIDADE_MAP,
        'raca_cor_etnia': RACA_COR_ETNIA_MAP
    }.get(campo, {})
    mapped_item = mapping.get(item, item)
    if mapped_item == item:
        logging.debug(f"Item não mapeado para {campo}: {item}")
    return mapped_item

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'error')
            return redirect(url_for('login'))
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT is_admin, role, is_super_admin FROM usuarios WHERE id = ?', (session['user_id'],))
            user = cursor.fetchone()
            conn.close()
            if not user or not user['is_admin']:
                flash('Acesso negado. Apenas administradores podem acessar esta página.', 'error')
                return redirect(url_for('calculadora'))
            session['is_admin'] = user['is_admin']
            session['is_super_admin'] = user['is_super_admin']
            session['role'] = user['role']
            return f(*args, **kwargs)
        except sqlite3.OperationalError as e:
            flash(f'Erro no banco de dados: {str(e)}. Contate o administrador do banco de dados.', 'danger')
            return redirect(url_for('calculadora'))
    return decorated_function

def pnar_access_required(f):
    """Permite acesso apenas a usuários estaduais ou apoios com permissão PNAR."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verifica se o usuário está logado
        if 'user_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))

        conn = get_db_connection()
        c = conn.cursor()

        # Verifica o perfil do usuário na tabela usuarios
        c.execute("""
            SELECT role, is_super_admin 
            FROM usuarios 
            WHERE id = ?
        """, (session['user_id'],))
        user = c.fetchone()

        # Se for estadual ou super admin, libera acesso
        if user and (user['role'] == 'estadual' or user['is_super_admin'] == 1):
            conn.close()
            return f(*args, **kwargs)

        # Caso contrário, verifica se é apoio com pnar=1
        c.execute("""
            SELECT pnar 
            FROM usuarios_apoio 
            WHERE user_id = ?
        """, (session['user_id'],))
        apoio = c.fetchone()
        conn.close()

        if apoio and apoio['pnar'] == 1:
            return f(*args, **kwargs)

        flash('Você não tem permissão para acessar o PNAR.', 'danger')
        return redirect(url_for('admin_painel'))
    return decorated_function

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('password')

        if not email or not senha:
            flash('E-mail e senha são obrigatórios.', 'error')
            return redirect(url_for('login'))

        email = email.lower().strip()

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # === 1. TENTA USUÁRIO NORMAL (TABELA usuarios) ===
            cursor.execute('SELECT * FROM usuarios WHERE email = ? AND ativo = 1', (email,))
            usuario = cursor.fetchone()

            if usuario and bcrypt.checkpw(senha.encode('utf-8'), usuario['senha'].encode('utf-8')):
                if usuario['approved'] == 0:
                    flash('Sua conta ainda não foi aprovada pelo administrador.', 'error')
                    conn.close()
                    return redirect(url_for('login'))

                session['user_id'] = usuario['id']
                session['is_admin'] = usuario['is_admin']
                session['is_super_admin'] = usuario['is_super_admin']
                session['role'] = usuario['role']
                session['tipo_usuario'] = 'usuario'
                session['user_nome'] = usuario['nome']
                session['municipio'] = usuario['municipio']

                conn.close()
                flash('Login realizado com sucesso!', 'success')

                if usuario['is_admin'] or usuario['role'] in ['municipal', 'estadual']:
                    return redirect(url_for('admin_painel'))
                return redirect(url_for('calculadora'))

            # === 2. TENTA USUÁRIO DE APOIO (TABELA usuarios_apoio) ===
            cursor.execute('''
                SELECT *, acesso_saude_indigena 
                FROM usuarios_apoio 
                WHERE email = ? AND ativo = 1 AND approved = 1
            ''', (email,))
            usuario_apoio = cursor.fetchone()

            if usuario_apoio and bcrypt.checkpw(senha.encode('utf-8'), usuario_apoio['senha'].encode('utf-8')):
                session['user_id'] = usuario_apoio['id']
                session['is_admin'] = 0
                session['is_super_admin'] = 0
                session['role'] = 'apoio'
                session['tipo_usuario'] = 'apoio'
                session['user_nome'] = usuario_apoio['nome']
                session['municipio'] = usuario_apoio['municipio']
                session['acesso_saude_indigena'] = usuario_apoio['acesso_saude_indigena']  # ARMAZENA NA SESSÃO

                conn.close()
                flash('Login realizado com sucesso!', 'success')

                # REDIRECIONA DE ACORDO COM acesso_saude_indigena
                if usuario_apoio['acesso_saude_indigena'] == 1:
                    return redirect(url_for('saude_indigena'))
                else:
                    return redirect(url_for('monitoramento'))

            # === 3. FALHA NO LOGIN ===
            flash('E-mail ou senha incorretos.', 'error')
            conn.close()
            return redirect(url_for('login'))

        except Exception as e:
            if 'conn' in locals():
                conn.close()
            logging.error(f"Erro no login: {str(e)}", exc_info=True)
            flash('Erro interno. Tente novamente.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form.get('nome')
        cpf = request.form.get('cpf')
        profissao = request.form.get('profissao')
        telefone = request.form.get('telefone')
        email = request.form.get('email')
        municipio = request.form.get('municipio')
        cnes = request.form.get('cnes')
        senha = request.form.get('senha')
        confirmar_senha = request.form.get('confirmar')

        # Validações dos campos
        errors = []
        if not nome:
            errors.append("Nome é obrigatório.")
        if not cpf:
            errors.append("CPF é obrigatório.")
        else:
            # Limpeza do CPF
            cpf = re.sub(r'[^\d]', '', cpf)
            if not re.match(r'^\d{11}$', cpf):
                errors.append("CPF inválido. Deve conter 11 dígitos numéricos.")
        if not profissao:
            errors.append("Profissão é obrigatória.")
        if not telefone:
            errors.append("Telefone é obrigatório.")
        if not email:
            errors.append("E-mail é obrigatório.")
        elif not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            errors.append("E-mail inválido.")
        if not municipio:
            errors.append("Município é obrigatório.")
        if not cnes or not cnes.isdigit():
            errors.append("CNES deve conter apenas números.")
        if not senha:
            errors.append("Senha é obrigatória.")
        if senha != confirmar_senha:
            errors.append("As senhas não coincidem.")
        if len(senha) < 6:
            errors.append("A senha deve ter pelo menos 6 caracteres.")

        if errors:
            for error in errors:
                flash(error, 'error')
            return redirect(url_for('register'))

        # Normalizar e-mail para lowercase
        email = email.lower()

        # Verificar se e-mail ou CPF já existem
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, ativo, municipio FROM usuarios WHERE email = ? OR cpf = ?', (email, cpf))
        existing_user = cursor.fetchone()

        try:
            if existing_user:
                if existing_user['ativo'] == 1:
                    # Usuário ativo: impedir recadastro
                    conn.close()
                    flash('E-mail ou CPF já cadastrado e ativo. Contate o administrador.', 'error')
                    return redirect(url_for('register'))
                else:
                    # Usuário inativo: permitir recadastro, atualizando os dados
                    senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    cursor.execute('''
                        UPDATE usuarios
                        SET nome = ?, cpf = ?, profissao = ?, telefone = ?, email = ?, municipio = ?, cnes = ?, 
                            senha = ?, approved = 0, ativo = 1
                        WHERE id = ?
                    ''', (nome, cpf, profissao, telefone, email, municipio, cnes, senha_hash, existing_user['id']))
                    cursor.execute('''
                        INSERT INTO acoes_administrativas (admin_id, usuario_id, acao, data_acao, detalhes)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (None, existing_user['id'], 'Recadastro', datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                          f'Usuário ID {existing_user["id"]} recadastrado no município {municipio} (anterior: {existing_user["municipio"]})'))
                    conn.commit()
                    flash('Recadastro realizado com sucesso! Aguarde aprovação.', 'success')
                    conn.close()
                    return redirect(url_for('login'))
            else:
                # Novo usuário: inserir novo registro
                senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cursor.execute('''
                    INSERT INTO usuarios (nome, cpf, profissao, telefone, email, municipio, cnes, senha, is_admin, approved, ativo, role)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 'comum')
                ''', (nome, cpf, profissao, telefone, email, municipio, cnes, senha_hash))
                cursor.execute('''
                    INSERT INTO acoes_administrativas (admin_id, usuario_id, acao, data_acao, detalhes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (None, cursor.lastrowid, 'Cadastro Inicial', datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                      f'Novo usuário cadastrado no município {municipio}'))
                conn.commit()
                flash('Cadastro realizado com sucesso! Aguarde aprovação.', 'success')
                conn.close()
                return redirect(url_for('login'))
        except sqlite3.IntegrityError as e:
            conn.rollback()
            conn.close()
            flash('Erro ao cadastrar: E-mail ou CPF já cadastrado por outro usuário.', 'error')
            return redirect(url_for('register'))
        except sqlite3.OperationalError as e:
            conn.rollback()
            conn.close()
            flash(f'Erro no banco de dados: {str(e)}. Contate o administrador.', 'danger')
            return redirect(url_for('register'))
        except Exception as e:
            conn.rollback()
            conn.close()
            flash(f'Erro inesperado: {str(e)}', 'error')
            return redirect(url_for('register'))

    return render_template('login.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            flash('As novas senhas não coincidem.', 'error')
            return redirect(url_for('login'))

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM usuarios WHERE email = ?', (email,))
            user = cursor.fetchone()

            if user and bcrypt.checkpw(old_password.encode('utf-8'), user['senha'].encode('utf-8')):
                new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cursor.execute('UPDATE usuarios SET senha = ? WHERE email = ?', (new_password_hash, email))
                conn.commit()
                flash('Senha redefinida com sucesso! Faça login.', 'success')
            else:
                flash('E-mail ou senha atual inválidos.', 'error')

            conn.close()
            return redirect(url_for('login'))
        except sqlite3.OperationalError as e:
            flash(f'Erro no banco de dados: {str(e)}. Contate o administrador do banco de dados.', 'danger')
            return redirect(url_for('login'))

    return render_template('reset_password.html')

@app.route('/calculadora', methods=['GET'])
def calculadora():
    if 'user_id' not in session:
        flash('Por favor, faça login para acessar a calculadora.', 'error')
        return redirect(url_for('login'))

    ficha = None
    codigo_ficha = request.args.get('codigo_ficha')
    if codigo_ficha:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM calculos WHERE codigo_ficha = ? AND user_id = ?', (codigo_ficha, session['user_id']))
            ficha = cursor.fetchone()
            if ficha:
                ficha = dict(ficha)
                for field in ['caracteristicas', 'avaliacao_nutricional', 'comorbidades', 'historia_obstetrica', 'condicoes_gestacionais']:
                    if ficha[field] and isinstance(ficha[field], str):
                        try:
                            ficha[field] = json.loads(ficha[field])
                            if not isinstance(ficha[field], list):
                                ficha[field] = [ficha[field]] if ficha[field] else []
                        except json.JSONDecodeError:
                            ficha[field] = [ficha[field]] if ficha[field] else []
                    else:
                        ficha[field] = []
                # Mapear os novos campos
                ficha['genero'] = GENERO_MAP.get(ficha.get('genero', 'nao_informado'), 'Não Informado')
                ficha['sexualidade'] = SEXUALIDADE_MAP.get(ficha.get('sexualidade', 'nao_informado'), 'Não Informado')
                ficha['raca_cor_etnia'] = RACA_COR_ETNIA_MAP.get(ficha.get('raca_cor_etnia', 'nao_informado'), 'Não Informado')
                ficha['etnia_indigena'] = ETNIA_INDIGENA_MAP.get(ficha.get('etnia_indigena', ''), '')
            conn.close()
        except sqlite3.OperationalError as e:
            flash(f'Erro no banco de dados: {str(e)}. Contate o administrador do banco de dados.', 'danger')
            ficha = None
        except Exception as e:
            logging.error(f"Erro ao carregar ficha {codigo_ficha}: {str(e)}")
            flash('Erro ao carregar a ficha.', 'error')
            ficha = None

    return render_template('calculadora.html', ficha=ficha, 
                          generos=GENERO_MAP, 
                          sexualidades=SEXUALIDADE_MAP, 
                          racas_cor_etnia=RACA_COR_ETNIA_MAP)

@app.route('/salvar_calculadora', methods=['POST'])
def salvar_calculadora():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Por favor, faça login para salvar os dados.'}), 401

    try:
        logging.debug(f"Dados recebidos do formulário: {request.form}")

        # Capturar campos do formulário
        nome_gestante = request.form.get('nome_gestante')
        deficiencia = request.form.get('deficiencia')
        data_nasc = request.form.get('data_nasc')
        cpf = request.form.get('cpf', '000.000.000-00')
        telefone = request.form.get('telefone')
        municipio = request.form.get('municipio')
        ubs = request.form.get('ubs')
        acs = request.form.get('acs')
        periodo_gestacional = request.form.get('periodo_gestacional')
        data_envio = request.form.get('data_envio', datetime.now().strftime('%d/%m/%Y'))
        pontuacao_total = request.form.get('pontuacao_total')
        classificacao_risco = request.form.get('classificacao_risco', 'Risco Habitual')
        imc = request.form.get('imc', None)
        genero = request.form.get('genero')
        sexualidade = request.form.get('sexualidade')
        raca_cor_etnia = request.form.get('raca_cor_etnia')
        etnia_indigena = request.form.get('etnia_indigena', '')  # ✅ NOVO CAMPO!

        # Função para parsear campos JSON
        def parse_json_field(field_name):
            field_value = request.form.get(field_name, '[]')
            try:
                parsed = json.loads(field_value)
                if not isinstance(parsed, list):
                    parsed = [parsed] if parsed else []
                return [str(item) for item in parsed if item and str(item).strip()]
            except json.JSONDecodeError as e:
                logging.warning(f"Erro ao desserializar {field_name}: {str(e)} - Valor bruto: {field_value}")
                return []

        # Parsear campos JSON
        caracteristicas = parse_json_field('caracteristicas')
        avaliacao_nutricional = parse_json_field('avaliacao_nutricional')
        comorbidades = parse_json_field('comorbidades')
        historia_obstetrica = parse_json_field('historia_obstetrica')
        condicoes_gestacionais = parse_json_field('condicoes_gestacionais')

        logging.debug(f"Características Individuais: {caracteristicas}")
        logging.debug(f"Avaliação Nutricional: {avaliacao_nutricional}")
        logging.debug(f"Comorbidades: {comorbidades}")
        logging.debug(f"História Obstétrica: {historia_obstetrica}")
        logging.debug(f"Condições Gestacionais: {condicoes_gestacionais}")
        logging.debug(f"Gênero: {genero}")
        logging.debug(f"Sexualidade: {sexualidade}")
        logging.debug(f"Raça/Cor/Etnia: {raca_cor_etnia}")
        logging.debug(f"Etnia Indígena: {etnia_indigena}")  # ✅ NOVO DEBUG!

        # Conectar ao banco
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT nome FROM usuarios WHERE id = ?', (session['user_id'],))
        usuario = cursor.fetchone()
        if not usuario:
            conn.close()
            return jsonify({'success': False, 'message': 'Usuário não encontrado.'}), 400
        profissional = usuario['nome']

        # Validação dos campos obrigatórios
        required_fields = {
            'Nome da Gestante': nome_gestante,
            'Data de Nascimento': data_nasc,
            'Telefone': telefone,
            'Município': municipio,
            'UBS': ubs,
            'ACS': acs,
            'Período Gestacional': periodo_gestacional,
            'Classificação de Risco': classificacao_risco,
            'Gênero': genero,
            'Raça/Cor/Etnia': raca_cor_etnia
            # ✅ etnia_indigena NÃO é obrigatório (só aparece se indígena)
        }
        for field_name, field_value in required_fields.items():
            if not field_value or field_value.strip() == '':
                conn.close()
                return jsonify({
                    'success': False,
                    'message': f'O campo "{field_name}" é obrigatório.'
                }), 400

        # Validação do CPF
        if cpf and cpf != '000.000.000-00':
            cpf = re.sub(r'[^\d]', '', cpf)
            if not re.match(r'^\d{11}$', cpf):
                conn.close()
                return jsonify({
                    'success': False,
                    'message': 'CPF inválido. Deve conter exatamente 11 dígitos.'
                }), 400
        else:
            cpf = '000.000.000-00'

        # Validação da pontuação total
        try:
            pontuacao_total = int(pontuacao_total) if pontuacao_total and pontuacao_total.strip() else 0
        except (ValueError, TypeError):
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Pontuação total inválida.'
            }), 400

        # Validação das datas
        if not re.match(r'^\d{2}/\d{2}/\d{4}$', data_nasc):
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Data de nascimento inválida. Use o formato DD/MM/YYYY.'
            }), 400

        if not re.match(r'^\d{2}/\d{2}/\d{4}$', data_envio):
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Data de envio inválida. Use o formato DD/MM/YYYY.'
            }), 400

        # Preparar dados JSON
        caracteristicas_json = json.dumps(caracteristicas)
        avaliacao_nutricional_json = json.dumps(avaliacao_nutricional)
        comorbidades_json = json.dumps(comorbidades)
        historia_obstetrica_json = json.dumps(historia_obstetrica)
        condicoes_gestacionais_json = json.dumps(condicoes_gestacionais)

        # Gerar código da ficha
        codigo_ficha = str(uuid.uuid4())[:8].upper()

        # ✅ INSERT COM ETNIA_INDIGENA
        cursor.execute('''
            INSERT INTO calculos (
                user_id, codigo_ficha, nome_gestante, data_nasc, cpf, telefone, municipio, ubs, acs,
                periodo_gestacional, data_envio, pontuacao_total, classificacao_risco, imc,
                caracteristicas, avaliacao_nutricional, comorbidades, historia_obstetrica,
                condicoes_gestacionais, profissional, genero, sexualidade, raca_cor_etnia, etnia_indigena
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session['user_id'], codigo_ficha, nome_gestante, data_nasc, cpf, telefone, municipio, ubs, acs,
            periodo_gestacional, data_envio, pontuacao_total, classificacao_risco,
            float(imc) if imc and imc.strip() else None,
            caracteristicas_json, avaliacao_nutricional_json, comorbidades_json,
            historia_obstetrica_json, condicoes_gestacionais_json, profissional,
            genero, sexualidade, raca_cor_etnia, etnia_indigena  # ✅ NOVO!
        ))

        conn.commit()
        cursor.execute('SELECT * FROM calculos WHERE codigo_ficha = ?', (codigo_ficha,))
        ficha_salva = cursor.fetchone()
        conn.close()

        if not ficha_salva:
            return jsonify({
                'success': False,
                'message': 'Erro ao salvar a ficha no banco de dados.'
            }), 500

        logging.debug(f"Ficha salva com sucesso! Código: {codigo_ficha}, Etnia: {etnia_indigena}")

        return jsonify({
            'success': True,
            'codigo_ficha': codigo_ficha,
            'message': f'Ficha salva com sucesso! Código: {codigo_ficha}',
            'dados': {
                'nome_gestante': nome_gestante,
                'deficiencia': deficiencia,
                'data_nasc': data_nasc,
                'cpf': cpf,
                'telefone': telefone,
                'municipio': municipio,
                'ubs': ubs,
                'acs': acs,
                'periodo_gestacional': periodo_gestacional,
                'data_envio': data_envio,
                'pontuacao_total': pontuacao_total,
                'classificacao_risco': classificacao_risco,
                'imc': imc,
                'caracteristicas': caracteristicas,
                'avaliacao_nutricional': avaliacao_nutricional,
                'comorbidades': comorbidades,
                'historia_obstetrica': historia_obstetrica,
                'condicoes_gestacionais': condicoes_gestacionais,
                'profissional': profissional,
                'genero': genero,
                'sexualidade': sexualidade,
                'raca_cor_etnia': raca_cor_etnia,
                'etnia_indigena': etnia_indigena  # ✅ NOVO!
            }
        })

    except sqlite3.IntegrityError as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        logging.error(f"Erro de integridade: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro de integridade no banco de dados: {str(e)}'
        }), 500
    except sqlite3.OperationalError as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        logging.error(f"Erro operacional no banco: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro no banco de dados: {str(e)}'
        }), 500
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        logging.error(f"Erro geral ao salvar: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao salvar os dados: {str(e)}'
        }), 500

@app.route('/buscar_por_cpf', methods=['POST'])
def buscar_por_cpf():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado.'}), 401

    data = request.get_json()
    cpf = data.get('cpf', '').strip()

    if not cpf or len(cpf.replace('.', '').replace('-', '')) != 11:
        return jsonify({'success': False, 'message': 'CPF inválido.'}), 400

    cpf_limpo = re.sub(r'\D', '', cpf)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM calculos 
            WHERE cpf = ?
            ORDER BY data_envio DESC, id DESC
            LIMIT 1
        ''', (cpf_limpo,))
        ficha = cursor.fetchone()

        if not ficha:
            return jsonify({'success': True, 'found': False, 'message': 'Nenhum registro encontrado.'})

        colunas = [desc[0] for desc in cursor.description]
        ficha_dict = dict(zip(colunas, ficha))

        campos_json = ['caracteristicas', 'avaliacao_nutricional', 'comorbidades', 
                       'historia_obstetrica', 'condicoes_gestacionais']
        for campo in campos_json:
            if ficha_dict[campo]:
                try:
                    ficha_dict[campo] = json.loads(ficha_dict[campo])
                except:
                    ficha_dict[campo] = []
            else:
                ficha_dict[campo] = []

        return jsonify({
            'success': True,
            'found': True,
            'ficha': ficha_dict
        })

    except Exception as e:
        logging.error(f"Erro ao buscar por CPF {cpf_limpo}: {str(e)}")
        if conn:
            try:
                conn.close()
            except:
                pass
        return jsonify({'success': False, 'message': 'Erro interno do servidor.'}), 500

@app.route('/historico', methods=['GET'])
def historico():
    if 'user_id' not in session:
        flash('Por favor, faça login para acessar o histórico.', 'error')
        return redirect(url_for('login'))

    return render_template('historico.html')

@app.route('/buscar_historico', methods=['POST'])
def buscar_historico():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Usuário não autenticado.'}), 401

    try:
        data = request.get_json()
        page = data.get('page', 1)
        per_page = data.get('per_page', 100)
        sort_column = data.get('sort_column', 'id')
        sort_direction = data.get('sort_direction', 'DESC')
        nome_gestante = data.get('nome_gestante', '').strip()
        data_nasc = data.get('data_nasc', '').strip()

        valid_columns = [
            'id', 'codigo_ficha', 'nome_gestante', 'data_nasc', 'data_envio', 'periodo_gestacional',
            'pontuacao_total', 'classificacao_risco', 'municipio', 'ubs', 'acs', 'profissional'
        ]
        if sort_column not in valid_columns:
            logging.warning(f"Coluna de ordenação inválida: {sort_column}. Usando 'id'.")
            sort_column = 'id'

        sort_direction = sort_direction.upper()
        if sort_direction not in ['ASC', 'DESC']:
            logging.warning(f"Direção de ordenação inválida: {sort_direction}. Usando 'DESC'.")
            sort_direction = 'DESC'

        offset = (page - 1) * per_page

        conn = get_db_connection()
        cursor = conn.cursor()

        # Montar a query com filtros, incluindo fa = 0
        query = '''
            SELECT id, codigo_ficha, nome_gestante, data_nasc, data_envio, periodo_gestacional, 
                   pontuacao_total, classificacao_risco, municipio, ubs, acs, profissional, pdf_compartilhado_municipal, pnar_ambulatorio
            FROM calculos 
            WHERE user_id = ? AND (desfecho IS NULL OR desfecho = '') AND fa = 0
        '''
        params = [session['user_id']]

        if nome_gestante:
            query += ' AND nome_gestante LIKE ?'
            params.append(f'%{nome_gestante}%')
        if data_nasc:
            query += ' AND data_nasc = ?'
            params.append(data_nasc)

        # Contar registros totais
        count_query = "SELECT COUNT(*) FROM calculos WHERE user_id = ? AND (desfecho IS NULL OR desfecho = '') AND fa = 0"
        count_params = [session['user_id']]
        if nome_gestante:
            count_query += ' AND nome_gestante LIKE ?'
            count_params.append(f'%{nome_gestante}%')
        if data_nasc:
            count_query += ' AND data_nasc = ?'
            count_params.append(data_nasc)

        cursor.execute(count_query, count_params)
        total_records = cursor.fetchone()[0]

        query += f' ORDER BY {sort_column} {sort_direction} LIMIT ? OFFSET ?'
        params.extend([per_page, offset])
        logging.debug(f"Executando query: {query} com params={params}")
        cursor.execute(query, params)
        fichas = cursor.fetchall()
        fichas_dict = [dict(ficha) for ficha in fichas]
        conn.close()

        return jsonify({
            'success': True,
            'fichas': fichas_dict,
            'total_records': total_records
        })

    except sqlite3.Error as e:
        logging.error(f"Erro no banco de dados: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro no banco de dados: {str(e)}'
        }), 500
    except Exception as e:
        logging.error(f"Erro ao buscar histórico: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao buscar histórico: {str(e)}'
        }), 500

@app.route('/marcar_fora_area', methods=['POST'])
def marcar_fora_area():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Usuário não autenticado.'}), 401

    try:
        data = request.get_json()
        codigo_ficha = data.get('codigo_ficha')
        nome_gestante = data.get('nome_gestante')
        data_nasc = data.get('data_nasc')

        if not codigo_ficha or not nome_gestante or not data_nasc:
            return jsonify({'success': False, 'message': 'Dados incompletos.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar se o registro existe para o usuário logado
        cursor.execute('''
            SELECT id, cpf, municipio FROM calculos 
            WHERE user_id = ? AND codigo_ficha = ? AND nome_gestante = ? AND data_nasc = ? AND fa = 0
        ''', (session['user_id'], codigo_ficha, nome_gestante, data_nasc))
        registro = cursor.fetchone()

        if not registro:
            conn.close()
            return jsonify({'success': False, 'message': 'Registro não encontrado ou já marcado como fora de área.'}), 404

        # Identificar todas as fichas da mesma gestante
        cpf = registro['cpf']
        municipio = registro['municipio']
        if cpf and cpf != '000.000.000-00':
            # Buscar fichas pelo CPF e município
            cursor.execute('''
                SELECT id, codigo_ficha FROM calculos 
                WHERE cpf = ? AND municipio = ? AND fa = 0
            ''', (cpf, municipio))
        else:
            # Buscar fichas por nome_gestante, data_nasc e município
            cursor.execute('''
                SELECT id, codigo_ficha FROM calculos 
                WHERE nome_gestante = ? AND data_nasc = ? AND municipio = ? AND fa = 0
            ''', (nome_gestante, data_nasc, municipio))
        
        fichas_relacionadas = cursor.fetchall()
        if not fichas_relacionadas:
            conn.close()
            return jsonify({'success': False, 'message': 'Nenhuma ficha relacionada encontrada.'}), 404

        # Marcar todas as fichas relacionadas como fora de área
        updated_fichas = []
        for ficha in fichas_relacionadas:
            cursor.execute('''
                UPDATE calculos 
                SET fa = 1 
                WHERE id = ?
            ''', (ficha['id'],))
            updated_fichas.append(ficha['codigo_ficha'])

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'{len(updated_fichas)} ficha(s) marcada(s) como fora de área com sucesso.',
            'fichas_atualizadas': updated_fichas
        })

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
            conn.close()
        logging.error(f"Erro no banco de dados: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro no banco de dados: {str(e)}'
        }), 500
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        logging.error(f"Erro ao marcar como fora de área: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao marcar como fora de área: {str(e)}'
        }), 500

@app.route('/registrar_desfecho_lote', methods=['POST'])
def registrar_desfecho_lote():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Por favor, faça login para registrar o desfecho.'}), 401

    try:
        # Forçar parse do JSON para capturar erros
        data = request.get_json(force=True)
        logging.debug(f"Corpo da requisição: {data}")
        nome_gestante = data.get('nome_gestante', '').strip()
        data_nasc = data.get('data_nasc', '').strip()
        desfecho = data.get('desfecho', '').strip()

        # Validar campos obrigatórios
        if not nome_gestante or not data_nasc or not desfecho:
            logging.error(f"Campos obrigatórios ausentes: nome_gestante={nome_gestante}, data_nasc={data_nasc}, desfecho={desfecho}")
            return jsonify({
                'success': False,
                'message': 'Nome da gestante, data de nascimento e desfecho são obrigatórios.'
            }), 400

        # Validar desfecho
        if desfecho not in DESFECHO_MAP:
            logging.error(f"Desfecho inválido: {desfecho}. Valores esperados: {list(DESFECHO_MAP.keys())}")
            return jsonify({
                'success': False,
                'message': f'Desfecho inválido: {desfecho}. Use um valor válido do DESFECHO_MAP.'
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        # Buscar fichas com desfecho NULL
        cursor.execute('''
            SELECT codigo_ficha, nome_gestante, data_nasc, municipio
            FROM calculos 
            WHERE nome_gestante = ? AND data_nasc = ? AND desfecho IS NULL
        ''', (nome_gestante, data_nasc))
        fichas = cursor.fetchall()
        logging.debug(f"Fichas encontradas: {len(fichas)} para nome={nome_gestante}, data_nasc={data_nasc}")
        for ficha in fichas:
            logging.debug(f"Ficha: codigo_ficha={ficha['codigo_ficha']}, municipio={ficha['municipio']}")

        if not fichas:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Nenhuma ficha encontrada para o nome e data de nascimento fornecidos.'
            }), 404

        data_desfecho = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        for ficha in fichas:
            cursor.execute('''
                UPDATE calculos 
                SET desfecho = ?, data_desfecho = ? 
                WHERE codigo_ficha = ?
            ''', (desfecho, data_desfecho, ficha['codigo_ficha']))
            logging.debug(f"Atualizado desfecho para ficha {ficha['codigo_ficha']}: desfecho={desfecho}, data_desfecho={data_desfecho}")

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Desfecho {DESFECHO_MAP.get(desfecho, desfecho)} registrado com sucesso para {len(fichas)} ficha(s)!'
        })

    except ValueError as e:
        logging.error(f"Erro ao processar JSON: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Corpo da requisição inválido. Envie um JSON válido.'
        }), 400
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
            conn.close()
        logging.error(f"Erro no banco de dados: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro no banco de dados: {str(e)}'
        }), 500
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        logging.error(f"Erro ao registrar desfecho em lote: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao registrar desfecho: {str(e)}'
        }), 500

@app.route('/obter_ficha_completa', methods=['POST'])
def obter_ficha_completa():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Por favor, faça login para acessar a ficha.'}), 401

    try:
        data = request.get_json()
        codigo_ficha = data.get('code')

        if not codigo_ficha:
            return jsonify({'error': 'Código da ficha não fornecido.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM calculos 
            WHERE codigo_ficha = ? AND user_id = ?
        ''', (codigo_ficha, session['user_id']))
        ficha = cursor.fetchone()
        conn.close()

        if not ficha:
            return jsonify({'error': 'Ficha não encontrada ou você não tem acesso a ela.'}), 404

        ficha_dict = dict(ficha)

        logging.debug(f"Valores brutos para ficha {codigo_ficha}:")
        for field in ['caracteristicas', 'avaliacao_nutricional', 'comorbidades', 'historia_obstetrica', 'condicoes_gestacionais']:
            logging.debug(f"{field} (raw): {ficha_dict[field]}")

        try:
            for field in ['caracteristicas', 'avaliacao_nutricional', 'comorbidades', 'historia_obstetrica', 'condicoes_gestacionais']:
                raw_value = ficha_dict[field]
                if raw_value is None or raw_value == '':
                    ficha_dict[field] = []
                else:
                    try:
                        parsed_value = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
                        if not isinstance(parsed_value, list):
                            parsed_value = [parsed_value] if parsed_value else []
                        if parsed_value and isinstance(parsed_value, list) and len(parsed_value) == 1:
                            try:
                                nested_items = json.loads(parsed_value[0]) if isinstance(parsed_value[0], str) else parsed_value[0]
                                if isinstance(nested_items, list):
                                    parsed_value = nested_items
                                elif nested_items:
                                    parsed_value = [nested_items]
                            except json.JSONDecodeError:
                                pass
                        ficha_dict[field] = parsed_value
                    except json.JSONDecodeError as e:
                        logging.warning(f"Erro ao desserializar {field}: {str(e)} - Valor bruto: {raw_value}")
                        ficha_dict[field] = [raw_value] if raw_value else []
            # Mapear os novos campos
            ficha_dict['genero'] = [ficha_dict.get('genero', 'nao_informado')]
            ficha_dict['sexualidade'] = [ficha_dict.get('sexualidade', 'nao_informado')]
            ficha_dict['raca_cor_etnia'] = [ficha_dict.get('raca_cor_etnia', 'nao_informado')]
        except Exception as e:
            logging.error(f"Erro geral ao desserializar JSON: {str(e)}")
            return jsonify({'error': 'Erro ao processar dados da ficha.'}), 500

        logging.debug(f"Valores após desserialização para ficha {codigo_ficha}:")
        for field in ['caracteristicas', 'avaliacao_nutricional', 'comorbidades', 'historia_obstetrica', 'condicoes_gestacionais', 'genero', 'sexualidade', 'raca_cor_etnia']:
            logging.debug(f"{field} (parsed): {ficha_dict[field]}")

        # Mapear os itens para exibição
        mapped_data = {}
        for field in ['caracteristicas', 'avaliacao_nutricional', 'comorbidades', 'historia_obstetrica', 'condicoes_gestacionais', 'genero', 'sexualidade', 'raca_cor_etnia']:
            mapped_data[field] = [map_item(field, item) for item in ficha_dict[field] if item]

        logging.debug(f"Valores após mapeamento para ficha {codigo_ficha}:")
        for field in ['caracteristicas', 'avaliacao_nutricional', 'comorbidades', 'historia_obstetrica', 'condicoes_gestacionais', 'genero', 'sexualidade', 'raca_cor_etnia']:
            logging.debug(f"{field} (mapped): {mapped_data[field]}")

        return jsonify({'ficha': ficha_dict, 'mapped_data': mapped_data}), 200

    except sqlite3.Error as e:
        logging.error(f"Erro no banco de dados: {str(e)}")
        return jsonify({'error': f'Erro no banco de dados: {str(e)}'}), 500
    except Exception as e:
        logging.error(f"Erro ao buscar ficha: {str(e)}")
        return jsonify({'error': f'Erro ao buscar ficha: {str(e)}'}), 500

@app.route('/compartilhar_tudo_preview', methods=['POST'])
def compartilhar_tudo_preview():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Usuário não autenticado.'}), 401

    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1️⃣ Buscar TODOS municípios das fichas ATIVAS do usuário
        cursor.execute('''
            SELECT DISTINCT municipio FROM calculos 
            WHERE user_id = ? AND desfecho IS NULL AND fora_area = 0
        ''', (session['user_id'],))
        municipios_fichas = [row['municipio'] for row in cursor.fetchall()]
        
        if not municipios_fichas:
            conn.close()
            return jsonify({
                'success': False, 
                'message': 'Nenhuma ficha ativa disponível para compartilhar.'
            }), 400

        # 2️⃣ Buscar ADMIN MUNICIPAL para CADA município
        placeholders = ','.join('?' * len(municipios_fichas))
        cursor.execute(f'''
            SELECT u.nome, um.municipio 
            FROM usuarios u 
            JOIN usuario_municipios um ON u.id = um.usuario_id 
            WHERE u.role = 'municipal' AND u.ativo = 1 
            AND um.municipio IN ({placeholders})
        ''', municipios_fichas)
        
        admins = []
        for row in cursor.fetchall():
            admins.append({
                'nome': row['nome'], 
                'municipio': row['municipio']
            })
        
        conn.close()

        if not admins:
            return jsonify({
                'success': False, 
                'message': f'❌ Nenhum administrador municipal encontrado para: {", ".join(municipios_fichas)}'
            }), 404

        return jsonify({
            'success': True,
            'admins': admins,
            'total_fichas': len(municipios_fichas)
        })

    except sqlite3.Error as e:
        if conn:
            conn.close()
        logging.error(f"Erro no banco ao buscar admins: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro no banco: {str(e)}'}), 500
    except Exception as e:
        if conn:
            conn.close()
        logging.error(f"Erro ao buscar admins: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro inesperado: {str(e)}'}), 500

# ✅ NOVA: Compartilhar TUDO para 1 admin específico
@app.route('/compartilhar_tudo', methods=['POST'])
def compartilhar_tudo():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Usuário não autenticado.'}), 401

    try:
        data = request.get_json()
        municipio_selecionado = data.get('municipio')

        if not municipio_selecionado:
            return jsonify({'success': False, 'message': 'Município não selecionado.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 1️⃣ Buscar ADMIN do município selecionado
        cursor.execute('''
            SELECT nome FROM usuarios u
            JOIN usuario_municipios um ON u.id = um.usuario_id 
            WHERE u.role = 'municipal' AND um.municipio = ? AND u.ativo = 1
            LIMIT 1
        ''', (municipio_selecionado,))
        admin = cursor.fetchone()
        
        if not admin:
            conn.close()
            return jsonify({
                'success': False, 
                'message': f'❌ Não há administrador municipal ativo para {municipio_selecionado}.'
            }), 404

        nome_admin = admin['nome']

        # 2️⃣ Marcar TODAS fichas ATIVAS deste município como COMPARTILHADAS
        cursor.execute('''
            UPDATE calculos 
            SET pdf_compartilhado_municipal = 1 
            WHERE user_id = ? AND municipio = ? 
            AND desfecho IS NULL AND fora_area = 0
        ''', (session['user_id'], municipio_selecionado))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()

        if rows_affected == 0:
            return jsonify({
                'success': False, 
                'message': f'❌ Nenhuma ficha ativa encontrada para {municipio_selecionado}.'
            }), 400

        return jsonify({
            'success': True,
            'message': f'✅ {rows_affected} ficha(s) compartilhada(s) com sucesso para <strong>{nome_admin}</strong> ({municipio_selecionado})!',
            'admin_nome': nome_admin,
            'municipio': municipio_selecionado,
            'quantidade': rows_affected
        })

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
            conn.close()
        logging.error(f"Erro no banco ao compartilhar tudo: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro no banco: {str(e)}'}), 500
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        logging.error(f"Erro ao compartilhar tudo: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro inesperado: {str(e)}'}), 500

# ✅ ATUALIZADO: Manter sua função original (para compatibilidade)
def compartilhar_pdf():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Usuário não autenticado.'}), 401

    try:
        data = request.get_json()
        codigo_ficha = data.get('codigo_ficha')

        if not codigo_ficha:
            return jsonify({'success': False, 'message': 'Código da ficha não fornecido.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 1️⃣ Buscar município da ficha
        cursor.execute('''
            SELECT municipio FROM calculos 
            WHERE codigo_ficha = ? AND user_id = ?
        ''', (codigo_ficha, session['user_id']))
        ficha = cursor.fetchone()
        
        if not ficha:
            conn.close()
            return jsonify({'success': False, 'message': 'Ficha não encontrada.'}), 404

        municipio_ficha = ficha['municipio']

        # 2️⃣ Buscar ADMIN MUNICIPAL deste município
        cursor.execute('''
            SELECT nome FROM usuarios u
            JOIN usuario_municipios um ON u.id = um.usuario_id 
            WHERE u.role = 'municipal' AND um.municipio = ? AND u.ativo = 1
            LIMIT 1
        ''', (municipio_ficha,))
        admin_municipal = cursor.fetchone()
        
        if not admin_municipal:
            conn.close()
            return jsonify({
                'success': False, 
                'message': f'Não há administrador municipal cadastrado para {municipio_ficha}.'
            }), 404

        nome_admin = admin_municipal['nome']

        # 3️⃣ Marcar como COMPARTILHADO (se ainda não estiver)
        cursor.execute('''
            UPDATE calculos 
            SET pdf_compartilhado_municipal = 1 
            WHERE codigo_ficha = ? AND user_id = ?
        ''', (codigo_ficha, session['user_id']))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()

        if rows_affected == 0:
            return jsonify({
                'success': False, 
                'message': 'Ficha já estava compartilhada.'
            }), 400

        return jsonify({
            'success': True,
            'message': f'PDF compartilhado com sucesso para o administrador municipal!',
            'admin_nome': nome_admin,
            'municipio': municipio_ficha
        })

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
            conn.close()
        logging.error(f"Erro no banco ao compartilhar PDF: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro no banco: {str(e)}'}), 500
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        logging.error(f"Erro ao compartilhar PDF: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro inesperado: {str(e)}'}), 500

@app.route('/verificar_compartilhamento/<codigo_ficha>', methods=['GET'])
def verificar_compartilhamento(codigo_ficha):
    """Para o histórico saber se já está compartilhado"""
    if 'user_id' not in session:
        return jsonify({'compartilhado': False}), 401

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT pdf_compartilhado_municipal FROM calculos 
        WHERE codigo_ficha = ? AND user_id = ?
    ''', (codigo_ficha, session['user_id']))
    resultado = cursor.fetchone()
    conn.close()

    return jsonify({'compartilhado': resultado['pdf_compartilhado_municipal'] == 1 if resultado else False})

@app.route('/pnar')
@pnar_access_required
def pnar():
    conn = get_db_connection()
    c = conn.cursor()
    user_id = session.get('user_id')
    user_role = session.get('role')

    # === PERSONALIZAÇÃO DO TÍTULO ===
    titulo_usuario = "Usuário PNAR"  # fallback

    if user_role == 'estadual':
        c.execute("SELECT is_super_admin, nome FROM usuarios WHERE id = ?", (user_id,))
        user = c.fetchone()
        if user and user[0] == 1:  # is_super_admin
            titulo_usuario = user[1]  # nome do estadual
        else:
            conn.close()
            flash('Você não tem permissão para acessar o PNAR.', 'danger')
            return redirect(url_for('admin_painel'))
    elif user_role == 'apoio':
        c.execute("SELECT pnar, servico FROM usuarios_apoio WHERE user_id = ?", (user_id,))
        apoio = c.fetchone()
        if apoio and apoio[0] == 1:  # pnar = 1
            titulo_usuario = apoio[1] or "Serviço de Apoio"  # nome do serviço
        else:
            conn.close()
            flash('Você não tem permissão para acessar o PNAR.', 'danger')
            return redirect(url_for('admin_painel'))
    else:
        conn.close()
        flash('Você não tem permissão para acessar o PNAR.', 'danger')
        return redirect(url_for('admin_painel'))

    conn.close()
    return render_template('pnar.html', titulo_usuario=titulo_usuario)

@app.route('/registrar_pnar', methods=['POST'])
def registrar_pnar():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Faça login novamente.'}), 401

    try:
        data = request.get_json(force=True)
        logging.debug(f"PNAR recebido: {data}")

        codigo_ficha = data.get('codigo_ficha', '').strip()
        nome_gestante = data.get('nome_gestante', '').strip()
        data_nasc = data.get('data_nasc', '').strip()
        servico = data.get('pnar_servico', '').strip()

        if not all([codigo_ficha, nome_gestante, data_nasc, servico]):
            return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verifica se a ficha existe e pertence ao usuário
        cursor.execute('''
            SELECT 1 FROM calculos
            WHERE codigo_ficha = ? AND nome_gestante = ? AND data_nasc = ? AND user_id = ?
        ''', (codigo_ficha, nome_gestante, data_nasc, session['user_id']))

        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Ficha não encontrada ou não pertence a você.'}), 404

        # Atualiza
        cursor.execute('''
            UPDATE calculos
            SET pnar_sinalizado = 1,
                pnar_ambulatorio = ?,
                pnar_data_registro = datetime('now','localtime')
            WHERE codigo_ficha = ?
        ''', (servico, codigo_ficha))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'PNAR sinalizado para {servico}'
        })

    except Exception as e:
        logging.error(f"Erro PNAR: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Erro interno.'}), 500

@app.route('/buscar_pnar', methods=['POST'])
def buscar_pnar():
    # Verifica login
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Faça login."}), 401

    try:
        data = request.get_json() or {}
        page = max(1, int(data.get('page', 1)))
        per_page = min(100, int(data.get('per_page', 100)))
        sort_column = data.get('sort_column', 'nome_gestante')
        sort_direction = data.get('sort_direction', 'ASC').upper()

        # Validação básica
        valid_columns = ['nome_gestante', 'periodo_gestacional', 'municipio']
        if sort_column not in valid_columns:
            sort_column = 'nome_gestante'
        if sort_direction not in ['ASC', 'DESC']:
            sort_direction = 'ASC'

        user_id = session['user_id']
        user_role = session.get('role')

        conn = get_db_connection()
        c = conn.cursor()

        # Query base
        query = """
            SELECT codigo_ficha, nome_gestante, periodo_gestacional, municipio
            FROM calculos
            WHERE classificacao_risco = 'Alto Risco'
              AND desfecho IS NULL
              AND pnar_sinalizado = 1
        """
        params = []
        count_params = []

        # Filtro para usuário de apoio
        if user_role == 'apoio':
            c.execute("SELECT servico FROM usuarios_apoio WHERE user_id = ?", (user_id,))
            apoio = c.fetchone()
            if not apoio or not apoio[0]:
                conn.close()
                return jsonify({"success": False, "message": "Acesso negado."}), 403
            servico = apoio[0]
            query += " AND pnar_ambulatorio = ?"
            params.append(servico)
            count_params.append(servico)

        # Contar total
        c.execute(f"SELECT COUNT(*) FROM ({query})", count_params)
        total_records = c.fetchone()[0]

        # Paginação
        offset = (page - 1) * per_page
        c.execute(f"""
            {query}
            ORDER BY {sort_column} {sort_direction}
            LIMIT ? OFFSET ?
        """, params + [per_page, offset])

        fichas = [
            {
                'codigo_ficha': row[0],
                'nome_gestante': row[1],
                'periodo_gestacional': row[2],
                'municipio': row[3]
            }
            for row in c.fetchall()
        ]

        conn.close()

        return jsonify({
            "success": True,
            "fichas": fichas,
            "total_records": total_records
        })

    except Exception as e:
        logging.error(f"Erro em /buscar_pnar: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Erro no servidor."}), 500

@app.route('/logout', methods=['POST'])
def logout():
    if 'user_id' in session:
        session.pop('user_id', None)
        session.pop('is_admin', None)
        session.pop('role', None)
        return jsonify({'success': True, 'message': 'Logout realizado com sucesso.'})
    return jsonify({'success': False, 'message': 'Nenhuma sessão ativa.'}), 401

def restrict_to_municipio(cursor, usuario_id, admin_id):
    cursor.execute('SELECT municipio, role, is_super_admin FROM usuarios WHERE id = ?', (admin_id,))
    admin_user = cursor.fetchone()
    if not admin_user:
        return False, 'Administrador não encontrado.'
    
    admin_municipio = admin_user['municipio']
    admin_role = admin_user['role']
    is_super_admin = admin_user['is_super_admin']

    cursor.execute('SELECT municipio FROM usuarios WHERE id = ?', (usuario_id,))
    target_user = cursor.fetchone()
    if not target_user:
        return False, 'Usuário não encontrado.'
    
    if admin_role == 'municipal' and not is_super_admin and target_user['municipio'] != admin_municipio:
        return False, 'Acesso negado: você só pode gerenciar usuários do seu município.'
    
    return True, None

@app.route('/admin/painel', methods=['GET'])
@admin_required
def admin_painel():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obter informações do usuário logado
        cursor.execute('SELECT municipio, role, is_super_admin FROM usuarios WHERE id = ?', (session['user_id'],))
        user = cursor.fetchone()
        if not user:
            conn.close()
            flash('Usuário não encontrado.', 'error')
            return redirect(url_for('calculadora'))

        user_municipio = user['municipio']
        user_role = user['role']
        is_super_admin = user['is_super_admin']

        # Definir query para usuários pendentes
        if user_role == 'municipal' and not is_super_admin:
            cursor.execute('SELECT id, nome, email, municipio, profissao, cnes FROM usuarios WHERE approved = ? AND municipio = ?', (0, user_municipio))
        else:
            cursor.execute('SELECT id, nome, email, municipio, profissao, cnes FROM usuarios WHERE approved = ?', (0,))
        usuarios_pendentes = [dict(user) for user in cursor.fetchall()]

        # Definir query para usuários cadastrados
        if user_role == 'municipal' and not is_super_admin:
            cursor.execute('SELECT id, nome, email, municipio, profissao, cnes, ativo FROM usuarios WHERE approved = ? AND municipio = ?', (1, user_municipio))
        else:
            cursor.execute('SELECT id, nome, email, municipio, profissao, cnes, ativo FROM usuarios WHERE approved = ?', (1,))
        usuarios_cadastrados = [dict(user) for user in cursor.fetchall()]

        # Histórico de ações administrativas (limitado a 100 registros, sem paginação)
        if user_role == 'municipal' and not is_super_admin:
            cursor.execute('''
                SELECT a.data_acao, u1.nome AS admin_nome, u2.nome AS usuario_nome, a.acao, a.detalhes
                FROM acoes_administrativas a
                LEFT JOIN usuarios u1 ON a.admin_id = u1.id
                LEFT JOIN usuarios u2 ON a.usuario_id = u2.id
                WHERE u2.municipio = ?
                ORDER BY a.data_acao DESC
                LIMIT 100
            ''', (user_municipio,))
        else:
            cursor.execute('''
                SELECT a.data_acao, u1.nome AS admin_nome, u2.nome AS usuario_nome, a.acao, a.detalhes
                FROM acoes_administrativas a
                LEFT JOIN usuarios u1 ON a.admin_id = u1.id
                LEFT JOIN usuarios u2 ON a.usuario_id = u2.id
                ORDER BY a.data_acao DESC
                LIMIT 100
            ''')
        historico_acoes = [dict(acao) for acao in cursor.fetchall()]

        # Adicionar logs para debugging
        logging.info(f"Administrador ID {session['user_id']}: role={user_role}, municipio={user_municipio}, is_super_admin={is_super_admin}")
        logging.info(f"Usuários pendentes encontrados: {len(usuarios_pendentes)}")
        logging.info(f"Usuários cadastrados encontrados: {len(usuarios_cadastrados)}")
        logging.info(f"Ações administrativas encontradas: {len(historico_acoes)}")

        conn.close()
        return render_template('admin_painel.html',
                             usuarios_pendentes=usuarios_pendentes,
                             usuarios_cadastrados=usuarios_cadastrados,
                             historico_acoes=historico_acoes,  # Passar lista direta, não objeto paginado
                             is_super_admin=is_super_admin,
                             role=user_role)
    except sqlite3.OperationalError as e:
        if conn:
            conn.close()
        flash(f'Erro no banco de dados: {str(e)}. Contate o administrador.', 'danger')
        return redirect(url_for('calculadora'))
    except Exception as e:
        if conn:
            conn.close()
        flash(f'Erro ao carregar painel administrativo: {str(e)}.', 'danger')
        return redirect(url_for('calculadora'))

@app.route('/admin/aprovar_usuario', methods=['POST'])
@admin_required
def admin_aprovar_usuario():
    usuario_id = request.form.get('usuario_id')
    if not usuario_id:
        flash('ID do usuário inválido.', 'danger')
        return redirect(url_for('admin_painel'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar restrição de município
        allowed, error_message = restrict_to_municipio(cursor, usuario_id, session['user_id'])
        if not allowed:
            conn.close()
            flash(error_message, 'danger')
            return redirect(url_for('admin_painel'))

        # Prosseguir com a aprovação
        cursor.execute('UPDATE usuarios SET approved = ?, ativo = ? WHERE id = ?', (1, 1, usuario_id))
        if cursor.rowcount == 0:
            flash('Usuário não encontrado.', 'danger')
        else:
            cursor.execute('''
                INSERT INTO acoes_administrativas (admin_id, usuario_id, acao, data_acao, detalhes)
                VALUES (?, ?, ?, ?, ?)
            ''', (session['user_id'], usuario_id, 'Aprovação', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                  f'Usuário ID {usuario_id} aprovado'))
            conn.commit()
            flash('Usuário aprovado com sucesso.', 'success')
        conn.close()
    except sqlite3.OperationalError as e:
        conn.close()
        flash(f'Erro no banco de dados: {str(e)}. Contate o administrador.', 'danger')
    return redirect(url_for('admin_painel'))

@app.route('/admin/rejeitar_usuario', methods=['POST'])
@admin_required
def admin_rejeitar_usuario():
    usuario_id = request.form.get('usuario_id')
    if not usuario_id:
        flash('ID do usuário inválido.', 'danger')
        return redirect(url_for('admin_painel'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar restrição de município
        allowed, error_message = restrict_to_municipio(cursor, usuario_id, session['user_id'])
        if not allowed:
            conn.close()
            flash(error_message, 'danger')
            return redirect(url_for('admin_painel'))

        # Prosseguir com a rejeição
        cursor.execute('DELETE FROM usuarios WHERE id = ?', (usuario_id,))
        if cursor.rowcount == 0:
            flash('Usuário não encontrado.', 'danger')
        else:
            cursor.execute('''
                INSERT INTO acoes_administrativas (admin_id, usuario_id, acao, data_acao, detalhes)
                VALUES (?, ?, ?, ?, ?)
            ''', (session['user_id'], usuario_id, 'Rejeição', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                  f'Usuário ID {usuario_id} rejeitado e removido'))
            conn.commit()
            flash('Usuário rejeitado e removido.', 'success')
        conn.close()
    except sqlite3.OperationalError as e:
        conn.close()
        flash(f'Erro no banco de dados: {str(e)}. Contate o administrador.', 'danger')
    return redirect(url_for('admin_painel'))

@app.route('/admin/ativar_usuario', methods=['POST'])
@admin_required
def admin_ativar_usuario():
    try:
        usuario_id = int(request.form.get('usuario_id'))
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'ID do usuário inválido.'}), 400

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            allowed, error_message = restrict_to_municipio(cursor, usuario_id, session['user_id'])
            if not allowed:
                return jsonify({'success': False, 'message': error_message}), 403

            cursor.execute('SELECT email, nome, municipio, profissao, cnes FROM usuarios WHERE id = ?', (usuario_id,))
            user = cursor.fetchone()
            if not user:
                return jsonify({'success': False, 'message': 'Usuário não encontrado.'}), 404

            cursor.execute('UPDATE usuarios SET ativo = ? WHERE id = ?', (1, usuario_id))
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': 'Usuário não encontrado.'}), 404

            cursor.execute('''
                INSERT INTO acoes_administrativas (admin_id, usuario_id, acao, data_acao, detalhes)
                VALUES (?, ?, ?, ?, ?)
            ''', (session['user_id'], usuario_id, 'Ativação', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                  f'Usuário ID {usuario_id} ({user["email"]}) ativado'))
            conn.commit()

            # Retornar dados do usuário para atualizar o front-end
            return jsonify({
                'success': True,
                'message': 'Usuário ativado com sucesso.',
                'usuario': {
                    'id': usuario_id,
                    'nome': user['nome'],
                    'email': user['email'],
                    'municipio': user['municipio'],
                    'profissao': user['profissao'],
                    'cnes': user['cnes'],
                    'ativo': 1
                }
            })
    except sqlite3.OperationalError as e:
        return jsonify({'success': False, 'message': f'Erro no banco de dados: {str(e)}.'}), 500

@app.route('/admin/desativar_usuario', methods=['POST'])
@admin_required
def admin_desativar_usuario():
    try:
        usuario_id = int(request.form.get('usuario_id'))
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'ID do usuário inválido.'}), 400

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            allowed, error_message = restrict_to_municipio(cursor, usuario_id, session['user_id'])
            if not allowed:
                return jsonify({'success': False, 'message': error_message}), 403

            cursor.execute('SELECT email, nome, municipio, profissao, cnes FROM usuarios WHERE id = ?', (usuario_id,))
            user = cursor.fetchone()
            if not user:
                return jsonify({'success': False, 'message': 'Usuário não encontrado.'}), 404

            cursor.execute('UPDATE usuarios SET ativo = ? WHERE id = ?', (0, usuario_id))
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': 'Usuário não encontrado.'}), 404

            cursor.execute('''
                INSERT INTO acoes_administrativas (admin_id, usuario_id, acao, data_acao, detalhes)
                VALUES (?, ?, ?, ?, ?)
            ''', (session['user_id'], usuario_id, 'Desativação', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                  f'Usuário ID {usuario_id} ({user["email"]}) desativado'))
            conn.commit()

            return jsonify({
                'success': True,
                'message': 'Usuário desativado com sucesso.',
                'usuario': {
                    'id': usuario_id,
                    'nome': user['nome'],
                    'email': user['email'],
                    'municipio': user['municipio'],
                    'profissao': user['profissao'],
                    'cnes': user['cnes'],
                    'ativo': 0
                }
            })
    except sqlite3.OperationalError as e:
        return jsonify({'success': False, 'message': f'Erro no banco de dados: {str(e)}.'}), 500

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'error')
            return redirect(url_for('login'))
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT is_admin, role, is_super_admin FROM usuarios WHERE id = ?', (session['user_id'],))
            user = cursor.fetchone()
            conn.close()
            if not user or user['role'] != 'estadual' or not user['is_super_admin']:
                flash(f'Acesso negado: apenas administradores estaduais podem acessar esta página.', 'error')
                return redirect(url_for('admin_painel'))
            return f(*args, **kwargs)
        except sqlite3.OperationalError as e:
            flash(f'Erro no banco de dados: {str(e)}. Contate o administrador do banco de dados.', 'danger')
            return redirect(url_for('admin_painel'))
    return decorated_function

def apoio_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'error')
            return redirect(url_for('login'))
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            if session.get('tipo_usuario') == 'apoio':
                cursor.execute('SELECT id FROM usuarios_apoio WHERE id = ?', (session['user_id'],))
            else:
                cursor.execute('SELECT role FROM usuarios WHERE id = ?', (session['user_id'],))
            user = cursor.fetchone()
            conn.close()
            if not user or (session.get('tipo_usuario') != 'apoio' and user['role'] != 'estadual'):
                flash('Acesso negado. Apenas usuários de apoio ou administradores estaduais podem acessar esta página.', 'error')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        except sqlite3.OperationalError as e:
            flash(f'Erro no banco de dados: {str(e)}. Contate o administrador do banco de dados.', 'danger')
            return redirect(url_for('login'))
    return decorated_function

# Função auxiliar para obter municípios de um usuário
def get_usuario_municipios(cursor, usuario_id):
    cursor.execute('SELECT municipio FROM usuario_municipios WHERE usuario_id = ?', (usuario_id,))
    return [row['municipio'] for row in cursor.fetchall()]

# Rota para buscar usuários aprovados para autocomplete
@app.route('/admin/buscar_usuarios_aprovados', methods=['GET'])
@super_admin_required
def buscar_usuarios_aprovados():
    try:
        query = request.args.get('query', '').lower()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, nome FROM usuarios 
            WHERE approved = 1 AND ativo = 1 AND lower(nome) LIKE ?
            LIMIT 10
        ''', (f'%{query}%',))
        usuarios = [{'id': row['id'], 'nome': row['nome']} for row in cursor.fetchall()]
        conn.close()
        return jsonify({'success': True, 'usuarios': usuarios})
    except sqlite3.OperationalError as e:
        logging.error(f"Erro no banco de dados: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro no banco de dados: {str(e)}'}), 500

# Rota para obter dados de um usuário para edição
@app.route('/admin/obter_usuario/<int:user_id>')
@super_admin_required
def obter_usuario(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE id = ?', (user_id,))
        usuario = cursor.fetchone()
        if not usuario:
            return jsonify({'success': False, 'message': 'Usuário não encontrado'})
        
        cursor.execute('SELECT municipio FROM usuario_municipios WHERE usuario_id = ?', (user_id,))
        municipios = [row['municipio'] for row in cursor.fetchall()]
        
        cursor.execute('SELECT DISTINCT municipio FROM usuarios WHERE municipio != "Não informado"')
        todos_municipios = [row['municipio'] for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'usuario': {
                'id': usuario['id'],
                'nome': usuario['nome'],
                'email': usuario['email'],
                'profissao': usuario['profissao'],
                'cnes': usuario['cnes'],
                'municipio': usuario['municipio'],
                'municipios': municipios  # Lista de municípios associados
            },
            'todos_municipios': todos_municipios
        })
    except sqlite3.Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

# Rota para atualizar dados do usuário
@app.route('/admin/atualizar_usuario/<int:user_id>', methods=['POST'])
@super_admin_required
def atualizar_usuario(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obter dados do formulário
        nome = request.form['nome']
        email = request.form['email']
        profissao = request.form['profissao']
        cnes = request.form['cnes']
        municipios = request.form.getlist('municipios[]')  # Lista de municípios
        
        # Atualizar dados do usuário
        cursor.execute('''
            UPDATE usuarios
            SET nome = ?, email = ?, profissao = ?, cnes = ?, municipio = ?
            WHERE id = ?
        ''', (nome, email, profissao, cnes, municipios[0] if municipios else 'Não informado', user_id))
        
        # Remover municípios antigos do usuário
        cursor.execute('DELETE FROM usuario_municipios WHERE usuario_id = ?', (user_id,))
        
        # Inserir novos municípios
        for municipio in municipios:
            cursor.execute('INSERT INTO usuario_municipios (usuario_id, municipio) VALUES (?, ?)', 
                          (user_id, municipio))
        
        conn.commit()
        flash('Usuário atualizado com sucesso!', 'success')
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'Erro ao atualizar usuário: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin_painel'))

@app.route('/admin/gerenciar_usuarios', methods=['GET', 'POST'])
@super_admin_required
def admin_gerenciar_usuarios():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # === NOME DO USUÁRIO LOGADO ===
        cursor.execute('SELECT nome FROM usuarios WHERE id = ?', (session['user_id'],))
        user = cursor.fetchone()
        if not user:
            logging.error(f"Usuário com ID {session['user_id']} não encontrado.")
            flash('Usuário não encontrado.', 'danger')
            conn.close()
            return redirect(url_for('login'))
        full_name = user['nome']
        logging.debug(f"Usuário logado: {full_name}")

        # === PAGINAÇÃO ===
        page = request.args.get('page', 1, type=int)
        per_page = 100
        offset = (page - 1) * per_page

        # === CONTAGEM POR PAPEL (TABELA usuarios) ===
        cursor.execute('''
            SELECT role, COUNT(*) AS total
            FROM usuarios
            WHERE ativo = 1 AND approved = 1 AND role IS NOT NULL
            GROUP BY role
        ''')
        counts = {row['role']: row['total'] for row in cursor.fetchall()}

        # === CONTAGEM TOTAL DE APOIO (GERAL) ===
        cursor.execute('''
            SELECT COUNT(*) AS total
            FROM usuarios_apoio
            WHERE ativo = 1 AND approved = 1
        ''')
        apoio_count = cursor.fetchone()['total']

        # === CONTAGEM DE APOIO INDÍGENA (acesso_saude_indigena = 1) ===
        cursor.execute('''
            SELECT COUNT(*) AS total
            FROM usuarios_apoio
            WHERE ativo = 1 AND approved = 1 AND acesso_saude_indigena = 1
        ''')
        indigena_count = cursor.fetchone()['total']

                    # === CONTAGEM DE PNAR (NOVA TABELA) ===
        cursor.execute('''
            SELECT COUNT(*) AS total
            FROM usuarios_apoio
            WHERE ativo = 1 AND approved = 1 AND pnar = 1
        ''')
        pnar_count = cursor.fetchone()['total']

        # === MONTAR TOTAIS PARA OS CARDS ===
        totais_usuarios = {
            'municipal': counts.get('municipal', 0),
            'estadual': counts.get('estadual', 0),
            'comum': counts.get('comum', 0),
            'apoio': apoio_count - indigena_count - pnar_count,
            'indigena': indigena_count,
            'pnar': pnar_count,
            'total': sum(counts.values()) + apoio_count + pnar_count
        }
        logging.debug(f"Contagens de usuários: {totais_usuarios}")

        # === TOTAL PARA PAGINAÇÃO (só usuarios da tabela principal) ===
        cursor.execute('''
            SELECT COUNT(*) AS total
            FROM usuarios
            WHERE ativo = 1 AND approved = 1
        ''')
        total_usuarios = cursor.fetchone()['total']
        total_pages = (total_usuarios + per_page - 1) // per_page

        # === LISTAR USUÁRIOS (apenas da tabela usuarios) ===
        cursor.execute('''
            SELECT id, COALESCE(nome, '') as nome, email, profissao, cnes, municipio, role, is_admin, is_super_admin
            FROM usuarios
            WHERE ativo = 1 AND approved = 1
            ORDER BY nome ASC
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        usuarios = [dict(user) for user in cursor.fetchall()]

        # === DADOS PARA O MAPA (por município) ===
        usuarios_por_municipio = {}
        cursor.execute('''
            SELECT DISTINCT municipio 
            FROM (
                SELECT municipio FROM usuarios WHERE ativo = 1 AND approved = 1
                UNION
                SELECT municipio FROM usuarios_apoio WHERE ativo = 1 AND approved = 1
            ) AS combined
            WHERE municipio IS NOT NULL
        ''')
        municipios = [row['municipio'] for row in cursor.fetchall()]

        for municipio in municipios:
            cursor.execute('''
                SELECT
                    (SELECT COUNT(*) FROM usuarios u
                     WHERE u.municipio = ? AND u.role = 'municipal' AND u.ativo = 1 AND u.approved = 1) AS municipal,
                    (SELECT COUNT(*) FROM usuarios u
                     WHERE u.municipio = ? AND u.role = 'estadual' AND u.ativo = 1 AND u.approved = 1) AS estadual,
                    (SELECT COUNT(*) FROM usuarios u
                     WHERE u.municipio = ? AND u.role = 'comum' AND u.ativo = 1 AND u.approved = 1) AS comum,
                    (SELECT COUNT(*) FROM usuarios_apoio u
                     WHERE u.municipio = ? AND u.ativo = 1 AND u.approved = 1) AS apoio
            ''', (municipio, municipio, municipio, municipio))
            counts = cursor.fetchone()
            usuarios_por_municipio[municipio] = {
                'municipal': counts['municipal'] or 0,
                'estadual': counts['estadual'] or 0,
                'comum': counts['comum'] or 0,
                'apoio': counts['apoio'] or 0
            }

        # === TRATAMENTO DE POST (ALTERAR PAPEL) ===
        if request.method == 'POST':
            usuario_id = request.form.get('usuario_id')
            novo_role = request.form.get('novo_role')
            logging.debug(f"POST: usuario_id={usuario_id}, novo_role={novo_role}")

            if not usuario_id or not novo_role:
                flash('ID do usuário ou novo papel inválido.', 'danger')
                conn.close()
                return redirect(url_for('admin_gerenciar_usuarios', page=page))

            if novo_role not in ['comum', 'municipal', 'estadual', 'apoio']:
                flash('Papel inválido.', 'danger')
                conn.close()
                return redirect(url_for('admin_gerenciar_usuarios', page=page))

            if int(usuario_id) == session['user_id']:
                flash('Você não pode modificar seu próprio papel.', 'danger')
                conn.close()
                return redirect(url_for('admin_gerenciar_usuarios', page=page))

            try:
                cursor.execute('''
                    SELECT id, COALESCE(nome, '') as nome, email, municipio, senha 
                    FROM usuarios 
                    WHERE id = ? AND ativo = 1 AND approved = 1
                ''', (usuario_id,))
                user_in_usuarios = cursor.fetchone()

                if not user_in_usuarios:
                    flash('Usuário não encontrado.', 'danger')
                    conn.close()
                    return redirect(url_for('admin_gerenciar_usuarios', page=page))

                if novo_role == 'apoio':
                    required = ['nome', 'email', 'municipio', 'senha']
                    for field in required:
                        if user_in_usuarios[field] is None:
                            flash(f'O campo {field} é obrigatório para apoio.', 'danger')
                            conn.close()
                            return redirect(url_for('admin_gerenciar_usuarios', page=page))

                    cursor.execute('''
                        INSERT INTO usuarios_apoio (nome, email, municipio, senha, ativo, approved, acesso_saude_indigena)
                        VALUES (?, ?, ?, ?, 1, 1, 0)
                    ''', (user_in_usuarios['nome'], user_in_usuarios['email'], user_in_usuarios['municipio'], user_in_usuarios['senha']))
                    cursor.execute('UPDATE usuarios SET ativo = 0 WHERE id = ?', (usuario_id,))
                else:
                    is_admin = 1 if novo_role == 'municipal' else 0
                    is_super_admin = 1 if novo_role == 'estadual' else 0
                    cursor.execute('''
                        UPDATE usuarios 
                        SET role = ?, is_admin = ?, is_super_admin = ? 
                        WHERE id = ?
                    ''', (novo_role, is_admin, is_super_admin, usuario_id))

                # Log da ação
                role_traduzido = {
                    'comum': 'Usuário Comum',
                    'municipal': 'Administrador Municipal',
                    'estadual': 'Administrador Estadual',
                    'apoio': 'Usuário de Apoio'
                }.get(novo_role, novo_role)

                cursor.execute('''
                    INSERT INTO acoes_administrativas (admin_id, usuario_id, acao, data_acao, detalhes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session['user_id'], usuario_id, 'Alteração de Papel',
                      datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                      f'Papel alterado para {role_traduzido}'))

                conn.commit()
                flash(f'Papel alterado para {role_traduzido}.', 'success')
                conn.close()
                return redirect(url_for('admin_gerenciar_usuarios', page=page))

            except Exception as e:
                logging.error(f"Erro ao alterar papel: {str(e)}")
                flash(f'Erro ao alterar papel: {str(e)}', 'danger')
                conn.close()
                return redirect(url_for('admin_gerenciar_usuarios', page=page))

        # === PAGINAÇÃO (classe) ===
        class Pagination:
            def __init__(self, items, page, per_page, total, total_pages):
                self.items = items
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = total_pages
                self.has_prev = page > 1
                self.has_next = page < total_pages
                self.prev_num = page - 1 if self.has_prev else None
                self.next_num = page + 1 if self.has_next else None

        paginated_usuarios = Pagination(usuarios, page, per_page, total_usuarios, total_pages)

        # === FECHAR CONEXÃO E RENDERIZAR ===
        conn.close()

        # Teste de serialização JSON
        try:
            json.dumps(usuarios_por_municipio)
        except Exception as e:
            logging.error(f"Erro ao serializar mapa: {str(e)}")
            usuarios_por_municipio = {}

        return render_template('admin_gerenciar_usuarios.html',
                               usuarios=paginated_usuarios,
                               usuarios_por_municipio=usuarios_por_municipio,
                               totais_usuarios=totais_usuarios,
                               full_name=full_name)

    except sqlite3.OperationalError as e:
        logging.error(f"Erro no banco: {str(e)}")
        flash(f'Erro no banco de dados: {str(e)}', 'danger')
        return redirect(url_for('admin_painel'))
    except Exception as e:
        logging.error(f"Erro inesperado: {str(e)}")
        flash(f'Erro ao carregar página: {str(e)}', 'danger')
        return redirect(url_for('admin_painel'))

@app.route('/admin/cadastrar_apoio', methods=['POST'])
@admin_required
def cadastrar_apoio():
    nome = request.form.get('nome')
    cpf = request.form.get('cpf')
    email = request.form.get('email')
    senha = request.form.get('senha')
    confirmar_senha = request.form.get('confirmar_senha')
    saude_indigena = request.form.get('saude_indigena') == 'on'  # NOVO: Lê o checkbox

    # Validações
    errors = []
    if not nome:
        errors.append('Nome é obrigatório.')
    if not cpf:
        errors.append('CPF é obrigatório.')
    else:
        cpf = re.sub(r'[^\d]', '', cpf)
        if not re.match(r'^\d{11}$', cpf):
            errors.append('CPF inválido. Deve conter 11 dígitos numéricos.')
    if not email:
        errors.append('E-mail é obrigatório.')
    elif not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        errors.append('E-mail inválido.')
    if not senha:
        errors.append('Senha é obrigatória.')
    if senha != confirmar_senha:
        errors.append('As senhas não coincidem.')
    if len(senha) < 6:
        errors.append('A senha deve ter pelo menos 6 caracteres.')

    if errors:
        return jsonify({'success': False, 'message': ' '.join(errors)}), 400

    # Permissões do admin
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT role, is_super_admin, municipio FROM usuarios WHERE id = ?', (session['user_id'],))
    admin = cursor.fetchone()
    if not admin:
        conn.close()
        return jsonify({'success': False, 'message': 'Administrador não encontrado.'}), 404

    municipio = admin['municipio'] if admin['role'] == 'municipal' and not admin['is_super_admin'] else None
    email = email.lower()

    # Verificar duplicidade
    cursor.execute('SELECT id, ativo FROM usuarios_apoio WHERE email = ? OR cpf = ?', (email, cpf))
    existing_user = cursor.fetchone()

    try:
        senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        acesso_indigena_value = 1 if saude_indigena else 0  # Valor para o banco

        if existing_user:
            if existing_user['ativo'] == 1:
                conn.close()
                return jsonify({'success': False, 'message': 'E-mail ou CPF já cadastrado e ativo.'}), 400
            else:
                # Recadastro
                cursor.execute('''
                    UPDATE usuarios_apoio
                    SET nome = ?, cpf = ?, email = ?, senha = ?, municipio = ?, approved = 1, ativo = 1,
                        acesso_saude_indigena = ?
                    WHERE id = ?
                ''', (nome, cpf, email, senha_hash, municipio, acesso_indigena_value, existing_user['id']))
                
                cursor.execute('''
                    INSERT INTO acoes_administrativas (admin_id, usuario_id, acao, data_acao, detalhes, tipo_usuario)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (session['user_id'], existing_user['id'], 'Recadastro Apoio',
                      datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                      f'Recadastrado com acesso indígena: {"Sim" if saude_indigena else "Não"}', 'apoio'))
        else:
            # Novo cadastro
            cursor.execute('''
                INSERT INTO usuarios_apoio (nome, cpf, email, senha, municipio, approved, ativo, acesso_saude_indigena)
                VALUES (?, ?, ?, ?, ?, 1, 1, ?)
            ''', (nome, cpf, email, senha_hash, municipio, acesso_indigena_value))
            
            cursor.execute('''
                INSERT INTO acoes_administrativas (admin_id, usuario_id, acao, data_acao, detalhes, tipo_usuario)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], cursor.lastrowid, 'Cadastro Apoio',
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                  f'Novo apoio com acesso indígena: {"Sim" if saude_indigena else "Não"}', 'apoio'))

        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Usuário de apoio cadastrado com sucesso!'})

    except sqlite3.IntegrityError as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': 'E-mail ou CPF já cadastrado.'}), 400
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

@app.route('/admin/listar_usuarios_apoio', methods=['GET'])
@super_admin_required
def listar_usuarios_apoio():
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, COALESCE(nome, '') as nome, acesso_saude_indigena AS saude_indigena
            FROM usuarios_apoio
            WHERE ativo = 1 AND approved = 1
            ORDER BY nome ASC
        ''')
        usuarios_apoio = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return jsonify({'success': True, 'usuarios_apoio': usuarios_apoio})
    except Exception as e:
        logging.error(f"Erro ao listar usuários de apoio: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/excluir_apoio', methods=['POST'])
@admin_required
def excluir_apoio():
    usuario_id = request.form.get('usuario_id')
    if not usuario_id:
        flash('ID do usuário não fornecido.', 'error')
        return jsonify({'success': False, 'message': 'ID do usuário não fornecido.'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, municipio FROM usuarios_apoio WHERE id = ? AND ativo = 1", (usuario_id,))
        usuario_apoio = cursor.fetchone()
        if not usuario_apoio:
            conn.close()
            flash('Usuário de apoio não encontrado ou já inativo.', 'error')
            return jsonify({'success': False, 'message': 'Usuário de apoio não encontrado ou já inativo.'}), 404

        current_user_id = session.get('user_id')
        cursor.execute("SELECT role, municipio, is_super_admin FROM usuarios WHERE id = ?", (current_user_id,))
        current_user = cursor.fetchone()
        if not current_user:
            conn.close()
            flash('Administrador não encontrado.', 'error')
            return jsonify({'success': False, 'message': 'Administrador não encontrado.'}), 404

        if current_user['role'] == 'municipal' and not current_user['is_super_admin']:
            if usuario_apoio['municipio'] and usuario_apoio['municipio'] != current_user['municipio']:
                conn.close()
                flash('Você não tem permissão para excluir usuários de outros municípios.', 'error')
                return jsonify({'success': False, 'message': 'Você não tem permissão para excluir usuários de outros municípios.'}), 403

        cursor.execute("UPDATE usuarios_apoio SET ativo = 0 WHERE id = ?", (usuario_id,))
        cursor.execute('''
            INSERT INTO acoes_administrativas (admin_id, usuario_id, acao, data_acao, detalhes, tipo_usuario)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            current_user_id, 
            usuario_id, 
            'Exclusão de Apoio', 
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            f'Usuário de apoio ID {usuario_id} marcado como inativo',
            'apoio'
        ))

        conn.commit()
        conn.close()

        flash('Usuário de apoio desativado com sucesso.', 'success')
        logging.info(f"Usuário de apoio ID {usuario_id} desativado com sucesso pelo usuário ID {current_user_id}.")
        return jsonify({'success': True, 'message': 'Usuário de apoio desativado com sucesso.'})

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
            conn.close()
        logging.error(f"Erro ao desativar usuário de apoio ID {usuario_id}: {str(e)}")
        flash('Erro no banco de dados. Contate o administrador.', 'error')
        return jsonify({'success': False, 'message': f'Erro no banco de dados: {str(e)}'}), 500
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        logging.error(f"Erro inesperado ao desativar usuário de apoio ID {usuario_id}: {str(e)}")
        flash('Erro inesperado ao desativar usuário.', 'error')
        return jsonify({'success': False, 'message': f'Erro inesperado: {str(e)}'}), 500

@app.route('/admin/listar_pnar', methods=['GET'])
@super_admin_required
def listar_pnar():
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, nome, COALESCE(servico, 'Não informado') as servico
            FROM usuarios_apoio
            WHERE ativo = 1 AND approved = 1 AND pnar = 1
            ORDER BY nome ASC
        ''')
        usuarios = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({'success': True, 'usuarios': usuarios})
    except Exception as e:
        logging.error(f"Erro ao listar PNAR: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao carregar PNAR.'}), 500

@app.route('/admin/cadastrar_pnar', methods=['POST'])
@super_admin_required
def cadastrar_pnar():
    try:
        dados = request.form
        nome = dados.get('nome', '').strip()
        cpf = dados.get('cpf', '').strip()
        email = dados.get('email', '').strip().lower()
        senha = dados.get('senha', '')
        confirmar_senha = dados.get('confirmar_senha', '')
        servico = dados.get('servico', '').strip()

        if not all([nome, cpf, email, senha, servico]):
            return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios.'}), 400
        if senha != confirmar_senha:
            return jsonify({'success': False, 'message': 'Senhas não coincidem.'}), 400
        if len(senha) < 6:
            return jsonify({'success': False, 'message': 'Senha deve ter 6+ caracteres.'}), 400
        
        cpf = re.sub(r'\D', '', cpf)
        if len(cpf) != 11:
            return jsonify({'success': False, 'message': 'CPF inválido.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT id, ativo FROM usuarios_apoio WHERE cpf = ? OR email = ?', (cpf, email))
        existente = cursor.fetchone()

        hash_senha = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        if existente:
            user_id = existente['id']
            if existente['ativo'] == 1:
                conn.close()
                return jsonify({'success': False, 'message': 'Este CPF ou e-mail já está ativo como PNAR.'}), 400
            
            # REATIVAÇÃO CORRETA: pnar = 1 TAMBÉM!
            cursor.execute('''
                UPDATE usuarios_apoio 
                SET ativo = 1, approved = 1, pnar = 1, nome = ?, email = ?, senha = ?, servico = ?
                WHERE id = ?
            ''', (nome, email, hash_senha, servico, user_id))
            
            acao = 'Reativação PNAR'
            detalhes = f'PNAR {nome} reativado no serviço: {servico}'
        else:
            cursor.execute('''
                INSERT INTO usuarios_apoio 
                (nome, cpf, email, senha, servico, approved, ativo, pnar)
                VALUES (?, ?, ?, ?, ?, 1, 1, 1)
            ''', (nome, cpf, email, hash_senha, servico))
            user_id = cursor.lastrowid
            acao = 'Cadastro PNAR'
            detalhes = f'PNAR {nome} criado no serviço: {servico}'

        cursor.execute('''
            INSERT INTO acoes_administrativas 
            (admin_id, usuario_id, acao, data_acao, detalhes, tipo_usuario)
            VALUES (?, ?, ?, ?, ?, 'apoio')
        ''', (session['user_id'], user_id, acao,
              datetime.now().strftime('%Y-%m-%d %H:%M:%S'), detalhes))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'PNAR {nome} {"reativado" if existente else "cadastrado"} com sucesso!'
        })

    except Exception as e:
        logging.error(f"Erro ao cadastrar/reativar PNAR: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro interno.'}), 500

@app.route('/admin/excluir_pnar', methods=['POST'])
@super_admin_required
def excluir_pnar():
    try:
        uid = request.form.get('usuario_id')
        if not uid:
            return jsonify({'success': False, 'message': 'ID não informado.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # PRIMEIRO VERIFICA SE EXISTE E É PNAR
        cursor.execute('SELECT id, nome, servico FROM usuarios_apoio WHERE id = ? AND pnar = 1', (uid,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            return jsonify({'success': False, 'message': 'PNAR não encontrado.'}), 404

        # AGORA SIM: PEGA OS DADOS COM SEGURANÇA
        nome = user['nome'] or 'Desconhecido'
        servico = user['servico'] or 'Não informado'

        # APAGA DE VEZ
        cursor.execute('DELETE FROM usuarios_apoio WHERE id = ?', (uid,))

        # LOG
        cursor.execute('''
            INSERT INTO acoes_administrativas 
            (admin_id, usuario_id, acao, data_acao, detalhes, tipo_usuario)
            VALUES (?, ?, ?, ?, ?, 'apoio')
        ''', (
            session['user_id'],
            uid,
            'Exclusão PERMANENTE PNAR',
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            f'PNAR {nome} ({servico}) apagado permanentemente'
        ))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'PNAR {nome} excluído permanentemente!'
        })

    except Exception as e:
        logging.error(f"Erro ao excluir PNAR: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro interno no servidor.'}), 500

@app.route('/admin/saude-indigena', methods=['GET', 'POST'])
@admin_required
def saude_indigena():
    try:
        logging.debug(f"Entrando em saude_indigena() - user_id: {session.get('user_id')}")

        conn = get_db_connection()
        cursor = conn.cursor()

        # === 1. USUÁRIO ===
        if session.get('tipo_usuario') == 'apoio':
            cursor.execute('''
                SELECT a.id, a.municipio, 'apoio' as role, 0 as is_admin, 0 as is_super_admin, a.nome,
                       COALESCE(a.acesso_saude_indigena, 0) as acesso_saude_indigena
                FROM usuarios_apoio a WHERE a.id = ?
            ''', (session['user_id'],))
        else:
            cursor.execute('''
                SELECT u.id, u.municipio, u.role, u.is_admin, u.is_super_admin, u.nome,
                       COALESCE(a.acesso_saude_indigena, 0) as acesso_saude_indigena
                FROM usuarios u
                LEFT JOIN usuarios_apoio a ON a.id = u.id
                WHERE u.id = ?
            ''', (session['user_id'],))

        user = cursor.fetchone()
        if not user:
            conn.close()
            flash('Usuário não encontrado.', 'error')
            return redirect(url_for('calculadora'))

        user_id = user['id']
        user_role = user['role']
        is_super_admin = user['is_super_admin']
        acesso_saude_indigena = user['acesso_saude_indigena'] == 1
        full_name = user['nome']
        user_municipio = user['municipio']

        ver_todos_municipios = acesso_saude_indigena or (is_super_admin == 1 and user_role == 'estadual')

        # === 2. MUNICÍPIOS PERMITIDOS ===
        if ver_todos_municipios:
            cursor.execute('SELECT DISTINCT municipio FROM calculos WHERE raca_cor_etnia = ? ORDER BY municipio', ('Indígena',))
        else:
            cursor.execute('''
                SELECT municipio FROM usuario_municipios WHERE usuario_id = ?
                UNION SELECT municipio FROM usuarios WHERE id = ? AND municipio IS NOT NULL
                UNION SELECT municipio FROM usuarios_apoio WHERE id = ? AND municipio IS NOT NULL
            ''', (user_id, user_id, user_id))
            rows = cursor.fetchall()
            municipios = [r['municipio'] for r in rows if r['municipio']]
            if not municipios and user_municipio:
                municipios = [user_municipio]
            if municipios:
                placeholders = ','.join(['?'] * len(municipios))
                cursor.execute(f'''
                    SELECT DISTINCT municipio FROM calculos 
                    WHERE raca_cor_etnia = 'Indígena' AND municipio IN ({placeholders})
                    ORDER BY municipio
                ''', tuple(municipios))
            else:
                municipios = []
        municipios = [row['municipio'] for row in cursor.fetchall()]

        # === 3. FILTROS ===
        filtro_municipio = request.form.get('municipio') or request.args.get('municipio')
        filtro_data_inicio = request.form.get('data_inicio') or request.args.get('data_inicio')
        filtro_data_fim = request.form.get('data_fim') or request.args.get('data_fim')

        if filtro_municipio and filtro_municipio not in municipios:
            flash('Acesso negado ao município.', 'error')
            filtro_municipio = None

        # === 4. BASE PARA FILTROS (APENAS INDÍGENAS) ===
        base_where = ["raca_cor_etnia = 'Indígena'"]
        base_params = []

        if filtro_municipio:
            base_where.append("municipio = ?")
            base_params.append(filtro_municipio)
        if filtro_data_inicio:
            base_where.append("data_envio >= ?")
            base_params.append(filtro_data_inicio)
        if filtro_data_fim:
            base_where.append("data_envio <= ?")
            base_params.append(filtro_data_fim)
        if not ver_todos_municipios and municipios:
            placeholders = ','.join(['?'] * len(municipios))
            base_where.append(f"municipio IN ({placeholders})")
            base_params.extend(municipios)

        where_clause = ' AND '.join(base_where)
        where_full = f"WHERE {where_clause}" if where_clause else "WHERE 1=1"

        # === 5. ÚLTIMOS REGISTROS (CARDS) - APENAS ATIVAS (desfecho NULL, fa=0) ===
        latest_where_cards = where_full + " AND desfecho IS NULL AND fa = 0"
        latest_subquery = f'''
            SELECT 
                COALESCE(
                    NULLIF(TRIM(cpf), ''), 
                    NULLIF(TRIM(cpf), '000.000.000-00'),
                    'sem_cpf'
                ) AS cpf_limpo,
                nome_gestante, 
                data_nasc,
                MAX(id) as max_id
            FROM calculos
            {latest_where_cards}
            GROUP BY cpf_limpo, nome_gestante, data_nasc
        '''

        query_ultimos = f'''
            SELECT c.*
            FROM calculos c
            INNER JOIN ({latest_subquery}) latest ON c.id = latest.max_id
        '''

        logging.debug(f"Query cards:\n{query_ultimos}\nParams: {base_params}")
        cursor.execute(query_ultimos, base_params)
        ultimos_registros = [dict(row) for row in cursor.fetchall()]
        logging.debug(f"Registros para cards (ativas): {len(ultimos_registros)}")

        # === 6. TODOS OS REGISTROS (TABELA CONSOLIDADA) - TODOS INDÍGENAS ===
        query_todos = f'''
            SELECT c.*
            FROM calculos c
            {where_full}
            ORDER BY c.data_envio DESC
        '''
        cursor.execute(query_todos, base_params)
        todos_registros = [dict(row) for row in cursor.fetchall()]
        logging.debug(f"Registros na tabela (consolidado): {len(todos_registros)}")

        # === 7. TOTAL GERAL ===
        total_geral = cursor.execute('SELECT COUNT(*) FROM calculos WHERE fa = 0').fetchone()[0]
        total_indigenas = len(ultimos_registros)
        percentual_indigenas = round(total_indigenas / total_geral * 100, 1) if total_geral > 0 else 0

        # === 8. MAPEAMENTO SEGURO ===
        def mapear_campo(valor, mapa, default='Não informado'):
            if not valor:
                return default
            try:
                items = json.loads(valor) if isinstance(valor, str) else [valor]
                mapped = [mapa.get(str(i).strip(), str(i).strip()) for i in items if str(i).strip()]
                return ', '.join(mapped) if mapped else default
            except:
                return mapa.get(str(valor).strip(), default)

        # === 9. ESTATÍSTICAS (APENAS REGISTROS ATIVOS) ===
        genero_counts = {}
        sexualidade_counts = {}
        etnia_indigena_counts = {}
        total_etnias = 0
        periodo_gestacional = {}
        caracteristicas_counts = {}
        avaliacao_nutricional_counts = {}
        comorbidades_counts = {}
        historia_obstetrica_counts = {}
        condicoes_gestacionais_counts = {}
        desfecho_counts = {}
        risco_habitual = risco_intermediario = risco_alto = 0

        for reg in ultimos_registros:
            # Gênero
            genero = GENERO_MAP.get(reg.get('genero', ''), 'Não informado')
            genero_counts[genero] = genero_counts.get(genero, 0) + 1

            # Sexualidade
            sexual = SEXUALIDADE_MAP.get(reg.get('sexualidade', ''), 'Não informado')
            sexualidade_counts[sexual] = sexualidade_counts.get(sexual, 0) + 1

            # Etnia
            etnia = get_etnia_nome(reg.get('etnia_indigena', '')).strip()
            if etnia and etnia not in ['Não informado', '-', '']:
                etnia_indigena_counts[etnia] = etnia_indigena_counts.get(etnia, 0) + 1
                total_etnias += 1

            # Período
            periodo = reg.get('periodo_gestacional') or 'Não informado'
            periodo_gestacional[periodo] = periodo_gestacional.get(periodo, 0) + 1

            # Campos JSON
            for campo, mapa, contador in [
                ('caracteristicas', CARACTERISTICAS_MAP, caracteristicas_counts),
                ('avaliacao_nutricional', AVALIACAO_NUTRICIONAL_MAP, avaliacao_nutricional_counts),
                ('comorbidades', COMORBIDADES_MAP, comorbidades_counts),
                ('historia_obstetrica', HISTORIA_OBSTETRICA_MAP, historia_obstetrica_counts),
                ('condicoes_gestacionais', CONDICOES_GESTACIONAIS_MAP, condicoes_gestacionais_counts)
            ]:
                texto = mapear_campo(reg.get(campo), mapa, '-')
                for item in [x.strip() for x in texto.split(',') if x.strip() != '-']:
                    contador[item] = contador.get(item, 0) + 1

            # Desfecho (só para cards)
            desf = DESFECHO_MAP.get(reg.get('desfecho'), 'Sem desfecho')
            desfecho_counts[desf] = desfecho_counts.get(desf, 0) + 1

            # Risco
            risco = (reg.get('classificacao_risco') or '').strip().lower()
            if risco == 'risco habitual':
                risco_habitual += 1
            elif risco in ['médio risco', 'risco intermediário']:
                risco_intermediario += 1
            elif risco == 'alto risco':
                risco_alto += 1

        # Formatar etnias
        for etnia, count in etnia_indigena_counts.items():
            etnia_indigena_counts[etnia] = {
                'count': count,
                'porcentagem': round(count / total_etnias * 100, 1) if total_etnias > 0 else 0
            }

        # === 9.5 CONTADORES DO CONSOLIDADO (DISTINTOS POR GESTANTE) ===
        gestantes_vistas = set()
        fora_de_area_distinto = 0
        desfecho_consolidado_distinto = {}

        for reg in todos_registros:
            cpf = reg.get('cpf', '').strip()
            if cpf in ['000.000.000-00', '']:
                cpf = 'sem_cpf'
            chave_gestante = (cpf, reg.get('nome_gestante'), reg.get('data_nasc'))

            if chave_gestante not in gestantes_vistas:
                gestantes_vistas.add(chave_gestante)

                # Fora de Área
                if reg.get('fa') == 1:
                    fora_de_area_distinto += 1

                # Desfechos (só se tiver valor)
                desfecho_raw = reg.get('desfecho')
                if desfecho_raw:
                    desfecho_nome = DESFECHO_MAP.get(desfecho_raw, desfecho_raw)
                    if desfecho_nome != 'Não informado':
                        desfecho_consolidado_distinto[desfecho_nome] = desfecho_consolidado_distinto.get(desfecho_nome, 0) + 1

        # === 10. TOTAIS ===
        total_desfechos = sum(desfecho_counts.values())
        total_desfechos_consolidado = sum(desfecho_consolidado_distinto.values())
        total_gestantes_distintas = len(gestantes_vistas)

        # === 11. ESTATÍSTICAS FINAIS ===
        estatisticas = {
            'total_registros': total_indigenas,
            'municipios_unicos': len(set(r['municipio'] for r in ultimos_registros if r['municipio'])),
            'percentual_indigenas': percentual_indigenas,
            'total_etnias_indigenas': total_etnias,
            'etnia_indigena_counts': etnia_indigena_counts,
            'genero_counts': genero_counts,
            'sexualidade_counts': sexualidade_counts,
            'periodo_gestacional': periodo_gestacional,
            'caracteristicas_counts': caracteristicas_counts,
            'avaliacao_nutricional_counts': avaliacao_nutricional_counts,
            'comorbidades_counts': comorbidades_counts,
            'historia_obstetrica_counts': historia_obstetrica_counts,
            'condicoes_gestacionais_counts': condicoes_gestacionais_counts,
            'desfecho_counts': desfecho_counts,  # Cards
            'total_desfechos': total_desfechos,
            'desfecho_consolidado_distinto': desfecho_consolidado_distinto,  # Consolidado distinto
            'total_desfechos_consolidado': total_desfechos_consolidado,
            'fora_de_area_distinto': fora_de_area_distinto,  # Distinto
            'total_gestantes_distintas': total_gestantes_distintas,
            'risco_habitual': risco_habitual,
            'risco_intermediario': risco_intermediario,
            'risco_alto': risco_alto,
        }

        # === 12. FORMATAR TABELA (TODOS OS REGISTROS INDÍGENAS) ===
        for reg in todos_registros:
            reg['etnia_indigena'] = get_etnia_nome(reg.get('etnia_indigena', ''))
            reg['genero'] = GENERO_MAP.get(reg.get('genero'), 'Não informado')
            reg['sexualidade'] = SEXUALIDADE_MAP.get(reg.get('sexualidade'), 'Não informado')

            for campo, mapa in [
                ('caracteristicas', CARACTERISTICAS_MAP),
                ('avaliacao_nutricional', AVALIACAO_NUTRICIONAL_MAP),
                ('comorbidades', COMORBIDADES_MAP),
                ('historia_obstetrica', HISTORIA_OBSTETRICA_MAP),
                ('condicoes_gestacionais', CONDICOES_GESTACIONAIS_MAP)
            ]:
                reg[campo] = mapear_campo(reg.get(campo), mapa, '-')

            risco = (reg.get('classificacao_risco') or '').strip().lower()
            reg['classificacao_risco'] = {
                'risco habitual': 'Risco Habitual',
                'médio risco': 'Risco Intermediário',
                'risco intermediário': 'Risco Intermediário',
                'alto risco': 'Risco Alto'
            }.get(risco, 'Não informado')

            desfecho_raw = reg.get('desfecho')
            reg['desfecho'] = DESFECHO_MAP.get(desfecho_raw, '-') if desfecho_raw else '-'
            reg['fa'] = 'Sim' if reg.get('fa') == 1 else 'Não'

        conn.close()

        return render_template('admin_saude_indigena.html',
                               registros=todos_registros,
                               estatisticas=estatisticas,
                               municipios=municipios,
                               filtro_municipio=filtro_municipio,
                               filtro_data_inicio=filtro_data_inicio,
                               filtro_data_fim=filtro_data_fim,
                               current_user={
                                   'nome': full_name,
                                   'role': user_role,
                                   'municipio': user_municipio,
                                   'saude_indigena': acesso_saude_indigena,
                                   'is_super_admin': is_super_admin == 1
                               })

    except Exception as e:
        if 'conn' in locals():
            conn.close()
        logging.error(f"Erro em saude_indigena: {str(e)}", exc_info=True)
        flash('Erro interno ao carregar relatório.', 'error')
        return redirect(url_for('admin_painel'))

@app.route('/monitoramento', methods=['GET', 'POST'])
@admin_required
@apoio_required
def monitoramento():
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = session.get('user_id')
    user_role = session.get('role')
    user_municipio = session.get('municipio')
    
    # Obter filtros do formulário
    filtro_macrorregiao = request.form.get('macrorregiao', '')
    filtro_regiao = request.form.get('regiao', '')
    filtro_municipio = request.form.get('municipio', '')

    # Se município for selecionado, determinar macrorregião e região automaticamente
    if filtro_municipio and not filtro_macrorregiao and not filtro_regiao:
        filtro_macrorregiao, filtro_regiao = find_macrorregiao_regiao(filtro_municipio)

    # Determinar a lista de municípios permitidos com base nos filtros
    municipios_permitidos = []
    if filtro_macrorregiao:
        if filtro_regiao:
            municipios_permitidos = regioes_por_macrorregiao.get(filtro_macrorregiao, {}).get(filtro_regiao, [])
        else:
            for regiao in regioes_por_macrorregiao.get(filtro_macrorregiao, {}):
                municipios_permitidos.extend(regioes_por_macrorregiao[filtro_macrorregiao][regiao])
    else:
        for macro in regioes_por_macrorregiao:
            for regiao in regioes_por_macrorregiao[macro]:
                municipios_permitidos.extend(regioes_por_macrorregiao[macro][regiao])
    
    # Se houver filtro de município, sobrepõe os outros filtros
    if filtro_municipio:
        municipios_permitidos = [filtro_municipio]

    # Aplicar restrição de município para usuários com role 'municipal' ou 'apoio'
    if user_role in ['municipal', 'apoio'] and user_municipio:
        if user_municipio not in municipios_permitidos:
            municipios_permitidos = [user_municipio]
            filtro_municipio = user_municipio
            filtro_macrorregiao, filtro_regiao = find_macrorregiao_regiao(user_municipio)

    # Inicializar estatísticas
    estatisticas = {
        'total_registros': 0,
        'classificacao_risco': {
            'risco_habitual': 0,
            'risco_intermediario': 0,
            'risco_alto': 0
        },
        'municipios_unicos': 0
    }
    usuarios_por_municipio = {}
    municipios = []

    # Consulta para estatísticas de cálculos
    query_calculos = '''
        SELECT c.*, u.municipio as user_municipio
        FROM calculos c
        JOIN usuarios u ON c.user_id = u.id
        WHERE c.fa = 0
    '''
    params = []
    if municipios_permitidos:
        query_calculos += ' AND c.municipio IN (' + ','.join(['?'] * len(municipios_permitidos)) + ')'
        params.extend(municipios_permitidos)

    cursor.execute(query_calculos, params)
    fichas = cursor.fetchall()

    municipios_set = set()
    for ficha in fichas:
        municipio = ficha['municipio']
        if municipio not in municipios_permitidos:
            continue
        municipios_set.add(municipio)
        estatisticas['total_registros'] += 1
        classificacao = ficha['classificacao_risco']
        if classificacao == 'Risco Habitual':
            estatisticas['classificacao_risco']['risco_habitual'] += 1
        elif classificacao == 'Risco Intermediário':
            estatisticas['classificacao_risco']['risco_intermediario'] += 1
        elif classificacao == 'Risco Alto':
            estatisticas['classificacao_risco']['risco_alto'] += 1

        if municipio not in usuarios_por_municipio:
            usuarios_por_municipio[municipio] = {
                'total': 0,
                'risco_habitual': 0,
                'risco_intermediario': 0,
                'risco_alto': 0
            }
        usuarios_por_municipio[municipio]['total'] += 1
        if classificacao == 'Risco Habitual':
            usuarios_por_municipio[municipio]['risco_habitual'] += 1
        elif classificacao == 'Risco Intermediário':
            usuarios_por_municipio[municipio]['risco_intermediario'] += 1
        elif classificacao == 'Risco Alto':
            usuarios_por_municipio[municipio]['risco_alto'] += 1

    estatisticas['municipios_unicos'] = len(municipios_set)
    municipios = sorted(list(municipios_set))

    # Consulta para usuários ativos
    usuarios = []
    if municipios_permitidos:
        query_usuarios = '''
            SELECT id, nome, cpf, municipio, profissao, role, approved, ativo
            FROM usuarios
            WHERE municipio IN ({}) AND ativo = 1
        '''.format(','.join(['?'] * len(municipios_permitidos)))
        cursor.execute(query_usuarios, municipios_permitidos)
        usuarios.extend(cursor.fetchall())

        query_apoio = '''
            SELECT id, nome, cpf, municipio, NULL as profissao, 'apoio' as role, approved, ativo
            FROM usuarios_apoio
            WHERE municipio IN ({}) AND ativo = 1
        '''.format(','.join(['?'] * len(municipios_permitidos)))
        cursor.execute(query_apoio, municipios_permitidos)
        usuarios.extend(cursor.fetchall())

    conn.close()

    return render_template('monitoramento.html',
                          fichas=fichas,
                          estatisticas=estatisticas,
                          municipios=municipios,
                          filtro_municipio=filtro_municipio,
                          filtro_regiao=filtro_regiao,
                          filtro_macrorregiao=filtro_macrorregiao,
                          usuarios_por_municipio=usuarios_por_municipio,
                          usuarios=usuarios,
                          regioes_por_macrorregiao=regioes_por_macrorregiao)

@app.route('/admin/senha', methods=['GET'])
@admin_required
def admin_senha():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obter informações do administrador logado
        cursor.execute('SELECT role, is_super_admin, municipio FROM usuarios WHERE id = ?', (session['user_id'],))
        admin = cursor.fetchone()
        if not admin:
            conn.close()
            flash('Administrador não encontrado.', 'error')
            return redirect(url_for('calculadora'))

        admin_role = admin['role']
        is_super_admin = admin['is_super_admin']
        admin_municipio = admin['municipio']

        # Definir a query com base no papel do administrador
        if admin_role == 'estadual' and is_super_admin:
            # Administradores estaduais veem todos os usuários
            cursor.execute('SELECT id, nome, email, approved, municipio, role FROM usuarios')
        else:
            # Administradores municipais veem apenas usuários do seu município
            cursor.execute('SELECT id, nome, email, approved, municipio, role FROM usuarios WHERE municipio = ?', (admin_municipio,))

        usuarios = [dict(user) for user in cursor.fetchall()]
        conn.close()
        return render_template('admin_senha.html', usuarios=usuarios)
    except sqlite3.OperationalError as e:
        flash(f'Erro no banco de dados: {str(e)}. Contate o administrador.', 'danger')
        return redirect(url_for('calculadora'))

@app.route('/admin/reset_senha', methods=['POST'])
@admin_required
def admin_reset_senha():
    email = request.form.get('email')
    nova_senha = request.form.get('nova_senha')

    if not email or not nova_senha:
        flash('E-mail e nova senha são obrigatórios.', 'danger')
        return redirect(url_for('admin_senha'))

    if len(nova_senha) < 6:
        flash('A nova senha deve ter pelo menos 6 caracteres.', 'danger')
        return redirect(url_for('admin_senha'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT role, is_super_admin, municipio FROM usuarios WHERE id = ?', (session['user_id'],))
        admin = cursor.fetchone()
        if not admin:
            conn.close()
            flash('Administrador não encontrado.', 'danger')
            return redirect(url_for('admin_senha'))

        admin_role = admin['role']
        is_super_admin = admin['is_super_admin']
        admin_municipio = admin['municipio']

        cursor.execute('SELECT id, role, municipio FROM usuarios WHERE email = ?', (email,))
        target_user = cursor.fetchone()
        if not target_user:
            conn.close()
            flash('Usuário não encontrado.', 'danger')
            return redirect(url_for('admin_senha'))

        if admin_role == 'municipal' and not is_super_admin:
            if target_user['municipio'] != admin_municipio:
                conn.close()
                flash('Acesso negado: você só pode alterar senhas de usuários do seu município.', 'danger')
                return redirect(url_for('admin_senha'))
            if target_user['role'] == 'estadual':
                conn.close()
                flash('Acesso negado: apenas administradores estaduais podem alterar senhas de outros administradores estaduais.', 'danger')
                return redirect(url_for('admin_senha'))
        elif admin_role == 'estadual' and is_super_admin:
            pass
        else:
            conn.close()
            flash('Acesso negado: permissões insuficientes.', 'danger')
            return redirect(url_for('admin_senha'))

        nova_senha_hash = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute('UPDATE usuarios SET senha = ? WHERE email = ?', (nova_senha_hash, email))
        conn.commit()

        cursor.execute('''
            INSERT INTO acoes_administrativas (admin_id, usuario_id, acao, data_acao, detalhes)
            VALUES (?, ?, ?, ?, ?)
        ''', (session['user_id'], target_user['id'], 'Redefinição de Senha',
              datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
              f'Senha do usuário com email {email} redefinida'))
        conn.commit()

        conn.close()
        flash('Senha redefinida com sucesso.', 'success')
        return redirect(url_for('admin_senha'))
    except sqlite3.Error as e:
        flash(f'Erro no banco de dados: {str(e)}. Contate o administrador.', 'danger')
        return redirect(url_for('admin_senha'))

@app.route('/admin/relatorio', methods=['GET', 'POST'])
@admin_required
def admin_relatorio():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # === 1. USUÁRIO E PERMISSÕES ===
        cursor.execute('SELECT municipio, role, is_admin, is_super_admin, nome FROM usuarios WHERE id = ?',
                       (session['user_id'],))
        user = cursor.fetchone()
        if not user:
            conn.close()
            flash('Usuário não encontrado.', 'error')
            return redirect(url_for('calculadora'))

        user_role = user['role']
        is_admin = user['is_admin']
        is_super_admin = user['is_super_admin']
        full_name = user['nome']

        # === 2. MUNICÍPIOS VISÍVEIS ===
        if is_super_admin == 1 and user_role == 'estadual':
            cursor.execute('SELECT DISTINCT municipio FROM calculos ORDER BY municipio')
            municipios = [row['municipio'] for row in cursor.fetchall()]
        else:
            cursor.execute('SELECT municipio FROM usuario_municipios WHERE usuario_id = ?', (session['user_id'],))
            municipios = [row['municipio'] for row in cursor.fetchall()]
            if not municipios and user['municipio']:
                municipios = [user['municipio']]

        # === 3. FILTROS ===
        filtro_municipio = request.form.get('municipio') or request.args.get('municipio')
        filtro_data_inicio = request.form.get('data_inicio') or request.args.get('data_inicio')
        filtro_data_fim = request.form.get('data_fim') or request.args.get('data_fim')

        if filtro_municipio and filtro_municipio not in municipios:
            flash('Acesso negado ao município.', 'error')
            filtro_municipio = None

        # === 4. WHERE DINÂMICO ===
        where_parts = []
        params = []

        if municipios and (is_admin == 1 or is_super_admin == 0):
            placeholders = ','.join(['?'] * len(municipios))
            where_parts.append(f"municipio IN ({placeholders})")
            params.extend(municipios)
            if filtro_municipio:
                where_parts.append("municipio = ?")
                params.append(filtro_municipio)
        elif is_super_admin == 1 and user_role == 'estadual' and filtro_municipio:
            where_parts.append("municipio = ?")
            params.append(filtro_municipio)

        if filtro_data_inicio:
            where_parts.append("data_envio >= ?")
            params.append(filtro_data_inicio)
        if filtro_data_fim:
            where_parts.append("data_envio <= ?")
            params.append(filtro_data_fim + " 23:59:59")

        where_clause = " AND ".join(where_parts)
        where_full = f"WHERE {where_clause}" if where_clause else "WHERE 1=1"

        # === 5. GESTANTES ATIVAS DISTINTAS ===
        latest_sql = f'''
            SELECT COALESCE(NULLIF(TRIM(cpf), ''), NULLIF(TRIM(cpf), '000.000.000-00'), 'sem_cpf') AS cpf_limpo,
                   nome_gestante, data_nasc, MAX(id) as max_id
            FROM calculos
            {where_full} AND desfecho IS NULL AND fa = 0
            GROUP BY cpf_limpo, nome_gestante, data_nasc
        '''
        cursor.execute(f'SELECT c.* FROM calculos c INNER JOIN ({latest_sql}) l ON c.id = l.max_id', params)
        ultimos_registros = [dict(row) for row in cursor.fetchall()]
        total_gestantes_ativas = len(ultimos_registros)

        # === 6. TODOS OS REGISTROS ===
        cursor.execute(f'SELECT * FROM calculos {where_full} ORDER BY data_envio DESC', params)
        todos_registros = [dict(row) for row in cursor.fetchall()]

        # === 7. FORA DE ÁREA + DESFECHOS DISTINTOS ===
        vista = set()
        fora_de_area_distinto = 0
        desfechos_distintos = Counter()
        for r in todos_registros:
            chave = ((r.get('cpf') or '').strip() or 'sem_cpf', r.get('nome_gestante'), r.get('data_nasc'))
            if chave not in vista:
                vista.add(chave)
                if r.get('fa') == 1:
                    fora_de_area_distinto += 1
                d = DESFECHO_MAP.get(r.get('desfecho'))
                if d and d != 'Não informado':
                    desfechos_distintos[d] += 1

        # === 8. FORMATAR CAMPOS DA TABELA ===
        for r in todos_registros:
            r['etnia_indigena'] = get_etnia_nome(r.get('etnia_indigena', ''))
            r['genero'] = GENERO_MAP.get(r.get('genero', '').strip().lower(), 'Não informado')
            r['sexualidade'] = SEXUALIDADE_MAP.get(r.get('sexualidade', '').strip().lower(), 'Não informado')
            r['raca_cor_etnia'] = RACA_COR_ETNIA_MAP.get(r.get('raca_cor_etnia', '').strip().lower(), 'Não informado')
            r['fa'] = 'Sim' if r.get('fa') == 1 else 'Não'
            r['desfecho'] = DESFECHO_MAP.get(r.get('desfecho'), '-') if r.get('desfecho') else '-'

            risco = (r.get('classificacao_risco') or '').strip().lower()
            r['classificacao_risco'] = {
                'risco habitual': 'Risco Habitual',
                'habitual': 'Risco Habitual',
                'médio risco': 'Risco Intermediário',
                'risco intermediário': 'Risco Intermediário',
                'alto risco': 'Risco Alto',
                'risco alto': 'Risco Alto'
            }.get(risco, 'Não informado')

        # === 9. CONTADORES PRINCIPAIS (SÓ GESTANTES ATIVAS) ===
        periodo_gestacional = Counter()
        genero_counts = Counter()
        sexualidade_counts = Counter()
        raca_counts = Counter()
        etnia_indigena_final = {}

        for reg in ultimos_registros:
            if reg.get('periodo_gestacional'):
                periodo_gestacional[reg['periodo_gestacional']] += 1

            genero_counts[GENERO_MAP.get(reg.get('genero', '').strip().lower(), 'Não informado')] += 1
            sexualidade_counts[SEXUALIDADE_MAP.get(reg.get('sexualidade', '').strip().lower(), 'Não informado')] += 1
            raca_counts[RACA_COR_ETNIA_MAP.get(reg.get('raca_cor_etnia', '').strip().lower(), 'Não informado')] += 1

            cod = reg.get('etnia_indigena', '').strip()
            if cod and cod not in ['', 'Não indígena', 'Não informado']:
                nome = get_etnia_nome(cod)
                if nome and nome not in ['Não indígena', 'Não informado', '-']:
                    etnia_indigena_final[nome] = etnia_indigena_final.get(nome, 0) + 1

        # === 10. CONTADORES SECUNDÁRIOS ===
        caracteristicas_counts = Counter()
        avaliacao_nutricional_counts = Counter()
        comorbidades_counts = Counter()
        historia_counts = Counter()
        condicoes_counts = Counter()
        deficiencia_counts = Counter({'Sim': 0, 'Não': 0, 'Não informado': 0})
        risco_counts = Counter()

        for reg in ultimos_registros:
            # Campos múltiplos
            for campo, mapa, cont in [
                ('caracteristicas', CARACTERISTICAS_MAP, caracteristicas_counts),
                ('avaliacao_nutricional', AVALIACAO_NUTRICIONAL_MAP, avaliacao_nutricional_counts),
                ('comorbidades', COMORBIDADES_MAP, comorbidades_counts),
                ('historia_obstetrica', HISTORIA_OBSTETRICA_MAP, historia_counts),
                ('condicoes_gestacionais', CONDICOES_GESTACIONAIS_MAP, condicoes_counts),
            ]:
                try:
                    itens = json.loads(reg[campo]) if reg.get(campo) and isinstance(reg[campo], str) else (reg[campo] or [])
                    if not isinstance(itens, list): itens = [itens] if itens else []
                    for i in itens:
                        if i and str(i).strip():
                            nome = mapa.get(i, i)
                            if nome != '-':
                                cont[nome] += 1
                except: pass

            # Deficiência
            d = (reg.get('deficiencia') or '').strip().lower()
            if d in ['sim', 's', '1', 'yes', 'true']:
                deficiencia_counts['Sim'] += 1
            elif d in ['não', 'nao', 'n', '0', 'no', 'false', '']:
                deficiencia_counts['Não'] += 1
            else:
                deficiencia_counts['Não informado'] += 1

            # Risco
            risco_raw = (reg.get('classificacao_risco') or '').strip().lower()
            risco_map = {
                'risco habitual': 'Risco Habitual', 'habitual': 'Risco Habitual',
                'médio risco': 'Risco Intermediário', 'risco intermediário': 'Risco Intermediário',
                'alto risco': 'Risco Alto', 'risco alto': 'Risco Alto'
            }
            risco_counts[risco_map.get(risco_raw, 'Não informado')] += 1

        # === 11. MÉDIA DA PONTUAÇÃO (CORRIGIDA!) ===
        pontuacoes_validas = [
            float(r['pontuacao_total']) for r in ultimos_registros
            if r.get('pontuacao_total') and str(r['pontuacao_total']).replace('.', '', 1).replace(',', '.', 1).isdigit()
        ]
        media_pontuacao = round(sum(pontuacoes_validas) / len(pontuacoes_validas), 1) if pontuacoes_validas else 0.0

        # === 12. PORCENTAGENS FINAIS ===
        def fmt(counter, total):
            return {k: {'count': v, 'porcentagem': round(v/total*100, 1) if total else 0.0}
                    for k, v in sorted(counter.items())}

        total_risco = sum(risco_counts.values()) or 1  # evita divisão por zero
        risco_hab = risco_counts.get('Risco Habitual', 0)
        risco_int = risco_counts.get('Risco Intermediário', 0)
        risco_alt = risco_counts.get('Risco Alto', 0)

# === CORREÇÃO FINAL: PORCENTAGEM ENTRE AS INDÍGENAS (100% se só tiver uma) ===
        total_indigenas = len([r for r in ultimos_registros 
                              if r.get('etnia_indigena') and str(r.get('etnia_indigena')).strip() 
                              and str(r.get('etnia_indigena')).strip() not in ['', 'Não indígena', 'Não informado']])

        etnia_final_fmt = {}
        for nome, qtd in etnia_indigena_final.items():
            porcentagem = round(qtd / total_indigenas * 100, 1) if total_indigenas > 0 else 0.0
            etnia_final_fmt[nome] = {
                'count': qtd,
                'porcentagem': porcentagem
            }

        # === 13. ESTATÍSTICAS FINAIS ===
        estatisticas = {
            'total_registros': total_gestantes_ativas,
            'total_registros_filtrados': len(todos_registros),
            'municipios_unicos': len({r['municipio'] for r in ultimos_registros if r['municipio']}),
            'periodo_gestacional': dict(periodo_gestacional),
            'genero_counts': fmt(genero_counts, total_gestantes_ativas),
            'sexualidade_counts': fmt(sexualidade_counts, total_gestantes_ativas),
            'raca_cor_etnia_counts': fmt(raca_counts, total_gestantes_ativas),
            'etnia_indigena_counts': etnia_final_fmt,
            'deficiencia_counts': dict(deficiencia_counts),
            'media_pontuacao': media_pontuacao,
            'classificacao_risco': {
                'risco_habitual': risco_hab,
                'risco_intermediario': risco_int,
                'risco_alto': risco_alt,
                'porcentagem_habitual': round(risco_hab/total_risco*100, 1),
                'porcentagem_intermediario': round(risco_int/total_risco*100, 1),
                'porcentagem_alto': round(risco_alt/total_risco*100, 1),
            },
            'caracteristicas_counts': dict(caracteristicas_counts),
            'avaliacao_nutricional_counts': dict(avaliacao_nutricional_counts),
            'comorbidades_counts': dict(comorbidades_counts),
            'historia_obstetrica_counts': dict(historia_counts),
            'condicoes_gestacionais_counts': dict(condicoes_counts),
            'desfecho_counts': dict(desfechos_distintos),
            'total_desfechos': sum(desfechos_distintos.values()),
            'fora_area_count': fora_de_area_distinto,
            'total_gestantes_distintas': len(vista)
        }

        conn.close()
        return render_template('admin_relatorio.html',
                               municipios=municipios,
                               registros=todos_registros,
                               filtro_municipio=filtro_municipio,
                               filtro_data_inicio=filtro_data_inicio,
                               filtro_data_fim=filtro_data_fim,
                               estatisticas=estatisticas,
                               is_super_admin=is_super_admin,
                               user_role=user_role,
                               full_name=full_name,
                               current_user={'role': user_role, 'name': full_name})

    except Exception as e:
        if 'conn' in locals():
            conn.close()
        logging.error(f"Erro no relatório admin: {e}", exc_info=True)
        flash('Erro ao gerar relatório. Tente novamente.', 'error')
        return redirect(url_for('calculadora'))

@app.route('/gerar_pdf/<code>')
def gerar_pdf(code):
    if 'user_id' not in session:
        flash('Por favor, faça login para baixar o PDF.', 'error')
        return redirect(url_for('login'))

    try:
        logging.debug(f"Iniciando geração de PDF para ficha {code} pelo usuário {session.get('user_id')}")
        conn = get_db_connection()
        cursor = conn.cursor()

        # Consulta com verificação de permissão
        if session.get('role') in ['municipal', 'estadual']:
            cursor.execute('SELECT * FROM calculos WHERE codigo_ficha = ?', (code,))
        else:
            cursor.execute('SELECT * FROM calculos WHERE codigo_ficha = ? AND user_id = ?', 
                           (code, session['user_id']))
        ficha = cursor.fetchone()

        if not ficha:
            cursor.execute('SELECT * FROM calculos WHERE codigo_ficha = ?', (code,))
            if cursor.fetchone():
                logging.warning(f"Ficha {code} existe, mas usuário {session['user_id']} não tem acesso")
            else:
                logging.warning(f"Ficha {code} não encontrada no banco")
            conn.close()
            flash('Ficha não encontrada ou você não tem acesso a ela.', 'error')
            return redirect(url_for('historico'))

        colunas = [desc[0] for desc in cursor.description]
        ficha_dict = dict(zip(colunas, ficha))
        conn.close()
        logging.debug(f"Dados da ficha: {ficha_dict}")

        # ✅ MAPEAMENTO E PROCESSAMENTO DOS CAMPOS JSON
        campos_json = ['caracteristicas', 'avaliacao_nutricional', 'comorbidades', 
                       'historia_obstetrica', 'condicoes_gestacionais']
        mapped_data = {}

        # MAPEAMENTO SUBMENU - PARA JUNTAR EM UMA LINHA
        MAPEAMENTO_SUBMENU = {
            'Situação de Rua': 'Situação de rua',
            'Indígena': 'Indígena',
            'Quilombola': 'Quilombola'
        }

        for campo in campos_json:
            try:
                raw_value = ficha_dict.get(campo)
                logging.debug(f"Processando {campo} com valor bruto: {raw_value} (tipo: {type(raw_value)})")
                items = []
                if raw_value and isinstance(raw_value, str) and raw_value.strip():
                    try:
                        items = json.loads(raw_value)
                        if not isinstance(items, list):
                            items = [items] if items else []
                        items = [str(item).strip() for item in items if item and str(item).strip()]
                    except json.JSONDecodeError as e:
                        logging.warning(f"JSON inválido para {campo}: {raw_value} - {str(e)}")
                        items = [raw_value.strip()] if raw_value.strip() else []
                
                # PROCESSAMENTO ESPECIAL: SUBMENU EM UMA LINHA
                mapped_items = []
                submenu_items = []
                
                for item in items:
                    if item in MAPEAMENTO_SUBMENU:
                        submenu_items.append(MAPEAMENTO_SUBMENU[item])
                    else:
                        mapped_item = map_item(campo, item)
                        if mapped_item and mapped_item != "Item Não Informado":
                            mapped_items.append(mapped_item)
                
                if submenu_items:
                    combined_submenu = ', '.join(submenu_items)
                    mapped_items.append(combined_submenu)
                
                mapped_data[campo] = mapped_items
                logging.debug(f"Itens mapeados para {campo}: {mapped_data[campo]}")
            except Exception as e:
                logging.error(f"Erro ao processar {campo}: {str(e)}")
                mapped_data[campo] = []

        # ✅ MAPEAR CAMPOS SIMPLES - INCLUINDO deficiencia
        mapped_data['genero'] = [map_item('genero', ficha_dict.get('genero', 'nao_informado'))]
        mapped_data['sexualidade'] = [map_item('sexualidade', ficha_dict.get('sexualidade', 'nao_informado'))]
        mapped_data['raca_cor_etnia'] = [map_item('raca_cor_etnia', ficha_dict.get('raca_cor_etnia', 'nao_informado'))]
        mapped_data['etnia_indigena'] = [get_etnia_nome(ficha_dict.get('etnia_indigena', ''))]
        mapped_data['deficiencia'] = [DEFICIENCIA_MAP.get(ficha_dict.get('deficiencia', 'Não'), 'Não informado')]  # ✅ Novo mapeamento

        # Determinar rótulos dinâmicos para UBS e ACS
        raca_cor_etnia = ficha_dict.get('raca_cor_etnia', '').lower()
        ubs_label = "UBS/UBSI" if raca_cor_etnia == 'indigena' else "UBS"
        acs_label = "ACS/AIS" if raca_cor_etnia == 'indigena' else "ACS"

        # Configuração do PDF
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        margin_left = 2 * cm
        margin_right = 2 * cm
        margin_top = 1.5 * cm
        margin_bottom = 2 * cm
        max_width = width - margin_left - margin_right
        total_pages = 1

        def check_page_space(c, y_position, required_space, total_pages):
            if y_position < margin_bottom + required_space:
                draw_footer(total_pages)
                c.showPage()
                draw_page_border()
                total_pages += 1
                logging.debug("Nova página criada devido a espaço insuficiente")
                return height - margin_top, total_pages
            return y_position, total_pages

        def draw_page_border():
            c.setStrokeColorRGB(0.2, 0.2, 0.2)
            c.setLineWidth(0.5)
            c.rect(
                margin_left - 10, 
                margin_bottom - 10, 
                width - margin_left - margin_right + 20, 
                height - margin_top - margin_bottom + 20
            )

        def draw_footer(page_number):
            c.saveState()
            c.setFont('Helvetica', 8)
            c.setFillColorRGB(0.5, 0.5, 0.5)
            footer_text = f"Página {page_number} | Gerado por Sistema de Classificação de Risco - SES/PB"
            c.drawCentredString(width / 2, margin_bottom - 20, footer_text)
            c.setStrokeColorRGB(0.7, 0.7, 0.7)
            c.setLineWidth(0.3)
            c.line(margin_left, margin_bottom - 5, width - margin_right, margin_bottom - 5)
            c.restoreState()

        def draw_text(c, text, x, y, font='Helvetica', font_size=9, max_width=None, centered=False):
            if not text or not isinstance(text, str):
                text = "Não informado"
            try:
                c.setFont(font, font_size)
            except Exception as e:
                logging.warning(f"Erro ao definir fonte {font}: {str(e)}. Usando Helvetica.")
                c.setFont('Helvetica', font_size)
            if centered:
                c.drawCentredString(x, y, text)
                return y - (font_size + 2) - 5
            if max_width:
                words = text.split()
                lines = []
                current_line = []
                for word in words:
                    current_line.append(word)
                    test_line = ' '.join(current_line)
                    if c.stringWidth(test_line, font, font_size) > max_width:
                        current_line.pop()
                        lines.append(' '.join(current_line))
                        current_line = [word]
                if current_line:
                    lines.append(' '.join(current_line))
                for i, line in enumerate(lines):
                    c.drawString(x, y - i * (font_size + 2), line)
                return y - len(lines) * (font_size + 2) - 5
            else:
                c.drawString(x, y, text)
                return y - (font_size + 1) - 5

        y_position = height - margin_top
        logo_path = os.path.join('static', 'imagens', 'logo.png')
        if os.path.exists(logo_path):
            img = Image(logo_path)
            img_width = 100
            img_height = img_width * (img.imageHeight / img.imageWidth)
            c.drawImage(logo_path, (width - img_width) / 2, y_position - img_height, 
                        width=img_width, height=img_height, mask='auto')
            y_position -= img_height + 10
        else:
            logging.warning(f"Logo não encontrado em: {logo_path}")
            y_position -= 10

        y_position, total_pages = check_page_space(c, y_position, 60, total_pages)
        c.setFillColorRGB(0.9, 0.9, 0.9)
        c.setStrokeColorRGB(0.5, 0.5, 0.5)
        c.setLineWidth(0.5)
        c.rect(margin_left, y_position - 40, max_width, 40, fill=1, stroke=1)
        c.setFillColorRGB(0, 0, 0)
        y_position = draw_text(c, "SECRETARIA DE ESTADO DA SAÚDE DA PARAÍBA", 
                              width / 2, y_position - 12, font='Helvetica', font_size=12, centered=True)
        y_position = draw_text(c, "INSTRUMENTO DE CLASSIFICAÇÃO DE RISCO GESTACIONAL - APS", 
                              width / 2, y_position, font='Helvetica', font_size=10, centered=True)
        y_position -= 10
        draw_page_border()

        y_position, total_pages = check_page_space(c, y_position, 40, total_pages)
        c.setFillColorRGB(0.9, 0.9, 0.9)
        c.rect(margin_left, y_position - 20, max_width, 20, fill=1, stroke=1)
        c.setFillColorRGB(0, 0, 0)
        y_position = draw_text(c, "Dados da Gestante", margin_left + 10, y_position - 12, 
                              font='Helvetica', font_size=10, max_width=max_width - 20)
        c.setStrokeColorRGB(0.7, 0.7, 0.7)
        c.line(margin_left, y_position, width - margin_right, y_position)
        y_position -= 15

        # ✅ DADOS BÁSICOS - ADICIONADO deficiencia
        etnia_indigena_nome = mapped_data['etnia_indigena'][0] if mapped_data['etnia_indigena'] and mapped_data['etnia_indigena'][0] else 'Não informado'
        dados_basicos = [
            f"Nome: {ficha_dict.get('nome_gestante', 'Não informado')}",
            f"Pessoa com Deficiência?: {mapped_data['deficiencia'][0] if mapped_data['deficiencia'] else 'Não informado'}",
            f"Identidade de Gênero: {mapped_data['genero'][0] if mapped_data['genero'] else 'Não informado'}",
            f"Orientação Sexual: {mapped_data['sexualidade'][0] if mapped_data['sexualidade'] else 'Não informado'}",
            f"Raça/Cor/Etnia: {mapped_data['raca_cor_etnia'][0] if mapped_data['raca_cor_etnia'] else 'Não informado'}",
            f"Etnia Indígena: {etnia_indigena_nome}",
            f"Data de Nascimento: {ficha_dict.get('data_nasc', 'Não informado')}",
            f"Telefone: {ficha_dict.get('telefone', 'Não informado')}",
            f"Município: {ficha_dict.get('municipio', 'Não informado')}",
            f"{ubs_label}: {ficha_dict.get('ubs', 'Não informado')}",
            f"{acs_label}: {ficha_dict.get('acs', 'Não informado')}",
            f"Período Gestacional: {ficha_dict.get('periodo_gestacional', 'Não informado')}",
            f"Data de Envio: {ficha_dict.get('data_envio', 'Não informado')}",
            f"Código da Ficha: {ficha_dict.get('codigo_ficha', 'Não informado')}",
            f"IMC: {ficha_dict.get('imc', 'Não informado') if ficha_dict.get('imc') is not None else 'Não informado'}",
            f"Profissional: {ficha_dict.get('profissional', '')}"
        ]
        logging.debug(f"Dados básicos para renderização: {dados_basicos}")

        col1_width = max_width / 2 - 10
        col2_width = col1_width
        col1_x = margin_left + 10
        col2_x = margin_left + col1_width + 20
        halfway = len(dados_basicos) // 2 + 1
        col1_items = dados_basicos[:halfway]
        col2_items = dados_basicos[halfway:]
        y_col1 = y_position
        y_col2 = y_position

        for i in range(max(len(col1_items), len(col2_items))):
            y_position, total_pages = check_page_space(c, min(y_col1, y_col2), 10, total_pages)
            if y_position != min(y_col1, y_col2):
                y_col1 = y_position
                y_col2 = y_position
            if i < len(col1_items):
                y_col1 = draw_text(c, col1_items[i], col1_x, y_col1, font='Helvetica', font_size=8, max_width=col1_width)
            if i < len(col2_items):
                y_col2 = draw_text(c, col2_items[i], col2_x, y_col2, font='Helvetica', font_size=8, max_width=col2_width)

        y_position = min(y_col1, y_col2) - 15

        secoes = [
            ("1. Características Individuais, Condições Socioeconômicas e Familiares", mapped_data['caracteristicas']),
            ("2. Avaliação Nutricional", mapped_data['avaliacao_nutricional']),
            ("3. Comorbidades Prévias à Gestação Atual", mapped_data['comorbidades']),
            ("4. Condições clínicas específicas e relacionadas às gestações prévias", mapped_data['historia_obstetrica']),
            ("5. Condições clínicas específicas e relacionadas à gestação atual", mapped_data['condicoes_gestacionais'])
        ]

        for titulo, itens in secoes:
            y_position, total_pages = check_page_space(c, y_position, 30, total_pages)
            c.setFillColorRGB(0.9, 0.9, 0.9)
            c.rect(margin_left, y_position - 18, max_width, 18, fill=1, stroke=1)
            c.setFillColorRGB(0, 0, 0)
            y_position = draw_text(c, titulo, margin_left + 10, y_position - 10, 
                                  font='Helvetica', font_size=9, max_width=max_width - 20)
            c.setStrokeColorRGB(0.7, 0.7, 0.7)
            c.line(margin_left, y_position, width - margin_right, y_position)
            y_position -= 15

            if itens:
                for item in itens:
                    y_position, total_pages = check_page_space(c, y_position, 15, total_pages)
                    c.setFont('Helvetica', 8)
                    bullet_y = y_position + 2.5
                    c.circle(margin_left + 12, bullet_y, 1.5, stroke=1, fill=1)
                    y_position = draw_text(c, item, margin_left + 20, y_position, 
                                          font='Helvetica', font_size=8, max_width=max_width - 20)
            else:
                y_position = draw_text(c, "Nenhum item selecionado.", margin_left + 20, y_position, 
                                      font='Helvetica', font_size=8, max_width=max_width - 20)
            y_position -= 10

        y_position, total_pages = check_page_space(c, y_position, 40, total_pages)
        c.setFillColorRGB(0.9, 0.9, 0.9)
        c.rect(margin_left, y_position - 18, max_width, 18, fill=1, stroke=1)
        c.setFillColorRGB(0, 0, 0)
        y_position = draw_text(c, "Resultado", margin_left + 10, y_position - 10, 
                              font='Helvetica', font_size=9, max_width=max_width - 20)
        c.setStrokeColorRGB(0.7, 0.7, 0.7)
        c.line(margin_left, y_position, width - margin_right, y_position)
        y_position -= 15
        y_position = draw_text(c, f"Pontuação Total: {ficha_dict.get('pontuacao_total', '0')}", 
                              margin_left + 10, y_position, font='Helvetica', font_size=9, max_width=max_width - 10)
        y_position = draw_text(c, f"Classificação de Risco: {ficha_dict.get('classificacao_risco', 'Não informado')}", 
                              margin_left + 10, y_position, font='Helvetica', font_size=9, max_width=max_width - 10)

        draw_footer(total_pages)
        c.save()
        buffer.seek(0)
        logging.debug(f"Tamanho do buffer do PDF: {len(buffer.getvalue())} bytes")

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"ficha_{code}.pdf",
            mimetype='application/pdf'
        )

    except sqlite3.OperationalError as e:
        if 'conn' in locals() and conn:
            conn.close()
        logging.error(f"Erro no banco de dados ao gerar PDF para ficha {code}: {str(e)}")
        flash('Erro ao acessar o banco de dados.', 'error')
        return redirect(url_for('historico'))
    except Exception as e:
        if 'conn' in locals() and conn:
            conn.close()
        logging.exception(f"Erro ao gerar PDF para ficha {code}: {str(e)}")
        flash('Erro ao gerar o PDF.', 'error')
        return redirect(url_for('historico'))

if __name__ == '__main__':
    print(app.url_map)
    app.run(debug=True)