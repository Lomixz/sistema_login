"""
Script para verificar si los profesores asignados coinciden con los generados
"""
from app import app, db
from models import HorarioAcademico, AsignacionProfesorGrupo, Grupo

with app.app_context():
    grupo = Grupo.query.filter_by(codigo='1MTII1').first()
    if not grupo:
        print('Grupo no encontrado')
        exit()
    
    print('Verificación de profesores asignados vs generados:')
    print('='*60)
    
    materias = [m for m in grupo.materias if m.activa]
    for m in materias:
        # Profesor asignado oficialmente
        asig = AsignacionProfesorGrupo.query.filter_by(
            grupo_id=grupo.id, materia_id=m.id, activo=True
        ).first()
        prof_asignado = f'{asig.profesor.nombre} {asig.profesor.apellido}' if asig and asig.profesor else 'N/A'
        
        # Profesor en horarios generados
        ha = HorarioAcademico.query.filter_by(
            grupo='1MTII1', 
            materia_id=m.id,
            activo=True
        ).first()
        prof_generado = f'{ha.profesor.nombre} {ha.profesor.apellido}' if ha and ha.profesor else 'N/A'
        
        # Contar horas generadas
        ha_count = HorarioAcademico.query.filter_by(
            grupo='1MTII1', 
            materia_id=m.id,
            activo=True
        ).count()
        
        match = '✓' if prof_asignado == prof_generado else '❌'
        horas_ok = '✓' if ha_count == m.horas_semanales else '❌'
        
        print(f'{match} {m.codigo} ({m.horas_semanales}h requeridas, {ha_count}h generadas {horas_ok}):')
        print(f'   Asignado: {prof_asignado}')
        print(f'   Generado: {prof_generado}')
