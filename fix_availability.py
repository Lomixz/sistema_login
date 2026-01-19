from app import app, db
from models import User, DisponibilidadProfesor, Horario, AsignacionProfesorGrupo, Grupo

def fix_availability():
    with app.app_context():
        print("🔧 Iniciando reparación masiva de disponibilidad...")
        
        # 1. Encontrar todos los profesores con asignaciones activas
        asignaciones = AsignacionProfesorGrupo.query.filter_by(activo=True).all()
        profesores_ids = set([a.profesor_id for a in asignaciones if a.profesor_id])
        
        print(f"📋 Analizando {len(profesores_ids)} profesores con asignaciones activas...")
        
        # Horarios matutinos (default)
        horarios = Horario.query.filter_by(turno='matutino', activo=True).all()
        dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
        
        count = 0
        for pid in profesores_ids:
            p = User.query.get(pid)
            if not p or not p.activo: continue
            
            # Verificar si tiene disponibilidad
            disp_count = DisponibilidadProfesor.query.filter_by(profesor_id=pid, activo=True, disponible=True).count()
            
            if disp_count == 0:
                print(f"  ⚠️ {p.nombre} {p.apellido} tiene 0 slots disponibles. Corrigiendo...")
                
                # Borrar anteriores por si acaso
                DisponibilidadProfesor.query.filter_by(profesor_id=pid).delete()
                
                # Crear nuevas (Lunes-Viernes, mañana)
                nuevas = []
                for dia in dias:
                    for h in horarios:
                        nueva = DisponibilidadProfesor(
                            profesor_id=p.id,
                            horario_id=h.id,
                            dia_semana=dia,
                            disponible=True,
                            creado_por=1
                        )
                        db.session.add(nueva)
                count += 1
        
        if count > 0:
            db.session.commit()
            print(f"✅ Se corrigió la disponibilidad de {count} profesores.")
        else:
            print("✅ Todos los profesores activos ya tienen disponibilidad.")

if __name__ == '__main__':
    fix_availability()
