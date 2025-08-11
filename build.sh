#!/usr/bin/env bash
set -o errexit

echo "🔧 Upgrading pip..."
python -m pip install --upgrade pip

echo "📦 Installing build dependencies..."
python -m pip install setuptools>=68.0.0 wheel pip-tools

echo "📚 Installing project dependencies..."
python -m pip install -r requirements.txt

echo "🗄️ Initializing database..."
python -c "
from app import app, db, BaseConocimiento
with app.app_context():
    db.create_all()
    print('✅ Database tables created!')
    
    if BaseConocimiento.query.count() == 0:
        ejemplos = [
            BaseConocimiento(consulta='linux', respuesta='Linux es un sistema operativo de código abierto basado en Unix.'),
            BaseConocimiento(consulta='python', respuesta='Python es un lenguaje de programación de alto nivel.'),
            BaseConocimiento(consulta='flask', respuesta='Flask es un microframework web para Python.'),
            BaseConocimiento(consulta='render', respuesta='Render es una plataforma de hosting en la nube.'),
            BaseConocimiento(consulta='chatbot', respuesta='Un chatbot es un programa que simula conversaciones.')
        ]
        for ejemplo in ejemplos:
            db.session.add(ejemplo)
        db.session.commit()
        print('✅ Sample data added!')
    else:
        print('ℹ️ Database already has data')
"

echo "🎉 Build completed successfully!"