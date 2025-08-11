from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.event import listen
from sqlalchemy import or_, func, desc
from markupsafe import Markup
import numpy as np
import os
import random
from datetime import datetime, timedelta
from functools import wraps
#from transformers import pipeline
from flask_cors import CORS

app = Flask(__name__)

# Configuración para diferentes entornos
PORT = int(os.environ.get('PORT', 5000))

# Configuración de base de datos para producción
if os.environ.get('RENDER'):
    # En Render
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot.db'
    app.config['DEBUG'] = False
    ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
    ADMIN_PASS = os.environ.get('ADMIN_PASS', 'admin123')
else:
    # Local
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot.db?check_same_thread=False'
    app.config['DEBUG'] = True
    ADMIN_USER = 'admin'
    ADMIN_PASS = 'admin'

# Configuración de la base de datos (mantener como está)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False  # Desactivar en producción

app.config['SQLALCHEMY_ECHO'] = True
app.secret_key = 'tu_clave_secreta_aqui_cambiar_en_produccion'  # Cambiar en producción
# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot.db?check_same_thread=False'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Credenciales de admin (en producción usar hash)
ADMIN_USER = 'admin'
ADMIN_PASS = 'admin'

# Definir el modelo de la base de conocimiento
class BaseConocimiento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    consulta = db.Column(db.String(400), unique=True, nullable=False)
    respuesta = db.Column(db.String(2000), nullable=False)
    #categoria = db.Column(db.String(100), default='general')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<BaseConocimiento {self.consulta}>"

# Modelo para estadísticas de uso
class EstadisticasUso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    consulta = db.Column(db.String(400), nullable=False)
    respuesta_encontrada = db.Column(db.Boolean, default=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    ip_usuario = db.Column(db.String(45))  # Para IPv6

    def __repr__(self):
        return f"<EstadisticasUso {self.consulta}>"

CORS(app)

class Palabras(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    palabra = db.Column(db.String(400), nullable=False)

# Decorator para requerir autenticación
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def agregar_a_palabras(mapper, connection, target):
    connection.execute(
        Palabras.__table__.insert().values(palabra=target.consulta)
    )

listen(BaseConocimiento, 'after_insert', agregar_a_palabras)

# Función para registrar estadísticas
def registrar_estadistica(consulta, encontrada, ip):
    try:
        stat = EstadisticasUso(
            consulta=consulta,
            respuesta_encontrada=encontrada,
            ip_usuario=ip
        )
        db.session.add(stat)
        db.session.commit()
    except Exception as e:
        print(f"Error al registrar estadística: {e}")
        db.session.rollback()

# Rutas de autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '')
        password = data.get('password', '')

        if username == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            session['username'] = username
            if request.is_json:
                return jsonify({'success': True, 'message': 'Login exitoso'})
            return redirect(url_for('admin'))
        else:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Credenciales incorrectas'}), 401
            return render_template('login.html', error='Credenciales incorrectas')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/hide')
def hide():
    return render_template('hide.html')

@app.route('/')
def index():
    return render_template('index.html')

# API REST - Obtener todas las consultas (SIN CATEGORIA, CON FECHA)
@app.route('/api/consultas', methods=['GET'])
@login_required
def api_get_consultas():
    """Obtener todas las consultas - API REST"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        consultas = BaseConocimiento.query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'consultas': [{
                'id': c.id,
                'consulta': c.consulta,
                'respuesta': c.respuesta,
                'categoria': 'general',  # Valor fijo para compatibilidad con frontend
                'fecha_creacion': c.fecha_creacion.isoformat()
            } for c in consultas.items],
            'total': consultas.total,
            'pages': consultas.pages,
            'current_page': page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API REST - Crear consulta (SIN CATEGORIA, CON FECHA)
@app.route('/api/consultas', methods=['POST'])
@login_required
def api_create_consulta():
    """Crear nueva consulta - API REST"""
    try:
        data = request.get_json()
        consulta = data.get('consulta', '').strip().lower()
        respuesta = data.get('respuesta', '').strip()

        if not consulta or not respuesta:
            return jsonify({'error': 'Consulta y respuesta son requeridas'}), 400

        # Validar si ya existe
        consulta_existente = BaseConocimiento.query.filter_by(consulta=consulta).first()
        if consulta_existente:
            return jsonify({'error': 'La consulta ya existe'}), 400

        nueva_entrada = BaseConocimiento(
            consulta=consulta,
            respuesta=respuesta
            # fecha_creacion se asigna automáticamente por default
        )
        db.session.add(nueva_entrada)
        db.session.commit()

        return jsonify({
            'id': nueva_entrada.id,
            'consulta': nueva_entrada.consulta,
            'respuesta': nueva_entrada.respuesta,
            'categoria': 'general',  # Valor fijo para compatibilidad
            'fecha_creacion': nueva_entrada.fecha_creacion.isoformat(),
            'mensaje': 'Consulta creada exitosamente'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# API REST - Actualizar consulta (SIN CATEGORIA, CON FECHA)
@app.route('/api/consultas/<int:id>', methods=['PUT'])
@login_required
def api_update_consulta(id):
    """Actualizar consulta - API REST"""
    try:
        data = request.get_json()
        nueva_consulta = data.get('consulta', '').strip().lower()
        nueva_respuesta = data.get('respuesta', '').strip()

        if not nueva_consulta or not nueva_respuesta:
            return jsonify({'error': 'Consulta y respuesta son requeridas'}), 400

        entrada = BaseConocimiento.query.get_or_404(id)

        # Validar duplicados
        duplicado = BaseConocimiento.query.filter(
            BaseConocimiento.consulta == nueva_consulta,
            BaseConocimiento.id != id
        ).first()

        if duplicado:
            return jsonify({'error': 'Ya existe otra entrada con esa consulta'}), 400

        entrada.consulta = nueva_consulta
        entrada.respuesta = nueva_respuesta
        # fecha_creacion se mantiene igual (no se actualiza)
        db.session.commit()

        return jsonify({
            'id': entrada.id,
            'consulta': entrada.consulta,
            'respuesta': entrada.respuesta,
            'categoria': 'general',  # Valor fijo para compatibilidad
            'fecha_creacion': entrada.fecha_creacion.isoformat(),
            'mensaje': 'Consulta actualizada exitosamente'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# API REST - Eliminar consulta
@app.route('/api/consultas/<int:id>', methods=['DELETE'])
@login_required
def api_delete_consulta(id):
    """Eliminar consulta - API REST"""
    try:
        entrada = BaseConocimiento.query.get_or_404(id)
        db.session.delete(entrada)
        db.session.commit()
        return jsonify({'mensaje': 'Consulta eliminada exitosamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# API REST - Estadísticas
@app.route('/api/estadisticas', methods=['GET'])
@login_required
def api_estadisticas():
    """Obtener estadísticas de uso - API REST"""
    try:
        # Estadísticas generales
        total_consultas = BaseConocimiento.query.count()
        total_interacciones = EstadisticasUso.query.count()

        # Consultas más populares (últimos 30 días)
        hace_30_dias = datetime.utcnow() - timedelta(days=30)
        populares = db.session.query(
            EstadisticasUso.consulta,
            func.count(EstadisticasUso.consulta).label('count')
        ).filter(
            EstadisticasUso.fecha >= hace_30_dias
        ).group_by(EstadisticasUso.consulta).order_by(desc('count')).limit(10).all()

        # Estadísticas por día (últimos 7 días)
        stats_diarias = []
        for i in range(7):
            fecha = datetime.utcnow() - timedelta(days=i)
            inicio_dia = fecha.replace(hour=0, minute=0, second=0, microsecond=0)
            fin_dia = inicio_dia + timedelta(days=1)

            count = EstadisticasUso.query.filter(
                EstadisticasUso.fecha >= inicio_dia,
                EstadisticasUso.fecha < fin_dia
            ).count()

            stats_diarias.append({
                'fecha': inicio_dia.strftime('%Y-%m-%d'),
                'interacciones': count
            })

        # Tasa de éxito
        total_exitosas = EstadisticasUso.query.filter_by(respuesta_encontrada=True).count()
        tasa_exito = (total_exitosas / total_interacciones * 100) if total_interacciones > 0 else 0

        return jsonify({
            'total_consultas': total_consultas,
            'total_interacciones': total_interacciones,
            'tasa_exito': round(tasa_exito, 2),
            'consultas_populares': [{'consulta': c[0], 'count': c[1]} for c in populares],
            'estadisticas_diarias': list(reversed(stats_diarias))
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('mensaje', '').lower().strip()
    user_ip = request.environ.get('REMOTE_ADDR', 'unknown')

    defaults_phrases_bye = np.array(['hasta luego','adios','adiós','bye'])
    defaults_phrases_hello = np.array(['hola'])
    defaults_phrases_thanks = np.array(['gracias'])
    defaults_phrases_whatsup = np.array(['qué tal','¿qué tal?','que tal?','qué tal?'])
    reponses_to_hello = np.array(['¡Hola, bienvenido, puedes hacer consultas y responderé lo mejor posible','Hola, qué tal? ','¡Hola, cómo estás!','Hola'])
    index_array_response_to_hello = np.arange(len(reponses_to_hello))

    # Comandos especiales
    if user_message == '/help':
        registrar_estadistica(user_message, True, user_ip)
        return jsonify({
            'respuesta': 'Comandos disponibles:\n/help - Mostrar ayuda\n/stats - Ver estadísticas básicas\npalabras - Ver todas las consultas disponibles',
            'sugerencias': [],
            'origen': 'comando'
        })

    if user_message == '/stats' and 'logged_in' in session:
        total_consultas = BaseConocimiento.query.count()
        total_interacciones = EstadisticasUso.query.count()
        registrar_estadistica(user_message, True, user_ip)
        return jsonify({
            'respuesta': f'📊 Estadísticas:\n• Total consultas: {total_consultas}\n• Total interacciones: {total_interacciones}',
            'sugerencias': [],
            'origen': 'stats'
        })

    if user_message.lower() in defaults_phrases_hello:
        registrar_estadistica(user_message, True, user_ip)
        return jsonify({'respuesta': reponses_to_hello[np.random.choice(index_array_response_to_hello)], 'sugerencias':[],'origen':'local'})
    elif user_message.lower() in defaults_phrases_bye:
        registrar_estadistica(user_message, True, user_ip)
        return jsonify({'respuesta': 'Hasta luego 👋', 'sugerencias':[],'origen':'local'})
    elif user_message.lower() in defaults_phrases_thanks:
        registrar_estadistica(user_message, True, user_ip)
        return jsonify({'respuesta':'De nada, estoy aquí para ayudar 😊', 'sugerencias':[],'origen':'local'})
    elif user_message.lower() in defaults_phrases_whatsup:
        registrar_estadistica(user_message, True, user_ip)
        return jsonify({'respuesta':'Bien, gracias 🤖', 'sugerencias':[],'origen':'local'})

    if user_message.lower() == 'palabras':
        palabras_obj = Palabras.query.all()
        palabras_lista = [p.palabra for p in palabras_obj]
        registrar_estadistica(user_message, True, user_ip)
        return jsonify({'respuesta': palabras_lista, 'sugerencias':[],'origen':'palabras'})

    else:
        # Buscar en la base de datos
        respuesta_obj = BaseConocimiento.query.filter_by(consulta=user_message).first()

    if respuesta_obj:
        registrar_estadistica(user_message, True, user_ip)
        return jsonify({'respuesta': respuesta_obj.respuesta, 'sugerencias':[]})
    else:
        # Buscar consultas similares
        sugerencias = BaseConocimiento.query.filter(
            BaseConocimiento.consulta.like(f"%{user_message}%")
        ).limit(9).all()
        sugerencias_lista = [s.consulta for s in sugerencias]

        registrar_estadistica(user_message, len(sugerencias_lista) > 0, user_ip)

        if sugerencias_lista:
            return jsonify({
                'respuesta': 'No tengo una respuesta exacta. ¿Quizás quisiste decir:',
                'sugerencias': sugerencias_lista
            })
        else:
            return jsonify({'respuesta': "No tengo respuesta a tu consulta, puedes decirle al Admin que la agregue a nuestra base de conocimiento", 'sugerencias':[]})

# Rutas legacy para compatibilidad
@app.route('/agregar', methods=['POST'])
@login_required
def agregar():
    """Ruta legacy - usar /api/consultas en su lugar"""
    return api_create_consulta()

@app.route('/admin')
@login_required
def admin():
    return render_template('admin.html')

# Ruta legacy corregida
@app.route('/consultas')
@login_required
def get_consultas():
    """Ruta legacy - usar /api/consultas en su lugar"""
    consultas = BaseConocimiento.query.all()
    return jsonify([{
        'id': c.id,
        'consulta': c.consulta,
        'respuesta': c.respuesta,
        'categoria': 'general'  # Valor fijo para compatibilidad
    } for c in consultas])

@app.route('/edit/<int:id>', methods=['PUT'])
@login_required
def edit(id):
    """Ruta legacy - usar /api/consultas/<id> en su lugar"""
    return api_update_consulta(id)

def crear_base_de_datos():
    with app.app_context():
        db.create_all()


# Al final de app.py, cambiar la línea final:
if __name__ == '__main__':
    crear_base_de_datos()
    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=PORT)