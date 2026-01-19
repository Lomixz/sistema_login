"""
Prueba de generación SECUENCIAL de horarios
Esta es la estrategia más robusta
"""

from app import app, db
from models import Grupo, HorarioAcademico

def limpiar_horarios_previos():
    """Eliminar horarios previos de prueba"""
    with app.app_context():
        # Eliminar horarios de prueba anteriores
        deleted = HorarioAcademico.query.filter(
            HorarioAcademico.periodo_academico.like('%2026%')
        ).delete(synchronize_session=False)
        db.session.commit()
        print(f"🗑️ Eliminados {deleted} horarios previos de prueba")

def probar_secuencial():
    with app.app_context():
        # Primero limpiar
        limpiar_horarios_previos()
        
        grupos = Grupo.query.filter_by(activo=True).all()
        matutinos = [g.id for g in grupos if g.turno == 'M']
        
        print("="*80)
        print("🚀 PRUEBA DE GENERACIÓN SECUENCIAL")
        print("="*80)
        print(f"Grupos matutinos a generar: {len(matutinos)}")
        for g in grupos:
            if g.id in matutinos:
                print(f"   - {g.codigo}")
        
        from generador_horarios import generar_horarios_masivos
        
        resultado = generar_horarios_masivos(
            grupos_ids=matutinos,
            periodo_academico='2026-1',
            version_nombre='Prueba Secuencial',
            creado_por=1,
            modo='secuencial'  # USAR MODO SECUENCIAL
        )
        
        print("\n" + "="*80)
        print("📊 RESULTADO FINAL:")
        print("="*80)
        print(f"Éxito: {resultado['exito']}")
        print(f"Mensaje: {resultado['mensaje']}")
        print(f"Grupos procesados: {resultado.get('grupos_procesados', 0)}")
        print(f"Horarios generados: {resultado.get('horarios_generados', 0)}")
        
        if 'detalles' in resultado:
            print("\nDetalles por grupo:")
            for detalle in resultado['detalles']:
                if detalle.get('exito'):
                    print(f"   ✅ {detalle['grupo']}: {detalle.get('horarios', 0)} horarios")
                else:
                    print(f"   ❌ {detalle['grupo']}: {detalle.get('error', 'Error')}")

if __name__ == '__main__':
    probar_secuencial()
