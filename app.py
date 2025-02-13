from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import hashlib
import logging
import re
from markupsafe import escape

from flask_mail import Mail, Message
from reportlab.pdfgen import canvas
import os

# Configuración de la app
app = Flask(__name__)

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost/viajes'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'supersecreto'  # Clave secreta para JWT


# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Cambia según tu proveedor
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'jsebastian465@gmail.com'
app.config['MAIL_PASSWORD'] = 'pbgw vmoo nkqk nbgj'
app.config['MAIL_DEFAULT_SENDER'] = 'jsebastian465@gmail.com'

mail = Mail(app)

db = SQLAlchemy(app)
jwt = JWTManager(app)

# Configuración de logging
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Función para encriptar contraseñas
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Validación de email
def validar_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def generar_comprobante(reserva, tipo):
    file_path = f"comprobantes/comprobante_{reserva.id}.pdf"

    if not os.path.exists("comprobantes"):
        os.makedirs("comprobantes")

    c = canvas.Canvas(file_path)
    c.setFont("Helvetica", 14)

    c.drawString(100, 750, "Comprobante de Operación")
    c.drawString(100, 730, f"Usuario: {reserva.usuario.email}")
    c.drawString(100, 710, f"Viaje: {reserva.viaje.destino} - {reserva.viaje.fecha}")
    c.drawString(100, 690, f"Estado: {tipo}")

    c.save()
    return file_path

def enviar_comprobante(reserva, tipo):
    usuario_email = reserva.usuario.email
    file_path = generar_comprobante(reserva, tipo)

    msg = Message(f"Comprobante de {tipo}", recipients=[usuario_email])
    msg.body = f"Hola {reserva.usuario.nombre},\n\nAdjunto encontrarás el comprobante de tu {tipo}.\n\nGracias por usar Viajes Seguros S.A."
    
    with app.open_resource(file_path) as fp:
        msg.attach(f"comprobante_{reserva.id}.pdf", "application/pdf", fp.read())

    try:
        mail.send(msg)
        print(f"Correo enviado a {usuario_email}")
    except Exception as e:
        print(f"Error enviando correo: {str(e)}")


# MODELOS
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class Viaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    destino = db.Column(db.String(100), nullable=False)
    fecha = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    disponibilidad = db.Column(db.Integer, default=1)

class Reserva(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    viaje_id = db.Column(db.Integer, db.ForeignKey('viaje.id'), nullable=False)
    estado = db.Column(db.String(50), default="Reservado")

    # Relación con Usuario y Viaje
    usuario = db.relationship('Usuario', backref=db.backref('reservas', lazy=True))
    viaje = db.relationship('Viaje', backref=db.backref('reservas', lazy=True))


# Crear las tablas automáticamente
with app.app_context():
    db.create_all()

@app.route('/crear_viaje', methods=['POST'])
@jwt_required()
def crear_viaje():
    data = request.json

    if not data.get('destino') or not data.get('fecha') or not data.get('precio') or not data.get('disponibilidad'):
        return jsonify({"mensaje": "Todos los campos son obligatorios"}), 400

    try:
        nuevo_viaje = Viaje(
            destino=data['destino'],
            fecha=data['fecha'],
            precio=float(data['precio']),
            disponibilidad=int(data['disponibilidad'])
        )
        db.session.add(nuevo_viaje)
        db.session.commit()

        logging.info(f"Nuevo viaje creado: {nuevo_viaje.destino} el {nuevo_viaje.fecha}")
        return jsonify({"mensaje": "Viaje creado exitosamente", "id": nuevo_viaje.id}), 201  # ✅ Devuelve el ID del viaje creado

    except Exception as e:
        logging.error(f"Error al crear viaje: {str(e)}")
        return jsonify({"mensaje": "Error interno al crear viaje"}), 500


# REGISTRO DE USUARIOS
@app.route('/registro', methods=['POST'])
def registrar_usuario():
    data = request.json or {}

    email = data.get('email')
    nombre = data.get('nombre')
    password = data.get('password')

    if not email or not validar_email(email):
        return jsonify({"mensaje": "Formato de email inválido"}), 400
    if not password or len(password) < 6:
        return jsonify({"mensaje": "La contraseña debe tener al menos 6 caracteres"}), 400

    hashed_password = hash_password(password)
    usuario = Usuario(nombre=nombre, email=email, password=hashed_password)

    try:
        db.session.add(usuario)
        db.session.commit()
        logging.info(f"Usuario registrado: {email}")
        return jsonify({"mensaje": "Usuario registrado"}), 201
    except Exception as e:
        logging.error(f"Error en registro: {str(e)}")
        return jsonify({"mensaje": "Error al registrar usuario"}), 500

# LOGIN Y GENERACIÓN DE TOKEN
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    usuario = Usuario.query.filter_by(email=data['email']).first()
    if usuario and usuario.password == hash_password(data['password']):
        #token = create_access_token(identity=usuario.id)
        token = create_access_token(identity=str(usuario.id))  # Convertir a string
        logging.info(f"Inicio de sesión exitoso para usuario {usuario.email}")
        return jsonify({"token": token})
    
    logging.warning(f"Intento de inicio de sesión fallido para {data['email']}")
    return jsonify({"mensaje": "Credenciales inválidas"}), 401

# LISTAR VIAJES DISPONIBLES
@app.route('/viajes', methods=['GET'])
def obtener_viajes():
    viajes = Viaje.query.all()
    return jsonify([
        {
            "id": v.id,
            "destino": escape(v.destino),
            "fecha": escape(v.fecha),
            "precio": v.precio,
            "disponibilidad": v.disponibilidad
        } for v in viajes
    ])

@app.route('/buscar_viajes', methods=['GET'])
def buscar_viajes():
    destino = request.args.get('destino', type=str)
    fecha = request.args.get('fecha', type=str)
    min_precio = request.args.get('min_precio', type=float)
    max_precio = request.args.get('max_precio', type=float)

    # Iniciar la consulta base
    consulta = Viaje.query

    # Aplicar filtros opcionales
    if destino:
        consulta = consulta.filter(Viaje.destino.ilike(f"%{destino}%"))  # Búsqueda flexible
    if fecha:
        consulta = consulta.filter(Viaje.fecha == fecha)  # Fecha exacta
    if min_precio is not None:
        consulta = consulta.filter(Viaje.precio >= min_precio)  # Precio mínimo
    if max_precio is not None:
        consulta = consulta.filter(Viaje.precio <= max_precio)  # Precio máximo

    viajes = consulta.all()

    return jsonify([
        {
            "id": v.id,
            "destino": v.destino,
            "fecha": v.fecha,
            "precio": v.precio,
            "disponibilidad": v.disponibilidad
        } for v in viajes
    ])

# RESERVAR VIAJE (Requiere autenticación)
@app.route('/reservar', methods=['POST'])
@jwt_required()
def reservar_viaje():
    data = request.json
    usuario_id = get_jwt_identity()

    try:
        viaje_id = int(data['viaje_id'])
    except ValueError:
        return jsonify({"mensaje": "ID de viaje inválido"}), 400

    viaje = db.session.get(Viaje, viaje_id)
    usuario = db.session.get(Usuario, usuario_id)

    if not viaje:
        return jsonify({"mensaje": "Viaje no encontrado"}), 404
    if viaje.disponibilidad <= 0:
        return jsonify({"mensaje": "Viaje no disponible"}), 400

    nueva_reserva = Reserva(usuario_id=usuario_id, viaje_id=viaje.id)
    viaje.disponibilidad -= 1

    db.session.add(nueva_reserva)
    db.session.commit()

    enviar_comprobante(nueva_reserva, "reserva")

    return jsonify({"mensaje": "Reserva exitosa. Se envió el comprobante al correo."}), 201


# CANCELAR RESERVA (Requiere autenticación)
@app.route('/cancelar_reserva/<int:id>', methods=['DELETE'])
@jwt_required()
def cancelar_reserva(id):
    usuario_id = get_jwt_identity()  # ID del usuario autenticado

    # Obtener la reserva con el usuario precargado
    reserva = db.session.query(Reserva).options(db.joinedload(Reserva.usuario)).filter_by(id=id).first()

    if not reserva:
        return jsonify({"mensaje": "Reserva no encontrada"}), 404

    # 🔍 DEPURACIÓN: Verificar IDs
    print(f"🔍 Usuario autenticado: {usuario_id}, Dueño de la reserva: {reserva.usuario_id}")

    if reserva.usuario_id != int(usuario_id):  # Convertir a int
        return jsonify({"mensaje": "No puedes cancelar esta reserva"}), 403

    viaje = db.session.get(Viaje, reserva.viaje_id)
    viaje.disponibilidad += 1

    db.session.delete(reserva)
    db.session.commit()

    enviar_comprobante(reserva, "cancelación")

    return jsonify({"mensaje": "Reserva cancelada. Se envió el comprobante al correo."}), 200


@app.route('/mis_reservas', methods=['GET'])
@jwt_required()
def mis_reservas():
    usuario_id = get_jwt_identity()  # Obtener el ID del usuario autenticado
    reservas = Reserva.query.filter_by(usuario_id=usuario_id).all()

    if not reservas:
        return jsonify({"mensaje": "No tienes reservas"}), 404

    return jsonify([
        {
            "id": r.id,
            "viaje": r.viaje.destino,
            "fecha": r.viaje.fecha,
            "estado": r.estado
        } for r in reservas
    ]), 200


# MANEJO DE ERRORES
@app.errorhandler(400)
def bad_request(error):
    return jsonify({"mensaje": "Solicitud incorrecta"}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({"mensaje": "Recurso no encontrado"}), 404

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({"mensaje": "Error interno del servidor"}), 500

if __name__ == '__main__':
    app.run(debug=True)
