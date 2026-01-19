"""
Análisis detallado de disponibilidad para el grupo 1MTII1
"""
from app import app, db
from models import Grupo, AsignacionProfesorGrupo, DisponibilidadProfesor, Horario, HorarioAcademico

with app.app_context():
    grupo = Grupo.query.filter_by(codigo='1MTII1').first()
    
    print('Análisis de disponibilidad para grupo 1MTII1:')
    print('='*60)
    
    # Obtener horarios matutinos
    horarios_mat = Horario.query.filter_by(turno='matutino', activo=True).all()
    dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
    total_slots = len(horarios_mat) * len(dias)
    
    print(f'Total slots disponibles en turno matutino: {total_slots}')
    print()
    
    materias = [m for m in grupo.materias if m.activa]
    total_horas_requeridas = 0
    
    for m in materias:
        total_horas_requeridas += m.horas_semanales or 3
        
        asig = AsignacionProfesorGrupo.query.filter_by(
            grupo_id=grupo.id, materia_id=m.id, activo=True
        ).first()
        
        if asig and asig.profesor:
            prof = asig.profesor
            
            # Contar disponibilidad en matutino
            disp_count = 0
            for h in horarios_mat:
                for dia in dias:
                    d = DisponibilidadProfesor.query.filter_by(
                        profesor_id=prof.id,
                        horario_id=h.id,
                        dia_semana=dia,
                        activo=True,
                        disponible=True
                    ).first()
                    if d:
                        disp_count += 1
            
            # Contar horarios ya ocupados (excluyendo el grupo actual)
            ocupados = HorarioAcademico.query.filter(
                HorarioAcademico.profesor_id == prof.id,
                HorarioAcademico.activo == True,
                HorarioAcademico.grupo != grupo.codigo
            ).count()
            
            capacidad = disp_count - ocupados
            status = "✓" if capacidad >= (m.horas_semanales or 3) else "❌"
            
            print(f'{status} {m.codigo} ({m.horas_semanales}h):')
            print(f'    Prof: {prof.nombre} {prof.apellido}')
            print(f'    Disp. matutino: {disp_count}, Ocupados: {ocupados}, Capacidad: {capacidad}')
            print()
    
    print(f'Total horas requeridas para el grupo: {total_horas_requeridas}')
    print(f'Capacidad del turno: {total_slots}')
    
    # Verificar conflictos entre profesores del mismo grupo
    print()
    print('='*60)
    print('Profesores con múltiples materias:')
    print('='*60)
    
    profesores_materias = {}
    for m in materias:
        asig = AsignacionProfesorGrupo.query.filter_by(
            grupo_id=grupo.id, materia_id=m.id, activo=True
        ).first()
        if asig and asig.profesor:
            prof_id = asig.profesor_id
            if prof_id not in profesores_materias:
                profesores_materias[prof_id] = {
                    'nombre': f'{asig.profesor.nombre} {asig.profesor.apellido}',
                    'materias': [],
                    'horas': 0
                }
            profesores_materias[prof_id]['materias'].append(m.codigo)
            profesores_materias[prof_id]['horas'] += m.horas_semanales or 3
    
    for prof_id, data in profesores_materias.items():
        if len(data['materias']) > 1:
            print(f"{data['nombre']}: {', '.join(data['materias'])} = {data['horas']}h total")
