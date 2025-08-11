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
from app import app, db
with app.app_context():
    db.create_all()
    print('✅ Database tables created!')
"

echo "📊 Migrating real data..."
if [ -f "migrate_data.py" ]; then
    python migrate_data.py
    echo "✅ Real data migration completed!"
else
    echo "⚠️  migrate_data.py not found, using basic sample data"
    python -c "
from app import app, db, BaseConocimiento
with app.app_context():
    if BaseConocimiento.query.count() == 0:
        ejemplo = BaseConocimiento(consulta='linux', respuesta='Linux es un sistema operativo de código abierto.')
        db.session.add(ejemplo)
        db.session.commit()
        print('Basic sample data added')
    "
fi

echo "🎉 Build completed successfully!"