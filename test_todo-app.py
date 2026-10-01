import pytest
import sqlite3
import os
from unittest.mock import patch, MagicMock

# Importa as classes e a aplicação do arquivo principal
# O nome do arquivo principal deve ser 'todo_app.py'
from todo_app import GerenciadorTarefas, app, Tarefa

# Define o banco de dados de teste como memória
TEST_DATABASE = ':memory:'

# --- FIXTURES (SETUP E TEARDOWN) ---

@pytest.fixture
def db_conn():
    """Fornece uma conexão de banco de dados em memória isolada e inicializa o esquema."""
    
    # 1. Configuração (Setup)
    
    # Temporariamente, alteramos a classe GerenciadorTarefas para usar o banco em memória
    original_db_name = GerenciadorTarefas.DATABASE_NAME
    GerenciadorTarefas.DATABASE_NAME = TEST_DATABASE
    
    conn = sqlite3.connect(TEST_DATABASE)
    conn.row_factory = sqlite3.Row
    
    # Cria o esquema da tabela (simulando a inicialização)
    conn.execute('''
        CREATE TABLE tarefas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT,
            concluida BOOLEAN NOT NULL CHECK (concluida IN (0, 1))
        );
    ''')
    conn.commit()
    
    yield conn  # Retorna a conexão para uso nos testes
    
    # 2. Limpeza (Teardown)
    conn.close()
    GerenciadorTarefas.DATABASE_NAME = original_db_name # Restaura o nome original


@pytest.fixture
def gerenciador(db_conn):
    """Fornece uma instância do GerenciadorTarefas configurada para o banco de teste."""
    return GerenciadorTarefas()


@pytest.fixture
def client():
    """Fornece um cliente de teste do Flask para simular requisições HTTP."""
    app.config['TESTING'] = True
    # O Flask precisa saber que está em ambiente de teste
    with app.test_client() as client:
        yield client


# --- FUNÇÃO AUXILIAR PARA CRIAR O MOCK DE CONEXÃO ---
def _mock_db_connection(db_conn):
    """Cria um MagicMock que envolve a conexão real (db_conn), mas permite
    mockar o método close() para evitar o fechamento prematuro no try/finally."""
    # Wraps db_conn, mas permite que o close seja um mock que pode ser chamado, mas não executa o close real
    mock_conn = MagicMock(wraps=db_conn)
    
    # O Pytest fará o assert de que close() foi chamado, mas não fecharemos o objeto real aqui.
    # A limpeza (teardown) do objeto real é feita pelo fixture 'db_conn'.
    mock_conn.close = MagicMock() 
    
    return mock_conn

# --- I. TESTES DA LÓGICA DE NEGÓCIOS (GERENCIADORTAREFAS) ---

@patch.object(GerenciadorTarefas, '_get_db_connection', autospec=True)
def test_adicionar_tarefa_sucesso(mock_get_conn, gerenciador, db_conn):
    """Cenário: Título válido. Resultado: Retorna True e insere no DB com concluida=0."""
    
    mock_conn = _mock_db_connection(db_conn)
    mock_get_conn.return_value = mock_conn

    # Act
    sucesso = gerenciador.adicionar("Tarefa OK", "Descrição")
    
    # Assert (Retorno da função)
    assert sucesso is True
    
    # Assert (Verificação no DB) - A verificação usa a conexão 'db_conn' que está aberta
    cursor = db_conn.execute('SELECT titulo, concluida FROM tarefas WHERE titulo = "Tarefa OK"')
    tarefa_db = cursor.fetchone()
    assert tarefa_db is not None
    assert tarefa_db['concluida'] == 0
    
    # Garante que o close foi chamado pela função adicionar
    mock_conn.close.assert_called_once()


@patch.object(GerenciadorTarefas, '_get_db_connection', autospec=True)
@pytest.mark.parametrize("titulo_invalido", ["", "  ", "\t"])
def test_adicionar_tarefa_validacao_falha(mock_get_conn, gerenciador, titulo_invalido):
    """Cenário: Título vazio/espaços. Resultado: Retorna False e não insere no DB."""
    
    # Act
    sucesso = gerenciador.adicionar(titulo_invalido, "Desc")
    
    # Assert
    assert sucesso is False
    mock_get_conn.assert_not_called()


@patch.object(GerenciadorTarefas, '_get_db_connection', autospec=True)
def test_obter_todas_tarefas(mock_get_conn, gerenciador, db_conn):
    """Cenário: Banco com 2 tarefas. Resultado: Retorna lista de 2 objetos Tarefa (POO)."""
    
    mock_conn = _mock_db_connection(db_conn)
    mock_get_conn.return_value = mock_conn
    
    # Setup: Insere dados diretamente no DB
    db_conn.execute("INSERT INTO tarefas (titulo, descricao, concluida) VALUES (?, ?, ?)", ("Tarefa Antiga", "", 0))
    db_conn.execute("INSERT INTO tarefas (titulo, descricao, concluida) VALUES (?, ?, ?)", ("Tarefa Nova", "", 1))
    db_conn.commit()

    # Act
    tarefas = gerenciador.obter_todas()
    
    # Assert
    assert len(tarefas) == 2
    assert isinstance(tarefas[0], Tarefa)
    assert tarefas[0].titulo == "Tarefa Nova" # Verifica ordenação (DESC)
    assert tarefas[1].concluida is False
    mock_conn.close.assert_called_once()


@patch.object(GerenciadorTarefas, '_get_db_connection', autospec=True)
def test_marcar_e_desmarcar_status(mock_get_conn, gerenciador, db_conn):
    """Cenário: Alternar status de uma tarefa. Resultado: O campo 'concluida' é atualizado."""
    
    mock_conn = _mock_db_connection(db_conn)
    mock_get_conn.return_value = mock_conn
    
    db_conn.execute("INSERT INTO tarefas (titulo, descricao, concluida) VALUES (?, ?, ?)", ("Status Teste", "", 0))
    db_conn.commit()
    tarefa_id = db_conn.execute("SELECT id FROM tarefas LIMIT 1").fetchone()['id']

    # 1. Marca como concluída (0 -> 1)
    gerenciador.marcar_como_concluida(tarefa_id)
    status_depois_concluir = db_conn.execute("SELECT concluida FROM tarefas WHERE id = ?", (tarefa_id,)).fetchone()['concluida']
    assert status_depois_concluir == 1

    # 2. Desmarca como concluída (1 -> 0)
    gerenciador.desmarcar_como_concluida(tarefa_id)
    status_depois_desmarcar = db_conn.execute("SELECT concluida FROM tarefas WHERE id = ?", (tarefa_id,)).fetchone()['concluida']
    assert status_depois_desmarcar == 0
    
    # Garante que o close foi chamado
    assert mock_conn.close.call_count == 2 # Chamado uma vez em marcar_como_concluida e uma em desmarcar_como_concluida


@patch.object(GerenciadorTarefas, '_get_db_connection', autospec=True)
def test_remover_tarefa(mock_get_conn, gerenciador, db_conn):
    """Cenário: Remover tarefa. Resultado: Tarefa desaparece do DB."""
    
    mock_conn = _mock_db_connection(db_conn)
    mock_get_conn.return_value = mock_conn
    
    db_conn.execute("INSERT INTO tarefas (titulo, descricao, concluida) VALUES (?, ?, ?)", ("Para Remover", "", 0))
    db_conn.commit()
    tarefa_id = db_conn.execute("SELECT id FROM tarefas LIMIT 1").fetchone()['id']
    
    # Act
    gerenciador.remover(tarefa_id)
    
    # Assert
    tarefa_removida = db_conn.execute("SELECT * FROM tarefas WHERE id = ?", (tarefa_id,)).fetchone()
    assert tarefa_removida is None
    mock_conn.close.assert_called_once()


# --- II. TESTES DAS ROTAS FLASK (INTEGRAÇÃO HTTP) ---

@patch.object(GerenciadorTarefas, '_get_db_connection', autospec=True)
def test_index_route(mock_get_conn, client, gerenciador, db_conn):
    """Cenário: Acesso à página inicial (GET /). Resultado: Status 200 OK e conteúdo principal."""
    # Para o Flask, basta garantir que o GerenciadorTarefas._get_db_connection retorne a conexão do fixture
    mock_get_conn.return_value = db_conn
    response = client.get('/')
    assert response.status_code == 200
    assert b"Gerenciador de Tarefas" in response.data


@patch.object(GerenciadorTarefas, '_get_db_connection', autospec=True)
def test_adicionar_tarefa_route_sucesso(mock_get_conn, client, gerenciador, db_conn):
    """Cenário: POST /adicionar com dados válidos. Resultado: Redirecionamento (302)."""
    mock_get_conn.return_value = db_conn
    
    # Act
    response = client.post('/adicionar', data={'titulo': 'Tarefa Web', 'descricao': 'Via formulário'})
    
    # Assert
    assert response.status_code == 302
    assert response.headers['Location'] == '/'


@patch.object(GerenciadorTarefas, '_get_db_connection', autospec=True)
def test_adicionar_tarefa_route_validacao(mock_get_conn, client, gerenciador, db_conn):
    """Cenário: POST /adicionar com título vazio. Resultado: Status 200 OK (não redireciona) e erro no HTML."""
    mock_get_conn.return_value = db_conn
    
    # Act
    response = client.post('/adicionar', data={'titulo': '  '})
    
    # Assert
    assert response.status_code == 200
    assert b"O t\xc3\xadtulo da tarefa \xc3\xa9 obrigat\xc3\xb3rio e n\xc3\xa3o pode estar vazio." in response.data


@patch.object(GerenciadorTarefas, '_get_db_connection', autospec=True)
def test_remover_e_completar_routes(mock_get_conn, client, gerenciador, db_conn):
    """Cenário: Testa as rotas POST de remoção e status. Resultado: Redirecionamento (302)."""
    
    # FIX: Cria o mock de conexão uma única vez e garante que o decorator use ele.
    mock_conn = _mock_db_connection(db_conn)
    mock_get_conn.return_value = mock_conn 
    
    # Setup: Insere uma tarefa.
    gerenciador.adicionar("Tarefa para Rotas", "Teste de POST")
        
    # Get the ID (Esta chamada usa mock_conn e não fecha db_conn)
    tarefas = gerenciador.obter_todas()
    tarefa_id = tarefas[0].id
    
    # Reset mock_conn.close call count before hitting the routes
    mock_conn.close.reset_mock()

    # 1. Testar Rota de Completar/Alternar Status
    # CORREÇÃO CRÍTICA: Desabilitar o seguimento de redirecionamento (follow_redirects=False)
    # Garante que contamos apenas a chamada interna da rota, e não a chamada subsequente à rota index.
    response_completar = client.post(f'/completar/{tarefa_id}', follow_redirects=False)
    assert response_completar.status_code == 302
    
    # 2. Testar Rota de Remover
    response_remover = client.post(f'/remover/{tarefa_id}', follow_redirects=False)
    assert response_remover.status_code == 302
    
    # Garante que o método close foi chamado exatamente DUAS vezes (1 em /completar, 1 em /remover)
    assert mock_conn.close.call_count == 2 


def test_toggle_theme_route(client):
    """Cenário: Alternar tema. Resultado: Redirecionamento (302) e cookie setado."""
    # Este teste não interage com o DB, então não precisa de patch
    
    # 1. Simula o tema atual sendo 'light' (padrão) -> Mudar para 'dark'
    response_dark = client.get('/toggle_theme')
    assert response_dark.status_code == 302
    assert 'theme=dark' in response_dark.headers['Set-Cookie']

    # 2. Simula o tema atual sendo 'dark' -> Mudar para 'light'
    response_light = client.get('/toggle_theme', headers={'Cookie': 'theme=dark'})
    assert response_light.status_code == 302
    assert 'theme=light' in response_light.headers['Set-Cookie']
