import pytest
from app import app, db, Usuario, Viaje, Reserva

@pytest.fixture
def cliente():
    """ Configura el entorno de pruebas y limpia la base de datos antes de cada test. """
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost/viajes_test'
    
    with app.test_client() as cliente:
        with app.app_context():
            db.drop_all()  # Limpia la base de datos
            db.create_all()  # Crea las tablas de nuevo
        yield cliente

# 📌 1️⃣ TEST DE REGISTRO DE USUARIO
def test_registro_usuario_exitoso(cliente):
    respuesta = cliente.post('/registro', json={
        "nombre": "Sebastian Monga",
        "email": "sebas.tian5@live.com",
        "password": "securepassword"
    })
    assert respuesta.status_code == 201, f"Error: {respuesta.json}"
    assert respuesta.json["mensaje"] == "Usuario registrado"

def test_registro_usuario_falta_email(cliente):
    respuesta = cliente.post('/registro', json={
        "nombre": "Sebastian Monga",
        "password": "securepassword"
    })
    assert respuesta.status_code == 400, f"Error: {respuesta.json}"

# 📌 2️⃣ TEST DE LOGIN
def test_login_exitoso(cliente):
    cliente.post('/registro', json={
        "nombre": "Sebastian Monga",
        "email": "sebas.tian5@live.com",
        "password": "securepassword"
    })
    respuesta = cliente.post('/login', json={
        "email": "sebas.tian5@live.com",
        "password": "securepassword"
    })
    assert respuesta.status_code == 200, f"Error en login: {respuesta.json}"
    assert "token" in respuesta.json, "No se generó un token"

def test_login_fallido(cliente):
    respuesta = cliente.post('/login', json={
        "email": "juan@example.com",
        "password": "wrongpassword"
    })
    assert respuesta.status_code == 401, f"Error en login: {respuesta.json}"
    assert respuesta.json["mensaje"] == "Credenciales inválidas"

# 📌 3️⃣ TEST DE CREACIÓN DE VIAJE
def test_creacion_viaje(cliente):
    cliente.post('/registro', json={
        "nombre": "Sebastian Monga",
        "email": "sebas.tian5@live.com",
        "password": "securepassword"
    })

    respuesta_login = cliente.post('/login', json={
        "email": "sebas.tian5@live.com",
        "password": "securepassword"
    })

    assert respuesta_login.status_code == 200, f"Error en login: {respuesta_login.json}"
    assert "token" in respuesta_login.json, "No se generó un token"

    token = respuesta_login.json["token"]
    print(f"🔹 Token generado: {token}")  # <-- 🔍 DEPURACIÓN

    respuesta = cliente.post('/crear_viaje', json={
        "destino": "París",
        "fecha": "2025-06-15",
        "precio": 500.0,
        "disponibilidad": 10
    }, headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 201, f"Error en creación de viaje: {respuesta.json}"

# 📌 4️⃣ TEST DE RESERVAR VIAJE
def test_reservar_viaje(cliente):
    cliente.post('/registro', json={
        "nombre": "Sebastian Monga",
        "email": "sebas.tian5@live.com",
        "password": "securepassword"
    })
    respuesta_login = cliente.post('/login', json={
        "email": "sebas.tian5@live.com",
        "password": "securepassword"
    })
    assert respuesta_login.status_code == 200
    token = respuesta_login.json["token"]

    respuesta_viaje = cliente.post('/crear_viaje', json={
        "destino": "París",
        "fecha": "2025-06-15",
        "precio": 500.0,
        "disponibilidad": 10
    }, headers={"Authorization": f"Bearer {token}"})

    assert respuesta_viaje.status_code == 201, f"Error en creación de viaje: {respuesta_viaje.json}"
    viaje_id = respuesta_viaje.json.get("id")

    respuesta_reserva = cliente.post('/reservar', json={"viaje_id": viaje_id},
                                     headers={"Authorization": f"Bearer {token}"})

    assert respuesta_reserva.status_code == 201, f"Error en reserva: {respuesta_reserva.json}"
    assert "Reserva exitosa" in respuesta_reserva.json["mensaje"]

# 📌 5️⃣ TEST DE CANCELACIÓN DE RESERVA (CORREGIDO)
def test_cancelar_reserva(cliente):
    cliente.post('/registro', json={
        "nombre": "Sebastian Monga",
        "email": "sebas.tian5@live.com",
        "password": "securepassword"
    })
    respuesta_login = cliente.post('/login', json={
        "email": "sebas.tian5@live.com",
        "password": "securepassword"
    })
    assert respuesta_login.status_code == 200
    token = respuesta_login.json["token"]

    respuesta_viaje = cliente.post('/crear_viaje', json={
        "destino": "Cancún",
        "fecha": "2025-06-10",
        "precio": 350.0,
        "disponibilidad": 10
    }, headers={"Authorization": f"Bearer {token}"})
    assert respuesta_viaje.status_code == 201, f"Error creando viaje: {respuesta_viaje.json}"
    viaje_id = respuesta_viaje.json.get("id")

    respuesta_reserva = cliente.post('/reservar', json={"viaje_id": viaje_id},
                                     headers={"Authorization": f"Bearer {token}"})
    assert respuesta_reserva.status_code == 201, f"Error en reserva: {respuesta_reserva.json}"

    reservas_usuario = cliente.get('/mis_reservas', headers={"Authorization": f"Bearer {token}"})
    assert reservas_usuario.status_code == 200, f"Error obteniendo reservas: {reservas_usuario.json}"

    reservas = reservas_usuario.json
    print(f"🔍 Usuario autenticado al obtener reservas: {token}")
    print(f"🔍 Reservas obtenidas: {reservas}")  # DEPURACIÓN
    assert reservas, "No se encontró ninguna reserva para cancelar."


    reserva_id = reservas[0]["id"]

    print(f"🔍 Intentando cancelar reserva con ID: {reserva_id}")  # DEPURACIÓN

    respuesta_cancelacion = cliente.delete(f'/cancelar_reserva/{reserva_id}',
                                           headers={"Authorization": f"Bearer {token}"})
    
    print(f"🔍 Respuesta de cancelación: {respuesta_cancelacion.json}")  # DEPURACIÓN
    
    assert respuesta_cancelacion.status_code == 200, f"Error al cancelar reserva: {respuesta_cancelacion.json}"
    assert "Reserva cancelada" in respuesta_cancelacion.json["mensaje"]