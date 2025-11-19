import sqlite3

def criar_banco():
    try:
        conn = sqlite3.connect('banco.db')
        conn.row_factory = sqlite3.Row  # Para retornar dicionários
        cursor = conn.cursor()
        print("Conectado ao banco de dados 'banco.db'.")

        # Criando a tabela de usuários (cadastros normais)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            municipio TEXT NOT NULL,
            cpf TEXT NOT NULL,
            telefone TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            cnes TEXT NOT NULL,
            profissao TEXT NOT NULL,
            senha TEXT NOT NULL,
            approved INTEGER DEFAULT 0,
            ativo INTEGER DEFAULT 1,
            is_admin INTEGER DEFAULT 0,
            is_super_admin INTEGER DEFAULT 0,
            role TEXT DEFAULT 'comum' CHECK (role IN ('comum', 'municipal', 'estadual'))
        )
        ''')
        print("Tabela 'usuarios' verificada/criada.")

        # Criando a tabela de usuários de apoio
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios_apoio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            municipio TEXT,  -- Opcional, associado ao admin municipal
            acesso_saude_indigena INTEGER DEFAULT 0,  -- NOVO: 1 = acesso exclusivo ao relatório Saúde Indígena
            approved INTEGER DEFAULT 1,  -- Usuários de apoio são aprovados automaticamente
            ativo INTEGER DEFAULT 1
        )
        ''')
        print("Tabela 'usuarios_apoio' verificada/criada.")

        # Criando a tabela de mapeamento de usuários para múltiplos municípios
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuario_municipios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            municipio TEXT NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
            UNIQUE (usuario_id, municipio)  -- Evita duplicatas de município para o mesmo usuário
        )
        ''')
        print("Tabela 'usuario_municipios' verificada/criada.")

        # Criando a tabela calculos (adicionando genero, sexualidade e raca_cor_etnia)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS calculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            codigo_ficha TEXT NOT NULL,
            nome_gestante TEXT NOT NULL,
            data_nasc TEXT NOT NULL,
            cpf TEXT NOT NULL,
            telefone TEXT NOT NULL,
            municipio TEXT NOT NULL,
            ubs TEXT NOT NULL,
            acs TEXT NOT NULL,
            periodo_gestacional TEXT NOT NULL,
            data_envio TEXT NOT NULL,
            pontuacao_total TEXT NOT NULL,
            classificacao_risco TEXT NOT NULL,
            imc TEXT,
            caracteristicas TEXT,
            avaliacao_nutricional TEXT,
            comorbidades TEXT,
            historia_obstetrica TEXT,
            condicoes_gestacionais TEXT,
            profissional TEXT,
            desfecho TEXT,
            fa INTEGER DEFAULT 0,
            deficiencia TEXT,
            genero TEXT,  -- Novo campo
            sexualidade TEXT,  -- Novo campo
            raca_cor_etnia TEXT,  -- Novo campo
            pdf_compartilhado_municipal INTEGER DEFAULT 0,  -- ✅ NOVA COLUNA!
            FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE
        )
        ''')
        print("Tabela 'calculos' verificada/criada.")

        # Criando a tabela acoes_administrativas
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS acoes_administrativas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            usuario_id INTEGER,  -- Pode referenciar usuarios ou usuarios_apoio
            acao TEXT NOT NULL,
            data_acao TEXT NOT NULL,
            detalhes TEXT,
            tipo_usuario TEXT,  -- Para distinguir entre 'usuario' e 'apoio'
            FOREIGN KEY (admin_id) REFERENCES usuarios(id) ON DELETE CASCADE
        )
        ''')
        print("Tabela 'acoes_administrativas' verificada/criada.")

        # Adicionar a coluna tipo_usuario se ela não existir
        try:
            cursor.execute('ALTER TABLE acoes_administrativas ADD COLUMN tipo_usuario TEXT')
            print("Coluna 'tipo_usuario' adicionada à tabela 'acoes_administrativas'.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("Coluna 'tipo_usuario' já existe na tabela 'acoes_administrativas'.")
            else:
                print(f"Erro ao adicionar coluna 'tipo_usuario': {str(e)}")

        # === NOVO: Adicionar coluna acesso_saude_indigena se não existir ===
        try:
            cursor.execute('ALTER TABLE usuarios_apoio ADD COLUMN acesso_saude_indigena INTEGER DEFAULT 0')
            print("Coluna 'acesso_saude_indigena' adicionada à tabela 'usuarios_apoio'.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("Coluna 'acesso_saude_indigena' já existe na tabela 'usuarios_apoio'.")
            else:
                print(f"Erro ao adicionar coluna 'acesso_saude_indigena': {str(e)}")

# === NOVO: Adicionar coluna pnar se não existir ===
        try:
            cursor.execute('ALTER TABLE usuarios_apoio ADD COLUMN pnar INTEGER DEFAULT 0')
            print("Coluna 'pnar' adicionada à tabela 'usuarios_apoio'.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("Coluna 'pnar' já existe na tabela 'usuarios_apoio'.")
            else:
                print(f"Erro ao adicionar coluna 'pnar': {str(e)}")

# === NOVO: Adicionar coluna servico (AMBULATÓRIO) se não existir ===
        try:
            cursor.execute('ALTER TABLE usuarios_apoio ADD COLUMN servico TEXT')
            print("Coluna 'servico' adicionada à tabela 'usuarios_apoio'.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("Coluna 'servico' já existe na tabela 'usuarios_apoio'.")
            else:
                print(f"Erro ao adicionar coluna 'servico': {str(e)}")

        # Índice para listagem rápida de apoios ativos + PNAR
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_apoio_ativo_pnar ON usuarios_apoio(ativo, pnar, municipio)')
            print("Índice 'idx_apoio_ativo_pnar' criado com sucesso.")
        except sqlite3.Error as e:
            print(f"Aviso: Índice já existe ou erro: {str(e)}")

        # Preencher registros existentes com tipo_usuario = 'usuario'
        cursor.execute('''
            UPDATE acoes_administrativas
            SET tipo_usuario = 'usuario'
            WHERE tipo_usuario IS NULL
        ''')
        print("Registros em 'acoes_administrativas' com tipo_usuario NULL atualizados para 'usuario'.")

        # Atualizar registros existentes com municipio nulo em usuarios
        cursor.execute('UPDATE usuarios SET municipio = "Não informado" WHERE municipio IS NULL')
        print("Registros em 'usuarios' com municipio NULL atualizados para 'Não informado'.")

        # Atualizar registros antigos em calculos com CPF padrão
        cursor.execute('UPDATE calculos SET cpf = "000.000.000-00" WHERE cpf IS NULL OR cpf = ""')
        print("Registros antigos em 'calculos' atualizados com CPF padrão '000.000.000-00'.")

        # Migrar dados do campo municipio de usuarios para usuario_municipios (caso ainda não tenha sido feito)
        cursor.execute('''
            INSERT OR IGNORE INTO usuario_municipios (usuario_id, municipio)
            SELECT id, municipio FROM usuarios WHERE municipio != "Não informado"
        ''')
        print("Dados do campo 'municipio' migrados para a tabela 'usuario_municipios'.")

        # Verificar e adicionar colunas ausentes na tabela usuarios
        colunas_usuarios = [
            ('profissao', 'TEXT NOT NULL'),
            ('approved', 'INTEGER DEFAULT 0'),
            ('ativo', 'INTEGER DEFAULT 1'),
            ('is_admin', 'INTEGER DEFAULT 0'),
            ('is_super_admin', 'INTEGER DEFAULT 0'),
            ('role', 'TEXT DEFAULT "comum"')
        ]
        for coluna, tipo in colunas_usuarios:
            try:
                cursor.execute(f'ALTER TABLE usuarios ADD COLUMN {coluna} {tipo}')
                print(f"Coluna '{coluna}' adicionada à tabela 'usuarios'.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"Coluna '{coluna}' já existe na tabela 'usuarios'.")
                else:
                    print(f"Erro ao adicionar coluna '{coluna}': {str(e)}")

        # ✅ VERIFICAR E ADICIONAR COLUNAS AUSENTES NA TABELA CALCULOS
        colunas_calculos = [
            ('cpf', 'TEXT'),
            ('fa', 'INTEGER DEFAULT 0'),
            ('deficiencia', 'TEXT'),
            ('genero', 'TEXT'),
            ('sexualidade', 'TEXT'),
            ('raca_cor_etnia', 'TEXT'),
            ('etnia_indigena', 'TEXT'),
            ('pdf_compartilhado_municipal', 'INTEGER DEFAULT 0'),
            ('fora_area', 'INTEGER DEFAULT 0'),
            ('pnar_sinalizado', 'INTEGER DEFAULT 0'),     # 1 = já foi pro PNAR
            ('pnar_ambulatorio', 'TEXT DEFAULT NULL'),    # Nome do ambulatório
            ('pnar_data_registro', 'TEXT DEFAULT NULL'),  # Quando foi sinalizado
        ]
        for coluna, tipo in colunas_calculos:
            try:
                cursor.execute(f'ALTER TABLE calculos ADD COLUMN {coluna} {tipo}')
                print(f"Coluna '{coluna}' adicionada à tabela 'calculos'.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"Coluna '{coluna}' já existe na tabela 'calculos'.")
                else:
                    print(f"Erro ao adicionar coluna '{coluna}': {str(e)}")

        # ✅ ATUALIZAR VALORES PADRÃO PARA TODAS COLUNAS
        cursor.execute('UPDATE calculos SET deficiencia = "Não informado" WHERE deficiencia IS NULL')    
        cursor.execute('UPDATE calculos SET genero = "Não informado" WHERE genero IS NULL')
        cursor.execute('UPDATE calculos SET sexualidade = "Não informado" WHERE sexualidade IS NULL')
        cursor.execute('UPDATE calculos SET raca_cor_etnia = "Não informado" WHERE raca_cor_etnia IS NULL')
        cursor.execute('UPDATE calculos SET etnia_indigena = "" WHERE etnia_indigena IS NULL')
        cursor.execute('UPDATE calculos SET pdf_compartilhado_municipal = 0 WHERE pdf_compartilhado_municipal IS NULL')
        cursor.execute('UPDATE calculos SET fora_area = 0 WHERE fora_area IS NULL')
        
        print("✅ Registros em 'calculos' com deficiencia, genero, sexualidade, raca_cor_etnia, pdf_compartilhado_municipal e fora_area NULL atualizados!")

        conn.commit()
        print("✅ Banco de dados inicializado com SUCESSO + Apoio Saúde Indígena + COMPARTILHAMENTO PDF + FORA DE ÁREA!")

    except sqlite3.Error as e:
        print(f"Erro ao configurar o banco de dados: {str(e)}")
        raise
    finally:
        conn.close()
        print("Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    criar_banco()