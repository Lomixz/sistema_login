"""
Prueba completa del generador mejorado con todos los grupos
"""

from app import app, db
from models import Grupo, HorarioAcademico

def probar_todos_matutinos():
    with app.app_context():
        grupos = Grupo.query.filter_by(activo=True).all()
        
        matutinos = [g.id for g in grupos if g.turno == 'M']
        
        print("="*80)
        print("GENERACIÓN COMPLETA - TODOS LOS GRUPOS MATUTINOS")
        print("="*80)
        print(f"Grupos matutinos: {len(matutinos)}")
        
        from generador_horarios_mejorado import diagnosticar_y_generar
        
        resultado = diagnosticar_y_generar(
            grupos_ids=matutinos,
            periodo_academico='2026-1',
            version_nombre='Generación Completa Matutino',
            creado_por=1
        )
        
        print("\n" + "="*80)
        print("RESULTADO FINAL:")
        print("="*80)
        print(f"Éxito: {resultado['exito']}")
        print(f"Mensaje: {resultado['mensaje']}")
        print(f"Grupos procesados: {resultado.get('grupos_procesados', 0)}")
        print(f"Horarios generados: {resultado.get('horarios_generados', 0)}")
        
        if 'problemas' in resultado and resultado['problemas']:
            print("\n❌ Problemas:")
            for p in resultado['problemas']:
                print(f"   {p}")

def probar_vespertinos():
    with app.app_context():
        grupos = Grupo.query.filter_by(activo=True).all()
        
        vespertinos = [g.id for g in grupos if g.turno == 'V']
        
        if not vespertinos:
            print("No hay grupos vespertinos")
            return
        
        print("\n" + "="*80)
        print("GENERACIÓN - GRUPOS VESPERTINOS")
        print("="*80)
        print(f"Grupos vespertinos: {len(vespertinos)}")
        
        from generador_horarios_mejorado import DiagnosticoGeneracion
        
        # Solo diagnóstico (probablemente fallará)
        diagnostico = DiagnosticoGeneracion(vespertinos)
        factible = diagnostico.ejecutar_diagnostico()
        reporte = diagnostico.get_reporte()
        
        print("\n📋 DIAGNÓSTICO VESPERTINO:")
        print(f"Factible: {factible}")
        
        if reporte['problemas']:
            print("\n❌ Problemas detectados:")
            for p in reporte['problemas']:
                print(f"   {p}")
        
        if reporte['advertencias']:
            print("\n⚠️ Advertencias:")
            for a in reporte['advertencias']:
                print(f"   {a}")

if __name__ == '__main__':
    probar_todos_matutinos()
    probar_vespertinos()
