#!/usr/bin/env python3
"""
Script para agregar la columna fecha_creacion a la tabla base_conocimiento
"""

import sqlite3
import os
from datetime import datetime

def agregar_columna_fecha():
    # Ruta a tu base de datos
    db_path = 'instance/chatbot.db'
    
    if not os.path.exists(db_path):
        print(f"❌ No se encuentra la base de datos en: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar estructura actual
        cursor.execute("PRAGMA table_info(base_conocimiento);")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print("📋 Columnas actuales:", column_names)
        
        if 'fecha_creacion' not in column_names:
            print("➕ Agregando columna fecha_creacion...")
            cursor.execute("""
                ALTER TABLE base_conocimiento 
                ADD COLUMN fecha_creacion DATETIME
            """)
            
            # Poner fecha actual en todos los registros existentes
            cursor.execute("""
                UPDATE base_conocimiento 
                SET fecha_creacion = CURRENT_TIMESTAMP 
                WHERE fecha_creacion IS NULL
            """)
            
            conn.commit()
            print("✅ Columna fecha_creacion agregada y rellenada")

        else:
            print("ℹ️ La columna fecha_creacion ya existe")
        
        # Verificar estructura final
        cursor.execute("PRAGMA table_info(base_conocimiento);")
        columns = cursor.fetchall()
        print("📋 Estructura final:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Agregando columna fecha_creacion...")
    if agregar_columna_fecha():
        print("\n🎉 ¡Listo! Ahora puedes reiniciar tu servidor Flask.")
    else:
        print("\n❌ Hubo un problema. Verifica la ruta de tu base de datos.")