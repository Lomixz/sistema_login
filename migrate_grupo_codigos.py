#!/usr/bin/env python3
"""
Script de migración para actualizar los códigos de grupos existentes.
Cambia el formato de {numero_grupo}{turno}{carrera}{cuatrimestre}
a {cuatrimestre}{turno}{carrera}{numero_grupo}

Ejecutar: python3 migrate_grupo_codigos.py
"""

import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Grupo, Carrera


def migrate_grupo_codes():
    """Migrar códigos de grupos al nuevo formato."""
    with app.app_context():
        grupos = Grupo.query.all()
        
        if not grupos:
            print("No hay grupos en la base de datos.")
            return
        
        print(f"\n{'='*60}")
        print(f"MIGRACIÓN DE CÓDIGOS DE GRUPOS")
        print(f"{'='*60}")
        print(f"\nGrupos encontrados: {len(grupos)}")
        print(f"\nFormato anterior: {{numero_grupo}}{{turno}}{{carrera}}{{cuatrimestre}}")
        print(f"Formato nuevo:    {{cuatrimestre}}{{turno}}{{carrera}}{{numero_grupo}}")
        print(f"\n{'-'*60}")
        
        cambios = []
        
        for grupo in grupos:
            codigo_anterior = grupo.codigo
            carrera = Carrera.query.get(grupo.carrera_id)
            
            if carrera:
                codigo_nuevo = f"{grupo.cuatrimestre}{grupo.turno}{carrera.codigo}{grupo.numero_grupo}"
            else:
                codigo_nuevo = f"{grupo.cuatrimestre}{grupo.turno}XX{grupo.numero_grupo}"
            
            if codigo_anterior != codigo_nuevo:
                cambios.append({
                    'grupo': grupo,
                    'anterior': codigo_anterior,
                    'nuevo': codigo_nuevo
                })
                print(f"  {codigo_anterior:15} → {codigo_nuevo:15} (Cuatrimestre {grupo.cuatrimestre}, Grupo {grupo.numero_grupo})")
        
        if not cambios:
            print("\n✅ Todos los códigos ya están en el formato correcto.")
            return
        
        print(f"\n{'-'*60}")
        print(f"Total de cambios a realizar: {len(cambios)}")
        
        # Pedir confirmación
        respuesta = input("\n¿Desea aplicar estos cambios? (s/n): ").strip().lower()
        
        if respuesta != 's':
            print("\n❌ Migración cancelada por el usuario.")
            return
        
        # Aplicar cambios
        print("\n🔄 Aplicando cambios...")
        
        for cambio in cambios:
            cambio['grupo'].codigo = cambio['nuevo']
        
        try:
            db.session.commit()
            print(f"\n✅ ¡Migración completada! Se actualizaron {len(cambios)} códigos de grupos.")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error durante la migración: {e}")
            return
        
        # Mostrar resumen final
        print(f"\n{'='*60}")
        print("RESUMEN DE CAMBIOS APLICADOS")
        print(f"{'='*60}")
        for cambio in cambios:
            print(f"  {cambio['anterior']:15} → {cambio['nuevo']}")
        print(f"{'='*60}")


if __name__ == "__main__":
    migrate_grupo_codes()
