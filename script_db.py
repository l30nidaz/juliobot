from app import db, BaseConocimiento, app

with app.app_context():
    # Crear entradas de prueba
    entrada3 = BaseConocimiento(consulta='crear un archivo lin', respuesta='dd if=/dev/zero of=/home/appweb/fichero bs=26M count=1')
    
    # Agregar las entradas a la base de datos
    db.session.add(entrada3)
    
    db.session.commit()
    db.session.close()
    print("Entradas agregadas a la base de datos.")
