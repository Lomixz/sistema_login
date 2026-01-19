"""
Script para probar el generador de horarios mejorado
"""

from app import app, db
from models import Grupo

def probar_generacion():
    with app.app_context():
        # Obtener todos los grupos activos
        grupos = Grupo.query.filter_by(activo=True).all()
        
        print("="*80)
        print("PRUEBA DE GENERACIÓN MEJORADA")
        print("="*80)
        print(f"Grupos disponibles: {len(grupos)}")
        
        for g in grupos:
            print(f"  - {g.id}: {g.codigo} ({g.get_turno_display()})")
        
        # Separar por turno
        matutinos = [g.id for g in grupos if g.turno == 'M']
        vespertinos = [g.id for g in grupos if g.turno == 'V']
        
        print(f"\nMatutinos: {matutinos}")
        print(f"Vespertinos: {vespertinos}")
        
        # Probar solo con grupos matutinos primero (más factible)
        print("\n" + "="*80)
        print("PROBANDO CON GRUPOS MATUTINOS")
        print("="*80)
        
        from generador_horarios_mejorado import diagnosticar_y_generar
        
        if matutinos:
            resultado = diagnosticar_y_generar(
                grupos_ids=matutinos[:3],  # Solo 3 grupos para prueba
                periodo_academico='2026-1',
                version_nombre='Prueba Mejorado',
                creado_por=1
            )
            
            print("\n" + "="*80)
            print("RESULTADO:")
            print("="*80)
            print(f"Éxito: {resultado['exito']}")
            print(f"Mensaje: {resultado['mensaje']}")
            print(f"Grupos procesados: {resultado.get('grupos_procesados', 0)}")
            print(f"Horarios generados: {resultado.get('horarios_generados', 0)}")
            
            if 'problemas' in resultado and resultado['problemas']:
                print("\nProblemas detectados:")
                for p in resultado['problemas']:
                    print(f"  ❌ {p}")
            
            if 'advertencias' in resultado and resultado['advertencias']:
                print("\nAdvertencias:")
                for a in resultado['advertencias']:
                    print(f"  ⚠️ {a}")

if __name__ == '__main__':
    probar_generacion()
