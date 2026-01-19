"""
Verificar conflictos de profesores entre grupos
"""
from app import app, db
from models import HorarioAcademico, Grupo, AsignacionProfesorGrupo

with app.app_context():
    # Profesores del grupo 1MTII1
    grupo_1mtii1 = Grupo.query.filter_by(codigo='1MTII1').first()
    profesores_1mtii1 = set()
    
    for m in grupo_1mtii1.materias:
        asig = AsignacionProfesorGrupo.query.filter_by(
            grupo_id=grupo_1mtii1.id, materia_id=m.id, activo=True
        ).first()
        if asig and asig.profesor:
            profesores_1mtii1.add(asig.profesor_id)
    
    print(f'Profesores necesarios para 1MTII1: {len(profesores_1mtii1)}')
    
    # Ver si hay conflictos con horarios existentes
    print('\nProfesores con horarios ya asignados en otros grupos:')
    for prof_id in profesores_1mtii1:
        has = HorarioAcademico.query.filter_by(profesor_id=prof_id, activo=True).all()
        if has:
            prof = has[0].profesor
            grupos_set = set(ha.grupo for ha in has)
            print(f'  {prof.nombre} {prof.apellido}: {len(has)} horarios en grupos: {grupos_set}')
