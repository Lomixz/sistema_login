"""
Script para probar la generación de horarios para un grupo específico
"""
from app import app, db
from models import Grupo, HorarioAcademico, AsignacionProfesorGrupo
from generador_horarios_mejorado import GeneradorHorariosMejorado

def probar_generacion_grupo(grupo_codigo):
    """Probar generación para un grupo específico"""
    with app.app_context():
        # Buscar el grupo
        grupo = Grupo.query.filter_by(codigo=grupo_codigo, activo=True).first()
        if not grupo:
            print(f"❌ Grupo {grupo_codigo} no encontrado")
            return
        
        print("="*80)
        print(f"🔍 PROBANDO GENERACIÓN PARA GRUPO: {grupo_codigo}")
        print("="*80)
        
        # Información del grupo
        print(f"\nInformación del grupo:")
        print(f"  ID: {grupo.id}")
        print(f"  Turno: {grupo.get_turno_display()} ({grupo.turno})")
        print(f"  Carrera: {grupo.get_carrera_nombre()}")
        
        # Materias
        materias = [m for m in grupo.materias if m.activa]
        print(f"\nMaterias ({len(materias)}):")
        total_horas = 0
        for m in materias:
            total_horas += m.horas_semanales or 3
            asig = AsignacionProfesorGrupo.query.filter_by(
                grupo_id=grupo.id, materia_id=m.id, activo=True
            ).first()
            if asig and asig.profesor:
                print(f"  - {m.codigo}: {m.horas_semanales}h - Prof: {asig.profesor.nombre}")
            else:
                print(f"  - {m.codigo}: {m.horas_semanales}h - ❌ SIN PROFESOR")
        
        print(f"\nTotal horas requeridas: {total_horas}")
        
        # Horarios actuales
        ha_antes = HorarioAcademico.query.filter_by(grupo=grupo_codigo, activo=True).count()
        print(f"Horarios actuales: {ha_antes}")
        
        # Intentar generar
        print("\n" + "="*80)
        print("🚀 INICIANDO GENERACIÓN...")
        print("="*80)
        
        try:
            generador = GeneradorHorariosMejorado(
                grupos_ids=[grupo.id],
                periodo_academico="2025-TEST",
                version_nombre=f"Prueba {grupo_codigo}",
                creado_por=1,
                dias_semana=['lunes', 'martes', 'miercoles', 'jueves', 'viernes'],
                tiempo_limite=120,
            )
            
            resultado = generador.generar()
            
            print("\n" + "="*80)
            print("📊 RESULTADO:")
            print("="*80)
            print(f"  Éxito: {resultado['exito']}")
            print(f"  Mensaje: {resultado['mensaje']}")
            print(f"  Horarios generados: {resultado.get('horarios_generados', 0)}")
            
            # Verificar horarios después
            ha_despues = HorarioAcademico.query.filter_by(grupo=grupo_codigo, activo=True).count()
            print(f"\nHorarios en BD después: {ha_despues}")
            
            # Mostrar algunos horarios generados
            if ha_despues > 0:
                print("\nMuestra de horarios generados:")
                has = HorarioAcademico.query.filter_by(grupo=grupo_codigo, activo=True).limit(10).all()
                for ha in has:
                    print(f"  {ha.dia_semana}: {ha.materia.codigo} ({ha.horario.get_hora_inicio_str()}) - {ha.profesor.nombre}")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    import sys
    grupo_codigo = sys.argv[1] if len(sys.argv) > 1 else "1MTII1"
    probar_generacion_grupo(grupo_codigo)
