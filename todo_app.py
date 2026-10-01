import sqlite3
from dataclasses import dataclass
from flask import Flask, request, redirect, url_for, render_template_string, make_response
import os

# --- 1. MODELO DE DADOS (POO) ---

@dataclass
class Tarefa:
    """Modelo de dados para uma tarefa."""
    id: int
    titulo: str
    descricao: str
    concluida: bool = False

# --- 2. CAMADA DE SERVIÇO E ACESSO A DADOS (POO) ---

class GerenciadorTarefas:
    """Gerencia as operações CRUD e a conexão com o SQLite."""
    DATABASE_NAME = 'tarefas.db'

    def __init__(self):
        self._init_db()

    def _get_db_connection(self):
        """Cria e retorna uma conexão com o banco de dados."""
        conn = sqlite3.connect(self.DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Inicializa o esquema do banco de dados se não existir."""
        conn = self._get_db_connection()
        try:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tarefas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT NOT NULL,
                    descricao TEXT,
                    concluida BOOLEAN NOT NULL CHECK (concluida IN (0, 1))
                );
            ''')
            conn.commit()
        finally:
            conn.close()

    # --- 3. VALIDAÇÕES E CRUD ---

    def adicionar(self, titulo: str, descricao: str) -> bool:
        """Adiciona uma nova tarefa com validação."""
        titulo = titulo.strip()
        descricao = descricao.strip()

        if not titulo:
            print("ERRO DE VALIDAÇÃO: O título da tarefa não pode ser vazio.")
            return False

        conn = self._get_db_connection()
        try:
            conn.execute(
                'INSERT INTO tarefas (titulo, descricao, concluida) VALUES (?, ?, ?)',
                (titulo, descricao, 0)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def obter_todas(self) -> list[Tarefa]:
        """Obtém todas as tarefas do banco de dados."""
        conn = self._get_db_connection()
        tarefas = []
        try:
            cursor = conn.execute('SELECT id, titulo, descricao, concluida FROM tarefas ORDER BY id DESC')
            for row in cursor.fetchall():
                # Instanciando o objeto POO (Tarefa) a partir do resultado do banco
                tarefas.append(Tarefa(
                    id=row['id'],
                    titulo=row['titulo'],
                    descricao=row['descricao'],
                    concluida=bool(row['concluida'])
                ))
            return tarefas
        finally:
            conn.close()

    def _atualizar_status(self, tarefa_id: int, status: int):
        """Função interna para atualizar o status da tarefa."""
        if not isinstance(tarefa_id, int) or tarefa_id <= 0:
            print(f"ERRO DE VALIDAÇÃO: ID de tarefa inválido: {tarefa_id}")
            return

        conn = self._get_db_connection()
        try:
            conn.execute('UPDATE tarefas SET concluida = ? WHERE id = ?', (status, tarefa_id))
            conn.commit()
        finally:
            conn.close()

    def marcar_como_concluida(self, tarefa_id: int):
        """Marca uma tarefa como concluída (status = 1)."""
        self._atualizar_status(tarefa_id, 1)

    def desmarcar_como_concluida(self, tarefa_id: int):
        """Desmarca uma tarefa como concluída (status = 0)."""
        self._atualizar_status(tarefa_id, 0)

    def alternar_status(self, tarefa_id: int):
        """Lê o status atual da tarefa e grava o oposto, usando uma única conexão
        (evita abrir/fechar a conexão duas vezes como acontecia antes)."""
        if not isinstance(tarefa_id, int) or tarefa_id <= 0:
            print(f"ERRO DE VALIDAÇÃO: ID de tarefa inválido: {tarefa_id}")
            return

        conn = self._get_db_connection()
        try:
            cursor = conn.execute('SELECT concluida FROM tarefas WHERE id = ?', (tarefa_id,))
            row = cursor.fetchone()
            if row is not None:
                novo_status = 0 if row['concluida'] else 1
                conn.execute('UPDATE tarefas SET concluida = ? WHERE id = ?', (novo_status, tarefa_id))
                conn.commit()
        finally:
            conn.close()

    def remover(self, tarefa_id: int):
        """Remove uma tarefa do banco de dados."""
        if not isinstance(tarefa_id, int) or tarefa_id <= 0:
            print(f"ERRO DE VALIDAÇÃO: ID de tarefa inválido: {tarefa_id}")
            return

        conn = self._get_db_connection()
        try:
            conn.execute('DELETE FROM tarefas WHERE id = ?', (tarefa_id,))
            conn.commit()
        finally:
            conn.close()


# --- 4. CONFIGURAÇÃO DO FLASK E ROTAS ---

app = Flask(__name__)
# Instancia o gerenciador globalmente para uso nas rotas
gerenciador = GerenciadorTarefas()

def get_current_theme():
    """Obtém o tema atual do cookie, padrão para 'light'."""
    return request.cookies.get('theme', 'light')

# HTML/CSS (Utilizando Tailwind CSS CDN para UX/UI moderno e responsivo)
HOME_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br" class="{{ 'dark' if current_theme == 'dark' else '' }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>To-Do List Profissional</title>
    <!-- Tailwind CSS CDN para um layout moderno -->
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap');
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f5f5f5; /* Alterado para um cinza muito suave */
        }
        /* Estilos para o Dark Mode (ajustando o body principal) */
        .dark body {
            background-color: #1a202c; /* Cor de fundo escura */
        }
    </style>
</head>
<body class="p-4 sm:p-8 transition-colors duration-300">
    <div class="max-w-4xl mx-auto">
        <header class="text-center mb-10 flex flex-col sm:flex-row justify-between items-center">
            <div class="text-left mb-4 sm:mb-0">
                <h1 class="text-4xl sm:text-5xl font-extrabold text-indigo-700 dark:text-indigo-400">
                    Gerenciador de Tarefas
                </h1>
                <p class="text-gray-500 mt-2 dark:text-gray-400">
                    Simples, funcional e com validação de dados.
                </p>
            </div>
            
            <!-- Botão de Alternar Tema (Dark/Light) -->
            <a href="{{ url_for('toggle_theme') }}" class="inline-flex items-center justify-center p-3 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-yellow-400 shadow-md hover:shadow-lg transition duration-200" title="Alternar Modo">
                {% if current_theme == 'dark' %}
                    <!-- Ícone do Sol (Modo Light) -->
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                {% else %}
                    <!-- Ícone da Lua (Modo Dark) -->
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                    </svg>
                {% endif %}
            </a>

            {% if erro_validacao %}
                <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mt-4 dark:bg-red-900 dark:border-red-600 dark:text-red-300" role="alert">
                    <strong class="font-bold">Erro:</strong>
                    <span class="block sm:inline">{{ erro_validacao }}</span>
                </div>
            {% endif %}
        </header>

        <!-- Seção de Adicionar Tarefa -->
        <div class="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg mb-8 transition-colors duration-300">
            <h2 class="text-2xl font-bold mb-4 text-gray-800 dark:text-gray-100">Nova Tarefa</h2>
            <form method="POST" action="{{ url_for('adicionar_tarefa') }}" class="space-y-4">
                <input type="text" name="titulo" placeholder="Título da Tarefa (Obrigatório)" required
                       class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition duration-150 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-400">
                <textarea name="descricao" placeholder="Descrição Detalhada (Opcional)"
                          class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition duration-150 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-400"></textarea>
                <button type="submit"
                        class="w-full bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700 transition duration-200 shadow-md">
                    Adicionar Tarefa
                </button>
            </form>
        </div>

        <!-- Seção da Lista de Tarefas -->
        <h2 class="text-3xl font-bold mb-6 text-gray-800 dark:text-gray-100">Tarefas Pendentes e Concluídas</h2>
        
        <div class="space-y-4">
            {% for tarefa in tarefas %}
            {% set is_concluida = 'bg-green-50 border-green-200 dark:bg-green-800 dark:border-green-700' if tarefa.concluida else 'bg-white border-gray-200 dark:bg-gray-800 dark:border-gray-700' %}
            {% set text_style = 'text-gray-400 line-through' if tarefa.concluida else 'text-gray-800 dark:text-gray-100' %}

            <div class="{{ is_concluida }} p-5 rounded-xl border shadow-md flex items-start transition duration-300 hover:shadow-lg">
                <div class="flex-grow">
                    <h3 class="text-xl font-semibold {{ text_style }}">{{ tarefa.titulo }}</h3>
                    {% if tarefa.descricao %}
                        <p class="text-sm mt-1 {{ text_style }}">{{ tarefa.descricao }}</p>
                    {% endif %}
                </div>
                
                <div class="flex space-x-2 ml-4 flex-shrink-0">
                    <!-- Botão de Concluir/Reabrir -->
                    <form method="POST" action="{{ url_for('completar_tarefa', tarefa_id=tarefa.id) }}">
                        <button type="submit" 
                                class="p-2 rounded-full text-white shadow-md transition duration-200 
                                {% if tarefa.concluida %} bg-yellow-500 hover:bg-yellow-600 {% else %} bg-green-500 hover:bg-green-600 {% endif %}"
                                title="{% if tarefa.concluida %} Reabrir Tarefa {% else %} Marcar como Concluída {% endif %}">
                             <!-- Icone SVG simples para UX -->
                             <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                             </svg>
                        </button>
                    </form>

                    <!-- Botão de Remover -->
                    <form method="POST" action="{{ url_for('remover_tarefa', tarefa_id=tarefa.id) }}">
                        <button type="submit" 
                                class="p-2 rounded-full bg-red-500 text-white hover:bg-red-600 shadow-md transition duration-200"
                                onclick="return confirm('Tem certeza que deseja remover esta tarefa?')"
                                title="Remover Tarefa">
                             <!-- Icone SVG simples para UX -->
                             <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </form>
                </div>
            </div>
            {% endfor %}
        </div>

        {% if not tarefas %}
        <p class="text-center text-gray-500 mt-10 p-6 border-2 border-dashed border-gray-300 rounded-lg dark:text-gray-400 dark:border-gray-600">
            🎉 Tudo em ordem! Nenhuma tarefa cadastrada. Adicione uma nova acima.
        </p>
        {% endif %}

    </div>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    """Rota principal: exibe todas as tarefas."""
    current_theme = get_current_theme()
    tarefas = gerenciador.obter_todas()
    response = make_response(render_template_string(HOME_TEMPLATE, tarefas=tarefas, erro_validacao=None, current_theme=current_theme))
    return response

@app.route('/toggle_theme', methods=['GET'])
def toggle_theme():
    """Alterna o tema entre light e dark e salva a preferência em um cookie."""
    current_theme = get_current_theme()
    new_theme = 'dark' if current_theme == 'light' else 'light'
    
    # Redireciona para a página principal
    response = make_response(redirect(url_for('index')))
    
    # Define o cookie com a nova preferência de tema (válido por 30 dias)
    response.set_cookie('theme', new_theme, max_age=30*24*60*60) 
    
    return response

@app.route('/adicionar', methods=['POST'])
def adicionar_tarefa():
    """Adiciona uma nova tarefa."""
    titulo = request.form.get('titulo', '')
    descricao = request.form.get('descricao', '')

    current_theme = get_current_theme()
    
    if not gerenciador.adicionar(titulo, descricao):
        # Se a validação falhar (título vazio), exibe a mensagem de erro
        tarefas = gerenciador.obter_todas()
        erro = "O título da tarefa é obrigatório e não pode estar vazio."
        # Mantém o tema atual na página de erro
        return render_template_string(HOME_TEMPLATE, tarefas=tarefas, erro_validacao=erro, current_theme=current_theme)
    
    return redirect(url_for('index'))

@app.route('/completar/<int:tarefa_id>', methods=['POST'])
def completar_tarefa(tarefa_id):
    """Alterna o status de conclusão da tarefa (em uma única conexão com o banco)."""
    gerenciador.alternar_status(tarefa_id)
    
    return redirect(url_for('index'))

@app.route('/remover/<int:tarefa_id>', methods=['POST'])
def remover_tarefa(tarefa_id):
    """Remove uma tarefa."""
    gerenciador.remover(tarefa_id)
    return redirect(url_for('index'))

if __name__ == '__main__':
    # A linha abaixo garante que o servidor seja executado de forma simples no ambiente.
    # Em produção, usa-se um servidor WSGI, mas para o ambiente de teste, o Flask embutido é ideal.
    app.run(debug=True)
